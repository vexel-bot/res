import React from "react";
import { APIError } from "../../api";
import { productApi } from "../../api/productApi";
import { departmentApi, type DepartmentProject, type NarrationInput, type NarrationState } from "./departmentApi";
import "./narration.css";

const active = (value?: NarrationState) => !!value?.job && !["succeeded", "failed", "cancelled"].includes(value.job.status);
const labels: Record<string, string> = {
  queued: "Na fila", running: "Produzindo a fala", retrying: "Retomando a produção", cancel_requested: "Cancelando",
  succeeded: "Narração disponível", failed: "A fala não foi concluída", cancelled: "Narração cancelada",
};
const explain = (error: unknown) => {
  if (error instanceof TypeError) return "A conexão caiu. Confira o mesmo pedido para retomar sem duplicar a geração.";
  const code = error instanceof Error ? error.message : String(error || "");
  const messages: Record<string, string> = {
    selected_voice_runtime_unavailable: "A geração com essa voz está indisponível no momento. Você pode salvar o texto e continuar depois.",
    speech_provider_not_approved: "Esta voz ainda não foi liberada para gerar narrações.",
    speech_model_not_approved: "Esta voz ainda não foi liberada para gerar narrações.",
    speech_provider_benchmark_pending: "A avaliação dessa voz para gerar narrações ainda não foi concluída.",
    speech_provider_not_advertised: "O serviço de voz não está disponível agora.",
    stock_voice_synthesis_binding_mismatch: "Esta voz licenciada ainda precisa ter seu timbre de síntese configurado e revisado.",
    narration_direction_required: "Escolha a direção editorial antes de preparar a fala.",
    narration_already_running: "Já existe uma narração em andamento. Acompanhe ou cancele esse pedido.",
    narration_project_producing: "Aguarde a preparação da primeira versão antes de gerar a fala.",
    studio_project_conflict: "O projeto mudou em outra sessão. Confira a versão atual antes de gerar a fala.",
    narration_request_superseded: "Outro pedido de narração já substituiu este. Confira a versão atual.",
    production_voice_selection_conflict: "A narração não corresponde à voz escolhida. Reabra o projeto para conferir a seleção.",
    production_voice_lineage_conflict: "Não foi possível conferir a origem desta narração. Ela não será usada como a voz selecionada.",
    consent_not_active: "A autorização dessa voz não está ativa.",
    voice_profile_not_active: "A voz escolhida não está mais disponível para uso.",
    voice_version_not_active: "A versão dessa voz não está mais aprovada para uso.",
    queue_unavailable: "A produção não pôde entrar na fila. Seu texto foi preservado.",
  };
  return messages[code] || (code && !/^[a-z0-9_]+$/.test(code) ? code : "Não foi possível concluir a narração. Confira o pedido e tente novamente.");
};

export function ProjectNarration({ project, voiceName, onProject }: {
  project: DepartmentProject; voiceName: string; onProject: (project: DepartmentProject) => void;
}) {
  const [state, setState] = React.useState<NarrationState>();
  const [text, setText] = React.useState("");
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [busy, setBusy] = React.useState(false);
  const [refresh, setRefresh] = React.useState(0);
  const [listen, setListen] = React.useState(false);
  const [audioUrl, setAudioUrl] = React.useState<string>();
  const [audioError, setAudioError] = React.useState<string>();
  const pending = React.useRef<NarrationInput | undefined>(undefined);
  const dirty = React.useRef(false);
  const epoch = React.useRef(0);
  const alive = React.useRef(true);
  const notify = React.useRef(onProject);
  notify.current = onProject;
  React.useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  React.useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      const ticket = epoch.current;
      try {
        const value = await departmentApi.narration(project.id, controller.signal);
        if (controller.signal.aborted || ticket !== epoch.current) return;
        if (pending.current?.requestKey === value.requestKey) {
          pending.current = undefined; dirty.current = false;
          setError(undefined);
          setNotice("Pedido recuperado. Acompanhe a narração abaixo.");
        }
        setState(value); notify.current(value.project);
        if (!dirty.current) setText(value.text);
        if (active(value)) timer = setTimeout(() => void load(), 2500);
      } catch (failure) { if (!controller.signal.aborted && ticket === epoch.current) setError(explain(failure)); }
    };
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [project.id, project.voiceVersionId, project.directionId, refresh]);
  React.useEffect(() => {
    setAudioUrl(undefined); setAudioError(undefined);
    if (!listen || !state?.assetId) return;
    const controller = new AbortController();
    let owned: string | undefined;
    void productApi.studioAssetBlob(state.assetId, controller.signal).then(blob => {
      if (controller.signal.aborted) return;
      owned = URL.createObjectURL(blob); setAudioUrl(owned);
    }).catch(failure => { if (!controller.signal.aborted) setAudioError(explain(failure)); });
    return () => { controller.abort(); if (owned) URL.revokeObjectURL(owned); };
  }, [listen, state?.assetId]);
  const generate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy || active(state) || !state || (!pending.current && (!state.canGenerate || !text.trim()))) return;
    pending.current ||= { expectedRevision: state.project.revision, requestKey: crypto.randomUUID(), text: text.trim() };
    epoch.current++;
    setBusy(true); setError(undefined); setNotice(undefined);
    try {
      const value = await departmentApi.narrate(project.id, pending.current);
      if (!alive.current) return;
      pending.current = undefined; dirty.current = false;
      setState(value); setText(value.text); setListen(false); notify.current(value.project);
      setNotice("Pedido de narração salvo com a voz escolhida.");
      setRefresh(value => value + 1);
    } catch (failure) {
      if (!alive.current) return;
      // A rejected request can be edited. A lost response keeps its original
      // key/text until reconciliation, so a retry cannot mint a second job.
      if (failure instanceof APIError && [400, 403, 404, 409, 422].includes(failure.status)) pending.current = undefined;
      setError(explain(failure)); setRefresh(value => value + 1);
    } finally { if (alive.current) setBusy(false); }
  };
  const cancel = async () => {
    if (busy) return;
    epoch.current++;
    setBusy(true); setError(undefined);
    try {
      const value = await departmentApi.cancelNarration(project.id);
      if (alive.current) { setState(value); notify.current(value.project); setRefresh(value => value + 1); }
    } catch (failure) { if (alive.current) setError(explain(failure)); }
    finally { if (alive.current) setBusy(false); }
  };
  const saveDraft = async () => {
    if (busy || !state || active(state) || pending.current || !text.trim()) return;
    epoch.current++;
    setBusy(true); setError(undefined); setNotice(undefined);
    try {
      const value = await departmentApi.saveNarration(project.id, { expectedRevision: state.project.revision, text: text.trim() });
      if (alive.current) {
        dirty.current = false; setState(value); setText(value.text); notify.current(value.project);
        setNotice("Texto salvo no projeto. Nenhum áudio foi gerado.");
        setRefresh(value => value + 1);
      }
    } catch (failure) { if (alive.current) { setError(explain(failure)); setRefresh(value => value + 1); } }
    finally { if (alive.current) setBusy(false); }
  };
  return <section className="ds-narration" aria-labelledby="ds-narration-title">
    <header><div><small className="ds-eyebrow">A VOZ DESTA CRIAÇÃO</small><h2 id="ds-narration-title">Narração · {voiceName}</h2></div>
      {state?.job && <span role="status">{labels[state.job.status] || "Acompanhando a produção"} · {state.job.progress}%</span>}
    </header>
    <p>{project.format === "image" || project.format === "carousel"
      ? "Prepare a fala como um material para a versão narrada desta criação. O arquivo de imagem continua sendo uma imagem."
      : project.identityVersionId
        ? "Prepare a fala com a voz escolhida. A animação da aparência e a montagem do vídeo são etapas seguintes."
        : "Prepare a fala para narrar o material escolhido. A montagem terá a duração desta narração; se o vídeo for curto, sua imagem final permanece até a fala terminar. O áudio original continua no arquivo de origem."}</p>
    {error && <p className="ds-narration-error" role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {!state ? <button type="button" onClick={() => { setError(undefined); setRefresh(value => value + 1); }}>Carregar narração</button> : <>
      {state.blocker && <p>{explain(state.blocker)}</p>}
      {state.job?.status === "failed" && <p role="alert">{explain(state.job.errorCode)}</p>}
      <form onSubmit={event => void generate(event)}>
        <label>Texto da narração<textarea value={text} maxLength={4000} required
          disabled={busy || active(state) || !!pending.current}
          onChange={event => { dirty.current = true; setText(event.target.value); }} /></label>
        <div className="ds-narration-actions">
          <button type="button" className="ds-secondary" disabled={busy || active(state) || !!pending.current || !text.trim()} onClick={() => void saveDraft()}>Salvar texto</button>
          <button type="submit" className="ds-primary" disabled={busy || active(state) || (!pending.current && (!state.canGenerate || !text.trim()))}>
            {busy ? "Salvando pedido…" : pending.current ? "Conferir o mesmo pedido" : state.job ? "Gerar nova narração" : "Gerar narração"}
          </button>
          {active(state) && <button type="button" className="ds-secondary" disabled={busy || state.job?.status === "cancel_requested"} onClick={() => void cancel()}>Cancelar narração</button>}
          <button type="button" disabled={busy} onClick={() => { setError(undefined); setRefresh(value => value + 1); }}>Atualizar estado</button>
        </div>
      </form>
      {pending.current && <p>O envio ainda precisa ser conferido. Repetir usa o mesmo texto e o mesmo pedido.</p>}
      {state.assetId && state.job?.status === "succeeded" && <div className="ds-narration-audio">
        <p>Áudio do último pedido concluído.</p>
        {state.generatedText && <details><summary>Texto do áudio gerado</summary><p>{state.generatedText}</p></details>}
        {!listen && <button type="button" onClick={() => setListen(true)}>Ouvir narração</button>}
        {listen && !audioUrl && !audioError && <p role="status">Carregando áudio privado…</p>}
        {audioError && <p role="alert">{audioError}</p>}
        {audioUrl && <><audio controls src={audioUrl} aria-label="Narração produzida com a voz escolhida" /><a href={audioUrl} download="narracao.wav">Baixar narração</a></>}
      </div>}
    </>}
  </section>;
}
