import test from 'node:test';
import assert from 'node:assert/strict';
import { fromJourney, journeyGoals } from './journeyCatalog';
import { validateFlow } from './automationModel';

test('Clicko journeys cover the requested goals with complete decision metadata', () => {
  assert.equal(journeyGoals.length, 11);
  assert.equal(new Set(journeyGoals.map(goal => goal.id)).size, journeyGoals.length);
  for (const goal of journeyGoals) {
    for (const field of ['objective', 'signal', 'condition', 'action', 'responsible', 'deadline', 'expectedResult', 'indicator'] as const) assert.ok(goal[field].trim(), `${goal.id}: ${field}`);
    const flow = fromJourney(goal);
    assert.equal(flow.isActive, false);
    assert.equal(flow.executionsCount, 0);
    assert.equal(flow.requiresOperation, goal.requiresOperation);
    assert.equal(validateFlow(flow, false).status, 'valid', goal.id);
  }
  assert.equal(journeyGoals.find(goal => goal.id === 'operation-signal')?.requiresOperation, false);
  assert.equal(journeyGoals.find(goal => goal.id === 'cost-approval')?.requiresOperation, true);
});
