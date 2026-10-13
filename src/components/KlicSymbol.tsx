import React from 'react';
import './KlicSymbol.css';

type KlicSymbolProps = React.HTMLAttributes<HTMLSpanElement> & {
  size?: number | string;
  strokeWidth?: number;
};

/** Static KLIC identity. Interactive plasma and voice UI use KlicPlasma instead. */
export const KlicSymbol: React.FC<KlicSymbolProps> = ({ className = '', size, strokeWidth: _strokeWidth, style, ...props }) => (
  <span
    {...props}
    aria-hidden="true"
    className={`klic-symbol ${className}`.trim()}
    style={{ flex: 'none', ...style, ...(size !== undefined ? { width: size, height: size } : {}) }}
  />
);
