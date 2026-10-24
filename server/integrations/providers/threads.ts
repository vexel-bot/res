import { providerJson } from '../http';
import { SocialIntegrationError } from '../errors';
import type { SocialProvider } from '../types';
import { capabilities, configured, expiresAt, hasAny, postForm, requireToken, scopeList } from './shared';

const defaultScopes = ['threads_basic', 'threads_content_publish', 'threads_manage_insights', 'threads_read_replies', 'threads_manage_replies'];
const requestedScopes = () => scopeList(process.env.THREADS_SCOPES || defaultScopes.join(','));
const credentials = () => configured(process.env.THREADS_APP_ID, process.env.THREADS_APP_SECRET, process.env.THREADS_REDIRECT_URI);
const graphVersion = () => process.env.THREADS_GRAPH_VERSION || 'v1.0';
const graph = () => `https://graph.threads.net/${graphVersion()}`;

export const threadsProvider: SocialProvider = {
  id: 'threads',
  label: 'Threads',
  requiredEnvironment: ['THREADS_APP_ID', 'THREADS_APP_SECRET', 'THREADS_REDIRECT_URI'],
  credentials,
  usesPkce: false,
  authorizationUrl: ({ credentials: auth, redirectUri, state }) => {
    const url = new URL('https://threads.net/oauth/authorize');
    url.searchParams.set('client_id', auth.clientId);
    url.searchParams.set('redirect_uri', redirectUri);
    url.searchParams.set('scope', requestedScopes().join(','));
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('state', state);
    return url.toString();
  },
  exchangeCode: async ({ credentials: auth, fetch, signal }, input) => {
    const short = requireToken(await postForm(fetch, 'https://graph.threads.net/oauth/access_token', {
      client_id: auth.clientId, client_secret: auth.clientSecret, grant_type: 'authorization_code',
      redirect_uri: input.redirectUri, code: input.code,
    }, signal));
    const url = new URL('https://graph.threads.net/access_token');
    url.searchParams.set('grant_type', 'th_exchange_token');
    url.searchParams.set('client_secret', auth.clientSecret);
    url.searchParams.set('access_token', short.accessToken);
    const long = await providerJson<Record<string, unknown>>(fetch, url.toString(), { signal });
    const accessToken = typeof long.access_token === 'string' ? long.access_token : short.accessToken;
    return { accessToken, refreshToken: accessToken, expiresAt: expiresAt(long.expires_in), scopes: [] };
  },
  grantedScopes: async ({ fetch, signal }, token) => {
    const permissions = await providerJson<{ data?: Array<{ permission?: string; status?: string }> }>(fetch, `${graph()}/me/permissions`, {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return (permissions.data || []).filter(item => item.status === 'granted' && item.permission).map(item => item.permission!);
  },
  accounts: async ({ fetch, signal }, token) => {
    const account = await providerJson<{ id?: string; username?: string; threads_profile_picture_url?: string }>(fetch, `${graph()}/me?fields=id,username,threads_profile_picture_url`, {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return account.id ? [{ id: account.id, username: account.username, displayName: account.username || 'Perfil do Threads', avatarUrl: account.threads_profile_picture_url, accountType: 'profile' }] : [];
  },
  account: async ({ fetch, signal }, token, providerAccountId) => {
    const account = await providerJson<{ id?: string; username?: string; threads_profile_picture_url?: string }>(fetch, `${graph()}/me?fields=id,username,threads_profile_picture_url`, {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return account.id === providerAccountId ? { id: account.id, username: account.username, displayName: account.username || 'Perfil do Threads', avatarUrl: account.threads_profile_picture_url, accountType: 'profile' } : null;
  },
  refresh: async ({ fetch, signal }, refreshToken) => {
    const url = new URL('https://graph.threads.net/refresh_access_token');
    url.searchParams.set('grant_type', 'th_refresh_token');
    url.searchParams.set('access_token', refreshToken);
    const refreshed = await providerJson<Record<string, unknown>>(fetch, url.toString(), { signal });
    const accessToken = typeof refreshed.access_token === 'string' ? refreshed.access_token : '';
    if (!accessToken) throw new SocialIntegrationError('SOCIAL_TOKEN_MISSING', 502, 'O Threads não retornou uma credencial válida.');
    return { accessToken, refreshToken: accessToken, expiresAt: expiresAt(refreshed.expires_in), scopes: [] };
  },
  revoke: async ({ fetch, signal }, accessToken) => {
    await providerJson(fetch, `${graph()}/me/permissions`, { method: 'DELETE', headers: { Authorization: `Bearer ${accessToken}` }, signal });
  },
  publish: async ({ fetch, signal }, token, account, request) => {
    const mediaType = request.kind === 'text' ? 'TEXT' : request.kind === 'image' ? 'IMAGE' : request.kind === 'video' || request.kind === 'short_video' ? 'VIDEO' : '';
    if (!mediaType) throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'Este formato ainda não é aceito pelo Threads nesta conexão.');
    const mediaUrl = request.mediaUrls?.[0];
    if (mediaType !== 'TEXT' && !mediaUrl) throw new SocialIntegrationError('SOCIAL_MEDIA_REQUIRED', 422, 'Informe uma mídia acessível para publicar no Threads.');
    const createUrl = new URL(`${graph()}/${encodeURIComponent(account.providerAccountId)}/threads`);
    createUrl.searchParams.set('media_type', mediaType);
    if (request.text) createUrl.searchParams.set('text', request.text);
    if (mediaType === 'IMAGE') createUrl.searchParams.set('image_url', mediaUrl!);
    if (mediaType === 'VIDEO') createUrl.searchParams.set('video_url', mediaUrl!);
    const created = await providerJson<{ id?: string }>(fetch, createUrl.toString(), { method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}` }, signal });
    if (!created.id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O Threads não criou o contêiner de publicação.');
    const publishUrl = new URL(`${graph()}/${encodeURIComponent(account.providerAccountId)}/threads_publish`);
    publishUrl.searchParams.set('creation_id', created.id);
    const published = await providerJson<{ id?: string }>(fetch, publishUrl.toString(), { method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}` }, signal });
    if (!published.id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O Threads não confirmou a publicação.');
    return { providerPostId: published.id, status: 'published' };
  },
  capabilities: scopes => capabilities({
    canReadProfile: scopes.includes('threads_basic'),
    canReadAnalytics: scopes.includes('threads_manage_insights'),
    canPublishText: scopes.includes('threads_content_publish'),
    canPublishImage: scopes.includes('threads_content_publish'),
    canPublishVideo: scopes.includes('threads_content_publish'),
    canPublishShortVideo: scopes.includes('threads_content_publish'),
    canReadPosts: scopes.includes('threads_basic'),
    canReadComments: hasAny(scopes, ['threads_read_replies', 'threads_manage_replies']),
    canReplyComments: scopes.includes('threads_manage_replies'),
  }),
};
