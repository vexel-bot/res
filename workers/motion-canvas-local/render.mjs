import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createServer} from 'vite';
import {chromium} from 'playwright';

const root = path.dirname(fileURLToPath(import.meta.url));
const manifestPath = process.argv[2];
const output = path.resolve(process.argv[3] ?? path.join(root, 'output', 'fixture'));
const ffmpeg = process.argv[4] ?? 'ffmpeg';
if (!manifestPath) throw new Error('motion_canvas_manifest_required');
const raw = JSON.parse(await fs.readFile(path.resolve(manifestPath), 'utf8'));
if (raw.schemaVersion !== 'res.motion-canvas-composition.v1') throw new Error('motion_canvas_manifest_version_unsupported');
const {width, height, fps, durationFrames} = raw;
if (![width, height, fps, durationFrames].every(Number.isInteger) || width < 32 || height < 32 || fps < 1 || durationFrames < 1) {
  throw new Error('invalid_render_settings');
}
const duration = durationFrames / fps;
const assets = {};
for (const [id, entry] of Object.entries(raw.assetFiles ?? {})) {
  const file = path.resolve(entry.path);
  const data = await fs.readFile(file);
  if (crypto.createHash('sha256').update(data).digest('hex') !== entry.sha256) throw new Error(`asset_checksum_mismatch:${id}`);
  assets[id] = {file, mime: entry.mime};
}
const manifest = {...raw, assets: Object.fromEntries(Object.keys(assets).map(id => [id, `/res-assets/${encodeURIComponent(id)}`]))};
delete manifest.assetFiles;
await fs.mkdir(output, {recursive: true});
const server = await createServer({root, configFile: path.join(root, 'vite.config.ts'), server: {host: '127.0.0.1', port: 0}});
let browser;
try {
  await server.listen();
  const address = server.httpServer.address();
  browser = await chromium.launch({headless: true});
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
  await page.route('**/res-assets/*', async route => {
    const id = decodeURIComponent(new URL(route.request().url()).pathname.split('/').pop());
    const asset = assets[id];
    if (!asset) return route.abort();
    return route.fulfill({path: asset.file, contentType: asset.mime});
  });
  await page.addInitScript(value => {window.__resManifest = value;}, manifest);
  const frames = [];
  await page.exposeBinding('__resPushFrame', async (_source, frame, dataUrl) => {
    const data = Buffer.from(dataUrl.split(',')[1], 'base64');
    const file = path.join(output, `${String(frame).padStart(6, '0')}.png`);
    await fs.writeFile(file, data);
    frames.push({frame, sha256: crypto.createHash('sha256').update(data).digest('hex')});
  });
  await page.goto(`http://127.0.0.1:${address.port}/headless.html`, {waitUntil: 'networkidle'});
  await page.waitForFunction(() => typeof window.__resRender === 'function', {timeout: 30000});
  await page.evaluate(async () => {
    const spec = window.__resManifest;
    for (const font of spec.fonts ?? []) {
      const face = new FontFace(font.family, `url(${spec.assets[font.assetId]})`, {weight: String(font.weight)});
      await face.load();
      document.fonts.add(face);
    }
    await document.fonts.ready;
  });
  const result = await page.evaluate(settings => window.__resRender(settings), {width, height, fps, duration});
  const layoutDiagnostics = await page.evaluate(() => window.__resLayoutDiagnostics ?? []);
  const geometrySamples = await page.evaluate(() => window.__resGeometrySamples ?? []);
  const videoPath = path.join(output, 'visual.mp4');
  if (result === 0 && frames.length === durationFrames) {
    await new Promise((resolve, reject) => {
      const child = spawn(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-y', '-framerate', String(fps), '-i', path.join(output, '%06d.png'),
        '-frames:v', String(durationFrames), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', videoPath], {stdio: ['ignore', 'ignore', 'pipe']});
      let error = '';
      child.stderr.on('data', chunk => {error += chunk.toString().slice(0, 2000);});
      child.on('error', reject);
      child.on('exit', code => code === 0 ? resolve() : reject(new Error(`motion_canvas_ffmpeg_failed:${error}`)));
    });
  }
  const videoSha256 = result === 0 && frames.length === durationFrames
    ? crypto.createHash('sha256').update(await fs.readFile(videoPath)).digest('hex') : null;
  const receipt = {schemaVersion: 'res.motion-canvas-render-receipt.v1', result, settings: {width, height, fps, durationFrames}, frames, errors, layoutDiagnostics,
    geometrySchemaVersion: 'studio.rendered-geometry.v1', geometrySamples,
    manifestSha256: crypto.createHash('sha256').update(await fs.readFile(path.resolve(manifestPath))).digest('hex'), videoSha256};
  await fs.writeFile(path.join(output, 'receipt.json'), JSON.stringify(receipt, null, 2));
  console.log(JSON.stringify(receipt));
  if (result !== 0 || frames.length !== durationFrames || !videoSha256) process.exitCode = 1;
} finally {
  await browser?.close();
  await server.close();
}
