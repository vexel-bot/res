import type { ConnectedAccount, LibraryAsset, Post } from '../types';

type PublishKind = 'text' | 'image' | 'carousel' | 'video' | 'short_video' | 'story' | 'document';
export type CalendarPublishRequest = { kind: PublishKind; text?: string; title?: string; mediaUrls?: string[]; userConsentConfirmed?: boolean };

/** Converts a calendar post to an official-provider request, never uploading a browser-local URL. */
export function calendarPublishRequest(post: Post, account: ConnectedAccount, assets: LibraryAsset[]): CalendarPublishRequest {
  const media = (post.assetIds || []).map(id => assets.find(asset => asset.id === id)?.url).filter((url): url is string => Boolean(url && url.startsWith('https://')));
  if (post.imageUrl?.startsWith('https://') && !media.includes(post.imageUrl)) media.unshift(post.imageUrl);
  if (post.videoUrl?.startsWith('https://') && !media.includes(post.videoUrl)) media.unshift(post.videoUrl);
  const capabilities = account.capabilities;
  let kind: PublishKind;
  if (post.format === 'post') kind = media.length ? 'image' : 'text';
  else if (post.format === 'carousel') kind = 'carousel';
  else if (post.format === 'reels' || post.format === 'youtube-short') kind = 'short_video';
  else if (post.format === 'story') kind = 'story';
  else if (post.format === 'thread') kind = 'text';
  else throw new Error('Este formato é de planejamento e não possui publicação oficial nesta rede.');
  const capability = ({ text: 'canPublishText', image: 'canPublishImage', carousel: 'canPublishCarousel', video: 'canPublishVideo', short_video: 'canPublishShortVideo', story: 'canPublishStory', document: 'canPublishDocument' } as const)[kind];
  if (!capabilities?.[capability]) throw new Error('A conta não tem permissão para publicar este formato.');
  if (kind !== 'text' && !media.length) throw new Error('Escolha uma mídia HTTPS disponível na Biblioteca antes de agendar.');
  if (kind === 'carousel' && media.length < 2) throw new Error('O carrossel precisa de ao menos duas mídias acessíveis.');
  if (kind === 'text' && !post.copy.trim()) throw new Error('Informe o texto antes de agendar.');
  if (account.platform === 'tiktok' && !post.tiktokConsentConfirmed) throw new Error('Confirme o consentimento para publicar no TikTok.');
  if (['linkedin', 'x'].includes(account.platform) && kind !== 'text') throw new Error('O upload oficial de mídia para esta rede ainda não está disponível no Calendário.');
  return { kind, text: post.copy, title: post.title, ...(media.length ? { mediaUrls: media } : {}),
    ...(account.platform === 'tiktok' ? { userConsentConfirmed: true } : {}) };
}
