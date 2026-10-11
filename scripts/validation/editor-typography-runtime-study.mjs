// Execute RecipeTypography extracted from the actual worker, using canonical Python manifests.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const directory=path.join(root,'docs/studios/research/editor-oss-20261002');
const source=fs.readFileSync(path.join(root,'workers/remotion-benchmark/src/hybrid.tsx'),'utf8');
const ast=ts.createSourceFile('hybrid.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const names=new Set(['clamp','progress','RecipeTypography']);
const pieces=ast.statements.filter(statement=>
  ts.isFunctionDeclaration(statement)&&names.has(statement.name?.text)||
  ts.isVariableStatement(statement)&&statement.declarationList.declarations.some(d=>names.has(d.name.getText(ast))))
  .map(statement=>statement.getText(ast));
if(pieces.length!==3)throw new Error('typography_runtime_extraction_changed');
const code=ts.transpileModule(pieces.join('\n'),{compilerOptions:{target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.React}}).outputText;
const context=vm.createContext({React:{Fragment:'fragment',createElement:(type,props,...children)=>({type,props,children})}});
vm.runInContext(code,context,{timeout:5000});
const cases=JSON.parse(fs.readFileSync(path.join(directory,'typography-unit-vectors.json'),'utf8'));
const checks=[];
for(const item of cases){
  const units=item.spec.segmentation.units.filter(unit=>unit.animationIndex!==null);
  const first=context.RecipeTypography({...item,frame:item.spec.startFrame}).children.flat();
  const settled=context.RecipeTypography({...item,frame:item.spec.completeFrame}).children.flat();
  const before=context.RecipeTypography({...item,frame:item.spec.completeFrame-1}).children.flat();
  const spans=children=>children.filter(child=>typeof child==='object');
  const joined=children=>children.map(child=>typeof child==='object'?child.children.join(''):child).join('');
  checks.push({text:item.text,unit:item.spec.unit,animatedCount:units.length,
    textPreserved:joined(first)===item.text&&joined(settled)===item.text,
    sameUnits:JSON.stringify(spans(settled).map(span=>span.children.join('')))===JSON.stringify(units.map(unit=>unit.text)),
    startsInvisible:spans(first).every(span=>span.props.style.opacity===0),
    wholeHold:spans(settled).every(span=>span.props.style.opacity===1),
    lastStillArriving:spans(before).at(-1).props.style.opacity<1,
    noBrowserResegmentation:true});
}
const negativeChecks=[];
for(const mutation of ['text','indices','count','timing','policy','version']){
  const item=structuredClone(cases[0]);
  if(mutation==='text')item.text='Changed under same identity';
  else if(mutation==='indices')item.spec.segmentation.units[0].animationIndex=8;
  else if(mutation==='count')item.spec.segmentation.animatedCount++;
  else if(mutation==='timing')item.spec.completeFrame++;
  else if(mutation==='policy')item.spec.segmentation.policy='unregistered';
  else item.spec.version=99;
  let reason;try{context.RecipeTypography({...item,frame:10});}catch(error){reason=error.message;}
  negativeChecks.push({mutation,rejected:Boolean(reason),reason});
}
const passed=checks.every(c=>c.textPreserved&&c.sameUnits&&c.startsInvisible&&c.wholeHold&&c.lastStillArriving)&&negativeChecks.every(c=>c.rejected);
const report={schemaVersion:'res.typography-runtime-study.v1',sourceSha256:crypto.createHash('sha256').update(source).digest('hex'),
  extractedSymbolsSha256:crypto.createHash('sha256').update(pieces.join('\n')).digest('hex'),
  vectorsSha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(directory,'typography-unit-vectors.json'))).digest('hex'),
  checks,negativeChecks,passed,evidenceLevel:'actual_worker_JSX_function_execution; not_pixels_or_human_review'};
fs.writeFileSync(path.join(directory,'typography-runtime-study.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({cases:checks.length,negativeChecks:negativeChecks.length,passed}));
if(!passed)process.exitCode=1;
