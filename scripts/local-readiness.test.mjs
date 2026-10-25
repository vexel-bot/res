import assert from 'node:assert/strict';
import test from 'node:test';
import { createReadinessProbe, READINESS_TIMEOUT_MS } from './local-readiness.mjs';

test('polling shares a slow readiness request and does not abort it at one second', async () => {
  let calls = 0;
  let complete;
  const probe = createReadinessProbe('http://localhost/api/ready', { fetch: async (_url, options) => {
    calls++;
    await new Promise(resolve => { complete = resolve; });
    assert.equal(options.signal.aborted, false);
    return Response.json({ status: 'ready' });
  } });
  const first = probe(), second = probe();
  assert.equal(first, second);
  assert.equal(calls, 1);
  await new Promise(resolve => setTimeout(resolve, 1100));
  complete();
  assert.equal((await first).ready, true);
  assert.ok(READINESS_TIMEOUT_MS >= 12_000);
});

test('failed readiness can be retried and a misleading 200 never qualifies', async () => {
  let calls = 0;
  const probe = createReadinessProbe('http://localhost/api/ready', { fetch: async () => {
    calls++;
    if (calls === 1) throw new Error('starting');
    return Response.json(calls === 2 ? { status: 'ok' } : { status: 'ready' });
  } });
  assert.equal((await probe()).ready, false);
  assert.equal((await probe()).ready, false);
  assert.equal((await probe()).ready, true);
  assert.equal(calls, 3);
});
