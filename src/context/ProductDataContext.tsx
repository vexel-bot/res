import React from 'react';
import { apiFetch, setStudioScope } from '../api';
import type { AssetRecord } from '../api/productApi';
import { useGovernance } from './GovernanceContext';
import { useOperations } from './OperationsContext';

type Session = {
  user: { id: string; name: string };
  workspace: { id: string; name: string; brandProfile?: { targetAudience?: string[] } };
  assets: AssetRecord[];
  posts: Array<{ id: string; title: string; copy: string; objective?: string; campaignId?: string }>;
};
type StudioData = {
  status: 'loading' | 'ready' | 'refreshing' | 'error' | 'guest';
  error?: string;
  bootstrap?: { user: Session['user'] };
  activeWorkspace?: Session['workspace'];
  snapshot?: Pick<Session, 'assets' | 'posts'>;
  refresh: () => Promise<void>;
};
const Context = React.createContext<StudioData | null>(null);

/** Adapter for the imported Studios. Existing Clicko providers remain in charge. */
export function ProductDataProvider({ children, module }: { children: React.ReactNode; module: 'create-image' | 'create-video' }) {
  const { currentUser, activeAccount } = useGovernance();
  const { activeClient } = useOperations();
  const [session, setSession] = React.useState<Session>();
  const [error, setError] = React.useState<string>();
  const [attempt, setAttempt] = React.useState(0);
  const scope = JSON.stringify([currentUser?.id, activeAccount.workspaceId, activeClient?.id, module]);
  const [loadedScope, setLoadedScope] = React.useState<string>();
  React.useLayoutEffect(() => {
    setStudioScope({ module, clientId: activeClient?.id || null });
    return () => setStudioScope(undefined);
  }, [module, scope]);
  React.useEffect(() => {
    const controller = new AbortController();
    setSession(undefined); setError(undefined); setLoadedScope(undefined);
    void apiFetch<Session>('/api/v1/studios/v1/bridge/session', { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) { setSession(value); setLoadedScope(scope); } })
      .catch(failure => { if (!controller.signal.aborted) { setError(failure instanceof Error ? failure.message : 'Não foi possível abrir os Studios.'); setLoadedScope(scope); } });
    return () => controller.abort();
  }, [scope, attempt]);
  const value: StudioData = {
    status: !currentUser ? 'guest' : loadedScope !== scope ? 'loading' : error ? 'error' : 'ready',
    error: loadedScope === scope ? error : undefined,
    bootstrap: loadedScope === scope && session ? { user: session.user } : undefined,
    activeWorkspace: loadedScope === scope ? session?.workspace : undefined,
    snapshot: loadedScope === scope && session ? { assets: session.assets, posts: session.posts } : undefined,
    refresh: async () => { setAttempt(value => value + 1); },
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useProductData() {
  const value = React.useContext(Context);
  if (!value) throw new Error('Studio context unavailable');
  return value;
}
