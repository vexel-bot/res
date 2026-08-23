import { randomBytes } from 'crypto';
import { Router, type Request } from 'express';

type IntegrationPlatform = 'instagram' | 'facebook' | 'tiktok' | 'linkedin' | 'youtube' | 'pinterest' | 'threads';

type ProviderConfig = {
  clientId: string;
  clientSecret: string;
  authorizationUrl: string;
  tokenUrl: string;
  scopes: string[];
};

type PendingAuthorization = {
  platform: IntegrationPlatform;
  workspaceId: string;
  userId: string;
  redirectUri: string;
  returnTo: string;
  expiresAt: number;
};

type StoredToken = {
  accessToken: string;
  refreshToken?: string;
  scopes: string[];
  expiresAt?: number;
};

const pendingAuthorizations = new Map<string, PendingAuthorization>();
const workspaceTokens = new Map<string, StoredToken>();
const supportedPlatforms = new Set<IntegrationPlatform>(['instagram', 'facebook', 'tiktok', 'linkedin', 'youtube', 'pinterest', 'threads']);

const tokenKey = (workspaceId: string, platform: IntegrationPlatform) => `${workspaceId}:${platform}`;

function providerConfig(platform: IntegrationPlatform): ProviderConfig | null {
  switch (platform) {
    case 'instagram':
    case 'facebook':
      if (!process.env.META_CLIENT_ID || !process.env.META_CLIENT_SECRET) return null;
      return {
        clientId: process.env.META_CLIENT_ID,
        clientSecret: process.env.META_CLIENT_SECRET,
        authorizationUrl: 'https://www.facebook.com/dialog/oauth',
        tokenUrl: 'https://graph.facebook.com/oauth/access_token',
        scopes: platform === 'instagram'
          ? ['pages_show_list', 'pages_read_engagement', 'instagram_basic', 'instagram_content_publish', 'instagram_manage_insights']
          : ['pages_show_list', 'pages_read_engagement', 'pages_manage_posts'],
      };
    case 'linkedin':
      if (!process.env.LINKEDIN_CLIENT_ID || !process.env.LINKEDIN_CLIENT_SECRET) return null;
      return {
        clientId: process.env.LINKEDIN_CLIENT_ID,
        clientSecret: process.env.LINKEDIN_CLIENT_SECRET,
        authorizationUrl: 'https://www.linkedin.com/oauth/v2/authorization',
        tokenUrl: 'https://www.linkedin.com/oauth/v2/accessToken',
        scopes: ['openid', 'profile', 'w_member_social'],
      };
    case 'youtube':
      if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET) return null;
      return {
        clientId: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        authorizationUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
        tokenUrl: 'https://oauth2.googleapis.com/token',
        scopes: ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/youtube.upload'],
      };
    case 'tiktok':
      if (!process.env.TIKTOK_CLIENT_KEY || !process.env.TIKTOK_CLIENT_SECRET) return null;
      return {
        clientId: process.env.TIKTOK_CLIENT_KEY,
        clientSecret: process.env.TIKTOK_CLIENT_SECRET,
        authorizationUrl: 'https://www.tiktok.com/v2/auth/authorize/',
        tokenUrl: 'https://open.tiktokapis.com/v2/oauth/token/',
        scopes: ['user.info.basic', 'video.list', 'video.publish'],
      };
    case 'pinterest':
      if (!process.env.PINTEREST_APP_ID || !process.env.PINTEREST_APP_SECRET) return null;
      return {
        clientId: process.env.PINTEREST_APP_ID,
        clientSecret: process.env.PINTEREST_APP_SECRET,
        authorizationUrl: 'https://www.pinterest.com/oauth/',
        tokenUrl: 'https://api.pinterest.com/v5/oauth/token',
        scopes: ['user_accounts:read', 'boards:read', 'pins:read', 'pins:write'],
      };
    case 'threads':
      if (!process.env.THREADS_APP_ID || !process.env.THREADS_APP_SECRET) return null;
      return {
        clientId: process.env.THREADS_APP_ID,
        clientSecret: process.env.THREADS_APP_SECRET,
        authorizationUrl: 'https://threads.net/oauth/authorize',
        tokenUrl: 'https://graph.threads.net/oauth/access_token',
        scopes: ['threads_basic', 'threads_content_publish', 'threads_manage_insights'],
      };
  }
}

function platformFromRequest(req: Request): IntegrationPlatform | null {
  const platform = String(req.params.platform || '').toLowerCase() as IntegrationPlatform;
  return supportedPlatforms.has(platform) ? platform : null;
}

function workspaceFromRequest(req: Request) {
  return String(req.header('x-workspace-id') || '').trim();
}

function appOrigin(req: Request) {
  return (process.env.PUBLIC_APP_URL || `${req.protocol}://${req.get('host')}`).replace(/\/$/, '');
}

function cleanExpiredStates() {
  const currentTime = Date.now();
  pendingAuthorizations.forEach((authorization, state) => {
    if (authorization.expiresAt <= currentTime) pendingAuthorizations.delete(state);
  });
}

function authorizationUrl(platform: IntegrationPlatform, config: ProviderConfig, redirectUri: string, state: string) {
  const url = new URL(config.authorizationUrl);
  const clientIdKey = platform === 'tiktok' ? 'client_key' : 'client_id';
  url.searchParams.set(clientIdKey, config.clientId);
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('scope', config.scopes.join(platform === 'tiktok' ? ',' : ' '));
  url.searchParams.set('state', state);
  if (platform === 'youtube') {
    url.searchParams.set('access_type', 'offline');
    url.searchParams.set('include_granted_scopes', 'true');
    url.searchParams.set('prompt', 'consent');
  }
  return url.toString();
}

async function parseJsonResponse(response: Response) {
  const raw = await response.text();
  let data: any = {};
  try { data = raw ? JSON.parse(raw) : {}; } catch { data = { message: raw }; }
  if (!response.ok || data.error) {
    const providerMessage = data.error_description || data.error?.message || data.message || 'O provedor recusou a solicitação.';
    throw new Error(providerMessage);
  }
  return data;
}

async function exchangeAuthorizationCode(platform: IntegrationPlatform, config: ProviderConfig, code: string, redirectUri: string): Promise<StoredToken> {
  const body = new URLSearchParams({
    code,
    redirect_uri: redirectUri,
    grant_type: 'authorization_code',
  });
  const headers: Record<string, string> = { 'Content-Type': 'application/x-www-form-urlencoded' };

  if (platform === 'tiktok') {
    body.set('client_key', config.clientId);
    body.set('client_secret', config.clientSecret);
  } else if (platform === 'pinterest') {
    headers.Authorization = `Basic ${Buffer.from(`${config.clientId}:${config.clientSecret}`).toString('base64')}`;
  } else {
    body.set('client_id', config.clientId);
    body.set('client_secret', config.clientSecret);
  }

  const response = await fetch(config.tokenUrl, { method: 'POST', headers, body });
  const data = await parseJsonResponse(response);
  const accessToken = data.access_token;
  if (!accessToken) throw new Error('O provedor não retornou um token de acesso válido.');
  const scopes = String(data.scope || '').split(/[ ,]+/).filter(Boolean);
  return {
    accessToken,
    refreshToken: data.refresh_token,
    scopes: scopes.length ? scopes : config.scopes,
    expiresAt: data.expires_in ? Date.now() + Number(data.expires_in) * 1000 : undefined,
  };
}

async function providerResources(platform: IntegrationPlatform, token: StoredToken) {
  const bearerHeaders = { Authorization: `Bearer ${token.accessToken}` };
  switch (platform) {
    case 'facebook': {
      const response = await fetch(`https://graph.facebook.com/me/accounts?fields=id,name,picture&access_token=${encodeURIComponent(token.accessToken)}`);
      const data = await parseJsonResponse(response);
      return (data.data || []).map((item: any) => ({ id: item.id, name: item.name, type: 'page', avatar: item.picture?.data?.url }));
    }
    case 'instagram': {
      const response = await fetch(`https://graph.facebook.com/me/accounts?fields=id,name,instagram_business_account{id,username,name,profile_picture_url}&access_token=${encodeURIComponent(token.accessToken)}`);
      const data = await parseJsonResponse(response);
      return (data.data || []).filter((item: any) => item.instagram_business_account).map((item: any) => ({
        id: item.instagram_business_account.id,
        name: item.instagram_business_account.name || item.name,
        handle: item.instagram_business_account.username ? `@${item.instagram_business_account.username}` : undefined,
        avatar: item.instagram_business_account.profile_picture_url,
        type: 'profile',
      }));
    }
    case 'linkedin': {
      const response = await fetch('https://api.linkedin.com/v2/userinfo', { headers: bearerHeaders });
      const item = await parseJsonResponse(response);
      return [{ id: item.sub, name: item.name || 'Perfil do LinkedIn', type: 'profile', avatar: item.picture }];
    }
    case 'youtube': {
      const response = await fetch('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true', { headers: bearerHeaders });
      const data = await parseJsonResponse(response);
      return (data.items || []).map((item: any) => ({ id: item.id, name: item.snippet?.title || 'Canal do YouTube', type: 'channel', avatar: item.snippet?.thumbnails?.default?.url }));
    }
    case 'tiktok': {
      const response = await fetch('https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,avatar_url', { headers: bearerHeaders });
      const data = await parseJsonResponse(response);
      const item = data.data?.user;
      return item ? [{ id: item.open_id, name: item.display_name || 'Perfil do TikTok', type: 'profile', avatar: item.avatar_url }] : [];
    }
    case 'pinterest': {
      const response = await fetch('https://api.pinterest.com/v5/user_account', { headers: bearerHeaders });
      const item = await parseJsonResponse(response);
      return [{ id: item.username || item.id, name: item.business_name || item.username || 'Perfil do Pinterest', handle: item.username ? `@${item.username}` : undefined, type: 'profile', avatar: item.profile_image }];
    }
    case 'threads': {
      const response = await fetch(`https://graph.threads.net/v1.0/me?fields=id,username,threads_profile_picture_url&access_token=${encodeURIComponent(token.accessToken)}`);
      const item = await parseJsonResponse(response);
      return [{ id: item.id, name: item.username || 'Perfil do Threads', handle: item.username ? `@${item.username}` : undefined, type: 'profile', avatar: item.threads_profile_picture_url }];
    }
  }
}

export function createIntegrationsRouter() {
  const router = Router();

  router.post('/:platform/authorize', (req, res) => {
    cleanExpiredStates();
    const platform = platformFromRequest(req);
    const workspaceId = workspaceFromRequest(req);
    const userId = String(req.header('x-user-id') || '').trim();
    if (!platform) return res.status(404).json({ message: 'Plataforma não suportada.' });
    if (!workspaceId || !userId) return res.status(401).json({ message: 'Não foi possível confirmar o ambiente ativo.' });
    const config = providerConfig(platform);
    if (!config) return res.status(503).json({ message: `A autenticação oficial do ${platform} ainda não foi configurada pelo administrador.` });

    const state = randomBytes(32).toString('hex');
    const redirectUri = `${appOrigin(req)}/api/integrations/oauth/callback`;
    const requestedReturnTo = String(req.body?.returnTo || '/connected-accounts');
    const returnTo = requestedReturnTo.startsWith('/') && !requestedReturnTo.startsWith('//') ? requestedReturnTo : '/connected-accounts';
    pendingAuthorizations.set(state, { platform, workspaceId, userId, redirectUri, returnTo, expiresAt: Date.now() + 10 * 60 * 1000 });
    return res.json({ authorizationUrl: authorizationUrl(platform, config, redirectUri, state) });
  });

  router.get('/oauth/callback', async (req, res) => {
    cleanExpiredStates();
    const state = String(req.query.state || '');
    const pending = pendingAuthorizations.get(state);
    if (!pending) return res.status(400).send('Autorização expirada ou inválida. Volte à plataforma e tente novamente.');
    pendingAuthorizations.delete(state);
    const destination = new URL(pending.returnTo, appOrigin(req));
    destination.searchParams.set('integration', pending.platform);
    if (req.query.error) {
      destination.searchParams.set('status', 'error');
      destination.searchParams.set('reason', String(req.query.error_description || req.query.error));
      return res.redirect(destination.toString());
    }
    try {
      const config = providerConfig(pending.platform);
      const code = String(req.query.code || '');
      if (!config || !code) throw new Error('A resposta de autorização está incompleta.');
      const token = await exchangeAuthorizationCode(pending.platform, config, code, pending.redirectUri);
      workspaceTokens.set(tokenKey(pending.workspaceId, pending.platform), token);
      destination.searchParams.set('status', 'connected');
      return res.redirect(destination.toString());
    } catch (error) {
      destination.searchParams.set('status', 'error');
      destination.searchParams.set('reason', error instanceof Error ? error.message : 'Não foi possível concluir a autorização.');
      return res.redirect(destination.toString());
    }
  });

  router.get('/:platform/resources', async (req, res) => {
    const platform = platformFromRequest(req);
    const workspaceId = workspaceFromRequest(req);
    if (!platform || !workspaceId) return res.status(400).json({ message: 'Integração ou ambiente inválido.' });
    const token = workspaceTokens.get(tokenKey(workspaceId, platform));
    if (!token) return res.status(401).json({ message: 'Esta plataforma precisa ser autorizada novamente.' });
    try {
      const resources = await providerResources(platform, token);
      return res.json({ resources, permissions: token.scopes });
    } catch (error) {
      return res.status(502).json({ message: error instanceof Error ? error.message : 'Não foi possível carregar os perfis disponíveis.' });
    }
  });

  router.post('/:platform/sync', (req, res) => {
    const platform = platformFromRequest(req);
    const workspaceId = workspaceFromRequest(req);
    if (!platform || !workspaceId) return res.status(400).json({ message: 'Integração ou ambiente inválido.' });
    if (!workspaceTokens.has(tokenKey(workspaceId, platform))) return res.status(401).json({ message: 'A autorização expirou. Conecte a plataforma novamente.' });
    const selectedResourceIds = Array.isArray(req.body?.selectedResourceIds) ? req.body.selectedResourceIds.filter((id: unknown) => typeof id === 'string') : [];
    return res.json({ status: 'synced', syncedAt: new Date().toISOString(), selectedResources: selectedResourceIds.length });
  });

  router.post('/:platform/disconnect', (req, res) => {
    const platform = platformFromRequest(req);
    const workspaceId = workspaceFromRequest(req);
    if (!platform || !workspaceId) return res.status(400).json({ message: 'Integração ou ambiente inválido.' });
    workspaceTokens.delete(tokenKey(workspaceId, platform));
    return res.json({ disconnected: true });
  });

  return router;
}
