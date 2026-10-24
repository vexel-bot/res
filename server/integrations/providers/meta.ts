import { providerJson } from '../http';
import { SocialIntegrationError } from '../errors';
import type { ProviderAccount, SocialProvider } from '../types';
import { capabilities, configured, expiresAt, hasAny, scopeList } from './shared';

type MetaPage = {
  id?: string;
  name?: string;
  username?: string;
  access_token?: string;
  tasks?: string[];
  picture?: { data?: { url?: string } };
  instagram_business_account?: { id?: string; username?: string; name?: string; profile_picture_url?: string };
};

const graphVersion = () => process.env.META_GRAPH_VERSION || 'v23.0';
const graph = () => `https://graph.facebook.com/${graphVersion()}`;
const credentials = () => configured(
  process.env.META_APP_ID || process.env.META_CLIENT_ID,
  process.env.META_APP_SECRET || process.env.META_CLIENT_SECRET,
  process.env.META_REDIRECT_URI,
);

async function permissions(fetcher: typeof fetch, accessToken: string, signal: AbortSignal) {
  const data = await providerJson<{ data?: Array<{ permission?: string; status?: string }> }>(fetcher, `${graph()}/me/permissions`, {
    headers: { Authorization: `Bearer ${accessToken}` }, signal,
  });
  return (data.data || []).filter(item => item.status === 'granted' && item.permission).map(item => item.permission!);
}

const base = (id: 'instagram' | 'facebook', label: string, scopes: string[]): Omit<SocialProvider, 'accounts' | 'capabilities'> => ({
  id,
  label,
  requiredEnvironment: ['META_APP_ID', 'META_APP_SECRET', 'META_REDIRECT_URI'],
  credentials,
  usesPkce: false,
  authorizationUrl: ({ credentials: auth, redirectUri, state }) => {
    const url = new URL(`https://www.facebook.com/${graphVersion()}/dialog/oauth`);
    url.searchParams.set('client_id', auth.clientId);
    url.searchParams.set('redirect_uri', redirectUri);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', scopes.join(','));
    url.searchParams.set('state', state);
    return url.toString();
  },
  exchangeCode: async ({ credentials: auth, fetch, signal }, input) => {
    const exchangeUrl = new URL(`${graph()}/oauth/access_token`);
    exchangeUrl.searchParams.set('client_id', auth.clientId);
    exchangeUrl.searchParams.set('client_secret', auth.clientSecret);
    exchangeUrl.searchParams.set('redirect_uri', input.redirectUri);
    exchangeUrl.searchParams.set('code', input.code);
    const short = await providerJson<Record<string, unknown>>(fetch, exchangeUrl.toString(), { signal });
    if (typeof short.access_token !== 'string') throw new Error('SOCIAL_TOKEN_MISSING');

    // Page and Instagram tokens should be derived from a long-lived user token.
    // This is still server-side: the app secret and both token forms never cross
    // the public API boundary or enter application logs.
    const longLivedUrl = new URL(`${graph()}/oauth/access_token`);
    longLivedUrl.searchParams.set('grant_type', 'fb_exchange_token');
    longLivedUrl.searchParams.set('client_id', auth.clientId);
    longLivedUrl.searchParams.set('client_secret', auth.clientSecret);
    longLivedUrl.searchParams.set('fb_exchange_token', short.access_token);
    const long = await providerJson<Record<string, unknown>>(fetch, longLivedUrl.toString(), { signal });
    if (typeof long.access_token !== 'string') throw new Error('SOCIAL_TOKEN_MISSING');
    return { accessToken: long.access_token, expiresAt: expiresAt(long.expires_in), scopes: scopeList(long.scope || short.scope) };
  },
  grantedScopes: ({ fetch, signal }, token) => permissions(fetch, token.accessToken, signal),
  refresh: undefined,
  revoke: async ({ fetch, signal }, accessToken) => {
    await providerJson(fetch, `${graph()}/me/permissions`, { method: 'DELETE', headers: { Authorization: `Bearer ${accessToken}` }, signal });
  },
});

export const facebookProvider: SocialProvider = {
  ...base('facebook', 'Facebook', ['pages_show_list', 'pages_read_engagement', 'pages_manage_posts', 'pages_manage_engagement']),
  accounts: async ({ fetch, signal }, token) => {
    const data = await providerJson<{ data?: MetaPage[] }>(fetch, `${graph()}/me/accounts?fields=id,name,username,picture,access_token,tasks`, {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return (data.data || []).filter(page => page.id && page.name).map<ProviderAccount>(page => ({
      id: page.id!, username: page.username, displayName: page.name!, avatarUrl: page.picture?.data?.url,
      accessToken: page.access_token, accountType: 'page', metadata: { tasks: page.tasks || [] },
    }));
  },
  account: async ({ fetch, signal }, token, providerAccountId) => {
    const page = await providerJson<MetaPage>(fetch, `${graph()}/${encodeURIComponent(providerAccountId)}?fields=id,name,username,picture`, {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return page.id && page.name ? { id: page.id, username: page.username, displayName: page.name, avatarUrl: page.picture?.data?.url, accountType: 'page' } : null;
  },
  publish: async ({ fetch, signal }, token, account, request) => {
    const mediaUrl = request.mediaUrls?.[0];
    let endpoint = `${graph()}/${encodeURIComponent(account.providerAccountId)}/feed`;
    const payload: Record<string, string> = {};
    if (request.kind === 'text') payload.message = request.text || '';
    else if (request.kind === 'image' && mediaUrl) {
      endpoint = `${graph()}/${encodeURIComponent(account.providerAccountId)}/photos`;
      payload.url = mediaUrl;
      if (request.text) payload.caption = request.text;
    } else if (request.kind === 'video' && mediaUrl) {
      endpoint = `${graph()}/${encodeURIComponent(account.providerAccountId)}/videos`;
      payload.file_url = mediaUrl;
      if (request.text) payload.description = request.text;
    } else {
      throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'Este formato exige um fluxo de mídia ainda não habilitado para esta Página.');
    }
    const data = await providerJson<{ id?: string; post_id?: string }>(fetch, endpoint, {
      method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}`, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(payload), signal,
    });
    const id = data.post_id || data.id;
    if (!id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O Facebook não confirmou a publicação.');
    return { providerPostId: id, status: 'published' };
  },
  capabilities: scopes => capabilities({
    canReadProfile: hasAny(scopes, ['pages_show_list', 'pages_read_engagement']),
    canReadAnalytics: scopes.includes('pages_read_engagement'),
    canPublishText: scopes.includes('pages_manage_posts'),
    canPublishImage: scopes.includes('pages_manage_posts'),
    canPublishCarousel: false,
    canPublishVideo: scopes.includes('pages_manage_posts'),
    canPublishShortVideo: false,
    canReadPosts: scopes.includes('pages_read_engagement'),
    canReadComments: scopes.includes('pages_read_engagement'),
    canReplyComments: scopes.includes('pages_manage_engagement'),
  }),
};

export const instagramProvider: SocialProvider = {
  ...base('instagram', 'Instagram', ['pages_show_list', 'pages_read_engagement', 'instagram_basic', 'instagram_content_publish', 'instagram_manage_insights', 'instagram_manage_comments']),
  accounts: async ({ fetch, signal }, token) => {
    const data = await providerJson<{ data?: MetaPage[] }>(fetch, `${graph()}/me/accounts?fields=id,name,access_token,instagram_business_account{id,username,name,profile_picture_url}`, {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return (data.data || []).filter(page => page.instagram_business_account?.id).map<ProviderAccount>(page => ({
      id: page.instagram_business_account!.id!,
      username: page.instagram_business_account!.username,
      displayName: page.instagram_business_account!.name || page.instagram_business_account!.username || page.name || 'Conta profissional do Instagram',
      avatarUrl: page.instagram_business_account!.profile_picture_url,
      accessToken: page.access_token,
      accountType: 'professional',
      metadata: { pageId: page.id || '' },
    }));
  },
  account: async ({ fetch, signal }, token, providerAccountId) => {
    const account = await providerJson<{ id?: string; username?: string; name?: string; profile_picture_url?: string }>(fetch, `${graph()}/${encodeURIComponent(providerAccountId)}?fields=id,username,name,profile_picture_url`, {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    return account.id ? { id: account.id, username: account.username, displayName: account.name || account.username || 'Conta profissional do Instagram', avatarUrl: account.profile_picture_url, accountType: 'professional' } : null;
  },
  publish: async ({ fetch, signal }, token, account, request) => {
    const media = request.mediaUrls || [];
    const createContainer = async (values: Record<string, string>) => {
      const data = await providerJson<{ id?: string }>(fetch, `${graph()}/${encodeURIComponent(account.providerAccountId)}/media`, {
        method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}`, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(values), signal,
      });
      if (!data.id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O Instagram não criou o contêiner de mídia.');
      return data.id;
    };
    let creationId: string;
    if (request.kind === 'carousel') {
      if (media.length < 2 || media.length > 10) throw new SocialIntegrationError('SOCIAL_MEDIA_REQUIRED', 422, 'O carrossel do Instagram precisa ter entre 2 e 10 mídias.');
      const children = [];
      for (const url of media) children.push(await createContainer({ image_url: url, is_carousel_item: 'true' }));
      creationId = await createContainer({ media_type: 'CAROUSEL', children: children.join(','), caption: request.text || '' });
    } else {
      const mediaUrl = media[0];
      if (!mediaUrl) throw new SocialIntegrationError('SOCIAL_MEDIA_REQUIRED', 422, 'Informe uma mídia acessível para publicar no Instagram.');
      const values: Record<string, string> = { caption: request.text || '' };
      if (request.kind === 'image') values.image_url = mediaUrl;
      else if (request.kind === 'video' || request.kind === 'short_video') { values.video_url = mediaUrl; values.media_type = 'REELS'; }
      else if (request.kind === 'story') {
        values.media_type = 'STORIES';
        if (/\.(?:jpe?g|png|webp)(?:$|[?#])/i.test(mediaUrl)) values.image_url = mediaUrl;
        else values.video_url = mediaUrl;
      }
      else throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'Este formato não é aceito pelo Instagram nesta conexão.');
      creationId = await createContainer(values);
    }
    const published = await providerJson<{ id?: string }>(fetch, `${graph()}/${encodeURIComponent(account.providerAccountId)}/media_publish`, {
      method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}`, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ creation_id: creationId }), signal,
    });
    if (!published.id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O Instagram não confirmou a publicação.');
    return { providerPostId: published.id, status: 'published' };
  },
  capabilities: scopes => capabilities({
    canReadProfile: scopes.includes('instagram_basic'),
    canReadAnalytics: scopes.includes('instagram_manage_insights'),
    canPublishImage: scopes.includes('instagram_content_publish'),
    canPublishCarousel: scopes.includes('instagram_content_publish'),
    canPublishVideo: scopes.includes('instagram_content_publish'),
    canPublishShortVideo: scopes.includes('instagram_content_publish'),
    canPublishStory: scopes.includes('instagram_content_publish'),
    canReadPosts: scopes.includes('instagram_basic'),
    canReadComments: scopes.includes('instagram_manage_comments'),
    canReplyComments: scopes.includes('instagram_manage_comments'),
  }),
};
