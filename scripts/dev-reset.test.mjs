import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, readdirSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
test('DEV cleanup requires explicit confirmation and archives only a marked private test directory', () => {
  const parent = path.join(project, '.codex-runtime'); mkdirSync(parent, { recursive: true });
  const root = mkdtempSync(path.join(parent, 'clicko-dev-reset-test-'));
  writeFileSync(path.join(root, 'dev-profile.json'), JSON.stringify({ schemaVersion: 'clicko.local-dev.v1', root }));
  writeFileSync(path.join(root, 'own-test-data.txt'), 'disposable test fixture');
  const run = (target, args = [], more = {}) => spawnSync(process.execPath, ['scripts/dev-reset.mjs', ...args], {
    cwd: project, encoding: 'utf8', windowsHide: true, env: { ...process.env, NODE_ENV: 'development', CLICKO_LOCAL_DATA_DIR: target, ...more },
  });
  try {
    assert.equal(run(root).status, 2); assert.ok(existsSync(root));
    assert.notEqual(run(path.join(project, '.clicko-data'), ['--confirm=ARCHIVE_CLICKO_DEV']).status, 0);
    assert.notEqual(run(root, ['--confirm=ARCHIVE_CLICKO_DEV'], { NODE_ENV: 'production' }).status, 0);
    const confirmed = run(root, ['--confirm=ARCHIVE_CLICKO_DEV']);
    assert.equal(confirmed.status, 0, confirmed.stderr);
    assert.equal(existsSync(root), false);
    const archive = readdirSync(parent).find(name => name.startsWith(path.basename(root) + '-backup-'));
    assert.ok(archive); assert.ok(existsSync(path.join(parent, archive, 'own-test-data.txt')));
  } finally {
    // Only this uniquely-created disposable fixture or its archive, never user DEV data.
    for (const name of readdirSync(parent)) if (name === path.basename(root) || name.startsWith(path.basename(root) + '-backup-')) {
      const target = path.join(parent, name);
      if (path.dirname(target) === parent && name.startsWith('clicko-dev-reset-test-')) rmSync(target, { recursive: true, force: true });
    }
  }
});
