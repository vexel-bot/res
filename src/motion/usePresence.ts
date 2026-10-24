import React from 'react';

/** Retain only the exiting surface, without keeping its controls interactive. */
export function usePresence(open: boolean) {
  const [retained, setRetained] = React.useState(open);
  React.useEffect(() => {
    if (open) {
      setRetained(true);
      return;
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setRetained(false);
      return;
    }
    const duration = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--clicko-motion-fast')) || 140;
    const timer = window.setTimeout(() => setRetained(false), duration);
    return () => window.clearTimeout(timer);
  }, [open]);
  return {
    present: open || retained,
    props: {
      'data-clicko-presence': open ? 'open' : 'closed',
      inert: !open,
      'aria-hidden': !open || undefined,
    },
  };
}
