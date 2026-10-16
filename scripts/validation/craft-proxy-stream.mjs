// Verify that the actual production proxy forwards bytes before a large response finishes.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

let finished = false;
const chunk = Buffer.alloc(256 * 1024, 97), totalChunks = 64;
const upstream = createServer((_request, response) => {
  response.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Length': chunk.length * totalChunks });
  let count = 0;
  const timer = setInterval(() => {
    response.write(chunk);
    if (++count === totalChunks) { clearInterval(timer); finished = true; response.end(); }
  }, 40);
  response.on('close', () => clearInterval(timer));
});
await new Promise(resolve => upstream.listen(18518, '127.0.0.1', resolve));
const child = spawn(process.execPath, ['dist/server.js'], { cwd: process.cwd(), windowsHide: true,
  env: { ...process.env, NODE_ENV: 'production', PORT: '18519', CLICKO_API_ORIGIN: 'http://127.0.0.1:18518' },
  stdio: ['ignore', 'pipe', 'pipe'] });
let log = '';
child.stdout.on('data', data => { log += data; });
child.stderr.on('data', data => { log += data; });
try {
  const deadline = Date.now() + 30000;
  while (!log.includes('Clicko Studio Server running')) {
    if (child.exitCode !== null || Date.now() > deadline) throw new Error('Production proxy did not start');
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  const response = await fetch('http://127.0.0.1:18519/api/v1/stream-fixture');
  assert.equal(response.status, 200);
  const reader = response.body.getReader();
  const first = await reader.read();
  assert.equal(first.done, false);
  assert.equal(finished, false, 'Proxy buffered the whole response before forwarding bytes');
  let bytes = first.value.byteLength;
  for (;;) {
    const item = await reader.read();
    if (item.done) break;
    assert.ok(item.value.every(value => value === 97));
    bytes += item.value.byteLength;
  }
  assert.equal(bytes, chunk.length * totalChunks);
  const result = { productionProxy: true, bytes, firstChunkBeforeUpstreamFinished: true, byteIntegrity: true };
  await writeFile(resolve('.codex-runtime/craft/proxy-stream-results.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally {
  child.kill();
  if (child.exitCode === null) await once(child, 'exit');
  await new Promise(resolve => upstream.close(resolve));
}
