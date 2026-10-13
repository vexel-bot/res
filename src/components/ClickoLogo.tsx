import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { appearance as brand, type ThemeMode } from '../theme/appearance';

export const OFFICIAL_CLICKO_LOGO = brand.authenticationAssets.expanded;
export const OFFICIAL_CLICKO_COMPACT_LOGO = brand.authenticationAssets.compact;
export const OFFICIAL_CLICKO_LOGO_BACKGROUND = '#000000';

type ClickoLogoProps = {
  variant?: 'horizontal' | 'icon';
  className?: string;
  alt?: string;
  appearance?: 'auto' | 'seamless' | 'badge';
  assetSrc?: string;
  authentication?: boolean;
};

export const ClickoLogo: React.FC<ClickoLogoProps> = ({
  variant = 'horizontal',
  className = '',
  alt = 'Clicko Studio',
  appearance = 'auto',
  assetSrc,
  authentication = false,
}) => {
  const { theme } = useTheme();
  const [baseTheme] = React.useState<ThemeMode>(theme);
  const overlayTheme = baseTheme === 'dark' ? 'light' : 'dark';
  const themed = !authentication && !assetSrc;
  const assetVariant = variant === 'icon' ? 'compact' : 'expanded';
  return (
  <span
    className={`clicko-logo clicko-logo--${appearance} clicko-logo--${variant} ${className}`}
    style={{ backgroundColor: themed && theme === 'light' ? '#ffffff' : OFFICIAL_CLICKO_LOGO_BACKGROUND }}
    data-logo-theme={themed ? theme : undefined}
    data-logo-base={themed ? baseTheme : undefined}
    role={themed ? 'img' : undefined}
    aria-label={themed ? alt : undefined}
  >
    <img
      src={themed ? brand.assets[baseTheme][assetVariant] : assetSrc || (variant === 'icon' ? OFFICIAL_CLICKO_COMPACT_LOGO : OFFICIAL_CLICKO_LOGO)}
      width={themed || assetSrc ? 1125 : variant === 'icon' ? 740 : 1774}
      height={themed || assetSrc ? 1125 : variant === 'icon' ? 735 : 887}
      alt={themed ? '' : alt}
      draggable={false}
      className={`clicko-logo__image ${themed || assetSrc ? 'clicko-logo__image--sidebar-asset' : ''}`}
    />
    {themed && <img src={brand.assets[overlayTheme][assetVariant]} width={1125} height={1125} alt="" draggable={false} className="clicko-logo__image clicko-logo__image--sidebar-asset clicko-logo__theme-overlay" />}
  </span>
  );
};
