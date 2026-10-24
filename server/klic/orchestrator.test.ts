import test from 'node:test';
import assert from 'node:assert/strict';
import { KlicCore } from './core';
import { KlicMemory } from './store';
import { inferKlicIntent, orchestrateKlic } from './orchestrator';
import type { KlicActor, KlicDomain, KlicRequest } from '../../src/klic/contracts';

const actor: KlicActor = {
  workspaceId: 'ws-1', userId: 'usr-master', clientId: null, accountType: 'company',
  user: {
    id: 'usr-master', workspaceId: 'ws-1', role: 'master', status: 'active', name: 'Master', email: 'master@example.test', avatar: '', lastAccess: '', createdAt: '',
    modules: ['dashboard', 'ai-chat', 'workspace', 'strategy', 'calendar', 'library', 'analytics', 'connected-accounts', 'automations'],
  },
};

function request(message: string, source: KlicRequest['source'] = 'ai-chat'): KlicRequest {
  return { workspaceId: actor.workspaceId, clientId: null, source, message };
}

function coreWith(...domains: KlicDomain[]) {
  const core = new KlicCore(new KlicMemory(null));
  for (const domain of domains) core.register({ id: `${domain}.read`, domain, effect: 'read', run: () => ({ domain, provenance: 'service', status: 'empty', records: [] }) });
  return core;
}

test('KLIC classifies operational intent without treating every request as execution', () => {
  assert.equal(inferKlicIntent('Por que o alcance caiu este mês?'), 'measurement');
  assert.equal(inferKlicIntent('Prepare duas legendas para a próxima campanha'), 'organization');
  assert.equal(inferKlicIntent('Crie duas variações da legenda'), 'creation');
  assert.equal(inferKlicIntent('Publique agora no Instagram'), 'execution');
  assert.equal(inferKlicIntent('Qual é o tom de voz desta marca?'), 'learning');
  assert.equal(inferKlicIntent('O que temos para amanhã?'), 'question');
});

test('seven-stage plan uses verified page context, scoped goals and confirmation for critical actions', async () => {
  const core = coreWith('brand', 'connections');
  core.memory.setGoal(actor, { title: 'Manter frequência semanal', metric: 'publicações por semana', target: '4' });
  const body = request('Desconectar esta conta social', 'connected-accounts');
  const pageContext = { module: 'connected-accounts' as const, workspaceId: 'ws-1', clientId: null, details: { view: 'contas conectadas' } };
  const { plan } = await orchestrateKlic(core, actor, body, pageContext);
  assert.deepEqual(plan.stages.map(stage => stage.stage), ['understand', 'analyze', 'create', 'organize', 'execute', 'measure', 'learn']);
  assert.equal(plan.page?.details.view, 'contas conectadas');
  assert.equal(plan.intent, 'execution');
  assert.equal(plan.status, 'awaiting_confirmation');
  assert.equal(plan.actions[0].actionId, 'connections.disconnect.request');
  assert.equal(plan.actions[0].risk, 'critical');
  assert.equal(plan.actions[0].requiresConfirmation, true);
  assert.equal(plan.stages.find(stage => stage.stage === 'execute')?.status, 'awaiting_confirmation');
  assert.deepEqual(plan.goals.map(goal => goal.title), ['Manter frequência semanal']);
  assert.ok(core.memory.traces(actor).some(trace => trace.tool === 'orchestrator.execute'));
  assert.equal(core.memory.goals({ ...actor, userId: 'other' }).length, 0);
});

test('reversible creation is planned while read-only analysis can complete without pretending an action ran', async () => {
  const creationCore = coreWith('brand', 'strategy');
  const created = (await orchestrateKlic(creationCore, actor, request('Crie duas variações da legenda'))).plan;
  assert.equal(created.status, 'planned');
  assert.equal(created.actions[0].risk, 'reversible');
  assert.equal(created.actions[0].requiresConfirmation, false);
  assert.equal(created.stages.find(stage => stage.stage === 'create')?.status, 'ready');

  const analysisCore = coreWith('brand', 'analytics', 'calendar');
  const analyzed = (await orchestrateKlic(analysisCore, actor, request('Compare o desempenho deste mês', 'analytics'))).plan;
  assert.equal(analyzed.status, 'completed');
  assert.equal(analyzed.stages.find(stage => stage.stage === 'measure')?.status, 'ready');
  assert.equal(analyzed.actions.some(action => action.risk === 'external' || action.risk === 'critical'), false);
});

test('multi-client requests switch to service-only workspace scope and require a reviewed bulk plan', async () => {
  const memory = new KlicMemory(null);
  const core = new KlicCore(memory);
  let localRecordsSeen = -1;
  core.register({ id: 'brand.read', domain: 'brand', effect: 'read', run: ({ local }) => { localRecordsSeen = local.brand?.length || 0; return { domain: 'brand', provenance: 'service', status: 'empty', records: [] }; } });
  core.register({ id: 'calendar.read', domain: 'calendar', effect: 'read', run: ({ actor: scoped }) => ({ domain: 'calendar', provenance: 'service', status: 'available', records: [{ workspaceId: scoped.workspaceId, clientId: scoped.clientId, id: 'scheduled-1' }] }) });
  core.register({ id: 'clients.read', domain: 'clients', effect: 'read', run: ({ actor: scoped }) => ({ domain: 'clients', provenance: 'service', status: 'empty', records: [], reason: scoped.clientId ? 'client' : 'workspace' }) });
  const clientActor = { ...actor, clientId: 'client-a' };
  const body: KlicRequest = {
    workspaceId: 'ws-1', clientId: 'client-a', source: 'ai-chat', message: 'Prepare o calendário da próxima semana para todos os meus clientes',
    context: { workspaceId: 'ws-1', userId: actor.userId, clientId: 'client-a', source: 'browser-local', records: { brand: [{ workspaceId: 'ws-1', clientId: 'client-a', name: 'Browser value' }] } },
  };
  const { plan } = await orchestrateKlic(core, clientActor, body, { module: 'ai-chat', workspaceId: 'ws-1', clientId: 'client-a', details: { selected: { kind: 'client', id: 'client-a' } } });
  assert.equal(plan.scopeMode, 'workspace');
  assert.equal(plan.page, null);
  assert.equal(localRecordsSeen, 0);
  assert.equal(plan.actions[0].actionId, 'bulk.plan.review');
  assert.equal(plan.actions[0].requiresConfirmation, true);
  assert.equal(memory.traces({ ...clientActor, clientId: null }).some(trace => trace.tool === 'orchestrator.execute'), true);
  assert.equal(memory.traces(clientActor).some(trace => trace.tool === 'orchestrator.execute'), false);
});
