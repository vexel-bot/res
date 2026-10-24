import { providerJson } from '../http';
import { normalizeSocialAnalytics } from '../analytics';
import type { SocialProvider } from '../types';
import { capabilities, configured, postForm, requireToken } from './shared';

const credentials = () => configured(process.env.GOOGLE_CLIENT_ID, process.env.GOOGLE_CLIENT_SECRET, process.env.GOOGLE_REDIRECT_URI);
const readonly = 'https://www.googleapis.com/auth/youtube.readonly';

export const youtubeProvider: SocialProvider = {
  id: 'youtube',
  label: 'YouTube',
  requiredEnvironment: ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI'],
  credentials,
  usesPkce: true,
  authorizationUrl: ({ credentials: auth, redirectUri, state, codeChallenge }) => {
    const url = new URL('https://accounts.google.com/o/oauth2/v2/auth');
    url.searchParams.set('client_id', auth.clientId);
    url.searchParams.set('redirect_uri', redirectUri);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', readonly);
    url.searchParams.set('access_type', 'offline');
    url.searchParams.set('include_granted_scopes', 'true');
    url.searchParams.set('prompt', 'consent');
    url.searchParams.set('state', state);
    if (codeChallenge) {
      url.searchParams.set('code_challenge', codeChallenge);
      url.searchParams.set('code_challenge_method', 'S256');
    }
    return url.toString();
  },
  exchangeCode: async ({ credentials: auth, fetch, signal }, input) => requireToken(await postForm(fetch, 'https://oauth2.googleapis.com/token', {
    client_id: auth.clientId,
    client_secret: auth.clientSecret,
    code: input.code,
    grant_type: 'authorization_code',
    redirect_uri: input.redirectUri,
    ...(input.codeVerifier ? { code_verifier: input.codeVerifier } : {}),
  }, signal)),
  accounts: async ({ fetch, signal }, token) => {
    const data = await providerJson<{ items?: Array<{ id?: string; snippet?: { title?: string; customUrl?: string; thumbnails?: { default?: { url?: string } } } }> }>(fetch, 'https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true', {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return (data.items || []).filter(item => item.id).map(item => ({
      id: item.id!, username: item.snippet?.customUrl, displayName: item.snippet?.title || 'Canal do YouTube', avatarUrl: item.snippet?.thumbnails?.default?.url,
      accountType: 'channel',
    }));
  },
  refresh: async ({ credentials: auth, fetch, signal }, refreshToken) => requireToken(await postForm(fetch, 'https://oauth2.googleapis.com/token', {
    client_id: auth.clientId,
    client_secret: auth.clientSecret,
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
  }, signal)),
  revoke: async ({ fetch, signal }, accessToken) => {
    await postForm(fetch, 'https://oauth2.googleapis.com/revoke', { token: accessToken }, signal);
  },
  analytics: async ({ fetch, signal }, token, account, range) => {
    const url = new URL('https://www.googleapis.com/youtube/v3/channels');
    url.searchParams.set('part', 'statistics');
    url.searchParams.set('id', account.providerAccountId);
    const data = await providerJson<{ items?: Array<{ statistics?: Record<string, string> }> }>(fetch, url.toString(), {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    const statistics = data.items?.[0]?.statistics || {};
    const providerMetrics = Object.fromEntries(Object.entries(statistics)
      .map(([key, value]) => [key, Number(value)] as const)
      .filter(([, value]) => Number.isFinite(value)));
    return normalizeSocialAnalytics({
      ...range,
      providerMetrics,
      mapping: { followers: 'subscriberCount', views: 'viewCount' },
      rawMetadata: { aggregation: 'channel_lifetime', hiddenSubscriberCount: !Object.hasOwn(statistics, 'subscriberCount') },
    });
  },
  capabilities: scopes => capabilities({
    canReadProfile: scopes.includes(readonly),
    // The implemented collector is a channel statistics snapshot from the
    // YouTube Data API, so youtube.readonly is the permission it actually uses.
    canReadAnalytics: scopes.includes(readonly),
    canPublishImage: false,
    // Do not advertise uploads until the resumable binary media pipeline is
    // connected to this provider. The upload scope alone is not a capability.
    canPublishVideo: false,
    canPublishShortVideo: false,
    canReadPosts: scopes.includes(readonly),
    canReadComments: scopes.includes(readonly),
    canReplyComments: scopes.includes('https://www.googleapis.com/auth/youtube.force-ssl'),
  }),
};
