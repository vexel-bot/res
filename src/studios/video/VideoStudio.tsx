import React from "react";
import {
  ArrowRight,
  AudioLines,
  Check,
  ChevronRight,
  Clapperboard,
  Film,
  FolderOpen,
  Image as ImageIcon,
  Layers3,
  LoaderCircle,
  Megaphone,
  MonitorPlay,
  Plus,
  RefreshCw,
  Save,
  Sparkles,
  Upload,
  Video,
  WandSparkles,
  X,
} from "lucide-react";
import { apiFetch } from "../../api";
import {
  productApi,
  type AssetRecord,
  type StudioCapabilitiesRecord,
  type StudioDocumentCreate,
  type StudioGenerationJobRecord,
} from "../../api/productApi";
import { useProductData } from "../../context/ProductDataContext";
import { ClickoSelectMenu } from "../../components/ClickoSelectMenu";
import {
  craftApi,
  type CraftCommand,
  type CraftDocument,
} from "../craft/craftApi";
import { craftCommands } from "../craft/craftState";
import { craftError, useCraftStudio } from "../craft/useCraftStudio";
import {
  CraftModelPicker,
  type ModelSelection,
} from "../craft/CraftModelPicker";
import { VideoEditor } from "./VideoEditor";
import { CanonicalVideoEditor } from "./CanonicalVideoEditor";
import { LegacyVideoProjects } from "./LegacyVideoProjects";
import { VideoProjectTools } from "./VideoProjectTools";
import { workflowHint } from "./videoUsability";
import {
  dimensions,
  documentBrief,
  initialVideoBrief,
  JOB_LABELS,
  jobProgress,
  motionTitleCommand,
  outputAsset,
  updateVideoBrief,
  validateBrief,
  VIDEO_KINDS,
  videoDocumentInput,
  videoBriefDefaults,
  type VideoArea,
  type VideoBrief,
} from "./videoModel";
import "./video-studio.css";
import { matchesStudioDraft, readStudioSession, writeStudioSession } from '../studioSession';
import { StudioKlicButton, StudioUtilityPanel } from '../shared/StudioWorkspace';

const AREAS = [
  { id: "ai", name: "Criar com IA", icon: Sparkles },
  { id: "editor", name: "Editor de vídeo", icon: Film },
  { id: "motion", name: "Motion design", icon: Layers3 },
  { id: "ad", name: "Criar anúncio", icon: Megaphone },
] as const;
type SceneCapability = {
  state: "unavailable" | "experimental" | "qualified";
  serviceAccessible: boolean;
  modelReadiness: string;
};
export type VideoController = ReturnType<typeof useCraftStudio>;
type VideoStudioProps = {
  initialBrief?: { title: string; objective: string };
  onLibrary: () => void;
  onApprovals: () => void;
  embedded?: boolean;
  requestedArea?: VideoArea;
  onAreaChange?: (area: VideoArea) => void;
};
type VideoNavigationState = { brief: VideoBrief; project?: CraftDocument; assets: AssetRecord[]; materials: string[]; dirty: boolean };
export function VideoStudio(props: VideoStudioProps) {
  const data = useProductData();
  if (!data.activeWorkspace || !data.bootstrap || data.status !== 'ready') return <section className="vs-root" role={data.error ? 'alert' : 'status'}><p>{data.error || 'Carregando seu ambiente de vídeo…'}</p>{data.error && <button onClick={() => void data.refresh()}>Tentar novamente</button>}</section>;
  return <VideoRoom key={`${data.bootstrap.user.id}:${data.activeWorkspace.id}`} {...props} />;
}
function VideoRoom({
  initialBrief,
  onLibrary,
  onApprovals,
  embedded,
  requestedArea,
  onAreaChange,
}: VideoStudioProps) {
  const data = useProductData();
  const sessionKey = JSON.stringify(['video', data.bootstrap!.user.id, data.activeWorkspace!.id]);
  const [restored] = React.useState(() => readStudioSession<VideoNavigationState>(sessionKey));
  const recovered = restored && matchesStudioDraft(restored.brief, initialVideoBrief()) && Array.isArray(restored.assets) && Array.isArray(restored.materials) && (!restored.project || restored.project.workspaceId === data.activeWorkspace!.id) ? restored : undefined;
  const [area, updateArea] = React.useState<VideoArea>(requestedArea || 'ai');
  const pendingArea = React.useRef<VideoArea | undefined>(undefined);
  const setArea = (next: VideoArea) => { pendingArea.current = next; updateArea(next); };
  React.useEffect(() => { if (requestedArea) { pendingArea.current = undefined; updateArea(requestedArea); } }, [requestedArea]);
  const [brief, setBrief] = React.useState(() =>
    recovered?.brief || initialVideoBrief(initialBrief),
  );
  const [project, setProject] = React.useState<CraftDocument | undefined>(recovered?.project);
  const [projects, setProjects] = React.useState<CraftDocument[]>([]);
  const [addedAssets, setAddedAssets] = React.useState<AssetRecord[]>(recovered?.assets || []);
  const [materials, setMaterials] = React.useState<string[]>(recovered?.materials || []);
  const [selectedAsset, setSelectedAsset] = React.useState<string>();
  const [capabilities, setCapabilities] =
    React.useState<StudioCapabilitiesRecord>();
  const [scene, setScene] = React.useState<SceneCapability>();
  const [cpuRenderer, setCpuRenderer] = React.useState<{ available: boolean }>();
  const [catalogError, setCatalogError] = React.useState<string>();
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [dirty, setDirty] = React.useState(recovered?.dirty || false);
  const [reload, setReload] = React.useState(0);
  const [showProjects, setShowProjects] = React.useState(false);
  const [servicesOpen, setServicesOpen] = React.useState(false);
  const [model, setModel] = React.useState<ModelSelection>({
    available: false,
  });
  const [instruction, setInstruction] = React.useState("");
  const [outputUrl, setOutputUrl] = React.useState<string>();
  const [outputIsVideo, setOutputIsVideo] = React.useState(false);
  const fileInput = React.useRef<HTMLInputElement>(null);
  const servicesRef = React.useRef<HTMLDetailsElement>(null);
  const actionRef = React.useRef(false);
  const briefVersionRef = React.useRef(0);
  const creationAttempt = React.useRef<StudioDocumentCreate | undefined>(
    undefined,
  );
  const mounted = React.useRef(true);
  React.useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const workspaceId = data.activeWorkspace?.id;
  const engine =
    (!project && area === "motion") ||
    project?.nativeEditorState?.engine === "effectcraft" ||
    (project?.composition.narrative?.videoStudio &&
      (project.composition.narrative.videoStudio as { engine?: string })
        .engine === "effectcraft")
      ? "effectcraft"
      : "filmcraft";
  const studio = useCraftStudio({
    engine,
    workspaceId,
    userId: data.bootstrap?.user.id,
    requestedDocumentId: project?.documentId,
    contentType: "video",
    title: brief.title,
    brandRevision: 1,
    enabled: data.status === "ready" && Boolean(project?.nativeEditorState),
    standalone: true,
  });
  const assets = [...addedAssets, ...(data.snapshot?.assets || [])].filter(
    (asset, index, all) =>
      /^(video|audio|image)\//.test(asset.mediaType || "") &&
      all.findIndex((item) => item.id === asset.id) === index,
  );
  const currentDoc =
    studio.document?.documentId === project?.documentId && studio.document && studio.document.revision >= (project?.revision || 0)
      ? studio.document
      : project;
  const canonicalActive = area === 'editor' && Boolean(currentDoc && !currentDoc.nativeEditorState && currentDoc.composition.mediaTimeline);
  React.useEffect(() => {
    writeStudioSession(sessionKey, { brief, project:currentDoc, assets:addedAssets, materials, dirty } satisfies VideoNavigationState);
  }, [sessionKey, brief, currentDoc, addedAssets, materials, dirty]);
  React.useEffect(() => {
    const beforeLeave = (event: Event) => {
      if (actionRef.current || busy || studio.busy) { event.preventDefault(); setNotice('Aguarde a confirmação do processamento antes de trocar de módulo.'); }
    };
    window.addEventListener('clicko:studio-before-leave', beforeLeave);
    return () => window.removeEventListener('clicko:studio-before-leave', beforeLeave);
  }, [busy, studio.busy]);
  // A successful save may open the editor while its request is still settling.
  // Notify navigation only after the real operation has released its leave guard.
  React.useEffect(() => {
    if (busy || studio.busy || actionRef.current || !pendingArea.current) return;
    const next = pendingArea.current; pendingArea.current = undefined;
    onAreaChange?.(next);
  }, [area, busy, studio.busy, onAreaChange]);
  const available = Boolean(
    studio.engineInfo?.available &&
    currentDoc?.nativeEditorState?.engine === engine &&
    studio.inspection?.documentId === currentDoc.documentId &&
    studio.document?.documentId === currentDoc.documentId,
  );
  const locked =
    !available ||
    busy ||
    studio.busy ||
    Boolean(
      studio.recovery || studio.aiRecovery || studio.pending?.attempted,
    ) ||
    studio.status === "conflict";
  const commands = craftCommands(studio.inspection).filter(
    (command) => (command as { available?: boolean }).available !== false,
  );
  const formats =
    studio.engineInfo?.formats.filter(
      (format) => !["fcproj", "ecproj", "pcraft"].includes(format),
    ) || [];
  const [exportFormat, setExportFormat] = React.useState("");
  const hint = workflowHint(area, Boolean(currentDoc), available || Boolean(cpuRenderer?.available && currentDoc && !currentDoc.nativeEditorState));
  React.useEffect(() => {
    if (!formats.includes(exportFormat)) setExportFormat(formats[0] || "");
  }, [formats.join("|"), exportFormat]);

  React.useEffect(() => {
    if (!workspaceId) return;
    const controller = new AbortController();
    setLoading(true);
    setCatalogError(undefined);
    // Local projects and FFmpeg must not wait for an optional AI model preflight.
    void productApi.studioDocuments(workspaceId).then(documents => {
      if (!controller.signal.aborted) setProjects((documents as CraftDocument[]).filter(doc => doc.contentType === "video" || doc.contentType === "presenter"));
    }).catch(cause => {
      if (!controller.signal.aborted) setCatalogError(craftError(cause));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    const unconfirmed = () => {
      if (!controller.signal.aborted) setNotice("Não foi possível verificar todos os serviços de geração. Os recursos não confirmados permanecem indisponíveis.");
    };
    void productApi.studioCapabilities(workspaceId).then(readiness => {
      if (!controller.signal.aborted) setCapabilities(readiness);
    }).catch(unconfirmed);
    void apiFetch<SceneCapability>("/api/v1/studios/v1/scene-generation-capability", { signal: controller.signal }).then(generation => {
      if (!controller.signal.aborted) setScene(generation);
    }).catch(unconfirmed);
    void apiFetch<{ available: boolean }>("/api/v1/studios/v1/video/capabilities", { signal: controller.signal }).then(cpu => {
      if (!controller.signal.aborted) setCpuRenderer(cpu);
    }).catch(() => { /* An unverified local renderer remains unavailable. */ });
    return () => controller.abort();
  }, [workspaceId, reload]);
  React.useEffect(() => {
    const leave = (event: BeforeUnloadEvent) => {
      if (dirty || actionRef.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", leave);
    return () => window.removeEventListener("beforeunload", leave);
  }, [dirty]);
  React.useEffect(() => {
    const assetId =
      currentDoc && studio.job?.documentId === currentDoc.documentId
        ? outputAsset(studio.job)
        : undefined;
    setOutputUrl(undefined);
    setOutputIsVideo(false);
    if (!assetId) return;
    const controller = new AbortController();
    let url: string | undefined;
    void productApi
      .studioAssetBlob(assetId, controller.signal)
      .then((blob) => {
        if (!controller.signal.aborted) {
          url = URL.createObjectURL(blob);
          setOutputIsVideo(blob.type.startsWith("video/"));
          setOutputUrl(url);
        }
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(craftError(cause));
      });
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [studio.job?.id, studio.job?.status, currentDoc?.documentId]);

  function change<K extends keyof VideoBrief>(key: K, value: VideoBrief[K]) {
    briefVersionRef.current += 1;
    setBrief((current) => ({ ...current, [key]: value }));
    setDirty(true);
  }
  async function run(task: () => Promise<unknown>) {
    if (actionRef.current) return;
    actionRef.current = true;
    setBusy(true);
    setError(undefined);
    setNotice(undefined);
    try {
      await task();
    } catch (cause) {
      if (mounted.current) {
        const status =
          cause && typeof cause === "object" && "status" in cause
            ? Number(cause.status)
            : 0;
        setError(
          status === 409
            ? "O projeto foi alterado em outra sessão ou precisa de revisão. Atualize a revisão salva antes de tentar novamente."
            : craftError(cause),
        );
      }
    } finally {
      actionRef.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  async function saveProject(motion = false) {
    if (!workspaceId) throw new Error("Aguarde o carregamento do ambiente.");
    const resolvedBrief = videoBriefDefaults(brief, area === 'ad');
    const validation = validateBrief(resolvedBrief);
    if (validation) throw new Error(validation);
    const savedBriefVersion = briefVersionRef.current;
    let next: CraftDocument;
    if (currentDoc) {
      if (
        studio.document &&
        studio.document.documentId !== currentDoc.documentId
      )
        throw new Error(
          "Aguarde a abertura da revisão deste projeto antes de salvar.",
        );
      const active = currentDoc.nativeEditorState ? (await studio.save()) || currentDoc : currentDoc;
      if (active.documentId !== currentDoc.documentId)
        throw new Error(
          "O projeto mudou. Abra novamente a revisão antes de salvar.",
        );
      next = await productApi.replaceStudioDocument(
        active.documentId,
        active.revision,
        updateVideoBrief(active, resolvedBrief),
      );
    } else {
      if (creationAttempt.current) {
        // POST /documents has no idempotency header. Reconcile ambiguous transport
        // outcomes using its durable correlation ID; never silently duplicate a draft.
        const existing = await productApi.studioDocuments(workspaceId);
        const recovered = existing.find(
          (doc) => doc.correlationId === creationAttempt.current?.correlationId,
        );
        if (!recovered)
          throw new Error(
            "A criação anterior ainda não foi confirmada. Atualize os projetos antes de reenviar; não duplicamos o pedido automaticamente.",
          );
        next = await productApi.replaceStudioDocument(
          recovered.documentId,
          recovered.revision,
          updateVideoBrief(recovered, resolvedBrief),
        );
      } else {
        const input = videoDocumentInput(
          workspaceId,
          resolvedBrief,
          assets.filter((asset) => materials.includes(asset.id)),
          motion,
        );
        creationAttempt.current = input;
        try {
          next = await productApi.createStudioDocument(input);
        } catch (cause) {
          const status =
            cause && typeof cause === "object" && "status" in cause
              ? Number(cause.status)
              : 0;
          if (status >= 400 && status < 500 && status !== 408)
            creationAttempt.current = undefined;
          throw cause;
        }
      }
      creationAttempt.current = undefined;
    }
    if (!mounted.current) return next;
    setProject(next);
    // Typing during a request must remain an unsaved change, not be cleared by
    // the acknowledgement for the older brief that was actually submitted.
    if (briefVersionRef.current === savedBriefVersion) { setBrief(resolvedBrief); setDirty(false); }
    setProjects((current) => [
      next,
      ...current.filter((doc) => doc.documentId !== next.documentId),
    ]);
    studio.refresh();
    setNotice(
      "Projeto salvo no seu ambiente. O briefing não é um vídeo renderizado.",
    );
    return next;
  }
  async function openProject(doc: CraftDocument) {
    if (dirty || studio.pending) {
      if (
        !window.confirm(
          "Salvar os ajustes atuais antes de abrir outro projeto?",
        )
      )
        return;
      await saveProject(area === "motion");
    }
    if (doc.documentId === currentDoc?.documentId) {
      setShowProjects(false);
      setArea("editor");
      return;
    }
    // A catalog entry is a summary, not an authoritative revision. Reopening
    // must use the latest server document before populating editable fields.
    const fresh = (await productApi.studioDocument(
      doc.documentId,
    )) as CraftDocument;
    if (fresh.workspaceId !== workspaceId)
      throw new Error("Este projeto não pertence ao ambiente atual.");
    setProject(fresh);
    setBrief(documentBrief(fresh));
    setMaterials((fresh.assets || []).map((asset) => asset.id));
    setDirty(false);
    setError(undefined);
    setNotice(undefined);
    setSelectedAsset(undefined);
    setShowProjects(false);
    setArea("editor");
  }
  function newProject() {
    if (!window.dispatchEvent(new Event('clicko:studio-before-leave', { cancelable:true }))) return;
    if (
      (dirty || studio.pending || creationAttempt.current) &&
      !window.confirm(
        creationAttempt.current
          ? "Uma criação anterior ainda aguarda confirmação. Verifique Projetos para evitar duplicação. Deseja iniciar outro rascunho mesmo assim?"
          : "Há ajustes não salvos. Deseja iniciar outro projeto?",
      )
    )
      return;
    // A pending native batch is retained by useCraftStudio's recovery mechanism.
    creationAttempt.current = undefined;
    setProject(undefined);
    setBrief(initialVideoBrief());
    setMaterials([]);
    setDirty(false);
    setError(undefined);
    setNotice(undefined);
    setSelectedAsset(undefined);
    setArea("ai");
  }
  async function upload(files: FileList | null) {
    if (!files?.length || !workspaceId) return;
    const selected = Array.from(files);
    await run(async () => {
      for (const file of selected) {
        if (!/^(video|image|audio)\//.test(file.type))
          throw new Error("Envie arquivos de vídeo, imagem ou áudio.");
        const asset = await craftApi.uploadAsset(workspaceId, file);
        if (!mounted.current) return;
        setAddedAssets((current) => [asset, ...current]);
        setSelectedAsset(asset.id);
        if (!currentDoc) {
          setMaterials((current) => [...current, asset.id]);
          setDirty(true);
        }
      }
      setNotice("Materiais enviados para a biblioteca deste ambiente.");
    });
  }
  async function apply(command: CraftCommand) {
    if (locked || !commands.some((item) => item.id === command.id))
      throw new Error(
        "Esta ferramenta depende do motor de edição ativo e da versão do projeto.",
      );
    studio.queue(command);
    await studio.save();
    setReload((value) => value + 1);
  }
  async function applyDirection() {
    if (!model.available || locked)
      throw new Error(
        "Ative o motor do projeto e selecione uma conexão de IA disponível.",
      );
    await studio.applyAI(
      instruction.trim() ||
        `Monte este vídeo com os materiais do projeto. Objetivo: ${brief.objective}. Público: ${brief.audience}. Roteiro: ${brief.script}. Estilo: ${brief.style}. CTA: ${brief.cta}. Não invente materiais ou capacidades.`,
      model.connectionId,
      model.model,
    );
    setReload((value) => value + 1);
  }
  async function openLibrary() {
    if (dirty || studio.pending) {
      if (
        !window.confirm(
          "Salvar os ajustes do projeto antes de abrir a Biblioteca?",
        )
      )
        return;
      await saveProject(area === "motion");
    }
    onLibrary();
  }
  const assetPicker = (
    <div className="vs-materials">
      <div className="vs-panel-heading">
        <div>
          <h3>Materiais do projeto</h3>
          <p>Vídeos, imagens e áudio do seu ambiente.</p>
        </div>
        <button
          className="vs-icon"
          onClick={() => fileInput.current?.click()}
          disabled={busy}
          aria-label="Enviar materiais"
        >
          <Upload size={16} />
        </button>
      </div>
      {!assets.length ? (
        <button
          className="vs-upload-zone"
          onClick={() => fileInput.current?.click()}
          disabled={busy}
        >
          <Upload size={22} />
          <strong>Traga seus materiais</strong>
          <span>Selecione vídeos, imagens ou áudio</span>
        </button>
      ) : (
        <div className="vs-asset-list">
          {assets.map((asset) => (
            <button
              key={asset.id}
              className={materials.includes(asset.id) ? "is-selected" : ""}
              aria-pressed={materials.includes(asset.id)}
              onClick={() => {
                setSelectedAsset(asset.id);
                if (!currentDoc) {
                  setMaterials((current) =>
                    current.includes(asset.id)
                      ? current.filter((id) => id !== asset.id)
                      : [...current, asset.id],
                  );
                  setDirty(true);
                }
              }}
            >
              <span className="vs-asset-symbol">
                {asset.mediaType?.startsWith("audio/") ? (
                  <AudioLines />
                ) : asset.mediaType?.startsWith("image/") ? (
                  <ImageIcon />
                ) : (
                  <Video />
                )}
              </span>
              <span>
                <strong>{asset.title}</strong>
                <small>
                  {asset.mediaType?.split("/")[1]?.toUpperCase()}{" "}
                  {asset.sizeBytes
                    ? `· ${(asset.sizeBytes / 1024 / 1024).toFixed(1)} MB`
                    : ""}
                </small>
              </span>
              {materials.includes(asset.id) && <Check size={14} />}
            </button>
          ))}
        </div>
      )}
      <button className="vs-text-button" onClick={() => void run(openLibrary)}>
        Abrir biblioteca <ArrowRight size={13} />
      </button>
    </div>
  );

  return (
    <section
      className="vs-root"
      data-integrated-editor={canonicalActive}
      data-video-area={area}
      aria-label="Estúdio de vídeo Clicko"
    >
      <header className="vs-header" hidden={canonicalActive}>
        <div>
          <div className="vs-eyebrow">
            <Clapperboard size={14} /> CLICKO STUDIOS
          </div>
          <h1>Estúdio de vídeo</h1>
          <p>Da ideia ao último corte. Seu audiovisual, em um só lugar.</p>
        </div>
        <div className="vs-header-actions"><StudioKlicButton/>
          <button
            onClick={() => setShowProjects((value) => !value)}
            aria-expanded={showProjects}
          >
            <FolderOpen size={16} /> Projetos{" "}
            <span className="vs-count">{projects.length}</span>
          </button>
          <button
            className="vs-primary"
            onClick={newProject}
            disabled={busy || studio.busy}
          >
            <Plus size={16} /> Novo projeto
          </button>
        </div>
      </header>
      <nav className="vs-area-nav" aria-label="Áreas do estúdio" hidden={embedded}>
        {AREAS.map((item) => (
          <button
            key={item.id}
            aria-current={area === item.id ? "page" : undefined}
            onClick={() => setArea(item.id)}
          >
            <item.icon size={18} />
            <span>{item.name}</span>
          </button>
        ))}
      </nav>
      <div className="vs-project-bar" hidden={area === "editor" && Boolean(currentDoc && !currentDoc.nativeEditorState)}>
        <span className="vs-project-name">
          <span className="vs-status-dot" />
          <strong>
            {currentDoc?.title || brief.title || "Projeto sem título"}
          </strong>
          <small>
            {dirty
              ? "Ajustes não salvos"
              : currentDoc
                ? `Revisão ${currentDoc.revision} · salvo`
                : "Novo rascunho"}
          </small>
        </span>
        <div>
          <button
            className="vs-text-button"
            disabled={
              busy ||
              studio.busy ||
              Boolean(
                studio.recovery ||
                studio.aiRecovery ||
                studio.pending?.attempted,
              )
            }
            onClick={() => void run(() => saveProject(area === "motion"))}
          >
            {busy ? (
              <LoaderCircle size={15} className="vs-spin" />
            ) : (
              <Save size={15} />
            )}{" "}
            Salvar projeto
          </button>
          {currentDoc && (
            <button
              className="vs-text-button"
              onClick={() => {
                setArea("editor");
              }}
            >
              <MonitorPlay size={15} /> Abrir editor
            </button>
          )}
        </div>
      </div>
      <details className="studio-fold vs-workflow-disclosure" hidden={canonicalActive}><summary>Ajuda e recursos deste Studio</summary>
      <div
        className="vs-workflow-hint"
        aria-label="Orientação da área de trabalho"
      >
        <span className="vs-workflow-mark">
          <Film size={17} />
        </span>
        <div>
          <strong>{hint.title}</strong>
          <p>{hint.text}</p>
        </div>
        {area !== "editor" && (
          <button
            className="vs-text-button"
            onClick={() => {
              setServicesOpen(true);
              window.requestAnimationFrame(() => {
                servicesRef.current?.scrollIntoView({
                  block: "center",
                  behavior: "instant",
                });
                servicesRef.current
                  ?.querySelector("summary")
                  ?.focus({ preventScroll: true });
              });
            }}
            aria-expanded={servicesOpen}
            aria-controls="video-service-requirements"
          >
            Recursos e requisitos <ChevronRight size={14} />
          </button>
        )}
      </div>
      </details>
      {data.status === "loading" && (
        <div className="vs-banner" role="status">
          <LoaderCircle size={16} className="vs-spin" /> Carregando seu ambiente
          de produção…
        </div>
      )}
      {(busy || (studio.busy && currentDoc)) && (
        <div className="vs-banner" role="status">
          <LoaderCircle size={16} className="vs-spin" />
          {studio.status === "loading"
            ? "Carregando a revisão salva do projeto…"
            : "Processando solicitação. Aguarde a confirmação do serviço…"}
        </div>
      )}
      {data.error && (
        <div className="vs-banner vs-error" role="alert">
          {data.error}
          <button onClick={() => void data.refresh()}>Tentar novamente</button>
        </div>
      )}
      {(error || studio.error) && (
        <div className="vs-banner vs-error" role="alert">
          {error || studio.error}
          <button
            onClick={() => {
              setError(undefined);
              studio.refresh();
            }}
          >
            <RefreshCw size={14} /> Atualizar projeto
          </button>
        </div>
      )}
      {(notice || studio.notice) && !(canonicalActive && notice === 'Projeto salvo no seu ambiente. O briefing não é um vídeo renderizado.') && (
        <div className="vs-banner" role="status">
          {notice || studio.notice}
        </div>
      )}
      {studio.recovery && (
        <div className="vs-banner">
          Há alterações recuperáveis neste navegador.
          <button onClick={studio.recover}>Recuperar alterações</button>
          <button
            onClick={() =>
              void run(async () => {
                const url = URL.createObjectURL(
                  new Blob([JSON.stringify(studio.recovery, null, 2)], {
                    type: "application/json",
                  }),
                );
                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = "clicko-recuperacao-video.json";
                anchor.click();
                window.setTimeout(() => URL.revokeObjectURL(url), 1000);
              })
            }
          >
            Guardar cópia
          </button>
          <button onClick={studio.discardRecovery}>
            Descartar recuperação
          </button>
        </div>
      )}
      {studio.pending?.attempted && (
        <div className="vs-banner">
          Um salvamento aguarda confirmação. Não envie novas alterações.
          <button onClick={() => void run(studio.save)}>
            Verificar salvamento
          </button>
        </div>
      )}
      {studio.aiRecovery && (
        <div className="vs-banner">
          Pedido de IA pendente de confirmação.
          <button onClick={() => void run(studio.reconcileAI)}>
            Verificar pedido
          </button>
        </div>
      )}
      <StudioUtilityPanel title="Projetos de vídeo" open={showProjects} onClose={() => setShowProjects(false)}>
        {canonicalActive && <>
          <button type="button" className="vs-primary" disabled={busy || studio.busy} onClick={() => { newProject(); setShowProjects(false); }}><Plus size={16}/>Novo projeto</button>
          <details className="studio-fold"><summary>Ajuda e recursos deste Studio</summary><strong>{hint.title}</strong><p>{hint.text}</p></details>
        </>}
        <section className="vs-projects">
          <div className="vs-panel-heading">
            <h2>Seus projetos</h2>
            <button
              className="vs-icon"
              aria-label="Fechar projetos"
              onClick={() => setShowProjects(false)}
            >
              <X size={16} />
            </button>
          </div>
          {loading ? (
            <p role="status">Buscando projetos…</p>
          ) : catalogError ? (
            <div role="alert">
              <p>{catalogError}</p>
              <button onClick={() => setReload((value) => value + 1)}>
                Tentar novamente
              </button>
            </div>
          ) : projects.length ? (
            <div className="vs-project-grid">
              {projects.map((doc) => (
                <button
                  className="vs-project-card"
                  key={doc.documentId}
                  disabled={busy || studio.busy}
                  onClick={() => { if (window.dispatchEvent(new Event('clicko:studio-before-leave', { cancelable:true }))) void run(() => openProject(doc)); }}
                >
                  <span className="vs-project-thumb">
                    {doc.nativeEditorState?.engine === "effectcraft" ? (
                      <Layers3 size={28} />
                    ) : (
                      <Film size={28} />
                    )}
                  </span>
                  <span>
                    <strong>{doc.title}</strong>
                    <small>
                      {doc.nativeEditorState?.engine === "effectcraft"
                        ? "Composição"
                        : "Vídeo"}{" "}
                      · {Math.round(documentBrief(doc).duration)}s
                    </small>
                    <small>
                      {new Date(doc.updatedAt).toLocaleDateString("pt-BR")} ·{" "}
                      {doc.status === "draft"
                        ? "Rascunho"
                        : doc.status === "approved"
                          ? "Aprovado"
                          : doc.status === "in_review"
                            ? "Em revisão"
                            : "Arquivado"}
                    </small>
                  </span>
                  <ChevronRight size={15} />
                </button>
              ))}
            </div>
          ) : (
            <div className="vs-empty">
              <FolderOpen size={26} />
              <h3>Um espaço para suas próximas produções</h3>
              <p>
                Os projetos salvos neste ambiente aparecem aqui para você
                continuar.
              </p>
            </div>
          )}
          {workspaceId && (
            <LegacyVideoProjects
              workspaceId={workspaceId}
              disabled={busy || studio.busy}
              engineAvailable={Boolean(studio.engineInfo?.available)}
              run={run}
              onOpen={openProject}
              onNotice={setNotice}
            />
          )}
        </section>
      </StudioUtilityPanel>
      <div hidden={area === "editor" || Boolean(area === "motion" && currentDoc && !currentDoc.nativeEditorState)} className="vs-create-grid">
        <main className="vs-create-main">
          <div className="vs-section-intro">
            <span className="vs-step-label">
              {area === "ad"
                ? "CAMPANHAS EM VÍDEO"
                : area === "motion"
                  ? "MOVIMENTO COM INTENÇÃO"
                  : "CRIAÇÃO ASSISTIDA"}
            </span>
            <h2>
              {area === "ad"
                ? "Uma boa oferta merece um bom vídeo."
                : area === "motion"
                  ? "Dê movimento à sua mensagem."
                  : "Que história vamos colocar em movimento?"}
            </h2>
            <p>
              {area === "motion"
                ? "Composições, títulos e animações com as ferramentas do motor de efeitos."
                : "Defina a direção, reúna seus materiais e continue na montagem."}
            </p>
          </div>
          {area === "ad" ? (
            <details className="vs-disclosure vs-start-options"><summary>Materiais de partida · {brief.adPath === "own" ? "Vídeo próprio" : brief.adPath === "assembly" ? "Montagem" : "Ver opções"}</summary>
            <div className="vs-ad-paths">
              {[
                {
                  id: "own",
                  title: "Seu vídeo",
                  text: "Parta de uma gravação própria.",
                  icon: Video,
                  enabled: true,
                },
                {
                  id: "assembly",
                  title: "Montagem de mídias",
                  text: "Combine os ativos da biblioteca.",
                  icon: Layers3,
                  enabled: true,
                },
                {
                  id: "avatar",
                  title: "Apresentador / avatar",
                  text: "Exige identidade, voz e consentimento aprovados.",
                  icon: MonitorPlay,
                  enabled: false,
                },
                {
                  id: "generated",
                  title: "Geração integral",
                  text: "Exige modelo e plano de cenas qualificados.",
                  icon: Sparkles,
                  enabled: false,
                },
              ].map((item) => (
                <button
                  key={item.id}
                  disabled={!item.enabled || Boolean(currentDoc)}
                  title={
                    !item.enabled
                      ? "Fluxo ainda não habilitado neste estúdio. Consulte a disponibilidade de serviços ao lado."
                      : undefined
                  }
                  className={brief.adPath === item.id ? "is-selected" : ""}
                  aria-pressed={brief.adPath === item.id}
                  onClick={() =>
                    change("adPath", item.id as VideoBrief["adPath"])
                  }
                >
                  <item.icon size={21} />
                  <strong>{item.title}</strong>
                  <small>{item.text}</small>
                  {!item.enabled && <span>Não habilitado</span>}
                </button>
              ))}
            </div>
            </details>
          ) : area === "ai" ? (
            <details className="vs-disclosure vs-start-options"><summary>Tipo de vídeo · {VIDEO_KINDS.find(kind => kind.id === brief.kind)?.name}</summary>
            <div className="vs-kind-cards">
              {VIDEO_KINDS.map((kind, index) => (
                <button
                  key={kind.id}
                  className={brief.kind === kind.id ? "is-selected" : ""}
                  disabled={Boolean(currentDoc)}
                  aria-pressed={brief.kind === kind.id}
                  onClick={() => change("kind", kind.id)}
                >
                  <span className={`vs-kind-art vs-kind-art-${index}`}>
                    <span />
                    <span />
                    <span />
                  </span>
                  <strong>{kind.name}</strong>
                  <small>{kind.description}</small>
                </button>
              ))}
            </div>
            </details>
          ) : (
            <MotionTools
              studio={studio}
              locked={locked}
              run={run}
              apply={apply}
              engine={engine}
              onCreate={() => void run(() => saveProject(true))}
              hasProject={Boolean(currentDoc)}
            />
          )}
          <div className="vs-form-panel">
            <div className="vs-panel-heading">
              <h3>
                {area === "ad"
                  ? "Briefing do anúncio"
                  : area === "motion"
                    ? "Projeto da composição"
                    : "Direção do vídeo"}
              </h3>
              <span className="vs-muted">
                {currentDoc
                  ? "Mesmo projeto · sem duplicação"
                  : "Comece pelo essencial"}
              </span>
            </div>
            <fieldset className="vs-fields vs-progressive-fields" disabled={busy || studio.busy}>
              {area === 'ad' && <>
                <label className="vs-full">O que será divulgado?<input value={brief.offer} maxLength={2000} onChange={event => change('offer',event.target.value)} placeholder="Produto, serviço ou oferta"/></label>
                <label className="vs-full">Para quem?<input value={brief.audience} maxLength={2000} onChange={event => change('audience',event.target.value)} placeholder="Descreva seu público"/></label>
              </>}
              <label className="vs-full">{area === 'ad' ? 'Qual resultado deseja alcançar?' : 'Descreva sua ideia'}
                <textarea rows={4} value={brief.objective} maxLength={1000} onChange={event => change('objective',event.target.value)} placeholder={area === 'ad' ? 'Ex.: apresentar a oferta e levar pessoas ao site.' : 'O que você quer mostrar neste vídeo?'}/>
              </label>
              <details className="studio-fold vs-full"><summary>Direção e roteiro · opções</summary>
                <div className="vs-fields">
                  <label>Nome do projeto<input value={videoBriefDefaults(brief,area==='ad').title} maxLength={180} onChange={event => change('title',event.target.value)}/></label>
                  {area !== 'ad' && <label>Público-alvo<input value={videoBriefDefaults(brief).audience} maxLength={2000} onChange={event => change('audience',event.target.value)}/></label>}
                  <label>Estilo / tom<input value={brief.style} maxLength={1000} onChange={event => change('style',event.target.value)}/></label>
                  {area === 'ad' && <>
                    <label>Benefício principal<input value={brief.benefit} maxLength={1000} onChange={event => change('benefit',event.target.value)}/></label>
                    <label className="vs-full">Chamada para ação<input value={brief.cta} maxLength={500} onChange={event => change('cta',event.target.value)}/></label>
                  </>}
                  <label className="vs-full">Roteiro / mensagem<textarea rows={3} value={brief.script} maxLength={1000} onChange={event => change('script',event.target.value)} placeholder="Abertura, mensagem e fechamento. Opcional."/></label>
                </div>
                <p className="vs-fine">Nome sugerido a partir da ideia. {area !== 'ad' ? 'Público geral por padrão; você pode alterar.' : 'Público e oferta são definidos por você.'} Nenhuma chamada de IA é feita para preencher estes campos.</p>
              </details>
            </fieldset>
            <div className="vs-form-footer">
              <span>
                O briefing é salvo no projeto. A montagem com IA usa as
                ferramentas reais do editor.
              </span>
              <button
                className="vs-primary"
                disabled={busy || studio.busy || data.status !== "ready"}
                onClick={() =>
                  void run(async () => {
                    await saveProject(area === "motion");
                    setArea("editor");
                  })
                }
              >
                {currentDoc ? "Salvar e abrir editor" : "Criar e abrir editor"} <ArrowRight size={16} />
              </button>
            </div>
          </div>
          {!currentDoc && !showProjects && (
            <button className="vs-resume" onClick={() => setShowProjects(true)}>
              <FolderOpen size={19} />
              <span>
                <strong>Continue de onde parou</strong>
                <small>
                  {loading
                    ? "Carregando projetos…"
                    : `${projects.length} projeto${projects.length === 1 ? "" : "s"} neste ambiente`}
                </small>
              </span>
              <ArrowRight size={17} />
            </button>
          )}
        </main>
        <aside className="vs-create-sidebar">
          <div className="vs-panel">
            <div className="vs-panel-heading">
              <h3>Formato de produção</h3>
              <Film size={16} />
            </div>
            <fieldset
              disabled={Boolean(currentDoc || creationAttempt.current) || busy}
            >
              <ClickoSelectMenu
                label="Proporção"
                value={brief.aspect}
                options={[
                  ["9:16", "9:16 · Vertical"],
                  ["16:9", "16:9 · Horizontal"],
                  ["1:1", "1:1 · Quadrado"],
                ]}
                onChange={(value) =>
                  change("aspect", value as VideoBrief["aspect"])
                }
              />
              <label>
                Duração planejada <span className="vs-muted">segundos</span>
                <input
                  type="number"
                  min={1}
                  max={600}
                  value={brief.duration}
                  onChange={(event) =>
                    change("duration", Number(event.target.value))
                  }
                />
              </label>
              <ClickoSelectMenu
                label="Idioma do roteiro"
                value={brief.locale}
                options={[
                  ["pt-BR", "Português (Brasil)"],
                  ["en-US", "English (US)"],
                  ["es", "Español"],
                ]}
                onChange={(value) => change("locale", value)}
              />
            </fieldset>
            <p className="vs-fine">
              {currentDoc
                ? "Formato reservado no projeto. Mudanças na sequência usam as ferramentas do motor."
                : `${dimensions(brief.aspect).join(" × ")} px · 30 fps. Duração planejada, não estimativa de processamento.`}
            </p>
            <div className="vs-narration">
              <AudioLines size={16} />
              <div>
                <strong>Narração e música</strong>
                <small>
                  Envie arquivos de áudio. Síntese de voz depende de provedor
                  habilitado.
                </small>
              </div>
            </div>
          </div>
          <div className="vs-panel">{assetPicker}</div>
          <details
            id="video-service-requirements"
            ref={servicesRef}
            className="vs-panel vs-services vs-disclosure"
            open={servicesOpen}
            onToggle={(event) => setServicesOpen(event.currentTarget.open)}
          >
            <summary>
              <span>
                Disponibilidade de serviços
                <small>O que está conectado neste ambiente</small>
              </span>
            </summary>
            <div className="vs-disclosure-body">
              <Service
                label="Edição e renderização"
                ready={currentDoc?.nativeEditorState ? Boolean(studio.engineInfo?.available) : Boolean(cpuRenderer?.available)}
                text={
                  !currentDoc?.nativeEditorState && cpuRenderer?.available ? "Edição pela timeline e exportação MP4 disponíveis" : studio.engineInfo?.available
                    ? "Motor conectado"
                    : "Motor nativo não configurado"
                }
              />
              <Service
                label="Vídeo generativo"
                ready={scene?.state === "qualified" && scene.serviceAccessible}
                text={
                  scene
                    ? `${scene.state === "qualified" ? "Qualificado" : scene.state === "experimental" ? "Experimental" : "Indisponível"} · requer plano de cenas`
                    : "Não verificado"
                }
              />
              <Service
                label="Apresentador / avatar"
                ready={
                  capabilities?.capabilities.find(
                    (item) => item.capability === "avatar",
                  )?.status === "ready"
                }
                text={
                  capabilities?.capabilities.find(
                    (item) => item.capability === "avatar",
                  )?.status === "ready"
                    ? "Provedor apto · fluxo não habilitado aqui"
                    : "Exige provedor, identidade e consentimento"
                }
              />
              <p className="vs-fine">
                Nenhuma estimativa de consumo disponível. Não iniciamos serviços
                pagos automaticamente.
              </p>
              <button
                className="vs-text-button"
                onClick={() => {
                  setReload((value) => value + 1);
                  studio.refresh();
                }}
              >
                <RefreshCw size={13} /> Verificar novamente
              </button>
            </div>
          </details>
        </aside>
      </div>
      {currentDoc && !currentDoc.nativeEditorState && currentDoc.composition.mediaTimeline && data.bootstrap ?
        <CanonicalVideoEditor key={currentDoc.documentId} doc={currentDoc} assets={assets} visible={area === "editor" || area === "motion"}
          projectActions={<button type="button" onClick={() => setShowProjects(value => !value)} aria-expanded={showProjects}><FolderOpen size={15}/>Projetos</button>}
          userId={data.bootstrap.user.id} onUpload={() => fileInput.current?.click()} onLibrary={() => void run(openLibrary)}
          onDocument={next => { setProject(next); setProjects(current => [next, ...current.filter(d => d.documentId !== next.documentId)]); }} /> : <div hidden={area !== "editor"}>
        <VideoEditor
          visible={area === "editor"}
          studio={studio}
          doc={currentDoc}
          assets={assets}
          selectedAsset={selectedAsset}
          onSelectAsset={setSelectedAsset}
          onUpload={() => fileInput.current?.click()}
          onLibrary={() => void run(openLibrary)}
          onCreate={() => setArea("ai")}
          locked={locked}
          run={run}
          apply={apply}
          outputUrl={
            outputIsVideo && studio.jobRevision === currentDoc?.revision
              ? outputUrl
              : undefined
          }
        />
      </div>}
      {(area === "ai" || area === "ad" || area === "editor") && Boolean(currentDoc?.nativeEditorState) && (
        <section className="vs-production">
          <div className="vs-ai-control">
            <div className="vs-panel-heading">
              <h3>
                <WandSparkles size={17} /> Montagem assistida por IA
              </h3>
              <span className="vs-ai-badge">KLIC · ferramentas do editor</span>
            </div>
            <p>
              Transforme a direção em ajustes no projeto aberto. Não gera
              filmagens, avatares ou voz a partir de texto.
            </p>
            <details className="vs-disclosure vs-model-options">
              <summary>
                <span>
                  Modelo e conexão de IA
                  <small>
                    {model.available
                      ? model.model || "Configuração do servidor disponível"
                      : "Selecione uma conexão habilitada para edição"}
                  </small>
                </span>
              </summary>
              <div className="vs-disclosure-body">
                {workspaceId && data.bootstrap && (
                  <CraftModelPicker
                    workspaceId={workspaceId}
                    userId={data.bootstrap.user.id}
                    disabled={busy || studio.busy}
                    onChange={setModel}
                  />
                )}
                <p className="vs-fine">
                  Reutiliza as conexões existentes, com limites e credenciais
                  gerenciados pelo servidor.
                </p>
              </div>
            </details>
            <label>
              Pedido de montagem
              <textarea
                rows={2}
                value={instruction}
                maxLength={4000}
                onChange={(event) => setInstruction(event.target.value)}
                placeholder="Ex.: organize a abertura, ajuste os cortes e adicione uma chamada final…"
              />
            </label>
            <button
              className="vs-ai-button"
              disabled={locked || !model.available}
              onClick={() => void run(applyDirection)}
            >
              <Sparkles size={16} /> Aplicar ao projeto
            </button>
            {!available && (
              <small>
                Salve o projeto e ative o motor de edição para aplicar a
                direção.
              </small>
            )}
          </div>
          <div className="vs-export-control">
            <h3>Finalização</h3>
            <p>
              Exporte a revisão salva, acompanhe a fila e baixe apenas
              resultados confirmados pelo servidor.
            </p>
            {formats.length > 0 && (
              <ClickoSelectMenu
                label="Formato de saída"
                value={exportFormat}
                options={formats.map((format) => [
                  format,
                  format.toUpperCase(),
                ])}
                onChange={setExportFormat}
              />
            )}
            <button
              className="vs-primary"
              disabled={
                locked ||
                !exportFormat ||
                Boolean(
                  studio.job &&
                  !["succeeded", "failed", "cancelled"].includes(
                    studio.job.status,
                  ),
                )
              }
              onClick={() =>
                void run(() => studio.exportProject(exportFormat, 0))
              }
            >
              <Clapperboard size={16} /> Exportar produção
            </button>
            {!studio.engineInfo?.available && (
              <small>
                A exportação requer o runtime nativo do motor e os codecs de
                saída.
              </small>
            )}
            {outputUrl && (
              <a
                className="vs-download"
                href={outputUrl}
                download={`clicko-${currentDoc?.documentId}.${String((studio.job?.request?.output as { format?: string } | undefined)?.format || exportFormat)}`}
              >
                Baixar revisão {studio.jobRevision} <ArrowRight size={14} />
              </a>
            )}
          </div>
        </section>
      )}
      {currentDoc?.nativeEditorState && (
        <VideoProjectTools
          key={currentDoc.documentId}
          studio={studio}
          doc={currentDoc}
          locked={locked}
          run={run}
          onApprovals={onApprovals}
          onOpenProject={openProject}
          draftDirty={dirty}
        />
      )}
      {studio.job && (
        <JobStatus
          job={studio.job}
          onCancel={() => void run(studio.cancelJob)}
          onRetry={() =>
            void run(async () => {
              await productApi.retryStudioGenerationJob(studio.job!.id);
              studio.refresh();
            })
          }
        />
      )}
      <input
        ref={fileInput}
        type="file"
        hidden
        multiple
        accept="video/*,image/*,audio/*"
        onChange={(event) => {
          void upload(event.target.files);
          event.target.value = "";
        }}
      />
    </section>
  );
}
function Service({
  label,
  text,
  ready,
}: {
  label: string;
  text: string;
  ready: boolean;
}) {
  return (
    <div className="vs-service">
      <span className={ready ? "is-ready" : ""} />
      <div>
        <strong>{label}</strong>
        <small>{text}</small>
      </div>
    </div>
  );
}
function JobStatus({
  job,
  onCancel,
  onRetry,
}: {
  job: StudioGenerationJobRecord;
  onCancel: () => void;
  onRetry: () => void;
}) {
  const active = !["succeeded", "failed", "cancelled"].includes(job.status);
  return (
    <div className="vs-job" role="status">
      <div>
        <strong>{JOB_LABELS[job.status]}</strong>
        <span>
          {job.jobType === "craft_render"
            ? "Exportação do projeto"
            : job.jobType}
        </span>
        <progress max={100} value={jobProgress(job)} />
      </div>
      <span>{jobProgress(job)}%</span>
      {active && (
        <button disabled={job.status === "cancel_requested"} onClick={onCancel}>
          Cancelar
        </button>
      )}
      {job.status === "failed" && job.attempts < job.maxAttempts && (
        <button onClick={onRetry}>Tentar novamente</button>
      )}
      {job.errorMessage && <p>{job.errorMessage}</p>}
    </div>
  );
}
function MotionTools({
  studio,
  engine,
  locked,
  run,
  apply,
  onCreate,
  hasProject,
}: {
  studio: VideoController;
  engine: string;
  locked: boolean;
  run: (task: () => Promise<unknown>) => Promise<void>;
  apply: (command: CraftCommand) => Promise<void>;
  onCreate: () => void;
  hasProject: boolean;
}) {
  const [selected, setSelected] = React.useState("title");
  const [text, setText] = React.useState("Sua próxima grande ideia.");
  const [color, setColor] = React.useState("#FF7F50");
  const [size, setSize] = React.useState(72);
  const [montage, setMontage] = React.useState("");
  const commands = craftCommands(studio.inspection);
  const templateAvailable = [
    "layer.newText",
    "engine.batch",
    "prop.addKey",
  ].every((id) => commands.some((command) => command.id === id));
  return (
    <div className="vs-motion-panel">
      <div className="vs-motion-cards">
        {[
          {
            id: "title",
            title: "Título de abertura",
            text: "Uma mensagem em destaque.",
          },
          {
            id: "lower",
            title: "Identificação",
            text: "Nome, cargo ou chamada.",
          },
          {
            id: "cta",
            title: "Chamada final",
            text: "Encerre com uma ação clara.",
          },
        ].map((item) => (
          <button
            key={item.id}
            className={selected === item.id ? "is-selected" : ""}
            aria-pressed={selected === item.id}
            onClick={() => setSelected(item.id)}
          >
            <span className={`vs-motion-art vs-motion-${item.id}`}>
              <span>Aa</span>
              <i />
            </span>
            <strong>{item.title}</strong>
            <small>{item.text}</small>
          </button>
        ))}
      </div>
      <div className="vs-fields">
        <label className="vs-full">
          Texto da composição
          <input
            value={text}
            maxLength={500}
            onChange={(event) => setText(event.target.value)}
          />
        </label>
        <label>
          Cor
          <input
            type="color"
            value={color}
            onChange={(event) => setColor(event.target.value)}
          />
        </label>
        <label>
          Tamanho do texto
          <input
            type="number"
            min={12}
            max={300}
            value={size}
            onChange={(event) => setSize(Number(event.target.value))}
          />
        </label>
      </div>
      <p className="vs-fine">
        Títulos com entrada e saída por opacidade, salvos como keyframes
        nativos. A personalização avançada fica no inspetor do editor. A prévia
        e a exportação dependem do motor de efeitos.
      </p>
      {!hasProject ? (
        <button className="vs-primary" onClick={onCreate}>
          Salvar projeto de composição <Plus size={15} />
        </button>
      ) : engine !== "effectcraft" ? (
        <div className="vs-banner">
          Este projeto é uma montagem de vídeo. Abra um projeto de composição em
          Projetos ou crie um novo; eles podem ser vinculados sem duplicar a
          montagem.
        </div>
      ) : (
        <button
          className="vs-primary"
          disabled={
            locked ||
            !templateAvailable ||
            !text.trim() ||
            !Number.isFinite(size) ||
            size < 12 ||
            size > 300
          }
          onClick={() =>
            void run(() =>
              apply(
                motionTitleCommand({
                  preset: selected as "title" | "lower" | "cta",
                  text,
                  color,
                  size,
                  width: Number(studio.inspection?.project.width) || 1080,
                  height: Number(studio.inspection?.project.height) || 1920,
                  duration: Math.max(
                    1,
                    (Number(studio.inspection?.project.durationMs) || 5000) /
                      1000,
                  ),
                }),
              ),
            )
          }
        >
          Adicionar título animado <Plus size={15} />
        </button>
      )}
      {hasProject && engine === "effectcraft" && (
        <div className="vs-link-composition">
          <ClickoSelectMenu
            label="Usar composição em uma montagem"
            value={montage}
            options={[
              ["", "Selecione um projeto de vídeo"],
              ...studio.documents
                .filter((doc) => doc.nativeEditorState?.engine === "filmcraft")
                .map((doc) => [doc.documentId, doc.title]),
            ]}
            onChange={setMontage}
          />
          <button
            disabled={locked || !montage}
            onClick={() =>
              void run(async () => {
                await studio.save();
                const target = await productApi.studioDocument(montage);
                await craftApi.linkComposition(
                  target.documentId,
                  target.revision,
                  studio.document!.documentId,
                  crypto.randomUUID(),
                );
              })
            }
          >
            Vincular à montagem <ArrowRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
