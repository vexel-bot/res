import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createGovernanceRouter } from './governance';

test('governance refuses publicly served storage locations before creating files', () => {
  for (const folder of ['public', 'dist']) {
    assert.throws(() => createGovernanceRouter({ dataFile: path.resolve(folder, 'governance-test.json') }), /fora de public/);
  }
});

test('Vite refuses private governance snapshots and backups over HTTP', () => {
  // A separate Vite instance serves only temporary fixture data, never user data.
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', `
    import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
    import { tmpdir } from 'node:os';
    import path from 'node:path';
    import assert from 'node:assert/strict';
    import { createServer } from ${JSON.stringify(pathToFileURL(require.resolve('vite')).href)};
    const parent = path.resolve(tmpdir());
    const root = mkdtempSync(path.join(parent, 'clicko-data-access-test-'));
    let server;
    try {
      mkdirSync(path.join(root, '.clicko-data'));
      for (const name of ['governance.json', 'governance.json.previous', 'governance.json.lock', 'governance.json.fixture.tmp', 'social-integrations.json']) {
        writeFileSync(path.join(root, '.clicko-data', name), 'PRIVATE_FIXTURE_MUST_NOT_BE_SERVED');
      }
      const custom = path.join(root, 'custom-private.json');
      writeFileSync(custom, 'PRIVATE_FIXTURE_MUST_NOT_BE_SERVED');
      process.env.CLICKO_GOVERNANCE_DATA_FILE = custom;
      server = await createServer({ root, configFile: ${JSON.stringify(path.resolve('vite.config.ts'))}, logLevel: 'silent', server: { host: '127.0.0.1', port: 0, hmr: false, watch: null }, optimizeDeps: { noDiscovery: true, include: [] } });
      await server.listen();
      const base = 'http://127.0.0.1:' + server.httpServer.address().port;
      for (const url of ['/.clicko-data/governance.json', '/.clicko-data/governance.json.previous', '/.clicko-data/governance.json.lock', '/.clicko-data/governance.json.fixture.tmp', '/.clicko-data/social-integrations.json', '/custom-private.json', '/@fs/' + custom.replace(/\\\\/g, '/')]) {
        const response = await fetch(base + url);
        const body = await response.text();
        assert.equal(response.status, 403, url);
        assert.equal(body.includes('PRIVATE_FIXTURE_MUST_NOT_BE_SERVED'), false);
      }
    } finally {
      await server?.close();
      if (path.dirname(root) === parent && path.basename(root).startsWith('clicko-data-access-test-')) rmSync(root, { recursive: true, force: true });
    }
  `], { encoding: 'utf8', timeout: 30000, env: process.env });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
});

test('Vite ignores atomic runtime persistence while source changes still trigger HMR', () => {
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', `
    import { mkdtempSync, mkdirSync, writeFileSync, renameSync, rmSync } from 'node:fs';
    import { tmpdir } from 'node:os';
    import path from 'node:path';
    import assert from 'node:assert/strict';
    import { setTimeout as delay } from 'node:timers/promises';
    import { createServer } from ${JSON.stringify(pathToFileURL(require.resolve('vite')).href)};
    const parent = path.resolve(tmpdir());
    const root = mkdtempSync(path.join(parent, 'clicko-runtime-watch-test-'));
    const index = path.join(root, 'index.html');
    const runtime = path.join(root, '.clicko-data', 'conversations');
    const custom = path.join(root, 'custom-private.json');
    let server;
    const events = [];
    const reloads = [];
    const waitFor = async (condition, label) => {
      const deadline = Date.now() + 5000;
      while (!condition()) {
        assert.ok(Date.now() < deadline, label);
        await delay(25);
      }
    };
    try {
      mkdirSync(runtime, { recursive: true });
      writeFileSync(index, '<!doctype html><html><body>Source fixture</body></html>');
      writeFileSync(path.join(runtime, 'conversation.json'), '{}');
      writeFileSync(custom, '{}');
      process.env.CLICKO_GOVERNANCE_DATA_FILE = custom;
      delete process.env.DISABLE_HMR;
      server = await createServer({ root, configFile: ${JSON.stringify(path.resolve('vite.config.ts'))}, logLevel: 'silent', server: { host: '127.0.0.1', port: 0 }, optimizeDeps: { noDiscovery: true, include: [] } });
      assert.notEqual(server.config.server.hmr, false);
      assert.notEqual(server.config.server.watch, null);
      server.watcher.on('all', (event, file) => events.push({ event, file: path.resolve(file) }));
      const send = server.ws.send.bind(server.ws);
      server.ws.send = (...args) => {
        if (args[0]?.type === 'full-reload') reloads.push(args[0]);
        return send(...args);
      };
      await server.listen();
      await waitFor(() => Object.values(server.watcher.getWatched()).some(files => files.includes('index.html')), 'Source fixture was not watched');
      await delay(150);
      events.length = 0;
      reloads.length = 0;
      const atomicWrite = file => {
        writeFileSync(file + '.fixture.tmp', '{"fixture":true}');
        renameSync(file + '.fixture.tmp', file);
        writeFileSync(file + '.previous', '{}');
        writeFileSync(file + '.lock', 'fixture');
      };
      atomicWrite(path.join(runtime, 'conversation.json'));
      atomicWrite(custom);
      const created = path.join(runtime, 'new-conversation');
      mkdirSync(created);
      atomicWrite(path.join(created, 'messages.json'));
      await delay(350);
      assert.deepEqual(events, [], 'Runtime persistence reached the source watcher');
      assert.deepEqual(reloads, [], 'Runtime persistence triggered a page reload');

      // Positive control: private-data exclusions must not disable ordinary source HMR.
      writeFileSync(index, '<!doctype html><html><body>Updated source fixture</body></html>');
      await waitFor(() => events.some(entry => entry.event === 'change' && entry.file === index) && reloads.length > 0, 'Source changes no longer trigger HMR');
      await delay(250);
      assert.ok(events.every(entry => entry.file === index), JSON.stringify(events));
      assert.ok(reloads.every(payload => payload.path === '/index.html' || payload.path === index.replace(/\\\\/g, '/')), JSON.stringify(reloads));
    } finally {
      await server?.close();
      if (path.dirname(root) === parent && path.basename(root).startsWith('clicko-runtime-watch-test-')) rmSync(root, { recursive: true, force: true });
    }
  `], { encoding: 'utf8', timeout: 30000, env: process.env });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
});
