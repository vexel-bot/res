import React from 'react';

type KlicSymbolProps = {
  className?: string;
  strokeWidth?: number;
};

export const KlicSymbol: React.FC<KlicSymbolProps> = ({ className }) => (
  <span
    aria-hidden="true"
    className={`${className || ''} grid place-items-center text-[15px] font-normal leading-none`}
    style={{ fontFamily: '"Segoe UI Symbol", sans-serif' }}
  >
    ✧
  </span>
);
