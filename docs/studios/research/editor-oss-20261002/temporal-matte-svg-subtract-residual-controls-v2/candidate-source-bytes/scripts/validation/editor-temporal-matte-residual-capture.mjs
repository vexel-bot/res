// Derived lossless diagnostics; this does not admit a renderer or change an oracle.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const worker=path.join(root,'workers/remotion-benchmark');
const study=path.join(root,'docs/studios/research/editor-oss-20261002');
const output=path.join(study,'temporal-matte-svg-subtract-residual-controls-v2');
const sourceDir=path.join(study,'temporal-matte-native14-manifest-capture-2/rig-external-alpha-normal');
const canonicalPath=path.join(sourceDir,'canonical-manifest.json');
const maskPath=path.join(sourceDir,'original-matte.png');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const canonicalBytes=await fs.readFile(canonicalPath),maskBytes=await fs.readFile(maskPath);
const frozen=JSON.parse(await fs.readFile(path.join(output,'sources.json'),'utf8'));
const curve=(t,u,v)=>3*(1-t)**2*t*u+3*(1-t)*t*t*v+t**3;
// Match the pinned worker's 18-step easing solver for derived constant tracks.
function valueAt(keys,frame){
  if(frame<=keys[0].frame)return keys[0].value;
  for(let i=0;i<keys.length-1;i++){
    const a=keys[i],b=keys[i+1];if(frame>=b.frame)continue;
    let p=Math.max(0,Math.min(1,(frame-a.frame)/(b.frame-a.frame)));
    if(a.easing==='hold')p=0;
    else if(a.easing==='ease_in')p*=p;
    else if(a.easing==='ease_out')p=1-(1-p)**2;
    else if(a.easing==='ease_in_out')p=p<.5?2*p*p:1-(-2*p+2)**2/2;
    else if(a.easing==='cubic_bezier'&&a.cubicBezier){
      const [x1,y1,x2,y2]=a.cubicBezier;let low=0,high=1;
      for(let n=0;n<18;n++){const mid=(low+high)/2;if(curve(mid,x1,x2)<p)low=mid;else high=mid;}
      p=curve((low+high)/2,y1,y2);
    }
    return a.value+(b.value-a.value)*p;
  }
  return keys.at(-1).value;
}
const cases=[{name:'child-external-alpha-inverted',scope:'child',branch:'external',mode:'alpha',invert:true,frame:4},
  {name:'rig-common-luminance-normal',scope:'rig',branch:'common',mode:'luminance',invert:false,frame:7}];
const require=createRequire(path.join(worker,'package.json'));
const {bundle}=require('@remotion/bundler');
const {selectComposition,renderStill,openBrowser}=require('@remotion/renderer');
const browserSource=JSON.parse(await fs.readFile(path.join(study,'spatial-effects-browser-sources.json'),'utf8'));
if(sha(await fs.readFile(browserSource.browserPath))!==browserSource.installedBrowserSha256)throw new Error('browser_drift');
const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'res-matte-residual-'));let browser;const receipts=[];
try{
  const publicDir=path.join(temporary,'media');await fs.mkdir(publicDir);
  const publicName=sha(maskBytes)+'.png';await fs.writeFile(path.join(publicDir,publicName),maskBytes);
  const serveUrl=await bundle({entryPoint:path.join(worker,'src/hybrid.tsx'),publicDir,outDir:path.join(temporary,'bundle')});
  browser=await openBrowser('chrome',{browserExecutable:browserSource.browserPath,chromiumOptions:{gl:'swangle'},logLevel:'error'});
  for(const spec of cases){
    const folder=path.join(output,spec.name);await fs.mkdir(folder);
    const manifest=JSON.parse(canonicalBytes),byName=Object.fromEntries(manifest.layers.map(layer=>[layer.name,layer]));
    const hero=byName.hero,rig=byName.rig,assetId=Object.keys(manifest.assetFiles)[0];
    if(spec.scope==='child'){hero.properties.recipeTemporalBlur=rig.properties.recipeTemporalBlur;delete rig.properties.recipeTemporalBlur;}
    hero.properties.recipeAssetMatte={...hero.properties.recipeAssetMatte,mode:spec.mode,invert:spec.invert};
    if(spec.branch==='common'){
      const sourceParent=manifest.nodes.find(node=>node.targetLayerId===byName['mask-rig'].id);
      sourceParent.parentNodeId=manifest.nodes.find(node=>node.targetLayerId===byName.outer.id).nodeId;
      byName['mask-rig'].x=80;byName['mask-rig'].y=60;
    }
    manifest.assetFiles[assetId]={...manifest.assetFiles[assetId],path:maskPath,sha256:sha(maskBytes),mime:'image/png'};
    const sampledIds=spec.scope==='child'?[hero.id]:[rig.id,hero.id];
    const sampleTimes=Array.from({length:8},(_,i)=>spec.frame-.25+(i+.5)/8*.5);
    const manifests=[{name:'temporal',at:spec.frame,frame:spec.frame,manifest}];
    for(const [name,at] of [['center',spec.frame],...sampleTimes.map((at,i)=>[`sample-${i+1}`,at])]){
      const current=structuredClone(manifest);current.durationFrames=1;delete current.nativeCompositionDigest;
      for(const layer of current.layers){
        if(layer.properties.editorialTiming)layer.properties.editorialTiming={...layer.properties.editorialTiming,startFrame:0,durationFrames:1};
        delete layer.properties.recipeTemporalBlur;
        if(layer.properties.recipeAssetMatte)layer.properties.recipeAssetMatte={...layer.properties.recipeAssetMatte,startFrame:0,endFrameExclusive:1};
      }
      current.tracks=current.tracks.map(track=>({...track,keyframes:[{frame:0,
        value:valueAt(track.keyframes,sampledIds.includes(track.targetLayerId)?at:spec.frame),easing:'linear',cubicBezier:null}]}));
      manifests.push({name,at,frame:0,manifest:current});
    }
    const records=[];
    for(const item of manifests){
      const {name,frame,at,manifest:current}=item,raw=Buffer.from(JSON.stringify(current));
      await fs.writeFile(path.join(folder,`${name}.json`),raw);
      const inputManifest={...current,assets:{[assetId]:publicName}};delete inputManifest.assetFiles;
      const inputProps={manifest:inputManifest};
      const composition=await selectComposition({serveUrl,id:'ResHybrid',inputProps,puppeteerInstance:browser,
        chromiumOptions:{gl:'swangle'},logLevel:'error'});
      const png=path.join(folder,`${name}.png`);
      await renderStill({serveUrl,composition,inputProps,frame,imageFormat:'png',output:png,puppeteerInstance:browser,
        chromiumOptions:{gl:'swangle'},logLevel:'error'});
      records.push({name,sampleTime:at,renderFrame:frame,manifestSha256:sha(raw),pngSha256:sha(await fs.readFile(png))});
    }
    receipts.push({...spec,sampleTimes,sampledLayerIds:sampledIds,records});
  }
}finally{if(browser)await browser.close({silent:true});await fs.rm(temporary,{recursive:true,force:true});}
for(const [file,checksum] of Object.entries(frozen.sources))if(sha(await fs.readFile(path.join(root,file)))!==checksum)throw new Error(`source_drift:${file}`);
await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify({scope:'research_only_derived_lossless_residual_diagnostic',
  productionAdmission:'pending',canonicalManifestSha256:sha(canonicalBytes),maskSha256:sha(maskBytes),
  browserVersion:browserSource.installedBrowserVersion,browserSha256:browserSource.installedBrowserSha256,cases:receipts},null,2));
console.log(JSON.stringify({cases:receipts.length,captures:receipts.reduce((count,item)=>count+item.records.length,0)}));
