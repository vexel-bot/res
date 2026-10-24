import { providerJson, providerResponse } from '../http';
import { SocialIntegrationError } from '../errors';
import type { ProviderResource, SocialProvider, SocialPublishRequest } from '../types';
import { capabilities, configured, hasAny, postForm, requireToken, scopeList } from './shared';

const defaultScopes = ['openid', 'profile', 'email', 'w_member_social'];
const requestedScopes = () => scopeList(process.env.LINKEDIN_SCOPES || defaultScopes.join(' '));
const credentials = () => configured(process.env.LINKEDIN_CLIENT_ID, process.env.LINKEDIN_CLIENT_SECRET, process.env.LINKEDIN_REDIRECT_URI);
const apiVersion = () => process.env.LINKEDIN_API_VERSION || '202606';
const apiHeaders = (token: string) => ({
  Authorization: `Bearer ${token}`,
  'LinkedIn-Version': apiVersion(),
  'X-Restli-Protocol-Version': '2.0.0',
});

function linkedinPostBody(accountId: string, request: SocialPublishRequest) {
  const body: Record<string, unknown> = {
    author: accountId.startsWith('urn:li:') ? accountId : `urn:li:person:${accountId}`,
    commentary: request.text || '',
    visibility: 'PUBLIC',
    distribution: { feedDistribution: 'MAIN_FEED', targetEntities: [], thirdPartyDistributionChannels: [] },
    lifecycleState: 'PUBLISHED',
    isReshareDisabledByAuthor: false,
  };
  const asset = request.providerAssetIds?.[0];
  if (request.kind !== 'text' && !asset) {
    throw new SocialIntegrationError('SOCIAL_MEDIA_ASSET_REQUIRED', 422, 'A mídia precisa ser enviada e registrada antes da publicação no LinkedIn.');
  }
  if (asset && request.kind === 'image') body.content = { media: { id: asset, title: request.title || '' } };
  if (asset && request.kind === 'video') body.content = { media: { id: asset, title: request.title || '' } };
  if (asset && request.kind === 'document') body.content = { media: { id: asset, title: request.title || '' } };
  return body;
}

export const linkedinProvider: SocialProvider = {
  id: 'linkedin',
  label: 'LinkedIn',
  requiredEnvironment: ['LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET', 'LINKEDIN_REDIRECT_URI'],
  credentials,
  usesPkce: false,
  authorizationUrl: ({ credentials: auth, redirectUri, state }) => {
    const url = new URL('https://www.linkedin.com/oauth/v2/authorization');
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('client_id', auth.clientId);
    url.searchParams.set('redirect_uri', redirectUri);
    url.searchParams.set('state', state);
    url.searchParams.set('scope', requestedScopes().join(' '));
    return url.toString();
  },
  exchangeCode: async ({ credentials: auth, fetch, signal }, input) => {
    const token = requireToken(await postForm(fetch, 'https://www.linkedin.com/oauth/v2/accessToken', {
      grant_type: 'authorization_code', code: input.code, client_id: auth.clientId,
      client_secret: auth.clientSecret, redirect_uri: input.redirectUri,
    }, signal));
    return { ...token, scopes: token.scopes.length ? token.scopes : requestedScopes() };
  },
  accounts: async ({ fetch, signal }, token) => {
    const profile = await providerJson<{ sub?: string; name?: string; picture?: string }>(fetch, 'https://api.linkedin.com/v2/userinfo', {
      headers: apiHeaders(token.accessToken), signal,
    });
    return profile.sub ? [{ id: profile.sub, displayName: profile.name || 'Perfil do LinkedIn', avatarUrl: profile.picture, accountType: 'profile' }] : [];
  },
  account: async ({ fetch, signal }, token, providerAccountId) => {
    const profile = await providerJson<{ sub?: string; name?: string; picture?: string }>(fetch, 'https://api.linkedin.com/v2/userinfo', {
      headers: apiHeaders(token.accessToken), signal,
    });
    return profile.sub === providerAccountId ? { id: profile.sub, displayName: profile.name || 'Perfil do LinkedIn', avatarUrl: profile.picture, accountType: 'profile' } : null;
  },
  resources: async ({ fetch, signal }, token, account) => {
    const resources: ProviderResource[] = [{ id: account.providerAccountId, name: account.displayName, type: 'profile', handle: account.username, avatarUrl: account.avatarUrl }];
    if (!token.scopes.includes('rw_organization_admin')) return resources;
    const access = await providerJson<{ elements?: Array<{ organization?: string }> }>(fetch, 'https://api.linkedin.com/rest/organizationAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED', {
      headers: apiHeaders(token.accessToken), signal,
    });
    for (const item of access.elements || []) {
      const organizationId = item.organization?.split(':').pop();
      if (!organizationId) continue;
      const organization = await providerJson<{ id?: number; localizedName?: string; vanityName?: string }>(fetch, `https://api.linkedin.com/rest/organizations/${encodeURIComponent(organizationId)}`, {
        headers: apiHeaders(token.accessToken), signal,
      });
      if (organization.id) resources.push({ id: `urn:li:organization:${organization.id}`, name: organization.localizedName || organization.vanityName || 'Organização do LinkedIn', type: 'organization', handle: organization.vanityName, avatarUrl: undefined });
    }
    return resources;
  },
  refresh: async ({ credentials: auth, fetch, signal }, refreshToken) => requireToken(await postForm(fetch, 'https://www.linkedin.com/oauth/v2/accessToken', {
    grant_type: 'refresh_token', refresh_token: refreshToken, client_id: auth.clientId, client_secret: auth.clientSecret,
  }, signal)),
  revoke: async ({ credentials: auth, fetch, signal }, accessToken) => {
    await postForm(fetch, 'https://www.linkedin.com/oauth/v2/revoke', {
      token: accessToken, client_id: auth.clientId, client_secret: auth.clientSecret,
    }, signal);
  },
  publish: async ({ fetch, signal }, token, account, request) => {
    const body = linkedinPostBody(request.destinationId || account.providerAccountId, request);
    const { response } = await providerResponse<Record<string, unknown>>(fetch, 'https://api.linkedin.com/rest/posts', {
      method: 'POST', headers: { ...apiHeaders(token.accessToken), 'Content-Type': 'application/json' },
      body: JSON.stringify(body), signal,
    });
    const id = response.headers.get('x-restli-id');
    if (!id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O LinkedIn não confirmou a publicação.');
    return { providerPostId: id, status: 'published' };
  },
  capabilities: scopes => capabilities({
    canReadProfile: hasAny(scopes, ['openid', 'profile']),
    canReadAnalytics: hasAny(scopes, ['r_organization_social', 'r_organization_social_feed']),
    canPublishText: hasAny(scopes, ['w_member_social', 'w_organization_social', 'w_organization_social_feed']),
    canPublishImage: hasAny(scopes, ['w_member_social', 'w_organization_social', 'w_organization_social_feed']),
    canPublishVideo: hasAny(scopes, ['w_member_social', 'w_organization_social', 'w_organization_social_feed']),
    canPublishDocument: hasAny(scopes, ['w_member_social', 'w_organization_social', 'w_organization_social_feed']),
    canReadPosts: hasAny(scopes, ['r_member_social', 'r_organization_social', 'r_organization_social_feed']),
    canReadComments: hasAny(scopes, ['r_member_social', 'r_organization_social', 'r_organization_social_feed']),
    canReplyComments: hasAny(scopes, ['w_member_social', 'w_organization_social', 'w_organization_social_feed']),
  }),
};
