import React from "react";
import { APIError, apiFetch } from "../../api";
import type { StudioDocumentRecord } from "../../api/productApi";
import { buildCopyHandoff, copyContext, copyStrategy, momentStrategies, offerStrategies, type CopyData, type CopyDraft, type SavedCopy } from "./adCopy";
import "../shared/ad-copy-process.css";

const inputs = [
  ["product", "O que é anunciado"], ["audience", "Público da campanha"],
  ["problem", "Situação que o público reconhece"], ["objections", "Dúvida ou objeção"],
  ["awareness", "Linguagem e sinais do público"],
  ["benefit", "Benefício para o público"], ["offer", "Oferta"],
  ["videoChannel", "Canal"], ["videoTiming", "Momento ou calendário da campanha"],
  ["cta", "Ação desejada"], ["videoDestination", "Destino da ação"],
  ["restrictions", "Condições e limites"],
] as const;

const textFields = [
  ["angle", "Ângulo e justificativa"], ["hook", "Gancho escolhido"], ["body", "Corpo da copy"],
  ["videoAlternateHook", "Outra abertura"], ["videoHypothesis", "Hipótese para comparar as aberturas"],
] as const;

export function VideoAdCopyPanel({ project, durationSeconds, onSaved, disabled }: {
  project: StudioDocumentRecord;
  durationSeconds: number;
  onSaved: (saved?: SavedCopy) => void;
  disabled: boolean;
}) {
  const url = `/api/v1/studios/v1/copy/document/${encodeURIComponent(project.documentId)}`;
  const [saved, setSaved] = React.useState<SavedCopy>();
  const [data, setData] = React.useState<CopyData>({});
  const [busy, setBusy] = React.useState<"save" | "generate">();
  const [notice, setNotice] = React.useState("");
  const [error, setError] = React.useState("");
  const [reload, setReload] = React.useState(0);
  const [conflict, setConflict] = React.useState(false);
  const kindId = React.useId();
  const momentId = React.useId();
  const attempt = React.useRef<{ body: string; key: string } | undefined>(undefined);
  const operation = React.useRef<AbortController | undefined>(undefined);
  const { objective, audience, channel, cta, angle, hook, restrictions, tone } = project.brief;
  const seed = project.composition.narrative?.copyCampaign as CopyData | undefined;
  const defaults = React.useRef({ audience, videoChannel: channel, cta, restrictions: restrictions?.join("\n") || "", ...seed });

  const applySaved = React.useCallback((next: SavedCopy) => {
    setData({ ...defaults.current, ...next.data });
    setSaved(next);
    setConflict(false);
    onSaved(next);
  }, [onSaved]);

  React.useEffect(() => () => operation.current?.abort(), []);

  React.useEffect(() => {
    const controller = new AbortController();
    apiFetch<SavedCopy>(url, { signal: controller.signal }).then(next => {
      if (!controller.signal.aborted) applySaved(next);
    }).catch(cause => {
      if (controller.signal.aborted) return;
      onSaved(undefined);
      setError(cause instanceof Error ? cause.message : "Não foi possível recuperar a copy do projeto.");
    });
    return () => controller.abort();
  }, [url, applySaved, onSaved, reload]);

  const context = copyContext(data);
  const strategy = copyStrategy(data);

  function edit(field: string, value: string) {
    setData(current => ({ ...current, [field]: value }));
    setNotice("");
  }

  async function run(action: "save" | "generate") {
    if (!saved || operation.current) return;
    const controller = new AbortController();
    operation.current = controller;
    setBusy(action);
    setError("");
    setNotice("");
    try {
      if (action === "generate") {
        const draft = await apiFetch<CopyDraft>("/api/ai/generate-video-ad-copy", {
          method: "POST",
          body: JSON.stringify({ data, objective, durationSeconds, tone, angleIdea: angle, hookIdea: hook }),
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setData(current => ({
          ...current,
          angle: draft.angle, hook: draft.hook, body: draft.body,
          videoAlternateHook: draft.alternateHook, videoHypothesis: draft.hypothesis,
        }));
        setNotice("Duas aberturas com o mesmo argumento. Compare o gancho, confira provas e condições e salve a versão que vai para o briefing.");
        return;
      }
      const payload = { expectedRevision: saved.revision, status: "draft", data };
      const body = JSON.stringify(payload);
      if (attempt.current?.body !== body) attempt.current = { body, key: crypto.randomUUID() };
      const next = await apiFetch<SavedCopy>(url, {
        method: "PUT",
        body: JSON.stringify({ ...payload, requestKey: attempt.current.key }),
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      attempt.current = undefined;
      applySaved(next);
      setNotice(buildCopyHandoff(next) ? `Versão ${next.revision} incluída no briefing do anúncio.` : "Contexto salvo.");
    } catch (cause) {
      if (controller.signal.aborted) return;
      const isConflict = cause instanceof APIError && cause.status === 409 && action === "save";
      if (isConflict) setConflict(true);
      setError(isConflict ? "O anúncio tem uma versão mais recente. Carregue a versão salva antes de continuar." :
        cause instanceof Error ? cause.message : "Não foi possível concluir a operação.");
    } finally {
      operation.current = undefined;
      if (!controller.signal.aborted) setBusy(undefined);
    }
  }

  const locked = !saved || !!busy || disabled || conflict;
  return <details className="ad-copy-process">
    <summary>Copy para anúncios em vídeo</summary>
    {saved && <>
      <fieldset disabled={locked}>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="grid gap-1">
            <label htmlFor={kindId}>Tipo de oferta</label>
            <select id={kindId} value={data.videoKind || ""} onChange={event => edit("videoKind", event.target.value)}>
              <option value="">Selecione</option>
              {Object.entries(offerStrategies).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}
            </select>
          </div>
          <div className="grid gap-1">
            <label htmlFor={momentId}>Momento do público</label>
            <select id={momentId} value={data.videoMoment || ""} onChange={event => edit("videoMoment", event.target.value)}>
              <option value="">Selecione</option>
              {Object.entries(momentStrategies).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}
            </select>
          </div>
        </div>
        {strategy && <div className="my-3 space-y-1"><p>{strategy.approach}</p><p>{strategy.opening}</p></div>}
        <details className="ad-copy-group" open>
          <summary>Contexto, oferta e evidências</summary>
          <div>{inputs.map(([field, label]) => <label key={field}>{label}
            <textarea rows={2} maxLength={2500} value={data[field] || ""} onChange={event => edit(field, event.target.value)} />
          </label>)}</div>
          <label className="mt-3">Afirmações confirmadas
            <textarea rows={4} maxLength={2500} value={data.videoEvidence || ""} onChange={event => edit("videoEvidence", event.target.value)} />
          </label>
          <small>Até oito linhas. Use afirmação breve com suas condições | fonte | validade opcional (AAAA-MM-DD). Registre apenas informações que você conferiu.</small>
        </details>
        {context && !context.ready && <p className="my-2">Para preparar a copy, preencha {context.missing.join(", ")}.</p>}
        <button type="button" disabled={locked || !context?.ready} onClick={() => void run("generate")}>
          {busy === "generate" ? "Preparando copy…" : "Gerar copy na Clicko"}
        </button>
        <details className="ad-copy-group" open>
          <summary>Argumento comercial</summary>
          <div>{textFields.map(([field, label]) => <label key={field}>{label}
            <textarea rows={field === "body" ? 5 : 2} maxLength={2500} value={data[field] || ""} onChange={event => edit(field, event.target.value)} />
          </label>)}</div>
          {data.videoAlternateHook && <button className="mt-3" type="button" onClick={() => {
            setData(current => ({ ...current, hook: current.videoAlternateHook, videoAlternateHook: current.hook }));
            setNotice("");
          }}>Usar a outra abertura</button>}
          <p className="my-2 text-sm">Leia em voz alta e confira se a abertura desperta curiosidade que o corpo resolve, se a prova sustenta a promessa e se a ação está clara.</p>
        </details>
        <button type="button" disabled={locked} onClick={() => void run("save")}>
          {busy === "save" ? "Salvando…" : "Salvar contexto e copy"}
        </button>
      </fieldset>
      {buildCopyHandoff(saved) && !notice && <p className="text-sm">O briefing usa a versão salva {saved.revision}.</p>}
    </>}
    {!saved && !error && <p role="status">Carregando copy do projeto…</p>}
    {(conflict || (!saved && error)) && <button type="button" onClick={() => {
      setError("");
      setReload(value => value + 1);
    }}>Carregar versão salva</button>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
  </details>;
}
