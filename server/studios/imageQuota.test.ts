import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import express from 'express';
import { createGovernanceRouter } from '../governance';
import { createStudiosProxy } from './proxy';

test('image admission durably meters accepted jobs, preserves uncertain reservations and never double charges a replay', async t => {
  const temporaryRoot = path.resolve(tmpdir());
  const folder = mkdtempSync(path.join(temporaryRoot, 'clicko-image-quota-'));
  const filename = path.join(folder, 'governance.json');
  const jobs = new Map<string, any>();
  let mode: number | 'accept' | 'accept-lost' | 'settle-failure' | 'invalid-proof' = 'accept';
  let calls = 0;
  let created = 0;
  const app = express();
  app.use('/governance', express.json(), createGovernanceRouter({ dataFile: filename }));
  // Like server.ts, the Studio proxy is mounted BEFORE any global JSON parser.
  app.use('/api/v1/studios/v1', createStudiosProxy({ secret: 'test-only-studio-bridge-key-at-least-32-characters', fetch: async (url, init) => {
    calls++;
    const target = new URL(String(url));
    if (target.pathname.endsWith('/cancel') || target.pathname.endsWith('/retry'))
      return Response.json({ status: target.pathname.endsWith('/cancel') ? 'cancelled' : 'queued' });
    const headers = new Headers(init?.headers);
    const token = headers.get('authorization')!.slice(7).split('.')[1];
    const claims = JSON.parse(Buffer.from(token, 'base64url').toString());
    const key = headers.get('idempotency-key')!;
    const scope = JSON.stringify([claims.workspaceId, claims.clientId, key]);
    if (typeof mode === 'number') return Response.json({ detail: { code: 'fixture_rejection' } }, { status: mode });
    if (mode === 'invalid-proof') return Response.json({ ready: true });
    const body = JSON.parse(init!.body as string);
    assert.ok(body.prompt);
    if (!jobs.has(scope)) {
      created++;
      jobs.set(scope, { id: randomUUID(), documentId: decodeURIComponent(target.pathname.split('/').at(-2)!), idempotencyKey: key, jobType: 'editing_gemini', request: { input: body }, status: 'failed' });
    }
    if (mode === 'accept-lost') throw new TypeError('fixture loses transport after job commit');
    if (mode === 'settle-failure') writeFileSync(filename + '.lock', 'fixture owns this lock');
    return Response.json(jobs.get(scope), { status: 202 });
  } }));
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(async () => {
    await new Promise<void>(resolve => server.close(() => resolve()));
    if (path.dirname(folder) === temporaryRoot && path.basename(folder).startsWith('clicko-image-quota-')) rmSync(folder, { recursive: true, force: true });
  });
  const origin = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  const rootHeaders = { 'content-type': 'application/json', 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master' };
  const personalHeaders = { ...rootHeaders, 'x-workspace-id': 'ws-personal', 'x-user-id': 'usr-master-personal' };
  const body = { schemaVersion: 'studio.editing-ai-request.v1', expectedDocumentRevision: 1, operation: 'generate_image', prompt: 'Fotografia de um produto', referenceAssetIds: [], preserve: [] };
  const send = (key: string, value: unknown = body, headers: Record<string, string> = rootHeaders, document = 'document-1') => fetch(`${origin}/api/v1/studios/v1/documents/${document}/editing-ai-jobs`, { method: 'POST', headers: { ...headers, 'x-clicko-studio-module': 'create-image', 'idempotency-key': key }, body: JSON.stringify(value) });
  const call = (route: string, value: unknown) => fetch(origin + '/governance' + route, { method: route === '/usage/policy' ? 'PATCH' : 'POST', headers: rootHeaders, body: JSON.stringify(value) });
  const used = async (headers = rootHeaders) => (await (await fetch(origin + '/governance/usage', { headers })).json()).resources.image_generations.used as number;
  const saved = () => JSON.parse(readFileSync(filename, 'utf8'));

  await t.test('accepted failures/cancellations still consume one unit; HTTP and job retries do not duplicate it', async () => {
    const result = await send('accepted-request-001');
    assert.equal(result.status, 202);
    const job = await result.json();
    assert.equal(job.status, 'failed');
    assert.equal(await used(), 1);
    assert.equal(saved().usagePools.find((pool: any) => pool.workspaceId === 'ws-1').resources.image_generations.used, 1);
    assert.equal(saved().studioImageUsageReceipts[0].status, 'accepted');
    assert.equal((await send('accepted-request-001', { preserve: [], ...body })).status, 202);
    for (const operation of ['cancel', 'retry'])
      assert.equal((await fetch(`${origin}/api/v1/studios/v1/jobs/${job.id}/${operation}`, { method: 'POST', headers: { ...rootHeaders, 'x-clicko-studio-module': 'create-image' }, body: operation === 'cancel' ? JSON.stringify({ reason: 'Teste' }) : undefined })).status, 200);
    assert.equal(await used(), 1);
    assert.equal(created, 1);
    const before = calls;
    assert.equal((await send('accepted-request-001', { ...body, prompt: 'Outro pedido' })).status, 409);
    assert.equal((await send('accepted-request-001', body, rootHeaders, 'another-document')).status, 409);
    assert.equal(calls, before);
  });

  await t.test('confirmed admission rejection or invalid JSON never consumes quota', async () => {
    const baseline = await used();
    for (const status of [400, 401, 403, 404, 409, 413, 415, 422, 429]) {
      mode = status;
      assert.equal((await send(`rejected-request-${status}`)).status, status);
      assert.equal(await used(), baseline);
    }
    const before = calls;
    assert.equal((await send('short')).status, 422);
    assert.equal((await send('invalid-operation-001', { ...body, operation: 'generate_video' })).status, 422);
    const invalid = await fetch(`${origin}/api/v1/studios/v1/documents/document-1/editing-ai-jobs`, { method: 'POST', headers: { ...rootHeaders, 'x-clicko-studio-module': 'create-image', 'idempotency-key': 'invalid-json-001' }, body: '{' });
    assert.equal(invalid.status, 400);
    assert.equal(calls, before);
    assert.equal(await used(), baseline);
  });

  await t.test('unknown transport outcome and ambiguous 5xx hold the exact reservation until reconciled', async () => {
    const baseline = await used();
    mode = 'accept-lost';
    assert.equal((await send('uncertain-request-001')).status, 503);
    assert.equal(await used(), baseline + 1);
    const count = created;
    mode = 'accept';
    assert.equal((await send('uncertain-request-001')).status, 202);
    assert.equal(created, count);
    assert.equal(await used(), baseline + 1);
    mode = 503;
    assert.equal((await send('unconfirmed-request-001')).status, 503);
    assert.equal(await used(), baseline + 2);
    mode = 422;
    assert.equal((await send('unconfirmed-request-001')).status, 422);
    assert.equal(await used(), baseline + 1);
  });

  await t.test('concurrent same-key requests serialize and consume a single unit', async () => {
    mode = 'accept';
    const baseline = await used();
    const count = created;
    const results = await Promise.all([send('concurrent-request-001'), send('concurrent-request-001')]);
    assert.deepEqual(results.map(result => result.status), [202, 202]);
    assert.equal(await used(), baseline + 1);
    assert.equal(created, count + 1);
    assert.equal((await results[0].json()).id, (await results[1].json()).id);
  });

  await t.test('encoded route segments cannot bypass quota and unconfirmed success cannot be presented as admission', async () => {
    const baseline = await used();
    mode = 'invalid-proof';
    assert.equal((await send('invalid-proof-001')).status, 502);
    assert.equal(await used(), baseline + 1);
    mode = 422;
    assert.equal((await send('invalid-proof-001')).status, 422);
    assert.equal(await used(), baseline);
    mode = 'accept';
    const result = await fetch(origin + '/api/v1/studios/v1/documen%74s/document-1/editing%2Dai-jobs', { method: 'POST', headers: { ...rootHeaders, 'x-clicko-studio-module': 'create-image', 'idempotency-key': 'encoded-route-001' }, body: JSON.stringify(body) });
    assert.equal(result.status, 202);
    assert.equal(await used(), baseline + 1);
    assert.equal((await send('encoded-route-001')).status, 202);
    assert.equal(await used(), baseline + 1);
  });

  await t.test('storage failures block admission or retain the durable reservation without double billing', async () => {
    const baseline = await used();
    const before = calls;
    writeFileSync(filename + '.lock', 'fixture owns this lock');
    const blocked = await send('storage-blocked-001');
    assert.equal(blocked.status, 503);
    assert.equal((await blocked.json()).code, 'USAGE_PERSISTENCE_UNAVAILABLE');
    assert.equal(calls, before);
    assert.equal(await used(), baseline);
    unlinkSync(filename + '.lock');
    mode = 'settle-failure';
    assert.equal((await send('settle-recovery-001')).status, 503);
    assert.equal(await used(), baseline + 1);
    assert.equal(saved().studioImageUsageReceipts.at(-1).status, 'reserved');
    unlinkSync(filename + '.lock');
    mode = 'accept';
    assert.equal((await send('settle-recovery-001')).status, 202);
    assert.equal(await used(), baseline + 1);
    assert.equal(saved().studioImageUsageReceipts.at(-1).status, 'accepted');
  });

  await t.test('member limit and shared plan limit are enforced before forwarding, even concurrently', async () => {
    const baseline = await used();
    assert.equal((await call('/usage/policy', { allocationMode: 'member_limits', memberId: 'usr-master', limits: { image_generations: baseline + 1 } })).status, 200);
    mode = 'accept';
    assert.equal((await send('member-allowed-001')).status, 202);
    const before = calls;
    const blocked = await send('member-blocked-001');
    assert.equal(blocked.status, 409);
    assert.equal((await blocked.json()).code, 'MEMBER_USAGE_EXHAUSTED');
    assert.equal(calls, before);
    assert.equal((await call('/usage/policy', { allocationMode: 'shared' })).status, 200);
    const pool = await (await fetch(origin + '/governance/usage', { headers: rootHeaders })).json();
    assert.equal((await call('/usage/consume', { resource: 'image_generations', amount: pool.resources.image_generations.limit - pool.resources.image_generations.used - 1 })).status, 200);
    const count = calls;
    const results = await Promise.all([send('plan-last-unit-001'), send('plan-exhausted-001')]);
    assert.deepEqual(results.map(response => response.status).sort(), [202, 409]);
    assert.equal(calls, count + 1);
    // Already admitted requests remain recoverable at zero remaining quota.
    assert.equal((await send('accepted-request-001')).status, 202);
  });

  await t.test('personal/company and client scopes do not share idempotency identities', async () => {
    assert.equal(await used(personalHeaders), 0);
    assert.equal((await send('accepted-request-001', body, personalHeaders)).status, 202);
    assert.equal(await used(personalHeaders), 1);
    const client = await call('/clients/register', { id: 'client-image-quota', name: 'Cliente de teste' });
    assert.equal(client.status, 201);
    const record = await client.json();
    // The company quota is exhausted; another client cannot bypass the shared pool.
    const before = calls;
    assert.equal((await send('accepted-request-001', body, { ...rootHeaders, 'x-clicko-client-id': record.id })).status, 409);
    assert.equal(calls, before);
  });

  await t.test('persistent receipts survive a fresh process and replay without another quota deduction', async () => {
    const directory = typeof __dirname === 'string' ? __dirname : path.resolve('server/studios');
    const compiled = path.resolve(directory, '../governance.js');
    const governance = existsSync(compiled) ? compiled : path.resolve(directory, '../governance.ts');
    const receipt = saved().studioImageUsageReceipts[0];
    const child = spawnSync(process.execPath, [...(governance.endsWith('.ts') ? ['--import', 'tsx'] : []), '-e', `
      const { createGovernanceRouter, reserveStudioImageUsage } = require(${JSON.stringify(governance)});
      createGovernanceRouter({ dataFile: ${JSON.stringify(filename)} });
      const id = reserveStudioImageUsage({workspaceId:'ws-1',user:{id:'usr-master'}}, ${JSON.stringify(receipt.id)}, ${JSON.stringify(receipt.fingerprint)});
      process.stdout.write(id);
    `], { encoding: 'utf8', timeout: 20000, env: process.env });
    assert.equal(child.status, 0, child.stderr);
    assert.equal(child.stdout, receipt.id);
    const before = saved().usagePools.find((pool: any) => pool.workspaceId === 'ws-1').resources.image_generations.used;
    assert.equal(before, 500);
    assert.equal(saved().studioImageUsageReceipts.filter((item: any) => item.id === receipt.id).length, 1);
  });
});
