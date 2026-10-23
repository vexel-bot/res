import React from 'react';
import { usePresence } from '../motion/usePresence';
import { ArrowRight, BarChart3, CalendarDays, FileText, FolderOpen, GitFork, Link2, PenTool, Search, Settings, Users, X } from 'lucide-react';
import type { NavigationTab, SearchResultItem } from '../types';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';
import './SpotlightModal.css';

type CommandItem = SearchResultItem & { keywords: string; onSelect?: () => void };

const navigationItems: Array<Omit<CommandItem, 'id'>> = [
  { title: 'Studios · Imagem', subtitle: 'Gerar e editar imagens no ambiente unificado', type: 'action', tabToNavigate: 'create-image', keywords: 'studios imagem foto criar editar composição carrossel' },
  { title: 'Studios · Vídeo', subtitle: 'Vídeo, timeline, motion design e anúncios', type: 'action', tabToNavigate: 'create-video', keywords: 'studios vídeo video editor motion anúncio audiovisual' },
  { title: 'Criar conteúdo', subtitle: 'Abrir o estúdio de criação textual', type: 'action', tabToNavigate: 'create-copy', keywords: 'novo post copy carrossel roteiro' },
  { title: 'Calendário editorial', subtitle: 'Planejar, revisar e agendar conteúdos', type: 'action', tabToNavigate: 'calendar', keywords: 'agenda programação publicação' },
  { title: 'Contas conectadas', subtitle: 'Gerenciar redes e permissões', type: 'action', tabToNavigate: 'connected-accounts', keywords: 'instagram facebook tiktok youtube linkedin threads pinterest x oauth' },
  { title: 'Analytics', subtitle: 'Consultar resultados conectados', type: 'action', tabToNavigate: 'analytics', keywords: 'métricas alcance engajamento relatório' },
  { title: 'Jornadas Clicko', subtitle: 'Planejar e validar rotinas operacionais', type: 'automation', tabToNavigate: 'automations', keywords: 'automação playbook fluxo rotina' },
  { title: 'Configurações', subtitle: 'Conta, segurança, consumo e suporte', type: 'action', tabToNavigate: 'settings', keywords: 'preferências tema perfil ajuda' },
];

interface SpotlightModalProps { isOpen: boolean; onClose: () => void; onNavigate: (tab: NavigationTab) => void; }

export const SpotlightModal: React.FC<SpotlightModalProps> = ({ isOpen, onClose, onNavigate }) => {
  const operations = useOperations();
  const { canAccess } = useGovernance();
  const [query, setQuery] = React.useState('');
  const [activeIndex, setActiveIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const presence = usePresence(isOpen);

  const items = React.useMemo<CommandItem[]>(() => [
    ...navigationItems.filter(item => canAccess(item.tabToNavigate)).map((item, index) => ({ ...item, id: `command-${index}` })),
    ...operations.clients.map(client => ({ id: `client-${client.id}`, title: client.name, subtitle: `Cliente · ${client.segment || 'segmento não informado'}`, type: 'client' as const, tabToNavigate: 'workspace' as const, keywords: `${client.segment} ${client.products} ${client.audience}`, onSelect: () => operations.setActiveClientId(client.id) })),
    ...operations.campaigns.map(campaign => ({ id: `campaign-${campaign.id}`, title: campaign.name, subtitle: `Campanha · ${campaign.objective}`, type: 'campaign' as const, tabToNavigate: 'strategy' as const, keywords: `${campaign.objective} ${campaign.audience} ${campaign.channels.join(' ')}`, onSelect: () => operations.setActiveCampaignId(campaign.id) })),
    ...operations.posts.map(post => ({ id: `post-${post.id}`, title: post.title, subtitle: `Conteúdo · ${post.platform} · ${post.status}`, type: 'post' as const, tabToNavigate: 'calendar' as const, keywords: `${post.copy} ${post.hashtags.join(' ')} ${post.format} ${post.platform}` })),
    ...operations.assets.map(asset => ({ id: `asset-${asset.id}`, title: asset.title, subtitle: `Biblioteca · ${asset.type}`, type: 'asset' as const, tabToNavigate: 'library' as const, keywords: `${asset.description || ''} ${asset.tags.join(' ')} ${asset.type}` })),
  ], [canAccess, operations]);

  const normalized = query.trim().toLocaleLowerCase('pt-BR');
  const filtered = React.useMemo(() => items.map((item, index) => {
    const title = item.title.toLocaleLowerCase('pt-BR');
    const haystack = `${title} ${item.subtitle} ${item.keywords}`.toLocaleLowerCase('pt-BR');
    const score = !normalized ? index : title === normalized ? -30 : title.startsWith(normalized) ? -20 : title.includes(normalized) ? -10 : haystack.includes(normalized) ? 0 : 1000;
    return { item, score, index };
  }).filter(entry => entry.score < 1000).sort((left, right) => left.score - right.score || left.index - right.index).slice(0, 12).map(entry => entry.item), [items, normalized]);

  React.useEffect(() => {
    if (!isOpen) return;
    setQuery(''); setActiveIndex(0);
    const frame = window.requestAnimationFrame(() => inputRef.current?.focus());
    return () => window.cancelAnimationFrame(frame);
  }, [isOpen]);
  React.useEffect(() => setActiveIndex(0), [normalized]);

  if (!presence.present) return null;
  const select = (item: CommandItem) => { item.onSelect?.(); onNavigate(item.tabToNavigate); onClose(); };
  const icon = (type: SearchResultItem['type']) => type === 'post' ? <PenTool aria-hidden="true" /> : type === 'campaign' ? <GitFork aria-hidden="true" /> : type === 'client' || type === 'workspace' ? <Users aria-hidden="true" /> : type === 'asset' ? <FolderOpen aria-hidden="true" /> : <FileText aria-hidden="true" />;
  const quick = (id: string, tab: NavigationTab): CommandItem => ({ id, title: '', subtitle: '', keywords: '', type: 'action', tabToNavigate: tab });

  return <div {...presence.props} className="clicko-search-overlay" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="clicko-search-panel" role="dialog" aria-modal="true" aria-labelledby="clicko-search-title" onKeyDown={event => {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); }
      if (event.key === 'ArrowDown' && filtered.length) { event.preventDefault(); setActiveIndex(value => (value + 1) % filtered.length); }
      if (event.key === 'ArrowUp' && filtered.length) { event.preventDefault(); setActiveIndex(value => (value - 1 + filtered.length) % filtered.length); }
      if (event.key === 'Enter' && filtered[activeIndex]) { event.preventDefault(); select(filtered[activeIndex]); }
    }}>
      <header className="clicko-search-heading"><div><span className="clicko-search-eyebrow">Command Center · Ctrl K</span><h2 id="clicko-search-title">Encontre e abra o contexto certo</h2></div><div className="clicko-search-heading-actions"><button type="button" onClick={onClose} aria-label="Fechar pesquisa"><X aria-hidden="true" /></button></div></header>
      <div className="clicko-search-field"><Search aria-hidden="true" /><input ref={inputRef} type="search" autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder="Conteúdos, campanhas, clientes, arquivos ou ações" aria-label="Pesquisar na Clicko" aria-controls="clicko-search-results" aria-activedescendant={filtered[activeIndex] ? `clicko-search-result-${activeIndex}` : undefined} />{query && <button type="button" className="clicko-search-clear" onClick={() => { setQuery(''); inputRef.current?.focus(); }} aria-label="Limpar pesquisa"><X aria-hidden="true" /></button>}</div>
      <div className="clicko-search-meta" aria-live="polite"><span>{query ? `Resultados reais para “${query}”` : 'Ações e dados deste ambiente'}</span><span>{filtered.length} {filtered.length === 1 ? 'resultado' : 'resultados'}</span></div>
      <div id="clicko-search-results" className="clicko-search-results" role="listbox" aria-label="Resultados da pesquisa">
        {!filtered.length ? <div className="clicko-search-empty"><span><Search aria-hidden="true" /></span><strong>Nenhum resultado neste ambiente</strong><p>Tente outro termo ou ajuste sua busca.</p></div> : filtered.map((item, index) => <button id={`clicko-search-result-${index}`} key={item.id} type="button" role="option" aria-selected={activeIndex === index} onMouseEnter={() => setActiveIndex(index)} onClick={() => select(item)} className={`clicko-search-result ${activeIndex === index ? 'is-active' : ''}`}><span className={`clicko-search-result-icon is-${item.type}`}>{icon(item.type)}</span><span className="clicko-search-result-copy"><strong>{item.title}</strong><small>{item.subtitle}</small></span><span className="clicko-search-result-action">Abrir <ArrowRight aria-hidden="true" /></span></button>)}
      </div>
      <footer className="clicko-search-shortcuts" aria-label="Atalhos rápidos">{canAccess('calendar') && <button type="button" onClick={() => select(quick('calendar', 'calendar'))}><CalendarDays />Calendário</button>}{canAccess('connected-accounts') && <button type="button" onClick={() => select(quick('connections', 'connected-accounts'))}><Link2 />Conexões</button>}{canAccess('analytics') && <button type="button" onClick={() => select(quick('analytics', 'analytics'))}><BarChart3 />Analytics</button>}{canAccess('settings') && <button type="button" onClick={() => select(quick('settings', 'settings'))}><Settings />Configurações</button>}</footer>
    </section>
  </div>;
};
