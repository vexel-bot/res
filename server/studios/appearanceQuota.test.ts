import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import express from 'express';
import { createGovernanceRouter } from '../governance';
import { createStudiosProxy } from './proxy';

test('appearance admission binds the project and never double charges a replay', async t => {
  const temporaryRoot = path.resolve(tmpdir());
  const folder = mkdtempSync(path.join(temporaryRoot, 'clicko-appearance-quota-'));
  const app = express();
  app.use('/governance', express.json(), createGovernanceRouter({ dataFile: path.join(folder, 'governance.json') }));
  let calls = 0;
  let invalidate = false;
  app.use('/api/v1/studios/v1', createStudiosProxy({ secret: 'test-only-studio-bridge-key-at-least-32-characters', fetch: async (_url, init) => {
    calls++;
    const headers = new Headers(init?.headers);
    const claims = JSON.parse(Buffer.from(headers.get('authorization')!.slice(7).split('.')[1], 'base64url').toString());
    const admission = claims.mediaAdmission;
    assert.equal(admission.documentId, 'project-1');
    assert.equal(admission.operation, 'generate_image');
    assert.equal(admission.key, headers.get('idempotency-key'));
    return Response.json({ id: 'job-1', idempotencyKey: admission.key, jobType: 'appearance_image',
      request: { plan: { projectId: invalidate ? 'wrong-project' : 'project-1' }, commercialAdmission: admission }, status: 'queued' }, { status: 202 });
  } }));
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(async () => {
    await new Promise<void>(resolve => server.close(() => resolve()));
    if (path.dirname(folder) === temporaryRoot && path.basename(folder).startsWith('clicko-appearance-quota-')) rmSync(folder, { recursive: true, force: true });
  });
  const base = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  const headers = { 'content-type': 'application/json', 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master', 'x-clicko-studio-module': 'create-image', 'idempotency-key': 'appearance-request-001' };
  const body = { operation: 'generate_image', expectedRevision: 1, direction: 'Pessoa no cenário', planDigestSha256: 'a'.repeat(64) };
  const send = (value: unknown = body, extra = {}) => fetch(`${base}/api/v1/studios/v1/projects/project-1/appearance`, { method: 'POST', headers: { ...headers, ...extra }, body: JSON.stringify(value) });
  const used = async () => (await (await fetch(`${base}/governance/usage`, { headers })).json()).resources.image_generations.used as number;
  assert.equal((await send()).status, 202);
  assert.equal(await used(), 1);
  assert.equal((await send()).status, 202);
  assert.equal(await used(), 1);
  assert.equal((await send({ ...body, direction: 'Outro pedido' })).status, 409);
  assert.equal((await send(body, { 'x-clicko-studio-module': 'create-video' })).status, 422);
  assert.equal(calls, 2);
  invalidate = true;
  assert.equal((await send(body, { 'idempotency-key': 'appearance-request-002' })).status, 502);
  // An ambiguous success retains its reservation for reconciliation.
  assert.equal(await used(), 2);
});
