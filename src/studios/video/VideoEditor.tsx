import React from "react";
import {
  AudioLines,
  Captions,
  ChevronRight,
  Film,
  FolderOpen,
  Image as ImageIcon,
  Layers3,
  LoaderCircle,
  Maximize2,
  Minus,
  Pause,
  Play,
  Plus,
  Redo2,
  RefreshCw,
  Save,
  Scissors,
  SkipBack,
  SkipForward,
  Type,
  Undo2,
  Upload,
  Volume2,
  VolumeX,
} from "lucide-react";
import { productApi, type AssetRecord } from "../../api/productApi";
import { ClickoSelectMenu } from "../../components/ClickoSelectMenu";
import {
  craftApi,
  type CraftCapability,
  type CraftCommand,
  type CraftDocument,
  type CraftInputSchema,
} from "../craft/craftApi";
import {
  commandValidation,
  craftCommands,
  initialCommandParams,
} from "../craft/craftState";
import { useCraftBrowser } from "../craft/useCraftBrowser";
import { craftError } from "../craft/useCraftStudio";
import { moveClip, splitClip, timelineTracks } from "./videoModel";
import {
  audioGain,
  availableOperations,
  operationFields,
  primaryOperations,
  type VideoTool,
} from "./videoUsability";
import type { VideoController } from "./VideoStudio";

type Props = {
  visible: boolean;
  studio: VideoController;
  doc?: CraftDocument;
  assets: AssetRecord[];
  selectedAsset?: string;
  onSelectAsset: (id: string) => void;
  onUpload: () => void;
  onLibrary: () => void;
  onCreate: () => void;
  locked: boolean;
  run: (task: () => Promise<unknown>) => Promise<void>;
  apply: (command: CraftCommand) => Promise<void>;
  outputUrl?: string;
};
const timecode = (seconds: number) =>
  `${Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0")}.${Math.floor((seconds % 1) * 100)
    .toString()
    .padStart(2, "0")}`;
const fields: Record<string, string> = {
  text: "Texto",
  size: "Tamanho",
  fontSize: "Tamanho da fonte",
  fill: "Preenchimento",
  color: "Cor",
  font: "Fonte",
  fontFamily: "Fonte",
  clip: "Clipe",
  layer: "Camada",
  track: "Trilha",
  seconds: "Posição em segundos",
  durationSeconds: "Duração em segundos",
  durationMs: "Duração em ms",
  name: "Nome",
  path: "Propriedade",
  value: "Valor",
  edge: "Extremidade",
  deltaFrames: "Ajuste em quadros",
  mode: "Modo",
  time: "Tempo nativo",
  width: "Largura",
  height: "Altura",
  opacity: "Opacidade",
  position: "Posição",
  scale: "Escala",
  rotation: "Rotação",
  muted: "Silenciado",
  volumeDb: "Volume em dB",
  assetId: "Material",
  addToTimeline: "Inserir na timeline",
  start: "Início",
  end: "Fim",
  align: "Alinhamento",
  db: "Volume em dB",
};
const labels: Record<string, string> = {
  "asset.import": "Inserir material",
  "timeline.trim": "Ajustar corte",
  "timeline.razor": "Dividir clipe",
  "timeline.setTrack": "Configurar trilha",
  "captions.add": "Adicionar legenda",
  "captions.newTrack": "Criar trilha de legendas",
  "layer.newText": "Adicionar texto",
  "layer.newShape": "Adicionar forma",
  "prop.set": "Ajustar propriedade",
  "key.add": "Adicionar keyframe",
  "text.set": "Editar texto",
  "inspector.transform": "Posição, escala e opacidade",
  "effects.setParam": "Ajustar efeito",
  "sequence.settings": "Configurar sequência",
  "clip.audioGain": "Ajustar volume do clipe",
  "prop.addKey": "Adicionar keyframe",
  "captions.setText": "Editar legenda",
  "captions.setTiming": "Ajustar tempo da legenda",
  "captions.setStyle": "Estilo da legenda",
  "sequence.applyVideoTransition": "Adicionar transição",
  "comp.settings": "Configurar composição",
};
type Tool = VideoTool;
export function VideoEditor({
  visible,
  studio,
  doc,
  assets,
  selectedAsset,
  onSelectAsset,
  onUpload,
  onLibrary,
  onCreate,
  locked,
  run,
  apply,
  outputUrl,
}: Props) {
  const [frame, setFrame] = React.useState(0);
  const [playing, setPlaying] = React.useState(false);
  const [zoom, setZoom] = React.useState(1);
  const [selectedClip, setSelectedClip] = React.useState<string>();
  const [tool, setTool] = React.useState<Tool>("clip");
  const [commandId, setCommandId] = React.useState("");
  const [params, setParams] = React.useState<Record<string, unknown>>({});
  const [preview, setPreview] = React.useState<string>();
  const [source, setSource] = React.useState<string>();
  const [previewError, setPreviewError] = React.useState<string>();
  const [previewLoading, setPreviewLoading] = React.useState(false);
  const [position, setPosition] = React.useState(0);
  const [trim, setTrim] = React.useState(0);
  const [gain, setGain] = React.useState(0);
  const [mediaDuration, setMediaDuration] = React.useState(0);
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const previewRef = React.useRef<HTMLDivElement>(null);
  const previewUrlRef = React.useRef<string | undefined>(undefined);
  const active =
    doc?.nativeEditorState && studio.inspection?.documentId === doc.documentId;
  const browser = useCraftBrowser(
    doc,
    studio.activePageId,
    Boolean(visible && active && studio.engineInfo?.available),
  );
  const inspection =
    studio.inspection?.documentId === doc?.documentId
      ? studio.inspection
      : undefined;
  const projected =
    inspection && browser.inspection
      ? {
          ...inspection,
          project: { ...inspection.project, ...browser.inspection },
        }
      : inspection;
  const tracks = timelineTracks(projected, doc);
  const clips = tracks.flatMap((track) => track.clips);
  const clip = clips.find((item) => item.id === selectedClip);
  const fps = Number(projected?.project.fps) || 30;
  const projectDuration =
    (projected
      ? Math.max(
          Number(projected.project.durationMs) || 0,
          ...clips.map((item) => item.startMs + item.durationMs),
        )
      : Math.max(
          doc?.composition.pages[0]?.durationMs || 0,
          ...clips.map((item) => item.startMs + item.durationMs),
        )) / 1000;
  const commands = craftCommands(inspection).filter(
    (command) => (command as { available?: boolean }).available !== false,
  );
  const nativeLocked = locked || browser.applying;
  const selection =
    assets.find((asset) => asset.id === selectedAsset) ||
    assets.find(
      (asset) =>
        asset.id ===
        doc?.assets?.find((item) => item.mediaType.startsWith("video/"))?.id,
    );
  const sourceMode = !active && Boolean(source);
  const duration =
    (sourceMode || outputUrl) && mediaDuration > 0
      ? mediaDuration
      : projectDuration;
  const maxFrame = Math.max(0, Math.ceil(duration * fps) - 1);
  const playable = Boolean(
    (sourceMode && selection?.mediaType?.startsWith("video/")) ||
    outputUrl ||
    browser.state === "ready",
  );
  const commandList = availableOperations(commands, tool);
  const commonCommands = primaryOperations(commands, tool);
  const command = commandList.find((item) => item.id === commandId);
  React.useEffect(() => {
    setFrame(0);
    setPlaying(false);
    setSelectedClip(undefined);
    setCommandId("");
    setParams({});
  }, [doc?.documentId]);
  React.useEffect(() => {
    if (!visible) {
      setPlaying(false);
      videoRef.current?.pause();
    }
  }, [visible]);
  React.useEffect(() => {
    setPreview(undefined);
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = undefined;
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, [doc?.documentId]);
  React.useEffect(() => {
    setPosition((clip?.startMs || 0) / 1000);
    setTrim(0);
    setGain(Number(clip?.properties?.gainDb) || 0);
  }, [clip?.id, clip?.startMs, clip?.properties?.gainDb]);
  React.useEffect(() => {
    setFrame((current) => Math.min(current, maxFrame));
  }, [maxFrame]);
  React.useEffect(() => {
    setSource(undefined);
    setPreviewError(undefined);
    if (!selection || !visible) return;
    const controller = new AbortController();
    let url: string | undefined;
    void productApi
      .studioAssetBlob(selection.id, controller.signal)
      .then((blob) => {
        if (!controller.signal.aborted) {
          url = URL.createObjectURL(blob);
          setSource(url);
        }
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setPreviewError(craftError(cause));
      });
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [selection?.id, visible]);
  React.useEffect(() => {
    if (
      !visible ||
      !active ||
      outputUrl ||
      (playing && browser.state === "ready")
    )
      return;
    const controller = new AbortController();
    const timer = window.setTimeout(
      () => {
        setPreviewLoading(true);
        setPreviewError(undefined);
        const task =
          browser.state === "ready"
            ? browser.preview(frame, fps)
            : craftApi.preview(
                doc!.documentId,
                frame,
                controller.signal,
                studio.activePageId,
              );
        void task
          .then((blob) => {
            if (!controller.signal.aborted) {
              const url = URL.createObjectURL(blob);
              if (previewUrlRef.current)
                URL.revokeObjectURL(previewUrlRef.current);
              previewUrlRef.current = url;
              setPreview(url);
            }
          })
          .catch((cause) => {
            if (!controller.signal.aborted) {
              setPreviewError(craftError(cause));
              setPlaying(false);
            }
          })
          .finally(() => {
            if (!controller.signal.aborted) setPreviewLoading(false);
          });
      },
      browser.state === "ready" ? 30 : 180,
    );
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [
    doc?.documentId,
    doc?.revision,
    active,
    frame,
    browser.state,
    browser.change,
    outputUrl,
    fps,
    studio.activePageId,
    visible,
    playing,
  ]);
  React.useEffect(() => {
    if (
      !visible ||
      !playing ||
      sourceMode ||
      outputUrl ||
      browser.state !== "ready"
    )
      return;
    // Native frames are rendered by the original engine. Never animate a static mock preview.
    const started = performance.now();
    const origin = frame;
    let cancelled = false;
    let timer: number | undefined;
    const render = async () => {
      const next = Math.min(
        maxFrame,
        origin + Math.floor(((performance.now() - started) / 1000) * fps),
      );
      try {
        const blob = await browser.preview(next, fps);
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = url;
        setPreview(url);
        setFrame(next);
        if (next === maxFrame) setPlaying(false);
        else timer = window.setTimeout(() => void render(), 80);
      } catch (cause) {
        if (!cancelled) {
          setPreviewError(craftError(cause));
          setPlaying(false);
        }
      }
    };
    void render();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [
    playing,
    sourceMode,
    outputUrl,
    browser.state,
    maxFrame,
    fps,
    visible,
    doc?.revision,
  ]);
  React.useEffect(() => {
    setPlaying(false);
    setMediaDuration(0);
    videoRef.current?.pause();
  }, [source, outputUrl]);
  const seek = (next: number) => {
    const value = Math.max(0, Math.min(maxFrame, next));
    setFrame(value);
    if (videoRef.current) videoRef.current.currentTime = value / fps;
  };
  const togglePlay = () => {
    if (videoRef.current) {
      if (videoRef.current.paused)
        void videoRef.current
          .play()
          .catch((cause) => setPreviewError(craftError(cause)));
      else videoRef.current.pause();
    } else setPlaying((current) => !current);
  };
  function chooseCommand(next: CraftCapability) {
    setCommandId(next.id);
    setParams(initialCommandParams(next.inputSchema, selectedClip));
  }

  return (
    <section className="vs-editor" aria-label="Editor não linear de vídeo">
      <div className="vs-editor-toolbar">
        <div>
          <Film size={17} />
          <strong>
            {doc?.nativeEditorState?.engine === "effectcraft"
              ? "Composição"
              : "Montagem"}
          </strong>
          <span className="vs-muted">
            {doc?.composition.pages[0]
              ? `${doc.composition.pages[0].width} × ${doc.composition.pages[0].height}`
              : "Nenhum projeto aberto"}
          </span>
        </div>
        <div>
          <button
            className="vs-icon"
            aria-label="Desfazer"
            disabled={
              nativeLocked ||
              !commands.some((item) => item.id === "host.history.undo")
            }
            onClick={() => void run(studio.undo)}
          >
            <Undo2 size={16} />
          </button>
          <button
            className="vs-icon"
            aria-label="Refazer"
            disabled={
              nativeLocked ||
              !commands.some((item) => item.id === "host.history.redo")
            }
            onClick={() => void run(studio.redo)}
          >
            <Redo2 size={16} />
          </button>
          <button
            disabled={!studio.pending || studio.busy}
            onClick={() => void run(studio.save)}
          >
            <Save size={14} /> Salvar ajustes
          </button>
          {doc && !doc.nativeEditorState && (
            <button
              className="vs-primary"
              disabled={
                !studio.engineInfo?.available ||
                studio.busy ||
                (locked && studio.status === "loading")
              }
              onClick={() => void run(studio.migrate)}
            >
              <RefreshCw size={14} /> Ativar edição nativa
            </button>
          )}
        </div>
      </div>
      <div className="vs-edit-workspace">
        <aside className="vs-media-panel">
          <div className="vs-panel-heading">
            <h3>Mídia</h3>
            <button
              className="vs-icon"
              onClick={onUpload}
              aria-label="Importar mídia"
            >
              <Upload size={15} />
            </button>
          </div>
          <button className="vs-import" onClick={onUpload}>
            <Plus size={15} /> Importar arquivos
          </button>
          <div className="vs-asset-list">
            {assets.map((asset) => (
              <button
                key={asset.id}
                onClick={() => onSelectAsset(asset.id)}
                aria-pressed={selection?.id === asset.id}
                className={selection?.id === asset.id ? "is-selected" : ""}
              >
                <span className="vs-asset-symbol">
                  {asset.mediaType?.startsWith("audio/") ? (
                    <AudioLines size={18} />
                  ) : asset.mediaType?.startsWith("image/") ? (
                    <ImageIcon size={18} />
                  ) : (
                    <Film size={18} />
                  )}
                </span>
                <span>
                  <strong>{asset.title}</strong>
                  <small>{asset.mediaType?.split("/")[1]?.toUpperCase()}</small>
                </span>
              </button>
            ))}
          </div>
          {!assets.length && (
            <div className="vs-empty">
              <FolderOpen size={24} />
              <p>Seus materiais aparecem aqui.</p>
            </div>
          )}
          {selection && (
            <button
              disabled={
                nativeLocked ||
                !commands.some((item) => item.id === "asset.import")
              }
              onClick={() =>
                void run(() =>
                  apply({
                    id: "asset.import",
                    params: {
                      assetId: selection.id,
                      addToTimeline: true,
                      seconds: frame / fps,
                    },
                  }),
                )
              }
            >
              <Plus size={14} /> Inserir no cursor
            </button>
          )}
          <button className="vs-text-button" onClick={onLibrary}>
            Biblioteca <ChevronRight size={13} />
          </button>
        </aside>
        <div className="vs-monitor">
          <div className="vs-monitor-top">
            <span>
              {outputUrl
                ? "Resultado renderizado"
                : active
                  ? `Prévia visual · sem áudio · revisão ${doc?.revision}`
                  : selection
                    ? "Mídia original · sem efeitos da montagem"
                    : "Pré-visualização"}
            </span>
            <button
              className="vs-icon"
              aria-label="Tela cheia da prévia"
              onClick={() =>
                void previewRef.current
                  ?.requestFullscreen()
                  .catch((cause) => setPreviewError(craftError(cause)))
              }
            >
              <Maximize2 size={15} />
            </button>
          </div>
          <div className="vs-preview" ref={previewRef}>
            {outputUrl ? (
              <video
                ref={videoRef}
                src={outputUrl}
                controls
                onLoadedMetadata={(event) =>
                  setMediaDuration(
                    Number.isFinite(event.currentTarget.duration)
                      ? event.currentTarget.duration
                      : 0,
                  )
                }
                onError={() =>
                  setPreviewError(
                    "O navegador não conseguiu reproduzir este formato. O arquivo continua disponível para download.",
                  )
                }
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
                onTimeUpdate={(event) =>
                  setFrame(Math.round(event.currentTarget.currentTime * fps))
                }
                aria-label="Vídeo renderizado"
              />
            ) : active && preview ? (
              <img
                src={preview}
                alt="Quadro renderizado pelo motor de edição"
              />
            ) : !active &&
              source &&
              selection?.mediaType?.startsWith("video/") ? (
              <video
                ref={videoRef}
                src={source}
                controls
                onLoadedMetadata={(event) =>
                  setMediaDuration(
                    Number.isFinite(event.currentTarget.duration)
                      ? event.currentTarget.duration
                      : 0,
                  )
                }
                onError={() =>
                  setPreviewError(
                    "Este formato não pode ser reproduzido pelo navegador. Envie um vídeo compatível para pré-visualização.",
                  )
                }
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
                onEnded={() => setPlaying(false)}
                onTimeUpdate={(event) =>
                  setFrame(Math.round(event.currentTarget.currentTime * fps))
                }
                aria-label="Vídeo original enviado"
              />
            ) : !active &&
              source &&
              selection?.mediaType?.startsWith("image/") ? (
              <img src={source} alt={selection.title} />
            ) : !active &&
              source &&
              selection?.mediaType?.startsWith("audio/") ? (
              <audio src={source} controls aria-label="Áudio original" />
            ) : (
              <div className="vs-preview-empty">
                <span>
                  <MonitorGlyph />
                </span>
                <h3>
                  {doc
                    ? "Sua montagem começa aqui"
                    : "Seu próximo vídeo, quadro a quadro."}
                </h3>
                <p>
                  {doc
                    ? "A prévia da montagem depende do motor nativo. Você pode visualizar seus arquivos originais no painel Mídia."
                    : "Abra um projeto salvo ou prepare seu primeiro vídeo na área de criação."}
                </p>
                {!doc && (
                  <button onClick={onCreate}>
                    Preparar projeto <Plus size={15} />
                  </button>
                )}
              </div>
            )}
            {previewLoading && (
              <span className="vs-preview-loading" role="status">
                <LoaderCircle className="vs-spin" size={14} /> Renderizando
                quadro
              </span>
            )}
          </div>
          {previewError && (
            <p className="vs-inline-error" role="alert">
              {previewError}
            </p>
          )}
          <div className="vs-transport">
            <span className="vs-time">
              {timecode(frame / fps)} <small>/ {timecode(duration)}</small>
            </span>
            <div>
              <button
                className="vs-icon"
                aria-label="Voltar um quadro"
                disabled={!duration}
                onClick={() => seek(frame - 1)}
              >
                <SkipBack size={15} />
              </button>
              <button
                className="vs-play"
                aria-label={playing ? "Pausar vídeo" : "Reproduzir vídeo"}
                disabled={!playable}
                onClick={togglePlay}
              >
                {playing ? <Pause size={17} /> : <Play size={17} />}
              </button>
              <button
                className="vs-icon"
                aria-label="Avançar um quadro"
                disabled={!duration}
                onClick={() => seek(frame + 1)}
              >
                <SkipForward size={15} />
              </button>
            </div>
            <span className="vs-fps">{fps} fps</span>
          </div>
        </div>
        <aside className="vs-inspector">
          <div className="vs-panel-heading">
            <h3>Inspetor</h3>
            <Layers3 size={15} />
          </div>
          <div className="vs-tool-tabs" aria-label="Ferramentas do editor">
            {[
              { id: "clip", title: "Clipe", icon: Film },
              { id: "text", title: "Texto", icon: Type },
              { id: "audio", title: "Áudio", icon: AudioLines },
              { id: "captions", title: "Legendas", icon: Captions },
              { id: "effects", title: "Efeitos", icon: Layers3 },
            ].map((item) => (
              <button
                key={item.id}
                aria-label={item.title}
                title={item.title}
                aria-pressed={tool === item.id}
                onClick={() => {
                  setTool(item.id as Tool);
                  setCommandId("");
                }}
              >
                <item.icon size={16} />
              </button>
            ))}
          </div>
          <h4>
            {clip
              ? clip.name
              : {
                  clip: "Clipe e sequência",
                  text: "Títulos e textos",
                  audio: "Áudio e mixagem",
                  captions: "Legendas",
                  effects: "Efeitos e movimento",
                }[tool]}
          </h4>
          {clip && tool === "clip" && (
            <div className="vs-clip-inspector">
              <p>
                {timecode(clip.startMs / 1000)} ·{" "}
                {timecode(clip.durationMs / 1000)}
              </p>
              <label>
                Posição na montagem (s)
                <input
                  type="number"
                  min={0}
                  step={1 / fps}
                  value={position}
                  onChange={(event) => setPosition(Number(event.target.value))}
                />
              </label>
              <button
                disabled={
                  nativeLocked ||
                  !commands.some((item) => item.id === "timeline.move")
                }
                onClick={() => void run(() => apply(moveClip(clip, position)))}
              >
                Mover clipe
              </button>
              <label>
                Ajuste do corte (quadros)
                <input
                  type="number"
                  value={trim}
                  onChange={(event) => setTrim(Number(event.target.value))}
                />
              </label>
              <div className="vs-button-row">
                <button
                  disabled={
                    nativeLocked ||
                    !Number.isInteger(trim) ||
                    !trim ||
                    !commands.some((item) => item.id === "timeline.trim")
                  }
                  onClick={() =>
                    void run(() =>
                      apply({
                        id: "timeline.trim",
                        params: {
                          clip: Number(clip.id),
                          edge: "in",
                          mode: "regular",
                          deltaFrames: trim,
                        },
                      }),
                    )
                  }
                >
                  Ajustar início
                </button>
                <button
                  disabled={
                    nativeLocked ||
                    !Number.isInteger(trim) ||
                    !trim ||
                    !commands.some((item) => item.id === "timeline.trim")
                  }
                  onClick={() =>
                    void run(() =>
                      apply({
                        id: "timeline.trim",
                        params: {
                          clip: Number(clip.id),
                          edge: "out",
                          mode: "regular",
                          deltaFrames: trim,
                        },
                      }),
                    )
                  }
                >
                  Ajustar fim
                </button>
              </div>
            </div>
          )}
          {tool === "audio" &&
            clip &&
            commands.some((command) => command.id === "clip.audioGain") && (
              <div className="vs-quick-audio">
                <label>
                  Volume do clipe (dB)
                  <input
                    type="number"
                    min={-60}
                    max={12}
                    step={1}
                    value={gain}
                    disabled={nativeLocked}
                    onChange={(event) => setGain(Number(event.target.value))}
                  />
                </label>
                <button
                  disabled={nativeLocked}
                  onClick={() => void run(() => apply(audioGain(clip, gain)))}
                >
                  <Volume2 size={14} /> Aplicar volume
                </button>
              </div>
            )}
          {commandList.length ? (
            <>
              {commonCommands.length > 0 && (
                <div
                  className="vs-common-tools"
                  aria-label="Operações principais"
                >
                  {commonCommands.map((item) => (
                    <button
                      key={item.id}
                      disabled={nativeLocked}
                      aria-pressed={commandId === item.id}
                      onClick={() => chooseCommand(item)}
                    >
                      {labels[item.id] || item.label}
                    </button>
                  ))}
                </div>
              )}
              <details
                className="vs-disclosure vs-advanced-operations"
                key={tool}
              >
                <summary>
                  <span>
                    Todas as ferramentas
                    <small>Operações confirmadas por este motor</small>
                  </span>
                </summary>
                <div className="vs-disclosure-body">
                  <fieldset disabled={nativeLocked}>
                    <ClickoSelectMenu
                      label="Operação avançada"
                      value={commandId}
                      options={[
                        ["", "Escolha uma operação"],
                        ...commandList.map((item) => [
                          item.id,
                          labels[item.id] || item.label,
                        ]),
                      ]}
                      onChange={(value) => {
                        const next = commandList.find(
                          (item) => item.id === value,
                        );
                        if (next) chooseCommand(next);
                        else setCommandId("");
                      }}
                    />
                  </fieldset>
                </div>
              </details>
              {command && (
                <CommandForm
                  key={`${command.id}:${selectedClip || ""}`}
                  command={command}
                  params={params}
                  setParams={setParams}
                  disabled={nativeLocked}
                  assets={assets}
                  onApply={async () => {
                    const validation = commandValidation(
                      command.inputSchema,
                      params,
                    );
                    if (validation) throw new Error(validation);
                    await apply({ id: command.id, params });
                  }}
                  run={run}
                />
              )}
            </>
          ) : (
            <p className="vs-fine">
              As ferramentas de{" "}
              {
                {
                  clip: "corte e sequência",
                  text: "texto",
                  audio: "áudio",
                  captions: "legendas",
                  effects: "efeitos",
                }[tool]
              }{" "}
              aparecem conforme os comandos confirmados pelo motor.
            </p>
          )}
          {tool === "captions" && (
            <p className="vs-fine">
              Legendas manuais e arquivos SRT dependem dos comandos de
              legendagem do motor. Transcrição automática requer provedor
              habilitado; não é gerada no navegador.
            </p>
          )}
          {!active && (
            <div className="vs-inspector-note">
              {studio.engineInfo?.available
                ? "Ative a edição nativa deste projeto para liberar as ferramentas."
                : "Motor nativo indisponível. Os materiais e o briefing permanecem salvos."}
            </div>
          )}
          {doc?.nativeEditorState && (
            <p className="vs-fine">
              Versões e arquivos nativos ficam em “Histórico e arquivo do
              projeto”, abaixo do editor.
            </p>
          )}
        </aside>
      </div>
      <div className="vs-timeline">
        <div className="vs-timeline-toolbar">
          <div>
            <strong>Timeline</strong>
            <button
              className="vs-icon"
              aria-label="Dividir clipe no cursor"
              disabled={
                nativeLocked ||
                !clip ||
                !commands.some((item) => item.id === "timeline.razor")
              }
              onClick={() =>
                clip && void run(() => apply(splitClip(clip, frame / fps)))
              }
            >
              <Scissors size={16} />
            </button>
            <span className="vs-muted">
              {clips.length} elemento{clips.length === 1 ? "" : "s"} ·{" "}
              {doc?.nativeEditorState
                ? "Montagem nativa"
                : "Estrutura do projeto"}
            </span>
          </div>
          <div>
            <Minus size={13} />
            <input
              aria-label="Zoom da timeline"
              type="range"
              min={1}
              max={4}
              step={0.25}
              value={zoom}
              onChange={(event) => setZoom(Number(event.target.value))}
            />
            <Plus size={13} />
          </div>
        </div>
        <div className="vs-timeline-scroll">
          <div
            className="vs-timeline-inner"
            style={{ minWidth: `${zoom * 100}%` }}
          >
            <div className="vs-ruler">
              <span>TRILHAS</span>
              <div>
                {Array.from({ length: 7 }, (_, index) => (
                  <button
                    key={index}
                    disabled={!duration}
                    onClick={() => seek(Math.round((maxFrame * index) / 6))}
                  >
                    {timecode((duration * index) / 6).slice(0, 5)}
                  </button>
                ))}
              </div>
            </div>
            <input
              className="vs-seek"
              aria-label="Posição da timeline em quadros"
              type="range"
              min={0}
              max={maxFrame}
              value={Math.min(frame, maxFrame)}
              disabled={!duration}
              onChange={(event) => seek(Number(event.target.value))}
            />
            {(tracks.length
              ? tracks
              : [
                  {
                    id: "empty-video",
                    name: "Vídeo / imagem",
                    kind: "video",
                    muted: false,
                    clips: [],
                  },
                  {
                    id: "empty-audio",
                    name: "Áudio / narração",
                    kind: "audio",
                    muted: false,
                    clips: [],
                  },
                  {
                    id: "empty-caption",
                    name: "Texto / legendas",
                    kind: "caption",
                    muted: false,
                    clips: [],
                  },
                ]
            ).map((track) => (
              <div
                className={`vs-timeline-track vs-track-${track.kind}`}
                key={track.id}
              >
                <div className="vs-track-name">
                  {track.kind === "audio" ? (
                    <AudioLines size={15} />
                  ) : track.kind === "caption" ? (
                    <Type size={15} />
                  ) : (
                    <Film size={15} />
                  )}
                  <span>{track.name}</span>
                  {track.kind === "audio" && tracks.length > 0 && (
                    <button
                      className="vs-icon"
                      aria-label={`${track.muted ? "Ativar" : "Silenciar"} ${track.name}`}
                      disabled={
                        nativeLocked ||
                        !commands.some(
                          (item) => item.id === "timeline.setTrack",
                        )
                      }
                      onClick={() =>
                        void run(() =>
                          apply({
                            id: "timeline.setTrack",
                            params: {
                              track: Number(track.id),
                              muted: !track.muted,
                            },
                          }),
                        )
                      }
                    >
                      {track.muted ? (
                        <VolumeX size={13} />
                      ) : (
                        <Volume2 size={13} />
                      )}
                    </button>
                  )}
                </div>
                <div
                  className="vs-track-lane"
                  onDragOver={(event) => {
                    if (
                      !nativeLocked &&
                      commands.some((item) => item.id === "timeline.move")
                    )
                      event.preventDefault();
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    const item = clips.find(
                      (candidate) =>
                        candidate.id ===
                        event.dataTransfer.getData("application/x-clicko-clip"),
                    );
                    if (!item) return;
                    const rect = event.currentTarget.getBoundingClientRect();
                    const seconds = Math.max(
                      0,
                      Math.round(
                        ((event.clientX - rect.left) / rect.width) *
                          duration *
                          fps,
                      ) / fps,
                    );
                    void run(() =>
                      apply(moveClip({ ...item, trackId: track.id }, seconds)),
                    );
                  }}
                >
                  {!track.clips.length && (
                    <span className="vs-empty-lane">
                      Sem elementos nesta trilha
                    </span>
                  )}
                  {track.clips.map((item) => (
                    <button
                      className={`vs-timeline-clip ${selectedClip === item.id ? "is-selected" : ""}`}
                      key={item.id}
                      style={{
                        left: `${duration ? (item.startMs / 1000 / duration) * 100 : 0}%`,
                        width: `${duration ? Math.max(0.5, Math.min(100, (item.durationMs / 1000 / duration) * 100)) : 100}%`,
                      }}
                      draggable={
                        !nativeLocked &&
                        commands.some(
                          (command) => command.id === "timeline.move",
                        )
                      }
                      onDragStart={(event) =>
                        event.dataTransfer.setData(
                          "application/x-clicko-clip",
                          item.id,
                        )
                      }
                      aria-pressed={selectedClip === item.id}
                      title={`${item.name} · ${timecode(item.startMs / 1000)} · ${timecode(item.durationMs / 1000)}`}
                      onClick={() => {
                        setSelectedClip(item.id);
                        setTool("clip");
                      }}
                    >
                      <strong>{item.name}</strong>
                      <small>{timecode(item.durationMs / 1000)}</small>
                    </button>
                  ))}
                  <span
                    className="vs-playhead"
                    style={{
                      left: `${maxFrame ? (Math.min(frame, maxFrame) / maxFrame) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="vs-timeline-hint">
          {nativeLocked
            ? "Estrutura somente para leitura até a ativação do motor. Nenhum ajuste é aplicado sem confirmação."
            : "Selecione um clipe para ajustar cortes no inspetor. Arraste para reposicionar; alterações são confirmadas pelo servidor."}
        </p>
      </div>
    </section>
  );
}
function MonitorGlyph() {
  return <Film size={30} />;
}
function CommandForm({
  command,
  params,
  setParams,
  disabled,
  assets,
  onApply,
  run,
}: {
  command: CraftCapability;
  params: Record<string, unknown>;
  setParams: (value: Record<string, unknown>) => void;
  disabled: boolean;
  assets: AssetRecord[];
  onApply: () => Promise<void>;
  run: (task: () => Promise<unknown>) => Promise<void>;
}) {
  const [invalid, setInvalid] = React.useState<Record<string, boolean>>({});
  const markInvalid = (key: string, value: boolean) =>
    setInvalid((current) => ({ ...current, [key]: value }));
  const grouped = operationFields(command.inputSchema);
  return (
    <div className="vs-command-form">
      <fieldset disabled={disabled}>
        <SchemaFields
          schema={grouped.main}
          value={params}
          onChange={setParams}
          disabled={disabled}
          assets={assets}
          onInvalid={markInvalid}
        />
      </fieldset>
      <details className="vs-disclosure">
        <summary>
          <span>
            Mais ajustes<small>Parâmetros opcionais e técnicos</small>
          </span>
        </summary>
        <div className="vs-disclosure-body">
          <fieldset disabled={disabled}>
            <SchemaFields
              schema={grouped.advanced}
              value={params}
              onChange={setParams}
              disabled={disabled}
              assets={assets}
              onInvalid={markInvalid}
            />
          </fieldset>
          <details className="vs-raw-params">
            <summary>Editar parâmetros em JSON</summary>
            <JsonValue
              label="Parâmetros do comando (JSON)"
              value={params}
              disabled={disabled}
              onInvalid={(value) => markInvalid("advanced", value)}
              onChange={(next) => {
                if (next && typeof next === "object" && !Array.isArray(next)) {
                  setParams(next as Record<string, unknown>);
                  setInvalid({});
                } else markInvalid("advanced", true);
              }}
            />
          </details>
        </div>
      </details>
      <button
        className="vs-primary"
        disabled={disabled || Object.values(invalid).some(Boolean)}
        onClick={() => void run(onApply)}
      >
        Aplicar ajuste
      </button>
    </div>
  );
}
function SchemaFields({
  schema,
  value,
  onChange,
  disabled,
  assets,
  onInvalid,
  prefix = "",
}: {
  schema: CraftInputSchema;
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
  disabled: boolean;
  assets: AssetRecord[];
  onInvalid: (key: string, invalid: boolean) => void;
  prefix?: string;
}) {
  return (
    <div className="vs-schema-fields">
      {Object.entries(schema.properties || {}).map(([key, field]) => {
        const label = field.title || fields[key] || key;
        const set = (next: unknown) => onChange({ ...value, [key]: next });
        if (field.enum)
          return (
            <ClickoSelectMenu
              key={key}
              label={label}
              value={value[key] === undefined ? "" : JSON.stringify(value[key])}
              options={[
                ["", "Selecione…"],
                ...field.enum.map((item) => [
                  JSON.stringify(item),
                  String(item),
                ]),
              ]}
              onChange={(next) => set(next ? JSON.parse(next) : undefined)}
            />
          );
        if (key === "assetId")
          return (
            <ClickoSelectMenu
              key={key}
              label={label}
              value={String(value[key] || "")}
              options={[
                ["", "Escolha um material"],
                ...assets.map((asset) => [asset.id, asset.title]),
              ]}
              onChange={set}
            />
          );
        if (field.type === "object" && field.properties)
          return (
            <fieldset key={key} disabled={disabled}>
              <legend>{label}</legend>
              <SchemaFields
                schema={field}
                value={(value[key] as Record<string, unknown>) || {}}
                onChange={set}
                disabled={disabled}
                assets={assets}
                onInvalid={onInvalid}
                prefix={`${prefix}${key}.`}
              />
            </fieldset>
          );
        if (field.type === "boolean")
          return (
            <label className="vs-check" key={key}>
              <input
                type="checkbox"
                checked={Boolean(value[key])}
                disabled={disabled}
                onChange={(event) => set(event.target.checked)}
              />
              {label}
            </label>
          );
        if (
          field.type === "array" ||
          field.type === "object" ||
          !field.type ||
          Array.isArray(field.type)
        )
          return (
            <JsonValue
              key={key}
              label={label}
              value={value[key]}
              onChange={set}
              disabled={disabled}
              onInvalid={(invalid) => onInvalid(`${prefix}${key}`, invalid)}
            />
          );
        return (
          <label key={key}>
            {label}
            {schema.required?.includes(key) ? " *" : ""}
            <input
              disabled={disabled}
              type={
                field.type === "number" || field.type === "integer"
                  ? "number"
                  : "text"
              }
              step={field.type === "integer" ? 1 : "any"}
              min={field.minimum}
              max={field.maximum}
              value={
                typeof value[key] === "string" || typeof value[key] === "number"
                  ? (value[key] as string | number)
                  : ""
              }
              onChange={(event) =>
                set(
                  event.target.value === ""
                    ? undefined
                    : field.type === "number" || field.type === "integer"
                      ? Number(event.target.value)
                      : event.target.value,
                )
              }
            />
            {field.description && <small>{field.description}</small>}
          </label>
        );
      })}
    </div>
  );
}
function JsonValue({
  label,
  value,
  onChange,
  disabled,
  onInvalid,
}: {
  label: string;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled: boolean;
  onInvalid: (invalid: boolean) => void;
}) {
  const [raw, setRaw] = React.useState(
    value === undefined ? "" : JSON.stringify(value, null, 2),
  );
  const [error, setError] = React.useState(false);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);
  React.useEffect(() => {
    if (document.activeElement !== inputRef.current) {
      setRaw(value === undefined ? "" : JSON.stringify(value, null, 2));
      setError(false);
    }
  }, [value]);
  return (
    <label>
      {label}
      <textarea
        ref={inputRef}
        value={raw}
        disabled={disabled}
        aria-invalid={error}
        placeholder="Valor JSON: número, texto, lista ou objeto"
        onChange={(event) => {
          setRaw(event.target.value);
          try {
            onInvalid(false);
            onChange(
              event.target.value.trim()
                ? JSON.parse(event.target.value)
                : undefined,
            );
            setError(false);
          } catch {
            setError(true);
            onInvalid(true);
          }
        }}
      />
      {error && <small role="alert">Informe um valor JSON válido.</small>}
    </label>
  );
}
