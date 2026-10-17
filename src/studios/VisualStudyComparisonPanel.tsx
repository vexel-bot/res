import React from "react";
import {apiFetch, apiFetchBlob} from "../api";
import "./visual-study-comparison.css";

export type StudySession = {id: string; language: string; status: string; blockers: string[];
  labels: {label: string; assetId: string; checksum: string; documentId: string; documentRevision: number}[]};

export function VisualStudyComparisonPanel({workspaceId, session, onRecorded}: {
  workspaceId: string; session: StudySession; onRecorded: () => void;
}) {
  const [urls, setUrls] = React.useState<Record<string, string>>({});
  const [selected, setSelected] = React.useState("");
  const [scores, setScores] = React.useState<Record<string, string>>({});
  const [checked, setChecked] = React.useState<Record<string, boolean>>({});
  const [notes, setNotes] = React.useState("");
  const [findings, setFindings] = React.useState<{sceneId: string; startSeconds: string; endSeconds: string;
    cause: string; observation: string; correction: string}[]>([]);
  const [message, setMessage] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const dialog = React.useRef<HTMLDialogElement>(null);
  React.useEffect(() => {
    if (Object.keys(urls).length === 3 && dialog.current && !dialog.current.open) dialog.current.showModal();
  }, [urls]);
  const latest = React.useRef(0);
  React.useEffect(() => {
    latest.current++;
    setUrls({}); setSelected(""); setScores({}); setChecked({}); setNotes(""); setFindings([]); setMessage("");
  }, [session.id, session.status]);
  React.useEffect(() => () => Object.values(urls).forEach(URL.revokeObjectURL), [urls]);
  React.useEffect(() => () => {latest.current++;}, []);
  const prefix = `/api/v1/studios/v1/workspaces/${encodeURIComponent(workspaceId)}/visual-study-comparisons/${session.id}`;
  const scoresValid = ["clarity", "rhythm", "continuity", "finish", "suitability"].every(k => /^[1-5]$/.test(scores[k] ?? ""));
  const findingsValid = findings.every(f => f.startSeconds.trim() && f.endSeconds.trim() &&
    Number(f.startSeconds) >= 0 && Number(f.endSeconds) > Number(f.startSeconds) && Number(f.endSeconds) <= 15 &&
    f.observation.trim() && f.correction.trim());
  async function open() {
    setBusy(true); const generation = latest.current;
    try {
      const current = await apiFetch<StudySession>(prefix);
      if (current.status === "stale") throw new Error("Comparação obsoleta: crie outra sessão com os renders atuais.");
      const blobs = await Promise.all(current.labels.map(item => apiFetchBlob(`/api/v1/assets/${item.assetId}/content`)));
      if (generation !== latest.current) return;
      setUrls(Object.fromEntries(current.labels.map((item, i) => [item.label, URL.createObjectURL(blobs[i])])));
    } catch(error) {setMessage(error instanceof Error ? error.message : "Falha ao abrir a comparação.");}
    finally {setBusy(false);}
  }
  async function submit() {
    const reference = session.labels.find(item => item.label === selected);
    if (!reference || !notes.trim() || !scoresValid || !findingsValid) return;
    setBusy(true);
    try {
      // Numeric evaluation is supplied by the human, never by QC or an agent.
      await apiFetch(`/api/v1/studios/v1/documents/${reference.documentId}/renders/${reference.assetId}/visual-review`, {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
          expectedDocumentRevision: reference.documentRevision, renderChecksum: reference.checksum,
          clarity: Number(scores.clarity), rhythm: Number(scores.rhythm), continuity: Number(scores.continuity),
          finish: Number(scores.finish), suitability: Number(scores.suitability),
          fullVideoInspected: !!checked.full, mobileInspected: !!checked.mobile, notes,
          findings: findings.map(f => ({...f, sceneId: f.sceneId.trim() || null,
            startSeconds: Number(f.startSeconds), endSeconds: Number(f.endSeconds)})),
        }),
      });
      const review = await apiFetch<{status: string}>(prefix + "/review", {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
          preferredLabel: selected, fullVideoInspected: !!checked.full, mobileInspected: !!checked.mobile,
          blindReviewCompleted: !!checked.blind, sameMaterialsConfirmed: !!checked.materials,
          controlSimplicityConfirmed: !!checked.control, unrecordedManualCorrections: !!checked.hidden, notes,
        }),
      });
      setMessage(`Avaliação registrada: ${review.status}.`); onRecorded();
    } catch(error) {setMessage(error instanceof Error ? error.message : "Falha ao registrar avaliação.");}
    finally {setBusy(false);}
  }
  return <article aria-label="Comparação cega dos estudos próprios">
    <h4>Estudo {session.language === "interface_capture" ? "de interface real" : "de motion"} · comparação cega</h4>
    <p>Estado: {session.status}. Mesmos materiais; duas montagens dirigidas e controle simples. Direção assistida registrada.</p>
    {session.blockers.map(code => <p key={code}>{code}</p>)}
    <button disabled={busy || session.status === "stale"} onClick={open}>Abrir três opções</button>
    {Object.keys(urls).length === 3 && <dialog ref={dialog} className="vs-study-dialog" aria-label="Revisão cega em tamanho de celular"
      style={{width: "min(1040px, 94vw)", maxHeight: "85vh", overflow: "auto", padding: 24,
        position: "fixed", inset: 0, margin: "auto",
        background: "#171c20", color: "#f4ece6", border: "1px solid #72584b", borderRadius: 12}}>
      <h3>Compare as três opções sem identificar a variante</h3>
      <button onClick={() => dialog.current?.close()}>Fechar comparação</button>
      <div style={{display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 24, margin: "20px 0"}}>
        {session.labels.map(item => <div key={item.label}>
          <b style={{display: "block"}}>Opção {item.label}</b><video controls playsInline src={urls[item.label]}
            style={{display: "block", width: 280, maxWidth: "100%"}} />
        </div>)}
      </div>
      <label>Opção preferida<select value={selected} onChange={e => setSelected(e.target.value)}>
        <option value="">Selecione após assistir</option>{session.labels.map(item => <option key={item.label}>{item.label}</option>)}
      </select></label>
      {[["clarity", "Clareza"], ["rhythm", "Ritmo"], ["continuity", "Continuidade"], ["finish", "Acabamento"],
        ["suitability", "Adequação à mensagem"]].map(([key, label]) =>
        <label key={key}>{label} (1–5)<input type="number" min={1} max={5} value={scores[key] ?? ""}
          onChange={e => setScores(previous => ({...previous, [key]: e.target.value}))} /></label>)}
      {[["full", "Assisti aos três vídeos completos, em velocidade normal e com som"], ["mobile", "Conferi em tamanho de celular"],
        ["blind", "Comparei sem saber a variante"], ["materials", "Conferi que usam os mesmos materiais"],
        ["control", "O controle usa uma sequência simples de estados ou trechos"],
        ["hidden", "Houve correção manual não registrada"]].map(([key, label]) => <label key={key}>
          <input type="checkbox" checked={checked[key] ?? false} onChange={e => setChecked(previous => ({...previous, [key]: e.target.checked}))} />{label}
        </label>)}
      <label>Comparação e diferenças restantes<textarea value={notes} onChange={e => setNotes(e.target.value)}
        placeholder="Explique a preferência e as diferenças restantes frente às referências." /></label>
      {findings.map((finding, index) => <fieldset key={index}><legend>Achado {index + 1}</legend>
        {[["sceneId", "Cena (ID, opcional)"], ["startSeconds", "Início (s)"], ["endSeconds", "Fim (s)"],
          ["observation", "O que foi observado"], ["correction", "Mudança executável"]].map(([key, label]) =>
          <label key={key}>{label}<input value={finding[key as keyof typeof finding]}
            onChange={e => setFindings(all => all.map((f, i) => i === index ? {...f, [key]: e.target.value} : f))} /></label>)}
        <label>Causa<select value={finding.cause} onChange={e => setFindings(all => all.map((f, i) =>
          i === index ? {...f, cause: e.target.value} : f))}>
          {[["material", "Material"], ["direction", "Direção/composição"], ["translation", "Tradução para runtime"],
            ["render", "Falha no render"], ["motion", "Movimento"], ["mask", "Máscara"], ["readability", "Leitura"],
            ["continuity", "Continuidade"], ["sound", "Som"], ["cut", "Corte"], ["framing", "Enquadramento"]].map(([value, label]) =>
              <option key={value} value={value}>{label}</option>)}
        </select></label>
        <button onClick={() => setFindings(all => all.filter((_, i) => i !== index))}>Remover achado</button>
      </fieldset>)}
      <button disabled={findings.length >= 40} onClick={() => setFindings(all => [...all, {sceneId: "", startSeconds: "",
        endSeconds: "", cause: "direction", observation: "", correction: ""}])}>Adicionar achado com intervalo e correção</button>
      <button disabled={busy || !selected || !notes.trim() || !scoresValid || !findingsValid} onClick={submit}>Registrar avaliação humana</button>
      {message && <p role="status">{message}</p>}
    </dialog>}
    {Object.keys(urls).length !== 3 && message && <p role="status">{message}</p>}
  </article>;
}
