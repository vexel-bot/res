// Real browser workers against immutable artifacts from the native HTTP acceptance.
// This check needs the frontend and saved fixtures, but no running native server.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '@playwright/test';

const output = resolve('.codex-runtime/craft');
const fixtures = JSON.parse(await readFile(resolve(output, 'acceptance-results.json'), 'utf8'));
const extensions = { photocraft: 'pcraft', filmcraft: 'fcproj', effectcraft: 'ecproj' };
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const browser = await chromium.launch({ headless: true });
const results = [];
try {
  for (const fixture of fixtures) {
    const native = await readFile(resolve(output, `acceptance-${fixture.engine}.${extensions[fixture.engine]}`));
    const png = await readFile(resolve(output, `acceptance-${fixture.engine}.png`));
    assert.equal(sha256(native), fixture.nativeSha256, 'Native reference checksum changed');
    assert.equal(sha256(png), fixture.previewSha256, 'Native PNG checksum changed');
    const page = await browser.newPage();
    try {
      await page.goto('http://127.0.0.1:3018', { waitUntil: 'domcontentloaded', timeout: 120000 });
      const result = await page.evaluate(async ({ fixture, bytes }) => {
        const { CraftWorker } = await import('/src/studios/craft/craftWorker.ts');
        const worker = new CraftWorker(fixture.engine, fixture.documentId, fixture.revision);
        const digest = async data => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), b => b.toString(16).padStart(2, '0')).join('');
        try {
          await worker.initialize();
          await worker.call('open', new Uint8Array(bytes));
          const response = JSON.parse(await worker.call('request', JSON.stringify({
            protocolVersion: 1, requestId: crypto.randomUUID(), engine: fixture.engine,
            method: 'engine.capabilities', params: {},
          })));
          if (response.error) throw new Error(response.error.message);
          const before = await worker.call('preview', 0, 0);
          const saved = await worker.call('save');
          const savedBytes = saved.byteLength;
          if (!savedBytes) throw new Error('Native serialization produced no bytes');
          await worker.call('open', saved);
          const after = await worker.call('preview', 0, 0);
          if (await digest(before) !== await digest(after)) throw new Error('Save/reopen changed pixels');
          return { engine: fixture.engine, buildId: response.result.buildId,
            previewSha256: await digest(after), nativeReferenceSha256: fixture.nativeSha256,
            savedBytes, worker: true, reopen: true };
        } finally { worker.close(); }
      }, { fixture, bytes: Array.from(native) });
      assert.equal(result.previewSha256, fixture.previewSha256, `${fixture.engine}: WASM/native pixels differ`);
      results.push(result);
      console.log(JSON.stringify(result));
    } finally { await page.close(); }
  }
  await writeFile(resolve(output, 'wasm-reference-results.json'), JSON.stringify(results, null, 2));
} finally { await browser.close(); }
