import React from 'react';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import { KLIC_MODULES, type KlicEnvelope, type KlicRecord } from './contracts';
import type { NavigationTab } from '../types';
import { requestKlicJson } from './transport';
import { klicPageScope, useKlicPageRegistration } from './pageContext';
import type { KlicPageContext } from './contracts';

/** Bridge to existing browser stores. No media, tokens or account secrets are transmitted. */
export function useKlicClient(level: 'client' | 'workspace' = 'client') {
  const operations = useOperations();
  const page = useKlicPageRegistration();
  const { currentUser, activeAccount, canAccess } = useGovernance();
  const { activeWorkspace, activeClient, posts, assets, clients, campaigns } = operations;
  const workspaceId = activeWorkspace.id;
  const clientId = level === 'workspace' ? null : activeClient?.id || null;
  const userId = currentUser?.id || '';
  const scope = JSON.stringify([workspaceId, userId, clientId]);
  const pageContext = React.useMemo<KlicPageContext>(() => ({
    module: KLIC_MODULES.includes(page.module) && canAccess(page.module) ? page.module : 'ai-chat',
    workspaceId,
    clientId,
    details: KLIC_MODULES.includes(page.module) && canAccess(page.module)
      && page.registration?.module === page.module && page.registration.scope === klicPageScope(workspaceId, clientId)
      ? page.registration.details : {},
  }), [page, workspaceId, clientId, canAccess]);
  const currentScope = React.useRef(scope);
  currentScope.current = scope;
  const mounted = React.useRef(true);
  React.useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const snapshot = React.useMemo<KlicEnvelope>(() => {
    const base = { workspaceId, clientId };
    const selected = (record: { workspaceId?: string; clientId?: string }) => record.workspaceId === workspaceId && (record.clientId || null) === clientId;
    const records: KlicEnvelope['records'] = {};
    const allowedClient = !clientId || currentUser?.role === 'master' || currentUser?.scope?.allClients || currentUser?.scope?.clientIds.includes(clientId);
    if (allowedClient) {
      if (clientId && activeClient?.workspaceId === workspaceId && activeClient.access?.view !== false) {
        records.brand = [{
          ...base, id: activeClient.id, name: activeClient.name, segment: activeClient.segment,
          products: activeClient.products, audience: activeClient.audience, positioning: activeClient.positioning,
          toneOfVoice: activeClient.toneOfVoice, objectives: activeClient.currentObjective,
          differentiators: activeClient.differentiators, visualIdentity: activeClient.visualIdentity,
          brandColors: activeClient.brandColors?.join(', '), typography: activeClient.typography,
          visualReferences: activeClient.visualReferences, competitors: activeClient.competitors,
          requiredWords: activeClient.keywords, forbiddenWords: activeClient.avoidTopics,
        }];
        records.clients = clients.filter(client => client.workspaceId === workspaceId && client.id === clientId && client.access?.view !== false).map(client => ({ ...base, id: client.id, name: client.name, segment: client.segment, currentObjective: client.currentObjective, positioning: client.positioning, status: client.status }));
      }
      if (canAccess('calendar')) records.calendar = posts.filter(selected).slice(-80).map(({ id, title, status, scheduledAt, createdAt, platform, objective, campaignId }) => ({ ...base, id, title, status, scheduledAt, createdAt, platform, objective, campaignId }));
      if (canAccess('strategy')) records.strategy = campaigns.filter(selected).slice(-40).map(({ id, name, objective, status, startDate, endDate }) => ({ ...base, id, name, objective, status, startDate, endDate }));
      if (canAccess('library')) records.library = assets.filter(selected).filter(asset => !['image', 'video', 'upload'].includes(asset.type)).slice(-40).map(({ id, title, type, description, createdAt, updatedAt }) => ({ ...base, id, title, type, description, createdAt, updatedAt }));
    }
    return { workspaceId, userId, clientId, source: 'browser-local', records };
  }, [workspaceId, clientId, userId, currentUser?.role, currentUser?.scope, activeClient, clients, posts, assets, campaigns, canAccess]);

  const request = React.useCallback(async <T,>(endpoint: string, source: NavigationTab, payload: Record<string, unknown> = {}, signal?: AbortSignal): Promise<T> => {
    if (!KLIC_MODULES.includes(source) || !canAccess(source) || !userId || activeAccount.workspaceId !== workspaceId) throw new Error('Contexto da KLIC indisponível para este perfil.');
    if (clientId && activeClient?.access?.view === false) throw new Error('Este cliente não está disponível para consulta.');
    const requestScope = scope;
    const { records: extraRecords, ...extra } = payload;
    const context = { ...snapshot, records: { ...snapshot.records, ...(extraRecords as Partial<Record<string, KlicRecord[]>> || {}) } };
    const data = await requestKlicJson<T>('/api/klic/' + endpoint, {
      method: 'POST', signal, credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...extra, workspaceId, clientId, source, pageContext: { ...pageContext, module: source }, context }),
    }, endpoint === 'conversations/transcribe' ? 60000 : endpoint === 'conversations/cancel' ? 5000 : 30000);
    if (!mounted.current || currentScope.current !== requestScope) throw new DOMException('O contexto ativo mudou.', 'AbortError');
    return data as T;
  }, [scope, snapshot, workspaceId, clientId, userId, activeAccount.workspaceId, activeClient?.access?.view, canAccess, pageContext]);
  return { request, snapshot, scope, workspaceId, userId, clientId, pageContext };
}
