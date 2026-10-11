// Exercise the original worker's typed guard; this is not browser/pixel qualification.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import ts from 'typescript';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const source='workers/remotion-benchmark/src/spatial-effects.ts';
const bytes=fs.readFileSync(path.join(root,source));
const context={exports:{}};
const code=ts.transpileModule(bytes.toString('utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,
  target:ts.ScriptTarget.ES2022}}).outputText;
vm.runInNewContext(code,context,{timeout:5000});
const {spatialFilter}=context.exports,checks=[];
const check=(name,fn)=>{fn();checks.push({name,status:'passed'});};
const shadow={x:32,y:-12,blur:4,color:'#123456',opacity:.5};
check('identity omits the effect surface',()=>assert.equal(spatialFilter(0,null,'target'),undefined));
check('canonical offsets and alpha affect only the shadow',()=>assert.equal(spatialFilter(0,shadow,'target'),
  'drop-shadow(32px -12px 4px rgba(18,52,86,0.5))'));
check('blur before shadow uses the registered order',()=>assert.equal(spatialFilter(4,shadow,'target'),
  'blur(4px) drop-shadow(32px -12px 4px rgba(18,52,86,0.5))'));
check('transparent shadow omits identity',()=>assert.equal(spatialFilter(0,{...shadow,opacity:0},'target'),undefined));
check('transparent shadow retains spatial blur',()=>assert.equal(spatialFilter(4,{...shadow,opacity:0},'target'),'blur(4px)'));
check('graph blur range preserved',()=>assert.equal(spatialFilter(500,null,'target'),'blur(500px)'));
for (const value of [-1,501,NaN,Infinity,'4']) {
  check(`invalid blur ${String(value)}`,()=>assert.throws(()=>spatialFilter(value,null,'probe'),
    /hybrid_spatial_blur_invalid:target=probe/));
}
for (const [name,value] of [
  ['missing fields',{}],['unknown alias',{...shadow,offsetX:32}],['CSS injection',{...shadow,color:'url(free)'}],
  ['outside x',{...shadow,x:101}],['outside y',{...shadow,y:-101}],['negative sigma',{...shadow,blur:-1}],
  ['outside sigma',{...shadow,blur:101}],['outside opacity',{...shadow,opacity:1.01}],
  ['nonfinite opacity',{...shadow,opacity:NaN}],['nonfinite offset',{...shadow,y:Infinity}],
  ['array',[]],['untyped string','free CSS'],
]) check(name,()=>assert.throws(()=>spatialFilter(0,value,'probe'),/hybrid_spatial_shadow_invalid:target=probe/));
const report={scope:'actual original TypeScript guard; no browser/pixel claim',passed:checks.length,checks,source,
  sourceSha256:crypto.createHash('sha256').update(bytes).digest('hex')};
const output=path.join(root,'docs/studios/research/editor-oss-20261002/spatial-effects-runtime-study.json');
fs.writeFileSync(output,JSON.stringify(report,null,2));
console.log(JSON.stringify({output,passed:report.passed}));
