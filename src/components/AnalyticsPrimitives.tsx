import React from 'react';
import { formatNumber, formatPercent, percentChange, type AnalyticsMetric, type AnalyticsPoint } from '../analytics/analyticsModel';
import { ClickoLoader } from './ClickoLoader';

export const analyticsMetricLabels: Record<AnalyticsMetric, string> = {
  followers: 'Seguidores',
  reach: 'Alcance',
  impressions: 'Impressões',
  engagements: 'Engajamentos',
  likes: 'Curtidas',
  comments: 'Comentários',
  shares: 'Compartilhamentos',
  saves: 'Salvamentos',
  clicks: 'Cliques',
  views: 'Visualizações',
  posts: 'Conteúdos publicados',
};

export const analyticsFormatLabels: Record<string, string> = {
  post: 'Post', story: 'Stories', carousel: 'Carrossel', reels: 'Reels', tiktok: 'TikTok',
  'youtube-short': 'Shorts', 'youtube-long': 'Vídeo longo', 'linkedin-article': 'Artigo', pin: 'Pin',
  thread: 'Thread', newsletter: 'Newsletter', blog: 'Blog', vsl: 'VSL', ad: 'Anúncio',
  presentation: 'Apresentação', script: 'Roteiro',
};

export function AnalyticsTrendChart({ points, previous, metric, compare, loading = false, error = null, rangeLabel, comparisonRangeLabel, showInsight = true }: {
  points: AnalyticsPoint[];
  previous: AnalyticsPoint[];
  metric: AnalyticsMetric;
  compare: boolean;
  loading?: boolean;
  error?: string | null;
  rangeLabel?: string;
  comparisonRangeLabel?: string;
  showInsight?: boolean;
  key?: string;
}) {
  const width = 820;
  const height = 286;
  const pad = { top: 34, right: 24, bottom: 38, left: 58 };
  const [hoveredIndex, setHoveredIndex] = React.useState<number | null>(null);
  const [pinnedIndex, setPinnedIndex] = React.useState<number | null>(null);
  const [showPrevious, setShowPrevious] = React.useState(true);
  const gradientId = React.useId().replace(/:/g, '');
  const currentSeries = points.map((point, index) => ({ point, index, value: typeof point[metric] === 'number' ? point[metric] as number : null }));
  const previousSeries = previous.map((point, index) => ({ point, index, value: typeof point[metric] === 'number' ? point[metric] as number : null }));
  const currentValues = currentSeries.flatMap((item) => item.value === null ? [] : [item.value]);
  const allPreviousValues = previousSeries.flatMap((item) => item.value === null ? [] : [item.value]);
  const previousValues = compare && showPrevious ? allPreviousValues : [];
  const all = [...currentValues, ...previousValues];
  if (loading) return <div className="clicko-analytics-trend grid h-[356px] place-items-center overflow-hidden rounded-xl border"><ClickoLoader label="Atualizando dados do gráfico" message="Atualizando evolução temporal…" context="section" /></div>;
  if (error && !all.length) return <div className="clicko-analytics-trend grid h-[286px] place-items-center rounded-xl border px-6 text-center" role="alert"><div><strong className="text-[10px] font-medium text-white">Não foi possível atualizar este gráfico.</strong><p className="mt-2 text-[8px] leading-4 text-[#808080]">{error}</p></div></div>;
  if (!currentValues.length) return <div className="grid h-[286px] place-items-center px-6 text-center text-[11px] text-[#808080]">Dados não disponíveis para esta métrica no período selecionado.</div>;
  const rawMin = Math.min(...all);
  const rawMax = Math.max(...all);
  const breathingRoom = Math.max((rawMax - rawMin) * 0.12, Math.abs(rawMax) * 0.025, 1);
  const min = Math.max(0, rawMin - breathingRoom);
  const max = rawMax + breathingRoom;
  const range = Math.max(max - min, 1);
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const xAt = (index: number, length: number) => pad.left + (index / Math.max(1, length - 1)) * plotWidth;
  const yAt = (value: number) => pad.top + (1 - (value - min) / range) * plotHeight;
  const segments = (series: typeof currentSeries) => {
    const result: Array<Array<{ x: number; y: number; value: number; index: number }>> = [];
    let active: Array<{ x: number; y: number; value: number; index: number }> = [];
    series.forEach((item) => {
      if (item.value === null) { if (active.length) result.push(active); active = []; return; }
      active.push({ x: xAt(item.index, series.length), y: yAt(item.value), value: item.value, index: item.index });
    });
    if (active.length) result.push(active);
    return result;
  };
  const smoothPath = (rows: Array<{ x: number; y: number }>) => rows.length < 2 ? '' : rows.slice(1).reduce((path, point, index) => {
    const previousPoint = rows[index];
    const middle = (previousPoint.x + point.x) / 2;
    return `${path} C ${middle} ${previousPoint.y}, ${middle} ${point.y}, ${point.x} ${point.y}`;
  }, `M ${rows[0].x} ${rows[0].y}`);
  const currentSegments = segments(currentSeries);
  const previousSegments = segments(previousSeries);
  const selectedIndex = hoveredIndex ?? pinnedIndex;
  const activeIndex = selectedIndex === null ? null : Math.max(0, Math.min(currentSeries.length - 1, selectedIndex));
  const hovered = activeIndex === null ? null : currentSeries[activeIndex];
  const previousHovered = activeIndex === null || !previousSeries.length ? null : previousSeries[Math.min(previousSeries.length - 1, Math.round((activeIndex / Math.max(1, currentSeries.length - 1)) * Math.max(0, previousSeries.length - 1)))];
  const average = currentValues.reduce((sum, value) => sum + value, 0) / currentValues.length;
  const previousAverage = allPreviousValues.length ? allPreviousValues.reduce((sum, value) => sum + value, 0) / allPreviousValues.length : null;
  const averageChange = compare ? percentChange(average, previousAverage) : null;
  const currentIndicator = metric === 'followers' ? currentValues.at(-1) ?? null : currentValues.reduce((sum, value) => sum + value, 0);
  const previousIndicator = metric === 'followers' ? allPreviousValues.at(-1) ?? null : allPreviousValues.length ? allPreviousValues.reduce((sum, value) => sum + value, 0) : null;
  const indicatorDifference = currentIndicator !== null && previousIndicator !== null ? currentIndicator - previousIndicator : null;
  const indicatorChange = compare ? percentChange(currentIndicator, previousIndicator) : null;
  const hoveredDifference = hovered?.value !== null && hovered?.value !== undefined && previousHovered?.value !== null && previousHovered?.value !== undefined ? hovered.value - previousHovered.value : null;
  const hoveredChange = hovered?.value !== null && hovered?.value !== undefined ? percentChange(hovered.value, previousHovered?.value ?? null) : null;
  const peak = [...currentSeries].filter((item): item is typeof item & { value: number } => item.value !== null).sort((a, b) => b.value - a.value)[0];
  const peakDistance = peak ? percentChange(peak.value, average) : null;
  const trendState = averageChange === null || Math.abs(averageChange) < 0.5 ? 'Estável' : averageChange > 0 ? 'Crescimento' : 'Queda';
  const insight = currentValues.length >= 3 && averageChange !== null && peak
    ? `${analyticsMetricLabels[metric]} ${averageChange >= 0 ? 'cresceu' : 'recuou'} ${formatPercent(Math.abs(averageChange))} frente ao período anterior. O maior valor ocorreu em ${new Date(peak.point.date).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }).replace('.', '')}${peakDistance !== null ? ` e ficou ${formatPercent(Math.abs(peakDistance))} ${peakDistance >= 0 ? 'acima' : 'abaixo'} da média` : ''}.`
    : null;
  const dateLabel = (date?: string) => date ? new Date(date).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }).replace('.', '') : '—';
  const indexAt = (clientX: number, bounds: DOMRect) => {
    const fraction = (clientX - bounds.left) / Math.max(1, bounds.width);
    const rawIndex = Math.round(fraction * Math.max(0, currentSeries.length - 1));
    return Math.max(0, Math.min(currentSeries.length - 1, rawIndex));
  };
  const handlePointer = (event: React.PointerEvent<SVGRectElement>) => setHoveredIndex(indexAt(event.clientX, event.currentTarget.getBoundingClientRect()));
  const handleSelect = (event: React.MouseEvent<SVGRectElement>) => {
    const index = indexAt(event.clientX, event.currentTarget.getBoundingClientRect());
    setPinnedIndex((current) => current === index ? null : index);
    setHoveredIndex(index);
  };
  const hoverX = activeIndex === null ? null : xAt(activeIndex, currentSeries.length);
  const hoverY = hovered?.value === null || hovered?.value === undefined ? pad.top + plotHeight / 2 : yAt(hovered.value);
  const tooltipWidth = 176;
  const tooltipX = hoverX === null ? 0 : Math.min(width - pad.right - tooltipWidth, Math.max(pad.left, hoverX + (hoverX > width * 0.7 ? -tooltipWidth - 14 : 14)));
  const tooltipY = Math.min(height - pad.bottom - 118, Math.max(pad.top + 4, hoverY - 58));
  return (
    <div className="clicko-analytics-trend relative overflow-hidden rounded-xl border border-white/[0.055] bg-[radial-gradient(ellipse_at_50%_0%,rgba(255,127,80,0.045),transparent_48%),#000000]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.05] px-4 py-3">
        <div className="min-w-0 text-[8px]"><div className="flex flex-wrap items-center gap-4"><span className="inline-flex items-center gap-2 font-medium text-white"><i className="clicko-analytics-current-dot h-1.5 w-1.5 rounded-full" />Período atual</span>{compare && <button type="button" onClick={() => setShowPrevious((value) => !value)} className={`inline-flex items-center gap-2 rounded px-1 py-1 transition-colors focus-visible:outline focus-visible:outline-1 focus-visible:outline-[#FF7F50] ${showPrevious ? 'text-[#808080]' : 'text-[#808080]/50'}`} aria-pressed={showPrevious} aria-label={`${showPrevious ? 'Ocultar' : 'Mostrar'} período anterior`}><i className="h-px w-5 border-t border-dashed border-current" />Período anterior</button>}</div>{rangeLabel && <p className="mt-1.5 truncate text-[7px] text-[#808080]">{rangeLabel}{compare && comparisonRangeLabel ? ` · comparação: ${comparisonRangeLabel}` : ''}</p>}</div>
        <div className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-[8px] text-[#808080]"><span>Atual <strong className="ml-1 text-[11px] font-semibold text-white">{formatNumber(currentIndicator, false)}</strong></span>{compare && <span>Anterior <strong className="ml-1 font-medium text-[rgba(255,255,255,.68)]">{formatNumber(previousIndicator, false)}</strong></span>}<span>Média <strong className="ml-1 font-medium text-white">{formatNumber(average, false)}</strong></span>{indicatorChange !== null && <em className="not-italic text-[#FF7F50]">{indicatorChange >= 0 ? '↑' : '↓'} {formatPercent(Math.abs(indicatorChange))}</em>}<span className="rounded-full border border-white/[0.06] px-2 py-1 text-[7px] text-[#808080]">{trendState}</span>{pinnedIndex !== null ? <button type="button" onClick={() => { setPinnedIndex(null); setHoveredIndex(null); }} className="rounded-full border border-[#FF7F50]/20 px-2 py-1 text-[7px] text-[#FF7F50]">Limpar ponto fixado</button> : <span className="hidden text-[7px] text-[#808080] lg:inline">Passe o cursor e clique para fixar</span>}</div>
      </div>
      <div className="overflow-hidden">
      <svg viewBox={`0 0 ${width} ${height}`} className="block h-auto w-full min-w-0 touch-pan-y select-none" role="group" aria-label={`Gráfico interativo da evolução de ${analyticsMetricLabels[metric]}`} onPointerLeave={() => setHoveredIndex(null)}>
        <defs>
          <linearGradient id={`${gradientId}-area`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--cw-clicko-blue, #6EB8F5)" stopOpacity="0.22" /><stop offset="62%" stopColor="var(--cw-clicko-blue, #6EB8F5)" stopOpacity="0.05" /><stop offset="100%" stopColor="var(--cw-clicko-blue, #6EB8F5)" stopOpacity="0" /></linearGradient>
          <filter id={`${gradientId}-glow`} x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        {[0, 1, 2, 3, 4].map((row) => {
          const value = max - (row / 4) * range;
          const y = pad.top + row * (plotHeight / 4);
          return <g key={row}><line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="var(--cw-chart-grid, rgba(255,255,255,.06))" strokeDasharray={row === 4 ? undefined : '2 7'} /><text x={pad.left - 12} y={y + 3} fill="var(--cw-chart-muted, #808080)" fontSize="8" textAnchor="end">{formatNumber(value, false)}</text></g>;
        })}
        {currentSegments.map((rows, index) => rows.length > 1 && <path key={`area-${index}`} d={`${smoothPath(rows)} L ${rows.at(-1)!.x} ${pad.top + plotHeight} L ${rows[0].x} ${pad.top + plotHeight} Z`} fill={`url(#${gradientId}-area)`} />)}
        {compare && showPrevious && previousSegments.map((rows, index) => rows.length > 1 && <path key={`previous-${index}`} d={smoothPath(rows)} fill="none" stroke="var(--cw-chart-previous, #808080)" strokeOpacity="0.72" strokeDasharray="4 7" strokeLinecap="round" strokeWidth="1.4" />)}
        {currentSegments.map((rows, index) => rows.length > 1 ? <path key={`current-${index}`} className="clicko-analytics-trend-line" pathLength="1" d={smoothPath(rows)} fill="none" stroke="var(--cw-clicko-blue-ink, #6EB8F5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.15" /> : <circle key={`current-${index}`} cx={rows[0].x} cy={rows[0].y} r="3.5" fill="var(--cw-clicko-blue-ink, #6EB8F5)" />)}
        {[0, Math.floor((points.length - 1) / 2), points.length - 1].filter((index, position, rows) => index >= 0 && rows.indexOf(index) === position).map((index) => <text key={index} x={xAt(index, points.length)} y={height - 13} fill="var(--cw-chart-muted, #808080)" fontSize="8" textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}>{dateLabel(points[index]?.date)}</text>)}
        {hoverX !== null && <g className="clicko-analytics-tooltip" pointerEvents="none"><line x1={hoverX} x2={hoverX} y1={pad.top} y2={pad.top + plotHeight} stroke="var(--cw-chart-ink, #FFFFFF)" strokeOpacity="0.16" strokeDasharray="2 5" /><circle cx={hoverX} cy={hoverY} r="10" fill="var(--cw-clicko-blue, #6EB8F5)" fillOpacity="0.12" /><circle cx={hoverX} cy={hoverY} r="3.5" fill="var(--cw-tooltip, #000000)" stroke="var(--cw-clicko-blue-ink, #6EB8F5)" strokeWidth="2" /><g transform={`translate(${tooltipX} ${tooltipY})`}><rect width={tooltipWidth} height="108" rx="11" fill="var(--cw-tooltip, #000000)" stroke="var(--cw-line-strong, rgba(255,255,255,.13))" /><text x="12" y="18" fill="var(--cw-chart-muted, #808080)" fontSize="8">{dateLabel(hovered?.point.date)}</text><text x="12" y="35" fill="var(--cw-chart-muted, #808080)" fontSize="7">{analyticsMetricLabels[metric]}</text><text x="12" y="55" fill="var(--cw-chart-ink, #FFFFFF)" fontSize="14" fontWeight="600">{hovered?.value === null || hovered?.value === undefined ? 'Indisponível' : formatNumber(hovered.value, false)}</text>{compare && showPrevious && <><text x="12" y="73" fill="var(--cw-chart-muted, #808080)" fontSize="7">Período anterior  <tspan fill="var(--cw-chart-ink, #FFFFFF)">{previousHovered?.value === null || previousHovered?.value === undefined ? '—' : formatNumber(previousHovered.value, false)}</tspan></text><text x="12" y="93" fill="var(--cw-clicko-blue-ink, #6EB8F5)" fontSize="8" fontWeight="600">{hoveredDifference === null ? 'Sem comparação' : `${hoveredDifference >= 0 ? '+' : '−'}${formatNumber(Math.abs(hoveredDifference), false)}`}  <tspan fill="var(--cw-chart-muted, #808080)">{hoveredChange === null ? '' : `${hoveredChange >= 0 ? '↑' : '↓'} ${formatPercent(Math.abs(hoveredChange))}`}</tspan></text></>}</g></g>}
        <rect className="cursor-crosshair" x={pad.left} y={pad.top} width={plotWidth} height={plotHeight} fill="transparent" aria-label={`Explorar pontos de ${analyticsMetricLabels[metric]}`} onPointerMove={handlePointer} onPointerDown={handlePointer} onClick={handleSelect} />
      </svg>
      </div>
      {((showInsight && insight) || error || (compare && previousIndicator === null)) && <div className="border-t border-white/[0.05] px-4 py-3"><span className={`clicko-analytics-insight-label text-[7px] font-medium uppercase tracking-[0.15em] ${error ? 'is-error' : ''}`}>{error ? 'Atualização' : compare && previousIndicator === null ? 'Comparação' : 'Insight da Clicko'}</span><p className="mt-1.5 text-[8px] leading-4 text-[#808080]">{error || (compare && previousIndicator === null ? 'Não existem dados suficientes no período anterior para calcular uma comparação confiável.' : insight)}{indicatorDifference !== null && indicatorChange !== null && <span className="ml-1 text-[rgba(255,255,255,.62)]">Diferença absoluta: {indicatorDifference >= 0 ? '+' : '−'}{formatNumber(Math.abs(indicatorDifference), false)}.</span>}</p></div>}
    </div>
  );
}
