import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { createGovernanceRouter } from './governance';
import { createIntegrationsRouter } from './integrations';
import { createKlicRuntime } from './klic/router';
import { KlicMemory } from './klic/store';

// A separate in-process instance: never changes the user's running server or accounts.
test('governance API regression audit', async t => {
  const app = express();
  app.use(express.json());
  app.use('/api/governance', createGovernanceRouter({ dataFile: null }));
  app.use('/api/integrations', createIntegrationsRouter());
  app.use('/api/klic', createKlicRuntime({ memory: new KlicMemory(null) }).router);
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(() => new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve())));
  const address = server.address() as { port: number };
  const base = `http://127.0.0.1:${address.port}/api/governance`;
  const integrations = `http://127.0.0.1:${address.port}/api/integrations`;
  const klic = `http://127.0.0.1:${address.port}/api/klic`;
  const company = { 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master' };
  const personal = { 'x-workspace-id': 'ws-personal', 'x-user-id': 'usr-master-personal' };
  const call = (path: string, method = 'GET', body?: unknown, headers: Record<string,string> = company) => fetch(base + path, { method, headers: { ...headers, 'Content-Type': 'application/json' }, ...(body ? { body: JSON.stringify(body) } : {}) });
  await t.test('social connections require membership, while OAuth callback validates its own state', async () => {
    assert.equal((await fetch(integrations + '/instagram/status')).status, 401);
    assert.equal((await fetch(integrations + '/instagram/disconnect', { method: 'POST' })).status, 401);
    assert.equal((await fetch(integrations + '/oauth/callback?state=invalid')).status, 400);
    assert.equal((await fetch(integrations + '/instagram/status', { headers: company })).status, 200);
    assert.equal((await fetch(integrations + '/instagram/sync', { method: 'POST', headers: company })).status, 401);
  });

  await t.test('missing or cross-workspace identity cannot access data', async () => {
    assert.equal((await call('/session', 'GET', undefined, {})).status, 401);
    assert.equal((await call('/session', 'GET', undefined, { ...company, 'x-workspace-id': 'ws-personal' })).status, 401);
    const first = await (await call('/session')).json();
    const second = await (await call('/session', 'GET', undefined, personal)).json();
    assert.equal(first.currentUser.workspaceId, 'ws-1');
    assert.equal(second.currentUser.workspaceId, 'ws-personal');
  });
  await t.test('registration cannot add an administrator without an authenticated browser session', async () => {
    const response = await call('/workspaces/register', 'POST', { workspaceId: 'ws-1', userId: 'usr-intruder', name: 'Not authorized', type: 'company' }, {});
    assert.equal(response.status, 401);
    assert.equal((await call('/session', 'GET', undefined, { ...company, 'x-user-id': 'usr-intruder' })).status, 401);
  });
  await t.test('client registration is free, portal access is limited, and operational access requires a confirmed licence', async () => {
    const clientId = 'client-operation-audit';
    const registered = await call('/clients/register', 'POST', { id: clientId, name: 'Operação Auditada' });
    assert.equal(registered.status, 201);
    assert.equal((await registered.json()).operationState, 'registered');
    const denied = await call(`/clients/${clientId}/operation-access`);
    assert.equal(denied.status, 402);
    assert.equal((await denied.json()).code, 'CLIENT_OPERATION_REQUIRED');
    assert.equal((await call('/subscription/add-ons', 'POST', { resource: 'clients', quantity: 10 })).status, 409);
    assert.equal((await call(`/clients/${clientId}/operation-intents`, 'POST', { kind: 'costs' })).status, 200);
    assert.equal((await call(`/clients/${clientId}/operation-intents`, 'POST', { kind: 'costs' })).status, 200);
    assert.equal((await call('/clients', 'GET', undefined, personal)).status, 200);
    assert.equal((await (await call('/clients', 'GET', undefined, personal)).json()).some((item: { id: string }) => item.id === clientId), false);
    const invite = await call(`/clients/${clientId}/invite`, 'POST', { email: 'portal@example.test', kind: 'portal' });
    assert.equal(invite.status, 200);
    const invitation = await invite.json();
    assert.equal(invitation.client.operationState, 'invited');
    assert.equal(invitation.deliveryConfigured, false);
    const portalToken = new URLSearchParams(new URL(invitation.inviteUrl).hash.slice(1)).get('token')!;
    const portalHeaders = { 'Content-Type': 'application/json', 'x-client-portal-token': portalToken };
    assert.equal((await fetch(base + '/client-portal')).status, 401);
    assert.equal((await fetch(base + '/client-portal', { headers: portalHeaders })).status, 200);
    assert.equal((await call(`/clients/${clientId}/portal-request`, 'POST', { title: 'Revisar documento', detail: 'Confirme a proposta.' })).status, 201);
    const portal = await (await fetch(base + '/client-portal', { headers: portalHeaders })).json();
    assert.equal(portal.client.portalRequests.length, 1);
    assert.equal((await fetch(base + `/client-portal/requests/${portal.client.portalRequests[0].id}/approve`, { method: 'POST', headers: portalHeaders, body: '{}' })).status, 200);
    assert.equal((await fetch(base + '/client-portal/comments', { method: 'POST', headers: portalHeaders, body: JSON.stringify({ message: 'Aprovado pela cliente.' }) })).status, 201);
    assert.equal((await fetch(base + '/client-portal/documents', { method: 'POST', headers: portalHeaders, body: JSON.stringify({ name: 'arquivo.pdf', mime: 'application/pdf', data: Buffer.from('%PDF-1.4').toString('base64') }) })).status, 201);
    const ownerRecord = (await (await call('/clients')).json()).find((item: { id: string }) => item.id === clientId);
    assert.equal(ownerRecord.operationSignals.length, 1);
    assert.equal(ownerRecord.portalDocuments.length, 1);
    assert.equal(ownerRecord.portalDocuments[0].data, undefined);
    assert.equal(ownerRecord.portalTokenHash, undefined);
    assert.equal((await call(`/clients/${clientId}/operation-access`)).status, 402);
  });
  await t.test('independent invitation links only the matching new account and stays unlicensed before payment', async () => {
    const clientId = 'client-independent-audit';
    assert.equal((await call('/clients/register', 'POST', { id: clientId, name: 'Empresa Independente' })).status, 201);
    const invitationResponse = await call(`/clients/${clientId}/invite`, 'POST', { email: 'independent@example.test', kind: 'independent' });
    assert.equal(invitationResponse.status, 200);
    const invitation = await invitationResponse.json();
    const invitationParts = new URLSearchParams(new URL(invitation.inviteUrl).hash.slice(1));
    const signup = await call('/auth/signup', 'POST', { name: 'Cliente Independente', email: 'independent@example.test', password: 'SenhaForte123', confirmation: 'SenhaForte123', termsAccepted: true, privacyAccepted: true, clientInviteId: clientId, clientInviteToken: invitationParts.get('token') }, {});
    assert.equal(signup.status, 201);
    const record = (await (await call('/clients')).json()).find((item: { id: string }) => item.id === clientId);
    assert.equal(record.operationState, 'invited');
    assert.equal(record.billingStatus, 'none');
    assert.match(record.linkedWorkspaceId, /^ws-personal-/);
    assert.equal(record.independentTokenHash, undefined);
    assert.equal((await call(`/clients/${clientId}/operation-access`)).status, 402);
    const linkedCheckout = await call(`/clients/${clientId}/managed-checkout`, 'POST', {});
    assert.equal(linkedCheckout.status, 409);
    assert.equal((await linkedCheckout.json()).code, 'CLIENT_WORKSPACE_ALREADY_LINKED');
    const unlinkedClientId = 'client-unconfigured-billing-audit';
    assert.equal((await call('/clients/register', 'POST', { id: unlinkedClientId, name: 'Sem Cobrança Configurada' })).status, 201);
    const previousPrice = process.env.STRIPE_MANAGED_OPERATION_PRICE_ID;
    delete process.env.STRIPE_MANAGED_OPERATION_PRICE_ID;
    try {
      const checkout = await call(`/clients/${unlinkedClientId}/managed-checkout`, 'POST', {});
      assert.equal(checkout.status, 503);
      assert.equal((await checkout.json()).code, 'MANAGED_BILLING_NOT_CONFIGURED');
    } finally {
      if (previousPrice === undefined) delete process.env.STRIPE_MANAGED_OPERATION_PRICE_ID;
      else process.env.STRIPE_MANAGED_OPERATION_PRICE_ID = previousPrice;
    }
  });
  await t.test('independent invitation rejects a wrong token and is consumed only once', async () => {
    const clientId = 'client-independent-token-audit';
    assert.equal((await call('/clients/register', 'POST', { id: clientId, name: 'Empresa com Convite' })).status, 201);
    const response = await call(`/clients/${clientId}/invite`, 'POST', { email: 'token-audit@example.test', kind: 'independent' });
    assert.equal(response.status, 200);
    const token = new URLSearchParams(new URL((await response.json()).inviteUrl).hash.slice(1)).get('token');
    const signup = await call('/auth/signup', 'POST', { name: 'Cliente Convite', email: 'token-audit@example.test', password: 'SenhaForte123', confirmation: 'SenhaForte123', termsAccepted: true, privacyAccepted: true, clientInviteId: clientId, clientInviteToken: 'token-incorreto' }, {});
    assert.equal(signup.status, 201);
    const before = (await (await call('/clients')).json()).find((item: { id: string }) => item.id === clientId);
    assert.equal(before.linkedWorkspaceId, undefined);
    const login = await call('/auth/login', 'POST', { email: 'token-audit@example.test', password: 'SenhaForte123', clientInviteId: clientId, clientInviteToken: token }, {});
    assert.equal(login.status, 200);
    const linked = (await (await call('/clients')).json()).find((item: { id: string }) => item.id === clientId);
    assert.match(linked.linkedWorkspaceId, /^ws-personal-/);
    const repeated = await call('/auth/login', 'POST', { email: 'token-audit@example.test', password: 'SenhaForte123', clientInviteId: clientId, clientInviteToken: token }, {});
    assert.equal(repeated.status, 200);
    const after = (await (await call('/clients')).json()).find((item: { id: string }) => item.id === clientId);
    assert.equal(after.linkedWorkspaceId, linked.linkedWorkspaceId);
  });
  await t.test('invitation validates email, plan capacity, and cannot bypass acceptance', async () => {
    assert.equal((await call('/invites', 'POST', { name: 'Audit', email: 'invalid' })).status, 400);
    assert.equal((await call('/invites', 'POST', { name: 'Audit', email: 'audit@example.test' }, personal)).status, 403);
    const invite = await call('/invites', 'POST', { name: 'Audit', email: 'audit@example.test', modules: ['calendar'] });
    assert.equal(invite.status, 201);
    const member = await invite.json();
    assert.equal((await call(`/users/${member.id}`, 'PATCH', { status: 'active' })).status, 409);
    assert.equal((await call(`/users/${member.id}`, 'DELETE', undefined, personal)).status, 403);
  });
  await t.test('approval validates comments and dates, isolates records, and never fakes publication', async () => {
    const created = await call('/approvals', 'POST', { title: 'Audit content', contentId: 'audit-post', copy: 'Test', platform: 'instagram', format: 'post' });
    assert.equal(created.status, 201);
    const item = await created.json();
    const actionPath = `/approvals/${item.id}/actions`;
    assert.equal((await call(actionPath, 'POST', { action: 'approve' }, personal)).status, 403);
    assert.equal((await call(actionPath, 'POST', { action: 'comment', comment: ' ' })).status, 400);
    assert.equal((await call(actionPath, 'POST', { action: 'publish' })).status, 409);
    assert.equal((await call(actionPath, 'POST', { action: 'approve' })).status, 200);
    for (const scheduledAt of ['invalid', '2001-01-01T12:00:00Z']) {
      assert.equal((await call(actionPath, 'POST', { action: 'schedule', scheduledAt })).status, 400);
    }
    const scheduledAt = new Date(Date.now() + 86400000).toISOString();
    assert.equal((await call(actionPath, 'POST', { action: 'schedule', scheduledAt })).status, 200);
    assert.equal((await call(actionPath, 'POST', { action: 'publish' })).status, 501);
    const records = await (await call('/approvals')).json();
    assert.equal(records[0].stage, 'approved');
    assert.equal(records[0].scheduledAt, scheduledAt);
    assert.equal((await call('/approvals', 'GET', undefined, personal)).status, 403);
  });
  await t.test('calendar rescheduling changes the persisted date without approving content or crossing workspaces', async () => {
    const payload = { title: 'Calendar fixture', contentId: 'calendar-reschedule', copy: 'Test', platform: 'instagram', format: 'post' };
    assert.equal((await call('/approvals', 'POST', { ...payload, scheduledAt: 'invalid' })).status, 400);
    const item = await (await call('/approvals', 'POST', payload)).json();
    const endpoint = `/approvals/${item.id}/actions`;
    const scheduledAt = new Date(Date.now() + 86400000 * 2).toISOString();
    assert.equal((await call(endpoint, 'POST', { action: 'reschedule', scheduledAt }, personal)).status, 403);
    for (const badDate of ['invalid', '2001-01-01T12:00:00Z']) {
      assert.equal((await call(endpoint, 'POST', { action: 'reschedule', scheduledAt: badDate })).status, 400);
    }
    const changed = await call(endpoint, 'POST', { action: 'reschedule', scheduledAt });
    assert.equal(changed.status, 200);
    const data = await changed.json();
    assert.equal(data.scheduledAt, scheduledAt);
    assert.equal(data.stage, 'pending_approval');
    assert.equal(data.approvedAt, undefined);
    assert.equal(data.history[0].action, 'reschedule');
    assert.equal((await call(endpoint, 'POST', { action: 'publish' })).status, 409);
  });
  await t.test('organization licenses, roles, scopes, usage pool, add-ons and Master transfer are enforced server-side', async () => {
    const initialLicenses = await (await call('/licenses')).json();
    assert.equal(initialLicenses.filter((license: any) => license.status === 'in_use').length, 1);
    assert.equal((await call('/licenses', 'GET', undefined, personal)).status, 403);

    for (const [id, name] of [['client-alpha', 'Cliente Alpha'], ['client-beta', 'Cliente Beta']]) {
      assert.equal((await call('/clients/register', 'POST', { id, name })).status, 201);
    }
    const analystInviteResponse = await call('/invites', 'POST', {
      name: 'Analista Restrito', email: 'analyst@example.test', role: 'analyst', modules: ['dashboard', 'analytics', 'ai-chat'],
      scope: { allClients: false, clientIds: ['client-alpha'], allSocialAccounts: false, socialAccountIds: [], allProjects: false, projectIds: [], resourceIds: [] },
    });
    assert.equal(analystInviteResponse.status, 201);
    const analystInvite = await analystInviteResponse.json();
    assert.equal(analystInvite.role, 'analyst');
    assert.equal(analystInvite.licenseId, undefined, 'an invite must not consume a license unless explicitly reserved');
    assert.equal((await call('/licenses')).status, 200);
    assert.equal((await (await call('/licenses')).json()).filter((license: any) => license.status === 'in_use').length, 1);
    assert.equal((await call('/invites/accept', 'POST', { token: analystInvite.developmentInviteToken, password: 'ValidPass1' }, {})).status, 200);
    const analyst = { 'x-workspace-id': 'ws-1', 'x-user-id': analystInvite.id };
    assert.equal((await call('/access/modules/analytics', 'GET', undefined, analyst)).status, 200);
    assert.equal((await call('/access/modules/create-image', 'GET', undefined, analyst)).status, 403);
    assert.equal((await call('/subscription', 'GET', undefined, analyst)).status, 403);
    assert.deepEqual((await (await call('/clients', 'GET', undefined, analyst)).json()).map((client: any) => client.id), ['client-alpha']);
    assert.equal((await call('/clients/register', 'POST', { id: 'client-forbidden', name: 'Não autorizado' }, analyst)).status, 403);
    assert.equal((await fetch(`${klic}/memory?workspaceId=ws-1&clientId=client-alpha`, { headers: analyst })).status, 200);
    assert.equal((await fetch(`${klic}/memory?workspaceId=ws-1&clientId=client-beta`, { headers: analyst })).status, 403);

    assert.equal((await call('/usage/policy', 'PATCH', { allocationMode: 'member_limits', memberId: analystInvite.id, limits: { klic_credits: 1 } })).status, 200);
    assert.equal((await call('/usage/consume', 'POST', { resource: 'klic_credits', amount: 1 }, analyst)).status, 200);
    const exhausted = await call('/usage/consume', 'POST', { resource: 'klic_credits', amount: 1 }, analyst);
    assert.equal(exhausted.status, 409);
    assert.equal((await exhausted.json()).code, 'MEMBER_USAGE_EXHAUSTED');
    const ownUsage = await (await call('/usage', 'GET', undefined, analyst)).json();
    assert.equal(ownUsage.resources.klic_credits.used, 1);
    assert.equal(ownUsage.resources.klic_credits.limit, 1);
    assert.deepEqual(Object.keys(ownUsage.memberUsage), [analystInvite.id], 'members only receive their own usage');
    const beforeAddOn = await (await call('/usage')).json();
    assert.equal((await call('/subscription/add-ons', 'POST', { resource: 'klic_credits', quantity: 25 })).status, 201);
    const afterAddOn = await (await call('/usage')).json();
    assert.equal(afterAddOn.resources.klic_credits.limit, beforeAddOn.resources.klic_credits.limit + 25);

    const analystLicense = (await (await call('/licenses')).json()).find((license: any) => license.memberId === analystInvite.id);
    assert.ok(analystLicense);
    assert.equal((await call(`/licenses/${analystLicense.id}`, 'PATCH', { status: 'suspended' })).status, 200);
    const unlicensedAccess = await call('/clients', 'GET', undefined, analyst);
    assert.equal(unlicensedAccess.status, 401, 'suspending a license immediately revokes the membership session');

    const managerInviteResponse = await call('/invites', 'POST', { name: 'Novo Master', email: 'owner@example.test', role: 'manager', reserveSeat: true, modules: ['dashboard'] });
    assert.equal(managerInviteResponse.status, 201);
    const managerInvite = await managerInviteResponse.json();
    const reserved = await (await call('/licenses')).json();
    assert.ok(reserved.some((license: any) => license.id === managerInvite.licenseId && license.status === 'reserved'));
    assert.equal((await call('/invites/accept', 'POST', { token: managerInvite.developmentInviteToken, password: 'ValidPass2' }, {})).status, 200);
    const transferred = await call('/ownership/transfer', 'POST', { targetUserId: managerInvite.id });
    assert.equal(transferred.status, 200);
    const transferBody = await transferred.json();
    assert.equal(transferBody.owner.role, 'master');
    assert.equal(transferBody.previousOwner.role, 'administrator');
    assert.equal((await call('/ownership/transfer', 'POST', { targetUserId: analystInvite.id })).status, 403);
  });
});
