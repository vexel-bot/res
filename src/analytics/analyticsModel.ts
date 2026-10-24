import type { ConnectedAccount, Post, PostFormat, SocialPlatform } from '../types';

export type AnalyticsSource = 'connected' | 'demo';
export type AnalyticsMetric = 'followers' | 'reach' | 'impressions' | 'engagements' | 'likes' | 'comments' | 'shares' | 'saves' | 'clicks' | 'views' | 'posts';

export interface AnalyticsPoint {
  date: string;
  followers: number | null;
  gained: number | null;
  lost: number | null;
  reach: number | null;
  impressions: number | null;
  engagements: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  saves: number | null;
  replies?: number | null;
  clicks: number | null;
  views: number | null;
  conversions?: number | null;
  spend?: number | null;
  revenue?: number | null;
  retention?: number | null;
  posts: number;
}

export interface AnalyticsContent {
  id: string;
  title: string;
  date: string;
  network: SocialPlatform;
  format: PostFormat;
  thumbnail?: string;
  reach: number | null;
  impressions: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  saves: number | null;
  replies?: number | null;
  clicks: number | null;
  views: number | null;
  conversions?: number | null;
  spend?: number | null;
  revenue?: number | null;
  engagementRate: number | null;
  caption?: string;
  campaignId?: string;
  status?: Post['status'];
  origin?: Post['origin'];
  paid?: boolean | null;
}

export interface FormatPerformance {
  format: PostFormat;
  publications: number;
  averageReach: number | null;
  averageEngagement: number | null;
  averageImpressions: number | null;
  averageViews: number | null;
  totalShares: number | null;
  efficiency: number | null;
}

export interface NetworkAnalytics {
  accountId: string;
  accountLabel: string;
  network: SocialPlatform;
  source: AnalyticsSource;
  connected: boolean;
  lastSync?: string;
  bestTime?: string;
  points: AnalyticsPoint[];
  contents: AnalyticsContent[];
  formats: FormatPerformance[];
}

export interface AnalyticsDataset {
  source: AnalyticsSource;
  networks: NetworkAnalytics[];
}

export const networkMeta: Record<SocialPlatform, { label: string; color: string; short: string }> = {
  instagram: { label: 'Instagram', color: '#FF7F50', short: 'IG' },
  facebook: { label: 'Facebook', color: '#FF7F50', short: 'FB' },
  tiktok: { label: 'TikTok', color: '#FFFFFF', short: 'TK' },
  youtube: { label: 'YouTube', color: '#FF7F50', short: 'YT' },
  linkedin: { label: 'LinkedIn', color: '#FF7F50', short: 'IN' },
  x: { label: 'X', color: 'rgba(255,255,255,0.72)', short: 'X' },
  pinterest: { label: 'Pinterest', color: '#FF7F50', short: 'PT' },
  threads: { label: 'Threads', color: 'rgba(255,255,255,0.88)', short: 'TH' },
};

const isConnected = (account: ConnectedAccount) => Boolean(
  account.connected && ['connected', 'synced', 'syncing'].includes(account.connectionStatus || ''),
);

const sumAvailable = (values: Array<number | null | undefined>) => {
  const available = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  return available.length ? available.reduce((total, value) => total + value, 0) : null;
};

const averageAvailable = (values: Array<number | null | undefined>) => {
  const available = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  return available.length ? available.reduce((total, value) => total + value, 0) / available.length : null;
};

function formatBreakdown(contents: AnalyticsContent[]): FormatPerformance[] {
  const formats = [...new Set(contents.map((content) => content.format))];
  return formats.map((format) => {
    const rows = contents.filter((content) => content.format === format);
    return {
      format,
      publications: rows.length,
      averageReach: averageAvailable(rows.map((row) => row.reach)),
      averageEngagement: averageAvailable(rows.map((row) => row.engagementRate)),
      averageImpressions: averageAvailable(rows.map((row) => row.impressions)),
      averageViews: averageAvailable(rows.map((row) => row.views)),
      totalShares: sumAvailable(rows.map((row) => row.shares)),
      efficiency: averageAvailable(rows.map((row) => {
        const interactions = sumAvailable([row.likes, row.comments, row.shares, row.saves, row.replies, row.clicks]);
        return row.impressions && interactions !== null ? interactions / row.impressions * 100 : null;
      })),
    };
  });
}

export function buildConnectedDataset(accounts: ConnectedAccount[], _posts: Post[]): AnalyticsDataset | null {
  const active = accounts.filter(isConnected);
  if (!active.length) return null;

  const networks = active.map<NetworkAnalytics>((account) => {
    const providerContents = (account.analytics?.contents || []).map<AnalyticsContent>((content) => {
      const interactions = sumAvailable([content.likes, content.comments, content.shares, content.saves, content.replies, content.clicks]);
      return {
        id: content.id,
        title: content.title,
        date: content.date,
        network: account.platform,
        format: content.format,
        thumbnail: content.thumbnail,
        caption: content.caption,
        campaignId: content.campaignId,
        status: content.status,
        paid: content.paid,
        reach: content.reach ?? null,
        impressions: content.impressions ?? null,
        likes: content.likes ?? null,
        comments: content.comments ?? null,
        shares: content.shares ?? null,
        saves: content.saves ?? null,
        replies: content.replies ?? null,
        clicks: content.clicks ?? null,
        views: content.views ?? null,
        conversions: content.conversions ?? null,
        spend: content.spend ?? null,
        revenue: content.revenue ?? null,
        engagementRate: content.reach && interactions !== null ? interactions / content.reach * 100 : null,
        origin: 'analytics',
      };
    });
    // Calendar drafts and local status flags are not evidence of external metrics.
    // Only provider-sourced observations participate in connected Analytics.
    const contents = providerContents;
    const publishedContents = contents.filter((content) => content.status === 'published');

    return {
      accountId: account.id,
      accountLabel: account.name || account.handle || networkMeta[account.platform].label,
      network: account.platform,
      source: 'connected',
      connected: true,
      lastSync: account.lastSync,
      bestTime: account.bestTime,
      points: account.analytics?.points.length ? account.analytics.points.map((point) => ({
        date: point.date,
        followers: point.followers ?? null,
        gained: point.gained ?? null,
        lost: point.lost ?? null,
        reach: point.reach ?? null,
        impressions: point.impressions ?? null,
        engagements: point.engagements ?? null,
        likes: point.likes ?? null,
        comments: point.comments ?? null,
        shares: point.shares ?? null,
        saves: point.saves ?? null,
        replies: point.replies ?? null,
        clicks: point.clicks ?? null,
        views: point.views ?? null,
        conversions: point.conversions ?? null,
        spend: point.spend ?? null,
        revenue: point.revenue ?? null,
        retention: point.retention ?? null,
        posts: point.posts ?? 0,
      })) : [],
      contents,
      formats: formatBreakdown(publishedContents),
    };
  });

  return { source: 'connected', networks };
}

export function aggregatePoints(points: AnalyticsPoint[]) {
  const last = points.at(-1);
  const sum = (metric: Exclude<AnalyticsMetric, 'followers'>) => sumAvailable(points.map((point) => point[metric]));
  const reach = sum('reach');
  const engagements = sum('engagements');
  return {
    followers: last?.followers ?? null,
    gained: sumAvailable(points.map((point) => point.gained)),
    lost: sumAvailable(points.map((point) => point.lost)),
    netGrowth: sumAvailable(points.map((point) => point.gained !== null && point.lost !== null ? point.gained - point.lost : null)),
    reach,
    impressions: sum('impressions'),
    engagements,
    engagementRate: reach !== null && engagements !== null && reach > 0 ? (engagements / reach) * 100 : null,
    likes: sum('likes'),
    comments: sum('comments'),
    shares: sum('shares'),
    saves: sum('saves'),
    replies: sumAvailable(points.map((point) => point.replies)),
    clicks: sum('clicks'),
    views: sum('views'),
    conversions: sumAvailable(points.map((point) => point.conversions)),
    spend: sumAvailable(points.map((point) => point.spend)),
    revenue: sumAvailable(points.map((point) => point.revenue)),
    retention: averageAvailable(points.map((point) => point.retention)),
    ctr: (() => {
      const impressions = sum('impressions');
      const clicks = sum('clicks');
      return impressions !== null && clicks !== null && impressions > 0 ? clicks / impressions * 100 : null;
    })(),
    posts: points.reduce((total, point) => total + point.posts, 0),
  };
}

export function percentChange(current: number | null, previous: number | null) {
  if (current === null || previous === null || previous === 0) return null;
  return ((current - previous) / Math.abs(previous)) * 100;
}

export function formatNumber(value: number | null, compact = true) {
  if (value === null || !Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('pt-BR', compact ? { notation: 'compact', maximumFractionDigits: 1 } : { maximumFractionDigits: 0 }).format(value);
}

export function formatPercent(value: number | null) {
  if (value === null || !Number.isFinite(value)) return '—';
  return `${value.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}
