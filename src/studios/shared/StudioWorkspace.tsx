import React from 'react';
import { X, Sparkles } from 'lucide-react';
import { isStudioTypingTarget, studioDefaultTimelineHeight, studioShortcut, studioTimelineHeight, studioWorkspaceHeight, type StudioPane } from './studioWorkspaceModel';

/** Dispatch only to the current editor's existing action; never intercept text undo or another chat. */
export function useStudioShortcuts(root: React.RefObject<HTMLElement | null>, enabled = true) {
  React.useEffect(() => {
    if (!enabled) return;
    const handler = (event: KeyboardEvent) => {
      if (!(event.target instanceof Node) || !root.current?.contains(event.target)) return;
      const action = studioShortcut(event.key, event.ctrlKey || event.metaKey, event.shiftKey, isStudioTypingTarget(event.target));
      if (!action) return;
      const button = root.current.querySelector<HTMLButtonElement>(`button[data-studio-action="${action}"]`);
      if (!button) return;
      event.preventDefault(); if (!button.disabled) button.click();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [root, enabled]);
}

export function StudioKlicButton() {
  const trigger = React.useRef<HTMLButtonElement>(null);
  const wasOpen = React.useRef(false);
  const [expanded, setExpanded] = React.useState(false);
  React.useEffect(() => {
    const visibility = (event: Event) => {
      const open = (event as CustomEvent<boolean>).detail === true;
      if (wasOpen.current && !open && trigger.current?.getClientRects().length) trigger.current.focus({ preventScroll:true });
      wasOpen.current = open; setExpanded(open);
    };
    window.addEventListener('clicko:klic-panel-visibility', visibility);
    return () => window.removeEventListener('clicko:klic-panel-visibility', visibility);
  }, []);
  return <button ref={trigger} type="button" className="studio-klic-access" aria-controls="klic-floating-dialog" aria-expanded={expanded} onClick={() => window.dispatchEvent(new Event('clicko:klic-production-open'))}>
    <Sparkles size={15} aria-hidden="true" />KLIC
  </button>;
}

/** Utilities share the current document; this panel is not another editor/chat. */
export function StudioUtilityPanel({ title, open, onClose, children }: {
  title: string; open: boolean; onClose: () => void; children: React.ReactNode;
}) {
  const heading = React.useId();
  const close = React.useRef<HTMLButtonElement>(null);
  const callback = React.useRef(onClose); callback.current = onClose;
  React.useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    close.current?.focus({ preventScroll: true });
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || event.defaultPrevented) return;
      if (event.target instanceof Element && event.target.closest('.clicko-select-menu')?.querySelector('[role="listbox"]')) return;
      event.preventDefault(); callback.current();
    };
    window.addEventListener('keydown', escape);
    const openKlic = () => callback.current();
    window.addEventListener('clicko:klic-production-open', openKlic);
    return () => { window.removeEventListener('keydown', escape); window.removeEventListener('clicko:klic-production-open', openKlic); if (previous?.isConnected) previous.focus({ preventScroll: true }); };
  }, [open]);
  if (!open) return null;
  return <aside className="studio-utility-panel" role="dialog" aria-modal="false" aria-labelledby={heading}>
    <header><h2 id={heading}>{title}</h2><button ref={close} type="button" onClick={onClose} aria-label={`Fechar ${title}`}><X size={17} /></button></header>
    <div className="studio-utility-panel__body">{children}</div>
  </aside>;
}

export function StudioEditorFrame({ toolbar, materials, preview, inspector, timeline, pane, onPaneChange, className = '' }: {
  toolbar: React.ReactNode; materials: React.ReactNode; preview: React.ReactNode; inspector?: React.ReactNode;
  timeline?: React.ReactNode; pane: StudioPane; onPaneChange: (pane: StudioPane) => void; className?: string;
}) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [height, setHeight] = React.useState(560);
  const [timelineSize, setTimelineSize] = React.useState<number | undefined>(undefined);
  const drag = React.useRef<{ y: number; height: number } | undefined>(undefined);
  const actualTimeline = studioTimelineHeight(timelineSize ?? studioDefaultTimelineHeight(height), height);
  const id = React.useId();
  // Sibling notices and compact toolbars can change the frame's top without
  // resizing its immediate parent (or the window).
  React.useEffect(() => {
    if (ref.current) setHeight(studioWorkspaceHeight(window.visualViewport?.height || window.innerHeight, ref.current.getBoundingClientRect().top));
  });
  React.useEffect(() => {
    const update = () => { if (ref.current) setHeight(studioWorkspaceHeight(window.visualViewport?.height || window.innerHeight, ref.current.getBoundingClientRect().top)); };
    update(); window.addEventListener('resize', update); window.visualViewport?.addEventListener('resize', update);
    const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(update);
    if (ref.current?.parentElement) observer?.observe(ref.current.parentElement);
    return () => { window.removeEventListener('resize', update); window.visualViewport?.removeEventListener('resize', update); observer?.disconnect(); };
  }, []);
  const panes: Array<[StudioPane, string]> = [['preview', 'Prévia'], ['materials', 'Materiais'], ...(inspector ? [['properties', 'Propriedades'] as [StudioPane, string]] : []), ...(timeline ? [['timeline', 'Timeline'] as [StudioPane, string]] : [])];
  const active = panes.some(([key]) => key === pane) ? pane : 'preview';
  return <div ref={ref} className={`studio-editor-frame ${inspector ? 'has-inspector' : ''} ${className}`} data-pane={active}
    style={{ height, '--studio-timeline-height': `${actualTimeline}px` } as React.CSSProperties}>
    <div className="studio-editor-toolbar">{toolbar}</div>
    <nav className="studio-pane-switcher" aria-label="Painéis do editor">{panes.map(([key, label]) => <button type="button" key={key} aria-pressed={active === key} aria-controls={`${id}-${key}`} onClick={() => onPaneChange(key)}>{label}</button>)}</nav>
    <div className="studio-editor-stage">
      <aside id={`${id}-materials`} className="studio-region studio-materials" aria-label="Materiais e camadas">{materials}</aside>
      <div id={`${id}-preview`} className="studio-region studio-preview" aria-label="Visualização do projeto">{preview}</div>
      {inspector && <aside id={`${id}-properties`} className="studio-region studio-inspector" aria-label="Propriedades da seleção">{inspector}</aside>}
    </div>
    {timeline && <div id={`${id}-timeline`} className="studio-editor-timeline">
      <div className="studio-timeline-resize" role="separator" aria-label="Redimensionar timeline" aria-orientation="horizontal" tabIndex={0}
        aria-valuemin={100} aria-valuemax={Math.floor(Math.min(360, height * .45))} aria-valuenow={actualTimeline}
        onKeyDown={event => { if (['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) { event.preventDefault(); setTimelineSize(studioTimelineHeight(event.key === 'Home' ? 100 : event.key === 'End' ? 360 : actualTimeline + (event.key === 'ArrowUp' ? 20 : -20), height)); } }}
        onPointerDown={event => { if (event.button !== 0) return; drag.current = { y: event.clientY, height: actualTimeline }; event.currentTarget.setPointerCapture(event.pointerId); }}
        onPointerMove={event => { if (drag.current) setTimelineSize(studioTimelineHeight(drag.current.height + drag.current.y - event.clientY, height)); }}
        onPointerUp={event => { drag.current = undefined; if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); }}
        onPointerCancel={() => { drag.current = undefined; }} onLostPointerCapture={() => { drag.current = undefined; }} />
      <div className="studio-timeline-content">{timeline}</div>
    </div>}
  </div>;
}
