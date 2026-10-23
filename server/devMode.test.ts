import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { mkdtempSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import path from 'node:path';
import { request as httpRequest } from 'node:http';
import { createGovernanceRouter } from './governance';
import { devConfiguration, devNetworkBoundary, isLocalDevRequest } from './devMode';
import { DEV_WORKSPACE_ID, DEV_USER_ID, DEV_CLIENT_ID } from '../src/development/contracts';
import { FinancialAdmission } from './finance/admission';
import { providerResponse } from './integrations/http';
import { validateProductionEnvironment } from './production';

function environment(root: string) {
  return { NODE_ENV: 'development', PORT: '3018', CLICKO_DEV_MODE: 'true', CLICKO_PREVIEW_HOST: '127.0.0.1',
    CLICKO_LOCAL_DATA_DIR: root, CLICKO_GOVERNANCE_DATA_FILE: path.join(root, 'governance.json'),
    CLICKO_SOCIAL_DATA_FILE: path.join(root, 'social.json'), CLICKO_STUDIOS_DATA_DIR: path.join(root, 'studios'),
    CLICKO_KLIC_DATA_FILE: path.join(root, 'klic.json'), CLICKO_CONVERSATIONS_DIR: path.join(root, 'conversations'),
    CLICKO_RADAR_DATA_FILE: path.join(root, 'radar.json'), CLICKO_STUDIOS_ORIGIN: 'http://127.0.0.1:8018',
    CLICKO_NODE_OUTBOUND_ENABLED: 'false', STUDIO_NODE_OUTBOUND_ENABLED: 'false', KLIC_GOOGLE_TTS_ENABLED: 'false',
    CLICKO_DEV_AUTH_BYPASS: 'false', PUBLIC_APP_URL: 'http://127.0.0.1:3018' };
}

test('DEV configuration fails closed for production, remote binding, remote services and commercial stores', () => {
  const env = environment(path.resolve('.codex-runtime/clicko-dev-config-test'));
  assert.ok(devConfiguration(env));
  assert.equal(devConfiguration({ ...env, CLICKO_DEV_MODE: 'false' }), undefined);
  for (const patch of [
    { NODE_ENV: 'production' }, { NODE_ENV: 'test' }, { CLICKO_PREVIEW_HOST: '0.0.0.0' },
    { CLICKO_PREVIEW_HOST: '192.168.0.1' }, { CLICKO_DEV_AUTH_BYPASS: 'true' },
    { CLICKO_NODE_OUTBOUND_ENABLED: 'true' }, { PUBLIC_APP_URL: 'https://preview.example.test' },
    { CLICKO_STUDIOS_ORIGIN: 'https://api.example.test' },
    { CLICKO_LOCAL_DATA_DIR: path.resolve('.clicko-data') },
    { CLICKO_GOVERNANCE_DATA_FILE: path.resolve('.clicko-data/governance.json') },
  ]) assert.throws(() => devConfiguration({ ...env, ...patch }));
  assert.throws(() => devConfiguration(env, true), /DEV_REQUIRES_LOCAL_SOURCE_DEVELOPMENT/);
});

test('DEV identity is persisted once and requires a real server-issued local session, not identity headers', async t => {
  const parent = path.resolve('.codex-runtime'); mkdirSync(parent, { recursive: true });
  const root = mkdtempSync(path.join(parent, 'clicko-dev-auth-test-'));
  const env = environment(root), saved = Object.fromEntries(Object.keys(env).map(key => [key, process.env[key]]));
  Object.assign(process.env, env);
  const app = express(); app.use(devNetworkBoundary); app.use(express.json());
  app.use('/api/governance', createGovernanceRouter());
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(async () => {
    await new Promise<void>(resolve => server.close(() => resolve()));
    for (const [key, value] of Object.entries(saved)) if (value === undefined) delete process.env[key]; else process.env[key] = value;
    if (path.dirname(root) === parent && path.basename(root).startsWith('clicko-dev-auth-test-')) rmSync(root, { recursive: true, force: true });
  });
  const base = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  const request = (route: string, cookie = '', extra: Record<string, string> = {}, method = 'GET'): Promise<Response> => {
    const headers = { ...(cookie ? { cookie } : {}), ...extra };
    // Fetch normalizes Host to the URL. Use a real raw HTTP client for this
    // adversarial case so the test actually sends the forged Host header.
    if (extra.host) return new Promise((resolve, reject) => {
      const outgoing = httpRequest(base + '/api/governance' + route, { method, headers }, incoming => {
        let body = ''; incoming.setEncoding('utf8'); incoming.on('data', chunk => { body += chunk; });
        incoming.on('end', () => {
          const responseHeaders = new Headers();
          for (const [key, value] of Object.entries(incoming.headers)) if (value !== undefined)
            for (const item of Array.isArray(value) ? value : [value]) responseHeaders.append(key, item);
          resolve(new Response(body, { status: incoming.statusCode, headers: responseHeaders }));
        });
      });
      outgoing.once('error', reject); outgoing.end();
    });
    return fetch(base + '/api/governance' + route, { method, headers });
  };
  assert.equal((await request('/workspace', '', { 'x-user-id': DEV_USER_ID, 'x-workspace-id': DEV_WORKSPACE_ID })).status, 401);
  const response = await request('/auth/session');
  assert.equal(response.status, 200);
  assert.match(response.headers.get('set-cookie')!, /HttpOnly; SameSite=Strict; Max-Age=28800/);
  const cookie = response.headers.get('set-cookie')!.split(';')[0], payload = await response.json();
  assert.equal(payload.user.id, DEV_USER_ID);
  assert.equal(payload.account.workspaceId, DEV_WORKSPACE_ID);
  assert.equal(payload.account.planName, 'Desenvolvimento');
  assert.equal(payload.development.clientId, DEV_CLIENT_ID);
  assert.equal((await (await request('/workspace', cookie)).json()).id, DEV_WORKSPACE_ID);
  const clients = await (await request('/clients', cookie)).json();
  assert.equal(clients.length, 1); assert.equal(clients[0].id, DEV_CLIENT_ID);
  const session = await (await request('/session', cookie)).json();
  assert.ok(session.currentUser.modules.includes('create-video') && session.currentUser.modules.includes('ai-chat'));
  assert.ok(session.currentUser.permissions.includes('members.manage'));
  assert.equal((await request('/workspace', 'clicko_dev_session=forged')).status, 401);
  for (const headers of [{ origin: 'https://attacker.example' }, { origin: 'null' }, { host: 'attacker.example' },
    { 'x-forwarded-for': '127.0.0.1' }, { forwarded: 'for=127.0.0.1' }, { 'sec-fetch-site': 'cross-site' }]) {
    assert.equal((await request('/workspace', cookie, headers)).status, 403, JSON.stringify(headers));
    const rejected = await request('/auth/session', '', headers);
    assert.equal(rejected.status, 403); assert.equal(rejected.headers.get('set-cookie'), null);
  }
  assert.equal(isLocalDevRequest({ socket: { localAddress: '127.0.0.1', remoteAddress: '192.168.1.5' } } as express.Request), false);
  assert.equal((await request('/billing/checkout', cookie, {}, 'POST')).status, 403);
  let externalCalls = 0;
  const transport = (async () => { externalCalls++; throw new Error('External request forbidden'); }) as typeof fetch;
  await assert.rejects(new FinancialAdmission(transport).reserve({ provider: 'google.klic', model: 'test', operation: 'generate', fingerprint: 'test' }), /FINANCE_OUTBOUND_DISABLED/);
  await assert.rejects(providerResponse(transport, 'https://example.test'), /DEV_EXTERNAL_INTEGRATION_DISABLED/);
  assert.equal(externalCalls, 0);
  // Reprovisioning in the same store does not duplicate the reserved records.
  createGovernanceRouter();
  const stored = JSON.parse(readFileSync(path.join(root, 'governance.json'), 'utf8'));
  assert.equal(stored.workspaces.length, 1); assert.equal(stored.users.length, 1); assert.equal(stored.registeredClients.length, 1);
  assert.equal(stored.authCredentials.length, 0); assert.equal(stored.authSessions.length, 0);
  const now = Date.now;
  Date.now = () => now() + 9 * 60 * 60 * 1000;
  try { assert.equal((await request('/workspace', cookie)).status, 401); } finally { Date.now = now; }
  // Off-mode must reject even a fresh, otherwise valid DEV session, not only
  // the expired/revoked cookie used in the preceding expiration assertion.
  const fresh = (await request('/auth/session')).headers.get('set-cookie')!.split(';')[0];
  assert.equal((await request('/workspace', fresh)).status, 200);
  process.env.CLICKO_DEV_MODE = 'false';
  assert.equal((await request('/workspace', fresh)).status, 401);
  assert.equal((await request('/auth/session', '', { 'x-clicko-dev-mode': 'true', 'x-user-id': DEV_USER_ID })).status, 401);
  process.env.CLICKO_DEV_MODE = 'true'; process.env.NODE_ENV = 'production';
  assert.throws(() => validateProductionEnvironment(), /DEV_FORBIDDEN_IN_PRODUCTION/);
});
