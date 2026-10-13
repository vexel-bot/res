import test from 'node:test';
import assert from 'node:assert/strict';
import { observePlasma } from './plasmaVisibility';

test('all instances share visibility monitoring and release it on final unmount', () => {
  const previousDocument = Object.getOwnPropertyDescriptor(globalThis, 'document');
  const previousObserver = Object.getOwnPropertyDescriptor(globalThis, 'IntersectionObserver');
  let visibility: (() => void) | undefined;
  let notifications: (entries: Array<{ target: object; isIntersecting: boolean }>) => void = () => {};
  let created = 0, disconnected = 0, removed = 0, unobserved = 0;
  const page = { hidden: false, addEventListener: (_: string, callback: () => void) => { visibility = callback; }, removeEventListener: () => { removed++; } };
  class Observer {
    constructor(callback: typeof notifications) { created++; notifications = callback; }
    observe() {} unobserve() { unobserved++; } disconnect() { disconnected++; }
  }
  Object.defineProperty(globalThis, 'document', { configurable: true, value: page });
  Object.defineProperty(globalThis, 'IntersectionObserver', { configurable: true, value: Observer });
  const first = {} as HTMLElement, second = {} as HTMLElement;
  const firstStates: boolean[] = [], secondStates: boolean[] = [];
  const stopFirst = observePlasma(first, state => firstStates.push(state));
  const stopSecond = observePlasma(second, state => secondStates.push(state));
  try {
    assert.equal(created, 1);
    assert.equal(firstStates.at(-1), false);
    notifications([{ target: first, isIntersecting: true }, { target: second, isIntersecting: false }]);
    assert.equal(firstStates.at(-1), true);
    assert.equal(secondStates.at(-1), false);
    page.hidden = true; visibility?.();
    assert.equal(firstStates.at(-1), false);
    page.hidden = false; visibility?.();
    assert.equal(firstStates.at(-1), true);
    stopFirst(); assert.equal(disconnected, 0);
    stopSecond(); assert.equal(disconnected, 1);
    assert.equal(removed, 1); assert.equal(unobserved, 2);
  } finally {
    if (previousDocument) Object.defineProperty(globalThis, 'document', previousDocument);
    else Reflect.deleteProperty(globalThis, 'document');
    if (previousObserver) Object.defineProperty(globalThis, 'IntersectionObserver', previousObserver);
    else Reflect.deleteProperty(globalThis, 'IntersectionObserver');
  }
});
