import test from 'node:test';
import assert from 'node:assert/strict';
import { studiosReadiness } from './readiness';

test('readiness rejects unavailable services, HTML SPA responses and misleading 200 bodies', async () => {
  for (const response of [new Response('<html>SPA</html>'), Response.json({ status: 'ready' }),
    Response.json({ status: 'ready', service: 'clicko-studios' }),
    Response.json({ status: 'not_ready', service: 'clicko-studios' }, { status: 503 })]) {
    assert.equal((await studiosReadiness({ origin: 'http://127.0.0.1:8018', fetch: async () => response })).status, 'not_ready');
  }
  assert.equal((await studiosReadiness({ fetch: async () => { throw new Error('offline'); } })).status, 'not_ready');
  assert.equal((await studiosReadiness({ fetch: async () => Response.json({ status: 'ready', service: 'clicko-studios',
    dependencies: { database: 'ok', storage: 'ok', ffmpeg: 'ok', queue: 'local-thread-pool' } }) })).status, 'ready');
});
