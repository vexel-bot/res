// Research controls using the existing manifest/worker, never admission proof.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {deflateSync} from 'node:zlib';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const worker=path.join(root,'workers/remotion-benchmark');
const study=path.join(root,'docs/studios/research/editor-oss-20261002');
const subpixel=process.argv[2]==='subpixel';
const candidate=process.argv[2]==='svg-subtract'||subpixel;
const output=path.join(study,subpixel?'temporal-matte-subpixel-phase-controls':
  candidate?'temporal-matte-svg-subtract-uniform-controls':'temporal-matte-uniform-controls');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const baseline=JSON.parse(await fs.readFile(path.join(study,candidate?
  (subpixel?'temporal-matte-subpixel-phase-control-sources.json':'temporal-matte-svg-subtract-uniform-control-sources.json'):
  'temporal-matte-native13-current-sources.json'),'utf8'));
for(const [file,checksum] of Object.entries(baseline.sources)){
  if(sha(await fs.readFile(path.join(root,file)))!==checksum)throw new Error(`production_source_drift:${file}`);
}
try{await fs.access(output);throw new Error('diagnostic_evidence_already_exists');}
catch(error){if(error.code!=='ENOENT')throw error;}
await fs.mkdir(output);
const sourceFiles=['workers/remotion-benchmark/src/hybrid.tsx','workers/remotion-benchmark/src/asset-matte.tsx',
  'workers/remotion-benchmark/src/temporal-exposure.tsx','workers/remotion-benchmark/src/spatial-effects.ts',
  'workers/remotion-benchmark/src/typography-layout.tsx','scripts/validation/editor-temporal-matte-uniform-capture.mjs'];
const sourceHashes={};
for(const file of sourceFiles){
  const bytes=await fs.readFile(path.join(root,file));sourceHashes[file]=sha(bytes);
  const target=path.join(output,'source-bytes',file);await fs.mkdir(path.dirname(target),{recursive:true});
  await fs.writeFile(target,bytes);
}
// Exact authored RGBA fixtures, encoded without lossy conversion or resampling.
function crc32(bytes){let crc=0xffffffff;for(const byte of bytes){crc^=byte;
  for(let bit=0;bit<8;bit++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}return (crc^0xffffffff)>>>0;}
function chunk(type,bytes){const tag=Buffer.from(type),size=Buffer.alloc(4),crc=Buffer.alloc(4);
  size.writeUInt32BE(bytes.length);crc.writeUInt32BE(crc32(Buffer.concat([tag,bytes])));
  return Buffer.concat([size,tag,bytes,crc]);}
function uniformPng(alpha){const width=170,height=150,header=Buffer.alloc(13);
  header.writeUInt32BE(width,0);header.writeUInt32BE(height,4);header[8]=8;header[9]=6;
  const rows=Buffer.alloc((width*4+1)*height);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const index=y*(width*4+1)+1+x*4;rows[index]=rows[index+1]=rows[index+2]=255;rows[index+3]=alpha;
  }
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),
    chunk('IDAT',deflateSync(rows)),chunk('IEND',Buffer.alloc(0))]);}
const images={white:uniformPng(255),empty:uniformPng(0)};
for(const [name,bytes] of Object.entries(images))await fs.writeFile(path.join(output,`${name}.png`),bytes);
const basePath=path.join(study,'temporal-matte-isolated-samples/center.json');
const base=JSON.parse(await fs.readFile(basePath,'utf8'));
const variants=subpixel?Array.from({length:32},(_,index)=>{
  const scaled=index>=16,phase=(index%16+.25)/16;
  return {name:`${scaled?'scaled':'translated'}-phase-${index%16}`,hero:[phase,.25,0,scaled?1.12:1,scaled?.83:1]};
}):[
  {name:'identity',hero:[0,0,0,1,1]},
  {name:'fractional-translation',hero:[.35,.65,0,1,1]},
  {name:'small-affine',hero:[.375,.125,.15625,1.00078125,1]},
  {name:'rotation',hero:[24,8,12,1,1]},
  {name:'nonuniform-scale',hero:[.35,.65,0,1.12,.83]},
  {name:'rotation-scale',hero:[.35,.65,14,1.12,.83]},
  {name:'parented-hold',hero:[24,8,10,1.05,1],outer:[70,8,12,.95,1.1],rig:[20,-4,-10,1.08,.96]},
];
const modes=subpixel?['unmasked','normal-white-cover']:['unmasked','normal-white-local','normal-white-cover','inverse-empty'];
const records=[];
const require=createRequire(path.join(worker,'package.json'));
const {bundle}=require('@remotion/bundler');
const {selectComposition,renderStill,openBrowser}=require('@remotion/renderer');
const browserSource=JSON.parse(await fs.readFile(path.join(study,'spatial-effects-browser-sources.json'),'utf8'));
if(sha(await fs.readFile(browserSource.browserPath))!==browserSource.installedBrowserSha256)throw new Error('browser_source_drift');
const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'res-uniform-mask-'));
let browser;
try{
  const publicDir=path.join(temporary,'media');await fs.mkdir(publicDir);
  for(const [name,bytes] of Object.entries(images))await fs.writeFile(path.join(publicDir,`${name}.png`),bytes);
  const serveUrl=await bundle({entryPoint:path.join(worker,'src/hybrid.tsx'),publicDir,outDir:path.join(temporary,'bundle')});
  browser=await openBrowser('chrome',{browserExecutable:browserSource.browserPath,chromiumOptions:{gl:'swangle'},logLevel:'error'});
  for(const variant of variants){
    const selected=variant.name==='identity'?[...modes,'normal-empty-negative','inverse-white-negative']:modes;
    for(const mode of selected){
      const manifest=structuredClone(base);
      const hero=manifest.layers.find(l=>l.name==='hero'),source=manifest.layers.find(l=>l.name==='matte');
      const assetId=hero.properties.recipeAssetMatte.assetId;
      for(const layer of manifest.layers)delete layer.properties.recipeTemporalBlur;
      const paths=['position.x','position.y','rotation.degrees','scale.x','scale.y'];
      for(const name of ['outer','rig','hero']){
        const layer=manifest.layers.find(l=>l.name===name),values=variant[name]??[0,0,0,1,1];
        for(const [index,property] of paths.entries()){
          const track=manifest.tracks.find(t=>t.targetLayerId===layer.id&&t.propertyPath===property);
          track.keyframes=[{frame:0,value:values[index],easing:'linear',cubicBezier:null}];
        }
      }
      // The source shares the hero's parent and affine transform. A 3x source
      // centered on the same pivot covers the target without bitmap edges.
      const cover=mode==='normal-white-cover'||mode==='inverse-white-negative';
      source.x=hero.x-(cover?hero.width:0);source.y=hero.y-(cover?hero.height:0);
      source.width=hero.width*(cover?3:1);source.height=hero.height*(cover?3:1);source.opacity=1;
      manifest.nodes.find(n=>n.targetLayerId===source.id).parentNodeId=
        manifest.nodes.find(n=>n.targetLayerId===hero.id).parentNodeId;
      manifest.tracks=manifest.tracks.filter(t=>t.targetLayerId!==source.id);
      manifest.tracks.push(...manifest.tracks.filter(t=>t.targetLayerId===hero.id)
        .map(t=>({...structuredClone(t),targetLayerId:source.id})));
      const image=mode==='inverse-empty'||mode==='normal-empty-negative'?'empty':'white';
      hero.properties.recipeAssetMatte.invert=mode.startsWith('inverse-');
      if(mode==='unmasked')delete hero.properties.recipeAssetMatte;
      manifest.assetFiles={[assetId]:{path:path.join(output,`${image}.png`),sha256:sha(images[image]),mime:'image/png'}};
      const name=`${variant.name}--${mode}`;
      await fs.writeFile(path.join(output,`${name}.json`),JSON.stringify(manifest));
      const inputManifest={...manifest,assets:{[assetId]:`${image}.png`}};delete inputManifest.assetFiles;
      const inputProps={manifest:inputManifest};
      const composition=await selectComposition({serveUrl,id:'ResHybrid',inputProps,puppeteerInstance:browser,
        chromiumOptions:{gl:'swangle'},logLevel:'error'});
      const png=path.join(output,`${name}.png`);
      await renderStill({serveUrl,composition,inputProps,frame:0,imageFormat:'png',output:png,
        puppeteerInstance:browser,chromiumOptions:{gl:'swangle'},logLevel:'error'});
      records.push({name,variant:variant.name,mode,manifestSha256:sha(Buffer.from(JSON.stringify(manifest))),
        pngSha256:sha(await fs.readFile(png)),imageSha256:sha(images[image])});
      console.log(JSON.stringify({completed:records.length,name}));
    }
  }
}finally{
  if(browser)await browser.close({silent:true});
  await fs.rm(temporary,{recursive:true,force:true});
}
for(const [file,checksum] of Object.entries(baseline.sources)){
  if(sha(await fs.readFile(path.join(root,file)))!==checksum)throw new Error(`production_source_drift:${file}`);
}
for(const [file,checksum] of Object.entries(sourceHashes)){
  if(sha(await fs.readFile(path.join(root,file)))!==checksum)throw new Error(`diagnostic_source_drift:${file}`);
}
await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify({scope:'research_only_uniform_mask_lossless_controls',
  productionAdmission:'pending',baseManifestSha256:sha(await fs.readFile(basePath)),
  derivation:'Constant tracks, no temporal exposure; same parent/pivot for source and target; authored uniform PNGs.',
  browserVersion:browserSource.installedBrowserVersion,browserSha256:browserSource.installedBrowserSha256,
  variants,sourceHashes,productionSourceHashes:baseline.sources,records},null,2));
console.log(JSON.stringify({records:records.length,output}));
