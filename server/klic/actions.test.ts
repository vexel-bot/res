import test from 'node:test';
import assert from 'node:assert/strict';
import { KlicCore } from './core';
import { KlicMemory } from './store';
import { prepareKlicAction } from './actions';
import type { KlicActor, KlicRequest } from '../../src/klic/contracts';

const actor: KlicActor = {
  workspaceId: 'ws-1', userId: 'usr-master', clientId: 'client-a', accountType: 'company',
  user: { id: 'usr-master', workspaceId: 'ws-1', role: 'master', status: 'active', name: 'Master', email: 'master@example.test', avatar: '', lastAccess: '', createdAt: '', modules: ['ai-chat', 'workspace', 'calendar'] },
};
const request: KlicRequest = { workspaceId: 'ws-1', clientId: 'client-a', source: 'ai-chat', message: 'prepare' };

test('reversible KLIC actions are normalized, audited and idempotent inside the exact scope', () => {
  const core = new KlicCore(new KlicMemory(null));
  const first = prepareKlicAction(core, actor, request, 'calendar.draft.prepare', 'message-123-calendar', {
    title: '  Próxima publicação  ', copy: 'Legenda', scheduledAt: '2099-01-01T22:00:00.000Z', platform: 'instagram', format: 'post',
  });
  const repeated = prepareKlicAction(core, actor, request, 'calendar.draft.prepare', 'message-123-calendar', {
    title: 'Outro título', copy: 'Não deve sobrescrever', scheduledAt: '2099-01-02T22:00:00.000Z', platform: 'instagram', format: 'post',
  });
  assert.equal(first.id, repeated.id);
  assert.equal(first.executed, false);
  assert.equal(first.status, 'prepared');
  assert.equal(first.resource.title, 'Próxima publicação');
  assert.equal(first.resource.status, 'draft');
  assert.equal(repeated.resource.title, 'Próxima publicação');
  assert.ok(core.memory.traces(actor).some(trace => trace.tool === 'calendar.draft.prepare'));
  assert.equal(core.memory.preparedAction({ ...actor, clientId: 'client-b' }, 'message-123-calendar'), null);
});

test('external and critical actions cannot be authorized by a frontend confirmation flag', () => {
  const core = new KlicCore(new KlicMemory(null));
  assert.throws(() => prepareKlicAction(core, actor, request, 'publication.publish.request', 'message-123-publish', { title: 'Post', confirmed: true }), /CONFIRMATION_REQUIRED/);
  assert.throws(() => prepareKlicAction(core, actor, request, 'connections.disconnect.request', 'message-123-disconnect', { title: 'Conta', confirmed: true }), /CONFIRMATION_REQUIRED/);
  assert.equal(core.memory.preparedAction(actor, 'message-123-publish'), null);
});

test('prepared actions enforce permissions, inputs and future scheduling', () => {
  const core = new KlicCore(new KlicMemory(null));
  const limited: KlicActor = { ...actor, userId: 'analyst', user: { ...actor.user, id: 'analyst', role: 'analyst', permissions: ['analytics.read'], scope: { allClients: false, clientIds: ['client-a'], allSocialAccounts: false, socialAccountIds: [], allProjects: false, projectIds: [], resourceIds: [] } } };
  assert.throws(() => prepareKlicAction(core, limited, { ...request }, 'content.draft.prepare', 'message-123-content', { title: 'Brief', destination: 'create-copy' }), /PERMISSION_DENIED/);
  assert.throws(() => prepareKlicAction(core, actor, request, 'calendar.draft.prepare', 'message-123-past', { title: 'Post', scheduledAt: '2020-01-01T00:00:00.000Z' }), /SCHEDULE_INVALID/);
  assert.throws(() => prepareKlicAction(core, actor, request, 'content.draft.prepare', 'message-123-invalid', { title: 'Brief', destination: 'external-app' }), /ACTION_INPUT_INVALID/);
});
