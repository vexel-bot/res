import React from 'react';
import { ArrowRight, Check, FileText, MessageCircle, Paperclip, ShieldCheck } from 'lucide-react';
import { ClickoLogo } from './ClickoLogo';
import { ClickoLoader } from './ClickoLoader';
import './ClientPortalView.css';

type PortalData = { client: { name: string; sharedSummary: string; portalRequests: Array<{ id: string; title: string; detail: string; status: 'pending' | 'approved'; createdAt: string }>; portalComments: Array<{ id: string; message: string; createdAt: string }>; portalDocuments: Array<{ id: string; name: string; uploadedAt: string }> } };

export function ClientPortalView() {
  const [token] = React.useState(() => {
    const fromUrl = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token') || '';
    if (fromUrl) { sessionStorage.setItem('clicko:client-portal-token', fromUrl); window.history.replaceState({}, '', '/client-portal'); }
    return fromUrl || sessionStorage.getItem('clicko:client-portal-token') || '';
  });
  const [data, setData] = React.useState<PortalData | null>(null);
  const [error, setError] = React.useState('');
  const [comment, setComment] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [initialLoading, setInitialLoading] = React.useState(Boolean(token));
  const headers = React.useMemo(() => ({ 'Content-Type': 'application/json', 'x-client-portal-token': token }), [token]);
  const refresh = React.useCallback(async () => {
    if (!token) { setError('O link do convite está incompleto. Solicite outro à equipe responsável.'); return; }
    try {
      const response = await fetch('/api/governance/client-portal', { headers, cache: 'no-store' });
      if (!response.ok) throw new Error('Convite inválido ou expirado. Solicite um novo link.');
      setData(await response.json() as PortalData); setError('');
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Portal indisponível.'); }
    finally { setInitialLoading(false); }
  }, [headers, token]);
  React.useEffect(() => { void refresh(); }, [refresh]);
  const post = async (path: string, body: object) => {
    setBusy(true); setError('');
    try {
      const response = await fetch(`/api/governance/client-portal${path}`, { method: 'POST', headers, body: JSON.stringify(body) });
      if (!response.ok) { const payload = await response.json().catch(() => ({})) as { error?: string }; throw new Error(payload.error || 'Não foi possível concluir a ação.'); }
      await refresh();
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Não foi possível concluir a ação.'); }
    finally { setBusy(false); }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    if (file.size > 2_000_000 || !['application/pdf', 'image/jpeg', 'image/png', 'image/webp'].includes(file.type)) { setError('Envie um PDF, JPG, PNG ou WebP de até 2 MB.'); return; }
    const reader = new FileReader();
    reader.onload = () => { const result = String(reader.result || ''); void post('/documents', { name: file.name, mime: file.type, data: result.split(',')[1] || '' }); };
    reader.onerror = () => setError('Não foi possível ler o documento.');
    reader.readAsDataURL(file);
  };
  if (initialLoading && !data) return <main className="cx-portal"><ClickoLoader context="page" size="large" tone="dark" label="Carregando portal do cliente" /></main>;
  return <main className="cx-portal"><div className="cx-portal-shell"><header><ClickoLogo appearance="seamless" className="cx-portal-logo" /><span><ShieldCheck /> Portal do cliente</span></header><section className="cx-portal-intro"><span className="cx-portal-kicker">Colaboração limitada</span><h1>{data?.client.name || 'Portal do cliente'}</h1><p>{data?.client.sharedSummary || 'Acompanhe somente as informações que a equipe compartilhou com você.'}</p><small>Este acesso não inclui custos, automações, integrações, exportações ou administração de uma operação.</small></section>{error && <p className="cx-portal-error" role="alert">{error}</p>}{data && <div className="cx-portal-grid"><section><div className="cx-portal-heading"><h2>Solicitações</h2><span>{data.client.portalRequests.length}</span></div>{data.client.portalRequests.length ? data.client.portalRequests.map(request => <article key={request.id} className="cx-portal-card"><strong>{request.title}</strong><p>{request.detail}</p><small>{request.status === 'approved' ? 'Aprovada' : 'Aguardando sua resposta'}</small>{request.status === 'pending' && <button disabled={busy} onClick={() => void post(`/requests/${encodeURIComponent(request.id)}/approve`, {})}>{busy ? <ClickoLoader size="tiny" tone="dark" label="Aprovando solicitação" /> : <Check />} Aprovar solicitação</button>}</article>) : <p className="cx-portal-empty">Nenhuma solicitação compartilhada no momento.</p>}</section><section><div className="cx-portal-heading"><h2>Documentos</h2><Paperclip /></div><p className="cx-portal-copy">Envie os arquivos pedidos pela equipe. Máximo de 2 MB por arquivo.</p><label className="cx-portal-upload">{busy ? <ClickoLoader size="tiny" tone="dark" label="Enviando documento" /> : <Paperclip />} Selecionar documento<input type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" disabled={busy} onChange={event => { void upload(event.target.files?.[0]); event.target.value = ''; }} /></label>{data.client.portalDocuments.map(document => <div className="cx-portal-document" key={document.id}><FileText /> <span>{document.name}</span><Check /></div>)}</section><section className="cx-portal-comments"><div className="cx-portal-heading"><h2>Comentários</h2><MessageCircle /></div>{data.client.portalComments.map(item => <article key={item.id} className="cx-portal-card"><p>{item.message}</p><small>{new Date(item.createdAt).toLocaleString('pt-BR')}</small></article>)}<form onSubmit={event => { event.preventDefault(); if (comment.trim()) { void post('/comments', { message: comment.trim() }).then(() => setComment('')); } }}><label>Escrever comentário<textarea maxLength={2000} rows={3} value={comment} onChange={event => setComment(event.target.value)} placeholder="Deixe sua resposta para a equipe" /></label><button disabled={busy || !comment.trim()}>{busy ? <><ClickoLoader size="tiny" tone="dark" label="Enviando comentário" /> Enviando…</> : <>Enviar comentário <ArrowRight /></>}</button></form></section></div>}</div></main>;
}
