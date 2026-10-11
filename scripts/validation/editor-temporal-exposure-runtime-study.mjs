// Execute the original worker helper without substituting its sampler or reducer.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const source='workers/remotion-benchmark/src/temporal-exposure.tsx';
const bytes=fs.readFileSync(path.join(root,source));
const requireWorker=createRequire(path.join(root,'workers/remotion-benchmark/package.json'));
const React=requireWorker('react'),context={exports:{},require:name=>{
  if(name!=='react')throw new Error('unexpected runtime import');return React;
}};
const code=ts.transpileModule(bytes.toString('utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,
  target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.React,esModuleInterop:true}}).outputText;
vm.runInNewContext(code,context,{timeout:5000});
const {exposureFrames,visualFingerprint,TemporalExposure}=context.exports,checks=[];
const check=(name,fn)=>{fn();checks.push({name,status:'passed'});};
const normalizer=()=>null;
check('centered two-point quadrature',()=>assert.deepEqual(Array.from(exposureFrames(4,0,30,2,180)),[3.875,4.125]));
check('first-frame clipped and renormalized',()=>assert.deepEqual(Array.from(exposureFrames(0,0,30,2,180)),[.0625,.1875]));
check('cut starts at its own interval',()=>assert.deepEqual(Array.from(exposureFrames(30,30,60,2,180)),[30.0625,30.1875]));
check('zero shutter is the requested frame',()=>assert.deepEqual(Array.from(exposureFrames(29,0,30,8,0)),[29]));
check('fractional end clips before exclusive endpoint',()=>{
  const frames=Array.from(exposureFrames(29.9,0,30,2,360));
  assert.ok(Math.abs(frames[0]-29.55)<1e-10&&Math.abs(frames[1]-29.85)<1e-10);
});
for(const [name,values] of [
  ['outside interval',[30,0,30,8,180]],['empty interval',[0,0,0,8,180]],
  ['nonfinite time',[NaN,0,30,8,180]],['one sample',[4,0,30,1,180]],
  ['over sample cap',[4,0,30,33,180]],['fractional samples',[4,0,30,2.5,180]],
  ['negative shutter',[4,0,30,8,-1]],['over shutter cap',[4,0,30,8,361]],
])check(name,()=>assert.throws(()=>exposureFrames(...values),/interval_invalid/));
const rectangle=(x=20,opacity=.5)=>React.createElement('div',{style:{left:x,opacity,background:'#dcb446'}});
check('same draw inputs have same fingerprint',()=>assert.equal(visualFingerprint(rectangle(),normalizer),visualFingerprint(rectangle(),normalizer)));
check('position changes cannot reduce',()=>assert.notEqual(visualFingerprint(rectangle(20),normalizer),visualFingerprint(rectangle(21),normalizer)));
check('opacity changes cannot reduce',()=>assert.notEqual(visualFingerprint(rectangle(20,.5),normalizer),visualFingerprint(rectangle(20,.6),normalizer)));
function Unknown(){return null;}
check('unregistered component cannot reduce',()=>assert.equal(visualFingerprint(React.createElement(Unknown),normalizer),null));
check('unknown function prop cannot reduce',()=>assert.equal(visualFingerprint(React.createElement('div',{onClick:()=>{}}),normalizer),null));
const policy={schemaVersion:'studio.temporal-exposure.v1',sampling:'centered_clipped',coordinateSpace:'local_subtree',
  ancestorTime:'center_frame',compositing:'premultiplied_srgb_plus_lighter',staticReduction:'identical_registered_draw_inputs'};
const base={frame:4,start:0,end:30,samples:8,shutter:180,policy,zIndex:2,componentInputs:normalizer};
function diagnostic(props){return JSON.parse(TemporalExposure(props).props['data-temporal-exposure']);}
check('stationary compositor uses center once',()=>{
  const d=diagnostic({...base,draw:()=>rectangle()});assert.equal(d.actualSamples,1);
  assert.equal(d.reduction,'identical_registered_draw_inputs');assert.deepEqual(d.sampleFrames,[4]);
});
check('moving compositor retains samples and normalized weights',()=>{
  const d=diagnostic({...base,draw:time=>rectangle(time*10)});assert.equal(d.actualSamples,8);
  assert.equal(d.sampleWeights.reduce((a,b)=>a+b,0),1);assert.equal(d.pixelCoverageObserved,false);
});
check('zero shutter bypasses averaging even for unknown component',()=>{
  const d=diagnostic({...base,shutter:0,draw:()=>React.createElement(Unknown)});
  assert.equal(d.actualSamples,1);assert.equal(d.reduction,'zero_shutter');
});
check('unregistered compositing is rejected',()=>assert.throws(()=>TemporalExposure({
  ...base,policy:{...policy,compositing:'screen'},draw:()=>rectangle(),
}),/policy_invalid/));
const report={scope:'actual original React sampler/reducer; no browser or pixel claim',passed:checks.length,checks,
  source,sourceSha256:crypto.createHash('sha256').update(bytes).digest('hex')};
const output=path.join(root,'docs/studios/research/editor-oss-20261002/temporal-exposure-runtime-study.json');
fs.writeFileSync(output,JSON.stringify(report,null,2));console.log(JSON.stringify({output,passed:report.passed}));
