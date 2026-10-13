import React from 'react';
import type { NavigationTab } from '../types';

export type KlicPageDetails = {
  view?: string;
  period?: string;
  filters?: Record<string, string>;
  selected?: { kind: string; id: string };
};
export const klicPageScope = (workspaceId: string, clientId?: string | null) => JSON.stringify([workspaceId, clientId || null]);

type Registration = { module: NavigationTab; scope: string; details: KlicPageDetails; token: symbol } | null;
let activeModule: NavigationTab = 'ai-chat';
let registration: Registration = null;
let snapshot: { module: NavigationTab; registration: Registration } = { module: activeModule, registration };
const listeners = new Set<() => void>();
const notify = () => { snapshot = { module: activeModule, registration }; listeners.forEach(listener => listener()); };
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
const getSnapshot = () => snapshot;

export const klicModuleForPath = (path: string): NavigationTab => ({
  '/dashboard': 'dashboard', '/klic': 'ai-chat', '/clients': 'workspace', '/strategy': 'strategy',
  '/calendar': 'calendar', '/library': 'library', '/analytics': 'analytics',
  '/connected-accounts': 'connected-accounts', '/approvals': 'approvals', '/team': 'team',
  '/automations': 'automations', '/settings': 'settings', '/create': 'create-copy',
  '/subscription': 'subscription',
} as Record<string, NavigationTab>)[path.replace(/\/+$/, '') || '/'] || 'ai-chat';

activeModule = klicModuleForPath(window.location.pathname);
snapshot = { module: activeModule, registration };

export function clearKlicPageDetails() {
  if (!registration) return;
  registration = null;
  notify();
}

export function setKlicActiveModule(module: NavigationTab) {
  if (activeModule === module) return;
  activeModule = module;
  registration = null;
  notify();
}

export function useKlicPageDetails(module: NavigationTab, scope: string, details: KlicPageDetails) {
  const serialized = JSON.stringify(details);
  React.useLayoutEffect(() => {
    const token = Symbol('klic-page');
    if (activeModule === module) {
      registration = { module, scope, details: JSON.parse(serialized) as KlicPageDetails, token };
      notify();
    }
    return () => { if (registration?.token === token) clearKlicPageDetails(); };
  }, [module, scope, serialized]);
}

export function useKlicPageRegistration() { return React.useSyncExternalStore(subscribe, getSnapshot, getSnapshot); }
