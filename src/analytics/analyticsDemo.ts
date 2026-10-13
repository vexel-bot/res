import type { PostFormat, SocialPlatform } from '../types';
import type { AnalyticsContent, AnalyticsDataset, AnalyticsPoint, FormatPerformance, NetworkAnalytics } from './analyticsModel';

type DemoNetwork = {
  network: SocialPlatform;
  accountLabel: string;
  followers: number;
  dailyReach: number;
  growth: number;
  formats: PostFormat[];
};

const DEMO_NETWORKS: DemoNetwork[] = [
  { network: 'instagram', accountLabel: '@clicko.studio', followers: 18460, dailyReach: 4350, growth: 19, formats: ['reels', 'carousel', 'story'] },
  { network: 'tiktok', accountLabel: '@clickostudios', followers: 12780, dailyReach: 5620, growth: 27, formats: ['tiktok'] },
  { network: 'youtube', accountLabel: 'Clicko Studios', followers: 8940, dailyReach: 3180, growth: 12, formats: ['youtube-short', 'youtube-long'] },
  { network: 'linkedin', accountLabel: 'Clicko Studios', followers: 6210, dailyReach: 1760, growth: 8, formats: ['post', 'linkedin-article'] },
];

const CONTENT_TITLES = [
  'Como simplificar a operação de conteúdo',
  'Bastidores de uma campanha integrada',
  'Três ideias para melhorar o alcance',
  'O novo comportamento do consumidor digital',
  'Checklist de planejamento editorial',
  'Estratégia de conteúdo em cinco passos',
  'Como transformar dados em decisões',
  'Uma semana produzindo com a KLIC',
];

function makePoints(seed: DemoNetwork, networkIndex: number, days = 120): AnalyticsPoint[] {
  const today = new Date();
  today.setMinutes(0, 0, 0);
  let followers = seed.followers - days * seed.growth;
  return Array.from({ length: days }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - (days - index - 1));
    date.setHours([9, 12, 18, 20][(index + networkIndex) % 4]);
    const wave = Math.sin((index + networkIndex * 3) / 6) * .16 + Math.cos(index / 15) * .09;
    const campaignLift = index % 19 === 7 ? .34 : index % 29 === 11 ? .22 : 0;
    const reach = Math.max(280, Math.round(seed.dailyReach * (.78 + wave + campaignLift + index / days * .16)));
    const impressions = Math.round(reach * (1.38 + networkIndex * .07));
    const likes = Math.round(reach * (.043 + networkIndex * .003));
    const comments = Math.round(reach * .0065);
    const shares = Math.round(reach * (.008 + (seed.network === 'tiktok' ? .006 : 0)));
    const saves = Math.round(reach * (seed.network === 'instagram' ? .014 : .005));
    const clicks = Math.round(reach * (.009 + networkIndex * .001));
    const gained = Math.max(2, Math.round(seed.growth + wave * 10));
    const lost = Math.max(1, Math.round(seed.growth * .31 + Math.cos(index / 8) * 2));
    followers += gained - lost;
    return {
      date: date.toISOString(), followers, gained, lost, reach, impressions,
      engagements: likes + comments + shares + saves + clicks,
      likes, comments, shares, saves, replies: Math.round(comments * .32), clicks,
      views: ['tiktok', 'youtube'].includes(seed.network) ? Math.round(reach * 1.14) : Math.round(reach * .31),
      conversions: Math.round(clicks * .08), spend: null, revenue: null,
      retention: ['tiktok', 'youtube'].includes(seed.network) ? 41 + Math.sin(index / 9) * 5 : null,
      posts: index % (networkIndex + 3) === 0 ? 1 : 0,
    };
  });
}

function makeContents(seed: DemoNetwork, networkIndex: number, points: AnalyticsPoint[]): AnalyticsContent[] {
  return Array.from({ length: 8 }, (_, index) => {
    const point = points[Math.max(0, points.length - 4 - index * 11)];
    const factor = 2.2 + ((index * 7 + networkIndex * 3) % 8) / 10;
    const reach = Math.round((point.reach || seed.dailyReach) * factor);
    const impressions = Math.round(reach * 1.47);
    const likes = Math.round(reach * .051);
    const comments = Math.round(reach * .007);
    const shares = Math.round(reach * (.011 + (index % 3) * .002));
    const saves = Math.round(reach * .013);
    const clicks = Math.round(reach * .01);
    return {
      id: `demo-${seed.network}-${index}`,
      title: CONTENT_TITLES[(index + networkIndex) % CONTENT_TITLES.length],
      date: point.date,
      network: seed.network,
      format: seed.formats[index % seed.formats.length],
      reach, impressions, likes, comments, shares, saves, replies: Math.round(comments * .28), clicks,
      views: ['tiktok', 'youtube'].includes(seed.network) ? Math.round(reach * 1.18) : Math.round(reach * .26),
      conversions: Math.round(clicks * .09), spend: null, revenue: null,
      engagementRate: (likes + comments + shares + saves + clicks) / reach * 100,
      caption: 'Conteúdo ilustrativo do modo de demonstração do Analytics.',
      status: 'published', origin: 'analytics', paid: false,
    };
  });
}

function makeFormats(contents: AnalyticsContent[]): FormatPerformance[] {
  return [...new Set(contents.map((content) => content.format))].map((format) => {
    const rows = contents.filter((content) => content.format === format);
    const average = (values: Array<number | null>) => {
      const available = values.filter((value): value is number => value !== null);
      return available.length ? available.reduce((sum, value) => sum + value, 0) / available.length : null;
    };
    return {
      format, publications: rows.length,
      averageReach: average(rows.map((row) => row.reach)),
      averageEngagement: average(rows.map((row) => row.engagementRate)),
      averageImpressions: average(rows.map((row) => row.impressions)),
      averageViews: average(rows.map((row) => row.views)),
      totalShares: rows.reduce((sum, row) => sum + (row.shares || 0), 0),
      efficiency: average(rows.map((row) => row.engagementRate)),
    };
  });
}

export function buildAnalyticsDemoDataset(): AnalyticsDataset {
  const networks = DEMO_NETWORKS.map<NetworkAnalytics>((seed, index) => {
    const points = makePoints(seed, index);
    const contents = makeContents(seed, index, points);
    return {
      accountId: `analytics-demo-${seed.network}`,
      accountLabel: seed.accountLabel,
      network: seed.network,
      source: 'demo',
      connected: true,
      lastSync: new Date().toISOString(),
      bestTime: ['Quarta, 19h', 'Sexta, 20h', 'Domingo, 18h', 'Terça, 09h'][index],
      points, contents, formats: makeFormats(contents),
    };
  });
  return { source: 'demo', networks };
}
