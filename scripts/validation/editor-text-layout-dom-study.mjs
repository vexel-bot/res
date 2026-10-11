import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const worker=path.join(root,'workers/remotion-benchmark');
const require=createRequire(path.join(worker,'package.json'));
const {bundle}=require('@remotion/bundler');
const {renderStill,selectComposition}=require('@remotion/renderer');
const folder=path.join(root,'tmp','text-layout-dom-study-'+crypto.randomUUID());
const publicDir=path.join(folder,'public');await fs.mkdir(publicDir,{recursive:true});
const font=process.env.TYPOGRAPHY_TEST_FONT||'C:/Windows/Fonts/arial.ttf';
const bytes=await fs.readFile(font);await fs.writeFile(path.join(publicDir,'study.ttf'),bytes);
const boldBytes=await fs.readFile(process.env.TYPOGRAPHY_TEST_BOLD_FONT||'C:/Windows/Fonts/arialbd.ttf');
await fs.writeFile(path.join(publicDir,'study-bold.ttf'),boldBytes);
const serveUrl=await bundle({entryPoint:path.join(worker,'tests/typography-layout-study.tsx'),publicDir,
  outDir:path.join(folder,'bundle')});
const composition=await selectComposition({serveUrl,id:'TextLayoutStudy',logLevel:'error'});
let report;
await renderStill({serveUrl,composition,frame:0,output:null,logLevel:'error',onBrowserLog:log=>{
  if(log.text.startsWith('RES_TEXT_LAYOUT_STUDY:'))report=JSON.parse(log.text.slice('RES_TEXT_LAYOUT_STUDY:'.length));
}});
if(!report||report.passed!==13)throw new Error('text_layout_dom_study_incomplete');
const output=path.join(root,'docs/studios/research/editor-oss-20261002/text-layout-dom-study.json');
await fs.writeFile(output,JSON.stringify({...report,fontSha256:crypto.createHash('sha256').update(bytes).digest('hex'),
  boldFontSha256:crypto.createHash('sha256').update(boldBytes).digest('hex'),
  cleanupDirectory:folder,sourceHashes:Object.fromEntries(await Promise.all([
    'workers/remotion-benchmark/src/typography-layout.tsx','workers/remotion-benchmark/tests/typography-layout-study.tsx',
    'scripts/validation/editor-text-layout-dom-study.mjs',
  ].map(async name=>[name,crypto.createHash('sha256').update(await fs.readFile(path.join(root,name))).digest('hex')]))),
},null,2));
console.log(JSON.stringify({output,passed:report.passed,cleanupDirectory:folder}));
