import React from 'react';
import { createPortal } from 'react-dom';
import { useTheme } from '../context/ThemeContext';
import { mountKlicHologram, type FaceSurface } from '../klic/hologramRenderer';
import { SILENT_AUDIO, type KlicAudioSignal } from '../klic/hologramDynamics';
import type { KlicPlasmaState } from '../klic/plasmaState';
import type { HologramTheme } from '../klic/hologramModel';
import type { HologramInteractionMode } from '../klic/hologramInteraction';
import './KlicHologram.css';

/** Presentation-only face; communication actions belong to the existing chat controls. */
export function KlicHologram({ active = true, state = 'idle', audioSignal, tone, compact=false, interaction='click',surface='local' }: {
  active?:boolean; state?:KlicPlasmaState; audioSignal?:React.RefObject<KlicAudioSignal>; tone?:HologramTheme;compact?:boolean;interaction?:HologramInteractionMode;surface?:FaceSurface;
}) {
  const { theme: selectedTheme } = useTheme();
  const theme = tone || selectedTheme;
  const host = React.useRef<HTMLSpanElement>(null);
  const canvas = React.useRef<HTMLCanvasElement>(null);
  const controller = React.useRef<ReturnType<typeof mountKlicHologram> | null>(null);
  const initialTheme = React.useRef(theme);
  const visible = React.useRef(active);
  const signal = React.useRef(audioSignal); signal.current = audioSignal;
  const initialState = React.useRef(state);
  const interactionMode=React.useRef(interaction);
  React.useLayoutEffect(()=>{
    interactionMode.current=interaction;controller.current?.setInteraction(interaction);
  },[interaction]);
  React.useLayoutEffect(() => {
    initialState.current = state;
    controller.current?.setState(state);
  }, [state]);
  React.useLayoutEffect(() => {
    initialTheme.current = theme;
    controller.current?.setTheme(theme);
  }, [theme]);
  React.useLayoutEffect(() => {
    visible.current = active;
    controller.current?.setActive(active);
  }, [active]);
  React.useEffect(() => {
    if (!host.current || !canvas.current) return;
    // Transparent compositing preserves the existing light theme; on the black KLIC
    // stage it matches the standalone renderer's #000 background without a square.
    const instance = mountKlicHologram(host.current, canvas.current, initialTheme.current, {
      signal: () => signal.current?.current || SILENT_AUDIO, background: 'transparent',compact,interaction:interactionMode.current,surface,
    });
    instance.setActive(visible.current);
    instance.setState(initialState.current);
    controller.current = instance;
    return () => { instance.dispose(); controller.current = null; };
  }, [surface]);
  const drawing=<canvas ref={canvas} className={`klic-hologram__canvas${surface==='viewport'?' klic-hologram__canvas--viewport':''}`} hidden={surface==='viewport'&&!active} data-active={active?'true':'false'} aria-hidden="true" />;
  return <span ref={host} className="klic-hologram" data-active={active ? 'true' : 'false'} data-detail={compact?'compact':'full'} data-surface={surface} data-interaction={interaction} data-face-source="ai-studios-novo" aria-hidden="true">
    {surface==='viewport'?createPortal(drawing,document.body):drawing}
  </span>;
}
