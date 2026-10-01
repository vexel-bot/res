import React from "react";
import {
  productApi, type EditorialPlanInput, type EditorialReadiness, type EditorialReviewInput,
  type StudioDocumentRecord,
} from "../api/productApi";
import {
  canSubmitEditorialReview, editorialAxes, editorialBlockerLabel, editorialError,
  validateEditorialPlan, verifyEditorialBlob,
} from "./editorialReview";
import "./editorial-review.css";

export interface EditorialGateState { documentId: string; revision: number; blocked: boolean }

function AssetSelection({ assets, selected, onChange, label }: {
  assets: StudioDocumentRecord["assets"]; selected: string[];
  onChange: (ids: string[]) => void; label: string;
}) {
  return <fieldset className="vs-editorial-assets"><legend>{label}</legend>
    {assets.map((asset) => <label key={asset.id} className="vs-editorial-check">
      <input type="checkbox" checked={selected.includes(asset.id)} disabled={!asset.checksum}
        onChange={(event) => onChange(event.target.checked ? [...selected, asset.id] : selected.filter((id) => id !== asset.id))} />
      <span>{asset.id}<small>{asset.mediaType} · SHA {asset.checksum?.slice(0, 12) ?? "ausente"}</small></span>
    </label>)}
    {!assets.length && <p>Adicione evidências ao documento antes de registrar um plano.</p>}
  </fieldset>;
}

function EvidencePreview({ document, comparison = false }: { document: StudioDocumentRecord; comparison?: boolean }) {
  const [assetId, setAssetId] = React.useState("");
  const [url, setUrl] = React.useState<string>();
  const [error, setError] = React.useState<string>();
  const [loading, setLoading] = React.useState(false);
  const pending = React.useRef<AbortController>();
  const urlRef = React.useRef<string>();
  const asset = document.assets.find((item) => item.id === assetId);
  function clear() {
    pending.current?.abort();
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = undefined;
    setUrl(undefined); setLoading(false); setError(undefined);
  }
  React.useEffect(() => () => {
    pending.current?.abort();
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
  }, []);
  async function load() {
    if (!asset?.checksum) return;
    clear();
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    try {
      const blob = await productApi.studioAssetBlob(asset.id, controller.signal);
      await verifyEditorialBlob(blob, asset.checksum);
      if (controller.signal.aborted) return;
      const nextUrl = URL.createObjectURL(blob);
      urlRef.current = nextUrl; setUrl(nextUrl);
    } catch (cause) {
      if (!controller.signal.aborted) setError(editorialError(cause));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }
  function playExclusively(event: React.SyntheticEvent<HTMLMediaElement>) {
    event.currentTarget.playbackRate = 1;
    event.currentTarget.closest(".vs-editorial")?.querySelectorAll<HTMLMediaElement>("audio,video").forEach((media) => {
      if (media !== event.currentTarget) media.pause();
    });
  }
  return <section aria-label={comparison ? "Prévia de comparação" : "Prévia das evidências"} className="vs-editorial-preview">
    <h3>{comparison ? "Comparar uma segunda evidência" : "Examinar evidência privada"}</h3>
    <label>{comparison ? "Arquivo de comparação" : "Arquivo da prévia"}<select value={assetId} onChange={(event) => { clear(); setAssetId(event.target.value); }}>
      <option value="">Selecione um arquivo</option>
      {document.assets.map((item) => <option key={item.id} value={item.id}>{item.id} · {item.mediaType}</option>)}
    </select></label>
    <button type="button" disabled={!asset?.checksum || loading} onClick={() => void load()}>
      {loading ? "Conferindo arquivo…" : comparison ? "Carregar comparação verificada" : "Carregar prévia verificada"}
    </button>
    {error && <p role="alert">{error}</p>}
    {url && <>
      {asset?.mediaType?.startsWith("video/") && <video controls preload="metadata" src={url} onPlay={playExclusively} aria-label={comparison ? "Comparação visual" : "Evidência visual"} />}
      {asset?.mediaType?.startsWith("audio/") && <audio controls preload="metadata" src={url} onPlay={playExclusively} aria-label={comparison ? "Comparação vocal" : "Evidência vocal"} />}
      {["image/png", "image/jpeg", "image/webp"].includes(asset?.mediaType ?? "") && <img src={url} alt="Evidência selecionada do documento" />}
      <a href={url} download={`evidencia-${assetId}`}>Baixar evidência conferida</a>
      <small>Checksum conferido. Isso não certifica naturalidade, atuação ou direitos.</small>
    </>}
  </section>;
}

export function EditorialReviewPanel({ document, disabled, active, onGateChange }: {
  document?: StudioDocumentRecord; disabled: boolean; active: boolean;
  onGateChange: (state: EditorialGateState) => void;
}) {
  const [state, setState] = React.useState<EditorialReadiness>();
  const [loading, setLoading] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState("");
  const [planOpen, setPlanOpen] = React.useState(false);
  const [replaceConfirmed, setReplaceConfirmed] = React.useState(false);
  const [draft, setDraft] = React.useState<EditorialPlanInput>({
    expectedDocumentRevision: document?.revision ?? 1, workflow: "ugc-avatar",
    objective: document?.brief?.objective ?? "", cta: "", beats: [],
  });
  const [axis, setAxis] = React.useState<EditorialReviewInput["axis"]>("voice");
  const [notes, setNotes] = React.useState("");
  const [evidenceIds, setEvidenceIds] = React.useState<string[]>([]);
  const [confirmed, setConfirmed] = React.useState(false);
  const [comparisonOpen, setComparisonOpen] = React.useState(false);
  const alive = React.useRef(true);
  const readController = React.useRef<AbortController>();
  const keys = React.useRef(new Map<string, string>());
  const documentId = document?.documentId;
  const revision = document?.revision;
  const refresh = React.useCallback(async () => {
    if (!documentId) return;
    readController.current?.abort();
    const controller = new AbortController(); readController.current = controller;
    setLoading(true); setError(undefined);
    try {
      const next = await productApi.editorialReadiness(documentId, controller.signal);
      if (!controller.signal.aborted && alive.current) setState(next);
    } catch (cause) {
      if (!controller.signal.aborted && alive.current) { setState(undefined); setError(editorialError(cause)); }
    } finally {
      if (!controller.signal.aborted && alive.current) setLoading(false);
    }
  }, [documentId]);
  React.useEffect(() => {
    alive.current = true;
    if (!disabled) void refresh();
    return () => { alive.current = false; readController.current?.abort(); };
  }, [documentId, revision, refresh, disabled]);
  React.useEffect(() => {
    if (documentId && revision) onGateChange({ documentId, revision,
      blocked: loading || busy || !state || Boolean(state.managed && !state.fullRenderEligible) });
  }, [documentId, revision, state, loading, busy, onGateChange]);

  const assets = document?.assets ?? [];
  const locked = disabled || busy || loading || !document || !state;
  const changeBeat = (index: number, patch: Partial<EditorialPlanInput["beats"][number]>) => {
    setDraft((value) => ({ ...value, beats: value.beats.map((beat, at) => at === index ? { ...beat, ...patch } : beat) }));
    setReplaceConfirmed(false);
  };
  async function save(kind: "plan" | "review", decision?: EditorialReviewInput["decision"]) {
    if (!document || locked) return;
    const body = kind === "plan" ? { ...draft, expectedDocumentRevision: document.revision } : {
      planId: state?.plan?.id ?? "", axis, decision: decision!, evidenceAssetIds: evidenceIds, notes: notes.trim(),
    };
    if (kind === "plan") {
      const invalid = validateEditorialPlan(body as EditorialPlanInput, new Set(assets.map((item) => item.id)));
      if (invalid) { setError(invalid); return; }
      if (state?.managed && !replaceConfirmed) return;
    } else if (!canSubmitEditorialReview(state) || !confirmed || !notes.trim() || !evidenceIds.length) return;
    const signature = JSON.stringify([kind, document.documentId, body]);
    const key = keys.current.get(signature) ?? `editorial-${crypto.randomUUID()}`;
    keys.current.set(signature, key); // Retained across uncertain failures only.
    setBusy(true); setNotice(""); setError(undefined);
    readController.current?.abort();
    try {
      if (kind === "plan") await productApi.registerEditorialPlan(document.documentId, body as EditorialPlanInput, key);
      else await productApi.reviewEditorialAxis(document.documentId, body as EditorialReviewInput, key);
      keys.current.delete(signature);
      if (!alive.current) return;
      setConfirmed(false); setNotes(""); setEvidenceIds([]); setReplaceConfirmed(false);
      if (kind === "plan") setPlanOpen(false);
      setNotice(kind === "plan" ? "Plano registrado. As sete revisões começam pendentes." : "Decisão registrada no histórico do servidor.");
      await refresh();
    } catch (cause) {
      if (alive.current) setError(editorialError(cause));
    } finally {
      if (alive.current) setBusy(false);
    }
  }

  return <section className="vs-editorial" aria-label="Controle editorial UGC/avatar">
    <h2>Revisão editorial</h2>
    <p>Plano e decisões humanas da revisão {revision ?? "—"}. Não gera mídia nem publica.</p>
    <p>Ao mudar a versão, a confirmação e os rascunhos desta tela são limpos. Owner/admin registra decisões.</p>
    {!document && <p>Abra um documento com fontes para começar.</p>}
    {disabled && <p>Controles indisponíveis no modo demonstração ou durante uma operação do Studio.</p>}
    <button type="button" disabled={disabled || busy || loading || !document} onClick={() => { setConfirmed(false); void refresh(); }}>Atualizar revisões</button>
    {loading && <p role="status">Consultando estado do servidor…</p>}
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {state && <>
      <p className="vs-editorial-status">{!state.managed ? "Fluxo editorial não inscrito" : state.fullRenderEligible ? "Pré-produção aprovada · somente render privado" : "Render completo bloqueado"}</p>
      <ul>{(state.blockers ?? []).map((code) => <li key={code}>{editorialBlockerLabel(code)}</li>)}</ul>
      <p>Publicação bloqueada neste fluxo até a revisão final integrada de vídeo e montagem.</p>
      {state.plan && <details><summary>Plano vigente e decisões</summary>
        <p>{state.plan.plan.objective}</p><p>CTA: {state.plan.plan.cta}</p>
        <small>Plano {state.plan.id} · revisão {state.plan.documentRevision} · {state.plan.createdBy}</small>
        <ol>{state.plan.plan.beats.map((beat) => <li key={beat.id}>
          <b>{beat.message}</b><p>{beat.visualAction}</p><p>Corte: {beat.editReason}</p>
          <small>Evidências: {beat.evidenceAssetIds.join(", ")}</small>
        </li>)}</ol>
        {editorialAxes.map((item) => {
          const review = state.reviews?.find((entry) => entry.review.axis === item.id);
          return <article key={item.id}><b>{item.label}: {review ? review.review.decision === "approved" ? "aprovado" : "rejeitado" : "pendente"}</b>
            {review && <><p>{review.review.notes}</p><small>{review.reviewedBy} · {new Date(review.reviewedAt).toLocaleString("pt-BR")}</small></>}
          </article>;
        })}
        <small>Última decisão por eixo. Revisões anteriores continuam preservadas no servidor.</small>
      </details>}
    </>}
    <button type="button" disabled={locked || !state || !assets.length} onClick={() => {
      if (!planOpen && state?.plan) setDraft({ ...state.plan.plan, expectedDocumentRevision: document!.revision });
      setReplaceConfirmed(false); setPlanOpen(!planOpen);
    }}>{planOpen ? "Fechar rascunho do plano" : state?.managed ? "Preparar nova versão do plano" : "Preparar inscrição UGC/avatar"}</button>
    {planOpen && <form onSubmit={(event) => { event.preventDefault(); void save("plan"); }}>
      <fieldset disabled={locked}><legend>Plano editorial — rascunho</legend>
        <label>Objetivo<input required maxLength={2000} value={draft.objective} onChange={(event) => { setDraft({ ...draft, objective: event.target.value }); setReplaceConfirmed(false); }} /></label>
        <label>CTA<input required maxLength={1000} value={draft.cta} onChange={(event) => { setDraft({ ...draft, cta: event.target.value }); setReplaceConfirmed(false); }} /></label>
        {draft.beats.map((beat, index) => <fieldset key={beat.id}><legend>Beat {index + 1}</legend>
          <label>Mensagem<textarea required maxLength={2000} value={beat.message} onChange={(event) => changeBeat(index, { message: event.target.value })} /></label>
          <label>Ação visual<textarea required maxLength={2000} value={beat.visualAction} onChange={(event) => changeBeat(index, { visualAction: event.target.value })} /></label>
          <label>Motivo do corte<textarea required maxLength={2000} value={beat.editReason} onChange={(event) => changeBeat(index, { editReason: event.target.value })} /></label>
          <AssetSelection assets={assets} selected={beat.evidenceAssetIds} onChange={(ids) => changeBeat(index, { evidenceAssetIds: ids })} label={`Evidências do beat ${index + 1}`} />
          <button type="button" onClick={() => { setDraft({ ...draft, beats: draft.beats.filter((_, at) => at !== index) }); setReplaceConfirmed(false); }}>Remover beat {index + 1}</button>
        </fieldset>)}
        <button type="button" disabled={draft.beats.length >= 40} onClick={() => { setDraft({ ...draft, beats: [...draft.beats, { id: `beat-${crypto.randomUUID()}`, message: "", visualAction: "", editReason: "", evidenceAssetIds: [] }] }); setReplaceConfirmed(false); }}>Adicionar beat</button>
        {state?.managed && <label className="vs-editorial-check"><input type="checkbox" checked={replaceConfirmed} onChange={(event) => setReplaceConfirmed(event.target.checked)} />Entendo que um novo plano exige novamente as sete revisões.</label>}
        <button type="submit" disabled={!draft.beats.length || Boolean(state?.managed && !replaceConfirmed)}>Registrar plano editorial</button>
      </fieldset>
    </form>}
    {document && active && !disabled && <>
      <EvidencePreview document={document} />
      <button type="button" aria-expanded={comparisonOpen} onClick={() => setComparisonOpen(!comparisonOpen)}>
        {comparisonOpen ? "Fechar comparação" : "Comparar referência e candidata"}
      </button>
      {comparisonOpen && <>
        <p>Escolha os dois arquivos conscientemente. Comparação não cega, sem normalização automática de volume;
          reprodução em 1×, um player por vez. A seleção não altera origem, direitos ou aprovação dos arquivos.</p>
        <EvidencePreview document={document} comparison />
      </>}
    </>}
    <fieldset disabled={locked || !canSubmitEditorialReview(state)}><legend>Registrar decisão humana</legend>
      <label>Etapa a revisar<select value={axis} onChange={(event) => { setAxis(event.target.value as EditorialReviewInput["axis"]); setConfirmed(false); setNotes(""); setEvidenceIds([]); }}>
        {editorialAxes.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select></label>
      <AssetSelection assets={assets} selected={evidenceIds} onChange={(ids) => { setEvidenceIds(ids); setConfirmed(false); }} label="Evidências desta decisão" />
      <label>Observações e timestamps<textarea maxLength={4000} value={notes} onChange={(event) => { setNotes(event.target.value); setConfirmed(false); }} /></label>
      <label className="vs-editorial-check"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />Examinei as evidências selecionadas e confirmo esta decisão humana.</label>
      <div className="vs-editorial-actions">
        <button type="button" disabled={!confirmed || !notes.trim() || !evidenceIds.length} onClick={() => void save("review", "rejected")}>Rejeitar etapa</button>
        <button type="button" disabled={!confirmed || !notes.trim() || !evidenceIds.length} onClick={() => void save("review", "approved")}>Aprovar etapa</button>
      </div>
    </fieldset>
  </section>;
}
