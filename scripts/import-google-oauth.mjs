import { readFileSync, rmSync, writeFileSync } from 'node:fs';
import { basename, resolve } from 'node:path';

const source = resolve(String(process.argv[2] || ''));
const downloadsRoot = resolve(process.env.USERPROFILE || '', 'Downloads');
const relative = source.slice(downloadsRoot.length);
if (!source.startsWith(`${downloadsRoot}\\`) || relative.includes('..') || !/^client_secret_.*\.json$/i.test(basename(source))) {
  throw new Error('GOOGLE_OAUTH_IMPORT_SOURCE_INVALID');
}

const parsed = JSON.parse(readFileSync(source, 'utf8'));
const credentials = parsed?.web;
const clientId = typeof credentials?.client_id === 'string' ? credentials.client_id.trim() : '';
const clientSecret = typeof credentials?.client_secret === 'string' ? credentials.client_secret.trim() : '';
const redirects = Array.isArray(credentials?.redirect_uris) ? credentials.redirect_uris : [];
const expectedRedirect = 'http://localhost:3000/api/integrations/oauth/callback';
if (!clientId || !clientSecret || !redirects.includes(expectedRedirect)) {
  throw new Error('GOOGLE_OAUTH_IMPORT_CONTENT_INVALID');
}

const envFile = resolve('.env');
const original = readFileSync(envFile, 'utf8');
const newline = original.includes('\r\n') ? '\r\n' : '\n';
const lines = original.split(/\r?\n/);
const setValue = (key, value) => {
  const index = lines.findIndex(line => new RegExp(`^\\s*${key}\\s*=`).test(line));
  const entry = `${key}=${JSON.stringify(value)}`;
  if (index >= 0) lines[index] = entry;
  else lines.push(entry);
};

setValue('GOOGLE_CLIENT_ID', clientId);
setValue('GOOGLE_CLIENT_SECRET', clientSecret);
setValue('GOOGLE_REDIRECT_URI', expectedRedirect);
writeFileSync(envFile, `${lines.join(newline).replace(/(?:\r?\n)+$/, '')}${newline}`, { encoding: 'utf8', mode: 0o600 });
rmSync(source);
console.log('Google OAuth credentials imported into the server environment; downloaded credential file removed.');
