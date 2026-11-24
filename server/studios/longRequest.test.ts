import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { longStudioRequest } from './longRequest';

test('Long editing transport waits for the response and preserves its JSON and headers', async t => {
  const server = createServer(async (request, response) => {
    let body = '';
    for await (const chunk of request) body += chunk;
    assert.equal(body, '{"directionEffort":"open_ended"}');
    assert.equal(request.headers['idempotency-key'], 'same-edit');
    setTimeout(() => {
      response.writeHead(200, { 'content-type': 'application/json', etag: 'revision-4' });
      response.end('{"exportStatus":"succeeded"}');
    }, 40);
  }).listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(() => new Promise<void>(resolve => server.close(() => resolve())));
  const address = server.address() as { port: number };
  const response = await longStudioRequest(new URL(`http://127.0.0.1:${address.port}/edit`), {
    method: 'POST', headers: { 'idempotency-key': 'same-edit' },
    body: '{"directionEffort":"open_ended"}',
  });
  assert.equal(response.headers.get('etag'), 'revision-4');
  assert.deepEqual(await response.json(), { exportStatus: 'succeeded' });
});

test('A client can cancel while the editor is still working', async t => {
  const controller = new AbortController();
  const server = createServer(() => controller.abort()).listen(0, '127.0.0.1');
  await new Promise<void>(resolve => server.once('listening', resolve));
  t.after(() => new Promise<void>(resolve => server.close(() => resolve())));
  const address = server.address() as { port: number };
  await assert.rejects(longStudioRequest(new URL(`http://127.0.0.1:${address.port}/edit`), {
    method: 'POST', body: '{}', signal: controller.signal,
  }), { name: 'AbortError' });
});
