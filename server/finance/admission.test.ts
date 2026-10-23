import assert from 'node:assert/strict';
import test from 'node:test';
import { FinancialAdmission, runWithFinancialContext, type PaidCall } from './admission';
import { governGemini } from './gemini';
import type { AuthContext } from '../governance';
import type { GoogleGenAI } from '@google/genai';
import { GoogleCloudTtsProvider } from '../voice/providers/googleCloudTtsProvider';
import { KLIC_VOICES } from '../voice/config';

const auth = { workspaceId: 'qa-company', user: { id: 'qa-member' } } as AuthContext;
const call: PaidCall = { provider: 'google.klic', model: 'qa', operation: 'generate', fingerprint: 'a'.repeat(64) };
const key = 'stage1-finance-test-key-only-'.repeat(3);
test('disabled, missing actor, unavailable admission never contacts provider', async () => {
  const old = { ...process.env };
  let requests = 0;
  const gateway = new FinancialAdmission((async () => { requests++; throw new Error('network'); }) as typeof fetch);
  try {
    process.env.CLICKO_NODE_OUTBOUND_ENABLED = 'false';
    await assert.rejects(() => gateway.reserve(call), /OUTBOUND_DISABLED/);
    process.env.CLICKO_NODE_OUTBOUND_ENABLED = 'true';
    process.env.CLICKO_STUDIOS_BRIDGE_SECRET = key;
    await assert.rejects(() => gateway.reserve(call), /AUTH_REQUIRED/);
    await runWithFinancialContext(auth, 'request-001', async () => {
      await assert.rejects(() => gateway.reserve(call), /UNAVAILABLE/);
    });
    assert.equal(requests, 1);
  } finally { process.env = old; }
});

test('SDK guards generation and stream, records tokens including thinking and early-return holds', async () => {
  const settlements: unknown[] = [];
  let admitted = 0;
  let submitted = 0;
  const gateway = { reserve: async () => {
    admitted++;
    return { maxOutputTokens: 8192, settle: async (value: unknown) => { settlements.push(value); } };
  } } as unknown as FinancialAdmission;
  const chunk = { text: 'ok', usageMetadata: { promptTokenCount: 100, candidatesTokenCount: 20, thoughtsTokenCount: 80 } };
  const sdk = governGemini({ models: {
    generateContent: async () => { submitted++; return chunk; },
    generateContentStream: async function* () { submitted++; yield chunk; yield chunk; },
  } } as unknown as GoogleGenAI, gateway);
  await sdk.models.generateContent({ model: 'qa', contents: 'hello' });
  const stream = await sdk.models.generateContentStream({ model: 'qa', contents: 'hello' });
  for await (const _chunk of stream) break;
  assert.equal(admitted, 2); assert.equal(submitted, 2);
  assert.deepEqual(settlements, [{ outcome: 'completed', input_tokens: 100, output_tokens: 100 },
    { outcome: 'unknown', input_tokens: 100, output_tokens: 100 }]);
});

test('denied admission prevents both SDK methods from running', async () => {
  let submitted = 0;
  const gateway = { reserve: async () => { throw new Error('FINANCE_ADMISSION_DENIED'); } } as unknown as FinancialAdmission;
  const sdk = governGemini({ models: {
    generateContent: async () => { submitted++; }, generateContentStream: async () => { submitted++; },
  } } as unknown as GoogleGenAI, gateway);
  await assert.rejects(() => sdk.models.generateContent({ model: 'qa', contents: 'hello' }), /ADMISSION_DENIED/);
  await assert.rejects(() => sdk.models.generateContentStream({ model: 'qa', contents: 'hello' }), /ADMISSION_DENIED/);
  assert.equal(submitted, 0);
});

test('TTS checks the same admission before constructing its Google client', async () => {
  const previous = process.env.KLIC_GOOGLE_TTS_ENABLED;
  const denied = { reserve: async () => { throw new Error('FINANCE_ADMISSION_DENIED'); } } as unknown as FinancialAdmission;
  try {
    process.env.KLIC_GOOGLE_TTS_ENABLED = 'true';
    const provider = new GoogleCloudTtsProvider(denied);
    await assert.rejects(() => provider.synthesize({ text: 'Somente QA', voice: KLIC_VOICES.male }), /ADMISSION_DENIED/);
    assert.equal((provider as unknown as { client?: unknown }).client, undefined);
  } finally {
    if (previous === undefined) delete process.env.KLIC_GOOGLE_TTS_ENABLED;
    else process.env.KLIC_GOOGLE_TTS_ENABLED = previous;
  }
});
