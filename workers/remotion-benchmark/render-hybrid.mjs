import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia,selectComposition} from '@remotion/renderer';

const sha=(bytes)=>crypto.createHash('sha256').update(bytes).digest('hex');
const root=path.dirname(fileURLToPath(import.meta.url));
const [input,output]=process.argv.slice(2);
if(!input||!output)throw new Error('hybrid_paths_required');
const raw=await fs.readFile(input),manifest=JSON.parse(raw);
if(manifest.schemaVersion!=='res.remotion-native-composition.v2'||![1,2].includes(manifest.componentLibraryVersion))throw new Error('hybrid_manifest_unsupported');
if(![manifest.width,manifest.height,manifest.durationFrames].every(Number.isInteger)||manifest.width<320||manifest.height<320||
 Math.max(manifest.width,manifest.height)>3840||manifest.durationFrames<1||manifest.durationFrames>3600||
 !Number.isFinite(manifest.fps)||manifest.fps<=0||manifest.fps>60)throw new Error('hybrid_dimensions_invalid');
const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'res-hybrid-'));
const publicDir=path.join(temporary,'media');await fs.mkdir(publicDir);
const extensions={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp','video/mp4':'.mp4','video/webm':'.webm',
 'font/ttf':'.ttf','font/otf':'.otf','font/woff':'.woff','font/woff2':'.woff2'};
const assets={};const observed=new Map();const started=performance.now();
try{
 for(const [id,ref] of Object.entries(manifest.assetFiles)){
  if(!extensions[ref.mime])throw new Error('hybrid_asset_type_unsupported');
  const bytes=await fs.readFile(ref.path);
  if(sha(bytes)!==ref.sha256)throw new Error('hybrid_asset_checksum_conflict');
  const name=ref.sha256+extensions[ref.mime];await fs.writeFile(path.join(publicDir,name),bytes);assets[id]=name;
 }
 const inputProps={manifest:{...manifest,assets}};delete inputProps.manifest.assetFiles;
 const serveUrl=await bundle({entryPoint:path.join(root,'src','hybrid.tsx'),publicDir,outDir:path.join(temporary,'bundle')});
 const composition=await selectComposition({serveUrl,id:'ResHybrid',inputProps,logLevel:'error'});
 await fs.mkdir(path.dirname(path.resolve(output)),{recursive:true});
 await renderMedia({serveUrl,composition,inputProps,codec:'h264',pixelFormat:'yuv420p',outputLocation:path.resolve(output),
  concurrency:2,logLevel:'error',onBrowserLog:log=>{
   if(log.text.startsWith('RES_GEOMETRY:')){const sample=JSON.parse(log.text.slice('RES_GEOMETRY:'.length));observed.set(sample.frame,sample);}
  }});
 const geometry=JSON.stringify([...observed.values()].sort((a,b)=>a.frame-b.frame));
 if(observed.size!==manifest.durationFrames)throw new Error('hybrid_geometry_incomplete');
 await fs.writeFile(path.join(path.dirname(path.resolve(output)),'geometry.json'),geometry);
 console.log(JSON.stringify({schemaVersion:'res.remotion-hybrid-receipt.v2',manifestSha256:sha(raw),videoSha256:sha(await fs.readFile(output)),
  geometrySha256:sha(geometry),frameCount:manifest.durationFrames,observedFrames:observed.size,
  durationMs:Math.round(performance.now()-started),nativeCompositionDigest:manifest.nativeCompositionDigest,
  humanVisualReview:'pending'}));
}finally{await fs.rm(temporary,{recursive:true,force:true});}
