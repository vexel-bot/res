import React from "react";
import {
  Download,
  Film,
  Music2,
  Plus,
  Save,
  Scissors,
  Trash2,
  Type,
  Upload,
  Undo2,
  Redo2,
} from "lucide-react";
import { apiFetch, APIError } from "../../api";
import {
  productApi,
  type AssetRecord,
  type StudioGenerationJobRecord,
} from "../../api/productApi";
import type { CraftDocument } from "../craft/craftApi";
import { ClickoSelectMenu } from "../../components/ClickoSelectMenu";
import { useGovernance } from "../../context/GovernanceContext";
import { useOperations } from "../../context/OperationsContext";
import { klicPageScope, useKlicPageDetails } from '../../klic/pageContext';
import {
  animate,
  moveToTrack,
  fpsOf,
  items,
  patchItem,
  split,
  type Item,
  type Motion,
  type Timeline,
  type Track,
} from "./canonicalTimeline";
import { videoOutputUrl } from "./canonicalVideoApi";
import { CraftModelPicker, type ModelSelection } from "../craft/CraftModelPicker";
import "./canonical-video.css";
import { StudioEditorFrame, StudioKlicButton, StudioUtilityPanel, useStudioShortcuts } from '../shared/StudioWorkspace';
import type { StudioPane } from '../shared/studioWorkspaceModel';

const base = "/api/v1/studios/v1/video";
const active = (job?: StudioGenerationJobRecord) =>
  Boolean(job && !["failed", "succeeded", "cancelled"].includes(job.status));
export function CanonicalVideoEditor({
  doc,
  assets,
  visible,
  onDocument,
  onUpload,
  onLibrary,
  userId,
  projectActions,
}: {
  doc: CraftDocument;
  assets: AssetRecord[];
  visible: boolean;
  onDocument: (doc: CraftDocument) => void;
  onUpload: () => void;
  onLibrary: () => void;
  userId: string;
  projectActions?: React.ReactNode;
}) {
  const { activeAccount } = useGovernance();
  const { activeClient } = useOperations();
  const [timeline, setTimeline] = React.useState(
    () => structuredClone(doc.composition.mediaTimeline) as unknown as Timeline,
  );
  const [dirty, setDirty] = React.useState(false);
  const [selected, setSelected] = React.useState<string>();
  const [pane, setPane] = React.useState<StudioPane>('preview');
  const [assistanceOpen, setAssistanceOpen] = React.useState(false);
  const editorRoot = React.useRef<HTMLElement>(null);
  useStudioShortcuts(editorRoot, visible);
  useKlicPageDetails('create-video', klicPageScope(activeAccount.workspaceId, activeClient?.id), {
    view: 'Montagem de vídeo', selected: { kind: 'studio-document', id: doc.documentId },
    selectedLayerIds: [], ...(selected ? { filters: { selectedClip: selected } } : {}),
  });
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [runtime, setRuntime] = React.useState<{
    available: boolean;
    version?: string;
    encoder?: string;
  }>();
  const [job, setJob] = React.useState<StudioGenerationJobRecord>();
  const [playhead, setPlayhead] = React.useState(0);
  const [title, setTitle] = React.useState("");
  const [instruction, setInstruction] = React.useState("");
  const [model, setModel] = React.useState<ModelSelection>({ available: false });
  const [aiPending, setAiPending] = React.useState<{ key: string; body: { expectedRevision: number; instruction: string; connectionId?: string; model?: string } }>();
  const [keyProperty, setKeyProperty] = React.useState<
    "x" | "y" | "scale" | "opacity"
  >("opacity");
  const [keyStart, setKeyStart] = React.useState(0);
  const [keyEnd, setKeyEnd] = React.useState(1);
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const [undo, setUndo] = React.useState<Timeline[]>([]);
  const [redo, setRedo] = React.useState<Timeline[]>([]);
  const mounted = React.useRef(true);
  const inFlight = React.useRef(false);
  const savePending = React.useRef<{ key: string; body: unknown } | undefined>(
    undefined,
  );
  const renderPending = React.useRef<
    { key: string; revision: number } | undefined
  >(undefined);
  const recoveryKey = `clicko:timeline:v1:${userId}:${doc.workspaceId}:${doc.documentId}`;
  const [recovery, setRecovery] = React.useState<{
    timeline: Timeline;
    revision: number;
    save?: { key: string; body: unknown };
    render?: { key: string; revision: number };
  }>();
  const fps = fpsOf(timeline);
  const duration = timeline.durationFrames / fps;
  const track = timeline.tracks.find((t) =>
    items(t).some((i) => i.id === selected),
  );
  const item = track && items(track).find((i) => i.id === selected);
  const motion =
    (item && (track?.kind === "caption" ? item.motion : item.transform)) || {};
  const locked =
    busy || active(job) || Boolean(recovery) || Boolean(savePending.current) || Boolean(renderPending.current) || Boolean(aiPending);
  const aiRecoveryKey = `clicko:timeline-ai:v1:${userId}:${doc.workspaceId}:${doc.documentId}`;
  React.useEffect(() => {
    try {
      const pending = JSON.parse(localStorage.getItem(aiRecoveryKey) || "null");
      if (pending?.key && pending?.body?.instruction && Number.isInteger(pending?.body?.expectedRevision)) setAiPending(pending);
    } catch { /* Optional recovery never authorizes an external call on load. */ }
  }, [aiRecoveryKey]);
  React.useEffect(() => {
    const beforeLeave = (event: Event) => {
      if (dirty || aiPending || inFlight.current || savePending.current || renderPending.current) {
        event.preventDefault();
        setError(dirty ? 'Salve a montagem antes de trocar de módulo.' : 'Confira a confirmação do salvamento ou da exportação antes de trocar de módulo.');
      }
    };
    window.addEventListener('clicko:studio-before-leave', beforeLeave);
    return () => window.removeEventListener('clicko:studio-before-leave', beforeLeave);
  }, [dirty, aiPending]);
  const savedRevision = React.useRef(doc.revision);
  const revision = React.useRef(doc.revision);
  revision.current = doc.revision;
  React.useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(recoveryKey);
      if (raw) {
        const value = JSON.parse(raw);
        if (value?.timeline?.schemaVersion === "studio.media-timeline.v1")
          setRecovery(value);
      }
    } catch {
      setError("Não foi possível ler a recuperação local.");
    }
    const controller = new AbortController();
    void apiFetch<typeof runtime>(`${base}/capabilities`, {
      signal: controller.signal,
    })
      .then(setRuntime)
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e.message));
      });
    void productApi
      .studioGenerationJobs(doc.workspaceId, {
        documentId: doc.documentId,
        jobType: "timeline_render",
        limit: 10,
      })
      .then((jobs) => {
        if (!controller.signal.aborted) setJob(jobs[0]);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [recoveryKey]);
  React.useEffect(() => {
    if (
      doc.revision !== savedRevision.current &&
      !dirty &&
      !savePending.current
    ) {
      setTimeline(
        structuredClone(doc.composition.mediaTimeline) as unknown as Timeline,
      );
      savedRevision.current = doc.revision;
    }
  }, [doc.revision, dirty]);
  React.useEffect(() => {
    if (!active(job)) return;
    const timer = window.setTimeout(
      () =>
        void productApi
          .studioGenerationJob(job!.id)
          .then((value) => {
            if (mounted.current) {
              setJob(value);
              if (!active(value))
                window.dispatchEvent(new Event("clicko:video-library-updated"));
            }
          })
          .catch((e) => {
            if (mounted.current) setError(e.message);
          }),
      1200,
    );
    return () => window.clearTimeout(timer);
  }, [job]);
  React.useEffect(() => {
    if (!dirty && !savePending.current && !renderPending.current) return;
    const before = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", before);
    return () => window.removeEventListener("beforeunload", before);
  }, [dirty, busy]);
  function persist(
    next: Timeline,
    save = savePending.current,
    render = renderPending.current,
  ) {
    localStorage.setItem(
      recoveryKey,
      JSON.stringify({ timeline: next, revision: doc.revision, save, render }),
    );
  }
  function change(next: Timeline) {
    if (locked) return;
    persist(next);
    setUndo((u) => [...u.slice(-29), timeline]);
    setRedo([]);
    setTimeline(next);
    setDirty(true);
  }
  async function run(task: () => Promise<unknown>) {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (e) {
      if (mounted.current)
        setError(
          e instanceof Error
            ? e.message
            : "Não foi possível concluir a operação.",
        );
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  async function applyAI() {
    if (dirty) throw new Error("Salve a edição antes de solicitar alterações à IA.");
    const attempt = aiPending || { key: crypto.randomUUID(), body: {
      expectedRevision: doc.revision, instruction: instruction.trim(), connectionId: model.connectionId, model: model.model,
    } };
    if (!attempt.body.instruction) throw new Error("Descreva o ajuste desejado.");
    // Persist before POST. A network failure must reuse the exact request and key.
    localStorage.setItem(aiRecoveryKey, JSON.stringify(attempt));
    setAiPending(attempt);
    let result: { document: CraftDocument; receiptId: string };
    try {
      result = await apiFetch(`${base}/documents/${doc.documentId}/ai-commands`, {
          method: "POST", headers: { "Idempotency-Key": attempt.key }, body: JSON.stringify(attempt.body),
        });
    } catch (failure) {
      // Only a server-confirmed preflight rejection can discard a pending identity.
      try {
        const state = await apiFetch<{ status: string; safeToStartNew?: boolean }>(
          `/api/v1/studios/v1/documents/${doc.documentId}/craft/ai-requests/${attempt.key}`);
        if (state.safeToStartNew || (state.status === "not_found" && failure instanceof APIError && [400, 403, 409, 422].includes(failure.status))) {
          setAiPending(undefined); localStorage.removeItem(aiRecoveryKey);
        }
      } catch { /* Unknown means retained, never authorize another external submission. */ }
      throw failure;
    }
    if (!mounted.current) return;
    onDocument(result.document);
    setTimeline(structuredClone(result.document.composition.mediaTimeline) as unknown as Timeline);
    setDirty(false); setUndo([]); setRedo([]); setAiPending(undefined);
    localStorage.removeItem(aiRecoveryKey);
  }
  async function save() {
    if (!dirty && !savePending.current) return doc;
    if (!savePending.current)
      savePending.current = {
        key: crypto.randomUUID(),
        body: { expectedRevision: doc.revision, timeline },
      };
    persist(timeline);
    let next: CraftDocument;
    try {
      next = await apiFetch<CraftDocument>(
        `${base}/documents/${doc.documentId}/timeline`,
        {
          method: "PUT",
          body: JSON.stringify(savePending.current.body),
          headers: { "Idempotency-Key": savePending.current.key },
        },
      );
    } catch (error) {
      if (
        error instanceof APIError &&
        error.status >= 400 &&
        error.status < 500 &&
        error.status !== 408 &&
        error.status !== 409
      ) {
        savePending.current = undefined;
        persist(timeline);
      }
      throw error;
    }
    if (!mounted.current) return next;
    savePending.current = undefined;
    savedRevision.current = next.revision;
    setDirty(false);
    localStorage.removeItem(recoveryKey);
    onDocument(next);
    return next;
  }
  async function render() {
    const next = renderPending.current ? doc : await save();
    if (!renderPending.current)
      renderPending.current = {
        key: crypto.randomUUID(),
        revision: next.revision,
      };
    persist(timeline);
    let result: StudioGenerationJobRecord;
    try {
      result = await apiFetch<StudioGenerationJobRecord>(
        `${base}/documents/${next.documentId}/render-jobs`,
        {
          method: "POST",
          body: JSON.stringify({
            expectedRevision: renderPending.current.revision,
          }),
          headers: { "Idempotency-Key": renderPending.current.key },
        },
      );
    } catch (error) {
      if (
        error instanceof APIError &&
        [400, 401, 403, 404, 409, 422].includes(error.status)
      ) {
        renderPending.current = undefined;
        persist(timeline);
      }
      throw error;
    }
    renderPending.current = undefined;
    localStorage.removeItem(recoveryKey);
    if (mounted.current) setJob(result);
  }
  async function add(asset: AssetRecord) {
    const image = asset.mediaType?.startsWith("image/");
    const audio = asset.mediaType?.startsWith("audio/");
    let length = 4;
    if (!image) {
      const info = await apiFetch<{ durationSeconds: number }>(
        `${base}/assets/${asset.id}/probe?workspace_id=${encodeURIComponent(doc.workspaceId)}`,
      );
      length = Math.min(info.durationSeconds, 600);
    }
    const kind = audio ? "audio" : image ? "overlay" : "video";
    const found = timeline.tracks.find((t) => t.kind === kind && !t.locked);
    const row: Track = found || {
      id: crypto.randomUUID(),
      kind,
      name: audio ? "Áudio" : image ? "Imagens" : "Vídeo",
      clips: [],
      muted: false,
      locked: false,
    };
    const start =
      kind === "video"
        ? Math.max(
            0,
            ...items(row).map(
              (i) => i.timeline.startFrame + i.timeline.durationFrames,
            ),
          )
        : Math.min(playhead, timeline.durationFrames - 1);
    const frames = Math.min(
      Math.max(1, Math.floor(length * fps)),
      Math.floor(600 * fps) - start,
    );
    if (frames < 1)
      throw new Error("A timeline atingiu o limite de 10 minutos.");
    const value: Item = {
      id: crypto.randomUUID(),
      assetId: asset.id,
      label: asset.title,
      timeline: { startFrame: start, durationFrames: frames },
      playbackRate: 1,
      enabled: true,
      locked: false,
      transform: {},
      effects: [],
      keyframes: [],
      ...(!image
        ? {
            source: {
              startMicroseconds: 0,
              durationMicroseconds: Math.round((frames / fps) * 1e6),
            },
          }
        : {}),
      ...(audio
        ? { gainDb: 0, pan: 0, fadeInFrames: 0, fadeOutFrames: 0 }
        : {}),
    } as Item;
    const updated = { ...row, clips: [...items(row), value] };
    change({
      ...timeline,
      durationFrames: Math.max(timeline.durationFrames, start + frames),
      tracks: found
        ? timeline.tracks.map((t) => (t.id === row.id ? updated : t))
        : [...timeline.tracks, updated],
    });
    selectItem(value.id);
  }
  function updateItem(patch: Partial<Item>) {
    if (item)
      change(
        patchItem(timeline, item.id, (current) => ({ ...current, ...patch })),
      );
  }
  function updateMotion(patch: Motion) {
    updateItem({
      [track?.kind === "caption" ? "motion" : "transform"]: {
        ...motion,
        ...patch,
      },
    });
  }
  function number(
    label: string,
    value: number,
    min: number,
    max: number,
    action: (value: number) => void,
    step = 0.1,
  ) {
    return (
      <label>
        {label}
        <input
          type="number"
          value={Number.isFinite(value) ? Math.round(value * 1000) / 1000 : 0}
          min={min}
          max={max}
          step={step}
          disabled={locked || item?.locked || track?.locked}
          onChange={(e) => {
            const n = Number(e.target.value);
            if (Number.isFinite(n) && n >= min && n <= max) action(n);
          }}
        />
      </label>
    );
  }
  const result =
    job?.status === "succeeded" &&
    (job.result as { assetId?: string; documentRevision?: number } | undefined)
      ?.assetId;
  const resultRevision = (
    job?.result as { documentRevision?: number } | undefined
  )?.documentRevision;
  const url = result
    ? videoOutputUrl(result, activeAccount.workspaceId, activeClient?.id)
    : undefined;
  function selectItem(id: string) { setSelected(id); setPane('properties'); }
  return <section ref={editorRoot} className="cv-editor cv-integrated" hidden={!visible} aria-label="Editor audiovisual Clicko">
    {error && (
        <p role="alert" className="vs-banner">
          {error}
          <button
            onClick={() =>
              void run(async () => {
                const next = await productApi.studioDocument(doc.documentId);
                onDocument(next);
                setTimeline(
                  structuredClone(
                    next.composition.mediaTimeline,
                  ) as unknown as Timeline,
                );
                savePending.current = undefined;
                setDirty(false);
                localStorage.removeItem(recoveryKey);
              })
            }
          >
            Reabrir revisão salva
          </button>
        </p>
      )}
      {recovery && (
        <div className="vs-banner">
          Há uma edição recuperável da revisão {recovery.revision}.
          <button
            disabled={
              busy ||
              (recovery.revision !== doc.revision &&
                !recovery.save &&
                !recovery.render)
            }
            onClick={() => {
              setTimeline(recovery.timeline);
              savePending.current = recovery.save;
              renderPending.current = recovery.render;
              setDirty(true);
              setRecovery(undefined);
            }}
          >
            Recuperar
          </button>
          <button
            onClick={() => {
              localStorage.removeItem(recoveryKey);
              setRecovery(undefined);
            }}
          >
            Descartar recuperação
          </button>
        </div>
      )}
      {!runtime?.available && (
        <p className="vs-banner">
          O processamento de vídeo não está disponível. A edição pode ser salva
          para continuar depois.
        </p>
      )}
    {aiPending && <p role="status" className="vs-banner">Pedido de montagem aguardando confirmação. <button onClick={() => setAssistanceOpen(true)}>Conferir pedido</button></p>}
    <StudioEditorFrame pane={pane} onPaneChange={setPane}
      toolbar={<><div className="cv-toolbar-wrap"><div className="cv-toolbar">
        <div>
          <strong title={doc.title}>{doc.title}</strong>
          <small>
            {dirty ? "Alterações locais" : `Revisão ${doc.revision} salva`} ·
            MP4 / H.264
          </small>
        </div>
        <button
          data-studio-action="undo" aria-label="Desfazer" title="Desfazer · Ctrl/Cmd+Z" disabled={locked || !undo.length}
          onClick={() => {
            const next = undo.at(-1)!;
            persist(next);
            setRedo((r) => [timeline, ...r]);
            setUndo((u) => u.slice(0, -1));
            setTimeline(next);
            setDirty(true);
          }}
        >
          <Undo2 size={15}/>
        </button>
        <button
          data-studio-action="redo" aria-label="Refazer" title="Refazer · Ctrl/Cmd+Shift+Z" disabled={locked || !redo.length}
          onClick={() => {
            const next = redo[0];
            persist(next);
            setUndo((u) => [...u, timeline]);
            setRedo((r) => r.slice(1));
            setTimeline(next);
            setDirty(true);
          }}
        >
          <Redo2 size={15}/>
        </button>
        <button
          data-studio-action="save" disabled={busy || active(job) || Boolean(recovery) || Boolean(aiPending)}
          onClick={() => void run(save)}
        >
          <Save size={15} />{" "}
          {savePending.current ? "Verificar salvamento" : "Salvar edição"}
        </button>
        <button
          className="vs-primary"
          disabled={
            busy || active(job) || Boolean(recovery) || Boolean(aiPending) || !runtime?.available ||
            !timeline.tracks.some((row) => items(row).length > 0)
          }
          onClick={() => void run(render)}
        >
          <Film size={15} />
          {renderPending.current
            ? "Verificar exportação"
            : "Gerar prévia / MP4"}
        </button>
      </div></div>{projectActions}<button type="button" onClick={() => setAssistanceOpen(true)}>Assistência</button><StudioKlicButton/></>}
      materials={<aside className="cv-media">
          <header>
            <h3>Materiais</h3>
            <button
              disabled={locked}
              onClick={onUpload}
              aria-label="Importar mídia" title="Importar mídia"
            >
              <Upload size={16} />
            </button>
          </header>
          {assets.map((asset) => (
            <button
              className="cv-media-item"
              key={asset.id}
              disabled={locked}
              onClick={() => void run(() => add(asset))}
            >
              <span>
                {asset.mediaType?.startsWith("audio/") ? (
                  <Music2 size={17} />
                ) : (
                  <Film size={17} />
                )}
              </span>
              <span>
                {asset.title}
                <small>Adicionar à timeline</small>
              </span>
              <Plus size={14} />
            </button>
          ))}
          {!assets.length && (
            <p>Importe um vídeo, imagem ou áudio para começar.</p>
          )}
          <button disabled={locked} onClick={onUpload}>
            <Upload size={15} /> Importar arquivo
          </button>
          <button disabled={locked || dirty} onClick={onLibrary}>Abrir Biblioteca</button>
        </aside>}
      preview={<main className="cv-monitor">
          <header>
            <h3>Monitor de composição</h3>
            <small>
              {doc.composition.pages[0].width} ×{" "}
              {doc.composition.pages[0].height} · {Math.round(fps * 100) / 100}{" "}
              fps
            </small>
          </header>
          {url ? (
            <video
              ref={videoRef}
              key={url}
              src={url}
              controls
              playsInline
              preload="metadata"
              onTimeUpdate={(e) =>
                setPlayhead(Math.round(e.currentTarget.currentTime * fps))
              }
            />
          ) : (
            <div className="cv-monitor-empty">
              <Film size={38} />
              <strong>A sua montagem aparece aqui</strong>
              <p>
                Adicione materiais, ajuste os cortes e gere a prévia para
                assistir ao resultado com títulos, efeitos e áudio.
              </p>
            </div>
          )}
          {url && (
            <footer>
              <span>
                Prévia renderizada · revisão {resultRevision}
                {dirty || resultRevision !== doc.revision
                  ? " · edição atual ainda não renderizada"
                  : ""}
              </span>
              <a href={url + "&download=1"}>
                <Download size={15} /> Baixar MP4
              </a>
            </footer>
          )}
          {job && (
            <div className="cv-job" role="status">
              <strong>
                {(
                  {
                    queued: "Na fila",
                    running: "Renderizando",
                    retrying: "Tentando novamente",
                    succeeded: "MP4 validado",
                    failed: "Não concluído",
                    cancel_requested: "Cancelando",
                    cancelled: "Cancelado",
                  } as Record<string, string>
                )[job.status] || job.status}
              </strong>
              <progress
                max={100}
                value={job.status === "succeeded" ? 100 : job.progress}
              />
              {job.errorMessage && <small>{job.errorMessage}</small>}
              {active(job) ? (
                <button
                  disabled={job.status === "cancel_requested" || busy}
                  onClick={() =>
                    void run(async () =>
                      setJob(
                        await productApi.cancelStudioGenerationJob(job.id),
                      ),
                    )
                  }
                >
                  Cancelar
                </button>
              ) : job.status === "failed" && job.attempts < job.maxAttempts ? (
                <button
                  disabled={busy}
                  onClick={() =>
                    void run(async () =>
                      setJob(await productApi.retryStudioGenerationJob(job.id)),
                    )
                  }
                >
                  Tentar novamente
                </button>
              ) : null}
            </div>
          )}
        </main>}
      inspector={item ? <aside className="cv-inspector">
          <h3>Propriedades</h3>
          {item ? (
            <>
              <strong>{item.text || item.label}</strong>
              {track && <fieldset disabled={locked || Boolean(track.locked) || Boolean(item.locked)}><ClickoSelectMenu label="Faixa do elemento" value={track.id}
                options={timeline.tracks.filter(row => row.kind === track.kind && (!row.locked || row.id === track.id)).map(row => [row.id,row.name])}
                onChange={id => change(moveToTrack(timeline,item.id,id,item.timeline.startFrame))}/></fieldset>}
              {number(
                "Posição na timeline (s)",
                item.timeline.startFrame / fps,
                0,
                Math.max(0, duration - item.timeline.durationFrames / fps),
                (v) =>
                  updateItem({
                    timeline: {
                      ...item.timeline,
                      startFrame: Math.round(v * fps),
                    },
                  }),
              )}
              {number(
                "Duração (s)",
                item.timeline.durationFrames / fps,
                1 / fps,
                duration - item.timeline.startFrame / fps,
                (v) =>
                  updateItem({
                    timeline: {
                      ...item.timeline,
                      durationFrames: Math.round(v * fps),
                    },
                  }),
              )}
              {item.assetId &&
                number(
                  "Entrada no arquivo (s)",
                  (item.source?.startMicroseconds || 0) / 1e6,
                  0,
                  600,
                  (v) =>
                    updateItem({
                      source: {
                        startMicroseconds: Math.round(v * 1e6),
                        durationMicroseconds: Math.round(
                          (item.timeline.durationFrames / fps) *
                            (item.playbackRate || 1) *
                            1e6,
                        ),
                      },
                    }),
                )}
              {item.assetId &&
                number("Velocidade", item.playbackRate || 1, 0.5, 2, (v) =>
                  updateItem({
                    playbackRate: v,
                    source: {
                      startMicroseconds: item.source?.startMicroseconds || 0,
                      durationMicroseconds: Math.round(
                        (item.timeline.durationFrames / fps) * v * 1e6,
                      ),
                    },
                  }),
                )}
              {track?.kind === "audio" ? (
                <>
                  {number(
                    "Volume (dB)",
                    item.gainDb || 0,
                    -60,
                    12,
                    (v) => updateItem({ gainDb: v }),
                    1,
                  )}
                  {number(
                    "Entrada de áudio (s)",
                    (item.fadeInFrames || 0) / fps,
                    0,
                    item.timeline.durationFrames / fps,
                    (v) => updateItem({ fadeInFrames: Math.round(v * fps) }),
                  )}
                  {number(
                    "Saída de áudio (s)",
                    (item.fadeOutFrames || 0) / fps,
                    0,
                    item.timeline.durationFrames / fps,
                    (v) => updateItem({ fadeOutFrames: Math.round(v * fps) }),
                  )}
                </>
              ) : (
                <>
                  {number(
                    "Deslocamento X (px)",
                    motion.x || 0,
                    -1920,
                    1920,
                    (v) => updateMotion({ x: v }),
                    1,
                  )}
                  {number(
                    "Deslocamento Y (px)",
                    motion.y || 0,
                    -1920,
                    1920,
                    (v) => updateMotion({ y: v }),
                    1,
                  )}
                  {number("Escala", motion.scale ?? 1, 0.1, 4, (v) =>
                    updateMotion({ scale: v }),
                  )}
                  {number(
                    "Opacidade",
                    motion.opacity ?? 1,
                    0,
                    1,
                    (v) => updateMotion({ opacity: v }),
                    0.05,
                  )}
                  {number(
                    "Rotação (°)",
                    motion.rotation || 0,
                    -360,
                    360,
                    (v) => updateMotion({ rotation: v }),
                    1,
                  )}
                  <fieldset disabled={locked}>
                    <ClickoSelectMenu
                      label="Animação de entrada e saída"
                      value="choose"
                      options={[
                        ["choose", "Escolher preset…"],
                        ["none", "Sem animação"],
                        ["fade", "Fade"],
                        ["slide", "Entrada e saída suave"],
                        ["zoom", "Aproximação"],
                      ]}
                      onChange={(value) => {
                        if (value !== "choose")
                          change(
                            patchItem(timeline, item.id, (i) =>
                              animate(i, value, fps),
                            ),
                          );
                      }}
                    />
                  </fieldset>
                  {number(
                    "Fade de entrada (s)",
                    (motion.fadeInFrames || 0) / fps,
                    0,
                    item.timeline.durationFrames / fps,
                    (v) => updateMotion({ fadeInFrames: Math.round(v * fps) }),
                  )}
                  {number(
                    "Fade de saída (s)",
                    (motion.fadeOutFrames || 0) / fps,
                    0,
                    item.timeline.durationFrames / fps,
                    (v) => updateMotion({ fadeOutFrames: Math.round(v * fps) }),
                  )}
                  {item.text !== undefined && (
                    <>
                      <label>
                        Texto
                        <textarea
                          value={item.text}
                          maxLength={1000}
                          disabled={locked}
                          onChange={(e) => updateItem({ text: e.target.value })}
                        />
                      </label>
                      <label>
                        Cor
                        <input
                          type="color"
                          value={item.style?.color || "#ffffff"}
                          disabled={locked}
                          onChange={(e) =>
                            updateItem({
                              style: { ...item.style!, color: e.target.value },
                            })
                          }
                        />
                      </label>
                      {number(
                        "Tamanho do texto",
                        item.style?.fontSize || 56,
                        16,
                        240,
                        (v) =>
                          updateItem({
                            style: { ...item.style!, fontSize: Math.round(v) },
                          }),
                        1,
                      )}
                      <label>
                        Fundo do título
                        <input
                          type="color"
                          disabled={locked}
                          value={motion.backgroundColor || "#000000"}
                          onChange={(e) =>
                            updateMotion({ backgroundColor: e.target.value })
                          }
                        />
                      </label>
                      <button
                        disabled={locked}
                        onClick={() => updateMotion({ backgroundColor: null })}
                      >
                        Remover fundo do título
                      </button>
                    </>
                  )}
                  {Boolean(item.keyframes?.length) && (
                    <small>
                      {item.keyframes!.length} keyframes persistidos ·
                      interpolação linear
                    </small>
                  )}
                  <details>
                    <summary>Keyframes essenciais</summary>
                    <fieldset disabled={locked}>
                      <ClickoSelectMenu
                        label="Propriedade"
                        value={keyProperty}
                        options={[
                          ["x", "Posição X"],
                          ["y", "Posição Y"],
                          ["scale", "Escala"],
                          ["opacity", "Opacidade"],
                        ]}
                        onChange={(v) => {
                          setKeyProperty(v as typeof keyProperty);
                          setKeyStart(v === "scale" ? 1 : 0);
                          setKeyEnd(1);
                        }}
                      />
                      {number(
                        "Valor inicial",
                        keyStart,
                        keyProperty === "scale"
                          ? 0.1
                          : keyProperty === "opacity"
                            ? 0
                            : -1920,
                        keyProperty === "scale"
                          ? 4
                          : keyProperty === "opacity"
                            ? 1
                            : 1920,
                        setKeyStart,
                      )}
                      {number(
                        "Valor final",
                        keyEnd,
                        keyProperty === "scale"
                          ? 0.1
                          : keyProperty === "opacity"
                            ? 0
                            : -1920,
                        keyProperty === "scale"
                          ? 4
                          : keyProperty === "opacity"
                            ? 1
                            : 1920,
                        setKeyEnd,
                      )}
                      <button
                        onClick={() =>
                          updateItem({
                            keyframes: [
                              ...(item.keyframes || []).filter(
                                (k) => k.property !== keyProperty,
                              ),
                              {
                                property: keyProperty,
                                frame: 0,
                                value: keyStart,
                              },
                              {
                                property: keyProperty,
                                frame: item.timeline.durationFrames,
                                value: keyEnd,
                              },
                            ],
                          })
                        }
                      >
                        Aplicar do início ao fim
                      </button>
                      <button onClick={() => updateItem({ keyframes: [] })}>
                        Limpar keyframes
                      </button>
                    </fieldset>
                  </details>
                </>
              )}
              <button
                disabled={
                  locked ||
                  track?.kind === "caption" ||
                  Boolean(item.keyframes?.length)
                }
                title="Divida clipes sem keyframes na posição do cursor"
                onClick={() =>
                  change(
                    split(timeline, item.id, playhead, crypto.randomUUID()),
                  )
                }
              >
                <Scissors size={15} /> Dividir no cursor
              </button>
              <button
                disabled={locked}
                onClick={() => {
                  change({
                    ...timeline,
                    tracks: timeline.tracks.map((t) =>
                      t.kind === "marker"
                        ? t
                        : {
                            ...t,
                            [t.kind === "caption" ? "cues" : "clips"]: items(
                              t,
                            ).filter((i) => i.id !== item.id),
                          },
                    ),
                  });
                  setSelected(undefined);
                }}
              >
                <Trash2 size={15} /> Remover
              </button>
            </>
          ) : (
            <p>Selecione um clipe ou título para ajustar seus parâmetros.</p>
          )}
        </aside> : undefined}
      timeline={<section className="cv-timeline">
        <header>
          <h3>Timeline multipista</h3>
          <label>
            Cursor {Math.round((playhead / fps) * 100) / 100}s
            <input
              type="range"
              min={0}
              max={timeline.durationFrames - 1}
              value={Math.min(playhead, timeline.durationFrames - 1)}
              onChange={(e) => {
                const frame = Number(e.target.value);
                setPlayhead(frame);
                if (
                  videoRef.current &&
                  Number.isFinite(videoRef.current.duration)
                )
                  videoRef.current.currentTime = Math.min(
                    frame / fps,
                    videoRef.current.duration,
                  );
              }}
            />
          </label>
          {number(
            "Duração do projeto (s)",
            duration,
            Math.max(
              1,
              ...timeline.tracks.flatMap((t) =>
                items(t).map(
                  (i) =>
                    (i.timeline.startFrame + i.timeline.durationFrames) / fps,
                ),
              ),
            ),
            600,
            (v) => change({ ...timeline, durationFrames: Math.round(v * fps) }),
            1,
          )}
          <button
            disabled={locked}
            onClick={() =>
              change({
                ...timeline,
                tracks: [
                  ...timeline.tracks,
                  {
                    id: crypto.randomUUID(),
                    kind: "video",
                    name: `Vídeo ${timeline.tracks.length + 1}`,
                    clips: [],
                    muted: false,
                    locked: false,
                  },
                ],
              })
            }
          >
            <Plus size={15} /> Faixa
          </button>
        </header>
        <details className="studio-fold cv-title-entry"><summary>Adicionar título ou chamada à ação</summary>
        <div className="cv-title-add">
          <Type size={17} />
          <input
            value={title}
            disabled={locked}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={1000}
            placeholder="Escreva um título ou chamada à ação…"
          />
          <button
            disabled={locked || !title.trim()}
            onClick={() => {
              const id = crypto.randomUUID();
              const cue: Item = {
                id,
                text: title.trim(),
                timeline: {
                  startFrame: playhead,
                  durationFrames: Math.min(
                    Math.round(3 * fps),
                    timeline.durationFrames - playhead,
                  ),
                },
                style: {
                  fontFamily: "system",
                  color: "#ffffff",
                  fontSize: Math.max(
                    16,
                    Math.round(doc.composition.pages[0].width / 22),
                  ),
                  outlineWidth: 2,
                  maxLines: 3,
                },
                motion: {},
                keyframes: [],
              };
              change({
                ...timeline,
                tracks: [
                  ...timeline.tracks,
                  {
                    id: crypto.randomUUID(),
                    kind: "caption",
                    name: "Título / CTA",
                    cues: [animate(cue, "slide", fps)],
                    locked: false,
                  },
                ],
              });
              selectItem(id);
              setTitle("");
            }}
          >
            <Plus size={15} /> Adicionar título
          </button>
        </div>
        </details>
        <details className="studio-fold cv-timeline-help"><summary>Ajuda da timeline</summary>
        <p className="vs-fine">
          As faixas inferiores são compostas sobre as anteriores. Sobreponha
          clipes e aplique fade para criar uma transição. Arraste um clipe para
          reposicioná-lo.
        </p>
        </details>
        <div className="cv-tracks">
          {timeline.tracks
            .filter((t) => t.kind !== "marker")
            .map((row) => (
              <div className="cv-track" key={row.id}>
                <div>
                  <strong>{row.name}</strong>
                  {(row.kind === "video" || row.kind === "audio") && (
                    <button
                      disabled={locked}
                      onClick={() =>
                        change({
                          ...timeline,
                          tracks: timeline.tracks.map((t) =>
                            t.id === row.id ? { ...t, muted: !t.muted } : t,
                          ),
                        })
                      }
                    >
                      {row.muted ? "Ativar áudio" : "Silenciar"}
                    </button>
                  )}
                </div>
                <div
                  className="cv-lane"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const id = e.dataTransfer.getData("text/clicko-clip");
                    const box = e.currentTarget.getBoundingClientRect();
                    const frame = Math.round(
                      Math.max(
                        0,
                        Math.min(1, (e.clientX - box.left) / box.width),
                      ) * timeline.durationFrames,
                    );
                    change(moveToTrack(timeline, id, row.id, frame));
                  }}
                >
                  <span
                    className="cv-playhead"
                    style={{
                      left: `${(playhead / timeline.durationFrames) * 100}%`,
                    }}
                  />
                  {items(row).map((clip) => (
                    <button
                      className={clip.id === selected ? "is-selected" : ""}
                      draggable={!locked}
                      onDragStart={(e) =>
                        e.dataTransfer.setData("text/clicko-clip", clip.id)
                      }
                      disabled={busy}
                      key={clip.id}
                      style={{
                        left: `${(clip.timeline.startFrame / timeline.durationFrames) * 100}%`,
                        width: `${(clip.timeline.durationFrames / timeline.durationFrames) * 100}%`,
                      }}
                      onClick={() => selectItem(clip.id)}
                    >
                      {clip.text || clip.label}
                      <small>
                        {(clip.timeline.durationFrames / fps).toFixed(2)}s
                      </small>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          {!timeline.tracks.length && (
            <p>Adicione um material para começar a montagem.</p>
          )}
        </div>
      </section>}
    />
    <StudioUtilityPanel title="Ferramentas de montagem assistida" open={assistanceOpen} onClose={() => setAssistanceOpen(false)}>
      <StudioKlicButton/><p>A conversa KLIC usa o projeto aberto. Os controles abaixo aplicam ferramentas à timeline salva.</p>
      <details className="vs-disclosure">
        <summary>Montagem assistida por IA · timeline FFmpeg</summary>
        <div className="vs-disclosure-body">
          <p>Aplica cortes, textos, sobreposições, fades e ajustes de áudio aos materiais vinculados. Não gera cenas, voz ou transcrições.</p>
          <CraftModelPicker workspaceId={doc.workspaceId} userId={userId} disabled={locked} onChange={setModel} />
          <label>Pedido de edição
            <textarea rows={2} maxLength={4000} value={instruction} disabled={locked}
              onChange={event => setInstruction(event.target.value)} placeholder="Ex.: encurte a abertura e adicione um título…" />
          </label>
          <button disabled={busy || active(job) || dirty || Boolean(recovery) || (!aiPending && (!model.available || !instruction.trim()))}
            onClick={() => void run(applyAI)}>{aiPending ? "Conferir mesmo pedido de IA" : "Aplicar à timeline salva"}</button>
          {aiPending && <small>Pedido preservado. Conferir reutiliza a mesma identidade; um resultado externo desconhecido exige conciliação, sem nova cobrança automática.</small>}
        </div>
      </details>
    </StudioUtilityPanel>
  </section>;
}
