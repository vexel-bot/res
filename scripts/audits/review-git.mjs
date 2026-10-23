/** Read-only candidate manifest and secret checks. Never prints credential values. */
import { execFileSync } from 'node:child_process';
import { existsSync, lstatSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
process.chdir(root);
const output = path.join(root, '.codex-runtime/audit-2026-10-23');
mkdirSync(output, { recursive: true });
const git = (...args) => execFileSync('git', ['-c', 'core.quotepath=false', '-c', 'core.safecrlf=false', ...args], { encoding: 'utf8' });
const staged = new Set(git('diff', '--cached', '--diff-filter=ACMRT', '--name-only', '-z').split('\0').filter(Boolean));
const files = [...new Set([...git('diff', '--name-only', '-z').split('\0'),
  ...git('diff', '--cached', '--name-only', '-z').split('\0'),
  ...git('ls-files', '--others', '--exclude-standard', '-z').split('\0')].filter(Boolean))];
const excluded = files.filter(file => file.startsWith('círculo-pontilhado-interativo'));
const candidates = files.filter(file => !excluded.includes(file));
const findings = [], reviewed = [];
const secrets = ['.env', 'backend/.env'].filter(existsSync).flatMap(file => Object.entries(dotenv.parse(readFileSync(file))))
  .filter(([key, value]) => /KEY|SECRET|TOKEN|PASSWORD/.test(key) && value.length >= 16 && !/^(MY_|YOUR_|example|change[-_]me|<)/i.test(value));
const allowedRoots = new Set(['backend', 'src', 'server', 'scripts', 'docs', 'tests', 'workers']);
const allowedFiles = /^(?:\.dockerignore|\.gitignore|package(?:-lock)?\.json|bun\.lock|server\.ts|tsconfig\.json|vite\.config\.ts|README\.md|CHANGELOG\.md|CLICKO_[A-Z0-9_-]+\.md)$/;
for (const file of candidates) {
  if (!allowedRoots.has(file.split('/')[0]) && !allowedFiles.test(file)) findings.push({ file, reason: 'unexpected_scope' });
  if (/(^|\/)(?:\.env(?!\.example$)|\.secrets|\.git|\.aistudio|node_modules|\.venv|\.codex-runtime|backend\/data)(\/|$)|\.(?:log|sqlite(?:-wal|-shm)?|db|zip|pem|key|mp4|wav|png|jpg)$/i.test(file)) findings.push({ file, reason: 'private_or_generated_file' });
  const absolute = path.resolve(root, file);
  if (!existsSync(absolute)) { reviewed.push({ file, deleted: true }); continue; }
  if (lstatSync(absolute).isSymbolicLink() || !realpathSync(absolute).startsWith(root + path.sep)) { findings.push({ file, reason: 'symlink_or_outside_root' }); continue; }
  const bytes = readFileSync(absolute), text = bytes.toString('utf8');
  // A clean working copy is not proof of a clean index. Refuse stale staged
  // content rather than scan one version and publish a different one.
  if (staged.has(file) && git('hash-object', `--path=${file}`, file).trim() !== git('rev-parse', `:${file}`).trim()) {
    findings.push({ file, reason: 'staged_worktree_mismatch' });
  }
  if (bytes.includes(0)) findings.push({ file, reason: 'unexpected_binary' });
  const patterns = [/AIza[0-9A-Za-z_-]{30,}/g, /(?:sk_live_|sk-proj-|gh[pousr]_)[0-9A-Za-z_-]{20,}/g, /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g];
  for (const pattern of patterns) for (const match of text.matchAll(pattern)) findings.push({ file, line: text.slice(0, match.index).split('\n').length, reason: 'credential_pattern' });
  for (const [key, value] of secrets) if (text.includes(value)) findings.push({ file, keyName: key, reason: 'matches_private_environment_value' });
  reviewed.push({ file, bytes: bytes.length, lines: text.split('\n').length, sha256: createHash('sha256').update(bytes).digest('hex') });
}
writeFileSync(path.join(output, 'git-diff.patch'), git('diff', '--binary'));
writeFileSync(path.join(output, 'git-diff-staged.patch'), git('diff', '--cached', '--binary'));
writeFileSync(path.join(output, 'commit-candidates.txt'), candidates.join('\0') + '\0');
const documentation = candidates.filter(file => file.startsWith('docs/') || file.startsWith('scripts/audits/')
  || file === 'scripts/video/triage_stage1.py' || /^(?:README|CHANGELOG|CLICKO_[A-Z0-9_-]+)\.md$/.test(file));
const implementation = candidates.filter(file => !documentation.includes(file));
for (const [name, group] of [['implementation', implementation], ['audit', documentation]]) {
  writeFileSync(path.join(output, `commit-${name}.txt`), group.join('\0') + '\0');
}
const result = { branch: git('branch', '--show-current').trim(), base: git('rev-parse', 'HEAD').trim(), reviewed,
  excluded, findings, note: 'No stage/commit/push. Whole candidate files scanned; generated/private/reference bundle excluded. Not a complete secret-history or security audit.' };
writeFileSync(path.join(output, 'git-review.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify({ branch: result.branch, candidates: candidates.length, implementation: implementation.length,
  documentation: documentation.length, reviewedBytes: reviewed.reduce((sum, row) => sum + (row.bytes || 0), 0), excluded: excluded.length, findings }, null, 2));
process.exitCode = findings.length ? 1 : 0;
