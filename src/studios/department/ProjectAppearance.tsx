import React from 'react';
import { APIError } from '../../api';
import { productApi } from '../../api/productApi';
import { departmentApi, type AppearancePlan, type AppearanceState, type DepartmentProject } from './departmentApi';
import './narration.css';

const active = (status?: string) => !!status && !['succeeded', 'failed', 'cancelled'].includes(status);
type PendingAppearance = { plan: AppearancePlan; key: string };
const pendingKey = (project: DepartmentProject) => `clicko:appearance:${project.workspaceId}:${project.id}`;
const readPending = (project: DepartmentProject): PendingAppearance | undefined => {
  try {
    const value = JSON.parse(sessionStorage.getItem(pendingKey(project)) || 'null');
    if (typeof value?.key === 'string' && /^[a-f0-9]{64}$/.test(value?.plan?.planDigestSha256)
      && Number.isInteger(value?.plan?.projectRevision) && typeof value?.plan?.request?.direction === 'string'
      && Number.isInteger(value?.plan?.request?.seed)) return value as PendingAppearance;
  } catch { /* Storage can be disabled; keep the in-memory recovery path. */ }
  return undefined;
};
const savePending = (project: DepartmentProject, value?: PendingAppearance) => {
  try {
    if (value) sessionStorage.setItem(pendingKey(project), JSON.stringify(value));
    else sessionStorage.removeItem(pendingKey(project));
  } catch { /* The current tab can still retry its in-memory request. */ }
};
const explain = (failure: unknown) => {
  const code = failure instanceof Error ? failure.message : String(failure || '');
  const messages: Record<string, string> = {
    appearance_provider_not_approved: 'A criação de imagens com esta aparência ainda não está disponível neste ambiente.',
    appearance_model_not_approved: 'O modelo de imagem ainda está em avaliação neste ambiente.',
    appearance_provider_unavailable: 'A criação de imagens com esta aparência ainda não está disponível neste ambiente.',
    appearance_identity_required: 'Escolha uma aparência para este projeto.',
    identity_image_sample_required: 'A aparência escolhida precisa de uma imagem de referência.',
    identity_capability_missing: 'Esta aparência não está habilitada para geração de imagens.',
    appearance_direction_required: 'Escolha primeiro uma direção editorial.',
    appearance_project_plan_changed: 'O projeto ou seus materiais mudaram. Atualize e prepare outro pedido.',
    appearance_selected_result_changed: 'Os materiais ou autorizações desta imagem mudaram. Prepare outra versão.',
    studio_project_conflict: 'O projeto mudou em outra sessão. Atualize antes de continuar.',
    consent_not_active: 'A autorização da aparência escolhida não está mais ativa.',
    queue_unavailable: 'Não foi possível iniciar a produção. O projeto permanece salvo.',
  };
  return messages[code] || (failure instanceof TypeError
    ? 'A conexão caiu. Confira o mesmo pedido antes de tentar novamente.'
    : /\s/.test(code) ? code : 'Não foi possível concluir o pedido. Atualize e tente novamente.');
};

export function ProjectAppearance({ project, onProject }: { project: DepartmentProject; onProject: (value: DepartmentProject) => void }) {
  const pending = React.useRef<PendingAppearance | undefined>(readPending(project));
  const [state, setState] = React.useState<AppearanceState>();
  const [direction, setDirection] = React.useState(() => pending.current?.plan.request.direction || 'Coloque a pessoa na cena, preservando sua aparência.');
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [busy, setBusy] = React.useState(false);
  const [refresh, setRefresh] = React.useState(0);
  const [preview, setPreview] = React.useState<string>();
  const alive = React.useRef(true);
  const assetId = state?.job?.status === 'succeeded' ? state.job.result?.assetId : undefined;
  React.useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  React.useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const value = await departmentApi.appearance(project.id, controller.signal);
        if (controller.signal.aborted) return;
        setState(value);
        if (pending.current?.key === value.job?.idempotencyKey) {
          pending.current = undefined; savePending(project); setError(undefined); setNotice('Pedido encontrado. Acompanhe a produção abaixo.');
        }
        if (active(value.job?.status)) timer = setTimeout(() => void load(), 2500);
      } catch (failure) { if (!controller.signal.aborted) setError(explain(failure)); }
    };
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [project.id, refresh]);
  React.useEffect(() => {
    setPreview(undefined);
    if (!assetId) return;
    const controller = new AbortController(); let url: string | undefined;
    void productApi.studioAssetBlob(assetId, controller.signal).then(blob => {
      if (!controller.signal.aborted) { url = URL.createObjectURL(blob); setPreview(url); }
    }).catch(failure => { if (!controller.signal.aborted) setError(explain(failure)); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [assetId]);
  const generate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy || active(state?.job?.status) || !project.directionId || project.documentId) return;
    setBusy(true); setError(undefined); setNotice(undefined);
    try {
      if (!pending.current) {
        const plan = await departmentApi.planAppearance(project.id, project.revision, direction.trim());
        if (!alive.current) return;
        pending.current = { plan, key: crypto.randomUUID() };
        savePending(project, pending.current);
      }
      await departmentApi.generateAppearance(project.id, pending.current.plan, pending.current.key);
      if (alive.current) setNotice('Pedido enviado para produção.');
    } catch (failure) {
      if (alive.current) {
        if (failure instanceof APIError && [400, 403, 404, 409, 422, 429].includes(failure.status)) {
          pending.current = undefined; savePending(project);
        }
        setError(explain(failure));
      }
    } finally { if (alive.current) { setBusy(false); setRefresh(value => value + 1); } }
  };
  const select = async () => {
    if (!state?.job || busy) return;
    setBusy(true); setError(undefined);
    try {
      const next = await departmentApi.selectAppearance(project.id, project.revision, state.job.id);
      if (alive.current) { onProject(next); setNotice('Imagem escolhida para a entrega. O material original foi preservado.'); setRefresh(value => value + 1); }
    } catch (failure) { if (alive.current) setError(explain(failure)); }
    finally { if (alive.current) setBusy(false); }
  };
  return <section className="ds-narration ds-appearance" aria-labelledby="ds-appearance-title">
    <header><div><small className="ds-eyebrow">PERSONAGEM NA IMAGEM</small><h2 id="ds-appearance-title">Direção da cena</h2></div>
      {state?.job && <span role="status">{active(state.job.status) ? `Preparando imagem · ${state.job.progress}%` : state.job.status === 'succeeded' ? 'Imagem pronta para revisão' : 'Pedido encerrado'}</span>}</header>
    <p>Descreva como a aparência escolhida deve participar da imagem. A referência original permanece na biblioteca.</p>
    {!project.directionId && <p>Escolha uma direção editorial para preparar a imagem.</p>}
    {project.documentId && <p>Esta entrega já foi preparada. Crie outro projeto para experimentar uma nova cena.</p>}
    {state && !state.availability.available && <p role="status">{explain(state.availability.reason)}</p>}
    {error && <p role="alert" className="ds-narration-error">{error}</p>}
    {state?.job?.status === 'failed' && <p role="alert">{explain(state.job.errorCode)}</p>}
    {notice && <p role="status">{notice}</p>}
    <form onSubmit={event => void generate(event)}>
      <label>Como a pessoa deve aparecer?<textarea value={direction} minLength={3} maxLength={4000} required
        disabled={busy || active(state?.job?.status) || !!pending.current || !!project.documentId}
        onChange={event => setDirection(event.target.value)} /></label>
      <div className="ds-narration-actions"><button className="ds-primary" type="submit" disabled={busy || active(state?.job?.status) || !project.directionId || !!project.documentId || (!pending.current && !state?.availability.available)}>
        {busy ? 'Conferindo…' : pending.current ? 'Conferir o mesmo pedido' : 'Preparar imagem'}</button>
        <button type="button" disabled={busy} onClick={() => setRefresh(value => value + 1)}>Atualizar</button></div>
    </form>
    {pending.current && <p>Se o envio não foi confirmado, use o mesmo pedido para evitar uma nova cobrança.</p>}
    {assetId && <div className="ds-appearance-result">
      {preview ? <img src={preview} alt="Imagem gerada com a aparência escolhida, para revisão" /> : <p role="status">Carregando imagem privada…</p>}
      <div><p>Confira a imagem antes de usá-la. Conteúdo gerado por IA.</p>
        {state?.selection?.jobId === state?.job?.id ? <p role="status">Imagem escolhida para a entrega.</p> :
          <button type="button" disabled={busy || !!project.documentId} onClick={() => void select()}>Usar esta imagem</button>}</div>
    </div>}
  </section>;
}
