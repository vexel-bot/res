import React from "react";
import { productApi } from "../../api/productApi";
import { identityApi, type IdentityEvaluation, type ReviewTarget } from "./identityApi";

export type ReviewSelection = ReviewTarget & { name: string; version: number; capabilities: string[] };
const checkLabels: Record<string, string> = {
  "pt-br-speaker-review": "Correspondência da voz",
  "appearance-match": "Correspondência da aparência",
  "identity-match": "Correspondência da identidade",
  "pt-br-listening-review": "Pronúncia e qualidade do áudio",
  "motion-artifact-review": "Movimento e qualidade visual",
  "image-artifact-review": "Qualidade da imagem",
  "artifact-review": "Qualidade da prévia",
  "private-preview-observed": "Prévia examinada pelo responsável",
};
const errorMessage = (error: unknown) => {
  const message = error instanceof Error ? error.message : "Não foi possível concluir a revisão.";
  const labels: Record<string, string> = {
    identity_governance_role_required: "Somente responsáveis ou administradores da marca podem revisar versões.",
    passed_identity_evaluation_required: "Registre primeiro uma avaliação aprovada com uma prévia privada.",
    private_preview_asset_required: "A prévia não está mais disponível. Cadastre uma nova avaliação.",
    identity_version_already_reviewed: "Esta versão já foi revisada. Atualize a biblioteca para conferir o resultado.",
    consent_expired: "A autorização venceu. Renove-a antes de aprovar a versão.",
    consent_revoked: "A autorização foi revogada. Esta versão não pode ser aprovada.",
  };
  return labels[message] || message;
};

function Preview({ blob, name }: { blob: Blob; name: string }) {
  const [url, setUrl] = React.useState<string>();
  React.useEffect(() => {
    const owned = URL.createObjectURL(blob);
    setUrl(owned);
    return () => URL.revokeObjectURL(owned);
  }, [blob]);
  if (!url) return <p role="status">Abrindo prévia…</p>;
  if (blob.type.startsWith("audio/")) return <audio controls src={url} aria-label={name} />;
  if (blob.type.startsWith("video/")) return <video controls src={url} aria-label={name} />;
  if (blob.type.startsWith("image/")) return <img src={url} alt={name} />;
  return <p role="alert">A prévia precisa ser uma imagem, um áudio ou um vídeo.</p>;
}

function StoredPreview({ id }: { id: string }) {
  const [blob, setBlob] = React.useState<Blob>();
  const [error, setError] = React.useState<string>();
  React.useEffect(() => {
    const controller = new AbortController();
    void productApi.studioAssetBlob(id, controller.signal).then(value => {
      if (!controller.signal.aborted) setBlob(value);
    }).catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)); });
    return () => controller.abort();
  }, [id]);
  return error ? <p role="alert">{error}</p> : blob ? <Preview blob={blob} name="Prévia privada registrada" /> : <p role="status">Carregando prévia privada…</p>;
}

/** Human review records observations only. It never qualifies an inference provider. */
export function IdentityReview({ target, workspaceId, onClose, onReviewed }: {
  target: ReviewSelection;
  workspaceId: string;
  onClose: () => void;
  onReviewed: (notice: string) => void;
}) {
  const [evaluations, setEvaluations] = React.useState<IdentityEvaluation[]>();
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [refresh, setRefresh] = React.useState(0);
  const [file, setFile] = React.useState<File>();
  const [result, setResult] = React.useState<"passed" | "failed">("passed");
  const [fidelity, setFidelity] = React.useState(false);
  const [quality, setQuality] = React.useState(false);
  const [observed, setObserved] = React.useState(false);
  const [notes, setNotes] = React.useState("");
  const [comment, setComment] = React.useState("");
  const [confirmed, setConfirmed] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const alive = React.useRef(true);
  const heading = React.useRef<HTMLHeadingElement>(null);
  const fileInput = React.useRef<HTMLInputElement>(null);
  const uploads = React.useRef(new Map<File, string>());
  React.useEffect(() => {
    alive.current = true;
    heading.current?.focus();
    return () => { alive.current = false; };
  }, []);
  React.useEffect(() => {
    const controller = new AbortController();
    void identityApi.evaluations(target, controller.signal).then(value => {
      if (!controller.signal.aborted) { setEvaluations(value); setConfirmed(false); }
    }).catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)); });
    return () => controller.abort();
  }, [target, refresh]);
  const voice = target.kind === "voices";
  const motion = !voice && target.capabilities.includes("avatar.generate");
  const latest = evaluations?.[0];
  const validType = file && (voice ? /^(audio|video)\//.test(file.type) : motion ? file.type.startsWith("video/") : /^(image|video)\//.test(file.type));
  const canSave = !busy && !!evaluations && !!validType && observed && notes.trim().length >= 3 && (result === "failed" || (fidelity && quality));
  const evaluate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSave || !file) return;
    setBusy(true); setError(undefined); setNotice(undefined);
    try {
      let assetId = uploads.current.get(file);
      if (!assetId) {
        const asset = await productApi.uploadStudioAsset(workspaceId, file, `Prévia privada · ${target.name} · v${target.version}`);
        assetId = asset.id;
        uploads.current.set(file, assetId);
      }
      const saved = await identityApi.evaluate(target, {
        status: result, evaluatorKind: "human", previewAssetIds: [assetId],
        checks: [
          { code: voice ? "pt-br-speaker-review" : "appearance-match", passed: fidelity },
          { code: voice ? "pt-br-listening-review" : motion ? "motion-artifact-review" : "image-artifact-review", passed: quality },
          { code: "private-preview-observed", passed: observed },
        ], notes: notes.trim(),
      });
      if (!alive.current) return;
      setEvaluations(previous => [saved, ...(previous || []).filter(item => item.id !== saved.id)]);
      setNotice(result === "passed" ? "Avaliação registrada. A aprovação da versão é uma decisão separada, abaixo." : "Avaliação registrada com pendências. A versão continua indisponível para seleção.");
      setFile(undefined); setObserved(false); setConfirmed(false);
      if (fileInput.current) fileInput.current.value = "";
    } catch (failure) {
      if (alive.current) { setError(errorMessage(failure)); setRefresh(value => value + 1); }
    } finally { if (alive.current) setBusy(false); }
  };
  const review = async (action: "approve" | "reject") => {
    if (busy || comment.trim().length < 3 || (action === "approve" && (latest?.status !== "passed" || !confirmed))) return;
    setBusy(true); setError(undefined);
    try {
      const saved = await identityApi.review(target, { action, comment: comment.trim() });
      if (saved.id !== target.versionId || saved.status !== (action === "approve" ? "active" : "rejected")) throw new Error("Resposta de revisão inesperada. Atualize a biblioteca para conferir a versão.");
      if (alive.current) onReviewed(action === "approve" ? "Versão aprovada para seleção. A geração depende de um motor disponível e das autorizações vigentes." : "Versão devolvida para ajustes e retirada da seleção.");
    } catch (failure) {
      if (alive.current) { setError(errorMessage(failure)); setRefresh(value => value + 1); }
    } finally { if (alive.current) setBusy(false); }
  };
  return <section className="il-review" aria-labelledby="il-review-title" aria-busy={busy}>
    <header>
      <div><small>AVALIAÇÃO PRIVADA</small><h2 id="il-review-title" ref={heading} tabIndex={-1}>{target.name} · versão {target.version}</h2></div>
      <button type="button" disabled={busy} onClick={onClose}>Fechar avaliação</button>
    </header>
    <p>Confira uma prévia real para esta versão e registre o que observou. A aprovação permite escolher o cadastro; ela não instala nem habilita um motor de geração.</p>
    {error && <div className="il-error" role="alert">{error}<button type="button" disabled={busy} onClick={() => { setError(undefined); setRefresh(value => value + 1); }}>Recarregar avaliações</button></div>}
    {notice && <p className="il-notice" role="status">{notice}</p>}
    {!evaluations && !error && <p role="status">Carregando avaliações…</p>}
    <form onSubmit={event => void evaluate(event)}>
      <fieldset disabled={busy || !evaluations}>
        <legend>1. Registrar avaliação</legend>
        <label>Prévia privada desta versão<input ref={fileInput} type="file" accept={voice ? "audio/*,video/*" : motion ? "video/*" : "image/*,video/*"} onChange={event => {
          setFile(event.target.files?.[0]); setObserved(false); setFidelity(false); setQuality(false);
        }} /></label>
        <p>{voice ? "Use uma fala produzida com a voz cadastrada, para avaliar pronúncia e identidade vocal." : motion ? "Esta versão inclui uso em avatar. Use um vídeo para conferir aparência e movimento." : "Use uma imagem ou um vídeo para conferir a aparência."} A amostra original de cadastro não comprova a qualidade de uma geração.</p>
        {file && !validType && <p role="alert">Escolha um arquivo no formato indicado.</p>}
        {file && validType && <div className="il-review-media"><Preview key={`${file.name}:${file.lastModified}`} blob={file} name="Prévia selecionada para avaliação" /></div>}
        <label className="il-declaration"><input type="checkbox" checked={observed} onChange={e => setObserved(e.target.checked)} />Examinei a prévia e confirmei que ela pertence a esta versão.</label>
        <label className="il-declaration"><input type="checkbox" checked={fidelity} onChange={e => setFidelity(e.target.checked)} />{voice ? "A voz corresponde à referência autorizada." : "A aparência corresponde à referência autorizada."}</label>
        <label className="il-declaration"><input type="checkbox" checked={quality} onChange={e => setQuality(e.target.checked)} />{voice ? "Conferi a pronúncia em português e a qualidade do áudio." : motion ? "Conferi o movimento e a ausência de defeitos visuais relevantes." : "Conferi a qualidade visual e a ausência de defeitos relevantes."}</label>
        <label>Resultado da avaliação<select value={result} onChange={e => setResult(e.target.value as "passed" | "failed")}><option value="passed">Aprovada na avaliação</option><option value="failed">Com pendências</option></select></label>
        <label>Observações da avaliação<textarea minLength={3} maxLength={4000} required value={notes} onChange={e => setNotes(e.target.value)} /></label>
        <button type="submit" disabled={!canSave}>{busy ? "Salvando…" : "Registrar avaliação"}</button>
      </fieldset>
    </form>
    <section className="il-review-history" aria-label="Avaliações registradas">
      <h3>Avaliações registradas</h3>
      {evaluations?.length === 0 && <p>Nenhuma avaliação registrada para esta versão.</p>}
      {evaluations?.map((item, index) => <details key={item.id} open={index === 0}>
        <summary>{index === 0 ? "Mais recente · " : ""}{item.status === "passed" ? "Aprovada" : "Com pendências"} · {new Date(item.evaluatedAt).toLocaleString("pt-BR")}</summary>
        <p>{item.evaluatorKind === "human" ? "Revisão humana" : item.evaluatorKind === "automated" ? "Avaliação automática" : "Avaliação combinada"} · responsável registrado no histórico da marca</p>
        <p>{item.notes}</p>
        <ul>{item.checks?.map(check => <li key={check.code}>{checkLabels[check.code] || "Critério adicional"}: {check.passed ? "conferido" : "pendente"}{check.detail ? ` · ${check.detail}` : ""}</li>)}</ul>
        {item.previewAssetIds?.map(id => <PrivatePreview key={id} id={id} />)}
      </details>)}
    </section>
    <fieldset disabled={busy || !evaluations}>
      <legend>2. Decidir sobre a versão</legend>
      <label>Comentário da decisão<textarea minLength={3} maxLength={4000} value={comment} onChange={e => setComment(e.target.value)} /></label>
      <label className="il-declaration"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Conferi a avaliação mais recente e suas prévias para aprovar esta versão.</label>
      <div className="il-review-actions">
        <button type="button" className="il-primary" disabled={busy || latest?.status !== "passed" || !confirmed || comment.trim().length < 3} onClick={() => void review("approve")}>Aprovar versão para seleção</button>
        <button type="button" disabled={busy || comment.trim().length < 3} onClick={() => void review("reject")}>Devolver para ajustes</button>
      </div>
    </fieldset>
  </section>;
}

function PrivatePreview({ id }: { id: string }) {
  const [open, setOpen] = React.useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}><summary>Abrir prévia privada</summary>
    {open && <div className="il-review-media"><StoredPreview id={id} /></div>}
  </details>;
}
