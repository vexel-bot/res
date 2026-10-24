import dotenv from 'dotenv';
import { randomUUID } from 'node:crypto';
import { getKlicAiClient, assertKlicText } from '../server/klic/provider';
import { klicProviderConfig } from '../server/klic/providerConfig';
import { safeGoogleFailure } from '../server/klic/providerErrors';
import { streamWithKlicRetry } from '../server/klic/providerRetry';

// Backend-only diagnostic: credentials remain exclusively in the existing provider client.
dotenv.config({ quiet: true });
const provider = klicProviderConfig();
const requestId = randomUUID();
if (!provider.configured || provider.mode !== 'developer-api') {
  console.info(JSON.stringify({ requestId, provider: provider.mode, model: provider.model, result: 'DEVELOPER_API_CONFIGURATION_REQUIRED' }));
  process.exitCode = 1;
} else {
  let attempts = 0;
  try {
    const signal = AbortSignal.timeout(90000);
    const stream = streamWithKlicRetry(async function* () {
      const upstream = await getKlicAiClient().models.generateContentStream({
        model: provider.model,
        contents: 'Olá, responda apenas: KLIC funcionando.',
        config: { abortSignal: signal, maxOutputTokens: 8192 },
      });
      for await (const chunk of upstream) {
        if (chunk.promptFeedback?.blockReason || chunk.candidates?.some(c => ['SAFETY', 'RECITATION', 'PROHIBITED_CONTENT'].includes(String(c.finishReason)))) throw new Error('KLIC_RESPONSE_BLOCKED');
        if (chunk.text) yield chunk.text;
      }
    }, signal, { requestId, provider: provider.mode, model: provider.model, stage: 'diagnostic' }, {
      report(event) {
        attempts = event.attempt;
        console.info(JSON.stringify(event));
      },
    });
    let text = '';
    for await (const chunk of stream) text += chunk;
    assertKlicText(text);
    console.info(JSON.stringify({ requestId, provider: provider.mode, model: provider.model, attempts, upstreamStatus: 200, result: text.trim() === 'KLIC funcionando.' ? 'EXPECTED_RESPONSE' : 'UNEXPECTED_RESPONSE' }));
  } catch (error) {
    console.info(JSON.stringify({ requestId, provider: provider.mode, model: provider.model, attempts, ...safeGoogleFailure(error), result: 'FAILED' }));
    process.exitCode = 1;
  }
}
