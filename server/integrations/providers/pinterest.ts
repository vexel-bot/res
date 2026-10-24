import { providerJson } from '../http';
import { SocialIntegrationError } from '../errors';
import type { SocialProvider } from '../types';
import { capabilities, configured, hasAny, requireToken, scopeList } from './shared';

const defaultScopes = ['user_accounts:read', 'boards:read', 'pins:read', 'pins:write'];
const requestedScopes = () => scopeList(process.env.PINTEREST_SCOPES || defaultScopes.join(','));
const credentials = () => configured(process.env.PINTEREST_APP_ID, process.env.PINTEREST_APP_SECRET, process.env.PINTEREST_REDIRECT_URI);
const basic = (clientId: string, clientSecret: string) => `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString('base64')}`;

async function tokenRequest(fetcher: typeof fetch, auth: { clientId: string; clientSecret: string }, values: Record<string, string>, signal: AbortSignal) {
  return requireToken(await providerJson<Record<string, unknown>>(fetcher, 'https://api.pinterest.com/v5/oauth/token', {
    method: 'POST', headers: { Authorization: basic(auth.clientId, auth.clientSecret), 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(values), signal,
  }));
}

export const pinterestProvider: SocialProvider = {
  id: 'pinterest',
  label: 'Pinterest',
  requiredEnvironment: ['PINTEREST_APP_ID', 'PINTEREST_APP_SECRET', 'PINTEREST_REDIRECT_URI'],
  credentials,
  usesPkce: false,
  authorizationUrl: ({ credentials: auth, redirectUri, state }) => {
    const url = new URL('https://www.pinterest.com/oauth/');
    url.searchParams.set('client_id', auth.clientId);
    url.searchParams.set('redirect_uri', redirectUri);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', requestedScopes().join(','));
    url.searchParams.set('state', state);
    return url.toString();
  },
  exchangeCode: async ({ credentials: auth, fetch, signal }, input) => tokenRequest(fetch, auth, {
    grant_type: 'authorization_code', code: input.code, redirect_uri: input.redirectUri,
  }, signal),
  accounts: async ({ fetch, signal }, token) => {
    const account = await providerJson<{ id?: string; username?: string; profile_image?: string; account_type?: string }>(fetch, 'https://api.pinterest.com/v5/user_account', {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return account.id ? [{ id: account.id, username: account.username, displayName: account.username || 'Conta do Pinterest', avatarUrl: account.profile_image, accountType: account.account_type || 'profile' }] : [];
  },
  account: async ({ fetch, signal }, token, providerAccountId) => {
    const account = await providerJson<{ id?: string; username?: string; profile_image?: string; account_type?: string }>(fetch, 'https://api.pinterest.com/v5/user_account', {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return account.id === providerAccountId ? { id: account.id, username: account.username, displayName: account.username || 'Conta do Pinterest', avatarUrl: account.profile_image, accountType: account.account_type || 'profile' } : null;
  },
  resources: async ({ fetch, signal }, token) => {
    const data = await providerJson<{ items?: Array<{ id?: string; name?: string; description?: string }> }>(fetch, 'https://api.pinterest.com/v5/boards?page_size=100', {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return (data.items || []).filter(board => board.id && board.name).map(board => ({ id: board.id!, name: board.name!, type: 'board' as const, metadata: board.description ? { description: board.description } : undefined }));
  },
  refresh: async ({ credentials: auth, fetch, signal }, refreshToken) => tokenRequest(fetch, auth, {
    grant_type: 'refresh_token', refresh_token: refreshToken,
  }, signal),
  publish: async ({ fetch, signal }, token, _account, request) => {
    const imageUrl = request.mediaUrls?.[0];
    if (request.kind !== 'image' || !request.destinationId || !imageUrl) {
      throw new SocialIntegrationError('SOCIAL_PIN_INPUT_REQUIRED', 422, 'Escolha uma pasta e informe uma imagem acessível para criar o Pin.');
    }
    const data = await providerJson<{ id?: string }>(fetch, 'https://api.pinterest.com/v5/pins', {
      method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ board_id: request.destinationId, title: request.title || '', description: request.description || request.text || '', media_source: { source_type: 'image_url', url: imageUrl } }), signal,
    });
    if (!data.id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O Pinterest não confirmou a criação do Pin.');
    return { providerPostId: data.id, status: 'published' };
  },
  capabilities: scopes => capabilities({
    canReadProfile: scopes.includes('user_accounts:read'),
    canReadAnalytics: hasAny(scopes, ['pins:read', 'boards:read']),
    canPublishImage: scopes.includes('pins:write'),
    canPublishVideo: false,
    canReadPosts: scopes.includes('pins:read'),
  }),
};
