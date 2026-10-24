import { providerJson } from '../http';
import { normalizeSocialAnalytics } from '../analytics';
import { SocialIntegrationError } from '../errors';
import type { SocialProvider } from '../types';
import { capabilities, configured, hasAny, requireToken, scopeList } from './shared';

const defaultScopes = ['tweet.read', 'tweet.write', 'users.read', 'offline.access'];
const requestedScopes = () => scopeList(process.env.X_SCOPES || defaultScopes.join(' '));
const credentials = () => configured(process.env.X_CLIENT_ID, process.env.X_CLIENT_SECRET, process.env.X_REDIRECT_URI);
const basic = (clientId: string, clientSecret: string) => `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString('base64')}`;

async function tokenRequest(fetcher: typeof fetch, auth: { clientId: string; clientSecret: string }, values: Record<string, string>, signal: AbortSignal) {
  return requireToken(await providerJson<Record<string, unknown>>(fetcher, 'https://api.x.com/2/oauth2/token', {
    method: 'POST', headers: { Authorization: basic(auth.clientId, auth.clientSecret), 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(values), signal,
  }));
}

export const xProvider: SocialProvider = {
  id: 'x',
  label: 'X',
  requiredEnvironment: ['X_CLIENT_ID', 'X_CLIENT_SECRET', 'X_REDIRECT_URI'],
  credentials,
  usesPkce: true,
  authorizationUrl: ({ credentials: auth, redirectUri, state, codeChallenge }) => {
    if (!codeChallenge) throw new SocialIntegrationError('SOCIAL_PKCE_REQUIRED', 500, 'A autorização segura não pôde ser iniciada.');
    const url = new URL('https://x.com/i/oauth2/authorize');
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('client_id', auth.clientId);
    url.searchParams.set('redirect_uri', redirectUri);
    url.searchParams.set('scope', requestedScopes().join(' '));
    url.searchParams.set('state', state);
    url.searchParams.set('code_challenge', codeChallenge);
    url.searchParams.set('code_challenge_method', 'S256');
    return url.toString();
  },
  exchangeCode: async ({ credentials: auth, fetch, signal }, input) => {
    if (!input.codeVerifier) throw new SocialIntegrationError('SOCIAL_PKCE_REQUIRED', 400, 'A autorização segura expirou. Tente novamente.');
    return tokenRequest(fetch, auth, {
      code: input.code, grant_type: 'authorization_code', redirect_uri: input.redirectUri,
      code_verifier: input.codeVerifier, client_id: auth.clientId,
    }, signal);
  },
  accounts: async ({ fetch, signal }, token) => {
    const response = await providerJson<{ data?: { id?: string; name?: string; username?: string; profile_image_url?: string } }>(fetch, 'https://api.x.com/2/users/me?user.fields=id,name,username,profile_image_url', {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    const account = response.data;
    return account?.id ? [{ id: account.id, username: account.username, displayName: account.name || account.username || 'Conta do X', avatarUrl: account.profile_image_url, accountType: 'profile' }] : [];
  },
  account: async ({ fetch, signal }, token, providerAccountId) => {
    const response = await providerJson<{ data?: { id?: string; name?: string; username?: string; profile_image_url?: string } }>(fetch, 'https://api.x.com/2/users/me?user.fields=id,name,username,profile_image_url', {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    const account = response.data;
    return account?.id === providerAccountId ? { id: account.id, username: account.username, displayName: account.name || account.username || 'Conta do X', avatarUrl: account.profile_image_url, accountType: 'profile' } : null;
  },
  refresh: async ({ credentials: auth, fetch, signal }, refreshToken) => tokenRequest(fetch, auth, {
    refresh_token: refreshToken, grant_type: 'refresh_token', client_id: auth.clientId,
  }, signal),
  revoke: async ({ credentials: auth, fetch, signal }, accessToken) => {
    await providerJson(fetch, 'https://api.x.com/2/oauth2/revoke', {
      method: 'POST', headers: { Authorization: basic(auth.clientId, auth.clientSecret), 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ token: accessToken, token_type_hint: 'access_token', client_id: auth.clientId }), signal,
    });
  },
  publish: async ({ fetch, signal }, token, _account, request) => {
    const text = request.text?.trim();
    if (!text) throw new SocialIntegrationError('SOCIAL_TEXT_REQUIRED', 422, 'Informe o texto da publicação.');
    const payload: Record<string, unknown> = { text };
    if (request.providerAssetIds?.length) payload.media = { media_ids: request.providerAssetIds };
    const response = await providerJson<{ data?: { id?: string } }>(fetch, 'https://api.x.com/2/tweets', {
      method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload), signal,
    });
    if (!response.data?.id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O X não confirmou a publicação.');
    return { providerPostId: response.data.id, status: 'published' };
  },
  analytics: async ({ fetch, signal }, token, account, range) => {
    const url = new URL(`https://api.x.com/2/users/${encodeURIComponent(account.providerAccountId)}`);
    url.searchParams.set('user.fields', 'public_metrics');
    const response = await providerJson<{ data?: { public_metrics?: Record<string, number> } }>(fetch, url.toString(), {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return normalizeSocialAnalytics({
      ...range,
      providerMetrics: response.data?.public_metrics || {},
      mapping: { followers: 'followers_count' },
      rawMetadata: { aggregation: 'profile_lifetime', accessDependsOnXPlan: true },
    });
  },
  capabilities: scopes => capabilities({
    canReadProfile: scopes.includes('users.read'),
    canReadAnalytics: hasAny(scopes, ['tweet.read', 'users.read']),
    canPublishText: scopes.includes('tweet.write'),
    canPublishImage: scopes.includes('tweet.write') && scopes.includes('media.write'),
    canPublishVideo: scopes.includes('tweet.write') && scopes.includes('media.write'),
    canPublishShortVideo: scopes.includes('tweet.write') && scopes.includes('media.write'),
    canReadPosts: scopes.includes('tweet.read'),
    canReadComments: scopes.includes('tweet.read'),
    canReplyComments: scopes.includes('tweet.write'),
  }),
};
