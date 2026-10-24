import { useEffect } from 'react';

/** Keep fixed chat panels and dialogs within the viewport above a mobile keyboard. */
export function useVisualViewport() {
  useEffect(() => {
    const viewport = window.visualViewport;
    const root = document.documentElement;
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        // Pinch zoom is user-controlled; do not resize the interface while zooming.
        if (viewport && Math.abs(viewport.scale - 1) > .05) return;
        const height = viewport?.height ?? window.innerHeight;
        const top = viewport?.offsetTop ?? 0;
        root.style.setProperty('--clicko-viewport-height', `${height}px`);
        root.style.setProperty('--clicko-viewport-top', `${top}px`);
        root.style.setProperty('--clicko-keyboard-inset', `${Math.max(0, window.innerHeight - height - top)}px`);
      });
    };
    measure();
    window.addEventListener('resize', measure);
    viewport?.addEventListener('resize', measure);
    viewport?.addEventListener('scroll', measure);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', measure);
      viewport?.removeEventListener('resize', measure);
      viewport?.removeEventListener('scroll', measure);
      ['--clicko-viewport-height', '--clicko-viewport-top', '--clicko-keyboard-inset'].forEach(name => root.style.removeProperty(name));
    };
  }, []);
}
