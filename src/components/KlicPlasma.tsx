import React from 'react';

export type KlicPlasmaState = 'idle' | 'connecting' | 'listening' | 'processing' | 'speaking' | 'error';

const stateCopy: Record<KlicPlasmaState, string> = {
  idle: 'Disponível',
  connecting: 'Inicializando voz',
  listening: 'Ouvindo você',
  processing: 'Organizando a resposta',
  speaking: 'Falando',
  error: 'Conexão interrompida',
};

type KlicPlasmaProps = {
  state?: KlicPlasmaState;
  intensity?: number;
  compact?: boolean;
  showIdentity?: boolean;
  onActivate?: () => void;
};

export function KlicPlasma({ state = 'idle', intensity = 0, compact = false, showIdentity = true, onActivate }: KlicPlasmaProps) {
  const energy = Math.max(0, Math.min(1, intensity));
  const style = { '--klic-energy': energy.toFixed(3) } as React.CSSProperties;
  const content = (
    <>
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
    </>
  );

  return (
    <div className={`klic-plasma-wrap ${compact ? 'klic-plasma-wrap--compact' : ''}`}>
      {onActivate ? (
        <button
          type="button"
          className={`klic-plasma klic-plasma--${state}`}
          style={style}
          onClick={onActivate}
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
