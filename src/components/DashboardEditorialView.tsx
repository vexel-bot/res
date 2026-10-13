import React from 'react';
import { ArrowUpRight, ChartNoAxesCombined, Plus } from 'lucide-react';
import { KlicSymbol } from './KlicSymbol';
import type { NavigationTab, Post, Workspace } from '../types';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import { DashboardImmersiveScene } from './DashboardImmersiveScene';
import { DashboardControlPanel } from './DashboardControlPanel';
import { dashboardGreeting } from './dashboardOperationalModel';
import './DashboardExperience.css';
import './DashboardOperations.css';

interface DashboardViewProps {
  posts: Post[];
  activeWorkspace: Workspace;
  onNavigate: (tab: NavigationTab) => void;
  onNewPost: () => void;
  onSelectPost: (post: Post) => void;
}

function DashboardHero({ workspace, firstName, isPersonal, canAccess, onNavigate, onNewPost }: {
  workspace: Workspace; firstName: string; isPersonal: boolean;
  canAccess: (tab: NavigationTab) => boolean; onNavigate: DashboardViewProps['onNavigate']; onNewPost: () => void;
}) {
  const frame = React.useRef<number | null>(null);
  const hero = React.useRef<HTMLElement>(null);
  const [scenePaused, setScenePaused] = React.useState(true);
  const [greeting, setGreeting] = React.useState(() => dashboardGreeting());
  React.useEffect(() => () => { if (frame.current !== null) cancelAnimationFrame(frame.current); }, []);
  React.useEffect(() => {
    const refresh = () => setGreeting(current => {
      const next = dashboardGreeting();
      return current === next ? current : next;
    });
    const timer = window.setInterval(refresh, 60_000);
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, []);
  React.useEffect(() => {
    const node = hero.current;
    if (!node || !('IntersectionObserver' in window)) return;
    let visible = false;
    const staticScene = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setScenePaused(!visible || document.hidden || staticScene.matches);
    const observer = new IntersectionObserver(entries => { visible = Boolean(entries[0]?.isIntersecting && entries[0].intersectionRatio >= 0.05); update(); }, { threshold: 0.05 });
    observer.observe(node);
    document.addEventListener('visibilitychange', update);
    staticScene.addEventListener('change', update);
    return () => {
      observer.disconnect();
      document.removeEventListener('visibilitychange', update);
      staticScene.removeEventListener('change', update);
    };
  }, []);
  const handlePointer = (event: React.PointerEvent<HTMLElement>) => {
    if (event.pointerType !== 'mouse' || window.matchMedia('(prefers-reduced-motion: reduce), (max-width: 750px), (pointer: coarse)').matches) return;
    const element = event.currentTarget;
    const rect = element.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      element.style.setProperty('--cd-pointer-x', `${(x * 10).toFixed(1)}px`);
      element.style.setProperty('--cd-pointer-y', `${(y * 8).toFixed(1)}px`);
      element.style.setProperty('--cd-pointer-ry', `${(x * 7).toFixed(1)}deg`);
      element.style.setProperty('--cd-pointer-rx', `${(-y * 5).toFixed(1)}deg`);
    });
  };
  const resetPointer = (event: React.PointerEvent<HTMLElement>) => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    event.currentTarget.style.setProperty('--cd-pointer-x', '0px');
    event.currentTarget.style.setProperty('--cd-pointer-y', '0px');
    event.currentTarget.style.setProperty('--cd-pointer-ry', '0deg');
    event.currentTarget.style.setProperty('--cd-pointer-rx', '0deg');
  };
  return <header ref={hero} className="cd-hero" onPointerMove={handlePointer} onPointerLeave={resetPointer}>
    <div className="cd-hero-copy"><span className="cd-eyebrow"><span className="cd-live-dot" />{isPersonal ? 'Perfil pessoal' : 'Workspace'} · {workspace.name}</span><p className="cd-hero-greeting">{greeting}, {firstName}.</p><h1>O que vamos<br /><em>criar hoje?</em></h1><p className="cd-hero-intro">Da primeira ideia ao resultado, tudo começa aqui.</p><div className="cd-hero-actions">
      {canAccess('create-copy') && <button type="button" className="cd-button cd-button-primary" onClick={onNewPost}><Plus size={17} />Criar conteúdo</button>}
      {canAccess('ai-chat') && <button type="button" className="cd-button cd-button-quiet cd-quick-klic" onClick={() => onNavigate('ai-chat')}><KlicSymbol size={16} />Falar com a KLIC</button>}
      {canAccess('analytics') && <button type="button" className="cd-button cd-button-text" onClick={() => onNavigate('analytics')}><ChartNoAxesCombined size={15} />Ver desempenho<ArrowUpRight size={14} /></button>}
    </div></div>
    <div className="cd-hero-scene" aria-hidden="true"><DashboardImmersiveScene playing={!scenePaused} /></div>
  </header>;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ posts, activeWorkspace, onNavigate, onNewPost, onSelectPost }) => {
  const { environmentMode, currentUser, approvals, canAccess } = useGovernance();
  const { connectedAccounts, assets, clients } = useOperations();
  const root = React.useRef<HTMLDivElement>(null);
  const isPersonal = environmentMode === 'personal';
  const firstName = currentUser?.name?.replace(/\s*\(.*\)$/, '').split(/\s+/)[0] || 'bem-vindo';
  const workspacePosts = posts.filter(post => post.workspaceId === activeWorkspace.id);
  const workspaceAssets = assets.filter(asset => asset.workspaceId === activeWorkspace.id);
  const workspaceApprovals = canAccess('approvals') ? approvals.filter(item => item.workspaceId === activeWorkspace.id) : [];
  const workspaceAccounts = canAccess('connected-accounts') ? connectedAccounts.filter(account => !account.workspaceId || account.workspaceId === activeWorkspace.id) : [];
  React.useEffect(() => {
    const element = root.current;
    if (!element || !('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const sections = element.querySelectorAll<HTMLElement>('[data-reveal]');
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
    }), { threshold: 0.08, rootMargin: '0px 0px 80px 0px' });
    sections.forEach(section => observer.observe(section));
    element.classList.add('cd-enhanced');
    return () => { observer.disconnect(); element.classList.remove('cd-enhanced'); };
  }, [activeWorkspace.id, environmentMode]);
  return <div ref={root} className="clicko-dashboard-editorial cd-root">
    <DashboardHero workspace={activeWorkspace} firstName={firstName} isPersonal={isPersonal} canAccess={canAccess} onNavigate={onNavigate} onNewPost={onNewPost} />
    <DashboardControlPanel posts={workspacePosts} assets={workspaceAssets} approvals={workspaceApprovals} accounts={workspaceAccounts} clients={clients} workspace={activeWorkspace} isPersonal={isPersonal} canAccess={canAccess} onNavigate={onNavigate} onNewPost={onNewPost} onSelectPost={onSelectPost} />
  </div>;
};
