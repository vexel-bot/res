import assert from 'node:assert/strict';
import test from 'node:test';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, rmdir } from 'node:fs/promises';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

async function fixture(reply) {
  const directory = await mkdtemp(path.join(tmpdir(), 'clicko-control-test-'));
  const control = process.platform === 'win32'
    ? '\\\\.\\pipe\\clicko-local-' + createHash('sha256').update(directory).digest('hex').slice(0, 32)
    : path.join(directory, 'control.sock');
  const server = reply ? createServer(socket => {
    socket.on('error', () => {});
    socket.once('data', () => reply(socket));
  }) : null;
  if (server) await new Promise((resolve, reject) => server.once('error', reject).listen(control, resolve));
  try {
    const child = spawn(process.execPath, ['scripts/dev-local.mjs', 'status'], {
      cwd: project, windowsHide: true,
      env: { ...process.env, CLICKO_LOCAL_DATA_DIR: directory }, stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '', stderr = '';
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr += chunk; });
    const code = await new Promise((resolve, reject) => { child.once('error', reject); child.once('exit', resolve); });
    return { code, stdout, stderr };
  } finally {
    if (server) await new Promise(resolve => server.close(resolve));
    // Empty, uniquely created fixture only; no recursive removal or app data.
    if (path.dirname(directory) === path.resolve(tmpdir()) && path.basename(directory).startsWith('clicko-control-test-'))
      await rmdir(directory);
  }
}

test('status waits beyond the old 3s cutoff and receives the 4s health result', async () => {
  const result = await fixture(socket => setTimeout(() => socket.end(JSON.stringify({ ready: true }) + '\n'), 3500));
  assert.equal(result.code, 0);
  assert.deepEqual(JSON.parse(result.stdout), { ready: true });
});

test('unresponsive control reports timeout and fails instead of silently succeeding', async () => {
  const result = await fixture(() => {});
  assert.equal(result.code, 1);
  assert.match(result.stderr, /CLICKO_LOCAL_CONTROL_TIMEOUT/);
});

test('absent supervisor remains an explicit failure without launching the application', async () => {
  const result = await fixture(null);
  assert.equal(result.code, 1);
  assert.match(result.stderr, /CLICKO_LOCAL_NOT_RUNNING/);
});
