import React from 'react';
import { plasmaActivity, plasmaCompleted, plasmaEnergy, type KlicPlasmaState } from '../klic/plasmaState';
import { observePlasma } from '../klic/plasmaVisibility';
import './KlicPlasma.css';
import './KlicPlasmaSignature.css';
export type { KlicPlasmaState } from '../klic/plasmaState';

const stateCopy: Record<KlicPlasmaState, string> = {
  idle: 'Disponível',
  connecting: 'Inicializando voz',
  listening: 'Escutando...',
  processing: 'Processando...',
  speaking: 'Falando...',
  error: 'Conexão interrompida',
};

type KlicPlasmaProps = {
  state?: KlicPlasmaState;
  intensity?: number;
  compact?: boolean;
  appearance?: 'default' | 'signature';
  showIdentity?: boolean;
  onActivate?: () => void;
  interacting?: boolean;
  responding?: boolean;
  completionId?: string;
  scopeKey?: string;
};

export function KlicPlasma({ state = 'idle', intensity = 0, compact = false, appearance = 'default', showIdentity = true, onActivate, interacting = false, responding = false, completionId, scopeKey }: KlicPlasmaProps) {
  const energy = plasmaEnergy(intensity);
  const activity = plasmaActivity(state, responding, interacting);
  const root = React.useRef<HTMLDivElement>(null);
  const physical = React.useRef<HTMLSpanElement>(null);
  const pendingFrame = React.useRef<number | null>(null);
  const reaction = React.useRef<Animation | null>(null);
  const active = React.useRef(false);
  const reduced = React.useRef(false);
  const previous = React.useRef({ activity, completionId, scopeKey });
  const reactToTouch = React.useCallback((completed = false) => {
    if (!active.current || !physical.current) return;
    reaction.current?.cancel();
    const small = reduced.current;
    reaction.current = physical.current.animate([
      { scale: '1' }, { scale: String(completed ? (small ? 1.005 : 1.028) : (small ? 0.995 : 0.967)), offset: 0.3 },
      { scale: String(completed ? 1.008 : (small ? 1.003 : 1.022)), offset: 0.65 }, { scale: '1' },
    ], { duration: completed ? 900 : 650, easing: 'cubic-bezier(.22,.65,.32,1)' });
  }, []);
  React.useEffect(() => {
    const element = root.current;
    if (!element) return;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const resetPointer = () => {
      if (pendingFrame.current !== null) cancelAnimationFrame(pendingFrame.current);
      pendingFrame.current = null;
      element.style.setProperty('--klic-pointer-x', '0px');
      element.style.setProperty('--klic-pointer-y', '0px');
      element.style.setProperty('--klic-pointer-light', '0');
    };
    const syncReduced = () => { reduced.current = media.matches; if (media.matches) { resetPointer(); reaction.current?.cancel(); } };
    syncReduced(); media.addEventListener('change', syncReduced);
    const stopObserving = observePlasma(element, visible => {
      active.current = visible;
      element.dataset.motion = visible ? 'active' : 'paused';
      if (!visible) { resetPointer(); reaction.current?.cancel(); }
    });
    return () => {
      stopObserving(); media.removeEventListener('change', syncReduced);
      resetPointer(); reaction.current?.cancel();
    };
  }, []);
  React.useEffect(() => {
    if (previous.current.scopeKey === scopeKey && plasmaCompleted(previous.current.activity, activity, previous.current.completionId, completionId)) reactToTouch(true);
    previous.current = { activity, completionId, scopeKey };
  }, [activity, completionId, scopeKey, reactToTouch]);
  const movePointer = (event: React.PointerEvent) => {
    if (event.pointerType !== 'mouse' || reduced.current || !active.current || !root.current) return;
    const element = root.current;
    const bounds = physical.current?.getBoundingClientRect();
    if (!bounds) return;
    const x = Math.max(-1, Math.min(1, (event.clientX - bounds.left - bounds.width / 2) / (bounds.width / 2)));
    const y = Math.max(-1, Math.min(1, (event.clientY - bounds.top - bounds.height / 2) / (bounds.height / 2)));
    if (pendingFrame.current !== null) cancelAnimationFrame(pendingFrame.current);
    pendingFrame.current = requestAnimationFrame(() => {
      pendingFrame.current = null;
      element.style.setProperty('--klic-pointer-x', `${(x * bounds.width * .012).toFixed(2)}px`);
      element.style.setProperty('--klic-pointer-y', `${(y * bounds.height * .012).toFixed(2)}px`);
      element.style.setProperty('--klic-light-x', `${50 + x * 25}%`);
      element.style.setProperty('--klic-light-y', `${50 + y * 25}%`);
      element.style.setProperty('--klic-pointer-light', '1');
    });
  };
  const leavePointer = () => {
    if (pendingFrame.current !== null) cancelAnimationFrame(pendingFrame.current);
    pendingFrame.current = null;
    root.current?.style.setProperty('--klic-pointer-x', '0px');
    root.current?.style.setProperty('--klic-pointer-y', '0px');
    root.current?.style.setProperty('--klic-pointer-light', '0');
  };
  const style = { '--klic-energy': energy.toFixed(3) } as React.CSSProperties;
  const content = (
    <span ref={physical} className="klic-plasma__physical">
      <span className="klic-plasma__aura" />
      <span className="klic-plasma__orbit klic-plasma__orbit--outer" />
      <span className="klic-plasma__orbit klic-plasma__orbit--inner" />
      <span className="klic-plasma__body">
        <span className="klic-plasma__fluid klic-plasma__fluid--one" />
        <span className="klic-plasma__fluid klic-plasma__fluid--two" />
        <span className="klic-plasma__fluid klic-plasma__fluid--three" />
        <span className="klic-plasma__core" />
        <span className="klic-plasma__sheen" />
      </span>
      <span className="klic-plasma__particle klic-plasma__particle--one" />
      <span className="klic-plasma__particle klic-plasma__particle--two" />
      <span className="klic-plasma__particle klic-plasma__particle--three" />
    </span>
  );

  return (
    <div ref={root} data-activity={activity} data-motion="paused" onPointerMove={movePointer} onPointerLeave={leavePointer} onPointerDown={() => reactToTouch()} className={`klic-plasma-wrap ${compact ? 'klic-plasma-wrap--compact' : ''} ${appearance === 'signature' ? 'klic-plasma-wrap--signature' : ''}`}>
      {onActivate ? (
        <button
          type="button"
          className={`klic-plasma klic-plasma--${state}`}
          style={style}
          onClick={(event) => { if (event.detail === 0) reactToTouch(); onActivate(); }}
          aria-label={state === 'listening' || state === 'speaking' ? 'Encerrar conversa por voz com a KLIC' : 'Conversar por voz com a KLIC'}
        >
          {content}
        </button>
      ) : (
        <span className={`klic-plasma klic-plasma--${state}`} style={style} role="img" aria-label={`KLIC: ${stateCopy[state]}`}>
          {content}
        </span>
      )}
      {!compact && showIdentity && (
        <div className="klic-plasma__identity" aria-live="polite">
          <strong>KLIC</strong>
          <span>IA da Clicko Studios</span>
          <small className={`klic-plasma__status klic-plasma__status--${state}`}>{stateCopy[state]}</small>
        </div>
      )}
    </div>
  );
}
