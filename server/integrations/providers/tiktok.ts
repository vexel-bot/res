import { providerJson } from '../http';
import { SocialIntegrationError } from '../errors';
import type { SocialProvider } from '../types';
import { capabilities, configured, hasAny, postForm, requireToken } from './shared';

const credentials = () => configured(process.env.TIKTOK_CLIENT_KEY, process.env.TIKTOK_CLIENT_SECRET, process.env.TIKTOK_REDIRECT_URI);

export const tiktokProvider: SocialProvider = {
  id: 'tiktok',
  label: 'TikTok',
  requiredEnvironment: ['TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET', 'TIKTOK_REDIRECT_URI'],
  credentials,
  usesPkce: false,
  authorizationUrl: ({ credentials: auth, redirectUri, state }) => {
    const url = new URL('https://www.tiktok.com/v2/auth/authorize/');
    url.searchParams.set('client_key', auth.clientId);
    url.searchParams.set('redirect_uri', redirectUri);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', ['user.info.basic', 'video.list', 'video.publish'].join(','));
    url.searchParams.set('state', state);
    return url.toString();
  },
  exchangeCode: async ({ credentials: auth, fetch, signal }, input) => requireToken(await postForm(fetch, 'https://open.tiktokapis.com/v2/oauth/token/', {
    client_key: auth.clientId,
    client_secret: auth.clientSecret,
    code: input.code,
    grant_type: 'authorization_code',
    redirect_uri: input.redirectUri,
  }, signal)),
  accounts: async ({ fetch, signal }, token) => {
    const data = await providerJson<{ data?: { user?: { open_id?: string; display_name?: string; avatar_url?: string; username?: string } } }>(fetch, 'https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,avatar_url,username', {
      headers: { Authorization: `Bearer ${token.accessToken}` }, signal,
    });
    const user = data.data?.user;
    return user?.open_id ? [{ id: user.open_id, username: user.username, displayName: user.display_name || user.username || 'Conta do TikTok', avatarUrl: user.avatar_url, accountType: 'profile' }] : [];
  },
  refresh: async ({ credentials: auth, fetch, signal }, refreshToken) => requireToken(await postForm(fetch, 'https://open.tiktokapis.com/v2/oauth/token/', {
    client_key: auth.clientId,
    client_secret: auth.clientSecret,
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
  }, signal)),
  revoke: async ({ credentials: auth, fetch, signal }, accessToken) => {
    await postForm(fetch, 'https://open.tiktokapis.com/v2/oauth/revoke/', { client_key: auth.clientId, client_secret: auth.clientSecret, token: accessToken }, signal);
  },
  publish: async ({ fetch, signal }, token, _account, request) => {
    if (!request.userConsentConfirmed) throw new SocialIntegrationError('SOCIAL_USER_CONSENT_REQUIRED', 422, 'Confirme o consentimento do usuário antes de enviar o conteúdo ao TikTok.');
    const videoUrl = request.mediaUrls?.[0];
    if ((request.kind !== 'video' && request.kind !== 'short_video') || !videoUrl) throw new SocialIntegrationError('SOCIAL_MEDIA_REQUIRED', 422, 'Informe um vídeo HTTPS compatível para publicar no TikTok.');
    const creator = await providerJson<{ data?: { privacy_level_options?: string[]; max_video_post_duration_sec?: number } }>(fetch, 'https://open.tiktokapis.com/v2/post/publish/creator_info/query/', {
      method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}`, 'Content-Type': 'application/json; charset=UTF-8' },
      body: '{}', signal,
    });
    const allowedPrivacyLevels = creator.data?.privacy_level_options || [];
    const privacyLevel = request.privacyLevel || 'SELF_ONLY';
    if (!allowedPrivacyLevels.includes(privacyLevel)) {
      throw new SocialIntegrationError('SOCIAL_PRIVACY_LEVEL_UNAVAILABLE', 422, 'A privacidade escolhida não está disponível para esta conta do TikTok.');
    }
    const created = await providerJson<{ data?: { publish_id?: string } }>(fetch, 'https://open.tiktokapis.com/v2/post/publish/video/init/', {
      method: 'POST', headers: { Authorization: `Bearer ${token.accessToken}`, 'Content-Type': 'application/json; charset=UTF-8' },
      body: JSON.stringify({
        post_info: {
          title: request.text || request.title || '',
          privacy_level: privacyLevel,
          disable_duet: request.disableDuet ?? false,
          disable_comment: request.disableComment ?? false,
          disable_stitch: request.disableStitch ?? false,
        },
        source_info: { source: 'PULL_FROM_URL', video_url: videoUrl },
      }), signal,
    });
    const id = created.data?.publish_id;
    if (!id) throw new SocialIntegrationError('SOCIAL_PROVIDER_REJECTED', 502, 'O TikTok não confirmou o envio da publicação.');
    return { providerPostId: id, status: 'processing' };
  },
  capabilities: scopes => capabilities({
    canReadProfile: scopes.includes('user.info.basic'),
    canReadAnalytics: false,
    // Photo posting uses a separate official flow. Do not advertise it until
    // that adapter and the required product approval are configured.
    canPublishImage: false,
    canPublishVideo: scopes.includes('video.publish'),
    canPublishShortVideo: scopes.includes('video.publish'),
    canReadPosts: hasAny(scopes, ['video.list', 'video.publish']),
  }),
};
