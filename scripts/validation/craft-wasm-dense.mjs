// Compare dense legacy migration and native reopening in the genuine WASM worker.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '@playwright/test';

const output = resolve('.codex-runtime/craft');
const fixture = JSON.parse(await readFile(resolve(output, 'dense-fixture.json'), 'utf8'));
const reference = JSON.parse(await readFile(resolve(output, 'dense-motion-results.json'), 'utf8'));
const bytes = await readFile(resolve(output, 'dense-native.ecproj'));
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.route('**/__craft_dense_fixture.ecproj', route => route.fulfill({ contentType: 'application/octet-stream', body: bytes }));
  await page.goto('http://127.0.0.1:3018', { waitUntil: 'domcontentloaded', timeout: 120000 });
  const results = await page.evaluate(async ({ fixture, reference }) => {
    const { CraftWorker } = await import('/src/studios/craft/craftWorker.ts');
    const worker = new CraftWorker('effectcraft', crypto.randomUUID(), 1);
    const digest = async data => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), b => b.toString(16).padStart(2, '0')).join('');
    const request = async (method, params = {}) => {
      const response = JSON.parse(await worker.call('request', JSON.stringify({ protocolVersion: 1,
        requestId: crypto.randomUUID(), engine: 'effectcraft', method, params })));
      if (response.error) throw new Error(response.error.message);
      return response.result;
    };
    const frames = async () => Promise.all(reference.frames.map(async ({ frame }) => ({
      frame, sha256: await digest(await worker.call('preview', frame / 10, 0)),
    })));
    try {
      await worker.initialize();
      const capability = await request('engine.capabilities');
      await request('project.new', fixture);
      const migrated = await frames();
      await worker.call('open', await worker.call('save'));
      const reopened = await frames();
      await worker.call('open', new Uint8Array(await (await fetch('/__craft_dense_fixture.ecproj')).arrayBuffer()));
      const nativeReopened = await frames();
      return { buildId: capability.buildId, migrated, reopened, nativeReopened };
    } finally { worker.close(); }
  }, { fixture, reference });
  assert.equal(results.buildId, reference.buildId);
  const expected = reference.frames.map(({ frame, sha256 }) => ({ frame, sha256 }));
  assert.deepEqual(results.migrated, expected);
  assert.deepEqual(results.reopened, expected);
  assert.deepEqual(results.nativeReopened, expected);
  await writeFile(resolve(output, 'wasm-dense-results.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ sampledFrames: 12000, buildId: results.buildId, nativePixelParity: true, reopen: true }));
} finally { await browser.close(); }
