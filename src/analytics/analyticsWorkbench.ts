import { aggregatePoints, type AnalyticsMetric, type AnalyticsPoint, type NetworkAnalytics } from './analyticsModel';

const DAY = 86_400_000;

const sumNullable = (values: Array<number | null | undefined>) => {
  const valid = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) : null;
};

export function mergePointSlices(slices: AnalyticsPoint[][]): AnalyticsPoint[] {
  const dates = new Map<string, AnalyticsPoint[]>();
  slices.forEach(slice => {
    const days = new Map<string, AnalyticsPoint[]>();
    slice.forEach(point => {
      const date = new Date(point.date);
      if (!Number.isFinite(date.getTime())) return;
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
      days.set(key, [...(days.get(key) || []), point]);
    });
    days.forEach((points, key) => {
      const sorted = [...points].sort((a,b) => Date.parse(a.date) - Date.parse(b.date));
      const totals = aggregatePoints(sorted);
      dates.set(key, [...(dates.get(key) || []), { ...sorted.at(-1)!, ...totals }]);
    });
  });
  return [...dates.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, rows]) => {
    const metric = (key: keyof AnalyticsPoint) => sumNullable(rows.map((row) => typeof row[key] === 'number' ? row[key] as number : null));
    const retention = rows.flatMap(row => typeof row.retention === 'number' ? [row.retention] : []);
    return {
      date: `${date}T12:00:00`, followers: metric('followers'), gained: metric('gained'), lost: metric('lost'),
      reach: metric('reach'), impressions: metric('impressions'), engagements: metric('engagements'), likes: metric('likes'),
      comments: metric('comments'), shares: metric('shares'), saves: metric('saves'), replies: metric('replies'), clicks: metric('clicks'),
      views: metric('views'), conversions: metric('conversions'), spend: metric('spend'), revenue: metric('revenue'),
      retention: retention.length ? retention.reduce((a,b) => a+b,0)/retention.length : null, posts: metric('posts') || 0,
    };
  });
}

export function customPeriodPoints(networks: NetworkAnalytics[], start: string, end: string) {
  const from = new Date(`${start}T00:00:00`).getTime();
  const to = new Date(`${end}T23:59:59.999`).getTime();
  return mergePointSlices(networks.map((network) => network.points.filter((point) => {
    const time = new Date(point.date).getTime();
    return time >= from && time <= to;
  })));
}

export function previousCustomPeriodPoints(networks: NetworkAnalytics[], start: string, end: string) {
  const from = new Date(`${start}T00:00:00`).getTime();
  const to = new Date(`${end}T23:59:59.999`).getTime();
  const duration = Math.max(DAY, to - from + 1);
  const previousEnd = from - 1;
  const previousStart = previousEnd - duration + 1;
  return mergePointSlices(networks.map((network) => network.points.filter((point) => {
    const time = new Date(point.date).getTime();
    return time >= previousStart && time <= previousEnd;
  })));
}

export function groupPoints(points: AnalyticsPoint[], granularity: 'daily' | 'weekly' | 'monthly') {
  if (granularity === 'daily') return points;
  const buckets = new Map<string, AnalyticsPoint[]>();
  points.forEach(point => {
    const date = new Date(point.date);
    if (!Number.isFinite(date.getTime())) return;
    if (granularity === 'weekly') date.setDate(date.getDate() - (date.getDay() + 6) % 7);
    else date.setDate(1);
    const key = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
    buckets.set(key,[...(buckets.get(key) || []),point]);
  });
  const groups: AnalyticsPoint[] = [];
  for (const [, rows] of [...buckets.entries()].sort(([a],[b]) => a.localeCompare(b))) {
    const chunk = rows.sort((a,b) => Date.parse(a.date)-Date.parse(b.date));
    const totals = aggregatePoints(chunk);
    groups.push({
      date: chunk.at(-1)?.date || new Date().toISOString(), followers: totals.followers, gained: totals.gained, lost: totals.lost,
      reach: totals.reach, impressions: totals.impressions, engagements: totals.engagements, likes: totals.likes, comments: totals.comments,
      shares: totals.shares, saves: totals.saves, replies: totals.replies, clicks: totals.clicks, views: totals.views,
      conversions: totals.conversions, spend: totals.spend, revenue: totals.revenue, retention: totals.retention, posts: totals.posts,
    });
  }
  return groups;
}

export function metricValue(points: AnalyticsPoint[], metric: AnalyticsMetric | 'posts') {
  const values = points.flatMap((point) => typeof point[metric] === 'number' ? [point[metric] as number] : []);
  if (!values.length) return null;
  return metric === 'followers' ? values.at(-1)! : values.reduce((sum, value) => sum + value, 0);
}

export function rangeLabel(points: AnalyticsPoint[]) {
  if (!points.length) return 'Sem dados no intervalo';
  const formatter = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' });
  const first = formatter.format(new Date(points[0].date)).replace('.', '');
  const last = formatter.format(new Date(points.at(-1)!.date)).replace('.', '');
  return first === last ? first : `${first} — ${last}`;
}

export function availableMetrics(points: AnalyticsPoint[]): Array<AnalyticsMetric | 'posts'> {
  const metrics: Array<AnalyticsMetric | 'posts'> = ['followers', 'reach', 'impressions', 'engagements', 'likes', 'comments', 'shares', 'saves', 'clicks', 'views', 'posts'];
  return metrics.filter((metric) => points.some((point) => typeof point[metric] === 'number'));
}
