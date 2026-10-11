// Compare uniform source alpha and direct image paint at a retained pose.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const worker=path.join(root,'workers/remotion-benchmark');
const study=path.join(root,'docs/studios/research/editor-oss-20261002');
const folder=path.join(study,'temporal-matte-source-edge-controls');
const phase=process.argv[2];
if(!['native13','vector-guard','composite-inverse','target-inverse','svg-subtract'].includes(phase))throw new Error('unknown_diagnostic_phase');
const output=path.join(folder,phase);
const frozen=JSON.parse(await fs.readFile(path.join(output,'sources.json'),'utf8'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const basePath=path.join(folder,'base-manifest.json');
const base=JSON.parse(await fs.readFile(basePath,'utf8'));
const inputNames=['original','uniform50','uniform255','original-whitened'];
const bytes=Object.fromEntries(await Promise.all(inputNames.map(async name=>[name,await fs.readFile(path.join(folder,`${name}.png`))])));
const definitions=[['unmasked','original',false,false],['normal-original','original',false,false],
  ['inverse-original','original',true,false],['normal-uniform','uniform50',false,false],
  ['inverse-uniform','uniform50',true,false],['direct-original-whitened','original-whitened',false,true],
  ['direct-uniform50','uniform50',false,true],['direct-uniform255','uniform255',false,true]];
const require=createRequire(path.join(worker,'package.json'));
const {bundle}=require('@remotion/bundler');
const {selectComposition,renderStill,openBrowser}=require('@remotion/renderer');
const browserSource=JSON.parse(await fs.readFile(path.join(study,'spatial-effects-browser-sources.json'),'utf8'));
if(sha(await fs.readFile(browserSource.browserPath))!==browserSource.installedBrowserSha256)throw new Error('browser_drift');
const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'res-source-edge-'));let browser;const records=[];
try{
  const publicDir=path.join(temporary,'media');await fs.mkdir(publicDir);
  for(const [name,data] of Object.entries(bytes))await fs.writeFile(path.join(publicDir,`${name}.png`),data);
  const serveUrl=await bundle({entryPoint:path.join(worker,'src/hybrid.tsx'),publicDir,outDir:path.join(temporary,'bundle')});
  browser=await openBrowser('chrome',{browserExecutable:browserSource.browserPath,chromiumOptions:{gl:'swangle'},logLevel:'error'});
  for(const [name,image,invert,direct] of definitions){
    const manifest=structuredClone(base);
    const hero=manifest.layers.find(l=>l.name==='hero'),source=manifest.layers.find(l=>l.name==='matte');
    const assetId=hero.properties.recipeAssetMatte.assetId;
    hero.properties.recipeAssetMatte.invert=invert;
    if(name==='unmasked'||direct)delete hero.properties.recipeAssetMatte;
    if(direct){
      hero.visible=false;delete source.properties.matteSourceOnly;
      const parentId=manifest.nodes.find(n=>n.targetLayerId===source.id).parentNodeId;
      const parentLayerId=manifest.nodes.find(n=>n.nodeId===parentId).targetLayerId;
      manifest.layers.find(l=>l.id===parentLayerId).opacity=1;
    }
    manifest.assetFiles={[assetId]:{path:path.join(folder,`${image}.png`),sha256:sha(bytes[image]),mime:'image/png'}};
    await fs.writeFile(path.join(output,`${name}.json`),JSON.stringify(manifest));
    const inputManifest={...manifest,assets:{[assetId]:`${image}.png`}};delete inputManifest.assetFiles;
    const inputProps={manifest:inputManifest};
    const composition=await selectComposition({serveUrl,id:'ResHybrid',inputProps,puppeteerInstance:browser,
      chromiumOptions:{gl:'swangle'},logLevel:'error'});
    const png=path.join(output,`${name}.png`);
    await renderStill({serveUrl,composition,inputProps,frame:0,imageFormat:'png',output:png,puppeteerInstance:browser,
      chromiumOptions:{gl:'swangle'},logLevel:'error'});
    records.push({name,image,invert,direct,manifestSha256:sha(Buffer.from(JSON.stringify(manifest))),pngSha256:sha(await fs.readFile(png)),
      imageSha256:sha(bytes[image])});
  }
}finally{if(browser)await browser.close({silent:true});await fs.rm(temporary,{recursive:true,force:true});}
for(const [file,checksum] of Object.entries(frozen.sources))if(sha(await fs.readFile(path.join(root,file)))!==checksum)throw new Error(`source_drift:${file}`);
await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify({scope:'research_only_static_source_edge_controls',
  productionAdmission:'pending',phase,poseFrame:7,renderFrame:0,temporalExposure:false,
  directImageParentOpacity:1,baseManifestSha256:sha(await fs.readFile(basePath)),
  browserVersion:browserSource.installedBrowserVersion,browserSha256:browserSource.installedBrowserSha256,records},null,2));
console.log(JSON.stringify({phase,records:records.length}));
