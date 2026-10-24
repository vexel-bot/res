import { randomBytes } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const envFile = resolve('.env');
const appUrl = String(process.argv[2] || 'http://localhost:3000').replace(/\/$/, '');
const callbackUrl = `${appUrl}/api/integrations/oauth/callback`;
const original = existsSync(envFile) ? readFileSync(envFile, 'utf8') : '';
const newline = original.includes('\r\n') ? '\r\n' : '\n';
const lines = original ? original.split(/\r?\n/) : [];

function currentValue(key) {
  const line = lines.find(candidate => new RegExp(`^\\s*${key}\\s*=`).test(candidate));
  if (!line) return '';
  return line.slice(line.indexOf('=') + 1).trim().replace(/^['"]|['"]$/g, '');
}

function ensure(key, value) {
  if (currentValue(key)) return false;
  const index = lines.findIndex(candidate => new RegExp(`^\\s*${key}\\s*=`).test(candidate));
  const entry = `${key}=${JSON.stringify(value)}`;
  if (index >= 0) lines[index] = entry;
  else lines.push(entry);
  return true;
}

const changed = [];
if (ensure('APP_URL', appUrl)) changed.push('APP_URL');
if (ensure('SOCIAL_TOKEN_ENCRYPTION_KEY', randomBytes(32).toString('base64url'))) changed.push('SOCIAL_TOKEN_ENCRYPTION_KEY');
for (const key of [
  'META_REDIRECT_URI',
  'TIKTOK_REDIRECT_URI',
  'GOOGLE_REDIRECT_URI',
  'LINKEDIN_REDIRECT_URI',
  'THREADS_REDIRECT_URI',
  'PINTEREST_REDIRECT_URI',
  'X_REDIRECT_URI',
]) {
  if (ensure(key, callbackUrl)) changed.push(key);
}

writeFileSync(envFile, `${lines.join(newline).replace(/(?:\r?\n)+$/, '')}${newline}`, { encoding: 'utf8', mode: 0o600 });
console.log(`Configured local social environment fields: ${changed.length ? changed.join(', ') : 'none (already present)'}.`);
