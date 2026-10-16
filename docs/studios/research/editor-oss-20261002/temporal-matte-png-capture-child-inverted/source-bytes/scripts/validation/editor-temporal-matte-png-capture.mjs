import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const worker=path.join(root,'workers/remotion-benchmark');
const study=path.join(root,'docs/studios/research/editor-oss-20261002');
const canonicalPath=path.join(study,'temporal-matte-native14-manifest-capture-2/rig-external-alpha-normal/canonical-manifest.json');
const maskPath=path.join(study,'temporal-matte-native14-manifest-capture-2/rig-external-alpha-normal/original-matte.png');
const isolatedDir=path.join(study,'temporal-matte-isolated-samples');
const fixture=process.argv[2]??'rig';
if(!['rig','child-inverted'].includes(fixture))throw new Error('unknown_diagnostic_fixture');
const outputDir=path.join(study,fixture==='rig'?'temporal-matte-png-capture':'temporal-matte-png-capture-child-inverted');
const require=createRequire(path.join(worker,'package.json'));
const {bundle}=require('@remotion/bundler');
const {selectComposition,renderStill}=require('@remotion/renderer');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const canonical=JSON.parse(await fs.readFile(canonicalPath,'utf8'));
const maskBytes=await fs.readFile(maskPath);
const assetId=Object.keys(canonical.assetFiles)[0];
canonical.assetFiles[assetId]={...canonical.assetFiles[assetId],path:maskPath,sha256:sha(maskBytes),mime:'image/png'};
const manifests=[['temporal',canonical]];
for(const name of ['center',...Array.from({length:8},(_,i)=>`sample-${i+1}`)]){
  manifests.push([name,JSON.parse(await fs.readFile(path.join(isolatedDir,`${name}.json`),'utf8'))]);
}
if(fixture==='child-inverted'){
  const rig=canonical.layers.find(layer=>layer.name==='rig');
  const hero=canonical.layers.find(layer=>layer.name==='hero');
  const policy=rig.properties.recipeTemporalBlur;
  hero.properties.recipeTemporalBlur=policy;
  delete rig.properties.recipeTemporalBlur;
  for(const [name,manifest] of manifests){
    manifest.layers.find(layer=>layer.name==='hero').properties.recipeAssetMatte.invert=true;
    if(name==='temporal')continue;
    // Only the child is sampled. The rig and every external dependency stay
    // at center frame 0, as required by the production local-subtree policy.
    for(const track of manifest.tracks.filter(track=>track.targetLayerId===rig.id)){
      const authored=canonical.tracks.find(candidate=>candidate.targetLayerId===track.targetLayerId&&
        candidate.propertyPath===track.propertyPath);
      track.keyframes=[{...authored.keyframes[0],frame:0}];
    }
  }
}
try{await fs.access(outputDir);throw new Error('diagnostic_evidence_already_exists');}
catch(error){if(error.code!=='ENOENT')throw error;}
await fs.mkdir(outputDir,{recursive:true});
const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'res-matte-png-'));
const publicDir=path.join(temporary,'media');await fs.mkdir(publicDir);
const publicName=sha(maskBytes)+'.png';await fs.writeFile(path.join(publicDir,publicName),maskBytes);
const serveUrl=await bundle({entryPoint:path.join(worker,'src','hybrid.tsx'),publicDir,outDir:path.join(temporary,'bundle')});
const records=[];
try{
  for(const [name,manifest] of manifests){
    const inputManifest={...manifest,assets:{[assetId]:publicName}};delete inputManifest.assetFiles;
    const inputProps={manifest:inputManifest};
    const composition=await selectComposition({serveUrl,id:'ResHybrid',inputProps,chromiumOptions:{gl:'swangle'},logLevel:'error'});
    const output=path.join(outputDir,`${name}.png`);
    await renderStill({serveUrl,composition,inputProps,frame:0,imageFormat:'png',output,
      chromiumOptions:{gl:'swangle'},logLevel:'error'});
    records.push({name,manifestSha256:sha(Buffer.from(JSON.stringify(manifest))),pngSha256:sha(await fs.readFile(output))});
  }
}finally{await fs.rm(temporary,{recursive:true,force:true});}
const sourceFiles=['workers/remotion-benchmark/src/hybrid.tsx','workers/remotion-benchmark/src/asset-matte.tsx',
  'workers/remotion-benchmark/src/temporal-exposure.tsx','scripts/validation/editor-temporal-matte-png-capture.mjs'];
const sourceHashes=Object.fromEntries(await Promise.all(sourceFiles.map(async file=>[
  file,sha(await fs.readFile(path.join(root,file)))
])));
await fs.writeFile(path.join(outputDir,'receipt.json'),JSON.stringify({scope:'lossless_browser_png_composition_diagnostic',
  canonicalManifestSha256:sha(await fs.readFile(canonicalPath)),maskSha256:sha(maskBytes),
  fixture,derivation:fixture==='child-inverted'?{sampledTarget:'hero',externalRigFrame:0,matteMode:'alpha',matteInvert:true}:null,
  sourceHashes,records},null,2));
console.log(JSON.stringify({records:records.length,outputDir}));
