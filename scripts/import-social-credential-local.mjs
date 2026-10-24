import { randomBytes } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const allowedNames = new Set([
  'META_APP_ID',
  'META_APP_SECRET',
  'TIKTOK_CLIENT_KEY',
  'TIKTOK_CLIENT_SECRET',
  'LINKEDIN_CLIENT_ID',
  'LINKEDIN_CLIENT_SECRET',
  'THREADS_APP_ID',
  'THREADS_APP_SECRET',
  'PINTEREST_APP_ID',
  'PINTEREST_APP_SECRET',
  'X_CLIENT_ID',
  'X_CLIENT_SECRET',
]);
const name = process.argv[2];
if (!allowedNames.has(name)) throw new Error('Nome de credencial não permitido.');

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const envPath = path.join(projectRoot, '.env');
const nonce = randomBytes(24).toString('base64url');
const host = '127.0.0.1';

const html = `<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer">
<title>Importação local segura</title><style>body{font-family:system-ui;background:#000;color:#fff;display:grid;place-items:center;min-height:100vh;margin:0}form{width:min(420px,90vw);display:grid;gap:16px}input,button{font:inherit;padding:12px;border-radius:8px}button{background:#ff7f50;border:0}</style>
<form method="post"><h1>Importação local segura</h1><p>A credencial será salva somente no .env local e esta ponte será encerrada.</p><input aria-label="Credencial" name="credential" type="password" autocomplete="off" required><button>Importar</button></form>`;

const server = createServer(async (request, response) => {
  const url = new URL(request.url || '/', `http://${host}`);
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('Referrer-Policy', 'no-referrer');
  if (url.searchParams.get('token') !== nonce) {
    response.writeHead(403).end('Acesso negado.');
    return;
  }
  if (request.method === 'GET') {
    response.setHeader('Content-Type', 'text/html; charset=utf-8');
    response.end(html);
    return;
  }
  if (request.method !== 'POST') {
    response.writeHead(405).end('Método não permitido.');
    return;
  }

  let body = '';
  for await (const chunk of request) {
    body += chunk;
    if (body.length > 4096) {
      response.writeHead(413).end('Payload inválido.');
      return;
    }
  }
  const value = new URLSearchParams(body).get('credential')?.trim() || '';
  if (!value || value.length < 16 || /[\r\n]/.test(value)) {
    response.writeHead(422).end('Credencial inválida.');
    return;
  }

  const existing = await readFile(envPath, 'utf8').catch(() => '');
  const lines = existing.split(/\r?\n/).filter((line, index, all) => index < all.length - 1 || line.length);
  const replacement = `${name}=${value}`;
  const index = lines.findIndex(line => line.startsWith(`${name}=`));
  if (index >= 0) lines[index] = replacement;
  else lines.push(replacement);
  await writeFile(envPath, `${lines.join('\n')}\n`, { encoding: 'utf8', mode: 0o600 });

  response.setHeader('Content-Type', 'text/html; charset=utf-8');
  response.end('<!doctype html><meta charset="utf-8"><title>Concluído</title><p>Credencial importada com segurança. Esta aba pode ser fechada.</p>');
  setImmediate(() => server.close());
});

server.listen(0, host, () => {
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('Porta local indisponível.');
  console.log(`http://${host}:${address.port}/?token=${nonce}`);
});
