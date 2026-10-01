import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';

const root = path.dirname(fileURLToPath(import.meta.url));
const input = process.argv[2];
const output = process.argv[3];
if (!input || !output) throw new Error('native_scene_manifest_and_output_required');
const manifestPath = path.resolve(input);
const manifestBytes = await fs.readFile(manifestPath);
const manifest = JSON.parse(manifestBytes.toString('utf8'));
if (manifest.schemaVersion !== 'res.remotion-native-scene.v1' || manifest.component !== 'product-story-v1')
  throw new Error('native_scene_component_unsupported');
if (!Number.isInteger(manifest.width) || !Number.isInteger(manifest.height) || !Number.isInteger(manifest.fps) ||
    !Number.isInteger(manifest.durationFrames) || manifest.width < 1 || manifest.height < 1 ||
    manifest.width > 1920 || manifest.height > 1920 || manifest.fps < 1 || manifest.fps > 60 ||
    manifest.durationFrames < 1 || manifest.durationFrames > 1800) throw new Error('native_scene_dimensions_invalid');
if (!Array.isArray(manifest.beats) || manifest.beats.length !== 3 ||
    typeof manifest.brand !== 'string' || manifest.brand.length > 48 ||
    !/^#[0-9a-fA-F]{6}$/.test(manifest.accent) || !/^#[0-9a-fA-F]{6}$/.test(manifest.background))
  throw new Error('native_scene_contract_invalid');
let expectedStart = 0;
for (const beat of manifest.beats) {
  if (beat.startFrame !== expectedStart || !Number.isInteger(beat.durationFrames) || beat.durationFrames < 30 ||
      typeof beat.imageId !== 'string' || !beat.imageId ||
      !['eyebrow','headline','subline'].every((key) => typeof beat[key] === 'string' && beat[key].length <= 100) ||
      (beat.focusX != null && (!Number.isFinite(beat.focusX) || beat.focusX < 0 || beat.focusX > 100)) ||
      (beat.focusY != null && (!Number.isFinite(beat.focusY) || beat.focusY < 0 || beat.focusY > 100)))
    throw new Error('native_scene_beat_invalid');
  expectedStart += beat.durationFrames;
}
if (expectedStart !== manifest.durationFrames) throw new Error('native_scene_duration_mismatch');
const required = new Set(manifest.beats.map((beat) => beat.imageId));
if (manifest.audioId) required.add(manifest.audioId);
const assets = {};
for (const id of required) {
  const item = manifest.assetFiles?.[id];
  if (!item || typeof item.sha256 !== 'string' || typeof item.path !== 'string') throw new Error(`native_scene_asset_missing:${id}`);
  const expectedMime = id === manifest.audioId ? ['audio/wav','audio/mpeg'] : ['image/png','image/jpeg','image/webp'];
  if (!expectedMime.includes(item.mime)) throw new Error(`native_scene_asset_mime_unsupported:${id}`);
  const source = path.resolve(path.dirname(manifestPath), item.path);
  const bytes = await fs.readFile(source);
  if (bytes.length > 30_000_000 || crypto.createHash('sha256').update(bytes).digest('hex') !== item.sha256)
    throw new Error(`native_scene_asset_checksum_conflict:${id}`);
  assets[id] = `data:${item.mime};base64,${bytes.toString('base64')}`;
}
const inputProps = {manifest:{...manifest,assets}};
const started = performance.now();
const serveUrl = await bundle({entryPoint:path.join(root,'src','native-scene.tsx')});
const composition = await selectComposition({serveUrl,id:'ResNativeProductStory',inputProps,logLevel:'error'});
await fs.mkdir(path.dirname(path.resolve(output)),{recursive:true});
await renderMedia({serveUrl,composition,codec:'h264',outputLocation:path.resolve(output),inputProps,
  concurrency:2,logLevel:'error'});
const rendered = await fs.readFile(output);
console.log(JSON.stringify({schemaVersion:'res.remotion-native-scene-receipt.v1',component:manifest.component,
  manifestSha256:crypto.createHash('sha256').update(manifestBytes).digest('hex'),
  videoSha256:crypto.createHash('sha256').update(rendered).digest('hex'),
  durationMs:Math.round(performance.now()-started),bytes:rendered.length,frameCount:manifest.durationFrames,
  humanVisualReview:'pending'}));
