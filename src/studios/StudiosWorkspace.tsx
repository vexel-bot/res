import React from 'react';
import { Clapperboard, Image, Video, Megaphone, SlidersHorizontal } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { AccessDeniedView } from '../components/AccessDeniedView';
import type { NavigationTab } from '../types';
import { ClickoStudioView } from './ClickoStudioView';
import { permittedStudioTools, studioCategories, studioNavigationAllowed, studioTool, type StudioCategory, type StudioTool, type StudioToolId } from './studioNavigation';
import '../components/SettingsView.css';
import './studios-workspace.css';

const icons = { image: Image, video: Video, advertising: Megaphone, tools: SlidersHorizontal };
const futureTools: Partial<Record<StudioCategory, string[]>> = {
  advertising: ['Variações de Criativos'],
  tools: ['Variações de imagem e vídeo', 'Adaptação para redes sociais'],
};

export function StudiosWorkspace({ tool, onToolChange, onNavigate }: {
  tool: StudioTool; onToolChange: (tool: StudioTool) => void; onNavigate: (tab: NavigationTab) => void;
}) {
  const { canAccess } = useGovernance();
  const allowed = permittedStudioTools(canAccess);
  const recent = React.useRef<Partial<Record<StudioCategory, StudioToolId>>>({});
  recent.current[tool.category] = tool.id;
  const categoryNav = React.useRef<HTMLElement>(null);
  const toolsNav = React.useRef<HTMLElement>(null);
  const selectTool = (next: StudioTool) => {
    if (next.id !== tool.id && !studioNavigationAllowed()) return;
    onToolChange(next);
  };
  React.useEffect(() => {
    for (const nav of [categoryNav.current, toolsNav.current]) {
      const current = nav?.querySelector<HTMLElement>('[aria-current="page"]');
      if (current && nav) nav.scrollLeft = Math.max(0, current.offsetLeft - nav.offsetLeft - 12);
    }
  }, [tool.id]);
  const selectCategory = (category: StudioCategory) => {
    const previous = recent.current[category];
    const next = allowed.find(item => item.id === previous) || allowed.find(item => item.category === category);
    if (next) selectTool(next);
  };
  const arrowNavigation = (event: React.KeyboardEvent<HTMLElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    const buttons = [...event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')];
    const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (index < 0 || !buttons.length) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next]?.focus();
  };
  return <section className="studios-workspace" aria-label="Studios Clicko">
    <header className="studios-workspace__heading"><Clapperboard aria-hidden="true" /><div><h1>Studios</h1><p>Imagem, vídeo e produção criativa no mesmo lugar.</p></div></header>
    <nav className="clicko-settings-top-nav studios-categories" ref={categoryNav} aria-label="Categorias de Studios" onKeyDown={arrowNavigation}>
      <div className="clicko-settings-top-nav__track">{studioCategories.map(category => {
        const Icon = icons[category.id];
        const enabled = allowed.some(item => item.category === category.id);
        return <button type="button" key={category.id} className={`clicko-settings-top-tab ${tool.category === category.id ? 'is-active' : ''}`} disabled={!enabled} title={!enabled ? 'Categoria não disponível nas suas permissões atuais' : undefined} aria-current={tool.category === category.id ? 'page' : undefined} onClick={() => selectCategory(category.id)}><Icon aria-hidden="true" /><span>{category.label}</span></button>;
      })}</div>
    </nav>
    <nav className="studios-tools" ref={toolsNav} aria-label={`Ferramentas de ${studioCategories.find(category => category.id === tool.category)?.label}`} onKeyDown={arrowNavigation}>
      <div>{allowed.filter(item => item.category === tool.category).map(item => <button type="button" key={item.id} aria-current={item.id === tool.id ? 'page' : undefined} onClick={() => selectTool(item)}>{item.label}</button>)}
        {futureTools[tool.category]?.map(label => <button type="button" disabled key={label} title="Ainda não implementado"><span>{label}</span><small>Em breve</small></button>)}
      </div>
    </nav>
    {tool.id === 'image-composition' && <p className="studios-tool-note">Composição local com textos, formas e imagens em camadas. O PhotoCraft existente permanece na opção de editor avançado, conforme a disponibilidade do runtime.</p>}
    {tool.id === 'ad-creatives' && <p className="studios-tool-note">Crie a peça visual com o gerador de imagens existente. Objetivo publicitário, referências e revisão usam o mesmo fluxo. Esta área não publica nem gerencia campanhas de anúncios.</p>}
    {canAccess(tool.module) ? <ClickoStudioView module={tool.module} tool={tool} onNavigate={onNavigate} onToolChange={id => onToolChange(studioTool(id))} /> : <AccessDeniedView onBack={() => { if (allowed[0]) onToolChange(allowed[0]); else onNavigate('dashboard'); }} />}
  </section>;
}
