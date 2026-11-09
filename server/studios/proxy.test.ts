import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import express from 'express';
import { createGovernanceRouter } from '../governance';
import { createStudiosProxy } from './proxy';

test('Studio proxy requires the current Clicko identity and signs only an authorized scoped request', async t => {
  const app = express();
  app.use('/api/governance', createGovernanceRouter({ dataFile: null }));
  const key = 'private-studio-test-secret-with-more-than-32-characters';
  let forwarded: RequestInit | undefined;
  let calls = 0;
  app.use('/api/v1/studios/v1', createStudiosProxy({ secret: key, fetch: async (_url, init) => {
    calls++; forwarded = init;
    return new Response(JSON.stringify({ ready: true }), { headers: { 'content-type': 'application/json' } });
  } }));
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(() => new Promise<void>(resolve => server.close(() => resolve())));
  const url = `http://127.0.0.1:${(server.address() as { port: number }).port}/api/v1/studios/v1/bridge/session`;
  const headers = { 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master', 'x-clicko-studio-module': 'create-image' };
  assert.equal((await fetch(url)).status, 401);
  assert.equal((await fetch(url, { headers: { ...headers, 'x-user-id': 'foreign' } })).status, 401);
  assert.equal((await fetch(url, { headers: { ...headers, 'x-clicko-studio-module': 'dashboard' } })).status, 400);
  assert.equal((await fetch(url, { headers: { ...headers, 'x-clicko-client-id': 'unregistered-client' } })).status, 404);
  assert.equal(calls, 0);
  const result = await fetch(url, { headers: { ...headers, authorization: 'Bearer untrusted-browser-token', cookie: 'private-cookie=value' } });
  assert.equal(result.status, 200);
  assert.deepEqual(await result.json(), { ready: true });
  const upstream = new Headers(forwarded!.headers);
  assert.equal(upstream.get('cookie'), null);
  const token = upstream.get('authorization')!.slice(7);
  const [header, payload, signature] = token.split('.');
  assert.equal(signature, createHmac('sha256', key).update(`${header}.${payload}`).digest('base64url'));
  const claims = JSON.parse(Buffer.from(payload, 'base64url').toString());
  assert.equal(claims.workspaceId, 'ws-1');
  assert.equal(claims.sub, 'usr-master');
  assert.equal(claims.clientId, null);
  assert.equal(claims.module, 'create-image');
  assert.equal(claims.exp - claims.iat, 60);
  assert.equal(result.headers.get('cache-control'), 'no-store');
});

test('Canonical JSON is bounded and forwarded as a complete body while media uploads remain streams', async t => {
  const app = express();
  app.use('/api/governance', createGovernanceRouter({ dataFile: null }));
  const bodies: unknown[] = [];
  app.use('/api/v1/studios/v1', createStudiosProxy({
    secret: 'private-studio-test-secret-with-more-than-32-characters',
    fetch: async (_url, init) => {
      bodies.push(init?.body);
      return new Response('{}', { headers: { 'content-type': 'application/json' } });
    },
  }));
  const server = app.listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(() => new Promise<void>(resolve => server.close(() => resolve())));
  const base = `http://127.0.0.1:${(server.address() as { port: number }).port}/api/v1/studios/v1`;
  const headers = { 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master',
    'x-clicko-studio-module': 'create-video', 'content-type': 'application/json' };
  const body = JSON.stringify({ title: 'Vídeo', prompt: 'Uma cena com narração' });
  for (const [method, route] of [
    ['POST', '/documents'], ['POST', '/video/documents/doc/openrouter-media'],
    ['POST', '/video/documents/doc/ai-commands'], ['POST', '/video/documents/doc/render-jobs'],
    ['PUT', '/video/documents/doc/timeline'],
  ]) {
    const response = await fetch(base + route, { method, headers, body });
    assert.equal(response.status, 200, route);
    assert.equal(bodies.at(-1), body, route);
  }
  const before = bodies.length;
  assert.equal((await fetch(base + '/documents', { method: 'POST', headers, body: '{broken' })).status, 400);
  assert.equal((await fetch(base + '/documents', { method: 'POST', headers,
    body: JSON.stringify({ title: 'x'.repeat(129 * 1024) }) })).status, 413);
  assert.equal(bodies.length, before);
  assert.equal((await fetch(base + '/craft/assets?filename=scene.mp4', {
    method: 'POST', headers: { ...headers, 'content-type': 'video/mp4' }, body: 'video-bytes',
  })).status, 200);
  const upload = bodies.at(-1) as NodeJS.ReadableStream;
  assert.equal(typeof upload.pipe, 'function');
});
