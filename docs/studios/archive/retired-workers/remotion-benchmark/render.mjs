import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';

const root=path.dirname(fileURLToPath(import.meta.url));
const input=process.argv[2];
const output=process.argv[3];
if(!input||!output) throw new Error('benchmark_input_and_output_required');
const manifest=JSON.parse(await fs.readFile(input,'utf8'));
if(manifest.schemaVersion!=='res.motion-canvas-composition.v1'||manifest.width!==480||manifest.height!==320||manifest.fps!==15||manifest.durationFrames!==15)
  throw new Error('benchmark_manifest_out_of_scope');
const assets={};
for(const [id,item] of Object.entries(manifest.assetFiles??{})){
  const bytes=await fs.readFile(item.path);
  if(crypto.createHash('sha256').update(bytes).digest('hex')!==item.sha256) throw new Error('benchmark_asset_checksum_conflict');
  assets[id]=`data:${item.mime};base64,${bytes.toString('base64')}`;
}
const inputProps={manifest:{...manifest,assets}};
const start=performance.now();
const serveUrl=await bundle({entryPoint:path.join(root,'src','index.tsx')});
const composition=await selectComposition({serveUrl,id:'ResComparison',inputProps,logLevel:'error'});
await renderMedia({serveUrl,composition,codec:'h264',outputLocation:path.resolve(output),inputProps,concurrency:1,logLevel:'error'});
const bytes=await fs.readFile(output);
console.log(JSON.stringify({schemaVersion:'res.remotion-benchmark-receipt.v1',sha256:crypto.createHash('sha256').update(bytes).digest('hex'),
  durationMs:Math.round(performance.now()-start),bytes:bytes.length}));
