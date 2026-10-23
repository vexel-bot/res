import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';

// Read-only audit. It neither fetches Git refs nor installs/runs the demo app,
// activates its microphone, copies assets, or prints environment-file contents.
const root = fileURLToPath(new URL('../../', import.meta.url));
const reference = path.join(root, 'círculo-pontilhado-interativo');
const gitRef = process.argv[2] || 'origin/ai-studios-novo';
if (process.argv.length > 3 || !/^[A-Za-z0-9_./-]+$/.test(gitRef) || gitRef.startsWith('-')) {
  throw new Error('Usage: node scripts/klic/audit-face-reference.mjs [local-git-ref]');
}
const git = args => execFileSync('git', args, { cwd: root, maxBuffer: 16 * 1024 * 1024 });
const commit = git(['rev-parse', `${gitRef}^{commit}`]).toString('utf8').trim();
const prefix = 'ai-studios-novo/';
const remoteFiles = git(['ls-tree', '-r', '--name-only', '-z', commit, '--', prefix])
  .toString('utf8').split('\0').filter(Boolean);
assert.ok(remoteFiles.length, 'Reference directory is missing from the Git commit');
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const comparisons = remoteFiles.map(filename => {
  const relative = filename.slice(prefix.length);
  const local = readFileSync(path.join(reference, relative));
  const remote = git(['show', `${commit}:${filename}`]);
  return { file: relative, equal: local.equals(remote), localSha256: sha256(local), remoteSha256: sha256(remote) };
});
const walk = directory => readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
  if (['node_modules', '.git', 'dist'].includes(entry.name)) return [];
  const filename = path.join(directory, entry.name);
  return entry.isDirectory() ? walk(filename) : [path.relative(reference, filename).split(path.sep).join('/')];
});
const extras = walk(reference).filter(file => !comparisons.some(item => item.file === file));

// Execute only the two pure geometry functions with isolated, identical random
// streams. Imports are type-only and are erased; no application or audio runs.
function generator(filename) {
  const source = readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
  } }).outputText;
  const exports = {};
  const math = Object.create(Math);
  let seed = 0x434c4943;
  math.random = () => { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; return (seed >>> 0) / 4294967296; };
  runInNewContext(compiled, { exports, Math: math }, { filename, timeout: 2000 });
  assert.equal(typeof exports.generateAIFaceSphere, 'function');
  return exports.generateAIFaceSphere;
}
const original = generator(path.join(reference, 'src/utils/sphereGenerator.ts'));
const integrated = generator(path.join(root, 'src/klic/face/sphereGenerator.ts'));
let particles = 0;
for (const radius of [1, 110, 252]) {
  const expected = original(radius), actual = integrated(radius);
  assert.equal(actual.length, expected.length);
  assert.ok(actual.length > 5000);
  assert.equal(new Set(actual.map(point => point.ribbonIndex)).size, 72);
  for (let i = 0; i < expected.length; i++) {
    assert.deepEqual(Object.keys(actual[i]).sort(), Object.keys(expected[i]).sort());
    for (const [key, value] of Object.entries(expected[i])) {
      const found = actual[i][key];
      if (typeof value === 'number') assert.ok(Math.abs(found - value) <= 1e-10 * Math.max(1, Math.abs(value)), `Particle ${i}, ${key}, radius ${radius}`);
      else assert.equal(found, value);
    }
  }
  particles = actual.length;
}
console.log(JSON.stringify({ commit, reference: path.relative(root, reference), files: comparisons, extras,
  geometry: { equivalent: true, particles, ribbons: 72, radii: [1, 110, 252] } }, null, 2));
if (comparisons.some(item => !item.equal)) process.exitCode = 1;
