import { Router, type Request } from 'express';
import { authenticate, developmentAuth, type AuthContext } from './governance';
import { devConfiguration } from './devMode';
import { DEV_CLIENT_ID } from '../src/development/contracts';
import { studioBridgeSecret, studioBridgeToken } from './studios/proxy';
import { studiosReadiness } from './studios/readiness';
import { klicProviderConfig } from './klic/providerConfig';

export async function devBridgeStatus(auth = developmentAuth()) {
  if (!auth) return undefined;
  const readiness = await studiosReadiness();
  if (readiness.status !== 'ready') return { status: 'not_ready', bridge: false };
  try {
    const response = await fetch(new URL('/api/v1/studios/v1/bridge/session', process.env.CLICKO_STUDIOS_ORIGIN), {
      headers: { authorization: `Bearer ${studioBridgeToken(auth, DEV_CLIENT_ID, 'create-video', studioBridgeSecret())}` },
      signal: AbortSignal.timeout(4000), redirect: 'error',
    });
    const session = await response.json();
    if (!response.ok || typeof session.workspace?.id !== 'string' || typeof session.user?.id !== 'string')
      return { status: 'not_ready', bridge: false };
    return { status: 'ready', bridge: true, studioWorkspaceId: session.workspace.id };
  } catch { return { status: 'not_ready', bridge: false }; }
}

export function createDevelopmentRouter() {
  const router = Router();
  router.use((_req, res, next) => devConfiguration() ? next() : void res.status(404).json({ code: 'DEV_DISABLED' }));
  router.use(authenticate);
  router.get('/status', async (req: Request & { auth?: AuthContext }, res) => {
    const studio = await devBridgeStatus(req.auth);
    let roles: Record<string, { mode: string; model?: string }> | undefined;
    if (studio?.bridge) {
      try {
        const url = new URL('/api/v1/studios/v1/agents/roles', process.env.CLICKO_STUDIOS_ORIGIN);
        url.searchParams.set('workspace_id', studio.studioWorkspaceId!);
        const response = await fetch(url, { headers: { authorization: `Bearer ${studioBridgeToken(req.auth!, DEV_CLIENT_ID, 'create-video', studioBridgeSecret())}` }, signal: AbortSignal.timeout(4000), redirect: 'error' });
        if (response.ok) {
          const value = await response.json(); roles = {};
          for (const role of ['audiovisual', 'image']) roles[role] = { mode: value[role]?.mode === 'local_model' ? 'configured_not_verified' : 'disabled_using_local_rules', model: value[role]?.model };
        }
      } catch { /* Unavailable configuration is not a model availability claim. */ }
    }
    res.setHeader('Cache-Control', 'no-store');
    res.json({ mode: 'local_development', label: 'Ambiente de Desenvolvimento',
      services: { express: 'available', studios: studio?.status || 'not_ready', bridge: Boolean(studio?.bridge) },
      tools: { imageComposition: studio?.bridge ? 'operational_local' : 'unavailable',
        motion2D: studio?.bridge ? 'operational_local' : 'unavailable',
        videoEditing: studio?.bridge ? 'operational_local' : 'unavailable',
        cinematicGeneration: 'external_model_required', imageGeneration: 'external_model_required',
        craft: 'not_qualified', plannedTools: 'not_implemented' },
      models: { specialistDefault: 'deterministic_rules_no_inference', remoteGeneration: 'disabled',
        roles, klicConfigured: klicProviderConfig().configured,
        configuration: 'Consulte Modelos dos agentes no Studio; conexão configurada não significa modelo homologado.' },
      costs: { externalCallsEnabled: false, externalBudgetUsd: 0 },
      studioWorkspaceId: studio?.bridge ? studio.studioWorkspaceId : undefined });
  });
  return router;
}
