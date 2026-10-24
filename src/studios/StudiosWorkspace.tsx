import React from 'react';
import { Clapperboard, Image, Video, Megaphone, SlidersHorizontal } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { AccessDeniedView } from '../components/AccessDeniedView';
import { ClickoSelectMenu } from '../components/ClickoSelectMenu';
import type { NavigationTab } from '../types';
import { ClickoStudioView } from './ClickoStudioView';
import { StudioKlicButton } from './shared/StudioWorkspace';
import { categoryStudioTool, futureStudioTools, permittedStudioTools, studioCategories, studioNavigationAllowed, studioTool, type StudioCategory, type StudioTool, type StudioToolId } from './studioNavigation';
import './studios-workspace.css';

const icons = { image: Image, video: Video, advertising: Megaphone, tools: SlidersHorizontal };

export function StudiosWorkspace({ tool, onToolChange, onNavigate }: {
  tool: StudioTool; onToolChange: (tool: StudioTool) => void; onNavigate: (tab: NavigationTab) => void;
}) {
  const { canAccess } = useGovernance();
  const allowed = permittedStudioTools(canAccess);
  const remembered = React.useRef<Partial<Record<StudioCategory, StudioToolId>>>({});
  React.useEffect(() => { remembered.current[tool.category] = tool.id; }, [tool]);
  const selectTool = (next: StudioTool) => {
    if (!allowed.some(item => item.id === next.id)) return;
    if (next.id !== tool.id && !studioNavigationAllowed()) return;
    remembered.current[next.category] = next.id;
    onToolChange(next);
  };
  const selectCategory = (category: StudioCategory) => {
    const next = categoryStudioTool(allowed, category, remembered.current[category]);
    if (next) selectTool(next);
  };
  const arrowNavigation = (event: React.KeyboardEvent<HTMLElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    const buttons = [...event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')];
    const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (index < 0 || !buttons.length) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (['ArrowRight','ArrowDown'].includes(event.key) ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next]?.focus();
  };
  const category = studioCategories.find(item => item.id === tool.category)!;
  const categoryTools = allowed.filter(item => item.category === tool.category);
  const future = futureStudioTools[tool.category] || [];

  return <section className="studios-workspace" aria-label="Studios Clicko">
    <header className="studios-workspace__bar">
      <Clapperboard size={18} aria-hidden="true"/>
      <span className="studios-workspace__brand">Studios</span><span aria-hidden="true" className="studios-workspace__divider">/</span>
      <h1>{tool.label}</h1><StudioKlicButton/>
    </header>
    <div className="studios-navigation">
      <nav className="studios-category-nav" aria-label="Áreas dos Studios" onKeyDown={arrowNavigation}>
        {studioCategories.map(item => {
          const Icon = icons[item.id];
          return <button type="button" key={item.id} aria-pressed={item.id === tool.category}
            disabled={!allowed.some(next => next.category === item.id)} onClick={() => selectCategory(item.id)}>
            <Icon size={14} aria-hidden="true"/>{item.label}
          </button>;
        })}
      </nav>
      <nav className="studios-tool-nav" aria-label={'Ferramentas de ' + category.label} onKeyDown={arrowNavigation}>
        {categoryTools.map(item => <button type="button" key={item.id} aria-current={item.id === tool.id ? 'page' : undefined} onClick={() => selectTool(item)}>{item.label}</button>)}
        {future.map(label => <button type="button" disabled key={label} title="Ainda não implementado">{label}<small>Em breve</small></button>)}
      </nav>
      <div className="studios-compact-navigation" aria-label="Navegação compacta dos Studios">
        <ClickoSelectMenu label="Área dos Studios" ariaLabel="Área dos Studios" value={tool.category}
          options={studioCategories.filter(item => allowed.some(next => next.category === item.id)).map(item => [item.id, item.label])}
          onChange={id => selectCategory(id as StudioCategory)}/>
        <ClickoSelectMenu label="Ferramenta" ariaLabel="Ferramenta dos Studios" value={tool.id} options={categoryTools.map(item => [item.id, item.label])}
          onChange={id => { const next = categoryTools.find(item => item.id === id); if (next) selectTool(next); }}/>
        {future.length > 0 && <small className="studios-future-note">Em breve: {future.join(' · ')}</small>}
      </div>
    </div>
    {canAccess(tool.module) ? <ClickoStudioView module={tool.module} tool={tool} onNavigate={onNavigate} onToolChange={id => selectTool(studioTool(id))} /> : <AccessDeniedView onBack={() => { if (allowed[0]) selectTool(allowed[0]); else onNavigate('dashboard'); }} />}
  </section>;
}
