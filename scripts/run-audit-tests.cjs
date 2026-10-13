const { spawnSync } = require('node:child_process');
const { mkdtempSync, readdirSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const path = require('node:path');

const project = path.resolve(__dirname, '..');
const temporaryRoot = path.resolve(tmpdir());
const output = mkdtempSync(path.join(temporaryRoot, 'clicko-audit-'));
// Discover source tests so newly added suites cannot silently miss the audit.
const sources = ['src', 'server'].flatMap(directory => collect(path.join(project, directory), '.test.ts'));
function run(args, env = process.env) {
  const result = spawnSync(process.execPath, args, { cwd: project, stdio: 'inherit', env });
  if (result.error) throw result.error;
  return result.status ?? 1;
}
function collect(directory, suffix) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const filename = path.join(directory, entry.name);
    return entry.isDirectory() ? collect(filename, suffix) : entry.name.endsWith(suffix) ? [filename] : [];
  });
}
try {
  // Compile test dependencies only; no build of or edits to Image/Video modules.
  const status = run([require.resolve('typescript/bin/tsc'), ...sources, '--target', 'ES2022', '--module', 'commonjs', '--moduleResolution', 'node', '--esModuleInterop', '--skipLibCheck', '--outDir', output]);
  process.exitCode = status || run(['--test', ...collect(output, '.test.js')], { ...process.env, NODE_ENV: 'test', NODE_PATH: path.join(project, 'node_modules') });
} finally {
  // Delete only this run's verified temporary compilation directory.
  if (path.dirname(path.resolve(output)) === temporaryRoot && path.basename(output).startsWith('clicko-audit-')) rmSync(output, { recursive: true, force: true });
}
