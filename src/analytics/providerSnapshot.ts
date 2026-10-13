import type { ConnectedAnalyticsSnapshot } from '../types';

export type ProviderAnalyticsSnapshot = {
  connectionId: string;
  provider: string;
  from: string;
  to: string;
  metrics: Record<string, number>;
  updatedAt: string;
};

/** Official provider totals for a period. Missing metrics stay absent. */
export function providerSnapshotForAccount(snapshot: ProviderAnalyticsSnapshot): ConnectedAnalyticsSnapshot {
  const value = (key: string) => Number.isFinite(snapshot.metrics[key]) ? snapshot.metrics[key] : undefined;
  return {
    source: 'provider-api', dataStatus: 'available', updatedAt: snapshot.updatedAt, refreshIntervalMinutes: 60,
    points: [{ date: snapshot.to, followers: value('followers'), reach: value('reach'), impressions: value('impressions'),
      views: value('views'), likes: value('likes'), comments: value('comments'), shares: value('shares'), saves: value('saves'),
      clicks: value('clicks'), engagements: value('engagements') }],
    unavailableMetrics: ['followers', 'reach', 'impressions', 'views', 'likes', 'comments', 'shares', 'saves', 'clicks', 'engagements']
      .filter(key => value(key) === undefined),
  };
}
