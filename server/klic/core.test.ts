import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { KlicMemory } from './store';
import { KlicCore, KlicEventBus } from './core';
import { localContext, checkRequest } from './context';
import { recommend } from './recommendations';
import { createKlicRuntime } from './router';
import { createGovernanceRouter } from '../governance';
import { registerAdapters } from './adapters';
import type { KlicActor, KlicRequest, KlicSource } from '../../src/klic/contracts';
import { analyticsContext } from '../../src/klic/analyticsContext';
import type { AnalyticsPoint } from '../../src/analytics/analyticsModel';

const actor: KlicActor = { workspaceId: 'ws-1', userId: 'usr-master', clientId: null, accountType: 'company', user: { id: 'usr-master', workspaceId: 'ws-1', role: 'master', status: 'active', name: 'Test', email: 'test@example.test', avatar: '', lastAccess: '', modules: ['ai-chat', 'analytics', 'calendar'], createdAt: '' } };
const request = (records: KlicRequest['context']['records'] = {}): KlicRequest => ({ workspaceId: actor.workspaceId, clientId: null, source: 'ai-chat', context: { workspaceId: actor.workspaceId, userId: actor.userId, clientId: null, source: 'browser-local', records } });

test('KLIC context rejects mixed users, workspaces and clients; allowlists scalars and excludes media', () => {
  const valid = request({ brand: [{ workspaceId: 'ws-1', name: 'Brand', token: 'SECRET', arbitrary: { secret: 1 } }] });
  assert.equal(localContext(actor, valid.context).brand![0].name, 'Brand');
  assert.equal(JSON.stringify(localContext(actor, valid.context)).includes('SECRET'), false);
  for (const changed of [{ workspaceId: 'ws-personal' }, { userId: 'other' }, { clientId: 'other-client' }]) assert.throws(() => localContext(actor, { ...valid.context!, ...changed }), /SCOPE/);
  assert.throws(() => localContext(actor, request({ calendar: [{ workspaceId: 'ws-personal', title: 'Other' }] }).context), /SCOPE/);
  assert.throws(() => localContext(actor, request({ library: [{ workspaceId: 'ws-1', type: 'image' }] }).context), /MEDIA/);
  assert.throws(() => checkRequest(actor, { ...request(), source: 'create-image' }), /EXCLUDED/);
  assert.throws(() => checkRequest(actor, { ...request(), source: 'create-video' }), /EXCLUDED/);
  const collaborator: KlicActor = { ...actor, userId: 'limited', user: { ...actor.user, id: 'limited', role: 'collaborator', modules: ['ai-chat'] } };
  assert.throws(() => checkRequest(collaborator, { ...request(), source: 'analytics' }), /PERMISSION/);
  assert.deepEqual(localContext(collaborator, { ...valid.context!, userId: 'limited' }), {});
  assert.throws(() => checkRequest({ ...collaborator, clientId: 'a' }, { ...request(), clientId: 'a' }), /CLIENT_SCOPE_DENIED/);
});

test('KLIC tools deny external actions and unavailable adapters cannot fake data', async () => {
  const core = new KlicCore(new KlicMemory(null));
  let ran = false;
  core.register({ id: 'external', domain: 'calendar', effect: 'external', run: () => { ran = true; return { domain: 'calendar', status: 'available', records: [], provenance: 'service' }; } });
  core.register({ id: 'broken', domain: 'analytics', effect: 'read', run: () => { throw new Error('SECRET_PROVIDER_DETAILS'); } });
  const task = core.task(actor, request());
  assert.equal((await core.run(task, 'external', { confirmed: true })).status, 'denied');
  assert.equal(ran, false);
  assert.equal((await core.run(task, 'broken')).status, 'unavailable');
  assert.equal(JSON.stringify(core.memory.traces(actor)).includes('SECRET'), false);
  assert.equal(core.memory.traces(actor).length, 2);
  assert.throws(() => core.register({ id: 'external', domain: 'calendar', effect: 'read', run: () => { throw new Error(); } }), /DUPLICATE/);
});

test('KLIC memory survives restart and cannot leak to another user/client/workspace', () => {
  const folder = mkdtempSync(path.join(tmpdir(), 'clicko-core-test-'));
  try {
    const filename = path.join(folder, 'core.json');
    const first = new KlicMemory(filename);
    first.remember(actor, 'tone', 'Concise');
    const goal = first.setGoal(actor, { title: 'Aumentar alcance', metric: 'reach', target: '10%' });
    const restored = new KlicMemory(filename);
    assert.equal(restored.preferences(actor)[0].value, 'Concise');
    assert.equal(restored.goals(actor)[0].title, 'Aumentar alcance');
    assert.equal(restored.updateGoal(actor, goal.id, 'completed')?.status, 'completed');
    for (const scope of [{ ...actor, workspaceId: 'other' }, { ...actor, userId: 'other' }, { ...actor, clientId: 'other' }]) {
      assert.equal(restored.preferences(scope).length, 0);
      assert.equal(restored.goals(scope).length, 0);
    }
    restored.forget(actor, 'tone');
    assert.equal(new KlicMemory(filename).preferences(actor).length, 0);
    assert.throws(() => new KlicMemory(path.resolve('public/core.json')), /PRIVATE/);
  } finally { rmSync(folder, { recursive: true, force: true }); }
});

test('KLIC comparison rejects gaps/zero baselines and states correlation without causality', () => {
  const point = (date: string, reach: number | null) => ({ date, reach } as AnalyticsPoint);
  assert.deepEqual(analyticsContext('ws-1', [point('2026-01-03', 10), point('2026-01-04', null)], [point('2026-01-01', 20), point('2026-01-02', 20)], '2026-01-03', '2026-01-04'), []);
  const records = analyticsContext('ws-1', [point('2026-01-03', 10), point('2026-01-04', 10)], [point('2026-01-01', 20), point('2026-01-02', 20)], '2026-01-03', '2026-01-04');
  const sources: KlicSource[] = [{ domain: 'analytics', status: 'available', provenance: 'browser-local', records }, { domain: 'calendar', status: 'available', provenance: 'browser-local', records: [{ workspaceId: 'ws-1', status: 'published', scheduledAt: '2026-01-01' }] }];
  assert.match(recommend(sources)[0].text, /50%/);
  assert.match(recommend(sources)[0].text, /não uma causa comprovada/);
  sources[0].records = [{ ...records[0], previous: 0 }];
  assert.equal(recommend(sources).length, 0);
});

test('KLIC event bus isolates subscriber failure and deduplicates successful events by full scope', async () => {
  const bus = new KlicEventBus();
  let successful = 0;
  bus.subscribe(async () => { throw new Error('offline'); });
  bus.subscribe(async () => { successful++; });
  const event = { id: 'e1', type: 'calendar.changed', actor, request: request() };
  assert.equal(await bus.publish(event), false);
  assert.equal(successful, 1);
  const core = new KlicCore(new KlicMemory(null));
  core.register({ id: 'brand.read', domain: 'brand', effect: 'read', run: () => ({ domain: 'brand', status: 'empty', provenance: 'service', records: [] }) });
  assert.equal((await core.event(event)).duplicate, false);
  assert.equal((await core.event(event)).duplicate, true);
  assert.equal(core.memory.hasEvent({ ...actor, clientId: 'other' }, 'e1'), false);
  assert.ok(core.latest(actor, request()));
  assert.equal(core.latest({ ...actor, userId: 'another' }, { ...request(), context: undefined }), null);
  const report = core.latest(actor, request())!;
  report.insight = 'modified by consumer';
  assert.notEqual(core.latest(actor, request())!.insight, report.insight);
  const revoked = { ...actor, user: { ...actor.user, role: 'collaborator' as const, modules: ['ai-chat' as const] } };
  assert.equal(core.latest(revoked, { ...request(), context: undefined }), null);
});

test('KLIC authenticated HTTP boundary, explicit provider failure, event observer and read-only automation proposals', async t => {
  const app = express(); app.use(express.json());
  const memory = new KlicMemory(null);
  let providerCalls = 0;
  let providerPrompt = '';
  const runtime = createKlicRuntime({ memory, generate: async (_system, message) => {
    providerCalls++; providerPrompt = message;
    if (message.includes('RISK_ACTION_TEST')) return 'Análise concluída.';
    if (message.includes('TEST_FLOW')) return JSON.stringify({ title: 'Review', trigger: 'Scheduled', nodes: [{ type: 'trigger', label: 'When', details: 'Scheduled' }, { type: 'notify', label: 'Review', details: 'Review queue' }] });
    throw new Error('PROVIDER_SECRET');
  } });
  app.use(runtime.observe);
  app.use('/api/governance', createGovernanceRouter({ dataFile: null }));
  app.use('/api/klic', runtime.router);
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(() => new Promise<void>(resolve => server.close(() => resolve())));
  const base = 'http://127.0.0.1:' + (server.address() as { port: number }).port;
  const headers = { 'Content-Type': 'application/json', 'x-workspace-id': actor.workspaceId, 'x-user-id': actor.userId };
  const call = (route: string, body: unknown, custom = headers) => fetch(base + '/api/klic/' + route, { method: 'POST', headers: custom, body: JSON.stringify(body) });
  assert.equal((await call('chat', { ...request(), message: 'hello' }, { 'Content-Type': 'application/json' } as typeof headers)).status, 401);
  assert.equal((await call('chat', { ...request(), workspaceId: 'ws-personal', message: 'hello' })).status, 403);
  assert.equal((await call('chat', { ...request(), source: 'create-video', message: 'hello' })).status, 403);
  assert.equal(providerCalls, 0);
  const response = await call('chat', { ...request({ brand: [{ workspaceId: 'ws-1', name: 'Only this brand', accessToken: 'SECRET' }] }), message: 'Hello' });
  const result = await response.json();
  assert.equal(response.status, 503); assert.equal(result.reply, undefined);
  assert.equal(result.code, 'KLIC_PROVIDER_UNAVAILABLE'); assert.match(result.error, /não respondeu/);
  assert.equal(JSON.stringify(result).includes('PROVIDER_SECRET'), false);
  assert.equal(providerPrompt.includes('accessToken'), false);
  assert.equal(JSON.stringify(memory.traces(actor)).includes('PROVIDER_SECRET'), false);
  const riskActionResponse = await call('chat', { ...request(), message: 'RISK_ACTION_TEST: crie duas legendas' });
  const riskAction = await riskActionResponse.json();
  assert.equal(riskActionResponse.status, 200);
  assert.equal(riskAction.actionSuggestions.find((item: any) => item.actionId === 'content.draft.prepare')?.risk, 'reversible');
  assert.equal((await call('memory', { ...request(), key: 'tone', value: 'Direct', consent: false })).status, 400);
  assert.equal((await call('memory', { ...request(), key: 'tone', value: 'Direct', consent: true })).status, 200);
  assert.equal((await call('goals', { ...request(), title: 'Aumentar alcance', confirmedByUser: false })).status, 400);
  const goalResponse = await call('goals', { ...request(), title: 'Aumentar alcance', metric: 'reach', target: '10%', confirmedByUser: true });
  assert.equal(goalResponse.status, 200);
  const goals = await (await fetch(base + '/api/klic/goals?workspaceId=ws-1', { headers })).json();
  assert.equal(goals[0].title, 'Aumentar alcance');
  const planned = await (await call('orchestrate', { ...request(), message: 'Crie duas legendas' })).json();
  assert.deepEqual(planned.stages.map((stage: any) => stage.stage), ['understand', 'analyze', 'create', 'organize', 'execute', 'measure', 'learn']);
  assert.equal(planned.actions[0].actionId, 'content.draft.prepare');
  const preparedBody = { ...request(), actionId: 'content.draft.prepare', idempotencyKey: 'http-content-123', input: { title: 'Duas legendas', brief: 'Versões A e B', destination: 'create-copy' } };
  const prepared = await (await call('actions/prepare', preparedBody)).json();
  const repeated = await (await call('actions/prepare', preparedBody)).json();
  assert.equal(prepared.id, repeated.id); assert.equal(prepared.executed, false); assert.equal(prepared.resource.status, 'draft');
  assert.equal((await call('actions/prepare', { ...request(), actionId: 'publication.publish.request', idempotencyKey: 'http-publish-123', input: { title: 'Agora', confirmed: true } })).status, 409);
  const flowResponse = await call('automation-plan', { ...request(), source: 'automations', message: 'TEST_FLOW' });
  const flow = await flowResponse.json();
  assert.equal(flowResponse.status, 200);
  assert.equal(flow.executed, false); assert.equal(flow.flow.isActive, false); assert.equal(flow.requiresReview, true);
  const external = await (await call('tools', { ...request(), tool: 'automations.start', input: { confirmed: true } })).json();
  assert.equal(external.status, 'denied');
  const approval = await fetch(base + '/api/governance/approvals', { method: 'POST', headers, body: JSON.stringify({ contentId: 'core-test', title: 'Review test', copy: 'Test', platform: 'instagram', format: 'post' }) });
  assert.equal(approval.status, 201);
  // The event subscriber runs asynchronously after the original service commits.
  await new Promise(resolve => setImmediate(resolve));
  assert.ok(memory.traces(actor).some(trace => trace.tool === 'event.approvals.changed'));
  const traces = await (await fetch(base + '/api/klic/traces?workspaceId=ws-1', { headers })).json();
  assert.ok(traces.some((trace: any) => trace.tool === 'intelligence.respond'));
  const client = await (await fetch(base + '/api/klic/traces?workspaceId=ws-1&clientId=another-client', { headers })).json();
  assert.deepEqual(client, []);
  const core = new KlicCore(new KlicMemory(null)); registerAdapters(core);
  const isolated = await core.run(core.task({ ...actor, clientId: 'client-a' }, { ...request(), clientId: 'client-a', context: undefined }), 'approvals.read');
  assert.equal(isolated.status, 'unavailable'); assert.equal(isolated.records.length, 0);
});
