import { createHmac, randomUUID } from 'node:crypto';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import express from 'express';
import { authenticate, assertGovernanceAccess, readStudioWorkspace, type AuthContext } from '../governance';
import { canAccessNavigation } from '../../src/security/accessControl';
import { forwardMeteredImageRequest } from './imageQuota';
import { forwardMeteredVideoRequest } from './videoQuota';
import { reconcileStudioVideoJob } from '../governance';
import { studioBridgeSecret } from './bridgeKey';
import { isLocalDevRequest } from '../devMode';
export { studioBridgeSecret } from './bridgeKey';

export function studioBridgeToken(auth: AuthContext, clientId: string | null, module: string, secret: string, mediaAdmission?: Record<string, unknown>, motionGeminiExperimental = false) {
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
    ...(mediaAdmission ? { mediaAdmission } : {}),
    ...(motionGeminiExperimental ? { motionGeminiExperimental: true } : {}),
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
  const imageJobRoute = (req: express.Request) => {
    if (req.method !== 'POST' || req.header('x-clicko-studio-module') !== 'create-image') return null;
    // FastAPI matches decoded paths too; encoded static segments must not bypass metering.
    try { return decodeURIComponent(req.path).match(/^\/documents\/([^/]+)\/editing-ai-jobs\/?$/); }
    catch { return null; }
  };
  const editingJobRoute = (req: express.Request) => {
    if (req.method !== 'POST') return null;
    try { return decodeURIComponent(req.path).match(/^\/documents\/([^/]+)\/editing-ai-jobs\/?$/); }
    catch { return null; }
  };
  // Media elements cannot attach custom headers. Only this read-only, scoped
  // video delivery route accepts equivalent query context; session checks remain mandatory.
  router.use((req, _res, next) => {
    if (req.method === 'GET' && /^\/video\/library\/[^/]+\/content$/.test(req.path)) {
      req.headers['x-clicko-studio-module'] = 'create-video';
      if (typeof req.query.workspaceId === 'string') req.headers['x-workspace-id'] = req.query.workspaceId;
      if (typeof req.query.clientId === 'string') req.headers['x-clicko-client-id'] = req.query.clientId;
    }
    next();
  });
  router.use(authenticate);
  // Only the small image-job JSON is buffered. Uploads, native files and all
  // other media responses keep their existing streaming path.
  router.use((req, res, next) => {
    if (!editingJobRoute(req)) return next();
    express.json({ limit: '128kb' })(req, res, next);
  });
  router.use((error: { type?: string }, _req: express.Request, res: express.Response, next: express.NextFunction) => {
    const kind = _req.header('x-clicko-studio-module') === 'create-video' ? 'VIDEO' : 'IMAGE';
    if (error.type === 'entity.too.large') return res.status(413).json({ detail: 'A solicitação de mídia ultrapassa o limite permitido.', code: `${kind}_REQUEST_TOO_LARGE` });
    if (error.type === 'entity.parse.failed') return res.status(400).json({ detail: 'A solicitação de mídia não contém JSON válido.', code: `${kind}_REQUEST_INVALID` });
    next(error);
  });
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
    const experimental = process.env.CLICKO_MOTION_GEMINI_EXPERIMENTAL === 'true' && module === 'create-video' && isLocalDevRequest(req);
    const headers = new Headers({
      authorization: `Bearer ${studioBridgeToken(auth, clientId, module, secret, undefined, experimental)}`,
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
      const imageRoute = imageJobRoute(req);
      const editingRoute = editingJobRoute(req);
      const forward = (receiptId?: string) => {
        if (receiptId && editingRoute) headers.set('authorization', `Bearer ${studioBridgeToken(auth, clientId, module, secret, {
          id: receiptId, documentId: editingRoute[1], key: req.header('idempotency-key'), operation: req.body.operation,
          ...(req.body.operation === 'generate_video' ? { seconds: Number(req.body.durationSeconds ?? 8) } : {}),
        })}`);
        return upstreamFetch(target, {
        method: req.method, headers, signal: controller.signal,
        body: editingRoute ? JSON.stringify(req.body) : ['GET', 'HEAD'].includes(req.method) ? undefined : req as unknown as BodyInit,
        duplex: ['GET', 'HEAD'].includes(req.method) ? undefined : 'half',
      } as RequestInit & { duplex?: 'half' });
      };
      const upstream = imageRoute ? await forwardMeteredImageRequest({
        auth, clientId, documentId: imageRoute[1], key: req.header('idempotency-key'), body: req.body, signal: controller.signal, forward,
      }) : editingRoute && module === 'create-video' ? await forwardMeteredVideoRequest({
        auth, clientId, documentId: editingRoute[1], key: req.header('idempotency-key'), body: req.body, forward,
      }) : await forward();
      if (upstream.ok && module === 'create-video' && /\/jobs\/[^/]+(?:\/(?:cancel|retry))?\/?$/.test(req.path)) {
        const job = await upstream.clone().json();
        if (job && typeof job.id === 'string') reconcileStudioVideoJob(auth, job);
      }
      res.status(upstream.status);
      for (const name of ['content-type', 'content-disposition', 'content-range', 'accept-ranges', 'etag']) {
        const value = upstream.headers.get(name); if (value) res.setHeader(name, value);
      }
      res.setHeader('cache-control', 'no-store');
      if (upstream.body) await pipeline(Readable.fromWeb(upstream.body as Parameters<typeof Readable.fromWeb>[0]), res);
      else res.end();
    } catch (error) {
      if (res.headersSent) { res.destroy(); return; }
      const failure = error as Error & { status?: number; code?: string };
      if (failure.status && failure.code) return res.status(failure.status).json({ detail: failure.message, code: failure.code, requestId });
      res.status(503).json({ detail: 'O serviço de Imagem e Vídeo está temporariamente indisponível. Tente novamente.', code: 'STUDIOS_UNAVAILABLE', requestId });
    } finally {
      clearTimeout(timer); req.off('aborted', abort); res.off('close', abort);
    }
  });
  return router;
}
