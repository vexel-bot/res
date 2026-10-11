import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const worker=path.join(root,'workers/remotion-benchmark');
const require=createRequire(path.join(worker,'package.json'));
const {bundle}=require('@remotion/bundler');
const {selectComposition,renderStill}=require('@remotion/renderer');
const folder=path.join(root,'docs/studios/research/editor-oss-20261002/temporal-rig-raster');
const outDir=path.join(root,'tmp/temporal-rig-raster-bundle');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const serveUrl=await bundle({entryPoint:path.join(worker,'src/hybrid.tsx'),outDir});
const captures=[];
for(const variant of ['control','rig','child','disjoint']){
  const bytes=await fs.readFile(path.join(folder,variant+'.json'));
  const manifest=JSON.parse(bytes);manifest.assets={};delete manifest.assetFiles;
  const inputProps={manifest};
  const composition=await selectComposition({serveUrl,id:'ResHybrid',inputProps,logLevel:'error'});
  for(const frame of [0,6]){
    const output=path.join(folder,`${variant}-frame-${frame}.png`);
    await renderStill({serveUrl,composition,inputProps,frame,imageFormat:'png',output,logLevel:'error',onBrowserLog:()=>{}});
    captures.push({variant,frame,manifestSha256:sha(bytes),pngSha256:sha(await fs.readFile(output))});
  }
}
await fs.writeFile(path.join(folder,'capture.json'),JSON.stringify({scope:'reconstructed_lossless_browser_diagnostic',
  bundlePath:serveUrl,hybridSha256:sha(await fs.readFile(path.join(worker,'src/hybrid.tsx'))),captures},null,2));
console.log(JSON.stringify({captures:captures.length,bundlePath:serveUrl}));
