// Real WASM/native parity using the projects produced by scripts/craft/acceptance.py.
import { chromium } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const output = resolve('.codex-runtime/craft');
const auth = JSON.parse(await readFile(resolve(output, 'frontend-qa-auth.json'), 'utf8'));
const fixtures = JSON.parse(await readFile(resolve(output, 'acceptance-results.json'), 'utf8'));
const browser = await chromium.launch({headless: true});
const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
await context.addInitScript(token => localStorage.setItem('nexus_access_token', token), auth.token);
const page = await context.newPage();
const failures = [];
page.on('pageerror', error => failures.push(error.message));
const results = [];
try {
  for (const fixture of fixtures.filter(item => !process.argv[2] || item.engine === process.argv[2])) {
    const mode = {photocraft: 'carousel', filmcraft: 'video', effectcraft: 'effects'}[fixture.engine];
    await page.goto(`http://127.0.0.1:3018/content/draft/edit?mode=${mode}&document=${fixture.documentId}`, {waitUntil: 'domcontentloaded', timeout: 120000});
    await page.locator('.craft-workspace').waitFor({state: 'visible', timeout: 120000});
    if (fixture.pageId === 'page-1') await page.locator('.craft-page-list button').nth(1).click();
    const result = await page.evaluate(async ({fixture, token}) => {
      const module = await import(`/craft/${fixture.engine}/clicko_${fixture.engine}_adapter.js`);
      await module.default();
      const adapter = new module.Adapter();
      try {
        const headers = {Authorization: `Bearer ${token}`};
        const path = `/api/v1/studios/v1/documents/${fixture.documentId}/native-project${fixture.pageId ? `?pageId=${fixture.pageId}` : ''}`;
        const response = await fetch(path, {headers});
        if (!response.ok) throw new Error('Native fixture unavailable');
        const bytes = new Uint8Array(await response.arrayBuffer());
        const digest = async data => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), b => b.toString(16).padStart(2, '0')).join('');
        if (await digest(bytes) !== fixture.nativeSha256) throw new Error('Native fixture changed');
        adapter.openNative(bytes);
        const capability = JSON.parse(adapter.request(JSON.stringify({protocolVersion: 1, requestId: crypto.randomUUID(), engine: fixture.engine, method: 'engine.capabilities', params: {}}))).result;
        const preview = fixture.engine === 'photocraft' ? adapter.previewPng(0) : adapter.previewPng(0, 0);
        const sha256 = await digest(preview);
        const server = await fetch(`/api/v1/studios/v1/documents/${fixture.documentId}/craft/preview`, {method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({frame:0,pageId:fixture.pageId})});
        const serverPng = new Uint8Array(await server.arrayBuffer());
        if (!server.ok || sha256 !== await digest(serverPng)) throw new Error('Browser/server pixels differ');
        return {engine: fixture.engine, buildId: capability.buildId, sha256, width: 320, height: 320};
      } finally { adapter.free(); }
    }, {fixture, token: auth.token});
    await page.locator('.craft-preview img').waitFor({state: 'visible', timeout: 120000});
    await page.locator('.craft-stage[data-craft-browser-state="ready"]').waitFor({state: 'visible', timeout: 120000});
    if (!page.workers().some(worker => worker.url().includes('craft.worker'))) throw new Error('Customer preview did not start the native Web Worker');
    const actualPreview = await page.locator('.craft-preview img').evaluate(async image => {
      const blob = await (await fetch(image.src)).arrayBuffer();
      return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', blob)), b => b.toString(16).padStart(2, '0')).join('');
    });
    if (actualPreview !== result.sha256) throw new Error('Customer worker preview differs from the native reference');
    if (await page.locator('vite-error-overlay').count()) throw new Error('The customer Studio has a module-loading overlay');
    await page.screenshot({path: resolve(output, `studio-${fixture.engine}-editing.png`), fullPage: true});
    results.push(result);
    console.log(JSON.stringify(result));
  }
  if (failures.length) throw new Error(failures.join(' | '));
  await writeFile(resolve(output, 'browser-parity-results.json'), JSON.stringify(results, null, 2));
} finally { await context.close(); await browser.close(); }
