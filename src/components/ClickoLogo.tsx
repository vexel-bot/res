import React from 'react';

export const OFFICIAL_CLICKO_LOGO = '/clicko-ai-studios-logo-stacked.png';
export const OFFICIAL_CLICKO_COMPACT_LOGO = '/clicko-ai-studios-logo-compact.png';
export const OFFICIAL_CLICKO_LOGO_BACKGROUND = '#000000';
export const OFFICIAL_CLICKO_LOGO_HAS_SOLID_BLACK_BACKGROUND = true;

type ClickoLogoProps = {
  variant?: 'horizontal' | 'icon';
  loading?: boolean;
  className?: string;
  alt?: string;
  appearance?: 'auto' | 'seamless' | 'badge';
};

export const ClickoLogo: React.FC<ClickoLogoProps> = ({
  variant = 'horizontal',
  loading = false,
  className = '',
  alt = 'Clicko AI Studios',
  appearance = 'auto',
}) => (
  <span
    className={`clicko-logo clicko-logo--${appearance} ${loading ? 'clicko-logo--loading' : ''} ${className}`}
    style={{ backgroundColor: OFFICIAL_CLICKO_LOGO_BACKGROUND }}
  >
    <img
      src={variant === 'icon' ? OFFICIAL_CLICKO_COMPACT_LOGO : OFFICIAL_CLICKO_LOGO}
      width={variant === 'icon' ? 740 : 1774}
      height={variant === 'icon' ? 735 : 887}
      alt={alt}
      draggable={false}
      className="clicko-logo__image"
    />
  </span>
);

export const ClickoLoader: React.FC<{ className?: string }> = ({ className = '' }) => (
  <ClickoLogo loading className={className} alt="Clicko AI Studios carregando" />
);
