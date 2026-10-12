// Customer UI recovery/reopening with real API, WASM and native pixel parity.
import { chromium } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';

const output = resolve('.codex-runtime/craft');
const { token } = JSON.parse(await readFile(resolve(output, 'frontend-qa-auth.json'), 'utf8'));
const fixture = JSON.parse(await readFile(resolve(output, 'recovery-acceptance-results.json'), 'utf8'));
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
await context.addInitScript(value => localStorage.setItem('nexus_access_token', value), token);
const headers = { Authorization: `Bearer ${token}` };
const base = `/api/v1/studios/v1/documents/${fixture.documentId}`;
try {
  const before = await (await context.request.get(`http://127.0.0.1:8018${base}`, { headers })).json();
  const page = await context.newPage();
  const failures = [];
  page.on('pageerror', error => failures.push(error.message));
  await page.goto(`http://127.0.0.1:3018/content/draft/edit?mode=video&document=${fixture.documentId}`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('.craft-workspace').waitFor({ state: 'visible', timeout: 120000 });
  await page.getByRole('button', { name: 'Converter camadas e efeitos', exact: true }).click();
  await page.waitForURL(url => url.searchParams.get('mode') === 'effects' && url.searchParams.get('document') === fixture.compositionDocumentId, { timeout: 120000 });
  await page.locator('.craft-stage[data-craft-browser-state="ready"]').waitFor({ state: 'visible', timeout: 120000 });
  await page.locator('.craft-timeline input[type="number"]').fill('10');
  const reference = await context.request.post(`http://127.0.0.1:8018/api/v1/studios/v1/documents/${fixture.compositionDocumentId}/craft/preview`, { headers, data: { frame: 10 } });
  if (!reference.ok()) throw new Error('Native recovered preview unavailable');
  const sha256 = createHash('sha256').update(await reference.body()).digest('hex');
  await page.waitForFunction(async expected => {
    const image = document.querySelector('.craft-preview img');
    if (!image) return false;
    const bytes = await (await fetch(image.src)).arrayBuffer();
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
    return digest === expected;
  }, sha256, { timeout: 120000 });
  if (!page.workers().some(worker => worker.url().includes('craft.worker'))) throw new Error('Native browser worker missing');
  if (!(await page.getByRole('button', { name: 'Usar na montagem', exact: true }).count())) throw new Error('Montage return action missing');
  const after = await (await context.request.get(`http://127.0.0.1:8018${base}`, { headers })).json();
  if (after.revision !== before.revision || after.nativeEditorState.checksumSha256 !== before.nativeEditorState.checksumSha256) throw new Error('Reopening effects changed the montage');
  if (failures.length) throw new Error(failures.join(' | '));
  await page.screenshot({ path: resolve(output, 'studio-recovered-effects.png'), fullPage: true });
  await writeFile(resolve(output, 'browser-recovery-results.json'), JSON.stringify({ recoveredSourceOpened: true, customerWorkerReady: true, nativePreviewSha256: sha256, montageRevisionPreserved: true }, null, 2));
  console.log('Passed customer recovery navigation, WASM/native pixels and unchanged montage revision');
} finally {
  await context.close();
  await browser.close();
}
