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
const folder=path.join(root,'docs/studios/research/editor-oss-20261002/temporal-raster-diagnostic');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const serveUrl=await bundle({entryPoint:path.join(worker,'src/hybrid.tsx')});
const records=[];
for(const name of ['samples-0-shutter-180','samples-2-shutter-180','samples-8-shutter-180','samples-16-shutter-180','samples-8-shutter-0']){
  const bytes=await fs.readFile(path.join(folder,name+'.json'));
  const manifest=JSON.parse(bytes);manifest.assets={};delete manifest.assetFiles;
  const inputProps={manifest};
  const composition=await selectComposition({serveUrl,id:'ResHybrid',inputProps,logLevel:'error'});
  for(const frame of [4,34]){
    const output=path.join(folder,`${name}-frame-${frame}.png`);
    await renderStill({serveUrl,composition,inputProps,frame,imageFormat:'png',output,logLevel:'error'});
    records.push({name,frame,manifestSha256:sha(bytes),pngSha256:sha(await fs.readFile(output)),png:path.basename(output)});
  }
}
const sources={};
for(const name of ['src/hybrid.tsx','src/temporal-exposure.tsx'])sources[name]=sha(await fs.readFile(path.join(worker,name)));
await fs.writeFile(path.join(folder,'capture.json'),JSON.stringify({scope:'lossless_browser_diagnostic_reconstructed_fixture_not_API_job',bundlePath:serveUrl,records,sources},null,2));
console.log(JSON.stringify({records:records.length,folder}));
