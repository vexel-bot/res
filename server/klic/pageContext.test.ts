import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import express from 'express';
import type { KlicActor, KlicSource } from '../../src/klic/contracts';
import { checkedPageContext } from './pageContext';
import { domainsFor } from './context';
import { createKlicRuntime } from './router';
import { ConversationStore } from './conversations';
import { KlicMemory } from './store';
import { createGovernanceRouter } from '../governance';

const actor: KlicActor = {
  workspaceId: 'ws-1', userId: 'user-1', clientId: 'client-1', accountType: 'company',
  user: { id: 'user-1', workspaceId: 'ws-1', role: 'master', status: 'active', name: 'Pedro', email: 'pedro@example.test', avatar: '', lastAccess: '', modules: ['ai-chat', 'calendar'], createdAt: '' },
};
const page = { module: 'calendar', workspaceId: 'ws-1', clientId: 'client-1', details: { view: 'Agenda', period: '2026-10-04 a 2026-10-10', filters: { status: 'scheduled' }, selected: { kind: 'publicacao', id: 'post-1' } } };
const sources: KlicSource[] = [{ domain: 'calendar', provenance: 'service', status: 'available', records: [{ workspaceId: 'ws-1', clientId: 'client-1', id: 'post-1' }] }];

test('page context accepts only a verified selection in the current scope', () => {
  assert.equal(checkedPageContext(actor, 'calendar', page, sources)?.details.selected?.id, 'post-1');
  assert.equal(checkedPageContext(actor, 'calendar', page, [])?.details.selected, undefined);
  assert.equal(checkedPageContext(actor, 'calendar', { ...page, details: { ...page.details, selected: { kind: 'publicacao', id: 'private-post' } } }, sources)?.details.selected, undefined);
});

test('page context rejects cross-workspace, cross-client and source mismatches', () => {
  assert.throws(() => checkedPageContext(actor, 'calendar', { ...page, workspaceId: 'ws-2' }, sources));
  assert.throws(() => checkedPageContext(actor, 'calendar', { ...page, clientId: 'client-2' }, sources));
  assert.throws(() => checkedPageContext(actor, 'analytics', page, sources));
});

test('current module selects relevant authorized evidence without restricting other questions', () => {
  assert.ok(domainsFor('O que está programado?', 'calendar').includes('calendar'));
  assert.ok(domainsFor('E o desempenho?', 'calendar').includes('analytics'));
  assert.ok(domainsFor('Como está o calendário?', 'analytics').includes('calendar'));
});

test('conversation receives fresh page metadata as internal context across navigation', async t => {
  const folder = mkdtempSync(path.join(tmpdir(), 'clicko-page-context-'));
  const prompts: Array<Record<string, any>> = [];
  const runtime = createKlicRuntime({ memory: new KlicMemory(null), conversations: new ConversationStore(folder), conversationProvider: {
    async *stream(_system, prompt) { prompts.push(JSON.parse(prompt)); yield 'Resposta contextual'; },
    async transcribe() { return ''; },
  } });
  const app = express(); app.use(express.json());
  app.use('/api/governance', createGovernanceRouter({ dataFile: null }));
  app.use('/api/klic', runtime.router);
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(async () => {
    await new Promise<void>(resolve => server.close(() => resolve()));
    if (path.dirname(folder) === path.resolve(tmpdir()) && path.basename(folder).startsWith('clicko-page-context-')) rmSync(folder, { recursive: true, force: true });
  });
  const base = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  const post = (route: string, data: object) => fetch(`${base}/api/klic/conversations/${route}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master' },
    body: JSON.stringify({ workspaceId: 'ws-1', clientId: null, ...data }),
  });
  const created = await (await post('create', { source: 'ai-chat' })).json() as { id: string };
  for (const module of ['calendar', 'analytics'] as const) {
    const response = await post('send', { source: module, conversationId: created.id, requestId: randomUUID(), message: 'O que devo fazer agora?',
      context: { workspaceId: 'ws-1', userId: 'usr-master', clientId: null, source: 'browser-local', records: {} },
      pageContext: { module, workspaceId: 'ws-1', clientId: null, details: { view: module === 'calendar' ? 'Agenda' : 'Visão geral' } },
    });
    assert.equal(response.status, 200);
    assert.match(await response.text(), /"type":"done"/);
  }
  assert.equal(prompts[0].interfaceContext.module, 'calendar');
  assert.equal(prompts[0].interfaceContext.details.view, 'Agenda');
  assert.equal(prompts[1].interfaceContext.module, 'analytics');
  assert.equal(prompts[1].interfaceContext.details.view, 'Visão geral');
  assert.ok(prompts[0].operationalSources.some((source: { domain: string }) => source.domain === 'calendar'));
  assert.ok(prompts[1].operationalSources.some((source: { domain: string }) => source.domain === 'analytics'));
});
