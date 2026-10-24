import { useEffect, useId, useState } from 'react';
import './DashboardImmersiveScene.css';

type DashboardImmersiveSceneProps = { playing: boolean };

/** The official presentation assets are used as luminance masks, never as backgrounds. */
export function DashboardImmersiveScene({ playing }: DashboardImmersiveSceneProps) {
  const id = useId().replace(/:/g, '');
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let cancelled = false;
    // Decode both palettes before playing; a mid-sequence theme change is instant.
    const images = ['escuro', 'claro'].map(theme => {
      const image = new Image();
      image.src = `/branding/logo_${theme}.png`;
      return image.decode();
    });
    Promise.all(images).then(() => { if (!cancelled) setLoaded(true); }).catch(() => {});
    return () => { cancelled = true; };
  }, []);
  return <div className={`cd-space ${playing && loaded ? 'is-playing' : ''}`} aria-hidden="true">
    <div className="cd-space-light" />
    <div className="cd-space-object">
      <div className="cd-brand-symbol">
        <span className="cd-space-depth cd-space-depth-back" />
        <span className="cd-space-depth cd-space-depth-front" />
        <span className="cd-space-face" />
        <span className="cd-space-fallback cd-space-fallback-dark" />
        <span className="cd-space-fallback cd-space-fallback-light" />
      </div>
      <div className="cd-brand-signature">
        {(['dark', 'light'] as const).map(theme => <svg
          key={theme} className={`cd-brand-signature-${theme}`} viewBox="226 455 704 215"
          xmlns="http://www.w3.org/2000/svg" focusable="false"
        >
          <defs>
            <filter id={`${id}-invert-${theme}`} colorInterpolationFilters="sRGB">
              <feColorMatrix type="matrix" values="-1 0 0 0 1  0 -1 0 0 1  0 0 -1 0 1  0 0 0 1 0" />
            </filter>
            <mask id={`${id}-logo-${theme}`} maskUnits="userSpaceOnUse" x="226" y="455" width="704" height="215" style={{ maskType: 'luminance' }}>
              <image href={`/branding/logo_${theme === 'dark' ? 'escuro' : 'claro'}.png`} width="1125" height="1125"
                filter={theme === 'light' ? `url(#${id}-invert-${theme})` : undefined} />
            </mask>
          </defs>
          <rect x="226" y="455" width="704" height="215" fill={theme === 'dark' ? '#fff' : '#000'} mask={`url(#${id}-logo-${theme})`} />
        </svg>)}
      </div>
    </div>
    <div className="cd-space-shadow" />
  </div>;
}
