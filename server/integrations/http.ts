import { SocialIntegrationError } from './errors';
import type { FetchLike } from './types';

type ProviderRequestInit = RequestInit & { retryTransient?: boolean };

const wait = (milliseconds: number, signal: AbortSignal) => new Promise<void>((resolve, reject) => {
  if (signal.aborted) return reject(signal.reason);
  const onAbort = () => { clearTimeout(timer); reject(signal.reason); };
  const timer = setTimeout(() => { signal.removeEventListener('abort', onAbort); resolve(); }, milliseconds);
  signal.addEventListener('abort', onAbort, { once: true });
});

function retryDelay(response: Response, attempt: number) {
  const retryAfterHeader = response.headers.get('retry-after');
  const retryAfter = retryAfterHeader === null ? Number.NaN : Number(retryAfterHeader);
  if (Number.isFinite(retryAfter) && retryAfter >= 0) return Math.min(retryAfter * 1000, 5_000);
  const resetHeader = response.headers.get('x-rate-limit-reset');
  const resetAt = resetHeader === null ? Number.NaN : Number(resetHeader);
  if (Number.isFinite(resetAt) && resetAt > 0) return Math.min(Math.max(0, resetAt * 1000 - Date.now()), 5_000);
  return Math.min(250 * 2 ** (attempt - 1) + Math.floor(Math.random() * 150), 2_000);
}

function providerFailure(response: Response, body: Record<string, unknown>) {
  const error = body.error as Record<string, unknown> | string | undefined;
  const providerCode = typeof error === 'string' ? error : typeof error?.code === 'string' || typeof error?.code === 'number' ? String(error.code) : '';
  if (response.status === 401 || providerCode === 'invalid_grant' || providerCode === 'invalid_token') {
    return new SocialIntegrationError('SOCIAL_AUTHORIZATION_REVOKED', 401, 'A autorização foi revogada ou expirou. Reconecte a conta.');
  }
  if (response.status === 403) return new SocialIntegrationError('SOCIAL_PERMISSION_INSUFFICIENT', 403, 'As permissões concedidas não são suficientes para esta ação.');
  if (response.status === 429) return new SocialIntegrationError('SOCIAL_PROVIDER_RATE_LIMIT', 429, 'A plataforma limitou temporariamente as solicitações. Tente novamente mais tarde.');
  if (response.status >= 500 || response.status === 408) return new SocialIntegrationError('SOCIAL_PROVIDER_UNAVAILABLE', 502, 'A plataforma está temporariamente indisponível.');
  if (response.status === 400 || response.status === 409 || response.status === 422) return new SocialIntegrationError('SOCIAL_CONTENT_REJECTED', 422, 'A plataforma recusou os dados enviados. Revise o conteúdo e tente novamente.');
  return new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 400, 'A plataforma recusou a solicitação. Revise a autorização e tente novamente.');
}

export async function providerResponse<T>(fetcher: FetchLike, url: string, init: ProviderRequestInit = {}): Promise<{ response: Response; body: T }> {
  if (process.env.CLICKO_DEV_MODE === 'true') throw new SocialIntegrationError('DEV_EXTERNAL_INTEGRATION_DISABLED', 503, 'Integrações externas estão desativadas no modo DEV.');
  const timeout = AbortSignal.timeout(15_000);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  const { retryTransient, ...requestInit } = init;
  const safeMethod = String(init.method || 'GET').toUpperCase();
  const mayRetry = retryTransient === true || ['GET', 'HEAD', 'OPTIONS'].includes(safeMethod);
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    let response: Response;
    try { response = await fetcher(url, { ...requestInit, signal }); }
    catch (error) {
      if (signal.aborted) throw new SocialIntegrationError('SOCIAL_PROVIDER_TIMEOUT', 504, 'A plataforma demorou para responder. Tente novamente.');
      throw error;
    }
    const body: unknown = await response.json().catch(() => ({}));
    const errorBody = body !== null && typeof body === 'object' ? body as Record<string, unknown> : {};
    const failed = !response.ok || Boolean(errorBody.error);
    const transient = response.status === 429 || response.status === 408 || response.status >= 500;
    if (failed && transient && mayRetry && attempt < 3) {
      await wait(retryDelay(response, attempt), signal);
      continue;
    }
    if (failed) throw providerFailure(response, errorBody);
    return { response, body: body as T };
  }
  throw new SocialIntegrationError('SOCIAL_PROVIDER_UNAVAILABLE', 502, 'A plataforma está temporariamente indisponível.');
}

export async function providerJson<T>(fetcher: FetchLike, url: string, init: ProviderRequestInit = {}): Promise<T> {
  return (await providerResponse<T>(fetcher, url, init)).body;
}
