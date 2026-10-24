import React from 'react';
import { plasmaActivity, plasmaEnergy, type KlicPlasmaState } from '../klic/plasmaState';
import { KlicHologram } from './KlicHologram';
import type { KlicAudioSignal } from '../klic/hologramDynamics';
import type { HologramTheme } from '../klic/hologramModel';
import type { HologramInteractionMode } from '../klic/hologramInteraction';
import type { FaceSurface } from '../klic/hologramRenderer';
import './KlicPlasma.css';
export type { KlicPlasmaState } from '../klic/plasmaState';

const stateCopy:Record<KlicPlasmaState,string>={idle:'Disponível',connecting:'Inicializando voz',listening:'Escutando...',processing:'Processando...',speaking:'Falando...',error:'Conexão interrompida'};
type KlicPlasmaProps={
  state?:KlicPlasmaState;intensity?:number;compact?:boolean;appearance?:'default'|'signature';motionActive?:boolean;
  audioSignal?:React.RefObject<KlicAudioSignal>;hologramTheme?:HologramTheme;showIdentity?:boolean;onActivate?:()=>void;
  particleInteraction?:HologramInteractionMode;
  particleSurface?:FaceSurface;
  interacting?:boolean;responding?:boolean;completionId?:string;scopeKey?:string;
};

/** Keep the public KLIC identity/hit target contract; every size now uses the imported particle face. */
export function KlicPlasma({state='idle',intensity=0,compact=false,appearance='default',motionActive=true,audioSignal,hologramTheme,
  showIdentity=true,onActivate,interacting=false,responding=false,particleInteraction='click',particleSurface='local'}:KlicPlasmaProps) {
  const style={'--klic-energy':plasmaEnergy(intensity).toFixed(3)} as React.CSSProperties;
  const content=<span className="klic-plasma__physical"><KlicHologram active={motionActive} state={state} audioSignal={audioSignal} tone={hologramTheme} compact={compact} interaction={particleInteraction} surface={particleSurface}/></span>;
  return <div data-activity={plasmaActivity(state,responding,interacting)} className={`klic-plasma-wrap ${compact?'klic-plasma-wrap--compact':''} ${appearance==='signature'?'klic-plasma-wrap--signature':''} klic-plasma-wrap--entity`}>
    {onActivate?<button type="button" className={`klic-plasma klic-plasma--${state}`} style={style} onClick={onActivate}
      aria-label={state==='listening'||state==='speaking'?'Encerrar conversa por voz com a KLIC':'Conversar por voz com a KLIC'}>{content}</button>
      :<span className={`klic-plasma klic-plasma--${state}`} style={style} role="img" aria-label={`KLIC: ${stateCopy[state]}`}>{content}</span>}
    {!compact&&showIdentity&&<div className="klic-plasma__identity" aria-live="polite"><strong>KLIC</strong><span>IA da Clicko Studios</span><small className={`klic-plasma__status klic-plasma__status--${state}`}>{stateCopy[state]}</small></div>}
  </div>;
}
