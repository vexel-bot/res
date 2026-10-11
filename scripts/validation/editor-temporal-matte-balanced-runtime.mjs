// Read the sealed candidate, and exercise its actual React compositor tree.
// These checks concern weights/time/reduction, not browser pixel approval.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const study=path.join(root,'docs/studios/research/editor-oss-20261002');
const source='workers/remotion-benchmark/src/temporal-exposure.tsx';
const candidate=path.join(study,'temporal-matte-native14-balanced-vector-guard-svg-subtract-quantized-full');
const sealed=JSON.parse(fs.readFileSync(path.join(candidate,'sources.json'),'utf8'));
const bytes=fs.readFileSync(path.join(candidate,'source-bytes',source));
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
assert.equal(sha(bytes),sealed.sources[source]);
const output=path.join(study,'temporal-matte-native14-balanced-runtime.json');
assert.ok(!fs.existsSync(output),'Preserve previous runtime evidence');
const requireWorker=createRequire(path.join(root,'workers/remotion-benchmark/package.json'));
const React=requireWorker('react'),context={exports:{},require:name=>{
  assert.equal(name,'react');return React;
}};
const code=ts.transpileModule(bytes.toString('utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,
  target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.React,esModuleInterop:true}}).outputText;
vm.runInNewContext(code,context,{timeout:5000});
const {exposureFrames,TemporalExposure}=context.exports;
const checks=[],check=(name,fn)=>{fn();checks.push({name,status:'passed'});};
const policy={schemaVersion:'studio.temporal-exposure.v1',sampling:'centered_clipped',coordinateSpace:'local_subtree',
  ancestorTime:'center_frame',compositing:'premultiplied_srgb_plus_lighter',staticReduction:'identical_registered_draw_inputs'};
const rectangle=time=>React.createElement('div',{'data-original-sample':time,style:{left:time*10,opacity:.5}});
const base={frame:4,start:0,end:30,samples:8,shutter:180,policy,zIndex:2,componentInputs:()=>null};

for(let samples=2;samples<=32;samples++)check(`all ${samples} leaves retain normalized equal exposure`,()=>{
  const tree=TemporalExposure({...base,samples,draw:rectangle});
  const diagnostic=JSON.parse(tree.props['data-temporal-exposure']),leaves=[];
  const visit=(node,weight)=>{
    if(node===undefined||node===null)return;
    if(Array.isArray(node)){node.forEach(child=>visit(child,weight));return;}
    assert.ok(React.isValidElement(node));
    if(node.props['data-original-sample']!==undefined){
      leaves.push({time:node.props['data-original-sample'],weight});return;
    }
    const style=node.props.style;
    assert.equal(style.position,'absolute');
    if(style.opacity!==undefined){assert.equal(style.mixBlendMode,'plus-lighter');weight*=style.opacity;}
    else assert.equal(style.isolation,'isolate');
    visit(node.props.children,weight);
  };
  visit(tree,1);
  assert.equal(leaves.length,samples);
  assert.deepEqual(leaves.map(leaf=>leaf.time),Array.from(exposureFrames(4,0,30,samples,180)));
  assert.ok(leaves.every(leaf=>Math.abs(leaf.weight-1/samples)<1e-14));
  assert.ok(Math.abs(leaves.reduce((sum,leaf)=>sum+leaf.weight,0)-1)<1e-14);
  assert.equal(diagnostic.actualSamples,samples);assert.equal(diagnostic.reduction,'none');
  assert.equal(diagnostic.pixelCoverageObserved,false);
});
check('stationary registered draw inputs reduce to center once',()=>{
  const tree=TemporalExposure({...base,draw:()=>rectangle(4)}),d=JSON.parse(tree.props['data-temporal-exposure']);
  assert.equal(d.actualSamples,1);assert.equal(d.reduction,'identical_registered_draw_inputs');
  assert.equal(tree.props.children.props['data-original-sample'],4);
});
function Unknown(){return null;}
check('unregistered draw inputs retain all sample leaves',()=>{
  const tree=TemporalExposure({...base,draw:()=>React.createElement(Unknown)});
  const d=JSON.parse(tree.props['data-temporal-exposure']);assert.equal(d.actualSamples,8);
  assert.equal(d.reduction,'none');
});
check('zero shutter bypasses averaging for unregistered components',()=>{
  const tree=TemporalExposure({...base,shutter:0,draw:()=>React.createElement(Unknown)});
  const d=JSON.parse(tree.props['data-temporal-exposure']);assert.equal(d.actualSamples,1);
  assert.equal(d.reduction,'zero_shutter');
});
check('frame zero clips and renormalizes within its interval',()=>
  assert.deepEqual(Array.from(exposureFrames(0,0,30,2,180)),[.0625,.1875]));
check('cut restarts at the next authored interval',()=>
  assert.deepEqual(Array.from(exposureFrames(30,30,60,2,180)),[30.0625,30.1875]));
check('sample past an exclusive end is rejected',()=>
  assert.throws(()=>exposureFrames(30,0,30,8,180),/interval_invalid/));
check('unregistered compositor policy is rejected',()=>assert.throws(()=>TemporalExposure({
  ...base,policy:{...policy,compositing:'screen'},draw:rectangle,
}),/policy_invalid/));
const report={scope:'sealed_native14_React_tree_equal_weights_time_reduction_not_pixel_evidence',
  passed:checks.length,checks,source,sourceSha256:sha(bytes),apiSourcesSha256:sha(fs.readFileSync(path.join(candidate,'sources.json'))),
  scriptSha256:sha(fs.readFileSync(fileURLToPath(import.meta.url)))};
fs.writeFileSync(output,JSON.stringify(report,null,2));
console.log(JSON.stringify({output,passed:checks.length}));
