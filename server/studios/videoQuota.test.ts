import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { authenticate, createGovernanceRouter } from '../governance';
import { createStudiosProxy } from './proxy';
import { retiredEditing } from './legacyEditing';

test('only generated scenes consume video minutes; holds, retries, release and exact settlement persist', async t => {
  const directory = mkdtempSync(path.join(tmpdir(), 'clicko-video-quota-'));
  const filename = path.join(directory, 'governance.json');
  const jobs = new Map<string, any>();
  let lost = false;
  let deny = false;
  const app = express();
  app.use('/governance', express.json(), createGovernanceRouter({ dataFile: filename }));
  app.use('/api/v1/studios/v1', createStudiosProxy({ secret: 'test-bridge-key-'.repeat(4), fetch: async (url, init) => {
    const request = new URL(String(url));
    const headers = new Headers(init?.headers);
    if (init?.method === 'GET') return Response.json([...jobs.values()].find(job => request.pathname.endsWith(job.id)));
    if (deny) return Response.json({ detail: 'not configured' }, { status: 422 });
    const body = JSON.parse(init!.body as string);
    const key = headers.get('idempotency-key')!;
    const token = JSON.parse(Buffer.from(headers.get('authorization')!.split('.')[1], 'base64url').toString());
    if (body.operation === 'generate_video') {
      assert.match(token.mediaAdmission.id, /^[a-f0-9]{64}$/);
      assert.equal(token.mediaAdmission.key, key);
      assert.equal(token.mediaAdmission.seconds, 8);
    } else assert.equal(token.mediaAdmission, undefined);
    if (!jobs.has(key)) jobs.set(key, { id: randomUUID(), jobType: 'editing_gemini', documentId: 'doc-1', idempotencyKey: key,
      status: 'queued', request: { input: body } });
    if (lost) throw new Error('lost acknowledgement');
    return Response.json(jobs.get(key), { status: 202 });
  } }));
  app.use(express.json());
  app.post('/image-edit', authenticate, retiredEditing('create-image'));
  app.post('/video-edit', authenticate, retiredEditing('create-video'));
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(async () => {
    await new Promise<void>(resolve => server.close(() => resolve()));
    if (path.dirname(directory) === path.resolve(tmpdir()) && path.basename(directory).startsWith('clicko-video-quota-')) rmSync(directory, { recursive: true, force: true });
  });
  const origin = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  const headers = { 'content-type': 'application/json', 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master', 'x-clicko-studio-module': 'create-video' };
  const used = async () => (await (await fetch(origin + '/governance/usage', { headers })).json()).resources.video_minutes.used as number;
  const send = (key: string, operation = 'generate_video') => fetch(origin + '/api/v1/studios/v1/documents/doc-1/editing-ai-jobs', {
    method: 'POST', headers: { ...headers, 'idempotency-key': key }, body: JSON.stringify({ expectedDocumentRevision: 1, prompt: 'Cena', operation, durationSeconds: 8 }),
  });
  const initial = await used();
  assert.equal((await send('editor-edit-001', 'edit_video')).status, 202);
  assert.equal(await used(), initial);
  lost = true;
  assert.equal((await send('generated-scene-001')).status, 503);
  assert.ok(Math.abs(await used() - initial - 8.15 / 60) < 1e-8);
  lost = false;
  assert.equal((await send('generated-scene-001')).status, 202);
  assert.ok(Math.abs(await used() - initial - 8.15 / 60) < 1e-8);
  const job = jobs.get('generated-scene-001');
  job.status = 'succeeded';
  job.result = { assetId: 'validated-video', checksumSha256: 'a'.repeat(64), generatedVideoSeconds: 8 };
  for (let index = 0; index < 2; index++) await fetch(origin + '/api/v1/studios/v1/jobs/' + job.id, { headers });
  assert.ok(Math.abs(await used() - initial - 8 / 60) < 1e-8);
  assert.equal(JSON.parse(readFileSync(filename, 'utf8')).studioVideoUsageReceipts[0].status, 'settled');
  deny = true;
  assert.equal((await send('rejected-scene-001')).status, 422);
  assert.ok(Math.abs(await used() - initial - 8 / 60) < 1e-8);
  deny = false;
  const allowance = await used();
  const policy = await fetch(origin + '/governance/usage/policy', { method: 'PATCH', headers,
    body: JSON.stringify({ allocationMode: 'member_limits', memberId: 'usr-master', limits: { video_minutes: allowance } }) });
  assert.equal(policy.status, 200);
  assert.equal((await send('member-quota-blocked')).status, 409);
  assert.equal(jobs.has('member-quota-blocked'), false);
  for (const endpoint of ['image-edit', 'video-edit']) {
    const response = await fetch(origin + '/' + endpoint, { method: 'POST', headers, body: JSON.stringify({ sourceImage: 'original', videoUrl: 'original' }) });
    assert.equal(response.status, 410);
    assert.equal((await response.json()).success, false);
  }
  assert.ok(Math.abs(await used() - initial - 8 / 60) < 1e-8);
});
