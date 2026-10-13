import { createHash } from 'node:crypto';
import { collectPinterestKeywords } from './radar/pinterest';
import { radarHistoryStore, type RadarHistoryPoint } from './radar/history';
type RadarRegion = 'BR' | 'GLOBAL';

export type RadarEvidence = {
  id: string;
  source: 'google-trends' | 'google-news' | 'youtube' | 'pinterest';
  sourceLabel: string;
  title: string;
  url: string;
  observedAt: string;
  publishedAt?: string;
  signalType: 'search-growth' | 'news-coverage' | 'video-popularity' | 'keyword-growth';
  metricLabel?: string;
  metricValue?: number;
  official: boolean;
  growthPercent?: number;
};

export type RadarTrend = {
  id: string;
  title: string;
  description: string;
  category: 'news' | 'research' | 'social' | 'technology' | 'marketing' | 'business' | 'entertainment' | 'sports' | 'culture' | 'education' | 'segment';
  region: RadarRegion;
  status: 'exploding' | 'hot' | 'emerging' | 'opportunity' | 'cooling' | 'saturated' | 'ended';
  timing: 'good' | 'watch' | 'late';
  direction: 'growing' | 'stable' | 'falling';
  trendScore: number;
  brandRelevance: number;
  confidence: 'high' | 'moderate' | 'low';
  startedAt: string;
  updatedAt: string;
  relatedTerms: string[];
  keyword: string;
  hashtags: string[];
  platforms: string[];
  language?: string;
  growthPercent?: number;
  history: Array<{ score: number; observedAt: string }>;
  evidence: RadarEvidence[];
  dataExplanation: string;
  inference: string;
  opportunity?: string;
  format: string;
  formatId: 'post' | 'story' | 'carousel' | 'reels' | 'youtube-short';
  angle: string;
  scoreBasis: {
    recency: number;
    sourceDiversity: number;
    searchSignal: number;
    supportingCoverage: number;
  };
};

export type RadarSourceStatus = {
  id: RadarEvidence['source'] | 'instagram' | 'tiktok' | 'threads' | 'x' | 'facebook' | 'linkedin';
  label: string;
  available: boolean;
  lastCheckedAt: string;
  detail: string;
};

export type RadarSnapshot = {
  trends: RadarTrend[];
  sourceStatus: RadarSourceStatus[];
  region: RadarRegion;
  updatedAt: string;
  cached: boolean;
  expiresAt: string;
  historyAvailable: boolean;
  message?: string;
};

type RadarInput = {
  isolationKey?: string;
  workspaceId?: string;
  region?: RadarRegion;
  forceRefresh?: boolean;
  contextProfile?: Record<string, unknown>;
  clientContext?: Record<string, unknown>;
  strategyContext?: Record<string, unknown>;
  operationSummary?: Record<string, unknown>;
};

type RawTrend = {
  title: string;
  primarySource: RadarEvidence['source'];
  trafficLabel?: string;
  trafficValue?: number;
  growthPercent?: number;
  publishedAt: string;
  evidence: RadarEvidence[];
};

const CACHE_TTL_MS = 10 * 60 * 1000;
const radarCache = new Map<string, { expiresAt: number; snapshot: RadarSnapshot }>();
const radarHistory = new Map<string, RadarHistoryPoint[]>();
const inFlight = new Map<string, Promise<RadarSnapshot>>();
const feedCache = new Map<string, { expiresAt: number; body: string }>();
const feedErrorCache = new Map<string, { expiresAt: number; code: string }>();
const feedInFlight = new Map<string, Promise<string>>();

const stopWords = new Set([
  'para', 'como', 'com', 'sem', 'uma', 'uns', 'das', 'dos', 'que', 'por', 'mais', 'sobre', 'esta', 'esse', 'essa',
  'the', 'and', 'from', 'with', 'your', 'into', 'this', 'that', 'noticia', 'noticias', 'conteudo', 'empresa', 'marca',
]);

const decodeXml = (value = '') => value
  .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
  .replace(/&quot;/g, '"')
  .replace(/&apos;/g, "'")
  .replace(/&amp;/g, '&')
  .replace(/&lt;/g, '<')
  .replace(/&gt;/g, '>')
  .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
  .replace(/<[^>]+>/g, '')
  .trim();

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const readTag = (block: string, tagName: string) => {
  const tag = escapeRegExp(tagName);
  const match = block.match(new RegExp(`<${tag}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${tag}>`, 'i'));
  return decodeXml(match?.[1] || '');
};

const slugify = (value: string) => value
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/^-|-$/g, '')
  .slice(0, 72);

const tokens = (value: string) => [...new Set(value
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .split(/[^a-z0-9]+/)
  .filter((token) => token.length >= 4 && !stopWords.has(token)))];

const parseTraffic = (label?: string) => {
  if (!label) return undefined;
  const normalized = label.replace(/\s/g, '').replace(',', '.').toUpperCase();
  const number = Number.parseFloat(normalized.replace(/[^0-9.]/g, ''));
  if (!Number.isFinite(number)) return undefined;
  if (normalized.includes('M')) return Math.round(number * 1_000_000);
  if (normalized.includes('K') || normalized.includes('MIL')) return Math.round(number * 1_000);
  return Math.round(number);
};

const formatGrowth = (value: number) => value > 10000 ? 'mais de 10.000%' : value < -10000 ? 'menos de -10.000%' : `${value}%`;

const safeDate = (value?: string) => {
  const parsed = value ? new Date(value) : new Date();
  return Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();
};

const fetchText = async (url: string, timeoutMs = 9000, forceRefresh = false) => {
  const key = createHash('sha256').update(url).digest('hex');
  const cached = feedCache.get(key);
  if (cached && cached.expiresAt > Date.now() && (!forceRefresh || cached.expiresAt - CACHE_TTL_MS > Date.now() - 30_000)) return cached.body;
  const failed = feedErrorCache.get(key);
  if (failed && failed.expiresAt > Date.now() && (!forceRefresh || failed.expiresAt - 60_000 > Date.now() - 30_000)) throw new Error(failed.code);
  const existing = feedInFlight.get(key);
  if (existing) return existing;
  const work = (async () => {
    const deadline = Date.now() + timeoutMs;
    for (let attempt = 1; attempt <= 3; attempt++) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), Math.max(500, deadline - Date.now()));
      try {
        const response = await fetch(url, { signal: controller.signal, headers: { 'User-Agent': 'ClickoStudio-Radar/1.0 (+https://vexelbr.com/)' } });
        if (response.ok) {
          const body = await response.text();
          if (feedCache.size > 80) feedCache.delete(feedCache.keys().next().value!);
          feedCache.set(key, { expiresAt: Date.now() + CACHE_TTL_MS, body });
          feedErrorCache.delete(key);
          return body;
        }
        if (![429, 503].includes(response.status) || attempt === 3 || Date.now() + 700 >= deadline) throw new Error(`HTTP ${response.status}`);
        const delay = Math.min(500, 125 * 2 ** (attempt - 1) + Math.random() * 100);
        await new Promise(resolve => setTimeout(resolve, delay));
      } finally { clearTimeout(timeout); }
    }
    throw new Error('RADAR_SOURCE_UNAVAILABLE');
  })().catch((error: unknown) => {
    const code = error instanceof Error && /^HTTP \d{3}$/.test(error.message) ? error.message : 'RADAR_SOURCE_UNAVAILABLE';
    if (feedErrorCache.size > 80) feedErrorCache.delete(feedErrorCache.keys().next().value!);
    feedErrorCache.set(key, { expiresAt: Date.now() + 60_000, code });
    throw new Error(code);
  }).finally(() => feedInFlight.delete(key));
  feedInFlight.set(key, work);
  return work;
};

const fetchJson = async (url: string, timeoutMs = 9000, forceRefresh = false) => {
  const text = await fetchText(url, timeoutMs, forceRefresh);
  return JSON.parse(text);
};

const parseGoogleTrends = (xml: string, region: RadarRegion, observedAt: string): RawTrend[] => {
  const geo = region === 'BR' ? 'BR' : 'US';
  return [...xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)].flatMap((match, index) => {
    const block = match[1];
    const title = readTag(block, 'title');
    if (!title) return [];
    const trafficLabel = readTag(block, 'ht:approx_traffic') || undefined;
    const publishedAt = safeDate(readTag(block, 'pubDate'));
    const evidence: RadarEvidence[] = [{
      id: `trends-${slugify(title)}`,
      source: 'google-trends',
      sourceLabel: region === 'BR' ? 'Google Trends · Brasil' : 'Google Trends · referência global em inglês',
      title: `Pesquisa em crescimento: ${title}`,
      url: `https://trends.google.com/trending?geo=${geo}`,
      observedAt,
      publishedAt,
      signalType: 'search-growth',
      metricLabel: trafficLabel ? `Volume aproximado informado pela fonte: ${trafficLabel}` : undefined,
      metricValue: parseTraffic(trafficLabel),
      official: true,
    }];

    [...block.matchAll(/<ht:news_item>([\s\S]*?)<\/ht:news_item>/gi)].slice(0, 5).forEach((newsMatch, newsIndex) => {
      const newsBlock = newsMatch[1];
      const newsTitle = readTag(newsBlock, 'ht:news_item_title');
      const newsUrl = readTag(newsBlock, 'ht:news_item_url');
      const newsSource = readTag(newsBlock, 'ht:news_item_source');
      if (!newsTitle || !newsUrl) return;
      evidence.push({
        id: `trends-news-${index}-${newsIndex}`,
        source: 'google-news',
        sourceLabel: newsSource || 'Veículo relacionado',
        title: newsTitle,
        url: newsUrl,
        observedAt,
        publishedAt,
        signalType: 'news-coverage',
        official: false,
      });
    });

    return [{ title, primarySource: 'google-trends' as const, trafficLabel, trafficValue: parseTraffic(trafficLabel), publishedAt, evidence }];
  });
};

const parseGoogleNews = (xml: string, observedAt: string): RadarEvidence[] => [...xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)]
  .slice(0, 40)
  .flatMap((match, index) => {
    const block = match[1];
    const title = readTag(block, 'title');
    const url = readTag(block, 'link');
    const source = readTag(block, 'source');
    if (!title || !url) return [];
    return [{
      id: `news-${index}-${slugify(title).slice(0, 32)}`,
      source: 'google-news' as const,
      sourceLabel: source || 'Google Notícias',
      title,
      url,
      observedAt,
      publishedAt: safeDate(readTag(block, 'pubDate')),
      signalType: 'news-coverage' as const,
      official: false,
    }];
  });

const overlapRatio = (left: string, right: string) => {
  const leftTokens = tokens(left);
  const rightTokens = new Set(tokens(right));
  if (!leftTokens.length || !rightTokens.size) return 0;
  // A one-token match can be a generic word inside a different subject
  // (e.g. “série c” versus an article about “série a”). Require the full
  // normalized phrase in that case, rather than claiming corroboration.
  if (leftTokens.length < 2 || rightTokens.size < 2) {
    const normalize = (value: string) => ` ${value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()} `;
    const leftPhrase = normalize(left);
    const rightPhrase = normalize(right);
    return leftPhrase.length <= rightPhrase.length ? Number(rightPhrase.includes(leftPhrase)) : Number(leftPhrase.includes(rightPhrase));
  }
  return leftTokens.filter((token) => rightTokens.has(token)).length / Math.min(leftTokens.length, rightTokens.size);
};

const consolidateRelatedTrends = (items: RawTrend[]) => {
  const consolidated: RawTrend[] = [];
  const ordered = [...items].sort((left, right) => (right.trafficValue || 0) - (left.trafficValue || 0));

  for (const item of ordered) {
    const existing = consolidated.find((candidate) => overlapRatio(candidate.title, item.title) >= 0.72);
    if (!existing) {
      consolidated.push({ ...item, evidence: [...item.evidence] });
      continue;
    }

    const existingTraffic = existing.trafficValue || 0;
    const itemTraffic = item.trafficValue || 0;
    const itemIsMoreSpecific = tokens(item.title).length > tokens(existing.title).length;
    const signalIsComparable = !existingTraffic || itemTraffic >= existingTraffic * 0.45;
    if (itemIsMoreSpecific && signalIsComparable) existing.title = item.title;

    if (itemTraffic > existingTraffic) {
      existing.trafficValue = itemTraffic;
      existing.trafficLabel = item.trafficLabel;
    }
    if (existing.primarySource !== 'google-trends' && item.primarySource === 'google-trends') existing.primarySource = 'google-trends';
    if (item.growthPercent !== undefined && (existing.growthPercent === undefined || item.growthPercent > existing.growthPercent)) existing.growthPercent = item.growthPercent;
    if (new Date(item.publishedAt).getTime() > new Date(existing.publishedAt).getTime()) existing.publishedAt = item.publishedAt;

    const evidenceKeys = new Set(existing.evidence.map((evidence) => `${evidence.source}:${evidence.url}:${evidence.title}`));
    for (const evidence of item.evidence) {
      const key = `${evidence.source}:${evidence.url}:${evidence.title}`;
      if (!evidenceKeys.has(key)) {
        existing.evidence.push(evidence);
        evidenceKeys.add(key);
      }
    }
  }

  return consolidated;
};

const contextText = (input: RadarInput) => JSON.stringify({
  contextProfile: input.contextProfile,
  clientContext: input.clientContext,
  strategyContext: input.strategyContext,
  contentHistory: (input.operationSummary as any)?.contentHistory?.slice?.(0, 40),
}).replace(/[{}\[\]"_:,]/g, ' ');

const classifyCategory = (text: string): RadarTrend['category'] => {
  const value = text.toLowerCase();
  if (/futebol|campeonato|partida|jogo|atleta|esporte|copa|tenis|vôlei|volei/.test(value)) return 'sports';
  if (/inteligência artificial|inteligencia artificial|tecnolog|software|aplicativo|digital|internet|startup/.test(value)) return 'technology';
  if (/marketing|publicidade|campanha|conteúdo|conteudo|social media/.test(value)) return 'marketing';
  if (/economia|empresa|negócio|negocio|mercado|finan|empreendedor/.test(value)) return 'business';
  if (/filme|série|serie|música|musica|artista|show|celebridade|televis/.test(value)) return 'entertainment';
  if (/escola|educação|educacao|universidade|curso|enem/.test(value)) return 'education';
  if (/cultura|livro|arte|festival/.test(value)) return 'culture';
  return 'research';
};

const recommendedFormat = (category: RadarTrend['category']) => {
  if (category === 'sports' || category === 'entertainment' || category === 'social') return { label: 'Reel', id: 'reels' as const, angle: 'Contexto rápido + posicionamento próprio' };
  if (category === 'technology' || category === 'business' || category === 'education') return { label: 'Carrossel', id: 'carousel' as const, angle: 'Explicação + impacto prático' };
  if (category === 'news') return { label: 'Post', id: 'post' as const, angle: 'Notícia + leitura da marca' };
  return { label: 'Post', id: 'post' as const, angle: 'Contexto + aplicação para o público' };
};

const scoreTrend = (raw: RawTrend, context: string, now: number) => {
  const ageHours = Math.max(0, (now - new Date(raw.publishedAt).getTime()) / 3_600_000);
  const recency = ageHours <= 4 ? 25 : ageHours <= 12 ? 21 : ageHours <= 24 ? 16 : ageHours <= 48 ? 8 : 2;
  const publisherCount = new Set(raw.evidence.map((item) => item.sourceLabel.toLowerCase())).size;
  const sourceKinds = new Set(raw.evidence.map((item) => item.source)).size;
  const sourceDiversity = Math.min(25, sourceKinds * 8 + Math.max(0, publisherCount - sourceKinds) * 3);
  const traffic = raw.trafficValue || 0;
  const searchSignal = traffic > 0 ? Math.min(30, Math.max(8, Math.round(Math.log10(Math.max(traffic, 10)) * 8)))
    : raw.growthPercent !== undefined ? Math.min(30, Math.max(0, Math.round(Math.log10(Math.max(1, 1 + raw.growthPercent)) * 9))) : 0;
  const supportingCoverage = Math.min(20, raw.evidence.filter((item) => item.signalType !== 'search-growth').length * 4);
  const trendScore = Math.max(0, Math.min(100, recency + sourceDiversity + searchSignal + supportingCoverage));
  // Aderência à marca considera o assunto principal, não palavras incidentais das matérias de apoio.
  // Isso evita classificar um tema como relevante apenas porque uma notícia usa termos genéricos do contexto.
  const trendTokens = tokens(raw.title);
  const contextTokens = new Set(tokens(context));
  const matchingContext = trendTokens.filter((token) => contextTokens.has(token)).length;
  const brandRelevance = Math.max(5, Math.min(100, 18 + matchingContext * 16));
  return { trendScore, brandRelevance, ageHours, sourceKinds, publisherCount, basis: { recency, sourceDiversity, searchSignal, supportingCoverage } };
};

const fetchYouTube = async (region: RadarRegion, forceRefresh = false) => {
  const apiKey = process.env.YOUTUBE_API_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey) return null;
  const regionCode = region === 'BR' ? 'BR' : 'US';
  const endpoint = new URL('https://www.googleapis.com/youtube/v3/videos');
  endpoint.search = new URLSearchParams({ part: 'snippet,statistics', chart: 'mostPopular', regionCode, maxResults: '25', key: apiKey }).toString();
  return fetchJson(endpoint.toString(), 9000, forceRefresh);
};

const enrichWithYouTube = (trends: RawTrend[], observedAt: string, data: Awaited<ReturnType<typeof fetchYouTube>>) => {
  if (!data) return { available: false, detail: 'API oficial do YouTube não configurada; nenhum sinal do YouTube foi usado.' };
  for (const video of Array.isArray(data.items) ? data.items : []) {
    const videoTitle = String(video?.snippet?.title || '');
    const matching = trends.find((trend) => overlapRatio(trend.title, videoTitle) >= 0.5);
    if (!matching) continue;
    const videoId = String(video?.id || '');
    matching.evidence.push({
      id: `youtube-${videoId}`,
      source: 'youtube',
      sourceLabel: 'YouTube · Mais populares',
      title: videoTitle,
      url: `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`,
      observedAt,
      publishedAt: safeDate(video?.snippet?.publishedAt),
      signalType: 'video-popularity',
      metricLabel: 'Presente no ranking oficial de vídeos mais populares da região.',
      official: true,
    });
  }
  return { available: true, detail: 'Ranking oficial de vídeos mais populares consultado com sucesso.' };
};

const buildTrend = (raw: RawTrend, input: RadarInput, region: RadarRegion, observedAt: string): RadarTrend => {
  const context = contextText(input);
  const scored = scoreTrend(raw, context, new Date(observedAt).getTime());
  const id = `${region.toLowerCase()}-${slugify(raw.title)}`;
  const historyKey = `${input.isolationKey || input.workspaceId || 'anonymous'}:${id}`;
  const previous = radarHistory.get(historyKey)?.at(-1);
  const currentValue = raw.trafficValue ?? raw.growthPercent;
  const metricKind: RadarHistoryPoint['metricKind'] = raw.trafficValue !== undefined ? 'traffic' : raw.growthPercent !== undefined ? 'growth' : undefined;
  const direction: RadarTrend['direction'] = metricKind === 'growth' && raw.growthPercent !== undefined
    ? raw.growthPercent > 0 ? 'growing' : raw.growthPercent < 0 ? 'falling' : 'stable'
    : previous?.metricKind === 'traffic' && metricKind === 'traffic' && currentValue !== undefined && previous.observedValue !== undefined
      ? currentValue > previous.observedValue * 1.1 ? 'growing' : currentValue < previous.observedValue * 0.9 ? 'falling' : 'stable'
      : 'stable';
  let status: RadarTrend['status'] = scored.trendScore >= 69 ? 'hot' : scored.trendScore >= 52 ? 'emerging' : 'opportunity';
  if (direction === 'growing' && (raw.growthPercent ?? 0) >= 200 && scored.trendScore >= 84) status = 'exploding';
  else if (direction === 'growing' && status === 'opportunity') status = 'emerging';
  if (direction === 'falling') status = scored.ageHours > 24 ? 'saturated' : 'cooling';
  const timing: RadarTrend['timing'] = ['exploding', 'hot', 'emerging'].includes(status) ? 'good' : ['cooling', 'saturated', 'ended'].includes(status) ? 'late' : 'watch';
  const confidence: RadarTrend['confidence'] = scored.sourceKinds >= 3 || scored.publisherCount >= 4 ? 'high' : scored.sourceKinds >= 2 || scored.publisherCount >= 2 ? 'moderate' : 'low';
  const category = classifyCategory(`${raw.title} ${raw.evidence.map((item) => item.title).join(' ')}`);
  const format = recommendedFormat(category);
  const relatedTerms = tokens(raw.evidence.map((item) => item.title).join(' ')).filter((term) => !tokens(raw.title).includes(term)).slice(0, 8);
  const dataExplanation = raw.primarySource === 'pinterest'
    ? `Dado: palavra-chave no ranking oficial de crescimento do Pinterest em ${region === 'BR' ? 'Brasil' : 'EUA'}${raw.growthPercent !== undefined ? `, variação semanal informada de ${formatGrowth(raw.growthPercent)}` : ''}. Outras fontes só são atribuídas quando há correspondência observada.`
    : `Dado: o assunto aparece no Google Trends com atualização de ${new Date(raw.publishedAt).toLocaleString('pt-BR')}${raw.trafficLabel ? ` e volume aproximado informado de ${raw.trafficLabel}` : ''}. ${raw.evidence.length - 1} evidência(s) pública(s) adicional(is) foram vinculadas.`;
  const inference = scored.brandRelevance >= 50
    ? `Inferência da KLIC: há correspondência entre o assunto e elementos do contexto ativo da marca. A aderência deve ser validada antes da publicação.`
    : `Inferência da KLIC: a força do sinal não implica aderência à marca; a correspondência com o contexto ativo é baixa.`;
  const opportunity = scored.brandRelevance >= 35
    ? `Interpretar “${raw.title}” a partir da experiência da marca, explicando o impacto prático para o público sem reproduzir a cobertura existente.`
    : undefined;
  const history = [...(radarHistory.get(historyKey) || []), { scope: input.isolationKey || input.workspaceId || 'anonymous', region, trendId: id, score: scored.trendScore, observedAt, observedValue: currentValue, metricKind }].slice(-48);
  radarHistory.set(historyKey, history);
  return {
    id,
    title: raw.title,
    description: raw.evidence.find((item) => item.signalType === 'news-coverage')?.title || `Sinal observado em ${raw.primarySource === 'pinterest' ? 'pesquisas do Pinterest' : 'pesquisas do Google'} na região ${region === 'BR' ? 'Brasil' : 'EUA como referência global'}.`,
    category,
    region,
    status,
    timing,
    direction,
    trendScore: scored.trendScore,
    brandRelevance: scored.brandRelevance,
    confidence,
    startedAt: raw.publishedAt,
    updatedAt: observedAt,
    relatedTerms,
    keyword: raw.title,
    hashtags: [...new Set(raw.evidence.flatMap((item) => item.title.match(/#[\p{L}\p{N}_]+/gu) || []))].slice(0, 8),
    platforms: [...new Set(raw.evidence.filter((item) => item.source !== 'google-news').map((item) => item.source === 'google-trends' ? 'Google Trends' : item.source === 'youtube' ? 'YouTube' : 'Pinterest'))],
    language: region === 'BR' ? 'pt-BR' : 'en-US',
    growthPercent: raw.growthPercent,
    history: history.map(({ score, observedAt: sampleAt }) => ({ score, observedAt: sampleAt })),
    evidence: raw.evidence,
    dataExplanation,
    inference,
    opportunity,
    format: format.label,
    formatId: format.id,
    angle: format.angle,
    scoreBasis: scored.basis,
  };
};

async function collectRadar(input: RadarInput, region: RadarRegion, cacheKey: string): Promise<RadarSnapshot> {
  const observedAt = new Date().toISOString();
  const sourceStatus: RadarSourceStatus[] = [];
  const geo = region === 'BR' ? 'BR' : 'US';
  const historyScope = input.isolationKey || input.workspaceId || 'anonymous';
  let historyAvailable = true;
  try {
    const points = await radarHistoryStore().list(historyScope, region);
    const byTrend = new Map<string, RadarHistoryPoint[]>();
    for (const point of points) byTrend.set(point.trendId, [...(byTrend.get(point.trendId) || []), point]);
    for (const [id, entries] of byTrend) radarHistory.set(`${historyScope}:${id}`, entries.sort((left, right) => left.observedAt.localeCompare(right.observedAt)).slice(-48));
  } catch {
    historyAvailable = false;
  }
  let rawTrends: RawTrend[] = [];
  // Start independent provider requests together. Parsing and cross-source matching
  // still happen in order below, but a slow feed no longer serializes the others.
  const query = region === 'BR' ? 'marketing OR tecnologia OR negócios' : 'marketing OR technology OR business';
  const newsUrl = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=${region === 'BR' ? 'pt-BR' : 'en-US'}&gl=${geo}&ceid=${geo}:${region === 'BR' ? 'pt-419' : 'en'}`;
  const trendsRequest = fetchText(`https://trends.google.com/trending/rss?geo=${geo}`, 9000, input.forceRefresh);
  const newsRequest = fetchText(newsUrl, 9000, input.forceRefresh);
  const youtubeRequest = fetchYouTube(region, input.forceRefresh);
  const pinterestRequest = collectPinterestKeywords(region, fetch, input.forceRefresh === true);
  // All rejections are observed immediately, including when an earlier source fails.
  void newsRequest.catch(() => undefined);
  void youtubeRequest.catch(() => undefined);
  void pinterestRequest.catch(() => undefined);

  try {
    const trendsXml = await trendsRequest;
    rawTrends = consolidateRelatedTrends(parseGoogleTrends(trendsXml, region, observedAt));
    sourceStatus.push({ id: 'google-trends', label: 'Google Trends', available: true, lastCheckedAt: observedAt, detail: `${rawTrends.length} consultas atuais recebidas do feed público${region === 'GLOBAL' ? ' em inglês, usando os EUA como referência regional' : ' do Brasil'}.` });
  } catch (error) {
    sourceStatus.push({ id: 'google-trends', label: 'Google Trends', available: false, lastCheckedAt: observedAt, detail: `Fonte temporariamente indisponível: ${error instanceof Error ? error.message : 'falha desconhecida'}.` });
  }

  try {
    // Public news discovery does not send private brand/client terms to a third party.
    const newsXml = await newsRequest;
    const newsEvidence = parseGoogleNews(newsXml, observedAt);
    let matches = 0;
    for (const evidence of newsEvidence) {
      const matching = rawTrends
        .map((trend) => ({ trend, overlap: overlapRatio(trend.title, evidence.title) }))
        .sort((a, b) => b.overlap - a.overlap)[0];
      if (matching && matching.overlap >= 0.5 && !matching.trend.evidence.some((item) => item.url === evidence.url)) {
        matching.trend.evidence.push(evidence);
        matches += 1;
      }
    }
    sourceStatus.push({ id: 'google-news', label: 'Google Notícias', available: true, lastCheckedAt: observedAt, detail: `${matches} cobertura(s) independente(s) cruzada(s) com tendências detectadas; notícias sem correspondência não foram classificadas como trend.` });
  } catch (error) {
    sourceStatus.push({ id: 'google-news', label: 'Google Notícias', available: false, lastCheckedAt: observedAt, detail: `Fonte temporariamente indisponível: ${error instanceof Error ? error.message : 'falha desconhecida'}.` });
  }

  try {
    const youtube = enrichWithYouTube(rawTrends, observedAt, await youtubeRequest);
    sourceStatus.push({ id: 'youtube', label: 'YouTube', available: youtube.available, lastCheckedAt: observedAt, detail: youtube.detail });
  } catch (error) {
    sourceStatus.push({ id: 'youtube', label: 'YouTube', available: false, lastCheckedAt: observedAt, detail: `API oficial indisponível: ${error instanceof Error ? error.message : 'falha desconhecida'}.` });
  }

  try {
    const keywords = await pinterestRequest;
    if (keywords === null) {
      sourceStatus.push({ id: 'pinterest', label: 'Pinterest', available: false, lastCheckedAt: observedAt, detail: 'API oficial de Trends sem acesso autorizado configurado no servidor.' });
    } else {
      for (const keyword of keywords) {
        const evidence: RadarEvidence = {
          id: `pinterest-${slugify(keyword.keyword)}`, source: 'pinterest', sourceLabel: 'Pinterest Trends',
          title: `Palavra-chave em crescimento: ${keyword.keyword}`,
          url: 'https://trends.pinterest.com/', observedAt, publishedAt: observedAt,
          signalType: 'keyword-growth', growthPercent: keyword.pct_growth_wow,
          metricLabel: keyword.pct_growth_wow === undefined ? 'Ranking oficial de crescimento' : `Crescimento semanal informado: ${formatGrowth(keyword.pct_growth_wow)}`,
          official: true,
        };
        const matching = rawTrends.find((item) => overlapRatio(item.title, keyword.keyword) >= 0.72);
        if (matching) {
          matching.evidence.push(evidence);
          if (keyword.pct_growth_wow !== undefined) matching.growthPercent = keyword.pct_growth_wow;
        }
        else rawTrends.push({ title: keyword.keyword, primarySource: 'pinterest', growthPercent: keyword.pct_growth_wow, publishedAt: observedAt, evidence: [evidence] });
      }
      sourceStatus.push({ id: 'pinterest', label: 'Pinterest', available: true, lastCheckedAt: observedAt, detail: `${keywords.length} palavra(s)-chave no ranking oficial de crescimento.` });
    }
  } catch (error) {
    sourceStatus.push({ id: 'pinterest', label: 'Pinterest', available: false, lastCheckedAt: observedAt, detail: `API oficial temporariamente indisponível (${error instanceof Error && /^PINTEREST_HTTP_\d+$/.test(error.message) ? error.message : 'falha de consulta'}).` });
  }

  sourceStatus.push(
    { id: 'tiktok', label: 'TikTok', available: false, lastCheckedAt: observedAt, detail: 'Nenhuma API oficial de tendências foi configurada; o Radar não atribui sinais ao TikTok.' },
    { id: 'instagram', label: 'Instagram', available: false, lastCheckedAt: observedAt, detail: 'Nenhuma fonte pública oficial de tendências foi configurada; métricas privadas não são presumidas.' },
    { id: 'threads', label: 'Threads', available: false, lastCheckedAt: observedAt, detail: 'Busca e insights exigem permissões específicas; nenhum ranking global foi autorizado.' },
    { id: 'x', label: 'X', available: false, lastCheckedAt: observedAt, detail: 'Busca e volume dependem do plano de API; nenhum sinal foi coletado.' },
    { id: 'facebook', label: 'Facebook', available: false, lastCheckedAt: observedAt, detail: 'Dados de páginas próprias não representam tendências globais; fonte não habilitada.' },
    { id: 'linkedin', label: 'LinkedIn', available: false, lastCheckedAt: observedAt, detail: 'Análises de páginas exigem produto aprovado; ranking global não disponível nesta integração.' },
  );

  const trends = rawTrends
    .map((trend) => buildTrend(trend, input, region, observedAt))
    .sort((a, b) => (b.trendScore * 0.62 + b.brandRelevance * 0.38) - (a.trendScore * 0.62 + a.brandRelevance * 0.38))
    .slice(0, 18);
  if (historyAvailable) {
    try {
      await radarHistoryStore().append(trends.map(trend => radarHistory.get(`${historyScope}:${trend.id}`)?.at(-1)).filter((point): point is RadarHistoryPoint => Boolean(point)));
    } catch { historyAvailable = false; }
  }
  const expiresAt = new Date(Date.now() + CACHE_TTL_MS).toISOString();
  const snapshot: RadarSnapshot = {
    trends,
    sourceStatus,
    region,
    updatedAt: observedAt,
    cached: false,
    expiresAt,
    historyAvailable,
    message: trends.length ? undefined : 'Não há evidências suficientes para classificar assuntos como tendência neste momento.',
  };
  radarCache.set(cacheKey, { expiresAt: Date.now() + CACHE_TTL_MS, snapshot });
  return snapshot;
}

export async function getRadarSnapshot(input: RadarInput): Promise<RadarSnapshot> {
  const region: RadarRegion = input.region === 'GLOBAL' ? 'GLOBAL' : 'BR';
  const fingerprint = createHash('sha256').update(JSON.stringify([input.isolationKey || '', input.contextProfile || {}, input.clientContext || {}, input.strategyContext || {}, input.operationSummary || {}])).digest('hex');
  const cacheKey = `${input.workspaceId || 'anonymous'}:${region}:${fingerprint}`;
  const cached = radarCache.get(cacheKey);
  if (!input.forceRefresh && cached && cached.expiresAt > Date.now()) {
    return { ...cached.snapshot, cached: true };
  }
  const existing = inFlight.get(cacheKey);
  if (existing) return existing;
  const request = collectRadar(input, region, cacheKey).finally(() => inFlight.delete(cacheKey));
  inFlight.set(cacheKey, request);
  return request;
}
