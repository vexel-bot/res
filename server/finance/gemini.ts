import type { GenerateContentResponse, GoogleGenAI } from '@google/genai';
import { financialAdmission, requestFingerprint, type FinancialAdmission } from './admission';

function usage(response?: GenerateContentResponse) {
  const data = response?.usageMetadata;
  return data && Number.isFinite(data.promptTokenCount) && Number.isFinite(data.candidatesTokenCount)
    ? { input_tokens: data.promptTokenCount!, output_tokens: data.candidatesTokenCount! + (data.thoughtsTokenCount || 0) } : {};
}

/** Wrap the existing SDK instance; preserve transport/config and all caller contracts. */
export function governGemini(client: GoogleGenAI, admission: FinancialAdmission = financialAdmission) {
  const generate = client.models.generateContent.bind(client.models);
  const stream = client.models.generateContentStream.bind(client.models);
  client.models.generateContent = async params => {
    const receipt = await admission.reserve({ provider: 'google.klic', model: params.model, operation: 'generate',
      fingerprint: requestFingerprint(params) });
    try {
      // Never silently truncate an explicitly requested output budget.
      if (params.config?.maxOutputTokens && params.config.maxOutputTokens > receipt.maxOutputTokens) throw new Error('FINANCE_OUTPUT_LIMIT');
      const result = await generate({ ...params, config: { ...params.config, maxOutputTokens: params.config?.maxOutputTokens || receipt.maxOutputTokens } });
      await receipt.settle({ outcome: 'completed', ...usage(result) });
      return result;
    } catch (error) {
      await receipt.settle({ outcome: 'unknown' }).catch(() => undefined);
      throw error;
    }
  };
  client.models.generateContentStream = async params => {
    // Admission occurs before obtaining the stream: no iterator can bypass it.
    const receipt = await admission.reserve({ provider: 'google.klic', model: params.model, operation: 'stream',
      fingerprint: requestFingerprint(params) });
    async function* guarded() {
      let final: GenerateContentResponse | undefined;
      let completed = false;
      try {
        if (params.config?.maxOutputTokens && params.config.maxOutputTokens > receipt.maxOutputTokens) throw new Error('FINANCE_OUTPUT_LIMIT');
        const upstream = await stream({ ...params, config: { ...params.config, maxOutputTokens: params.config?.maxOutputTokens || receipt.maxOutputTokens } });
        for await (const chunk of upstream) { if (chunk.usageMetadata) final = chunk; yield chunk; }
        completed = true;
      } finally {
        // Early consumer return/abort still records uncertainty and keeps the hold.
        await receipt.settle({ outcome: completed ? 'completed' : 'unknown', ...usage(final) }).catch(() => undefined);
      }
    }
    return guarded();
  };
  return client;
}
