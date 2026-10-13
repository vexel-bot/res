import type { SocialProvider, SocialProviderId } from '../types';
import { facebookProvider, instagramProvider } from './meta';
import { linkedinProvider } from './linkedin';
import { pinterestProvider } from './pinterest';
import { threadsProvider } from './threads';
import { tiktokProvider } from './tiktok';
import { xProvider } from './x';
import { youtubeProvider } from './youtube';

export function socialProviderRegistry() {
  const providers: SocialProvider[] = [instagramProvider, facebookProvider, tiktokProvider, youtubeProvider, linkedinProvider, threadsProvider, pinterestProvider, xProvider];
  return new Map<SocialProviderId, SocialProvider>(providers.map(provider => [provider.id, provider]));
}
