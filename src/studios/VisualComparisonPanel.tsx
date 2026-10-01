import React from "react";
import { apiFetch, apiFetchBlob } from "../api";
import type { StudioDocumentRecord } from "../api/productApi";

type Render = { runId: string; assetId?: string; renderChecksum?: string; documentId: string; documentRevision: number;
  qualityPhaseId?: string; blockers: string[] };
type Clip = { assetId: string; startSeconds: number; durationSeconds: number };
type Preview = { role: "edit_a" | "edit_b" | "concat_control"; url: string; label: string };
type Session = { documentId: string; revision: number; editARunId: string; editBRunId: string;
  editAChecksum: string; editBChecksum: string; controlAssetId: string; controlChecksum: string; controlEdl: Clip[] };

export function VisualComparisonPanel({ document, renders, onRecorded }: {
  document: StudioDocumentRecord; renders: Render[]; onRecorded: () => void;
}) {
  const eligible = renders.filter(item => item.documentId === document.documentId
    && item.documentRevision === document.revision
    && item.qualityPhaseId === "visual-quality-2026-10-01" && item.assetId && item.renderChecksum
    && !item.blockers.some(code => ["render_missing", "render_checksum_mismatch", "document_revision_stale",
      "render_document_binding_mismatch"].includes(code)));
  const videoAssets = document.assets.filter(asset => asset.mediaType.startsWith("video/"));
  const [editA, setEditA] = React.useState("");
  const [editB, setEditB] = React.useState("");
  const [controlId, setControlId] = React.useState("");
  const [clips, setClips] = React.useState<Clip[]>([
    { assetId: "", startSeconds: 0, durationSeconds: 7.5 },
    { assetId: "", startSeconds: 0, durationSeconds: 7.5 },
  ]);
  const [previews, setPreviews] = React.useState<Preview[]>([]);
  const [session, setSession] = React.useState<Session | null>(null);
  const generation = React.useRef(0);
  const [preferredSlot, setPreferredSlot] = React.useState("");
  const [blind, setBlind] = React.useState(false);
  const [normalSpeed, setNormalSpeed] = React.useState(false);
  const [mobile, setMobile] = React.useState(false);
  const [straightConcat, setStraightConcat] = React.useState(false);
  const [sameMaterials, setSameMaterials] = React.useState(false);
  const [unrecordedManual, setUnrecordedManual] = React.useState(false);
  const [notes, setNotes] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState("");
  React.useEffect(() => () => previews.forEach(item => URL.revokeObjectURL(item.url)), [previews]);
  React.useEffect(() => () => { generation.current++; }, []);
  const renderSignature = eligible.map(item => `${item.runId}:${item.renderChecksum}`).sort().join("|");
  React.useEffect(() => {
    generation.current++;
    setPreviews([]); setPreferredSlot(""); setEditA(""); setEditB(""); setControlId("");
    setSession(null); setBusy(false); setMessage(""); setNotes("");
    setBlind(false); setNormalSpeed(false); setMobile(false); setStraightConcat(false);
    setSameMaterials(false); setUnrecordedManual(false);
  }, [document.documentId, document.revision, renderSignature]);
  if (eligible.length < 2) return <p>Comparação cega: aguardando duas montagens desta fase no mesmo projeto.</p>;
  const first = eligible.find(item => item.runId === editA);
  const second = eligible.find(item => item.runId === editB);
  const control = videoAssets.find(asset => asset.id === controlId);
  const distinctVideos = first && second && control && first.runId !== second.runId
    && new Set([first.renderChecksum, second.renderChecksum, control.checksum]).size === 3;
  const edlValid = clips.length >= 2 && clips.length <= 20 && new Set(clips.map(clip => clip.assetId)).size >= 2
    && clips.every(clip => clip.assetId && clip.assetId !== controlId && Number.isFinite(clip.startSeconds)
      && Number.isFinite(clip.durationSeconds) && clip.startSeconds >= 0 && clip.durationSeconds > 0)
    && Math.abs(clips.reduce((sum, clip) => sum + clip.durationSeconds, 0) - 15) <= 0.05;
  async function begin() {
    if (busy || !first?.assetId || !second?.assetId || !first.renderChecksum || !second.renderChecksum
      || !control || !edlValid || !distinctVideos) return;
    const currentGeneration = generation.current;
    const captured: Session = { documentId: document.documentId, revision: document.revision,
      editARunId: first.runId, editBRunId: second.runId, controlAssetId: control.id,
      editAChecksum: first.renderChecksum, editBChecksum: second.renderChecksum,
      controlChecksum: control.checksum, controlEdl: clips.map(clip => ({ ...clip })) };
    setBusy(true); setMessage("");
    try {
      const candidates = [
        { role: "edit_a" as const, assetId: first.assetId },
        { role: "edit_b" as const, assetId: second.assetId },
        { role: "concat_control" as const, assetId: control.id },
      ];
      const blobs = await Promise.all(candidates.map(item => apiFetchBlob(`/api/v1/assets/${item.assetId}/content`)));
      if (currentGeneration !== generation.current) return;
      const random = new Uint32Array(candidates.length);
      crypto.getRandomValues(random);
      const shuffled = candidates.map((item, index) => ({ role: item.role,
        url: URL.createObjectURL(blobs[index]), label: "", order: random[index] }))
        .sort((a, b) => a.order - b.order)
        .map((item, index) => ({ role: item.role, url: item.url, label: `Opção ${index + 1}` }));
      setPreviews(shuffled);
      setSession(captured);
      setPreferredSlot(""); setBlind(false); setNormalSpeed(false); setMobile(false);
      setStraightConcat(false); setSameMaterials(false); setUnrecordedManual(false); setNotes("");
    } catch {
      if (currentGeneration === generation.current) setMessage("Não foi possível abrir os três vídeos privados para a comparação.");
    } finally { if (currentGeneration === generation.current) setBusy(false); }
  }
  async function submit() {
    if (busy || !session || !preferredSlot || !notes.trim()) return;
    const currentGeneration = generation.current;
    setBusy(true); setMessage("");
    try {
      const selected = previews.find(item => item.label === preferredSlot);
      if (!selected) throw new Error("Escolha uma opção após assistir aos três vídeos.");
      const receipt = await apiFetch<{ status: string }>(
        `/api/v1/studios/v1/documents/${session.documentId}/visual-quality-comparison`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
            expectedDocumentRevision: session.revision, editARunId: session.editARunId, editBRunId: session.editBRunId,
            editAChecksum: session.editAChecksum, editBChecksum: session.editBChecksum,
            controlAssetId: session.controlAssetId, controlChecksum: session.controlChecksum, controlEdl: session.controlEdl,
            preferred: selected.role, blindReviewCompleted: blind, normalSpeedInspected: normalSpeed,
            mobileInspected: mobile, straightConcatenationConfirmed: straightConcat,
            sameMaterialsConfirmed: sameMaterials, unrecordedManualCorrections: unrecordedManual,
            notes: notes.trim(),
          }),
        });
      if (currentGeneration !== generation.current) return;
      setMessage(receipt.status === "passed" ? "Comparação registrada: montagem dirigida preferida."
        : "Comparação registrada; os critérios ainda não foram atendidos.");
      onRecorded();
    } catch (error) {
      if (currentGeneration === generation.current) setMessage(error instanceof Error ? error.message : "Não foi possível registrar a comparação.");
    } finally { if (currentGeneration === generation.current) setBusy(false); }
  }
  function updateClip(index: number, patch: Partial<Clip>) {
    setClips(old => old.map((clip, current) => current === index ? { ...clip, ...patch } : clip));
  }
  return <details className="vs-comparison" aria-label="Comparação cega de montagens">
    <summary>Comparar duas montagens e a concatenação de controle</summary>
    {!previews.length ? <div>
      <p>Prepare os três MP4s com os mesmos materiais. Importe e anexe a concatenação de 15 s com áudio pelo Acervo.</p>
      <label>Montagem A<select value={editA} onChange={event => setEditA(event.target.value)}>
        <option value="">Selecione um render</option>{eligible.map(item => <option key={item.runId} value={item.runId}>
          {item.runId.slice(0, 12)} · {item.renderChecksum?.slice(0, 12)}</option>)}</select></label>
      <label>Montagem B<select value={editB} onChange={event => setEditB(event.target.value)}>
        <option value="">Selecione outro render</option>{eligible.map(item => <option key={item.runId} value={item.runId}>
          {item.runId.slice(0, 12)} · {item.renderChecksum?.slice(0, 12)}</option>)}</select></label>
      <label>Concatenação de controle<select value={controlId} onChange={event => setControlId(event.target.value)}>
        <option value="">Selecione o MP4 anexado</option>{videoAssets.map(asset => <option key={asset.id} value={asset.id}>
          {asset.id.slice(0, 12)} · {asset.checksum.slice(0, 12)}</option>)}</select></label>
      <p>EDL do controle — origem e duração de cada trecho, somando 15 s:</p>
      {clips.map((clip, index) => <div className="vs-comparison-edl" key={index}>
        <label>Fonte {index + 1}<select value={clip.assetId} onChange={event => updateClip(index, { assetId: event.target.value })}>
          <option value="">Selecione</option>{videoAssets.filter(asset => asset.id !== controlId).map(asset =>
            <option key={asset.id} value={asset.id}>{asset.id.slice(0, 12)}</option>)}</select></label>
        <label>Início (s)<input type="number" min="0" step="0.01" value={clip.startSeconds}
          onChange={event => updateClip(index, { startSeconds: Number(event.target.value) })} /></label>
        <label>Duração (s)<input type="number" min="0.01" max="15" step="0.01" value={clip.durationSeconds}
          onChange={event => updateClip(index, { durationSeconds: Number(event.target.value) })} /></label>
        <button type="button" disabled={clips.length <= 2} onClick={() => setClips(old => old.filter((_, current) => current !== index))}>Remover trecho {index + 1}</button>
      </div>)}
      <button type="button" disabled={busy || clips.length >= 20} onClick={() => setClips(old => [...old, { assetId: "", startSeconds: 0, durationSeconds: 1 }])}>Adicionar trecho</button>
      <button type="button" disabled={busy || !distinctVideos || !edlValid}
        onClick={() => void begin()}>Iniciar reprodução sem rótulos</button>
    </div> : <div>
      <p>Assista aos três vídeos completos em velocidade normal e tamanho de celular antes de escolher.</p>
      <div className="vs-comparison-previews">{previews.map(item => <label key={item.role}>
        <span>{item.label}</span><video controls playsInline src={item.url} aria-label={item.label} />
        <input type="radio" name="visual-comparison-preference" value={item.label} checked={preferredSlot === item.label}
          onChange={() => setPreferredSlot(item.label)} /> Preferida
      </label>)}</div>
      <label><input type="checkbox" checked={blind} onChange={event => setBlind(event.target.checked)} /> Comparei sem saber qual era a montagem dirigida ou o controle</label>
      <label><input type="checkbox" checked={normalSpeed} onChange={event => setNormalSpeed(event.target.checked)} /> Vi os três vídeos completos em velocidade normal</label>
      <label><input type="checkbox" checked={mobile} onChange={event => setMobile(event.target.checked)} /> Conferi a leitura em tamanho de celular</label>
      <label><input type="checkbox" checked={straightConcat} onChange={event => setStraightConcat(event.target.checked)} /> Conferi que o controle é uma concatenação direta da EDL</label>
      <label><input type="checkbox" checked={sameMaterials} onChange={event => setSameMaterials(event.target.checked)} /> Confirmei os mesmos materiais nos três vídeos</label>
      <label><input type="checkbox" checked={unrecordedManual} onChange={event => setUnrecordedManual(event.target.checked)} /> Houve correção manual não registrada</label>
      <label>Por que escolheu esta opção?<textarea value={notes} onChange={event => setNotes(event.target.value)} maxLength={4000} /></label>
      <button type="button" disabled={busy || !preferredSlot || !notes.trim() || !blind || !normalSpeed || !mobile || !straightConcat || !sameMaterials}
        onClick={() => void submit()}>Registrar comparação</button>
      <button type="button" disabled={busy} onClick={() => { setPreviews([]); setSession(null); }}>Voltar à preparação</button>
    </div>}
    {message && <p role="status">{message}</p>}
  </details>;
}
