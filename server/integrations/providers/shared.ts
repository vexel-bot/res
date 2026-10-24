import { providerJson } from '../http';
import type { ProviderCredentials, ProviderTokenSet, SocialCapabilities } from '../types';

export const expiresAt = (seconds: unknown) => {
  const value = Number(seconds);
  return Number.isFinite(value) && value > 0 ? new Date(Date.now() + value * 1000).toISOString() : undefined;
};

export const scopeList = (value: unknown) => String(value || '').split(/[ ,]+/).map(item => item.trim()).filter(Boolean);

export function requireToken(data: Record<string, unknown>): ProviderTokenSet {
  const accessToken = typeof data.access_token === 'string' ? data.access_token : '';
  if (!accessToken) throw new Error('SOCIAL_TOKEN_MISSING');
  return {
    accessToken,
    refreshToken: typeof data.refresh_token === 'string' ? data.refresh_token : undefined,
    expiresAt: expiresAt(data.expires_in),
    refreshTokenExpiresAt: expiresAt(data.refresh_expires_in),
    scopes: scopeList(data.scope),
  };
}

export const hasAny = (scopes: string[], expected: string[]) => expected.some(scope => scopes.includes(scope));

export const capabilities = (values: Partial<SocialCapabilities>): SocialCapabilities => ({
  canReadProfile: false,
  canReadAnalytics: false,
  canPublishText: false,
  canPublishImage: false,
  canPublishCarousel: false,
  canPublishVideo: false,
  canPublishShortVideo: false,
  canPublishStory: false,
  canPublishDocument: false,
  canSchedule: false,
  canReadPosts: false,
  canReadComments: false,
  canReplyComments: false,
  ...values,
});

export async function postForm(fetcher: typeof fetch, url: string, values: Record<string, string>, signal: AbortSignal) {
  return providerJson<Record<string, unknown>>(fetcher, url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(values),
    signal,
  });
}

export function configured(clientId: string | undefined, clientSecret: string | undefined, redirectUri: string | undefined): ProviderCredentials | null {
  return clientId && clientSecret && redirectUri ? { clientId, clientSecret, redirectUri } : null;
}
