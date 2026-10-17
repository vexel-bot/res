import { createHmac, randomBytes, randomUUID } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import express from 'express';
import { authenticate, assertGovernanceAccess, readStudioWorkspace, type AuthContext } from '../governance';
import { canAccessNavigation } from '../../src/security/accessControl';

export function studioBridgeSecret() {
  if (process.env.CLICKO_STUDIOS_BRIDGE_SECRET) {
    if (process.env.CLICKO_STUDIOS_BRIDGE_SECRET.length < 32) throw new Error('STUDIOS_BRIDGE_KEY_INVALID');
    return process.env.CLICKO_STUDIOS_BRIDGE_SECRET;
  }
  const filename = path.resolve('.clicko-data/studios/bridge-key');
  mkdirSync(path.dirname(filename), { recursive: true });
  try { writeFileSync(filename, randomBytes(48).toString('hex'), { flag: 'wx', mode: 0o600 }); }
  catch (error) { if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error; }
  const key = readFileSync(filename, 'utf8').trim();
  if (key.length < 32) throw new Error('STUDIOS_BRIDGE_KEY_INVALID');
  return key;
}

export function studioBridgeToken(auth: AuthContext, clientId: string | null, module: string, secret: string) {
  const now = Math.floor(Date.now() / 1000);
  const scope = readStudioWorkspace(auth, clientId);
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const header = encode({ alg: 'HS256', typ: 'JWT' });
  const payload = encode({
    iss: 'clicko-governance', aud: 'clicko-studios', type: 'studio_bridge',
    sub: auth.user.id, workspaceId: auth.workspaceId, clientId, module,
    name: auth.user.name, workspaceName: scope.name,
    allowedModules: ['create-image', 'create-video'].filter(tab => canAccessNavigation(auth.user, tab as 'create-image' | 'create-video')),
    role: auth.user.role === 'master' ? 'Owner' : auth.user.role === 'administrator' ? 'Admin' : 'Member',
    iat: now, exp: now + 60,
  });
  const signature = createHmac('sha256', secret).update(`${header}.${payload}`).digest('base64url');
  return `${header}.${payload}.${signature}`;
}

/** Only Studios routes cross this boundary; the existing session remains authoritative. */
export function createStudiosProxy(options: { origin?: string; secret?: string; fetch?: typeof fetch } = {}) {
  const router = express.Router();
  const origin = new URL(options.origin || process.env.CLICKO_STUDIOS_ORIGIN || 'http://127.0.0.1:8000');
  const secret = options.secret || studioBridgeSecret();
  const upstreamFetch = options.fetch || fetch;
  router.use(authenticate);
  router.use(async (req, res) => {
    const requestId = randomUUID();
    const auth = (req as express.Request & { auth: AuthContext }).auth;
    const module = req.header('x-clicko-studio-module');
    const clientId = req.header('x-clicko-client-id') || null;
    if (module !== 'create-image' && module !== 'create-video') return res.status(400).json({ detail: 'Selecione a aba Imagem ou Vídeo.', code: 'STUDIOS_MODULE_REQUIRED' });
    try {
      const permission = /\/decisions$/.test(req.path) ? 'content.approve'
        : ['GET', 'HEAD'].includes(req.method) ? undefined
          : req.method === 'POST' && /\/projects$|\/documents$|\/upload$/.test(req.path) ? 'content.create' : 'content.edit';
      assertGovernanceAccess(auth, { module, clientId, permission });
      readStudioWorkspace(auth, clientId);
    } catch (error) {
      const failure = error as Error & { status?: number; code?: string };
      return res.status(failure.status || 403).json({ detail: failure.message, code: failure.code || 'STUDIOS_ACCESS_DENIED' });
    }
    // Do not expose the rest of the imported backend or accept a browser bearer token.
    if (!/^\/api\/v1\/(?:studios\/v1(?:\/|$)|assets(?:\/|$))/.test(req.originalUrl.split('?')[0])) {
      return res.status(404).json({ detail: 'Operação não disponível nos Studios.' });
    }
    const headers = new Headers({
      authorization: `Bearer ${studioBridgeToken(auth, clientId, module, secret)}`,
      'x-correlation-id': requestId,
    });
    for (const name of ['content-type', 'accept', 'range', 'idempotency-key', 'if-match']) {
      const value = req.header(name); if (value) headers.set(name, value);
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 180_000);
    const abort = () => { if (!res.writableEnded) controller.abort(); };
    req.on('aborted', abort); res.on('close', abort);
    try {
      const target = new URL(req.originalUrl, origin);
      if (target.origin !== origin.origin) return res.status(400).json({ detail: 'Destino inválido.' });
      const upstream = await upstreamFetch(target, {
        method: req.method, headers, signal: controller.signal,
        body: ['GET', 'HEAD'].includes(req.method) ? undefined : req as unknown as BodyInit,
        duplex: ['GET', 'HEAD'].includes(req.method) ? undefined : 'half',
      } as RequestInit & { duplex?: 'half' });
      res.status(upstream.status);
      for (const name of ['content-type', 'content-disposition', 'content-range', 'accept-ranges', 'etag']) {
        const value = upstream.headers.get(name); if (value) res.setHeader(name, value);
      }
      res.setHeader('cache-control', 'no-store');
      if (upstream.body) await pipeline(Readable.fromWeb(upstream.body as Parameters<typeof Readable.fromWeb>[0]), res);
      else res.end();
    } catch {
      if (res.headersSent) { res.destroy(); return; }
      res.status(503).json({ detail: 'O serviço de Imagem e Vídeo está temporariamente indisponível. Tente novamente.', code: 'STUDIOS_UNAVAILABLE', requestId });
    } finally {
      clearTimeout(timer); req.off('aborted', abort); res.off('close', abort);
    }
  });
  return router;
}
