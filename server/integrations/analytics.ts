import type { SocialAnalytics, SocialMetrics } from './types';

const commonMetricKeys = ['followers', 'reach', 'impressions', 'views', 'likes', 'comments', 'shares', 'saves', 'clicks', 'engagements'] as const satisfies ReadonlyArray<keyof SocialMetrics>;

export function normalizeSocialAnalytics(input: { from: string; to: string; providerMetrics: Record<string, number>; mapping: Partial<Record<keyof SocialMetrics, string>>; rawMetadata?: SocialAnalytics['rawMetadata']; nextCursor?: string }): SocialAnalytics {
  const metrics: SocialMetrics = {};
  for (const key of commonMetricKeys) {
    const providerKey = input.mapping[key];
    const value = providerKey ? input.providerMetrics[providerKey] : undefined;
    if (typeof value === 'number' && Number.isFinite(value)) metrics[key] = value;
  }
  return { from: input.from, to: input.to, metrics, providerMetrics: { ...input.providerMetrics }, rawMetadata: input.rawMetadata, nextCursor: input.nextCursor };
}
