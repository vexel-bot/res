// Original diagnostic study: execute the current res evaluator, without importing an external engine.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const sourcePath = path.join(root, 'workers/remotion-benchmark/src/hybrid.tsx');
const source = fs.readFileSync(sourcePath, 'utf8');
const ast = ts.createSourceFile(sourcePath, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const names = new Set(['clamp', 'valueAt', 'progress', 'RecipeTypography']);
const pieces = [];
for (const statement of ast.statements) {
  if (ts.isFunctionDeclaration(statement) && names.has(statement.name?.text)) pieces.push(statement.getText(ast));
  if (ts.isVariableStatement(statement) && statement.declarationList.declarations.some(d => names.has(d.name.getText(ast)))) {
    pieces.push(statement.getText(ast));
  }
}
if (pieces.length !== 4) throw new Error('Runtime source changed; review extraction before using this study.');
const code = ts.transpileModule(pieces.join('\n'), {compilerOptions: {target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React}}).outputText;
const context = vm.createContext({React: {Fragment: 'fragment', createElement: (type, props, ...children) => ({type, props, children})}});
vm.runInContext(code, context, {timeout: 5000});
const runtimeValue = (keys, frame) => context.valueAt(keys, frame);

// Independent de Casteljau oracle. This is original mathematical code, not extracted from any repository.
function axis(t, a, b) {
  const u = 1 - t;
  const p = u * 0 + t * a;
  const q = u * a + t * b;
  const r = u * b + t;
  return u * (u * p + t * q) + t * (u * q + t * r);
}
function reference(p, mode, controls) {
  if (mode === 'linear') return p;
  if (mode === 'hold') return p === 1 ? 1 : 0;
  if (mode === 'ease_in') return p * p;
  if (mode === 'ease_out') return p * (2 - p);
  if (mode === 'ease_in_out') return p <= 0.5 ? 2 * p * p : -2 * p * p + 4 * p - 1;
  if (p === 0 || p === 1) return p;
  let low = 0, high = 1;
  for (let n = 0; n < 70; n++) {
    const t = (low + high) / 2;
    if (axis(t, controls[0], controls[2]) > p) high = t; else low = t;
  }
  return axis((low + high) / 2, controls[1], controls[3]);
}

const checks = [];
let maximumAbsoluteErrorPx = 0;
let samples = 0;
const configurations = ['linear', 'hold', 'ease_in', 'ease_out', 'ease_in_out'].map(mode => ({mode}));
for (const controls of [[0.22, 0.75, 0.25, 1], [0.34, 1.56, 0.64, 1], [0, 0, 0, 1], [1, 0, 1, 1], [0, -4, 1, 4]]) {
  configurations.push({mode: 'cubic_bezier', controls});
}
for (const {mode, controls} of configurations) {
  const keys = [{frame: 100, value: -120, easing: mode, ...(controls ? {cubicBezier: controls} : {})}, {frame: 130, value: 880, easing: 'linear'}];
  let error = 0;
  for (let n = 0; n <= 600; n++) {
    const frame = 100 + n / 20;
    const expected = -120 + 1000 * reference(n / 600, mode, controls);
    error = Math.max(error, Math.abs(runtimeValue(keys, frame) - expected));
    samples++;
  }
  maximumAbsoluteErrorPx = Math.max(maximumAbsoluteErrorPx, error);
  checks.push({name: 'interpolation_oracle', mode, controls, samples: 601, maxErrorPx: error, tolerancePx: 0.02, passed: error < 0.02});
  checks.push({name: 'clamp_and_exact_keys', mode, controls, passed: runtimeValue(keys, 99) === -120 && runtimeValue(keys, 100) === -120 && runtimeValue(keys, 130) === 880 && runtimeValue(keys, 131) === 880});
  const shifted = keys.map(k => ({...k, frame: k.frame + 135}));
  checks.push({name: 'absolute_frame_shift', mode, controls, passed: Math.abs(runtimeValue(keys, 115.25) - runtimeValue(shifted, 250.25)) < 1e-9});
}
const hold = [{frame: 0, value: 10, easing: 'hold'}, {frame: 12, value: 30, easing: 'linear'}, {frame: 24, value: 30, easing: 'linear'}];
checks.push({name: 'hold_boundary_and_rest', passed: runtimeValue(hold, 11.999) === 10 && runtimeValue(hold, 12) === 30 && runtimeValue(hold, 23.5) === 30});

const typography = [];
for (const text of ['A B', 'AÇÃO', 'AC\u0327A\u0303O', '👨‍👩‍👧‍👦']) {
  const spec = {unit: 'character', startFrame: 0, staggerFrames: 3, entranceFrames: 10};
  const result = context.RecipeTypography({text, frame: 1, spec});
  const children = result.children.flat();
  const spans = children.filter(child => typeof child === 'object');
  typography.push({text, codePoints: Array.from(text).length, graphemes: Array.from(new Intl.Segmenter('pt-BR', {granularity: 'grapheme'}).segment(text)).length, animatedSpans: spans.length, renderedUnits: spans.map(span => span.children.join(''))});
}
const report = {
  schemaVersion: 'res.editor-oss-runtime-study.v1', date: '2026-10-02',
  source: {path: 'workers/remotion-benchmark/src/hybrid.tsx', sha256: crypto.createHash('sha256').update(source).digest('hex'), extractedSymbolsSha256: crypto.createHash('sha256').update(pieces.join('\n')).digest('hex')},
  evidenceLevel: 'Executed current local numerical evaluator and JSX unit segmentation; no render, API job, pixel proof or human approval.',
  checks, summary: {checks: checks.length, passed: checks.filter(c => c.passed).length, samples, maximumAbsoluteErrorPx},
  typography, externalCodeCopied: false,
};
const destination = path.join(root, 'docs/studios/research/editor-oss-20261002/runtime-study.json');
fs.writeFileSync(destination, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report.summary));
console.log(JSON.stringify(typography));
if (checks.some(c => !c.passed)) process.exitCode = 1;
