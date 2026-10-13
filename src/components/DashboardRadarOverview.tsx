import React from 'react';
import { createPortal } from 'react-dom';
import { ArrowRight, Maximize2, Radar, TrendingUp, X } from 'lucide-react';
import type { NavigationTab, Workspace } from '../types';
import { useKlicClient } from '../klic/useKlicClient';
import { useTheme } from '../context/ThemeContext';
import { KlicRadarSection, isRadarTrend, type RadarInitialSnapshot, type RadarResponse } from './KlicRadarSection';
import { ClickoLoader } from './ClickoLoader';

type Props = {
  activeWorkspace: Workspace;
  onNavigate: (tab: NavigationTab) => void;
};

export function DashboardRadarOverview({ activeWorkspace, onNavigate }: Props) {
  const klic = useKlicClient();
  const { theme } = useTheme();
  const request = React.useRef(klic.request);
  request.current = klic.request;
  const section = React.useRef<HTMLElement>(null);
  const tool = React.useRef<HTMLDivElement>(null);
  const openButton = React.useRef<HTMLButtonElement>(null);
  const [started, setStarted] = React.useState(false);
  const [snapshot, setSnapshot] = React.useState<RadarInitialSnapshot | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');
  const [open, setOpen] = React.useState(false);
  const [revision, retry] = React.useReducer(value => value + 1, 0);
  const closeTool = React.useCallback(() => { setOpen(false); openButton.current?.focus({ preventScroll: true }); }, []);

  React.useEffect(() => {
    const node = section.current;
    if (!node || !('IntersectionObserver' in window)) { setStarted(true); return; }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { setStarted(true); observer.disconnect(); }
    }, { rootMargin: '200px 0px' });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  React.useEffect(() => {
    if (!started) return;
    const scope = klic.scope;
    const controller = new AbortController();
    setLoading(true);
    setError('');
    void request.current<RadarResponse>('radar', 'ai-chat', { region: 'BR', forceRefresh: false }, controller.signal)
      .then(data => { if (!controller.signal.aborted) setSnapshot({ scope, region: 'BR', data }); })
      .catch(cause => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar as tendências.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [started, klic.scope, revision]);

  React.useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => tool.current?.focus({ preventScroll: true }));
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { closeTool(); return; }
      if (event.key !== 'Tab' || !tool.current) return;
      const focusable = Array.from(tool.current.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'));
      if (!focusable.length) { event.preventDefault(); tool.current.focus(); return; }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', onKey);
    return () => { cancelAnimationFrame(frame); document.removeEventListener('keydown', onKey); document.body.style.overflow = previousOverflow; };
  }, [open, closeTool]);

  const current = snapshot?.scope === klic.scope ? snapshot : null;
  const trends = (Array.isArray(current?.data.trends) ? current.data.trends.filter(isRadarTrend) : [])
    .filter(trend => trend.region === 'BR' && trend.status !== 'ended')
    .sort((a, b) => b.trendScore - a.trendScore)
    .slice(0, 3);

  return <section ref={section} className="cd-module cd-radar-chapter" aria-labelledby="cd-radar-title">
    <div className="cd-section-heading"><div><span className="cd-eyebrow">Radar de Trends</span><h2 id="cd-radar-title">Assuntos em alta</h2><p>Sinais atuais para orientar sua próxima pauta.</p></div></div>
    {loading && !current ? <div className="cd-radar-state"><ClickoLoader size="small" label="Buscando sinais atuais" />Buscando sinais atuais…</div>
      : error && !current ? <div className="cd-radar-state"><Radar size={19} /><span>{error}</span><button type="button" className="cd-link" onClick={retry}>Tentar novamente<ArrowRight size={16} /></button></div>
      : trends.length ? <div className="cd-trend-list">{trends.map((trend, index) => <button type="button" className="cd-trend-row" key={trend.id} onClick={() => setOpen(true)} title={`${trend.evidence[0]?.sourceLabel || 'Fonte verificada'} · Trend Score ${trend.trendScore}`}><span className="cd-trend-rank">{String(index + 1).padStart(2, '0')}</span><TrendingUp size={16} className="cd-trend-direction" aria-hidden="true" /><span className="cd-trend-copy"><strong>{trend.title}</strong><small>{trend.evidence[0]?.sourceLabel || 'Fonte verificada'} · {trend.status === 'exploding' ? 'Explodindo' : trend.status === 'hot' ? 'Em alta' : 'Em observação'}</small></span><span className="cd-trend-score" aria-label={`Trend Score ${trend.trendScore}`}><small>Score</small>{trend.trendScore}</span><ArrowRight size={16} aria-hidden="true" /></button>)}</div>
      : <div className="cd-empty"><span className="cd-empty-icon"><TrendingUp size={22} /></span><div><strong>Nenhuma tendência disponível agora.</strong><p>Explore o Radar para consultar outras regiões, períodos e filtros.</p></div></div>}
    <button ref={openButton} type="button" className="cd-radar-expand" onClick={() => setOpen(true)} aria-expanded={open} aria-haspopup="dialog"><span><Maximize2 size={16} /><span><strong>Ampliar Radar</strong><small>Ver filtros, fontes e detalhes dos sinais</small></span></span><ArrowRight size={16} /></button>
    {open && createPortal(<div className="clicko-app-shell clicko-creative-workspace cd-trends-popout" data-theme={theme} role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) closeTool(); }}><section ref={tool} className="cd-trends-popout-panel" role="dialog" aria-modal="true" aria-labelledby="cd-trends-popout-title" tabIndex={-1}><header className="cd-trends-popout-header"><div><span>Radar de Trends</span><h2 id="cd-trends-popout-title">Assuntos em alta</h2><p>Explore sinais, fontes e oportunidades com mais contexto.</p></div><button type="button" onClick={closeTool} aria-label="Fechar assuntos em alta"><X size={19} /></button></header><div className="cd-trends-popout-body"><KlicRadarSection key={klic.scope} activeWorkspace={activeWorkspace} onNavigate={onNavigate} initialSnapshot={current || undefined} /></div></section></div>, document.body)}
  </section>;
}
