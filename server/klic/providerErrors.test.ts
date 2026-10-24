import assert from 'node:assert/strict';
import test from 'node:test';
import { providerFailure, safeGoogleFailure } from './providerErrors';

test('malformed upstream errors cannot break diagnostics or expose arbitrary payloads', () => {
  const failures: unknown[] = [null, undefined, false, 42, 'PRIVATE', Symbol('PRIVATE'),
    { status: Symbol('PRIVATE'), code: { private: 'SECRET' }, cause: { code: Symbol('PRIVATE') } },
    ...['null', '[]', '[null]', '42', '"PRIVATE"', '{"error":null}'].map(message => ({ message })),
    { error: { status: 'PRIVATE', details: [null, 42, 'SECRET', { reason: 'PRIVATE' }] } },
  ];
  for (const failure of failures) {
    const diagnostic = safeGoogleFailure(failure);
    assert.deepEqual(diagnostic, { upstreamStatus: undefined, upstreamCode: undefined, upstreamReason: undefined });
    assert.equal(providerFailure(failure).code, 'KLIC_PROVIDER_UNAVAILABLE');
    assert.doesNotMatch(JSON.stringify({ diagnostic, failure: providerFailure(failure) }), /SECRET|PRIVATE/);
  }
});

test('typed diagnostics keep allowlisted provider reasons and real HTTP statuses', () => {
  assert.deepEqual(safeGoogleFailure({ error: {
    code: '403', status: 'PERMISSION_DENIED', details: [null, { reason: 'SERVICE_DISABLED', token: 'PRIVATE' }],
  } }), { upstreamStatus: 403, upstreamCode: 'PERMISSION_DENIED', upstreamReason: 'SERVICE_DISABLED' });
  assert.equal(providerFailure({ cause: { code: 'ECONNRESET' } }).code, 'KLIC_PROVIDER_NETWORK');
});
