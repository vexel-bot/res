import test from 'node:test';
import assert from 'node:assert/strict';
import { stableStudioContext } from './stableStudioContext';

test('lazy imports and HMR share the Studio context without replacing the provider identity', () => {
  const cache = {};
  const first = stableStudioContext(cache, () => ({ id: 'context' }));
  const second = stableStudioContext(cache, () => { throw new Error('Must reuse context'); });
  assert.equal(first, second);
});
test('without HMR the context stays module-local; no global production cache is created', () => {
  assert.notEqual(stableStudioContext(undefined, () => ({})), stableStudioContext(undefined, () => ({})));
});
