const googleCodes = new Set(['UNAVAILABLE', 'RESOURCE_EXHAUSTED', 'UNAUTHENTICATED', 'PERMISSION_DENIED', 'NOT_FOUND', 'INVALID_ARGUMENT', 'FAILED_PRECONDITION', 'INTERNAL', 'DEADLINE_EXCEEDED', 'CANCELLED']);
const googleReasons = new Set(['SERVICE_DISABLED', 'API_DISABLED', 'API_KEY_INVALID', 'API_KEY_EXPIRED', 'API_KEY_SERVICE_BLOCKED', 'API_KEY_HTTP_REFERRER_BLOCKED', 'API_KEY_IP_ADDRESS_BLOCKED', 'BILLING_DISABLED', 'BILLING_NOT_ACTIVE', 'RATE_LIMIT_EXCEEDED', 'QUOTA_EXCEEDED', 'MODEL_NOT_FOUND', 'ACCESS_DENIED', 'CAPACITY_EXHAUSTED']);

/** Extract only known Google enums; never return messages, metadata, headers or SDK payloads. */
export function safeGoogleFailure(error: unknown) {
  const value = error as { status?: unknown; code?: unknown; message?: unknown; error?: unknown } | null;
  let body: any = value?.error;
  if (typeof value?.message === 'string') {
    // The SDK prefixes errors received during streaming with "got status: CODE. ".
    const json = value.message.replace(/^got status: [A-Z_]+\.\s*/, '');
    try {
      const parsed = JSON.parse(json);
      // Streaming HTTP failures can be returned as a one-element JSON array by Google.
      const envelope = Array.isArray(parsed) && parsed.length === 1 ? parsed[0] : parsed;
      body = envelope?.error ?? envelope;
    } catch { /* Non-JSON errors have no trusted upstream code. */ }
  }
  const status = Number(value?.status ?? body?.code ?? value?.code);
  const upstreamStatus = Number.isInteger(status) && status >= 100 && status <= 599 ? status : undefined;
  const candidate = body?.status ?? value?.code;
  const upstreamCode = googleCodes.has(candidate) ? String(candidate) : undefined;
  const reasons = Array.isArray(body?.details) ? body.details.map((detail: any) => detail?.reason) : [];
  const upstreamReason = reasons.find((reason: unknown) => googleReasons.has(reason as string)) as string | undefined;
  return { upstreamStatus, upstreamCode, upstreamReason };
}

/** Only allowlisted diagnostics cross the provider boundary; never log SDK payloads or credentials. */
export function providerFailure(error: unknown) {
  const value = error as { status?: number; code?: string | number; name?: string; message?: string; cause?: { code?: string } } | null;
  const status = Number(value?.status || value?.code) || undefined;
  const message = typeof value?.message === 'string' ? value.message : '';
  const diagnostic = `${message} ${value?.code || ''} ${value?.cause?.code || ''}`;
  let code = 'KLIC_PROVIDER_UNAVAILABLE';
  let httpStatus = 503;
  let retryable = true;
  let text = 'O serviço de IA não respondeu. Tente novamente em instantes.';
  if (message === 'KLIC_GEMINI_API_KEY_REQUIRED' || message === 'KLIC_PROVIDER_NOT_CONFIGURED') {
    code = 'KLIC_GEMINI_API_KEY_REQUIRED'; retryable = false;
    text = 'A variável privada GEMINI_API_KEY precisa ser configurada no servidor da Clicko.';
  } else if (message === 'KLIC_VERTEX_CONFIGURATION_REQUIRED') {
    code = message; retryable = false;
    text = 'O Vertex AI foi selecionado, mas GOOGLE_CLOUD_PROJECT não está configurado corretamente no servidor.';
  } else if (/SERVICE_DISABLED|API_DISABLED/.test(diagnostic)) {
    code = 'KLIC_PROVIDER_SERVICE_DISABLED'; retryable = false;
    text = 'O serviço de IA está desativado no projeto Google da Clicko. O responsável precisa habilitá-lo.';
  } else if (/BILLING_DISABLED|BILLING_NOT_ACTIVE|billing account.*(?:disabled|closed)/i.test(diagnostic)) {
    code = 'KLIC_PROVIDER_BILLING'; retryable = false;
    text = 'O provedor de IA exige a regularização do faturamento do projeto. Contate o responsável pela plataforma.';
  } else if (status === 401 || status === 403 || /API_KEY_INVALID|API_KEY_EXPIRED|UNAUTHENTICATED|PERMISSION_DENIED|invalid.*api.?key/i.test(diagnostic)) {
    code = 'KLIC_PROVIDER_ACCESS_DENIED'; retryable = false;
    text = 'O provedor recusou a credencial ou a permissão da KLIC. O responsável precisa revisar o acesso no servidor.';
  } else if (status === 429 || /RESOURCE_EXHAUSTED/.test(diagnostic)) {
    code = 'KLIC_PROVIDER_QUOTA'; httpStatus = 429;
    text = 'O provedor de IA atingiu um limite de uso. Aguarde antes de tentar novamente; se persistir, revise a cota do projeto.';
  } else if (status === 404 || /model.*(?:not found|not supported)/i.test(diagnostic)) {
    code = 'KLIC_PROVIDER_MODEL_UNAVAILABLE'; retryable = false;
    text = 'O modelo de IA configurado não está disponível para este projeto. Contate o responsável pela plataforma.';
  } else if (value?.name === 'TimeoutError' || status === 504 || /KLIC_PROVIDER_TIMEOUT|timeout|timed out|DEADLINE_EXCEEDED/i.test(diagnostic)) {
    code = 'KLIC_PROVIDER_TIMEOUT'; httpStatus = 504;
    text = 'O serviço de IA excedeu o tempo de resposta. Tente novamente.';
  } else if (/ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|fetch failed|network/i.test(diagnostic)) {
    code = 'KLIC_PROVIDER_NETWORK';
    text = 'O servidor da Clicko não conseguiu se conectar ao provedor de IA. Tente novamente em instantes.';
  } else if (message === 'KLIC_EMPTY_RESPONSE' || message === 'KLIC_RESPONSE_BLOCKED') {
    code = message; httpStatus = 502;
    text = message === 'KLIC_RESPONSE_BLOCKED' ? 'O provedor não liberou uma resposta para este pedido. Reformule a mensagem.' : 'O provedor retornou uma resposta vazia. Tente novamente.';
  } else if (message === 'KLIC_CONTEXT_LIMIT' || message === 'KLIC_OUTPUT_LIMIT') {
    code = message; httpStatus = 413; retryable = false;
    text = 'Esta consulta excedeu o limite de contexto ou de resposta. Divida o pedido em partes menores.';
  } else if (status === 400) {
    code = 'KLIC_PROVIDER_INVALID_REQUEST'; httpStatus = 502; retryable = false;
    text = 'O provedor de IA recusou o formato da consulta. Contate o responsável pela plataforma.';
  }
  return { code, status: httpStatus, retryable, message: text, upstreamStatus: status };
}

export function logProviderFailure(error: unknown, context: { requestId?: string; stage: string }) {
  const failure = providerFailure(error);
  console.warn('KLIC_PROVIDER_FAILURE', { ...context, code: failure.code, ...safeGoogleFailure(error) });
  return failure;
}
