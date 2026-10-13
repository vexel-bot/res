import React from 'react';
import { useKlicClient } from './useKlicClient';
import { KLIC_MODULES } from './contracts';
import type { NavigationTab } from '../types';

const events: Partial<Record<NavigationTab, string>> = { calendar: 'calendar.changed', library: 'library.changed', workspace: 'brand.changed', analytics: 'analytics.changed', approvals: 'approval.changed', 'connected-accounts': 'connection.changed', automations: 'automation.changed' };
/** Invisible event adapter, mounted only for the permitted application screens. */
export function KlicOperationalBridge({ module }: { module: NavigationTab }) {
  const { request, snapshot, scope } = useKlicClient();
  const revision = JSON.stringify(snapshot);
  const latest = React.useRef(request);
  latest.current = request;
  React.useEffect(() => {
    if (!KLIC_MODULES.includes(module)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      if (document.hidden) return;
      void latest.current('events', module, { event: { type: events[module] || 'operation.changed', revision } }, controller.signal).catch(() => {
        // Failures remain observable on the server; core downtime never blocks the UI.
      });
    }, 750);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [module, revision, scope]);
  return null;
}
