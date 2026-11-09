import React from 'react';
import { apiFetch, APIError } from '../../api';
import type { CraftDocument } from '../craft/craftApi';

type Model = { id: string; name?: string; supported_voices?: string[]; supported_durations?: number[] };
type Job = { id: string; status: string; assetId?: string; estimatedCostUsd?: number; providerReportedCostUsd?: number; errorCode?: string; requiresReconciliation?: boolean };
type Pending = { key: string; body: Record<string, unknown> };
const terminal = (status: string) => ['succeeded', 'failed', 'cancelled'].includes(status);
const store = (key: string, value: unknown) => { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Recovery is optional; server identity remains authoritative. */ } };
export function OpenRouterMediaPanel({ doc, disabled, onComplete, onBusyChange }: { doc: CraftDocument; disabled: boolean; onComplete: (doc: CraftDocument) => void; onBusyChange: (busy: boolean) => void }) {
  const base = `/api/v1/studios/v1/video/documents/${doc.documentId}/openrouter-media`;
  const storageKey = `clicko:media-generation:${doc.workspaceId}:${doc.documentId}`;
  const [connections, setConnections] = React.useState<{ id: string; label: string }[]>([]);
  const [connection, setConnection] = React.useState('');
  const [catalog, setCatalog] = React.useState<{ videoModels: Model[]; speechModels: Model[]; balanceUsd: number }>();
  const [kind, setKind] = React.useState<'video' | 'speech'>('video');
  const [model, setModel] = React.useState('');
  const [voice, setVoice] = React.useState('');
  const [duration, setDuration] = React.useState(6);
  const [text, setText] = React.useState('');
  const [budget, setBudget] = React.useState(0);
  const [job, setJob] = React.useState<Job>();
  const [pending, setPending] = React.useState<Pending>();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');
  const onCompleteRef = React.useRef(onComplete); onCompleteRef.current = onComplete;
  React.useEffect(() => { onBusyChange(busy || Boolean(pending) || Boolean(job && (!terminal(job.status) || job.requiresReconciliation))); }, [busy, pending, job?.status, job?.requiresReconciliation, onBusyChange]);
  React.useEffect(() => {
    let alive = true;
    try { const saved = JSON.parse(localStorage.getItem(storageKey) || 'null'); if (saved?.pending) setPending(saved.pending); if (saved?.job) setJob(saved.job); } catch { /* optional local recovery */ }
    void apiFetch<{ connections: { id: string; label: string; provider: string; config?: { enabled?: boolean } }[] }>(`/api/v1/studios/v1/craft/llm-connections?workspace_id=${doc.workspaceId}`).then(value => {
      if (!alive) return;
      const available = value.connections.filter(c => c.provider === 'openrouter' && c.config?.enabled);
      setConnections(available); setConnection(available[0]?.id || '');
    }).catch(e => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [storageKey, doc.workspaceId]);
  React.useEffect(() => {
    if (!connection) return;
    const controller = new AbortController(); setCatalog(undefined);
    void apiFetch<NonNullable<typeof catalog>>(`/api/v1/studios/v1/video/openrouter-models?workspace_id=${doc.workspaceId}&connection_id=${connection}`, { signal: controller.signal }).then(value => {
      setCatalog(value); setBudget(current => current || Math.floor(value.balanceUsd * 50) / 100);
    }).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [connection, doc.workspaceId]);
  const models = kind === 'video' ? catalog?.videoModels : catalog?.speechModels;
  const chosen = models?.find(m => m.id === model);
  React.useEffect(() => { setModel(models?.[0]?.id || ''); }, [models]);
  React.useEffect(() => { setVoice(chosen?.supported_voices?.[0] || ''); setDuration(chosen?.supported_durations?.includes(6) ? 6 : chosen?.supported_durations?.[0] || 6); }, [chosen]);
  React.useEffect(() => {
    if (!job || terminal(job.status)) return;
    let alive = true; let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await apiFetch<Job>(`${base}/${job!.id}`);
        if (!alive) return;
        setJob(next); store(storageKey, { job: next });
        if (next.status === 'succeeded') {
          const fresh = await apiFetch<CraftDocument>(`/api/v1/studios/v1/documents/${doc.documentId}`);
          if (alive) onCompleteRef.current(fresh);
        }
        if (next.errorCode) setError(next.errorCode);
        if (terminal(next.status)) return;
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Não foi possível consultar o pedido.'); }
      if (alive) timer = setTimeout(poll, 4000);
    }
    void poll(); return () => { alive = false; clearTimeout(timer); };
  }, [job?.id, base, storageKey, doc.documentId]);
  async function submit() {
    setBusy(true); setError('');
    const request = pending || { key: crypto.randomUUID(), body: { connectionId: connection, kind, model, ...(kind === 'video' ? { prompt: text, durationSeconds: duration, resolution: '720p', aspectRatio: '16:9', generateAudio: false } : { text, voice }), productionId: doc.documentId, maxCostUsd: budget } };
    setPending(request); store(storageKey, { pending: request });
    try {
      const next = await apiFetch<Job>(base, { method: 'POST', headers: { 'Idempotency-Key': request.key }, body: JSON.stringify(request.body) });
      setJob(next); setPending(undefined); store(storageKey, { job: next });
      if (next.status === 'succeeded') {
        const fresh = await apiFetch<CraftDocument>(`/api/v1/studios/v1/documents/${doc.documentId}`);
        onCompleteRef.current(fresh);
      }
    } catch (e) {
      const detail = e instanceof APIError ? e.detail as { canDiscardPending?: boolean } | undefined : undefined;
      if (detail?.canDiscardPending) { setPending(undefined); store(storageKey, { job }); }
      setError(e instanceof Error ? e.message : 'Confira o pedido antes de tentar novamente.');
    }
    finally { setBusy(false); }
  }
  const locked = disabled || busy || Boolean(job && (!terminal(job.status) || job.requiresReconciliation));
  return <details className="studio-fold cv-media-generation"><summary>Gerar cenas e narração</summary>
    <p>Crie os materiais deste projeto com sua conexão OpenRouter. Materiais concluídos ficam disponíveis na mídia do editor.</p>
    <fieldset disabled={locked || Boolean(pending)}>
      <label>Conexão<select value={connection} onChange={e => setConnection(e.target.value)}>{connections.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}</select></label>
      <label>Material<select value={kind} onChange={e => setKind(e.target.value as typeof kind)}><option value="video">Cena em vídeo</option><option value="speech">Narração</option></select></label>
      <label>Modelo<select value={model} onChange={e => setModel(e.target.value)}>{models?.map(m => <option key={m.id} value={m.id}>{m.name || m.id}</option>)}</select></label>
      {kind === 'video' ? <label>Duração (segundos)<select value={duration} onChange={e => setDuration(Number(e.target.value))}>{(chosen?.supported_durations || [6]).map(n => <option key={n} value={n}>{n}</option>)}</select></label> : <label>Voz<select value={voice} onChange={e => setVoice(e.target.value)}>{chosen?.supported_voices?.map(v => <option key={v} value={v}>{v}</option>)}</select></label>}
      <label>{kind === 'video' ? 'Descreva a cena' : 'Texto da narração'}<textarea value={text} onChange={e => setText(e.target.value)} rows={4}/></label>
      <label>Orçamento desta produção (US$)<input type="number" min="0.01" step="0.01" value={budget} onChange={e => setBudget(Number(e.target.value))}/></label>
      {catalog && <small>Saldo consultado: US$ {catalog.balanceUsd.toFixed(2)}. O orçamento é compartilhado entre os materiais deste projeto.</small>}
    </fieldset>
    <button type="button" disabled={locked || (!pending && (!connection || !model || !text.trim() || budget <= 0 || (kind === 'speech' && !voice)))} onClick={() => void submit()}>{busy ? 'Enviando…' : pending ? 'Verificar pedido pendente' : 'Gerar material'}</button>
    {job && <p role="status">{job.status === 'succeeded' ? 'Material adicionado ao projeto.' : job.status === 'failed' ? 'A geração falhou.' : 'Pedido em processamento…'} {job.providerReportedCostUsd !== undefined && `Custo: US$ ${job.providerReportedCostUsd.toFixed(4)}`}</p>}
    {error && <p role="alert">{error}</p>}
    {job?.requiresReconciliation && terminal(job.status) && <p role="alert">O resultado da cobrança deste pedido ainda precisa ser conferido. Uma nova geração permanece bloqueada para evitar cobrança duplicada.</p>}
  </details>;
}
