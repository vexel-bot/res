import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia,selectComposition} from '@remotion/renderer';
import {validateMattePngHeader} from './src/asset-matte-png.mjs';

const sha=(bytes)=>crypto.createHash('sha256').update(bytes).digest('hex');
const root=path.dirname(fileURLToPath(import.meta.url));
const [input,output]=process.argv.slice(2);
if(!input||!output)throw new Error('hybrid_paths_required');
const raw=await fs.readFile(input),manifest=JSON.parse(raw);
const encodeQuality=manifest.encodeQuality??'standard';
const videoCrf={draft:28,standard:23,high:1}[encodeQuality];
const pixelFormat=encodeQuality==='high'?'yuv444p':'yuv420p';
if(!['draft','standard','high'].includes(encodeQuality))throw new Error('hybrid_encode_quality_invalid');
if(manifest.schemaVersion!=='res.remotion-native-composition.v2'||![1,2,3,4,5,6,7].includes(manifest.componentLibraryVersion))throw new Error('hybrid_manifest_unsupported');
if(manifest.componentLibraryVersion<7&&manifest.layers.some(layer=>layer.properties.recipeTemporalBlur?.exposurePolicy)){
  throw new Error('hybrid_temporal_exposure_library_required');
}
if(manifest.layers.some(layer=>layer.properties.recipeTemporalBlur?.shutterAngle===0&&
  !layer.properties.recipeTemporalBlur.exposurePolicy))throw new Error('hybrid_temporal_zero_shutter_requires_policy');
if(![manifest.width,manifest.height,manifest.durationFrames].every(Number.isInteger)||manifest.width<320||manifest.height<320||
 Math.max(manifest.width,manifest.height)>3840||manifest.durationFrames<1||manifest.durationFrames>3600||
 !Number.isFinite(manifest.fps)||manifest.fps<=0||manifest.fps>60)throw new Error('hybrid_dimensions_invalid');
const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'res-hybrid-'));
const publicDir=path.join(temporary,'media');await fs.mkdir(publicDir);
const extensions={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp','video/mp4':'.mp4','video/webm':'.webm',
 'font/ttf':'.ttf','font/otf':'.otf','font/woff':'.woff','font/woff2':'.woff2'};
const assets={};const observed=new Map();const started=performance.now();
const matteAssetIds=new Set(manifest.layers.filter(layer=>layer.properties.matteSourceOnly).map(layer=>layer.properties.assetId));
let matteSourcePixels=0;
const hasVideo=manifest.layers.some(layer=>layer.kind==='video');
const freeMemoryAtStart=os.freemem();
const videoCacheBytes=hasVideo?Math.min(256*1024*1024,Math.floor(freeMemoryAtStart/4)):undefined;
if(hasVideo&&videoCacheBytes<64*1024*1024)throw new Error('hybrid_insufficient_video_decode_memory');
const concurrency=hasVideo?1:2;
try{
 for(const [id,ref] of Object.entries(manifest.assetFiles)){
  if(!extensions[ref.mime])throw new Error('hybrid_asset_type_unsupported');
  const bytes=await fs.readFile(ref.path);
  if(sha(bytes)!==ref.sha256)throw new Error('hybrid_asset_checksum_conflict');
  if(matteAssetIds.has(id)){
    try{matteSourcePixels=validateMattePngHeader(bytes,ref.mime,matteSourcePixels).totalPixels;}
    catch(error){throw new Error(`${String(error)}:asset=${id}`);}
  }
  const name=ref.sha256+extensions[ref.mime];await fs.writeFile(path.join(publicDir,name),bytes);assets[id]=name;
 }
 const inputProps={manifest:{...manifest,assets}};delete inputProps.manifest.assetFiles;
 const assetsReady=performance.now();
 const serveUrl=await bundle({entryPoint:path.join(root,'src','hybrid.tsx'),publicDir,outDir:path.join(temporary,'bundle')});
 const bundled=performance.now();
 const chromiumOptions={gl:'swangle'};
 const composition=await selectComposition({serveUrl,id:'ResHybrid',inputProps,chromiumOptions,logLevel:'error'});
 const selected=performance.now();
 await fs.mkdir(path.dirname(path.resolve(output)),{recursive:true});
 await renderMedia({serveUrl,composition,inputProps,chromiumOptions,codec:'h264',pixelFormat,outputLocation:path.resolve(output),
  imageFormat:'png',crf:videoCrf,concurrency,offthreadVideoCacheSizeInBytes:videoCacheBytes,logLevel:'error',onBrowserLog:log=>{
   if(log.text.startsWith('RES_GEOMETRY:')){const sample=JSON.parse(log.text.slice('RES_GEOMETRY:'.length));observed.set(sample.frame,sample);}
  }});
 const rendered=performance.now();
 const geometry=JSON.stringify([...observed.values()].sort((a,b)=>a.frame-b.frame));
 if(observed.size!==manifest.durationFrames)throw new Error('hybrid_geometry_incomplete');
 await fs.writeFile(path.join(path.dirname(path.resolve(output)),'geometry.json'),geometry);
 console.log(JSON.stringify({schemaVersion:'res.remotion-hybrid-receipt.v2',manifestSha256:sha(raw),videoSha256:sha(await fs.readFile(output)),
  geometrySha256:sha(geometry),frameCount:manifest.durationFrames,observedFrames:observed.size,
  durationMs:Math.round(performance.now()-started),nativeCompositionDigest:manifest.nativeCompositionDigest,
  rasterCapture:'png_lossless_intermediate',graphicsBackend:'chromium_swangle',
  encodeRole:'visual_intermediate',encodeQuality,videoCrf,pixelFormat,timingsMs:{
    assetPreparation:Math.round(assetsReady-started),bundle:Math.round(bundled-assetsReady),
    selectComposition:Math.round(selected-bundled),renderAndEncode:Math.round(rendered-selected)},
  decodeProfile:{concurrency,freeMemoryAtStart,videoCacheBytes:videoCacheBytes??null,
    matteAssetCount:matteAssetIds.size,matteSourcePixels},
  humanVisualReview:'pending'}));
}finally{await fs.rm(temporary,{recursive:true,force:true});}
