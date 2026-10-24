import { SocialIntegrationError } from './errors';
import type { SocialCapabilities, SocialPublishKind, SocialPublishRequest } from './types';

const capabilityByKind: Record<SocialPublishKind, keyof SocialCapabilities> = {
  text: 'canPublishText',
  image: 'canPublishImage',
  carousel: 'canPublishCarousel',
  video: 'canPublishVideo',
  short_video: 'canPublishShortVideo',
  story: 'canPublishStory',
  document: 'canPublishDocument',
};

function validHttpsUrl(value: string) {
  try { return new URL(value).protocol === 'https:'; } catch { return false; }
}

export function validatePublishRequest(input: unknown, capabilities: SocialCapabilities, now = Date.now()): SocialPublishRequest {
  if (!input || typeof input !== 'object') throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'Escolha um formato de publicação compatível.');
  const request = input as Partial<SocialPublishRequest>;
  if (!request.kind || !Object.hasOwn(capabilityByKind, request.kind)) {
    throw new SocialIntegrationError('SOCIAL_FORMAT_UNSUPPORTED', 422, 'Escolha um formato de publicação compatível.');
  }
  if (!capabilities[capabilityByKind[request.kind]]) {
    throw new SocialIntegrationError('SOCIAL_CAPABILITY_UNAVAILABLE', 403, 'Esta conta ou autorização não permite esse formato de publicação.');
  }
  if (request.text && request.text.length > 20_000) throw new SocialIntegrationError('SOCIAL_CONTENT_INVALID', 422, 'O texto excede o limite aceito pela Clicko.');
  if (request.mediaUrls?.some(url => !validHttpsUrl(url))) throw new SocialIntegrationError('SOCIAL_MEDIA_URL_INVALID', 422, 'As mídias precisam usar endereços HTTPS válidos.');
  if (request.scheduledAt) {
    const scheduledAt = Date.parse(request.scheduledAt);
    if (!Number.isFinite(scheduledAt) || scheduledAt <= now) throw new SocialIntegrationError('SOCIAL_SCHEDULE_INVALID', 422, 'Informe uma data futura válida para o agendamento.');
    if (!capabilities.canSchedule) throw new SocialIntegrationError('SOCIAL_SCHEDULING_UNAVAILABLE', 409, 'Esta rede exige que a Clicko publique no horário agendado; o executor ainda não está habilitado.');
  }
  return request as SocialPublishRequest;
}
