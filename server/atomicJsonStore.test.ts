import test, { type TestContext } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { AtomicJsonStore } from './atomicJsonStore';

type Sample = { version: 1; items: string[] };
const valid = (value: unknown): value is Sample => Boolean(value && typeof value === 'object' && (value as Sample).version === 1 && Array.isArray((value as Sample).items) && (value as Sample).items.every(item => typeof item === 'string'));
function fixture(t: TestContext) {
  const parent = path.resolve(tmpdir());
  const folder = mkdtempSync(path.join(parent, 'clicko-store-test-'));
  t.after(() => { if (path.dirname(folder) === parent && path.basename(folder).startsWith('clicko-store-test-')) rmSync(folder, { recursive: true, force: true }); });
  return { folder, filename: path.join(folder, 'governance.json') };
}

test('local repository survives a new instance and keeps the previous revision', t => {
  const { filename, folder } = fixture(t);
  const store = new AtomicJsonStore(filename, valid);
  store.load({ version: 1, items: [] });
  store.save({ version: 1, items: ['real saved item'] });
  assert.deepEqual(new AtomicJsonStore(filename, valid).load({ version: 1, items: ['must not replace'] }), { version: 1, items: ['real saved item'] });
  assert.deepEqual(JSON.parse(readFileSync(filename + '.previous', 'utf8')), { version: 1, items: [] });
  assert.equal(readdirSync(folder).some(name => /\.(lock|tmp)$/.test(name)), false);
});

test('corrupt or unsupported files fail without overwriting the original', t => {
  const { filename } = fixture(t);
  for (const content of ['broken JSON', '{"version":99,"items":[]}', '{"version":1,"items":[false]}']) {
    writeFileSync(filename, content);
    assert.throws(() => new AtomicJsonStore(filename, valid).load({ version: 1, items: [] }), /INVALID/);
    assert.equal(readFileSync(filename, 'utf8'), content);
  }
});

test('stale writer cannot overwrite a newer snapshot', t => {
  const { filename } = fixture(t);
  const first = new AtomicJsonStore(filename, valid);
  first.load({ version: 1, items: [] });
  const second = new AtomicJsonStore(filename, valid);
  second.load({ version: 1, items: [] });
  first.save({ version: 1, items: ['newer'] });
  assert.throws(() => second.save({ version: 1, items: ['stale'] }), /CONFLICT/);
  assert.deepEqual(JSON.parse(readFileSync(filename, 'utf8')).items, ['newer']);
});

test('lock contention fails safely and does not remove another writer lock', t => {
  const { filename } = fixture(t);
  const store = new AtomicJsonStore(filename, valid);
  store.load({ version: 1, items: ['existing'] });
  writeFileSync(filename + '.lock', 'other writer');
  assert.throws(() => store.save({ version: 1, items: ['not saved'] }));
  assert.equal(readFileSync(filename + '.lock', 'utf8'), 'other writer');
  assert.deepEqual(JSON.parse(readFileSync(filename, 'utf8')).items, ['existing']);
});
