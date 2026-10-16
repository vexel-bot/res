// Exercise the bundled production worker against real native reference artifacts.
import assert from 'node:assert/strict';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '@playwright/test';

const fixtureRoot = resolve(process.env.CRAFT_REFERENCE_OUTPUT || '.codex-runtime/craft');
const fixtures = JSON.parse(await readFile(resolve(fixtureRoot, 'acceptance-results.json'), 'utf8'));
const name = (await readdir(resolve('dist/assets'))).find(name => /^craft\.worker-.*\.js$/.test(name));
assert.ok(name, 'Build the production worker first');
const extensions = { photocraft: 'pcraft', filmcraft: 'fcproj', effectcraft: 'ecproj' };
const browser = await chromium.launch({ headless: true });
const results = [];
try {
  for (const fixture of fixtures) {
    const native = await readFile(resolve(fixtureRoot, `acceptance-${fixture.engine}.${extensions[fixture.engine]}`));
    const page = await browser.newPage();
    await page.route('**/__craft_production_fixture', route => route.fulfill({ contentType: 'application/octet-stream', body: native }));
    await page.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded', timeout: 120000 });
    const result = await page.evaluate(async ({ name, fixture }) => {
      const worker = new Worker(`/assets/${name}`, { type: 'module' });
      const pending = new Map();
      worker.onmessage = ({ data }) => {
        const item = pending.get(data.requestId);
        if (!item) return;
        clearTimeout(item.timer); pending.delete(data.requestId);
        if (data.error) item.reject(new Error(data.error)); else item.resolve(data.result);
      };
      const call = (operation, ...args) => new Promise((resolve, reject) => {
        const requestId = crypto.randomUUID();
        const timer = setTimeout(() => reject(new Error('Production worker timed out')), 120000);
        pending.set(requestId, { resolve, reject, timer });
        worker.postMessage({ protocolVersion: 1, requestId, engine: fixture.engine,
          projectId: fixture.documentId, expectedRevision: fixture.revision, operation, args });
      });
      const digest = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
      try {
        await call('initialize');
        await call('open', new Uint8Array(await (await fetch('/__craft_production_fixture')).arrayBuffer()));
        const before = await digest(await call('preview', 0, 0));
        await call('open', await call('save'));
        const after = await digest(await call('preview', 0, 0));
        return { engine: fixture.engine, before, after };
      } finally { worker.terminate(); }
    }, { name, fixture });
    assert.equal(result.before, fixture.previewSha256);
    assert.equal(result.after, fixture.previewSha256);
    results.push({ engine: fixture.engine, productionWorker: true, nativePixelParity: true, reopened: true });
    await page.close();
  }
  await writeFile(resolve('.codex-runtime/craft/production-wasm-results.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results));
} finally { await browser.close(); }
