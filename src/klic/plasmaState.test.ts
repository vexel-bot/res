import test from 'node:test';
import assert from 'node:assert/strict';
import { plasmaActivity, plasmaCompleted, plasmaEnergy } from './plasmaState';

test('energy is finite and bounded even for invalid input', () => {
  for (const value of [NaN, Infinity, -Infinity, -1]) assert.equal(plasmaEnergy(value), 0);
  assert.equal(plasmaEnergy(2), 1);
  assert.equal(plasmaEnergy(.4), .4);
});
test('typing and response generation do not mask real voice/error states', () => {
  assert.equal(plasmaActivity('idle'), 'idle');
  assert.equal(plasmaActivity('idle', false, true), 'interacting');
  assert.equal(plasmaActivity('processing', false, true), 'processing');
  assert.equal(plasmaActivity('processing', true, true), 'responding');
  for (const state of ['error', 'listening', 'speaking', 'connecting'] as const) assert.equal(plasmaActivity(state, true, true), state);
});
test('completion requires an actual new completed response, not hydration, cancellation or failure', () => {
  assert.equal(plasmaCompleted('responding', 'idle', undefined, 'reply-1'), true);
  assert.equal(plasmaCompleted('responding', 'responding', undefined, 'reply-1'), true);
  assert.equal(plasmaCompleted('idle', 'idle', undefined, 'old-reply'), false);
  assert.equal(plasmaCompleted('processing', 'idle', 'old-reply', 'old-reply'), false);
  assert.equal(plasmaCompleted('processing', 'idle'), false);
  assert.equal(plasmaCompleted('responding', 'error', undefined, 'reply-1'), false);
});
