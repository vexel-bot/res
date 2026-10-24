import React from 'react';
import type { ClientOperationRecord } from './clientOperations';

export function useClientOperations(workspaceId: string, userId: string) {
  const [records, setRecords] = React.useState<ClientOperationRecord[]>([]);
  const [loading, setLoading] = React.useState(true);
  const headers = React.useMemo(() => ({ 'Content-Type': 'application/json', 'x-workspace-id': workspaceId, 'x-user-id': userId }), [workspaceId, userId]);

  const refresh = React.useCallback(async () => {
    if (!workspaceId || !userId) return;
    setLoading(true);
    try {
      const response = await fetch('/api/governance/clients', { headers, cache: 'no-store' });
      if (!response.ok) throw new Error('Não foi possível consultar as licenças dos clientes.');
      setRecords(await response.json() as ClientOperationRecord[]);
    } finally { setLoading(false); }
  }, [headers, workspaceId, userId]);

  React.useEffect(() => {
    let live = true;
    if (!workspaceId || !userId) { setRecords([]); setLoading(false); return; }
    setLoading(true);
    fetch('/api/governance/clients', { headers, cache: 'no-store' })
      .then(async response => { if (!response.ok) throw new Error('Falha ao consultar clientes.'); return response.json() as Promise<ClientOperationRecord[]>; })
      .then(value => { if (live) setRecords(value); })
      .catch(() => { if (live) setRecords([]); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [headers, workspaceId, userId]);

  const mutate = React.useCallback(async <T,>(path: string, body: object): Promise<T> => {
    const response = await fetch(`/api/governance${path}`, { method: 'POST', headers, body: JSON.stringify(body) });
    const payload = await response.json().catch(() => ({})) as T & { error?: string };
    if (!response.ok) throw new Error(payload.error || 'Não foi possível concluir a operação.');
    await refresh();
    return payload;
  }, [headers, refresh]);

  const visibleRecords = React.useMemo(() => records.filter(record => record.workspaceId === workspaceId), [records, workspaceId]);
  return { records: visibleRecords, loading, refresh, mutate };
}
