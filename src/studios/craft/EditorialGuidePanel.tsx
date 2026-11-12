import React from "react";
import { craftApi, type CraftReview, type EditorialGuide, type EditorialLesson } from "./craftApi";

interface Props { documentId: string; revision: number; disabled: boolean }
const blank: EditorialLesson = { situation: "", correction: "", useWhen: [], avoidWhen: [] };

export function EditorialGuidePanel({ documentId, revision, disabled }: Props) {
  const [guides, setGuides] = React.useState<EditorialGuide[]>([]);
  const [scope, setScope] = React.useState<"workspace" | "document">("document");
  const [lesson, setLesson] = React.useState<EditorialLesson>(blank);
  const [reviews, setReviews] = React.useState<CraftReview[]>([]);
  const [selected, setSelected] = React.useState<string>();
  const [mediaUrl, setMediaUrl] = React.useState<string>();
  const [start, setStart] = React.useState(0);
  const [duration, setDuration] = React.useState(3);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string>();
  const guide = guides.find((item) => item.scope === scope);
  const review = reviews.find((item) => item.assetId === selected) || reviews[0];

  React.useEffect(() => {
    const controller = new AbortController();
    void craftApi.editorialGuides(documentId, controller.signal).then((value) => setGuides(value.guides))
      .catch(() => { if (!controller.signal.aborted) setError("Não foi possível carregar o guia de edição."); });
    return () => controller.abort();
  }, [documentId, revision]);

  React.useEffect(() => {
    const controller = new AbortController();
    let loading = false;
    const refresh = async () => {
      if (loading) return;
      loading = true;
      try {
        const result = await craftApi.reviews(documentId, controller.signal);
        if (!controller.signal.aborted) setReviews(result.reviews);
      } catch { /* A subsequent refresh can recover a temporarily unavailable review. */ }
      finally { loading = false; }
    };
    void refresh();
    const timer = disabled ? window.setInterval(() => void refresh(), 4000) : undefined;
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [documentId, revision, disabled]);

  React.useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | undefined;
    setMediaUrl(undefined);
    if (review) void craftApi.reviewMedia(documentId, review.assetId, controller.signal).then((blob) => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(blob); setMediaUrl(objectUrl);
    }).catch(() => { if (!controller.signal.aborted) setError("Não foi possível abrir a prévia."); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [documentId, review?.assetId]);

  async function save(value: EditorialLesson) {
    if (!guide) return;
    setBusy(true); setError(undefined);
    const { status: _status, ...content } = value;
    try {
      const saved = await craftApi.saveEditorialLesson(documentId, revision, guide, {
        ...content, useWhen: content.useWhen.map((item) => item.trim()).filter(Boolean),
        avoidWhen: content.avoidWhen.map((item) => item.trim()).filter(Boolean),
      });
      setGuides((current) => current.map((item) => item.scope === saved.scope ? saved : item));
      setLesson(blank);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível salvar a preferência.");
      try { setGuides((await craftApi.editorialGuides(documentId)).guides); } catch { /* Keep the editable form. */ }
    } finally { setBusy(false); }
  }

  return <div className="craft-editorial-guide">
    {error && <p role="alert">{error}</p>}
    <details>
      <summary>Preferências de edição</summary>
      <label>Aplicar<select value={scope} disabled={busy || disabled} onChange={(event) => { setScope(event.target.value as typeof scope); setLesson(blank); }}>
        <option value="document">Neste projeto</option><option value="workspace">Nos próximos projetos deste espaço</option>
      </select></label>
      {(guide?.lessons || []).map((item) => <div className="craft-editorial-lesson" key={item.id}>
        <strong>{item.situation}</strong><p>{item.correction}</p>
        <small>{item.status === "approved" ? "Preferência salva" : "Sugestão do editor"}</small>
        <button disabled={busy || disabled} onClick={() => setLesson(item)}>Revisar</button>
        {item.status === "candidate" && <button disabled={busy || disabled} onClick={() => void save(item)}>Aprovar preferência</button>}
      </div>)}
      <form onSubmit={(event) => { event.preventDefault(); void save(lesson); }}>
        <label>Situação<input required value={lesson.situation} maxLength={2000} disabled={busy || disabled}
          onChange={(event) => setLesson({ ...lesson, situation: event.target.value })} /></label>
        <label>Como a edição deve ficar<textarea required value={lesson.correction} maxLength={4000} disabled={busy || disabled}
          onChange={(event) => setLesson({ ...lesson, correction: event.target.value })} /></label>
        <label>Usar quando<textarea required value={lesson.useWhen.join("\n")} disabled={busy || disabled}
          onChange={(event) => setLesson({ ...lesson, useWhen: event.target.value.split("\n") })} /></label>
        <label>Evitar quando<textarea value={lesson.avoidWhen.join("\n")} disabled={busy || disabled}
          onChange={(event) => setLesson({ ...lesson, avoidWhen: event.target.value.split("\n") })} /></label>
        <button disabled={busy || disabled || !guide}>{busy ? "Salvando…" : "Salvar preferência"}</button>
      </form>
    </details>
    <details>
      <summary>Revisão com movimento e som</summary>
      <form onSubmit={async (event) => {
        event.preventDefault(); setBusy(true); setError(undefined);
        try {
          const next = await craftApi.reviewClip(documentId, revision, start, duration);
          setReviews((current) => [next, ...current.filter((item) => item.assetId !== next.assetId)]); setSelected(next.assetId);
        } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível preparar o trecho."); }
        finally { setBusy(false); }
      }}>
        <label>Início em segundos<input type="number" min={0} step="0.1" value={start} disabled={busy || disabled} onChange={(event) => setStart(Number(event.target.value))} /></label>
        <label>Duração em segundos<input type="number" min="0.1" step="0.1" value={duration} disabled={busy || disabled} onChange={(event) => setDuration(Number(event.target.value))} /></label>
        <button disabled={busy || disabled}>{busy ? "Preparando trecho…" : "Preparar prévia local"}</button>
      </form>
      {reviews.length > 0 && <label>Prévia<select value={review?.assetId} onChange={(event) => setSelected(event.target.value)}>
        {reviews.map((item) => <option key={item.assetId} value={item.assetId}>Revisão {item.documentRevision}{item.draftBatch != null ? ` · edição ${item.draftBatch}` : ""} · {item.report.interval.startSeconds.toFixed(2)}–{item.report.interval.endSeconds.toFixed(2)} s</option>)}
      </select></label>}
      {mediaUrl && review && (review.mediaType.startsWith("audio/")
        ? <audio controls src={mediaUrl} /> : <video controls playsInline className="craft-output-video" src={mediaUrl} />)}
      {review && <p>Quadros observados {review.report.visual.sampledSeconds.length}.
        {review.report.audio.status === "measured" ? ` Nível médio ${review.report.audio.rmsDbfs} dBFS. Eventos sonoros medidos ${review.report.audio.onsetCount}.` : " Sem faixa de áudio."}
        {review.report.visual.nextPage != null && " O editor pode consultar os próximos quadros do trecho."}</p>}
    </details>
  </div>;
}
