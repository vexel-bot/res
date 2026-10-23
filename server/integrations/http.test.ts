import assert from 'node:assert/strict';
import test from 'node:test';
import { SocialIntegrationError } from './errors';
import { providerJson } from './http';

test('non-object provider errors retain public HTTP classification without payload leaks', async () => {
  for (const body of ['null', '"PRIVATE"', '42', 'false', '[]', '<html>SECRET</html>']) {
    for (const [status, code] of [[401, 'SOCIAL_AUTHORIZATION_REVOKED'], [403, 'SOCIAL_PERMISSION_INSUFFICIENT'],
      [422, 'SOCIAL_CONTENT_REJECTED'], [503, 'SOCIAL_PROVIDER_UNAVAILABLE']] as const) {
      let requests = 0;
      const fetcher = (async () => { requests++; return new Response(body, { status }); }) as typeof fetch;
      await assert.rejects(providerJson(fetcher, 'https://provider.example/test', { method: 'POST' }), error => {
        assert.ok(error instanceof SocialIntegrationError);
        assert.equal(error.code, code);
        assert.doesNotMatch(error.publicMessage, /SECRET|PRIVATE/);
        return true;
      });
      assert.equal(requests, 1, 'writes must not be retried');
    }
  }
});

test('successful provider arrays, objects and null are returned without rewriting their shape', async () => {
  for (const body of [[{ id: 'account-1' }], { data: [] }, null]) {
    const fetcher = (async () => new Response(JSON.stringify(body))) as typeof fetch;
    assert.deepEqual(await providerJson(fetcher, 'https://provider.example/test'), body);
  }
});

test('null transient read errors retain the existing bounded retry policy', async () => {
  let requests = 0;
  const fetcher = (async () => ++requests < 3
    ? new Response('null', { status: 503, headers: { 'retry-after': '0' } })
    : new Response('{"ok":true}')) as typeof fetch;
  assert.deepEqual(await providerJson(fetcher, 'https://provider.example/test'), { ok: true });
  assert.equal(requests, 3);
});
