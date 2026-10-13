import test from 'node:test';
import assert from 'node:assert/strict';
import { safeGoogleFailure } from './providerErrors';
import { isTransientGoogleFailure, streamWithKlicRetry } from './providerRetry';

const context = { provider: 'developer-api', model: 'test-only', stage: 'test', requestId: 'test-only' };
const upstream = (status: number, code: string, reason?: string) => ({ status, message: JSON.stringify({ error: { code: status, status: code, message: 'PRIVATE', details: [{ reason, metadata: { key: 'SECRET' } }] } }) });
async function collect<T>(stream: AsyncIterable<T>) { const items: T[] = []; for await (const item of stream) items.push(item); return items; }

test('safe Google diagnostics expose only known status/code/reason, not messages or arbitrary reason/metadata', () => {
  assert.deepEqual(safeGoogleFailure(upstream(503, 'UNAVAILABLE')), { upstreamStatus: 503, upstreamCode: 'UNAVAILABLE', upstreamReason: undefined });
  assert.equal(safeGoogleFailure(upstream(403, 'PERMISSION_DENIED', 'SERVICE_DISABLED')).upstreamReason, 'SERVICE_DISABLED');
  const streamed = upstream(503, 'UNAVAILABLE');
  streamed.message = `got status: UNAVAILABLE. ${streamed.message}`;
  assert.equal(safeGoogleFailure(streamed).upstreamCode, 'UNAVAILABLE');
  assert.equal(isTransientGoogleFailure(streamed), true);
  const arrayError = upstream(503, 'UNAVAILABLE');
  arrayError.message = `[${arrayError.message}]`;
  assert.equal(safeGoogleFailure(arrayError).upstreamCode, 'UNAVAILABLE');
  assert.equal(isTransientGoogleFailure(arrayError), true);
  for (const error of [upstream(503, 'SECRET', 'SECRET'), { message: 'PRIVATE SECRET' }, null]) assert.doesNotMatch(JSON.stringify(safeGoogleFailure(error)), /SECRET|PRIVATE/);
});

test('only exact transient pairs are retryable; permanent failures and unrelated 5xx are not', () => {
  assert.equal(isTransientGoogleFailure(upstream(503, 'UNAVAILABLE')), true);
  assert.equal(isTransientGoogleFailure(upstream(429, 'RESOURCE_EXHAUSTED')), true);
  assert.equal(isTransientGoogleFailure({ status: 503 }), true);
  assert.equal(isTransientGoogleFailure({ status: 429 }), true);
  for (const error of [upstream(401, 'UNAUTHENTICATED'), upstream(403, 'PERMISSION_DENIED'), upstream(404, 'NOT_FOUND'), upstream(400, 'INVALID_ARGUMENT'), upstream(500, 'INTERNAL'), upstream(503, 'PERMISSION_DENIED'), upstream(429, 'RESOURCE_EXHAUSTED', 'API_KEY_INVALID'), upstream(503, 'UNAVAILABLE', 'SERVICE_DISABLED'), new Error('KLIC_EMPTY_RESPONSE')]) assert.equal(isTransientGoogleFailure(error), false);
  for (const reason of ['MODEL_NOT_FOUND', 'API_KEY_SERVICE_BLOCKED', 'API_KEY_IP_ADDRESS_BLOCKED', 'ACCESS_DENIED']) assert.equal(isTransientGoogleFailure(upstream(503, 'UNAVAILABLE', reason)), false);
});

test('503 and 429 stop at three total attempts, with exponential backoff and jitter', async () => {
  for (const error of [upstream(503, 'UNAVAILABLE'), upstream(429, 'RESOURCE_EXHAUSTED')]) {
    let attempts = 0; const waits: number[] = []; const events: unknown[] = [];
    const operation = async function* (): AsyncGenerator<string> { attempts++; throw error; };
    await assert.rejects(() => collect(streamWithKlicRetry(operation, new AbortController().signal, context, { random: () => 0.8, wait: async ms => { waits.push(ms); }, report: event => events.push(event) })), e => e === error);
    assert.equal(attempts, 3); assert.deepEqual(waits, [1150, 2300]);
    assert.doesNotMatch(JSON.stringify(events), /PRIVATE|SECRET/);
  }
});

test('two transient failures then success emit exactly one response; permanent failures never sleep', async () => {
  let attempts = 0;
  const operation = async function* () { if (++attempts < 3) throw upstream(503, 'UNAVAILABLE'); yield 'real-path-test'; };
  assert.deepEqual(await collect(streamWithKlicRetry(operation, new AbortController().signal, context, { wait: async () => {}, report: () => {} })), ['real-path-test']);
  assert.equal(attempts, 3);
  for (const error of [upstream(401, 'UNAUTHENTICATED'), upstream(403, 'PERMISSION_DENIED'), upstream(404, 'NOT_FOUND')]) {
    attempts = 0;
    await assert.rejects(() => collect(streamWithKlicRetry(async function* (): AsyncGenerator<string> { attempts++; throw error; }, new AbortController().signal, context, { wait: async () => { assert.fail('Permanent error must not wait'); }, report: () => {} })), e => e === error);
    assert.equal(attempts, 1);
  }
});

test('partial stream failures cannot replay content or duplicate output', async () => {
  let attempts = 0; const items: string[] = [];
  await assert.rejects(async () => {
    for await (const item of streamWithKlicRetry(async function* () { attempts++; yield 'partial'; throw upstream(503, 'UNAVAILABLE'); }, new AbortController().signal, context, { report: () => {} })) items.push(item);
  });
  assert.equal(attempts, 1); assert.deepEqual(items, ['partial']);
});

test('cancellation during actual backoff clears the pending delay and prevents another attempt', async () => {
  const controller = new AbortController(); let attempts = 0;
  const stream = streamWithKlicRetry(async function* (): AsyncGenerator<string> { attempts++; throw upstream(503, 'UNAVAILABLE'); }, controller.signal, context, { report: event => { if (event.event === 'failed') queueMicrotask(() => controller.abort()); } });
  await assert.rejects(() => collect(stream), error => error instanceof Error && error.name === 'AbortError');
  assert.equal(attempts, 1);
});

test('an expired total deadline starts no provider attempt', async () => {
  const controller = new AbortController(); const reason = new DOMException('deadline', 'TimeoutError'); controller.abort(reason);
  await assert.rejects(() => collect(streamWithKlicRetry(async function* () { assert.fail('Must not start'); yield ''; }, controller.signal, context)), error => error === reason);
});
