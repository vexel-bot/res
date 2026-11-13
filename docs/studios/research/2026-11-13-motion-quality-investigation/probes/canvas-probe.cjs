const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const crypto=require('node:crypto');
const out=path.resolve(process.argv[3] || '.codex-runtime/clicko-dev/motion-quality-probe-replay');
fs.mkdirSync(out,{recursive:true});
const html=path.resolve(process.argv[2] || 'C:/Users/edugu/Downloads/clicko-orbita-independent-20261112/src/orbita.html');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext();
 await context.route(/^https?:/,route=>route.abort());
 async function page(){const p=await context.newPage();await p.goto(pathToFileURL(html).href);await p.evaluate(()=>window.ORBITA.ready);return p;}
 const p=await page(); const samples=[];const initial=new Map();const start=Date.now();
 for(const second of [3.4,7.9666666667,8,8.1,11.4,15.9,8,3.4]){
  const data=await p.evaluate(t=>{
   window.ORBITA.renderFrame(t); const c=document.querySelector('canvas');const a=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
   let alphaMin=255,alphaMax=0,mean=0;for(let i=0;i<a.length;i+=4){alphaMin=Math.min(alphaMin,a[i+3]);alphaMax=Math.max(alphaMax,a[i+3]);mean+=.2126*a[i]+.7152*a[i+1]+.0722*a[i+2];}
   return {png:c.toDataURL('image/png').split(',')[1],alphaMin,alphaMax,meanLuma:mean/(a.length/4)};
  },second);
  const buffer=Buffer.from(data.png,'base64');const digest=hash(buffer);delete data.png;
  const repeated=initial.has(second);samples.push({second,...data,pngSha256:digest,repeated,sameAsEarlier:repeated?initial.get(second)===digest:null});
  if(!repeated){initial.set(second,digest);fs.writeFileSync(path.join(out,'frame-'+String(second).replace('.','_')+'.png'),buffer);}
 }
 const p2=await page();const independent=await p2.evaluate(()=>window.ORBITA.frameData(3.4));const other=hash(Buffer.from(independent.split(',')[1],'base64'));
 const result={probe:'existing-canvas-renderer-repeatability-and-alpha',apiSpendUsd:0,sourceModified:false,newAdvertisementGenerated:false,source:html,
  rendererSeconds:(Date.now()-start)/1000,allRepeatedFramesIdentical:samples.filter(s=>s.repeated).every(s=>s.sameAsEarlier),freshPageSameFrame:other===initial.get(3.4),samples,
  limitations:['Tests selected still-frame rendering only; not full motion, auditory review, engine parity, or viewer approval.','Opaque output may be correct for full-scene rendering; transparent layer compositing requires a separate contract and test.']};
 fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2));await browser.close();console.log(JSON.stringify(result));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
