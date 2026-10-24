import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import express from 'express';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createGovernanceRouter } from './governance';
import { createIntegrationsRouter, readKlicAnalytics, readKlicConnections, readKlicScheduledPublications, runDueScheduledPublications } from './integrations';
import { createTokenCipher } from './integrations/crypto';
import { providerJson } from './integrations/http';
import { socialProviderRegistry } from './integrations/providers/registry';
import { SocialIntegrationRepository } from './integrations/repository';
import { validatePublishRequest } from './integrations/publishing';
import { emptyCapabilities, type StoredSocialConnection } from './integrations/types';
import { verifySocialWebhookChallenge, verifySocialWebhookSignature } from './integrations/webhooks';

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

test('social integrations refuse publicly served token storage locations', () => {
  for (const folder of ['public', 'dist']) {
    assert.throws(
      () => createIntegrationsRouter({ dataFile: path.resolve(folder, 'social-integrations.json') }),
      /SOCIAL_STORE_PUBLIC_PATH/,
    );
  }
});

test('stale claimed publication becomes indeterminate without a second provider attempt', () => {
  const repository = new SocialIntegrationRepository(null);
  const owner = { ownerType: 'workspace' as const, ownerId: 'ws-scheduler-test' };
  const created = repository.upsert({ ...owner, provider: 'tiktok', providerAccountId: 'account-1', displayName: 'Account',
    accessTokenEncrypted: 'encrypted', scopes: [], status: 'connected', capabilities: emptyCapabilities(), providerMetadata: {} }, '2026-01-01T00:00:00.000Z');
  const job = repository.schedule(owner, { connectionId: created.id, contentId: 'content-one', scheduledAt: '2026-01-01T01:00:00.000Z',
    request: { kind: 'video', text: 'Scheduled', mediaUrls: ['https://example.test/video.mp4'], userConsentConfirmed: true } }, '2026-01-01T00:00:00.000Z');
  assert.ok(job);
  assert.equal(repository.claimDue('2026-01-01T01:00:00.000Z').length, 1);
  assert.equal(repository.claimDue('2026-01-01T01:01:00.000Z').length, 0);
  assert.equal(repository.recoverStalePublishing('2026-01-01T00:59:00.000Z').length, 0);
  assert.equal(repository.recoverStalePublishing('2026-01-01T01:11:00.000Z', '2026-01-01T01:11:00.000Z')[0].status, 'indeterminate');
  assert.equal(repository.claimDue('2026-01-01T02:00:00.000Z').length, 0);
});

test('confirmed scheduled publications remain in owner history and cannot be cancelled', () => {
  const repository = new SocialIntegrationRepository(null);
  const owner = { ownerType: 'workspace' as const, ownerId: 'ws-history-a' };
  const other = { ownerType: 'workspace' as const, ownerId: 'ws-history-b' };
  const connection = repository.upsert({ ...owner, provider: 'tiktok', providerAccountId: 'account-history', displayName: 'Account',
    accessTokenEncrypted: 'encrypted', scopes: [], status: 'connected', capabilities: emptyCapabilities(), providerMetadata: {} }, '2026-01-01T00:00:00.000Z');
  const job = repository.schedule(owner, { connectionId: connection.id, contentId: 'content-history', scheduledAt: '2026-01-01T01:00:00.000Z',
    request: { kind: 'video', text: 'Publicado', mediaUrls: ['https://example.test/video.mp4'], userConsentConfirmed: true } }, '2026-01-01T00:00:00.000Z');
  assert.ok(job);
  assert.equal(repository.claimDue('2026-01-01T01:00:00.000Z').length, 1);
  assert.equal(repository.listScheduled(owner)[0].status, 'publishing');
  repository.updateScheduled(owner, job.id, { status: 'published', providerPostId: 'provider-history-1' }, '2026-01-01T01:00:30.000Z');
  assert.equal(repository.listScheduled(owner)[0].status, 'published');
  assert.equal(repository.listScheduled(owner)[0].providerPostId, 'provider-history-1');
  assert.equal(repository.listScheduled(other).length, 0);
  assert.equal(repository.cancelScheduled(owner, job.id), undefined);
  assert.equal(repository.rescheduleScheduled(owner, job.id, '2026-01-02T01:00:00.000Z'), undefined);
});

test('social OAuth persists encrypted tokens, isolates owners, refreshes, validates, deduplicates and revokes', async t => {
  const previous = new Map(['TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET', 'TIKTOK_REDIRECT_URI', 'SOCIAL_TOKEN_ENCRYPTION_KEY', 'PUBLIC_APP_URL', 'APP_URL'].map(key => [key, process.env[key]]));
  process.env.TIKTOK_CLIENT_KEY = 'test-client';
  process.env.TIKTOK_CLIENT_SECRET = 'test-secret';
  process.env.TIKTOK_REDIRECT_URI = 'http://localhost/api/integrations/oauth/callback';
  process.env.SOCIAL_TOKEN_ENCRYPTION_KEY = Buffer.alloc(32, 7).toString('base64url');
  delete process.env.PUBLIC_APP_URL;
  delete process.env.APP_URL;
  t.after(() => previous.forEach((value, key) => value === undefined ? delete process.env[key] : process.env[key] = value));

  let currentTime = Date.now();
  let revoked = false;
  let refreshes = 0;
  let revocations = 0;
  let publications = 0;
  let publicationRateLimited = false;
  const fetcher = (async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/v2/oauth/token/')) {
      const body = new URLSearchParams(String(init?.body || ''));
      if (body.get('grant_type') === 'refresh_token') {
        refreshes += 1;
        return json({ access_token: 'access-two', refresh_token: 'refresh-two', expires_in: 86400, refresh_expires_in: 31536000, scope: 'user.info.basic,video.list,video.publish' });
      }
      return json({ access_token: 'access-one', refresh_token: 'refresh-one', expires_in: 60, refresh_expires_in: 31536000, scope: 'user.info.basic,video.list,video.publish' });
    }
    if (url.includes('/v2/oauth/revoke/')) { revocations += 1; return json({}); }
    if (url.includes('/v2/post/publish/creator_info/query/')) return json({ data: { privacy_level_options: ['SELF_ONLY'], max_video_post_duration_sec: 600 } });
    if (url.includes('/v2/post/publish/video/init/')) { publications += 1; return publicationRateLimited
      ? json({ error: { code: 'rate_limit_exceeded' } }, 429) : json({ data: { publish_id: 'tt-post-1' } }); }
    if (url.includes('/v2/user/info/')) return revoked ? json({ error: { code: 'invalid_token' } }, 401) : json({ data: { user: { open_id: 'tt-account-1', username: 'clicko', display_name: 'Clicko TikTok', avatar_url: 'https://example.test/avatar.png' } } });
    return json({ error: { code: 'unexpected_request' } }, 400);
  }) as typeof fetch;

  const directory = mkdtempSync(path.join(tmpdir(), 'clicko-social-'));
  const dataFile = path.join(directory, 'social.json');
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const app = express();
  app.use(express.json());
  app.use('/api/governance', createGovernanceRouter({ dataFile: null }));
  app.use('/api/integrations', createIntegrationsRouter({ dataFile, fetch: fetcher, now: () => currentTime }));
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(() => new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve())));
  const base = `http://127.0.0.1:${(server.address() as { port: number }).port}/api/integrations`;
  const company = { 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master', 'Content-Type': 'application/json' };
  const personal = { 'x-workspace-id': 'ws-personal', 'x-user-id': 'usr-master-personal', 'Content-Type': 'application/json' };
  const request = (route: string, init: RequestInit = {}) => fetch(base + route, { ...init, headers: { ...company, ...init.headers }, redirect: 'manual' });
  const beginOAuth = async (body = '{}') => {
    const response = await request('/tiktok/authorize', { method: 'POST', body });
    return { data: await response.json(), cookie: String(response.headers.get('set-cookie') || '').split(';')[0] };
  };

  assert.equal((await fetch(base + '/connections')).status, 401);
  assert.equal((await fetch(base + '/oauth/callback?state=invalid', { redirect: 'manual' })).status, 400);
  const providers = await (await request('/providers')).json();
  assert.equal(providers.providers.find((item: { id: string }) => item.id === 'tiktok').configured, true);

  const begin = await beginOAuth(JSON.stringify({ returnTo: '//outside.example' }));
  const authorization = new URL(begin.data.authorizationUrl);
  const state = authorization.searchParams.get('state')!;
  assert.equal(authorization.origin, 'https://www.tiktok.com');
  assert.equal(authorization.searchParams.get('client_secret'), null);
  assert.equal((await fetch(`${base}/oauth/callback?state=${encodeURIComponent(state)}&code=stolen`, { redirect: 'manual', headers: { Cookie: 'clicko_social_oauth=wrong-browser' } })).status, 400);
  const callback = await fetch(`${base}/oauth/callback?state=${encodeURIComponent(state)}&code=valid-code`, { redirect: 'manual', headers: { Cookie: begin.cookie } });
  assert.equal(callback.status, 302);
  assert.match(callback.headers.get('location') || '', /\/connected-accounts\?integration=tiktok&status=connected/);
  assert.equal((await fetch(`${base}/oauth/callback?state=${encodeURIComponent(state)}&code=replay`, { redirect: 'manual' })).status, 400);

  let connections = await (await request('/connections')).json();
  assert.equal(connections.connections.length, 1);
  assert.equal(connections.connections[0].providerAccountId, 'tt-account-1');
  assert.equal('accessTokenEncrypted' in connections.connections[0], false);
  assert.equal('refreshTokenEncrypted' in connections.connections[0], false);
  assert.equal((await (await fetch(base + '/connections', { headers: personal })).json()).connections.length, 0);
  const stored = readFileSync(dataFile, 'utf8');
  for (const secret of ['access-one', 'refresh-one', 'test-secret']) assert.equal(stored.includes(secret), false);
  assert.equal(new SocialIntegrationRepository(dataFile).list({ ownerType: 'workspace', ownerId: 'ws-1' }).length, 1);

  const duplicateBegin = await beginOAuth();
  const duplicateState = new URL(duplicateBegin.data.authorizationUrl).searchParams.get('state')!;
  assert.equal((await fetch(`${base}/oauth/callback?state=${encodeURIComponent(duplicateState)}&code=valid-code`, { redirect: 'manual', headers: { Cookie: duplicateBegin.cookie } })).status, 302);
  connections = await (await request('/connections')).json();
  assert.equal(connections.connections.length, 1);

  currentTime += 120_000;
  const status = await (await request('/tiktok/status')).json();
  assert.equal(status.connected, true);
  assert.equal(refreshes, 1);
  assert.equal(readFileSync(dataFile, 'utf8').includes('access-two'), false);
  assert.equal((await (await request('/tiktok/test', { method: 'POST', body: '{}' })).json()).healthy, true);

  process.env.APP_URL = `http://localhost:${new URL(base).port}`;
  assert.equal((await request('/tiktok/test', { method: 'POST', body: '{}', headers: { Origin: `http://127.0.0.1:${new URL(base).port}` } })).status, 200);
  assert.equal((await request('/tiktok/test', { method: 'POST', body: '{}', headers: { Origin: 'https://cross-site.example.test' } })).status, 403);
  delete process.env.APP_URL;

  connections = await (await request('/connections')).json();
  const connectionId = connections.connections[0].id;
  const governanceBase = base.replace('/api/integrations', '/api/governance');
  const inviteRestrictedMember = async (role: 'creative' | 'social_media', email: string) => {
    const invitationResponse = await fetch(`${governanceBase}/invites`, {
      method: 'POST', headers: company,
      body: JSON.stringify({ name: `Integration ${role}`, email, role, reserveSeat: true, modules: ['connected-accounts'] }),
    });
    assert.equal(invitationResponse.status, 201);
    const invitation = await invitationResponse.json();
    assert.equal((await fetch(`${governanceBase}/invites/accept`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: invitation.developmentInviteToken, password: 'ValidPass1' }),
    })).status, 200);
    return { 'x-workspace-id': 'ws-1', 'x-user-id': invitation.id, 'Content-Type': 'application/json' };
  };
  const creativeMember = await inviteRestrictedMember('creative', 'creative-integrations@example.test');
  const socialMember = await inviteRestrictedMember('social_media', 'social-integrations@example.test');
  assert.equal((await fetch(`${base}/tiktok/status`, { headers: creativeMember })).status, 403);
  assert.equal((await fetch(`${base}/tiktok/sync`, { method: 'POST', headers: creativeMember, body: '{}' })).status, 403);
  assert.equal((await fetch(`${base}/tiktok/status`, { headers: socialMember })).status, 200);
  assert.equal((await fetch(`${base}/tiktok/sync`, { method: 'POST', headers: socialMember, body: '{}' })).status, 403);
  for (const [id, name] of [['client-clicko', 'Clicko Studio'], ['client-vitalis', 'Vitalis']]) {
    assert.equal((await fetch(`${governanceBase}/clients/register`, { method: 'POST', headers: company, body: JSON.stringify({ id, name }) })).status, 201);
  }
  assert.equal((await request(`/connections/${connectionId}/client`, { method: 'PATCH', body: JSON.stringify({ clientId: 'client-unknown' }) })).status, 400);
  assert.equal((await fetch(`${base}/connections/${connectionId}/client`, { method: 'PATCH', headers: personal, body: JSON.stringify({ clientId: null }) })).status, 404);
  assert.equal((await request(`/connections/${connectionId}/client`, { method: 'PATCH', body: JSON.stringify({ clientId: 'client-clicko' }) })).status, 200);
  assert.equal((await (await request('/connections')).json()).connections[0].clientId, 'client-clicko');
  const reconnect = await beginOAuth();
  const reconnectState = new URL(reconnect.data.authorizationUrl).searchParams.get('state')!;
  assert.equal((await fetch(`${base}/oauth/callback?state=${encodeURIComponent(reconnectState)}&code=valid-code`, { redirect: 'manual', headers: { Cookie: reconnect.cookie } })).status, 302);
  const afterReconnect = (await (await request('/connections')).json()).connections;
  assert.equal(afterReconnect.length, 1);
  assert.equal(afterReconnect[0].id, connectionId);
  assert.equal(afterReconnect[0].clientId, 'client-clicko');
  assert.equal((await request('/connections/validate', { method: 'POST', body: JSON.stringify({ clientId: 'client-clicko', connectionIds: [connectionId] }) })).status, 200);
  assert.equal((await request('/connections/validate', { method: 'POST', body: JSON.stringify({ connectionIds: [connectionId] }) })).status, 409);
  assert.equal((await request('/connections/validate', { method: 'POST', body: JSON.stringify({ clientId: 'client-vitalis', connectionIds: [connectionId] }) })).status, 409);
  assert.equal((await fetch(`${base}/connections/validate`, { method: 'POST', headers: personal, body: JSON.stringify({ clientId: 'client-clicko', connectionIds: [connectionId] }) })).status, 400);
  assert.equal((await request('/connections/validate', { method: 'POST', body: JSON.stringify({ clientId: 'client-clicko', connectionIds: [connectionId], requireScheduling: true }) })).status, 200);
  assert.deepEqual((await (await request('/analytics/snapshots')).json()).snapshots, []);
  assert.deepEqual((await (await fetch(base + '/analytics/snapshots', { headers: personal })).json()).snapshots, []);
  assert.equal((await request('/tiktok/sync', { method: 'POST', body: JSON.stringify({ connectionId: 'social-other-workspace' }) })).status, 401);
  const synced = await (await request('/tiktok/sync', { method: 'POST', body: JSON.stringify({ connectionId }) })).json();
  assert.equal(synced.selectedResources, 1);
  assert.equal(synced.analytics, undefined);
  const publishBody = JSON.stringify({ kind: 'video', text: 'Publicação validada', mediaUrls: ['https://cdn.example.test/video.mp4'], userConsentConfirmed: true });
  assert.equal((await request(`/connections/${connectionId}/publish`, { method: 'POST', headers: { 'Idempotency-Key': 'publish-other-client-001' }, body: JSON.stringify({ ...JSON.parse(publishBody), clientId: 'client-vitalis' }) })).status, 409);
  assert.equal((await request(`/connections/${connectionId}/publish`, { method: 'POST', headers: { 'Idempotency-Key': 'publish-missing-client-001' }, body: publishBody })).status, 409);
  const scopedPublishBody = JSON.stringify({ ...JSON.parse(publishBody), clientId: 'client-clicko' });
  const published = await (await request(`/connections/${connectionId}/publish`, { method: 'POST', headers: { 'Idempotency-Key': 'publish-operation-001' }, body: scopedPublishBody })).json();
  assert.equal(published.providerPostId, 'tt-post-1');
  assert.equal(published.replayed, false);
  const replayed = await (await request(`/connections/${connectionId}/publish`, { method: 'POST', headers: { 'Idempotency-Key': 'publish-operation-001' }, body: scopedPublishBody })).json();
  assert.equal(replayed.replayed, true);
  assert.equal(publications, 1);

  const contentId = 'post-scheduled-one';
  const approval = await (await fetch(`${governanceBase}/approvals`, { method: 'POST', headers: company,
    body: JSON.stringify({ contentId, title: 'Vídeo validado', copy: 'Texto', platform: 'tiktok', format: 'reels' }) })).json();
  const scheduledAt = new Date(currentTime + 60_000).toISOString();
  const scheduleBody = JSON.stringify({ contentId, title: 'Vídeo agendado', connectionId, clientId: 'client-clicko', scheduledAt,
    request: { kind: 'video', text: 'Vídeo autorizado', mediaUrls: ['https://cdn.example.test/video.mp4'], userConsentConfirmed: true } });
  assert.equal((await request('/publications/schedule', { method: 'POST', body: scheduleBody })).status, 409);
  assert.equal((await fetch(`${governanceBase}/approvals/${approval.id}/actions`, { method: 'POST', headers: company, body: JSON.stringify({ action: 'approve' }) })).status, 200);
  assert.equal((await request('/publications/schedule', { method: 'POST', body: JSON.stringify({ ...JSON.parse(scheduleBody), clientId: null }) })).status, 409);
  const cancelBody = JSON.stringify({ ...JSON.parse(scheduleBody), contentId: 'post-cancelled-one' });
  const cancelCreated = await request('/publications/schedule', { method: 'POST', body: cancelBody });
  assert.equal(cancelCreated.status, 201);
  const cancelId = (await cancelCreated.json()).publication.id;
  assert.equal((await request(`/publications/scheduled/${cancelId}`, { method: 'DELETE' })).status, 200);
  assert.equal((await request(`/publications/scheduled/${cancelId}`, { method: 'DELETE' })).status, 409);
  assert.equal((await request(`/publications/scheduled/${cancelId}`, { method: 'PATCH', body: JSON.stringify({ scheduledAt: new Date(currentTime + 120_000).toISOString() }) })).status, 409);
  assert.equal((await request('/publications/schedule', { method: 'POST', body: cancelBody })).status, 409);
  const scheduled = await request('/publications/schedule', { method: 'POST', body: scheduleBody });
  assert.equal(scheduled.status, 201);
  const scheduleId = (await scheduled.json()).publication.id;
  assert.equal((await request('/publications/schedule', { method: 'POST', body: scheduleBody })).status, 200);
  const rescheduledAt = new Date(currentTime + 120_000).toISOString();
  assert.equal((await request(`/publications/scheduled/${scheduleId}`, { method: 'PATCH', body: JSON.stringify({ scheduledAt: new Date(currentTime - 1).toISOString() }) })).status, 400);
  assert.equal((await fetch(`${base}/publications/scheduled/${scheduleId}`, { method: 'PATCH', headers: personal, body: JSON.stringify({ scheduledAt: rescheduledAt }) })).status, 404);
  const rescheduled = await request(`/publications/scheduled/${scheduleId}`, { method: 'PATCH', body: JSON.stringify({ scheduledAt: rescheduledAt }) });
  assert.equal(rescheduled.status, 200);
  assert.equal((await rescheduled.json()).publication.scheduledAt, rescheduledAt);
  currentTime += 121_000;
  await runDueScheduledPublications();
  await runDueScheduledPublications();
  const jobs = (await (await request('/publications/scheduled')).json()).publications;
  assert.equal(jobs.find((job: { id: string }) => job.id === scheduleId).status, 'processing');
  assert.equal(jobs.find((job: { id: string }) => job.id === scheduleId).title, 'Vídeo agendado');
  assert.equal(jobs.find((job: { id: string }) => job.id === scheduleId).provider, 'tiktok');
  assert.equal(jobs.find((job: { id: string }) => job.id === scheduleId).scheduledAt, rescheduledAt);
  assert.equal((await request(`/publications/scheduled/${scheduleId}`, { method: 'PATCH', body: JSON.stringify({ scheduledAt: new Date(currentTime + 60_000).toISOString() }) })).status, 409);
  assert.equal(jobs.find((job: { id: string }) => job.id === cancelId).status, 'cancelled');
  assert.equal(publications, 2);
  const klicCalendar = await readKlicScheduledPublications('ws-1', 'company', 'client-clicko');
  assert.equal(klicCalendar.find(record => record.publicationId === scheduleId)?.title, 'Vídeo agendado');
  assert.equal((await readKlicScheduledPublications('ws-1', 'company')).find(record => record.publicationId === scheduleId)?.clientId, null);
  assert.equal(JSON.stringify(klicCalendar).includes('access-two'), false);
  assert.deepEqual(await readKlicScheduledPublications('ws-1', 'personal', 'client-clicko'), []);
  assert.deepEqual(await readKlicScheduledPublications('ws-1', 'company', 'client-vitalis'), []);

  const failedAt = new Date(currentTime + 60_000).toISOString();
  const failureBody = JSON.stringify({ ...JSON.parse(scheduleBody), contentId: 'post-rate-limited-one', scheduledAt: failedAt });
  const failedCreated = await request('/publications/schedule', { method: 'POST', body: failureBody });
  assert.equal(failedCreated.status, 201);
  const failedId = (await failedCreated.json()).publication.id;
  publicationRateLimited = true;
  currentTime += 61_000;
  await runDueScheduledPublications();
  await runDueScheduledPublications();
  assert.equal(publications, 3);
  assert.equal((await (await request('/publications/scheduled')).json()).publications.find((job: { id: string }) => job.id === failedId).status, 'indeterminate');
  publicationRateLimited = false;

  revoked = true;
  const unhealthy = await (await request('/tiktok/test', { method: 'POST', body: '{}' })).json();
  assert.equal(unhealthy.healthy, false);
  assert.equal(unhealthy.results[0].status, 'authorization_revoked');
  revoked = false;
  const disconnected = await (await request('/tiktok/disconnect', { method: 'POST', body: '{}' })).json();
  assert.equal(disconnected.count, 1);
  assert.equal(revocations, 1);
  assert.equal((await (await request('/connections')).json()).connections.length, 0);

  const incompleteBegin = await beginOAuth();
  const incompleteState = new URL(incompleteBegin.data.authorizationUrl).searchParams.get('state')!;
  const incomplete = await fetch(`${base}/oauth/callback?state=${encodeURIComponent(incompleteState)}`, { redirect: 'manual', headers: { Cookie: incompleteBegin.cookie } });
  assert.equal(incomplete.status, 302);
  assert.match(incomplete.headers.get('location') || '', /status=error&reason=provider_error/);

  const expiredBegin = await beginOAuth();
  const expiredState = new URL(expiredBegin.data.authorizationUrl).searchParams.get('state')!;
  currentTime += 11 * 60_000;
  assert.equal((await fetch(`${base}/oauth/callback?state=${encodeURIComponent(expiredState)}&code=late`, { redirect: 'manual', headers: { Cookie: expiredBegin.cookie } })).status, 400);
});

test('provider analytics snapshots remain scoped to the social account and feed KLIC with normalized metrics', async () => {
  const repository = new SocialIntegrationRepository(null);
  const owner = { ownerType: 'workspace' as const, ownerId: 'ws-1' };
  const connection = repository.upsert({ ...owner, provider: 'youtube', providerAccountId: 'channel-1', displayName: 'Canal 1',
    accessTokenEncrypted: 'encrypted-test-only', scopes: [], status: 'connected', capabilities: emptyCapabilities(), providerMetadata: {} });
  const snapshot = { connectionId: connection.id, provider: 'youtube' as const, from: '2026-09-01', to: '2026-09-30',
    metrics: { followers: 1250, views: 8400 }, updatedAt: '2026-10-01T00:00:00.000Z' };
  assert.equal(repository.upsertAnalyticsSnapshot(owner, snapshot)?.metrics.views, 8400);
  assert.equal(repository.listAnalyticsSnapshots({ ownerType: 'workspace', ownerId: 'ws-other' }).length, 0);
  assert.equal(repository.upsertAnalyticsSnapshot({ ownerType: 'workspace', ownerId: 'ws-other' }, snapshot), undefined);
  createIntegrationsRouter({ repository });
  const accountRecords = await readKlicConnections('ws-1', 'company');
  assert.equal(accountRecords.find(record => 'socialAccountId' in record && record.socialAccountId === connection.id)?.connected, true);
  assert.equal(JSON.stringify(accountRecords).includes('encrypted-test-only'), false);
  assert.equal((await readKlicConnections('ws-1', 'personal')).some(record => 'socialAccountId' in record && record.socialAccountId === connection.id), false);
  const records = await readKlicAnalytics('ws-1', 'company');
  assert.deepEqual(records.map(record => [record.socialAccountId, record.metric, record.current]), [
    [connection.id, 'followers', 1250], [connection.id, 'views', 8400],
  ]);
  assert.deepEqual(await readKlicAnalytics('ws-other', 'company'), []);
  assert.deepEqual(await readKlicAnalytics('ws-1', 'company', 'client-other'), []);
  repository.update(connection.id, owner, { clientId: 'client-clicko' });
  assert.equal((await readKlicAnalytics('ws-1', 'company', 'client-clicko')).length, 2);
  assert.deepEqual(await readKlicAnalytics('ws-1', 'company', 'client-vitalis'), []);
  repository.remove(owner, 'youtube', [connection.id]);
  assert.deepEqual(repository.listAnalyticsSnapshots(owner), []);
});

test('OAuth cancellation is explicit and multi-resource selection is one-time and tenant isolated', async t => {
  const keys = ['META_APP_ID', 'META_APP_SECRET', 'META_REDIRECT_URI', 'SOCIAL_TOKEN_ENCRYPTION_KEY'] as const;
  const previous = new Map(keys.map(key => [key, process.env[key]]));
  t.after(() => previous.forEach((value, key) => value === undefined ? delete process.env[key] : process.env[key] = value));
  process.env.META_APP_ID = 'meta-app';
  process.env.META_APP_SECRET = 'meta-secret';
  process.env.META_REDIRECT_URI = 'http://localhost/api/integrations/oauth/callback';
  process.env.SOCIAL_TOKEN_ENCRYPTION_KEY = Buffer.alloc(32, 12).toString('base64url');
  const fetcher = (async (input: string | URL | Request) => {
    const url = new URL(String(input));
    if (url.pathname.endsWith('/oauth/access_token')) {
      return url.searchParams.get('grant_type') === 'fb_exchange_token'
        ? json({ access_token: 'long-user-token', expires_in: 5_184_000 })
        : json({ access_token: 'short-user-token', expires_in: 3_600 });
    }
    if (url.pathname.endsWith('/me/permissions')) return json({ data: [
      { permission: 'pages_show_list', status: 'granted' },
      { permission: 'pages_read_engagement', status: 'granted' },
      { permission: 'pages_manage_posts', status: 'granted' },
    ] });
    if (url.pathname.endsWith('/me/accounts')) return json({ data: [
      { id: 'page-one', name: 'Página Um', username: 'paginaum', access_token: 'page-token-one', tasks: ['CREATE_CONTENT'] },
      { id: 'page-two', name: 'Página Dois', username: 'paginadois', access_token: 'page-token-two', tasks: ['CREATE_CONTENT'] },
    ] });
    return json({ error: { message: 'unexpected' } }, 400);
  }) as typeof fetch;
  const directory = mkdtempSync(path.join(tmpdir(), 'clicko-social-selection-'));
  const dataFile = path.join(directory, 'social.json');
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const app = express();
  app.use(express.json());
  app.use('/api/governance', createGovernanceRouter({ dataFile: null }));
  app.use('/api/integrations', createIntegrationsRouter({ dataFile, fetch: fetcher }));
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(() => new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve())));
  const base = `http://127.0.0.1:${(server.address() as { port: number }).port}/api/integrations`;
  const company = { 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master', 'Content-Type': 'application/json' };
  const personal = { 'x-workspace-id': 'ws-personal', 'x-user-id': 'usr-master-personal', 'Content-Type': 'application/json' };
  const begin = async () => {
    const response = await fetch(`${base}/facebook/authorize`, { method: 'POST', headers: company, body: '{}', redirect: 'manual' });
    const data = await response.json();
    return { state: new URL(data.authorizationUrl).searchParams.get('state')!, cookie: String(response.headers.get('set-cookie') || '').split(';')[0] };
  };

  const cancelled = await begin();
  const cancelResponse = await fetch(`${base}/oauth/callback?state=${encodeURIComponent(cancelled.state)}&error=access_denied`, { redirect: 'manual', headers: { Cookie: cancelled.cookie } });
  assert.equal(cancelResponse.status, 302);
  assert.match(cancelResponse.headers.get('location') || '', /reason=authorization_denied/);
  assert.equal((await (await fetch(`${base}/connections`, { headers: company })).json()).connections.length, 0);

  const authorized = await begin();
  const callback = await fetch(`${base}/oauth/callback?state=${encodeURIComponent(authorized.state)}&code=valid`, { redirect: 'manual', headers: { Cookie: authorized.cookie } });
  assert.equal(callback.status, 302);
  const location = new URL(callback.headers.get('location')!);
  assert.equal(location.searchParams.get('status'), 'selection_required');
  const selectionToken = location.searchParams.get('selection')!;
  assert.equal((await (await fetch(`${base}/connections`, { headers: company })).json()).connections.length, 0);
  assert.equal((await fetch(`${base}/oauth/selections/${selectionToken}`, { headers: personal })).status, 404);
  const available = await (await fetch(`${base}/oauth/selections/${selectionToken}`, { headers: company })).json();
  assert.deepEqual(available.accounts.map((item: { providerAccountId: string }) => item.providerAccountId), ['page-one', 'page-two']);
  assert.equal(JSON.stringify(available).includes('page-token'), false);
  const selected = await fetch(`${base}/oauth/selections/${selectionToken}`, { method: 'POST', headers: company, body: JSON.stringify({ providerAccountIds: ['page-two'] }) });
  assert.equal(selected.status, 201);
  const connections = await (await fetch(`${base}/connections`, { headers: company })).json();
  assert.deepEqual(connections.connections.map((item: { providerAccountId: string }) => item.providerAccountId), ['page-two']);
  assert.equal((await fetch(`${base}/oauth/selections/${selectionToken}`, { method: 'POST', headers: company, body: JSON.stringify({ providerAccountIds: ['page-two'] }) })).status, 404);
  const persisted = readFileSync(dataFile, 'utf8');
  for (const secret of ['short-user-token', 'long-user-token', 'page-token-one', 'page-token-two', 'meta-secret']) assert.equal(persisted.includes(secret), false);
});

test('token encryption authenticates ciphertext and provider capabilities follow granted scopes', () => {
  const cipher = createTokenCipher(Buffer.alloc(32, 9).toString('base64url'))!;
  const encrypted = cipher.encrypt('server-only-token');
  assert.equal(encrypted.includes('server-only-token'), false);
  assert.equal(cipher.decrypt(encrypted), 'server-only-token');
  const parts = encrypted.split(':');
  const ciphertext = Buffer.from(parts.at(-1)!, 'base64url');
  ciphertext[0] ^= 1;
  parts[parts.length - 1] = ciphertext.toString('base64url');
  assert.throws(() => cipher.decrypt(parts.join(':')));
  const oldKey = Buffer.alloc(32, 3).toString('base64url');
  const newKey = Buffer.alloc(32, 4).toString('base64url');
  const oldCipher = createTokenCipher(oldKey)!;
  const oldPayload = oldCipher.encrypt('rotatable-token');
  const rotatedCipher = createTokenCipher(newKey, [oldKey])!;
  assert.equal(rotatedCipher.decrypt(oldPayload), 'rotatable-token');
  assert.throws(() => oldCipher.decrypt(rotatedCipher.encrypt('new-token')));

  const providers = socialProviderRegistry();
  assert.deepEqual([...providers.keys()], ['instagram', 'facebook', 'tiktok', 'youtube', 'linkedin', 'threads', 'pinterest', 'x']);
  assert.equal(providers.get('youtube')!.capabilities(['https://www.googleapis.com/auth/youtube.upload']).canPublishVideo, false);
  assert.equal(providers.get('youtube')!.capabilities(['https://www.googleapis.com/auth/youtube.readonly']).canPublishVideo, false);
  assert.equal(providers.get('youtube')!.capabilities(['https://www.googleapis.com/auth/youtube.readonly']).canReadAnalytics, true);
  const youtubeAuthorization = new URL(providers.get('youtube')!.authorizationUrl({
    credentials: { clientId: 'youtube-test', clientSecret: 'server-secret', redirectUri: 'http://localhost/callback' },
    redirectUri: 'http://localhost/callback', state: 'test-state', codeChallenge: 'test-challenge',
  }));
  assert.equal(youtubeAuthorization.searchParams.get('scope'), 'https://www.googleapis.com/auth/youtube.readonly');
  assert.equal(providers.get('instagram')!.capabilities(['instagram_manage_insights']).canReadAnalytics, true);
  assert.equal(providers.get('tiktok')!.capabilities(['user.info.basic']).canReadProfile, true);
  assert.equal(providers.get('linkedin')!.capabilities(['w_member_social']).canPublishText, true);
  assert.equal(providers.get('threads')!.capabilities(['threads_content_publish']).canPublishImage, true);
  assert.equal(providers.get('pinterest')!.capabilities(['pins:write']).canPublishImage, true);
  assert.equal(providers.get('x')!.capabilities(['tweet.write', 'media.write']).canPublishVideo, true);

  assert.throws(() => validatePublishRequest({ kind: 'image', mediaUrls: ['http://unsafe.example/image.png'] }, { ...emptyCapabilities(), canPublishImage: true }), /SOCIAL_MEDIA_URL_INVALID/);
  assert.throws(() => validatePublishRequest({ kind: 'story' }, emptyCapabilities()), /SOCIAL_CAPABILITY_UNAVAILABLE/);
});

test('providers remain unavailable until client id, secret and exact redirect URI are all configured', t => {
  const keys = ['TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET', 'TIKTOK_REDIRECT_URI'] as const;
  const previous = new Map(keys.map(key => [key, process.env[key]]));
  t.after(() => previous.forEach((value, key) => value === undefined ? delete process.env[key] : process.env[key] = value));
  process.env.TIKTOK_CLIENT_KEY = 'configured-client';
  process.env.TIKTOK_CLIENT_SECRET = 'configured-secret';
  delete process.env.TIKTOK_REDIRECT_URI;
  assert.equal(socialProviderRegistry().get('tiktok')!.credentials(), null);
  process.env.TIKTOK_REDIRECT_URI = 'http://localhost:3000/api/integrations/oauth/callback';
  assert.equal(socialProviderRegistry().get('tiktok')!.credentials()?.redirectUri, process.env.TIKTOK_REDIRECT_URI);
});

test('Meta exchanges the authorization code for a long-lived server-side token', async t => {
  const keys = ['META_APP_ID', 'META_APP_SECRET', 'META_REDIRECT_URI'] as const;
  const previous = new Map(keys.map(key => [key, process.env[key]]));
  t.after(() => previous.forEach((value, key) => value === undefined ? delete process.env[key] : process.env[key] = value));
  process.env.META_APP_ID = 'meta-test-app';
  process.env.META_APP_SECRET = 'meta-test-secret';
  process.env.META_REDIRECT_URI = 'http://localhost:3000/api/integrations/oauth/callback';
  const requests: URL[] = [];
  const fetcher = (async (input: string | URL | Request) => {
    const url = new URL(String(input));
    requests.push(url);
    return url.searchParams.get('grant_type') === 'fb_exchange_token'
      ? json({ access_token: 'long-lived-token', expires_in: 5_184_000 })
      : json({ access_token: 'short-lived-token', expires_in: 3_600 });
  }) as typeof fetch;
  const provider = socialProviderRegistry().get('facebook')!;
  const token = await provider.exchangeCode({ credentials: provider.credentials()!, fetch: fetcher, signal: AbortSignal.timeout(1_000) }, {
    code: 'authorization-code', redirectUri: process.env.META_REDIRECT_URI,
  });
  assert.equal(token.accessToken, 'long-lived-token');
  assert.equal(requests.length, 2);
  assert.equal(requests[1].searchParams.get('grant_type'), 'fb_exchange_token');
  assert.equal(requests[1].searchParams.get('fb_exchange_token'), 'short-lived-token');
});

test('provider HTTP retries safe transient reads at most three times and never retries writes implicitly', async () => {
  let reads = 0;
  const readFetcher = (async () => {
    reads += 1;
    return reads < 3 ? json({ error: { code: 'rate_limit' } }, 429) : json({ ok: true });
  }) as typeof fetch;
  assert.deepEqual(await providerJson(readFetcher, 'https://provider.example/resource'), { ok: true });
  assert.equal(reads, 3);

  let writes = 0;
  const writeFetcher = (async () => { writes += 1; return json({ error: { code: 'unavailable' } }, 503); }) as typeof fetch;
  await assert.rejects(() => providerJson(writeFetcher, 'https://provider.example/publish', { method: 'POST' }), /SOCIAL_PROVIDER_UNAVAILABLE/);
  assert.equal(writes, 1);
});

test('social webhook verification requires the exact raw body and constant-time challenge match', () => {
  const secret = 'webhook-test-secret';
  const rawBody = Buffer.from('{"event":"updated","id":"social-1"}');
  const signature = `sha256=${createHmac('sha256', secret).update(rawBody).digest('hex')}`;
  assert.equal(verifySocialWebhookSignature({ rawBody, secret, signature }), true);
  assert.equal(verifySocialWebhookSignature({ rawBody: Buffer.from('{"id":"social-1","event":"updated"}'), secret, signature }), false);
  assert.equal(verifySocialWebhookSignature({ rawBody, secret, signature: 'sha256=invalid' }), false);
  assert.equal(verifySocialWebhookChallenge('challenge-token', 'challenge-token'), true);
  assert.equal(verifySocialWebhookChallenge('challenge-token', 'other-token'), false);
});

test('official YouTube and X profile snapshots preserve provider metrics and only map equivalent totals', async () => {
  const connection = (provider: 'youtube' | 'x', providerAccountId: string): StoredSocialConnection => ({
    id: `social-${provider}`, ownerType: 'workspace', ownerId: 'ws-analytics', provider, providerAccountId,
    displayName: provider, accessTokenEncrypted: 'encrypted', scopes: [], status: 'connected', capabilities: emptyCapabilities(),
    providerMetadata: {}, createdAt: '2026-09-01T00:00:00.000Z', updatedAt: '2026-09-01T00:00:00.000Z',
  });
  const registry = socialProviderRegistry();
  const youtube = registry.get('youtube')!;
  const youtubeAnalytics = await youtube.analytics!({
    credentials: { clientId: 'test', clientSecret: 'test', redirectUri: 'http://localhost/callback' }, signal: AbortSignal.timeout(1_000),
    fetch: (async () => json({ items: [{ statistics: { subscriberCount: '1250', viewCount: '8400', videoCount: '19' } }] })) as typeof fetch,
  }, { accessToken: 'token', scopes: [] }, connection('youtube', 'channel-1'), { from: '2026-09-01', to: '2026-09-13' });
  assert.deepEqual(youtubeAnalytics.metrics, { followers: 1250, views: 8400 });
  assert.deepEqual(youtubeAnalytics.providerMetrics, { subscriberCount: 1250, viewCount: 8400, videoCount: 19 });

  const x = registry.get('x')!;
  const xAnalytics = await x.analytics!({
    credentials: { clientId: 'test', clientSecret: 'test', redirectUri: 'http://localhost/callback' }, signal: AbortSignal.timeout(1_000),
    fetch: (async () => json({ data: { public_metrics: { followers_count: 240, following_count: 31, tweet_count: 82 } } })) as typeof fetch,
  }, { accessToken: 'token', scopes: [] }, connection('x', 'x-user-1'), { from: '2026-09-01', to: '2026-09-13' });
  assert.deepEqual(xAnalytics.metrics, { followers: 240 });
  assert.deepEqual(xAnalytics.providerMetrics, { followers_count: 240, following_count: 31, tweet_count: 82 });
});
