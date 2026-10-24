import { SocialIntegrationError } from './errors';
import type { SocialProviderId, SocialPublishRequest, StoredSocialConnection } from './types';

/** Clicko-side scheduling is advertised only where the official publisher can accept a prepared request. */
export function supportsClickoScheduling(connection: StoredSocialConnection) {
  const caps = connection.capabilities;
  if (connection.provider === 'instagram') return caps.canPublishImage;
  if (connection.provider === 'tiktok') return caps.canPublishVideo || caps.canPublishShortVideo;
  if (['facebook', 'linkedin', 'threads', 'x'].includes(connection.provider)) return caps.canPublishText;
  return false;
}

export function validateScheduledProviderRequest(provider: SocialProviderId, request: SocialPublishRequest) {
  const media = request.mediaUrls || [];
  if (provider === 'instagram' && (request.kind !== 'image' || !media.length)) throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'O Instagram exige uma imagem HTTPS para este fluxo.');
  if (provider === 'tiktok' && (!['video', 'short_video'].includes(request.kind) || !media.length || request.userConsentConfirmed !== true)) {
    throw new SocialIntegrationError('SOCIAL_USER_CONSENT_REQUIRED', 422, 'O TikTok exige vídeo HTTPS e consentimento explícito antes do agendamento.');
  }
  if (['linkedin', 'x'].includes(provider) && request.kind !== 'text') throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'Este formato exige upload de mídia oficial antes do agendamento.');
  if (provider === 'facebook' && !['text', 'image', 'video'].includes(request.kind)) throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'Este formato não está habilitado no Facebook.');
  if (provider === 'threads' && !['text', 'image', 'video', 'short_video'].includes(request.kind)) throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'Este formato não está habilitado no Threads.');
  if (provider === 'pinterest' || provider === 'youtube') throw new SocialIntegrationError('SOCIAL_SCHEDULE_UNAVAILABLE', 409, 'Esta rede ainda não oferece publicação automática no calendário.');
}
