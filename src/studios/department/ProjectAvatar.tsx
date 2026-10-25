import React from 'react';
import { APIError } from '../../api';
import { productApi } from '../../api/productApi';
import { departmentApi, type AvatarPlan, type AvatarState, type DepartmentProject } from './departmentApi';
import './narration.css';

const running = (state?: AvatarState) => !!state?.job && !['succeeded', 'failed', 'cancelled'].includes(state.job.status);
const labels: Record<string, string> = { queued: 'Na fila', running: 'Preparando apresentação', retrying: 'Retomando produção',
  succeeded: 'Apresentação disponível', failed: 'A apresentação não foi concluída', cancelled: 'Apresentação cancelada', cancel_requested: 'Cancelando' };
const explain = (failure: unknown): string => {
  const code = failure instanceof Error ? failure.message : String(failure || '');
  const messages: Record<string, string> = {
    avatar_final_narration_required: 'Conclua a narração com a voz escolhida antes de preparar a apresentação.',
    avatar_narration_draft_not_generated: 'O texto foi alterado. Gere e revise a nova narração antes de preparar a apresentação.',
    avatar_appearance_and_voice_required: 'Escolha a aparência e a voz para esta apresentação.',
    avatar_plan_changed: 'Os materiais ou a disponibilidade mudaram. Atualize o pedido antes de continuar.',
    studio_project_conflict: 'O projeto mudou em outra sessão. Atualize o pedido antes de continuar.',
    avatar_project_materials_changed: 'A apresentação pertence a uma fala ou direção anterior. Prepare uma nova versão.',
    avatar_already_running: 'Uma apresentação já está em andamento. Acompanhe ou cancele o pedido.',
    avatar_project_producing: 'Aguarde a preparação da montagem antes de gerar outra apresentação.',
    consent_not_active: 'Uma autorização do elenco não está mais ativa.',
    identity_profile_not_active: 'A aparência escolhida não está disponível para uso.',
    voice_profile_not_active: 'A voz escolhida não está disponível para uso.',
    queue_unavailable: 'A apresentação não pôde entrar na fila. O projeto foi preservado.',
  };
  if (messages[code]) return messages[code];
  if (code.startsWith('avatar_profile_unavailable:') && code.includes('duration')) return 'Esta fala excede a duração liberada para o serviço de apresentação. Ela permanece salva integralmente.';
  if (/avatar_(provider|model|profile)/.test(code)) return 'A produção da apresentação ainda não está disponível neste ambiente. A aparência e a fala permanecem salvas.';
  if (failure instanceof TypeError) return 'A conexão caiu. Confira o mesmo pedido para continuar sem duplicar a geração.';
  return code && /\s/.test(code) ? code : 'Não foi possível conferir a apresentação. Atualize o pedido e tente novamente.';
};

export function ProjectAvatar({ project, onProject }: { project: DepartmentProject; onProject: (project: DepartmentProject) => void }) {
  const [state, setState] = React.useState<AvatarState>();
  const [performance, setPerformance] = React.useState('Plano médio, postura natural e fala clara.');
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [busy, setBusy] = React.useState(false);
  const [refresh, setRefresh] = React.useState(0);
  const [watch, setWatch] = React.useState(false);
  const [videoUrl, setVideoUrl] = React.useState<string>();
  const pending = React.useRef<{ plan: AvatarPlan; key: string; confirmed?: boolean } | undefined>(undefined);
  const epoch = React.useRef(0);
  const dirty = React.useRef(false);
  const alive = React.useRef(true);
  const notify = React.useRef(onProject); notify.current = onProject;
  React.useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  React.useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      const ticket = epoch.current;
      try {
        const value = await departmentApi.avatar(project.id, controller.signal);
        if (controller.signal.aborted || ticket !== epoch.current) return;
        if (pending.current?.key === value.requestKey) {
          setNotice(pending.current.confirmed ? 'Pedido confirmado. Acompanhe a apresentação abaixo.' : 'Pedido recuperado. Acompanhe a apresentação abaixo.');
          pending.current = undefined; dirty.current = false; setError(undefined);
        }
        if (!dirty.current && value.performanceDirection) setPerformance(value.performanceDirection);
        setState(value); notify.current(value.project);
        // The signed Node boundary reconciles the minute reservation from the full job result.
        if (value.job) await departmentApi.reconcileAvatar(value.job.id, controller.signal);
        if (!controller.signal.aborted && ticket === epoch.current && running(value)) timer = setTimeout(() => void load(), 2500);
      } catch (failure) { if (!controller.signal.aborted && ticket === epoch.current) setError(explain(failure)); }
    };
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [project.id, project.revision, refresh]);
  React.useEffect(() => {
    setVideoUrl(undefined);
    if (!watch || !state?.assetId) return;
    const controller = new AbortController(); let owned: string | undefined;
    void productApi.studioAssetBlob(state.assetId, controller.signal).then(blob => {
      if (controller.signal.aborted) return;
      owned = URL.createObjectURL(blob); setVideoUrl(owned);
    }).catch(failure => { if (!controller.signal.aborted) setError(explain(failure)); });
    return () => { controller.abort(); if (owned) URL.revokeObjectURL(owned); };
  }, [watch, state?.assetId]);
  const generate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy || running(state) || (!pending.current && !state?.canGenerate)) return;
    epoch.current++; setBusy(true); setError(undefined); setNotice(undefined);
    try {
      if (!pending.current) {
        const plan = await departmentApi.planAvatar(project.id, performance.trim());
        if (!alive.current) return;
        pending.current = { plan, key: crypto.randomUUID() };
      }
      await departmentApi.generateAvatar(project.id, pending.current.plan, pending.current.key);
      if (!alive.current) return;
      if (pending.current) pending.current.confirmed = true;
      setWatch(false); setNotice('Pedido enviado com a aparência e a fala escolhidas.');
    } catch (failure) {
      if (!alive.current) return;
      if (failure instanceof APIError && [400, 403, 404, 409, 422, 429].includes(failure.status)) pending.current = undefined;
      setError(explain(failure));
    } finally { if (alive.current) { setBusy(false); setRefresh(value => value + 1); } }
  };
  const cancel = async () => {
    if (busy) return;
    epoch.current++; setBusy(true); setError(undefined);
    try { await departmentApi.cancelAvatar(project.id); }
    catch (failure) { if (alive.current) setError(explain(failure)); }
    finally { if (alive.current) { setBusy(false); setRefresh(value => value + 1); } }
  };
  return <section className="ds-narration ds-avatar" aria-labelledby="ds-avatar-title">
    <header><div><small className="ds-eyebrow">APARÊNCIA E VOZ EM CENA</small><h2 id="ds-avatar-title">Apresentação</h2></div>
      {state?.job && <span role="status">{labels[state.job.status] || 'Acompanhando produção'} · {state.job.progress}%</span>}</header>
    <p>A aparência selecionada apresenta a fala final com a voz escolhida. Revise esta versão antes de preparar a montagem.</p>
    {error && <p role="alert" className="ds-narration-error">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {state?.blocker && <p>{explain(state.blocker)}</p>}
    {state?.job?.status === 'failed' && <p role="alert">{explain(state.job.errorCode)}</p>}
    <form onSubmit={event => void generate(event)}>
      <label>Como deve ser a apresentação?<textarea value={performance} minLength={3} maxLength={2000} required
        disabled={busy || running(state) || !!pending.current} onChange={event => { dirty.current = true; setPerformance(event.target.value); }} /></label>
      <div className="ds-narration-actions">
        <button type="submit" className="ds-primary" disabled={busy || running(state) || (!pending.current && !state?.canGenerate)}>
          {busy ? 'Conferindo pedido…' : pending.current ? 'Conferir o mesmo pedido' : state?.job ? 'Preparar nova apresentação' : 'Preparar apresentação'}</button>
        {running(state) && <button type="button" disabled={busy || state?.job?.status === 'cancel_requested'} onClick={() => void cancel()}>Cancelar apresentação</button>}
        <button type="button" disabled={busy} onClick={() => setRefresh(value => value + 1)}>Atualizar apresentação</button>
      </div>
    </form>
    {pending.current && <p>O envio ainda precisa ser conferido. Repetir mantém os mesmos materiais e o mesmo pedido.</p>}
    {state?.assetId && <div className="ds-narration-audio">
      {!watch && <button type="button" onClick={() => setWatch(true)}>Ver apresentação</button>}
      {watch && !videoUrl && <p role="status">Carregando vídeo privado…</p>}
      {videoUrl && <><video controls preload="metadata" src={videoUrl} aria-label="Apresentação com a aparência e a voz escolhidas" />
        <a href={videoUrl} download="apresentacao.mp4">Baixar apresentação</a></>}
      <p>Conteúdo sintético. A entrega continua sujeita à revisão.</p>
    </div>}
  </section>;
}
