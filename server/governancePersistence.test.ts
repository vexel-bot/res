import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { mkdtempSync, readFileSync, rmSync, unlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createGovernanceRouter } from './governance';

test('governance persists before HTTP success, survives process restart, and rolls back failed writes', async t => {
  const temporaryRoot = path.resolve(tmpdir());
  const folder = mkdtempSync(path.join(temporaryRoot, 'clicko-governance-test-'));
  const filename = path.join(folder, 'governance.json');
  const app = express(); app.use(express.json());
  app.use(createGovernanceRouter({ dataFile: filename }));
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(async () => {
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    if (path.dirname(folder) === temporaryRoot && path.basename(folder).startsWith('clicko-governance-test-')) rmSync(folder, { recursive: true, force: true });
  });
  const base = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  const headers = { 'Content-Type': 'application/json', 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master' };
  const create = (contentId: string) => fetch(base + '/approvals', { method: 'POST', headers, body: JSON.stringify({ contentId, title: 'Persisted test content', copy: 'Only fixture data', platform: 'instagram', format: 'post' }) });
  const created = await create('persistent-fixture');
  assert.equal(created.status, 201);
  const approval = await created.json();
  assert.equal(JSON.parse(readFileSync(filename, 'utf8')).approvals[0].id, approval.id);
  const scheduledAt = new Date(Date.now() + 86400000).toISOString();
  const moved = await fetch(base + '/approvals/' + approval.id + '/actions', { method: 'POST', headers, body: JSON.stringify({ action: 'reschedule', scheduledAt }) });
  assert.equal(moved.status, 200);

  // A completely new Node process has no access to this process's memory arrays.
  const child = spawnSync(process.execPath, ['-e', `
    const express = require('express');
    const { createGovernanceRouter } = require(${JSON.stringify(path.join(__dirname, 'governance.js'))});
    const app = express(); app.use(express.json());
    app.use(createGovernanceRouter({ dataFile: ${JSON.stringify(filename)} }));
    const server = app.listen(0, '127.0.0.1', async () => {
      try {
        const response = await fetch('http://127.0.0.1:' + server.address().port + '/approvals', { headers: ${JSON.stringify(headers)} });
        const data = await response.json();
        process.stdout.write(JSON.stringify({ status: response.status, ids: data.map(item => item.id), scheduledAt: data[0].scheduledAt, stage: data[0].stage }));
      } catch { process.exitCode = 1; }
      finally { server.close(); }
    });
  `], { encoding: 'utf8', timeout: 15000, env: process.env });
  assert.equal(child.status, 0, child.stderr);
  assert.deepEqual(JSON.parse(child.stdout), { status: 200, ids: [approval.id], scheduledAt, stage: 'pending_approval' });

  const before = readFileSync(filename, 'utf8');
  writeFileSync(filename + '.lock', 'fixture simulates unavailable storage');
  const failed = await create('must-not-exist');
  assert.equal(failed.status, 503);
  assert.match((await failed.json()).error, /estado anterior/);
  assert.equal(readFileSync(filename, 'utf8'), before);
  const records = await (await fetch(base + '/approvals', { headers })).json();
  assert.deepEqual(records.map(item => item.contentId), ['persistent-fixture']);
  unlinkSync(filename + '.lock'); // Only this test's explicitly created lock.
  assert.equal((await create('after-recovery')).status, 201);

  const invited = await fetch(base + '/invites', { method: 'POST', headers, body: JSON.stringify({ name: 'Fixture', email: 'fixture@example.test', modules: ['calendar'] }) });
  assert.equal(invited.status, 201);
  const member = await invited.json();
  assert.equal((await fetch(base + '/users/' + member.id, { method: 'DELETE', headers })).status, 204);
  const saved = JSON.parse(readFileSync(filename, 'utf8'));
  assert.equal(saved.users.some(item => item.id === member.id), false);
  assert.equal(saved.inviteTokens.some(pair => pair[1] === member.id), false);
});
