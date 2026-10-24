import React from 'react';
import { useOperations } from '../context/OperationsContext';
import type { SocialPlatform } from '../types';
import { aggregatePoints, buildConnectedDataset } from './analyticsModel';
import { buildAnalyticsDemoDataset } from './analyticsDemo';
import { customPeriodPoints, previousCustomPeriodPoints } from './analyticsWorkbench';
import { createRequestGuard } from '../utils/requestGuard';
import { useKlicClient } from '../klic/useKlicClient';
import { analyticsContext } from '../klic/analyticsContext';
import { providerSnapshotForAccount, type ProviderAnalyticsSnapshot } from './providerSnapshot';

export const dateInput = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
const daysAgo = (days: number) => { const date = new Date(); date.setDate(date.getDate() - days); return dateInput(date); };

/** All sections share one dataset and date window; demonstration never reaches the APIs. */
export function useAnalyticsReport() {
  const klic = useKlicClient('workspace');
  const { activeWorkspace, clients, connectedAccounts, posts, updateConnectedAccount } = useOperations();
  const connected = React.useMemo(() => buildConnectedDataset(connectedAccounts, posts), [connectedAccounts, posts]);
  const demo = React.useMemo(buildAnalyticsDemoDataset, []);
  const [demoMode, setDemo] = React.useState(false);
  const [period, setPeriod] = React.useState(30);
  const [network, setNetwork] = React.useState<SocialPlatform | 'all'>('all');
  const [account, setAccount] = React.useState('all');
  const [client, setClient] = React.useState('all');
  const [compare, setCompare] = React.useState(true);
  const [customStart, setCustomStart] = React.useState(() => daysAgo(29));
  const [customEnd, setCustomEnd] = React.useState(() => daysAgo(0));
  const [manualComparison, setManualComparison] = React.useState(false);
  const [comparisonStart, setComparisonStart] = React.useState(() => daysAgo(59));
  const [comparisonEnd, setComparisonEnd] = React.useState(() => daysAgo(30));
  const [refreshing, setRefreshing] = React.useState(false);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);
  const [analysis, setAnalysis] = React.useState<string | null>(null);
  const [analyzing, setAnalyzing] = React.useState(false);
  const requestVersion = React.useRef(0);
  const busy = React.useRef(false);
  const workspaceRef = React.useRef(activeWorkspace.id);
  workspaceRef.current = activeWorkspace.id;
  const syncGuard = React.useRef(createRequestGuard());
  const dataset = demoMode ? demo : connected;
  const start = period ? daysAgo(period - 1) : customStart;
  const end = period ? daysAgo(0) : customEnd;
  const validDates = Boolean(start && end && start <= end && (!compare || !manualComparison || (comparisonStart && comparisonEnd && comparisonStart <= comparisonEnd)));
  const networks = React.useMemo(() => dataset?.networks.filter(row => (network === 'all' || row.network === network) && (account === 'all' || row.accountId === account)
    && (demoMode || client === 'all' || connectedAccounts.find(connection => connection.id === row.accountId)?.clientId === client)) || [], [dataset, network, account, client, demoMode, connectedAccounts]);
  const points = React.useMemo(() => validDates ? customPeriodPoints(networks, start, end) : [], [networks, start, end, validDates]);
  const previous = React.useMemo(() => !validDates || !compare ? [] : manualComparison ? customPeriodPoints(networks, comparisonStart, comparisonEnd) : previousCustomPeriodPoints(networks, start, end), [networks, start, end, compare, manualComparison, comparisonStart, comparisonEnd, validDates]);
  const totals = React.useMemo(() => aggregatePoints(points), [points]);
  const priorTotals = React.useMemo(() => aggregatePoints(previous), [previous]);
  const rows = React.useMemo(() => networks.map(row => ({ ...row, current: aggregatePoints(validDates ? customPeriodPoints([row], start, end) : []), previous: aggregatePoints(!validDates || !compare ? [] : manualComparison ? customPeriodPoints([row], comparisonStart, comparisonEnd) : previousCustomPeriodPoints([row], start, end)) })), [networks, start, end, validDates, compare, manualComparison, comparisonStart, comparisonEnd]);
  const contents = React.useMemo(() => validDates ? networks.flatMap(row => row.contents.map(content => ({ ...content, accountId: row.accountId }))).filter(content => {
    const time = new Date(content.date).getTime();
    return content.status === 'published' && time >= new Date(`${start}T00:00:00`).getTime() && time <= new Date(`${end}T23:59:59.999`).getTime();
  }) : [], [networks, start, end, validDates]);
  const changeSource = (enabled: boolean) => { setDemo(enabled); setNetwork('all'); setAccount('all'); setClient('all'); setAnalysis(null); setRefreshError(null); requestVersion.current++; };
  React.useEffect(() => { requestVersion.current++; setAnalysis(null); setAnalyzing(false); }, [demoMode, network, account, client, start, end, activeWorkspace.id, compare, manualComparison, comparisonStart, comparisonEnd]);
  React.useEffect(() => { syncGuard.current.invalidate(); busy.current = false; setRefreshing(false); setRefreshError(null); setDemo(false); setNetwork('all'); setAccount('all'); setClient('all'); }, [activeWorkspace.id]);
  React.useEffect(() => () => { requestVersion.current++; syncGuard.current.invalidate(); }, []);

  React.useEffect(() => {
    const workspaceId = activeWorkspace.id;
    let active = true;
    void fetch('/api/integrations/analytics/snapshots', { credentials: 'same-origin', headers: { 'x-workspace-id': workspaceId } })
      .then(async response => response.ok ? response.json() as Promise<{ snapshots: ProviderAnalyticsSnapshot[] }> : { snapshots: [] })
      .then(data => {
        if (!active || workspaceRef.current !== workspaceId) return;
        const latest = new Map<string, ProviderAnalyticsSnapshot>();
        for (const item of (data.snapshots || []).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))) if (!latest.has(item.connectionId)) latest.set(item.connectionId, item);
        latest.forEach(item => updateConnectedAccount(item.connectionId, { analytics: providerSnapshotForAccount(item), lastSync: item.updatedAt }));
      }).catch(() => undefined);
    return () => { active = false; };
  }, [activeWorkspace.id, updateConnectedAccount]);

  const refresh = React.useCallback(async () => {
    if (demoMode || busy.current) return;
    const isCurrent = syncGuard.current.begin(activeWorkspace.id, () => workspaceRef.current);
    busy.current = true; setRefreshing(true); setRefreshError(null);
    const active = connectedAccounts.filter(item => item.connected && item.capabilities?.canReadAnalytics === true && networks.some(row => row.accountId === item.id));
    try {
      const results = await Promise.allSettled(active.map(async item => {
        updateConnectedAccount(item.id, { connectionStatus: 'syncing' });
        try {
          const response = await fetch(`/api/integrations/connections/${encodeURIComponent(item.id)}/analytics?from=${encodeURIComponent(start)}&to=${encodeURIComponent(end)}`, { credentials: 'same-origin', headers: { 'x-workspace-id': activeWorkspace.id } });
          const data = await response.json();
          if (!isCurrent()) return;
          if (!response.ok) throw new Error(data.error || 'Falha na sincronização.');
          if (!data.analytics?.metrics) throw new Error('A fonte não retornou métricas. Os dados anteriores foram preservados.');
          const snapshot = providerSnapshotForAccount({ connectionId: item.id, provider: item.platform, from: data.analytics.from, to: data.analytics.to,
            metrics: data.analytics.metrics, updatedAt: new Date().toISOString() });
          updateConnectedAccount(item.id, { connectionStatus: 'synced', lastSync: snapshot.updatedAt, analytics: snapshot, lastError: undefined });
        } catch (error) {
          if (!isCurrent()) return;
          updateConnectedAccount(item.id, { connectionStatus: item.connectionStatus === 'syncing' ? 'connected' : item.connectionStatus, lastError: error instanceof Error ? error.message : 'Falha na sincronização.' });
          throw error;
        }
      }));
      const failed = results.filter(result => result.status === 'rejected').length;
      if (failed && isCurrent()) setRefreshError(`Não foi possível atualizar ${failed} conexão(ões). Os últimos dados disponíveis foram preservados.`);
    } finally { if (isCurrent()) { busy.current = false; setRefreshing(false); } }
  }, [demoMode, connectedAccounts, networks, activeWorkspace.id, updateConnectedAccount, start, end]);
  const refreshRef = React.useRef(refresh);
  refreshRef.current = refresh;
  const interval = Math.min(...connectedAccounts.flatMap(item => item.analytics?.refreshIntervalMinutes ? [Math.max(5, item.analytics.refreshIntervalMinutes)] : []));
  React.useEffect(() => {
    if (demoMode || !Number.isFinite(interval)) return;
    const timer = window.setInterval(() => { if (document.visibilityState === 'visible') void refreshRef.current(); }, interval * 60_000);
    return () => window.clearInterval(timer);
  }, [demoMode, interval, activeWorkspace.id]);
  const askKlic = async () => {
    if (demoMode || !points.length || analyzing) return;
    const version = requestVersion.current;
    setAnalyzing(true);
    try {
      const result = await klic.request<{ insight: string }>('analyze', 'analytics', { records: { analytics: analyticsContext(activeWorkspace.id, points, previous, start, end) } });
      if (version === requestVersion.current) setAnalysis(result.insight || 'Dados insuficientes para uma análise.');
    } catch { if (version === requestVersion.current) setAnalysis('Não foi possível consultar a KLIC agora.'); }
    finally { if (version === requestVersion.current) setAnalyzing(false); }
  };
  return { dataset, connected, demoMode, changeSource, period, setPeriod, network, setNetwork, account, setAccount, client, setClient, clients, connectedAccounts, compare, setCompare, customStart, setCustomStart, customEnd, setCustomEnd, manualComparison, setManualComparison, comparisonStart, setComparisonStart, comparisonEnd, setComparisonEnd, start, end, validDates, networks, points, previous, totals, priorTotals, rows, contents, refreshing, refreshError, refresh, analysis, analyzing, askKlic };
}
