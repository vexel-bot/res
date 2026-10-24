import test from 'node:test';
import assert from 'node:assert/strict';
import { fromTemplate, makeStep, newFlow, parseSuggestion, templates, validateFlow } from './automationModel';

test('all six templates are valid configurations with a connection, never executions', () => {
  assert.equal(templates.length, 6);
  for (const template of templates) {
    const flow = fromTemplate(template);
    const before = JSON.stringify(flow);
    const log = validateFlow(flow, true);
    assert.equal(log.status, 'valid', template.id);
    assert.equal(log.kind, 'validation');
    assert.equal(flow.isActive, false);
    assert.equal(flow.executionsCount, 0);
    assert.equal(JSON.stringify(flow), before);
    assert.ok(log.durationMs! >= 0);
    assert.ok(log.steps!.every(step => step.durationMs >= 0 && Number.isFinite(Date.parse(step.createdAt))));
  }
});

test('templates create independent flow and step identities', () => {
  const first = fromTemplate(templates[0]);
  const second = fromTemplate(templates[0]);
  assert.notEqual(first.id, second.id);
  assert.ok(first.nodes.every((node, index) => node.id !== second.nodes[index].id));
  first.nodes[0].details = 'changed';
  assert.notEqual(first.nodes[0].details, second.nodes[0].details);
});

test('empty flows cannot be activated', () => {
  const result = validateFlow(newFlow(), false);
  assert.equal(result.status, 'blocked');
  assert.match(result.message, /nome/);
});

test('publication requires a connected account but other templates do not', () => {
  for (const template of templates) {
    const result = validateFlow(fromTemplate(template), false);
    assert.equal(result.status, template.id === 'publish' ? 'blocked' : 'valid');
  }
});

test('a single trigger must be first and at least one action is required', () => {
  const flow = fromTemplate(templates[0]);
  flow.nodes.reverse();
  assert.equal(validateFlow(flow, true).status, 'blocked');
  flow.nodes.reverse();
  flow.nodes.push(makeStep('trigger', 'Duplicate', 'Another event'));
  assert.equal(validateFlow(flow, true).status, 'blocked');
  flow.nodes = [flow.nodes[0], makeStep('condition', 'Check', 'Has content')];
  assert.equal(validateFlow(flow, true).status, 'blocked');
});

test('wait steps reject non-positive and non-finite durations', () => {
  const flow = fromTemplate(templates.find(template => template.id === 'followup')!);
  const wait = flow.nodes.find(node => node.type === 'wait')!;
  for (const value of [0, -1, Infinity, NaN]) {
    wait.minutes = value;
    assert.equal(validateFlow(flow, true).status, 'blocked');
  }
  wait.minutes = 1440;
  assert.equal(validateFlow(flow, true).status, 'valid');
});

const suggestion = () => ({ title: 'Revisar conteúdo', trigger: 'Quando aprovado', isActive: true, executionsCount: 99, nodes: [{ type: 'trigger', label: 'Aprovado', details: 'Quando aprovado' }, { type: 'notify', label: 'Avisar', details: 'Avisar equipe' }] });

test('KLIC suggestions always become new inactive drafts for review', () => {
  const flow = parseSuggestion('```json\n' + JSON.stringify(suggestion()) + '\n```');
  assert.equal(flow.title, 'Revisar conteúdo');
  assert.equal(flow.isActive, false);
  assert.equal(flow.executionsCount, 0);
  assert.equal(validateFlow(flow, false).status, 'valid');
});

test('KLIC rejects prose, incomplete output, unknown steps and misplaced triggers', () => {
  assert.throws(() => parseSuggestion('Aqui está sua sugestão'));
  assert.throws(() => parseSuggestion('{}'));
  const flow = suggestion();
  flow.nodes[1].type = 'execute_code';
  assert.throws(() => parseSuggestion(JSON.stringify(flow)));
  flow.nodes[1].type = 'trigger';
  assert.throws(() => parseSuggestion(JSON.stringify(flow)));
  flow.nodes[1].type = 'condition';
  assert.throws(() => parseSuggestion(JSON.stringify(flow)));
  flow.nodes[1].type = 'notify';
  flow.nodes.reverse();
  assert.throws(() => parseSuggestion(JSON.stringify(flow)));
});

test('KLIC does not silently invent wait durations or accept blank descriptions', () => {
  const flow = suggestion();
  flow.nodes.push({ type: 'wait', label: 'Esperar', details: 'Aguardar' });
  assert.throws(() => parseSuggestion(JSON.stringify(flow)));
  Object.assign(flow.nodes[2], { minutes: 30 });
  assert.equal(parseSuggestion(JSON.stringify(flow)).nodes[2].minutes, 30);
  flow.nodes[2].details = ' ';
  assert.throws(() => parseSuggestion(JSON.stringify(flow)));
});
