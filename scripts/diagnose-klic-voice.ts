import dotenv from 'dotenv';
import { randomUUID } from 'node:crypto';
import { klicVoiceEngine } from '../server/voice/klicVoiceEngine';
import { getKlicAiClient, assertKlicText } from '../server/klic/provider';
import { klicProviderConfig, klicTranscriptionModel } from '../server/klic/providerConfig';
import { withKlicRetry } from '../server/klic/providerRetry';
import { safeGoogleFailure } from '../server/klic/providerErrors';

dotenv.config({ quiet: true });
const requestId = randomUUID();
const provider = klicProviderConfig();
const transcriptionModel = klicTranscriptionModel();
const phrase = 'KLIC voz funcionando.';

try {
  if (!klicVoiceEngine.isEnabled()) throw new Error('KLIC_TTS_NOT_CONFIGURED');
  if (!provider.configured || provider.mode !== 'developer-api') throw new Error('KLIC_STT_NOT_CONFIGURED');
  const [male, female] = await Promise.all([
    klicVoiceEngine.synthesize(phrase, 'male'),
    klicVoiceEngine.synthesize(phrase, 'female'),
  ]);
  const signal = AbortSignal.timeout(90_000);
  const response = await withKlicRetry(() => getKlicAiClient().models.generateContent({
    model: transcriptionModel,
    contents: [{ role: 'user', parts: [
      { text: 'Transcreva fielmente a fala deste áudio em português. Retorne somente a transcrição.' },
      { inlineData: { mimeType: male.contentType, data: male.audio.toString('base64') } },
    ] }],
    config: { abortSignal: signal, maxOutputTokens: 256 },
  }), signal, { requestId, provider: provider.mode, model: transcriptionModel, stage: 'voice-diagnostic' });
  const transcript = assertKlicText(response.text).toLocaleLowerCase('pt-BR').replace(/[^a-zà-ÿ ]/g, '').trim();
  console.info(JSON.stringify({ requestId, provider: provider.mode, model: transcriptionModel, maleTts: male.audio.length > 0, femaleTts: female.audio.length > 0, stt: transcript.length > 0, result: 'COMPLETED' }));
} catch (error) {
  console.info(JSON.stringify({ requestId, provider: provider.mode, model: transcriptionModel, ...safeGoogleFailure(error), result: error instanceof Error && /^KLIC_[A-Z_]+$/.test(error.message) ? error.message : 'FAILED' }));
  process.exitCode = 1;
}
