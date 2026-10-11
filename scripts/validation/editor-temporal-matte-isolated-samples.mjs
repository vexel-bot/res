import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';

const run=promisify(execFile);
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const study=path.join(root,'docs/studios/research/editor-oss-20261002');
const sourceDir=path.join(study,'temporal-matte-native14-manifest-capture-2/rig-external-alpha-normal');
const basePath=path.join(sourceDir,'canonical-manifest.json');
const maskPath=path.join(sourceDir,'original-matte.png');
const outDir=path.join(study,'temporal-matte-isolated-samples');
const worker=path.join(root,'workers/remotion-benchmark');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const clamp=x=>Math.max(0,Math.min(1,x));
const curve=(t,u,v)=>3*(1-t)**2*t*u+3*(1-t)*t*t*v+t**3;
function valueAt(keys,frame){
  if(frame<=keys[0].frame)return keys[0].value;
  for(let i=0;i<keys.length-1;i++){
    const a=keys[i],b=keys[i+1];if(frame>=b.frame)continue;
    let p=clamp((frame-a.frame)/(b.frame-a.frame));
    if(a.easing==='hold')p=0;
    else if(a.easing==='ease_in')p*=p;
    else if(a.easing==='ease_out')p=1-(1-p)**2;
    else if(a.easing==='ease_in_out')p=p<.5?2*p*p:1-(-2*p+2)**2/2;
    else if(a.easing==='cubic_bezier'&&a.cubicBezier){
      const [x1,y1,x2,y2]=a.cubicBezier;let low=0,high=1;
      for(let n=0;n<18;n++){const m=(low+high)/2;if(curve(m,x1,x2)<p)low=m;else high=m;}
      p=curve((low+high)/2,y1,y2);
    }
    return a.value+(b.value-a.value)*p;
  }
  return keys.at(-1).value;
}
const manifest=JSON.parse(await fs.readFile(basePath,'utf8'));
const maskBytes=await fs.readFile(maskPath);
const assetId=Object.keys(manifest.assetFiles)[0];
manifest.assetFiles[assetId]={...manifest.assetFiles[assetId],path:maskPath,sha256:sha(maskBytes),mime:'image/png'};
const layerById=new Map(manifest.layers.map(layer=>[layer.id,layer]));
const nodeByLayer=new Map(manifest.nodes.map(node=>[node.targetLayerId,node]));
const nodeToLayer=new Map(manifest.nodes.map(node=>[node.nodeId,node.targetLayerId]));
const children=new Map();
for(const node of manifest.nodes){
  const parent=node.parentNodeId?nodeToLayer.get(node.parentNodeId):null;
  const list=children.get(parent)??[];list.push(node.targetLayerId);children.set(parent,list);
}
const descendants=(rootId)=>{const result=new Set([rootId]);const visit=id=>{for(const child of children.get(id)??[]){if(!result.has(child)){result.add(child);visit(child);}}};visit(rootId);return result;};
const sampled=descendants(manifest.layers.find(layer=>layer.name==='rig').id);
const centerFrame=0;
const sampleTimes=Array.from({length:8},(_,i)=>(i+.5)/8*.25);
await fs.rm(outDir,{recursive:true,force:true});
await fs.mkdir(outDir,{recursive:true});
const records=[];
for(const [index,time] of [[0,centerFrame],...sampleTimes.map((value,i)=>[i+1,value])]){
  const current=structuredClone(manifest);
  current.durationFrames=1;
  for(const layer of current.layers){
    const timing=layer.properties.editorialTiming;
    if(timing)layer.properties.editorialTiming={...timing,startFrame:0,durationFrames:1};
    delete layer.properties.recipeTemporalBlur;
    if(layer.properties.recipeAssetMatte)layer.properties.recipeAssetMatte={...layer.properties.recipeAssetMatte,startFrame:0,endFrameExclusive:1};
  }
  current.tracks=current.tracks.map(track=>{
    const at=sampled.has(track.targetLayerId)?time:centerFrame;
    const value=valueAt(track.keyframes,at);
    return {...track,keyframes:[{frame:0,value,easing:'linear',cubicBezier:null}]};
  });
  current.nativeCompositionDigest=undefined;
  const name=index===0?'center':`sample-${index}`;
  const manifestPath=path.join(outDir,`${name}.json`);
  const videoPath=path.join(outDir,`${name}.mp4`);
  await fs.writeFile(manifestPath,JSON.stringify(current));
  await run('node',[path.join(worker,'render-hybrid.mjs'),manifestPath,videoPath],{cwd:worker,timeout:120000,maxBuffer:2*1024*1024});
  records.push({name,time,manifestSha256:sha(await fs.readFile(manifestPath)),videoSha256:sha(await fs.readFile(videoPath))});
}
await fs.writeFile(path.join(outDir,'receipt.json'),JSON.stringify({scope:'isolated_single_sample_diagnostic_from_actual_canonical_manifest',sourceManifestSha256:sha(await fs.readFile(basePath)),maskSha256:sha(maskBytes),sampledLayerIds:[...sampled],centerFrame,sampleTimes,records},null,2));
console.log(JSON.stringify({scope:'isolated_single_sample_diagnostic',records:records.length,outDir}));
