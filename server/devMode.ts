import { createHash, randomBytes } from 'node:crypto';
import { existsSync, realpathSync } from 'node:fs';
import path from 'node:path';
import type { Request, Response, RequestHandler } from 'express';

export const DEV_COOKIE = 'clicko_dev_session';
const lifetime = 8 * 60 * 60 * 1000;
const sessions = new Map<string, number>();
const digest = (value: string) => createHash('sha256').update(value).digest('hex');

export function devConfiguration(env = process.env, bundled = false) {
  if (env.CLICKO_DEV_MODE !== 'true') return undefined;
  if (env.NODE_ENV !== 'development' || bundled) throw new Error('DEV_REQUIRES_LOCAL_SOURCE_DEVELOPMENT');
  if (!['127.0.0.1', 'localhost'].includes(env.CLICKO_PREVIEW_HOST || '')) throw new Error('DEV_REQUIRES_LOOPBACK_BIND');
  if (env.CLICKO_DEV_AUTH_BYPASS === 'true') throw new Error('DEV_GLOBAL_BYPASS_FORBIDDEN');
  if (env.CLICKO_NODE_OUTBOUND_ENABLED !== 'false' || env.STUDIO_NODE_OUTBOUND_ENABLED !== 'false'
      || env.KLIC_GOOGLE_TTS_ENABLED !== 'false') throw new Error('DEV_EXTERNAL_SPENDING_MUST_BE_DISABLED');
  const parent = path.resolve('.codex-runtime');
  const root = path.resolve(env.CLICKO_LOCAL_DATA_DIR || '.codex-runtime/clicko-dev');
  if (path.dirname(root) !== parent || !/^clicko-dev(?:-[a-zA-Z0-9_-]+)?$/.test(path.basename(root)))
    throw new Error('DEV_PRIVATE_DATA_DIRECTORY_REQUIRED');
  // A junction/symlink cannot redirect the isolated directory into commercial data.
  for (const candidate of [parent, root]) if (existsSync(candidate) && realpathSync(candidate) !== candidate)
    throw new Error('DEV_DATA_SYMLINK_FORBIDDEN');
  const inside = (value: string | undefined) => {
    if (!value) return false;
    const relative = path.relative(root, path.resolve(value));
    return Boolean(relative) && !relative.startsWith('..') && !path.isAbsolute(relative);
  };
  for (const key of ['CLICKO_GOVERNANCE_DATA_FILE', 'CLICKO_SOCIAL_DATA_FILE', 'CLICKO_STUDIOS_DATA_DIR',
    'CLICKO_KLIC_DATA_FILE', 'CLICKO_CONVERSATIONS_DIR', 'CLICKO_RADAR_DATA_FILE'] as const) {
    if (!inside(env[key])) throw new Error('DEV_DATA_ISOLATION_REQUIRED:' + key);
    let candidate = path.resolve(env[key]!);
    while (candidate !== root) {
      if (existsSync(candidate) && realpathSync(candidate) !== candidate) throw new Error('DEV_DATA_SYMLINK_FORBIDDEN');
      candidate = path.dirname(candidate);
    }
  }
  const studio = new URL(env.CLICKO_STUDIOS_ORIGIN || '');
  if (studio.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(studio.hostname)
      || studio.username || studio.password || studio.pathname !== '/' || studio.search || studio.hash)
    throw new Error('DEV_STUDIOS_MUST_BE_LOOPBACK');
  if (env.PUBLIC_APP_URL) {
    const publicUrl = new URL(env.PUBLIC_APP_URL);
    if (publicUrl.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(publicUrl.hostname)
        || publicUrl.port !== String(env.PORT) || publicUrl.username || publicUrl.password
        || publicUrl.pathname !== '/' || publicUrl.search || publicUrl.hash) throw new Error('DEV_PUBLIC_PREVIEW_FORBIDDEN');
  }
  return { root, port: Number(env.PORT || 3018) };
}

function loopback(address: string | undefined) {
  return address === '127.0.0.1' || address === '::1' || address === '::ffff:127.0.0.1';
}

export function isLocalDevRequest(req: Request) {
  const config = devConfiguration();
  if (!config || !loopback(req.socket.localAddress) || !loopback(req.socket.remoteAddress)) return false;
  if (Object.keys(req.headers).some(name => name === 'forwarded' || name.startsWith('x-forwarded-') || name === 'x-real-ip')) return false;
  try {
    const host = new URL('http://' + req.headers.host);
    if (!['127.0.0.1', 'localhost'].includes(host.hostname) || Number(host.port || 80) !== req.socket.localPort
        || host.username || host.password || host.pathname !== '/') return false;
    const origin = req.header('origin');
    if (origin && new URL(origin).origin !== host.origin) return false;
    const site = req.header('sec-fetch-site');
    return !site || site === 'same-origin' || site === 'none';
  } catch { return false; }
}

const cookie = (value: string, seconds: number) => `${DEV_COOKIE}=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${seconds}`;
export function resolveDevSession(req: Request) {
  if (!isLocalDevRequest(req)) return undefined;
  const token = String(req.headers.cookie || '').split(';').map(part => part.trim())
    .find(part => part.startsWith(DEV_COOKIE + '='))?.slice(DEV_COOKIE.length + 1) || '';
  const expires = sessions.get(digest(token));
  if (!expires || expires <= Date.now()) { if (expires) sessions.delete(digest(token)); return undefined; }
  return new Date(expires).toISOString();
}
export function issueDevSession(req: Request, res: Response) {
  if (!isLocalDevRequest(req)) throw new Error('DEV_LOCAL_REQUEST_REQUIRED');
  const existing = resolveDevSession(req);
  if (existing) return existing;
  for (const [key, expires] of sessions) if (expires <= Date.now()) sessions.delete(key);
  if (sessions.size >= 128) throw new Error('DEV_SESSION_LIMIT');
  const token = randomBytes(32).toString('base64url'), expires = Date.now() + lifetime;
  sessions.set(digest(token), expires);
  res.append('Set-Cookie', cookie(token, lifetime / 1000));
  res.setHeader('Cache-Control', 'no-store');
  return new Date(expires).toISOString();
}
export function revokeDevSession(req: Request, res: Response) {
  const token = String(req.headers.cookie || '').split(';').map(part => part.trim())
    .find(part => part.startsWith(DEV_COOKIE + '='))?.slice(DEV_COOKIE.length + 1) || '';
  sessions.delete(digest(token));
  res.append('Set-Cookie', cookie('', 0));
}

export const devNetworkBoundary: RequestHandler = (req, res, next) => {
  if (!devConfiguration()) return next();
  if (!isLocalDevRequest(req)) return void res.status(403).json({ code: 'DEV_LOCAL_REQUEST_REQUIRED', error: 'O modo DEV aceita somente conexão local direta.' });
  if (req.path.startsWith('/api/governance/billing') || /\/api\/governance\/clients\/[^/]+\/(invite|checkout|managed-checkout|activate)/.test(req.path))
    return void res.status(403).json({ code: 'DEV_EXTERNAL_PAYMENT_DISABLED', error: 'Contratação e pagamentos estão desativados no ambiente DEV.' });
  if (['/api/governance/auth/signup', '/api/governance/workspaces/register'].includes(req.path)
      || req.method !== 'GET' && req.path.startsWith('/api/governance/subscription'))
    return void res.status(403).json({ code: 'DEV_FIXED_WORKSPACE', error: 'O ambiente DEV utiliza sua identidade, workspace e plano locais reservados.' });
  if (!['GET', 'HEAD', 'OPTIONS'].includes(req.method) && req.path.startsWith('/api/integrations'))
    return void res.status(503).json({ code: 'DEV_EXTERNAL_INTEGRATION_DISABLED', error: 'A integração externa não é executada no modo DEV. As ferramentas locais continuam disponíveis.' });
  next();
};
