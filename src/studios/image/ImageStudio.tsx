import React from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Download,
  FolderOpen,
  History,
  Image as ImageIcon,
  Layers3,
  LoaderCircle,
  Maximize2,
  Plus,
  RefreshCw,
  Save,
  SlidersHorizontal,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import {
  productApi,
  type AssetRecord,
  type StudioDocumentCreate,
  type StudioGenerationJobRecord,
} from "../../api/productApi";
import { APIError } from "../../api";
import { ClickoSelectMenu } from "../../components/ClickoSelectMenu";
import { useProductData } from "../../context/ProductDataContext";
import { useKlicClient } from "../../klic/useKlicClient";
import { klicPageScope, useKlicPageDetails } from "../../klic/pageContext";
import type { NavigationTab } from "../../types";
import { craftApi, type CraftDocument } from "../craft/craftApi";
import { craftError } from "../craft/useCraftStudio";
import { verifyEditorialBlob } from "../editorialReview";
import { imageApi, type ImageAIStatus, type ImageUsage } from "./imageApi";
import {
  IMAGE_FORMATS,
  IMAGE_PURPOSES,
  IMAGE_STYLES,
  authorizeImageInputs,
  imageDocumentInput,
  imageDraftError,
  imageDraftFromDocument,
  imageJobInput,
  imageJobOperation,
  imageResultId,
  imageSourceReferences,
  imageUploadError,
  initialImageDraft,
  readPendingImageRequest,
  requiresImageReview,
  updateImageBrief,
  type ImageDraft,
  type ImageMode,
  type PendingImageRequest,
} from "./imageModel";
import "./image-studio.css";
import { matchesStudioDraft, readStudioSession, writeStudioSession } from '../studioSession';

type ImageEntry = 'create' | 'edit' | 'advertising' | 'composition' | 'editorial';
type ImageNavigationState = { draft: ImageDraft; doc?: CraftDocument; sourceId?: string; references: string[]; assets: AssetRecord[]; job?: StudioGenerationJobRecord; dirty: boolean };

const CraftStudio = React.lazy(() =>
  import("../craft/CraftStudio").then((module) => ({
    default: module.CraftStudio,
  })),
);
const DepartmentStudio = React.lazy(() =>
  import("../department/DepartmentStudio").then((module) => ({
    default: module.DepartmentStudio,
  })),
);
const labels: Record<string, string> = {
  queued: "Na fila",
  running: "Processando imagem",
  retrying: "Nova tentativa em andamento",
  cancel_requested: "Cancelamento solicitado",
  cancelled: "Cancelado",
  succeeded: "Resultado recebido",
  failed: "Não foi possível concluir",
};
const terminal = (job?: StudioGenerationJobRecord) =>
  !job || ["succeeded", "failed", "cancelled"].includes(job.status);

export function ImageStudio(props: {
  initialBrief?: { title: string; objective: string };
  onNavigate: (tab: NavigationTab) => void;
  embedded?: boolean;
  requestedEntry?: ImageEntry;
  onModeChange?: (mode: ImageMode) => void;
  onEditorial?: () => void;
}) {
  const data = useProductData();
  if (!data.activeWorkspace || !data.bootstrap || data.status !== "ready")
    return (
      <section className="is-root">
        <div className="is-access" role={data.error ? "alert" : "status"}>
          <ImageIcon size={30} />
          <h1>Estúdio de imagens</h1>
          <p>
            {data.error ||
              (data.status === "guest"
                ? "Entre na sua conta para acessar suas criações."
                : "Carregando seu ambiente de criação…")}
          </p>
          {data.error && (
            <button onClick={() => void data.refresh()}>
              Tentar novamente
            </button>
          )}
        </div>
      </section>
    );
  // Account/client changes unmount requests, private URLs and all editable state.
  return (
    <ImageRoom
      key={`${data.bootstrap.user.id}:${data.activeWorkspace.id}`}
      {...props}
      workspaceId={data.activeWorkspace.id}
      userId={data.bootstrap.user.id}
    />
  );
}

function ImageRoom({
  initialBrief,
  onNavigate,
  workspaceId,
  userId,
  embedded,
  requestedEntry,
  onModeChange,
  onEditorial,
}: {
  initialBrief?: { title: string; objective: string };
  onNavigate: (tab: NavigationTab) => void;
  workspaceId: string;
  userId: string;
  embedded?: boolean;
  requestedEntry?: ImageEntry;
  onModeChange?: (mode: ImageMode) => void;
  onEditorial?: () => void;
}) {
  const data = useProductData();
  const klic = useKlicClient();
  const sessionKey = JSON.stringify(['image', userId, workspaceId]);
  const [restored] = React.useState(() => readStudioSession<ImageNavigationState>(sessionKey));
  const recovered = restored && matchesStudioDraft(restored.draft, initialImageDraft()) && Array.isArray(restored.assets) && Array.isArray(restored.references) && (!restored.doc || restored.doc.workspaceId === workspaceId) ? restored : undefined;
  const [mode, updateMode] = React.useState<ImageMode>(requestedEntry === 'edit' ? 'edit' : 'create');
  const setMode = (next: ImageMode) => { updateMode(next); onModeChange?.(next); };
  const [draft, setDraft] = React.useState(() =>
    recovered?.draft || { ...initialImageDraft(initialBrief), ...(requestedEntry === 'advertising' ? { purpose:'Anúncio' } : {}) },
  );
  const [doc, setDoc] = React.useState<CraftDocument | undefined>(recovered?.doc);
  const docRef = React.useRef(doc);
  docRef.current = doc;
  const [documents, setDocuments] = React.useState<CraftDocument[]>([]);
  const [jobs, setJobs] = React.useState<StudioGenerationJobRecord[]>([]);
  const [job, setJob] = React.useState<StudioGenerationJobRecord | undefined>(recovered?.job);
  const [localAssets, setLocalAssets] = React.useState<AssetRecord[]>(recovered?.assets || []);
  const [sourceId, setSourceId] = React.useState<string | undefined>(recovered?.sourceId);
  const [references, setReferences] = React.useState<string[]>(recovered?.references || []);
  const [status, setStatus] = React.useState<ImageAIStatus>();
  const [model, setModel] = React.useState("");
  const [usage, setUsage] = React.useState<ImageUsage>();
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [dirty, setDirty] = React.useState(recovered?.dirty || false);
  const [error, setError] = React.useState<string>();
  const [catalogError, setCatalogError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [projectsOpen, setProjectsOpen] = React.useState(false);
  const [pickerOpen, setPickerOpen] = React.useState(false);
  const [pickerRole, setPickerRole] = React.useState<"source" | "reference">(
    "reference",
  );
  const [query, setQuery] = React.useState("");
  const [usageEvidence, setUsageEvidence] = React.useState("");
  const [authorized, setAuthorized] = React.useState(false);
  const [suggestion, setSuggestion] = React.useState("");
  const [reviewNotes, setReviewNotes] = React.useState("");
  const [reviewConfirmed, setReviewConfirmed] = React.useState(false);
  const [view, setView] = React.useState<"studio" | "native" | "editorial">(
    "studio",
  );
  const [nativeSearch, setNativeSearch] = React.useState("");
  const [refresh, setRefresh] = React.useState(0);
  const recoveryKey = `clicko:image-job:v1:${JSON.stringify([userId, workspaceId])}`;
  const [pending, setPending] = React.useState(() => {
    try {
      return readPendingImageRequest(localStorage.getItem(recoveryKey));
    } catch {
      return undefined;
    }
  });
  const pendingRef = React.useRef(pending);
  pendingRef.current = pending;
  const creationRef = React.useRef<StudioDocumentCreate | undefined>(undefined);
  const action = React.useRef(false);
  const alive = React.useRef(true);
  const draftVersion = React.useRef(0);
  const inputRef = React.useRef<HTMLInputElement>(null);
  React.useEffect(() => {
    if (!requestedEntry) return;
    updateMode(requestedEntry === 'edit' ? 'edit' : 'create');
    setView(requestedEntry === 'editorial' ? 'editorial' : 'studio');
    if (requestedEntry === 'advertising') setDraft(current => !current.prompt && !current.title ? { ...current, purpose:'Anúncio' } : current);
  }, [requestedEntry]);
  React.useEffect(() => {
    writeStudioSession(sessionKey, { draft, doc, sourceId, references, assets:localAssets, job, dirty } satisfies ImageNavigationState);
  }, [sessionKey, draft, doc, sourceId, references, localAssets, job, dirty]);
  React.useEffect(() => {
    const beforeLeave = (event: Event) => {
      if (action.current || busy || pendingRef.current) { event.preventDefault(); setNotice('Aguarde a confirmação do pedido antes de trocar de módulo.'); }
    };
    window.addEventListener('clicko:studio-before-leave', beforeLeave);
    return () => window.removeEventListener('clicko:studio-before-leave', beforeLeave);
  }, [busy]);
  const assets = [...localAssets, ...(data.snapshot?.assets || [])].filter(
    (asset, index, all) =>
      asset.mediaType?.startsWith("image/") &&
      all.findIndex((item) => item.id === asset.id) === index,
  );
  const source = assets.find((asset) => asset.id === sourceId);
  const outputId = imageResultId(job);
  const result = assets.find((asset) => asset.id === outputId);
  const originalId = (
    job?.request?.input as { sourceAssetId?: string } | undefined
  )?.sourceAssetId;
  const original = assets.find((asset) => asset.id === originalId);
  const sourcePreview = useImageUrl(source);
  const resultPreview = useImageUrl(result);
  const originalPreview = useImageUrl(original);
  const activeJob = !terminal(job);
  const locked = busy || activeJob || Boolean(pending);
  const operation = mode === "edit" ? "edit_image" : "generate_image";
  const ready =
    status?.stages?.[operation]?.configured === true &&
    status.operations.includes(operation);
  const brand = klic.snapshot.records.brand?.[0];
  const brandContext = brand
    ? JSON.stringify({
        name: brand.name,
        visualIdentity: brand.visualIdentity,
        brandColors: brand.brandColors,
        typography: brand.typography,
        visualReferences: brand.visualReferences,
      }).slice(0, 4000)
    : "";
  useKlicPageDetails(
    "create-image",
    klicPageScope(klic.workspaceId, klic.clientId),
    {
      view:
        view === "studio"
          ? mode === "edit"
            ? "Editar imagem"
            : "Criar imagem"
          : view,
      selected: doc
        ? { kind: "projeto de imagem", id: doc.documentId }
        : source
          ? { kind: "imagem", id: source.id }
          : undefined,
    },
  );
  React.useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  React.useEffect(() => {
    const leave = (event: BeforeUnloadEvent) => {
      if (dirty || action.current || pendingRef.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", leave);
    return () => window.removeEventListener("beforeunload", leave);
  }, [dirty]);
  React.useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setCatalogError(undefined);
    void Promise.allSettled([
      productApi.studioDocuments(workspaceId),
      productApi.studioGenerationJobs(workspaceId, { limit: 100 }),
      imageApi.status(controller.signal),
      imageApi.models(controller.signal),
      imageApi.usage(workspaceId, controller.signal),
    ]).then(([docs, history, services, models, consumption]) => {
      if (controller.signal.aborted) return;
      if (docs.status === "fulfilled")
        setDocuments(
          (docs.value as CraftDocument[]).filter((item) =>
            ["visual", "carousel"].includes(item.contentType),
          ),
        );
      else setCatalogError(craftError(docs.reason));
      if (history.status === "fulfilled")
        setJobs(
          history.value.filter((item) => Boolean(imageJobOperation(item))),
        );
      else setCatalogError(craftError(history.reason));
      if (services.status === "fulfilled") setStatus(services.value);
      else {
        setStatus(undefined);
        setNotice(
          "Não foi possível conferir o provedor. A geração permanece bloqueada até a confirmação do serviço.",
        );
      }
      if (models.status === "fulfilled") setModel(models.value.models.image);
      if (consumption.status === "fulfilled") setUsage(consumption.value);
      setLoading(false);
    });
    return () => controller.abort();
  }, [workspaceId, refresh]);
  React.useEffect(() => {
    if (!job || terminal(job)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void productApi
        .studioGenerationJob(job.id)
        .then((next) => {
          if (!controller.signal.aborted) {
            setJob(next);
            setJobs((current) => [
              next,
              ...current.filter((item) => item.id !== next.id),
            ]);
          }
        })
        .catch((cause) => {
          if (!controller.signal.aborted)
            setError(
              `${craftError(cause)} Use Atualizar para conferir o processamento antes de iniciar outro pedido.`,
            );
        });
    }, 2000);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [job, refresh]);
  React.useEffect(() => {
    if (!outputId) return;
    let active = true;
    void craftApi
      .assetDetails(outputId)
      .then((asset) => {
        if (active)
          setLocalAssets((current) => [
            asset,
            ...current.filter((item) => item.id !== asset.id),
          ]);
      })
      .catch((cause) => {
        if (active) setError(craftError(cause));
      });
    return () => {
      active = false;
    };
  }, [outputId, refresh]);
  React.useEffect(() => {
    setReviewNotes("");
    setReviewConfirmed(false);
  }, [outputId]);

  function change<K extends keyof ImageDraft>(key: K, value: ImageDraft[K]) {
    draftVersion.current++;
    setDraft((current) => ({ ...current, [key]: value }));
    setDirty(true);
    setSuggestion("");
  }
  async function run(task: () => Promise<unknown>) {
    if (action.current) return;
    action.current = true;
    setBusy(true);
    setError(undefined);
    setNotice(undefined);
    try {
      await task();
    } catch (cause) {
      if (alive.current) setError(imageError(cause));
    } finally {
      action.current = false;
      if (alive.current) setBusy(false);
    }
  }
  function remember(next: CraftDocument) {
    if (!alive.current) return;
    docRef.current = next;
    setDoc(next);
    setDocuments((current) => [
      next,
      ...current.filter((item) => item.documentId !== next.documentId),
    ]);
  }
  function rememberJob(next: StudioGenerationJobRecord) {
    if (!alive.current) return;
    setJob(next);
    setJobs((current) => [
      next,
      ...current.filter((item) => item.id !== next.id),
    ]);
  }
  async function saveDraft(value = draft) {
    if (!alive.current)
      throw new DOMException("O contexto de criação mudou.", "AbortError");
    const validation = imageDraftError(value);
    if (validation) throw new Error(validation);
    const version = draftVersion.current;
    let next: CraftDocument;
    const active = docRef.current;
    if (active)
      next =
        dirty || value !== draft
          ? await productApi.replaceStudioDocument(
              active.documentId,
              active.revision,
              {
                ...updateImageBrief(active, value),
                assets: imageSourceReferences(
                  active.assets,
                  sourceId,
                  references,
                  assets,
                ),
              },
            )
          : active;
    else if (creationRef.current) {
      const existing = await productApi.studioDocuments(workspaceId);
      if (!alive.current)
        throw new DOMException("O contexto de criação mudou.", "AbortError");
      const recovered = existing.find(
        (item) => item.correlationId === creationRef.current?.correlationId,
      ) as CraftDocument | undefined;
      if (!recovered)
        throw new Error(
          "A criação anterior ainda não foi confirmada. Confira Projetos antes de iniciar outro pedido.",
        );
      next = await productApi.replaceStudioDocument(
        recovered.documentId,
        recovered.revision,
        {
          ...updateImageBrief(recovered, value),
          assets: imageSourceReferences(
            recovered.assets,
            sourceId,
            references,
            assets,
          ),
        },
      );
    } else {
      creationRef.current = imageDocumentInput(workspaceId, value);
      creationRef.current.assets = imageSourceReferences(
        [],
        sourceId,
        references,
        assets,
      );
      try {
        next = await productApi.createStudioDocument(creationRef.current);
      } catch (cause) {
        if (
          cause instanceof APIError &&
          cause.status >= 400 &&
          cause.status < 500 &&
          cause.status !== 408
        )
          creationRef.current = undefined;
        throw cause;
      }
    }
    creationRef.current = undefined;
    remember(next);
    if (alive.current && draftVersion.current === version) setDirty(false);
    return next;
  }
  function clearPending() {
    try {
      localStorage.removeItem(recoveryKey);
    } catch {
      setNotice(
        "O pedido foi confirmado, mas a cópia de recuperação não pôde ser removida deste navegador.",
      );
    }
    pendingRef.current = undefined;
    setPending(undefined);
  }
  async function submit(request: PendingImageRequest) {
    if (!alive.current) return;
    try {
      const confirmed = await imageApi.generate(
        request.documentId,
        request.input,
        request.key,
      );
      if (alive.current) {
        rememberJob(confirmed);
        clearPending();
        setNotice(
          "Solicitação registrada. O resultado aparecerá após a confirmação do processamento.",
        );
      }
    } catch (cause) {
      if (
        cause instanceof APIError &&
        cause.status >= 400 &&
        cause.status < 500 &&
        cause.status !== 408 &&
        alive.current
      )
        clearPending();
      throw cause;
    }
  }
  async function generate() {
    if (pendingRef.current)
      throw new Error(
        "Verifique o pedido pendente antes de iniciar outra geração.",
      );
    if (!ready)
      throw new Error("O provedor não confirmou suporte para esta operação.");
    const inputs = [
      ...new Set([
        ...(mode === "edit" && sourceId ? [sourceId] : []),
        ...references,
      ]),
    ];
    if (mode === "edit" && !source)
      throw new Error("Escolha uma imagem para editar.");
    if (
      inputs.some((id) => {
        const item = assets.find((asset) => asset.id === id);
        return !item?.checksumSha256 || requiresImageReview(item);
      })
    )
      throw new Error(
        "Confira o arquivo e aprove a revisão visual dos materiais gerados antes de reutilizá-los.",
      );
    if (inputs.length && (!authorized || usageEvidence.trim().length < 3))
      throw new Error(
        "Informe a autorização de uso e confirme o envio das imagens ao provedor.",
      );
    let active = await saveDraft();
    if (!alive.current) return;
    const inputAssets = authorizeImageInputs(
      active.assets,
      inputs,
      assets,
      authorized,
      usageEvidence,
      userId,
    );
    if (inputAssets !== active.assets) {
      const next = { ...active, assets: inputAssets };
      active = await productApi.replaceStudioDocument(
        active.documentId,
        active.revision,
        next,
      );
      remember(active);
    }
    if (!alive.current) return;
    const input = imageJobInput(
      active,
      mode,
      draft,
      sourceId,
      references,
      brandContext,
    );
    const request = {
      documentId: active.documentId,
      input,
      key: crypto.randomUUID(),
    };
    // Do not send a potentially paid request unless its exact retry identity is durable.
    localStorage.setItem(recoveryKey, JSON.stringify(request));
    pendingRef.current = request;
    setPending(request);
    await submit(request);
  }
  async function openDocument(id: string) {
    if (
      dirty &&
      !window.confirm(
        "Abrir outro projeto? Os ajustes ainda não salvos neste formulário serão descartados.",
      )
    )
      return;
    const next = (await productApi.studioDocument(id)) as CraftDocument;
    if (
      next.workspaceId !== workspaceId ||
      !["visual", "carousel"].includes(next.contentType)
    )
      throw new Error(
        "Este projeto não pertence ao estúdio de imagens deste ambiente.",
      );
    remember(next);
    setDraft(imageDraftFromDocument(next));
    setDirty(false);
    setSuggestion("");
    const selectedSource = next.assets.find(
      (item) => item.provenance?.imageStudioRole === "source",
    )?.id;
    setSourceId(selectedSource);
    setReferences(
      next.assets
        .filter((item) => item.provenance?.imageStudioRole === "reference")
        .map((item) => item.id)
        .slice(0, 3),
    );
    setMode(selectedSource ? "edit" : "create");
    for (const ref of next.assets.filter(
      (item) => item.provenance?.imageStudioRole,
    ))
      if (!assets.some((asset) => asset.id === ref.id)) {
        const asset = await craftApi.assetDetails(ref.id);
        if (alive.current)
          setLocalAssets((current) => [
            asset,
            ...current.filter((item) => item.id !== asset.id),
          ]);
      }
    setAuthorized(false);
    setUsageEvidence("");
    setJob(undefined);
    setProjectsOpen(false);
  }
  async function openJob(next: StudioGenerationJobRecord) {
    if (next.documentId !== docRef.current?.documentId && next.documentId) {
      await openDocument(next.documentId);
      if (docRef.current?.documentId !== next.documentId) return;
    }
    rememberJob(next);
    const input = next.request?.input as
      { sourceAssetId?: string; referenceAssetIds?: string[] } | undefined;
    setMode(imageJobOperation(next) === "edit_image" ? "edit" : "create");
    setSourceId(input?.sourceAssetId);
    setReferences(input?.referenceAssetIds || []);
    for (const id of [
      ...new Set(
        [input?.sourceAssetId, ...(input?.referenceAssetIds || [])].filter(
          Boolean,
        ) as string[],
      ),
    ]) {
      if (!assets.some((asset) => asset.id === id)) {
        const asset = await craftApi.assetDetails(id);
        if (alive.current)
          setLocalAssets((current) => [
            asset,
            ...current.filter((item) => item.id !== id),
          ]);
      }
    }
    setProjectsOpen(false);
  }
  function selectAsset(asset: AssetRecord) {
    if (pickerRole === "source") {
      setSourceId(asset.id);
      setMode("edit");
      if (terminal(job)) setJob(undefined);
    } else if (references.includes(asset.id))
      setReferences((current) => current.filter((id) => id !== asset.id));
    else if (references.length >= 3) {
      setError("Use até 3 imagens de referência por solicitação.");
      return;
    } else setReferences((current) => [...current, asset.id]);
    setAuthorized(false);
    setDirty(true);
    setPickerOpen(false);
  }
  async function upload(file?: File) {
    if (!file) return;
    const invalid = imageUploadError(file);
    if (invalid) throw new Error(invalid);
    if (usageEvidence.trim().length < 3)
      throw new Error(
        "Descreva a autorização de uso antes de enviar a imagem.",
      );
    const asset = await imageApi.upload(
      workspaceId,
      file,
      usageEvidence.trim(),
    );
    if (!alive.current) return;
    setLocalAssets((current) => [
      asset,
      ...current.filter((item) => item.id !== asset.id),
    ]);
    selectAsset(asset);
    setNotice(
      "Imagem armazenada na Biblioteca deste ambiente. O original foi preservado.",
    );
  }
  async function suggest() {
    if (!draft.prompt.trim())
      throw new Error("Escreva sua ideia antes de pedir uma sugestão.");
    const reply = await klic.request<{ reply: string }>(
      "chat",
      "create-image",
      {
        message: `Ajude a aprimorar APENAS a descrição visual abaixo para ${mode === "edit" ? "editar uma imagem" : "criar uma imagem"}. Retorne somente uma sugestão de prompt em português, até 1000 caracteres, sem executar ações, sem prometer recursos, sem inventar detalhes da marca. Preserve a intenção do usuário.\nDescrição: ${draft.prompt}\nObjetivo: ${draft.purpose}\nEstilo: ${draft.style}`,
      },
    );
    if (!reply.reply?.trim())
      throw new Error(
        "A KLIC não retornou uma sugestão. Seu texto foi mantido.",
      );
    if (alive.current) setSuggestion(reply.reply.trim());
  }
  async function showNative() {
    if (pendingRef.current || activeJob)
      throw new Error(
        "Aguarde ou confira o pedido em andamento antes de abrir a edição avançada.",
      );
    const nativeDraft =
      draft.prompt.trim().length >= 8
        ? draft
        : {
            ...draft,
            title: draft.title || source?.title || "Nova composição",
            prompt: source
              ? `Edição da imagem ${source.title}.`
              : "Nova composição de imagem em branco.",
          };
    let active = await saveDraft(nativeDraft);
    if (!alive.current) return;
    if (alive.current && nativeDraft !== draft) setDraft(nativeDraft);
    if (result && !requiresImageReview(result)) {
      active = await imageApi.attach(
        active.documentId,
        active.revision,
        result.id,
      );
      remember(active);
    }
    setNativeSearch(
      `?mode=visual&document=${encodeURIComponent(active.documentId)}`,
    );
    setView("native");
  }
  async function returnToStudio() {
    const id =
      new URLSearchParams(nativeSearch).get("document") ||
      docRef.current?.documentId;
    if (id) {
      const next = (await productApi.studioDocument(id)) as CraftDocument;
      if (next.workspaceId !== workspaceId)
        throw new Error("Projeto fora do ambiente atual.");
      remember(next);
      setDraft(imageDraftFromDocument(next));
      setDirty(false);
      setSourceId(
        next.assets.find((item) => item.provenance?.imageStudioRole === "source")
          ?.id,
      );
      setReferences(
        next.assets
          .filter((item) => item.provenance?.imageStudioRole === "reference")
          .map((item) => item.id)
          .slice(0, 3),
      );
      if (job?.documentId !== id) setJob(undefined);
    }
    setRefresh((value) => value + 1);
    setView("studio");
    if (requestedEntry === 'editorial') onModeChange?.(mode);
  }
  const navigateNative = (url: string) => {
    const target = new URL(url, window.location.origin);
    if (target.pathname === "/studios/native") {
      setNativeSearch(target.search);
      setView("native");
    } else if (target.pathname.startsWith("/approvals"))
      onNavigate("approvals");
    else if (target.pathname.startsWith("/library")) onNavigate("library");
    else if (target.pathname === "/brand-memory") onNavigate("workspace");
    else void run(returnToStudio);
  };
  async function leaveForLibrary() {
    if (dirty) {
      if (!window.confirm("Salvar o briefing antes de abrir a Biblioteca?"))
        return;
      await saveDraft();
    }
    onNavigate("library");
  }
  function newDraft() {
    if (
      dirty &&
      !window.confirm(
        "Iniciar outra criação sem salvar os ajustes do formulário?",
      )
    )
      return;
    if (
      creationRef.current &&
      !window.confirm(
        "Uma criação anterior aguarda confirmação. Confira Projetos para evitar duplicação. Iniciar outro rascunho?",
      )
    )
      return;
    creationRef.current = undefined;
    docRef.current = undefined;
    setDoc(undefined);
    setDraft(initialImageDraft());
    setMode("create");
    setSourceId(undefined);
    setReferences([]);
    setJob(undefined);
    setDirty(false);
    setSuggestion("");
    setError(undefined);
    setNotice(undefined);
    setAuthorized(false);
  }
  const selectedAssets = assets.filter((asset) =>
    references.includes(asset.id),
  );
  const hasInputs = Boolean((sourceId && mode === "edit") || references.length);
  const previewUrl = result
    ? resultPreview.url
    : mode === "edit"
      ? sourcePreview.url
      : undefined;
  const previewError = result ? resultPreview.error : sourcePreview.error;
  const displayed = result || (mode === "edit" ? source : undefined);

  return (
    <section className="is-root" aria-label="Estúdio de imagens Clicko">
      <div hidden={view === "studio"} className="is-advanced-top">
        <button disabled={busy} onClick={() => void run(returnToStudio)}>
          <ArrowLeft size={16} /> Voltar ao estúdio de imagens
        </button>
        <small>
          Ferramentas existentes da Clicko · projeto e originais preservados
        </small>
      </div>
      {view === "native" && (
        <React.Suspense
          fallback={<p role="status">Carregando editor PhotoCraft…</p>}
        >
          <CraftStudio
            mode="visual"
            pathname="/studios/native"
            search={nativeSearch}
            navigate={navigateNative}
            returnTo="/image"
            sourceAssetId={result?.id || sourceId}
          />
        </React.Suspense>
      )}
      {view === "editorial" && (
        <React.Suspense
          fallback={<p role="status">Carregando produção editorial…</p>}
        >
          <DepartmentStudio
            mode="image"
            pathname="/image"
            search=""
            navigate={navigateNative}
            initialBrief={initialBrief}
          />
        </React.Suspense>
      )}
      <div hidden={view !== "studio"}>
        <header className="is-header">
          <div>
            <span className="is-eyebrow">CLICKO STUDIOS / IMAGENS</span>
            <h1>
              Crie com intenção.
              <br className="is-mobile-break" /> Edite com precisão.
            </h1>
            <p>Da primeira ideia ao último detalhe, no seu espaço criativo.</p>
          </div>
          <div className="is-header-actions">
            <button
              onClick={() => setProjectsOpen((value) => !value)}
              aria-expanded={projectsOpen}
            >
              <History size={16} /> Projetos e histórico
            </button>
            <button className="is-primary" disabled={locked} onClick={newDraft}>
              <Plus size={16} /> Nova criação
            </button>
          </div>
        </header>
        <div className="is-workspace-bar">
          <nav aria-label="Operação de imagem" hidden={embedded}>
            {(["create", "edit"] as const).map((item) => (
              <button
                key={item}
                disabled={locked}
                aria-pressed={mode === item}
                onClick={() => {
                  setMode(item);
                  if (item === "create" && sourceId) {
                    setSourceId(undefined);
                    setDirty(true);
                  }
                  setSuggestion("");
                }}
              >
                {item === "create" ? (
                  <Sparkles size={16} />
                ) : (
                  <SlidersHorizontal size={16} />
                )}
                {item === "create" ? "Criar imagem" : "Editar imagem"}
              </button>
            ))}
          </nav>
          <span>
            {doc
              ? `${doc.title} · revisão ${doc.revision}`
              : "Seu próximo projeto"}
            {dirty && <small>Alterações não salvas</small>}
          </span>
          <button
            className="is-text"
            disabled={locked}
            onClick={() =>
              void run(async () => {
                await saveDraft();
                setNotice(
                  "Briefing salvo. Salvar o projeto não inicia uma geração.",
                );
              })
            }
          >
            <Save size={15} /> Salvar briefing
          </button>
        </div>
        {(error || notice) && (
          <div
            className={`is-feedback ${error ? "is-error" : ""}`}
            role={error ? "alert" : "status"}
          >
            <span>{error || notice}</span>
            <button
              className="is-icon"
              aria-label="Fechar aviso"
              onClick={() => {
                setError(undefined);
                setNotice(undefined);
              }}
            >
              <X size={15} />
            </button>
          </div>
        )}
        {busy && (
          <div className="is-feedback" role="status">
            <LoaderCircle size={15} className="is-spin" /> Enviando solicitação.
            Aguarde a confirmação do serviço.
          </div>
        )}
        {pending && (
          <div className="is-feedback" role="status">
            <span>
              Um pedido ainda aguarda confirmação. A verificação reutiliza
              exatamente o mesmo identificador, sem gerar uma nova solicitação.
              Pode haver 1 unidade da cota reservada até essa confirmação.
            </span>
            <button
              disabled={busy}
              onClick={() => void run(() => submit(pending))}
            >
              Verificar pedido
            </button>
          </div>
        )}
        {projectsOpen && (
          <section className="is-history">
            <div className="is-section-title">
              <h2>Suas criações, preservadas</h2>
              <button
                className="is-icon"
                aria-label="Fechar histórico"
                onClick={() => setProjectsOpen(false)}
              >
                <X size={17} />
              </button>
            </div>
            {loading ? (
              <p role="status">Carregando projetos e solicitações…</p>
            ) : catalogError ? (
              <p role="alert">{catalogError}</p>
            ) : (
              <>
                <div className="is-project-list">
                  {documents.map((item) => (
                    <button
                      key={item.documentId}
                      disabled={locked}
                      onClick={() =>
                        void run(() => openDocument(item.documentId))
                      }
                    >
                      <FolderOpen size={20} />
                      <span>
                        <strong>{item.title}</strong>
                        <small>
                          {item.contentType === "carousel"
                            ? "Carrossel"
                            : "Imagem"}{" "}
                          ·{" "}
                          {new Date(item.updatedAt).toLocaleDateString("pt-BR")}{" "}
                          · revisão {item.revision}
                        </small>
                      </span>
                      <ArrowRight size={15} />
                    </button>
                  ))}
                </div>
                {!documents.length && (
                  <p>
                    Seus projetos salvos aparecerão aqui. Nenhum exemplo
                    substitui suas criações.
                  </p>
                )}
                <details className="is-details">
                  <summary>
                    Histórico de geração e edição{" "}
                    <span>{jobs.length} solicitações</span>
                  </summary>
                  <div className="is-job-list">
                    {jobs.map((item) => (
                      <button
                        disabled={locked}
                        key={item.id}
                        onClick={() => void run(() => openJob(item))}
                      >
                        <span>
                          <strong>
                            {imageJobOperation(item) === "edit_image"
                              ? "Edição de imagem"
                              : "Geração de imagem"}
                          </strong>
                          <small>
                            {new Date(item.createdAt).toLocaleString("pt-BR")} ·{" "}
                            {labels[item.status]}
                          </small>
                          <small className="is-truncate">
                            {String(
                              (item.request?.input as { prompt?: string })
                                ?.prompt || "",
                            )}
                          </small>
                        </span>
                        <ArrowRight size={15} />
                      </button>
                    ))}
                    {!jobs.length && (
                      <p>Nenhuma solicitação encontrada neste ambiente.</p>
                    )}
                  </div>
                </details>
              </>
            )}
            <div className="is-history-footer">
              <button
                disabled={busy}
                onClick={() => setRefresh((value) => value + 1)}
              >
                <RefreshCw size={14} /> Atualizar
              </button>
              <button
                disabled={locked || dirty}
                onClick={() => { setView("editorial"); onEditorial?.(); }}
              >
                Produção editorial e projetos anteriores{" "}
                <ArrowRight size={14} />
              </button>
            </div>
          </section>
        )}
        <div className="is-studio-grid">
          <main className="is-visual-panel">
            <div className="is-stage-heading">
              <div>
                <span className="is-eyebrow">
                  {result
                    ? "SUA CRIAÇÃO"
                    : mode === "edit"
                      ? "IMAGEM ORIGINAL"
                      : "ESPAÇO DE CRIAÇÃO"}
                </span>
                <h2>
                  {result
                    ? result.title
                    : source && mode === "edit"
                      ? source.title
                      : mode === "edit"
                        ? "Toda transformação tem um ponto de partida."
                        : "Sua próxima ideia ganha forma aqui."}
                </h2>
              </div>
              {previewUrl && (
                <button
                  className="is-icon"
                  aria-label="Ampliar imagem"
                  onClick={() =>
                    void run(async () => {
                      await document
                        .querySelector<HTMLElement>(".is-root .is-stage")
                        ?.requestFullscreen();
                    })
                  }
                >
                  <Maximize2 size={17} />
                </button>
              )}
            </div>
            <div className={`is-stage ${previewUrl ? "has-image" : ""}`}>
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt={
                    result
                      ? `Resultado recebido: ${result.title}`
                      : `Original preservado: ${source?.title}`
                  }
                />
              ) : (
                <div className="is-empty-stage">
                  <span className="is-empty-symbol">
                    <ImageIcon size={44} strokeWidth={1} />
                  </span>
                  <h3>
                    {activeJob
                      ? labels[job!.status]
                      : mode === "edit"
                        ? "Escolha a imagem que vamos trabalhar."
                        : "Uma ideia sua. Inúmeras possibilidades."}
                  </h3>
                  <p>
                    {activeJob
                      ? "Você acompanha o estado real do processamento abaixo. A imagem só aparece após a confirmação do servidor."
                      : mode === "edit"
                        ? "Envie uma imagem ou use um arquivo da Biblioteca. O original permanece intacto."
                        : "Descreva o que imagina no painel ao lado. A visualização será ocupada apenas por resultados reais."}
                  </p>
                  {mode === "edit" && !activeJob && (
                    <button
                      disabled={locked}
                      onClick={() => {
                        setPickerRole("source");
                        setPickerOpen(true);
                      }}
                    >
                      <FolderOpen size={15} /> Escolher imagem
                    </button>
                  )}
                </div>
              )}
              {(resultPreview.loading ||
                (!result && mode === "edit" && sourcePreview.loading)) && (
                <span className="is-image-loading" role="status">
                  <LoaderCircle className="is-spin" size={16} /> Conferindo
                  arquivo…
                </span>
              )}
            </div>
            {previewError && (
              <p className="is-inline-error" role="alert">
                {previewError}
              </p>
            )}
            {displayed && (
              <div className="is-result-actions">
                <span>
                  {result
                    ? "Resultado salvo na Biblioteca"
                    : "Original preservado"}
                  <small>
                    {displayed.mediaType}{" "}
                    {displayed.sizeBytes
                      ? `· ${(displayed.sizeBytes / 1024 / 1024).toFixed(1)} MB`
                      : ""}
                  </small>
                </span>
                {previewUrl && (
                  <a
                    href={previewUrl}
                    download={`${displayed.title}.${displayed.mediaType === "image/jpeg" ? "jpg" : displayed.mediaType === "image/webp" ? "webp" : "png"}`}
                  >
                    <Download size={15} /> Baixar arquivo
                  </a>
                )}
                <button
                  disabled={locked}
                  onClick={() => void run(leaveForLibrary)}
                >
                  Abrir Biblioteca <ArrowRight size={14} />
                </button>
              </div>
            )}
            {job && (
              <div className="is-processing" role="status">
                <div>
                  <strong>{labels[job.status]}</strong>
                  <small>
                    {imageJobOperation(job) === "edit_image"
                      ? "Edição com IA"
                      : "Geração com IA"}{" "}
                    ·{" "}
                    {String(
                      job.request?.model || model || "Modelo do servidor",
                    )}
                  </small>
                  {!terminal(job) && (
                    <progress
                      max={100}
                      value={Math.max(
                        0,
                        Math.min(100, Number(job.progress) || 0),
                      )}
                    />
                  )}
                </div>
                {!terminal(job) && (
                  <button
                    disabled={busy || job.status === "cancel_requested"}
                    onClick={() =>
                      void run(async () =>
                        rememberJob(
                          await productApi.cancelStudioGenerationJob(job.id),
                        ),
                      )
                    }
                  >
                    Cancelar
                  </button>
                )}
                {job.status === "failed" && job.attempts < job.maxAttempts && (
                  <button
                    disabled={busy || Boolean(pending)}
                    onClick={() =>
                      void run(async () =>
                        rememberJob(
                          await productApi.retryStudioGenerationJob(job.id),
                        ),
                      )
                    }
                  >
                    Tentar novamente
                  </button>
                )}
                <button
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      rememberJob(await productApi.studioGenerationJob(job.id));
                      setRefresh((value) => value + 1);
                    })
                  }
                >
                  <RefreshCw size={14} /> Atualizar
                </button>
                {job.errorMessage && (
                  <p>
                    {imageError(new Error(job.errorCode || job.errorMessage))}
                  </p>
                )}
              </div>
            )}
            {job?.status === "succeeded" && !outputId && (
              <p className="is-inline-error">
                O serviço confirmou o processamento, mas não retornou um arquivo
                de imagem. Consulte o histórico; não mostramos um resultado
                substituto.
              </p>
            )}
            {result && original && (
              <details className="is-details">
                <summary>
                  Comparar original e resultado{" "}
                  <span>Dois arquivos independentes</span>
                </summary>
                <div className="is-comparison">
                  <figure>
                    {originalPreview.url ? (
                      <img
                        src={originalPreview.url}
                        alt="Imagem original preservada"
                      />
                    ) : (
                      <p>{originalPreview.error || "Carregando original…"}</p>
                    )}
                    <figcaption>Original preservado</figcaption>
                  </figure>
                  <figure>
                    {resultPreview.url && (
                      <img src={resultPreview.url} alt="Resultado da edição" />
                    )}
                    <figcaption>Resultado recebido</figcaption>
                  </figure>
                </div>
              </details>
            )}
            {result && requiresImageReview(result) && (
              <section className="is-material-review">
                <h3>Seu olhar faz parte da criação.</h3>
                <p>
                  O resultado foi salvo como candidato. Confira os detalhes
                  antes de usá-lo em novas edições ou produções. Esta revisão
                  não aprova uma publicação.
                </p>
                <label>
                  O que você conferiu?
                  <textarea
                    rows={2}
                    value={reviewNotes}
                    maxLength={4000}
                    disabled={busy}
                    onChange={(event) => setReviewNotes(event.target.value)}
                    placeholder="Ex.: produto, cores, composição e elementos preservados."
                  />
                </label>
                <label className="is-check">
                  <input
                    type="checkbox"
                    disabled={!resultPreview.url || busy}
                    checked={reviewConfirmed}
                    onChange={(event) =>
                      setReviewConfirmed(event.target.checked)
                    }
                  />{" "}
                  Examinei a imagem exibida e quero registrar minha avaliação.
                </label>
                <div className="is-button-row">
                  <button
                    className="is-primary"
                    disabled={
                      busy ||
                      !resultPreview.url ||
                      !reviewConfirmed ||
                      !reviewNotes.trim()
                    }
                    onClick={() =>
                      void run(async () => {
                        const updated = await imageApi.review(
                          result,
                          "passed",
                          reviewNotes.trim(),
                        );
                        if (alive.current) {
                          setLocalAssets((current) => [
                            updated,
                            ...current.filter((item) => item.id !== updated.id),
                          ]);
                          setNotice(
                            "Avaliação visual registrada para o arquivo e checksum conferidos.",
                          );
                        }
                      })
                    }
                  >
                    <Check size={15} /> Aprovar como material
                  </button>
                  <button
                    disabled={
                      busy ||
                      !resultPreview.url ||
                      !reviewConfirmed ||
                      !reviewNotes.trim()
                    }
                    onClick={() =>
                      void run(async () => {
                        const updated = await imageApi.review(
                          result,
                          "failed",
                          reviewNotes.trim(),
                        );
                        if (alive.current) {
                          setLocalAssets((current) => [
                            updated,
                            ...current.filter((item) => item.id !== updated.id),
                          ]);
                          setNotice(
                            "Avaliação registrada. O material permanece no histórico para consulta.",
                          );
                        }
                      })
                    }
                  >
                    Marcar para ajustes
                  </button>
                </div>
              </section>
            )}
            {result && (
              <div className="is-result-next">
                <button
                  disabled={locked || requiresImageReview(result)}
                  onClick={() => {
                    setSourceId(result.id);
                    setMode("edit");
                    setJob(undefined);
                    setAuthorized(false);
                    setDirty(true);
                    setNotice(
                      "Resultado selecionado como nova origem. Descreva a próxima alteração.",
                    );
                  }}
                >
                  Continuar editando <ArrowRight size={14} />
                </button>
                <button
                  disabled={
                    locked ||
                    requiresImageReview(result) ||
                    references.length >= 3
                  }
                  onClick={() => {
                    setReferences((current) => [
                      ...new Set([...current, result.id]),
                    ]);
                    setAuthorized(false);
                    setDirty(true);
                    setNotice(
                      "Imagem selecionada como referência. Confira a autorização antes de gerar.",
                    );
                  }}
                >
                  Usar como referência
                </button>
                <button
                  disabled={locked || !ready}
                  onClick={() => void run(generate)}
                >
                  Gerar nova alternativa
                </button>
              </div>
            )}
            <details className="is-details is-native-details" open={requestedEntry === 'composition' ? true : undefined}>
              <summary>
                <Layers3 size={16} /> Edição avançada e produção editorial
                <span>PhotoCraft · camadas · formatos · versões</span>
              </summary>
              <p>
                Use as ferramentas já integradas para composição, textos, cores,
                camadas e exportação. A disponibilidade depende do runtime
                nativo. A geração por IA entrega um novo arquivo; não altera o
                original.
              </p>
              <div className="is-button-row">
                <button disabled={locked} onClick={() => void run(showNative)}>
                  Abrir editor PhotoCraft <ArrowRight size={14} />
                </button>
                <button
                  disabled={locked || dirty}
                  onClick={() => { setView("editorial"); onEditorial?.(); }}
                >
                  Produção editorial e carrosséis
                </button>
              </div>
              <p>
                Um resultado aprovado é vinculado como material, não inserido
                automaticamente na tela. Use o painel Materiais do PhotoCraft
                para posicioná-lo. Revisão e aprovação de conteúdo permanecem no
                fluxo editorial existente.
              </p>
            </details>
          </main>
          <aside className="is-controls">
            <div className="is-controls-title">
              <span className="is-eyebrow">
                {mode === "edit" ? "EDIÇÃO COM IA" : "DIREÇÃO CRIATIVA"}
              </span>
              <h2>
                {mode === "edit"
                  ? "O que vamos transformar?"
                  : "Comece pela sua ideia."}
              </h2>
              <p>
                {mode === "edit"
                  ? "Seja específico sobre o que muda e o que deve permanecer."
                  : "Uma boa descrição já é um ótimo ponto de partida."}
              </p>
            </div>
            <fieldset disabled={locked}>
              <label>
                {mode === "edit" ? "Alteração desejada" : "Descreva sua imagem"}
                <textarea
                  className="is-prompt"
                  rows={6}
                  maxLength={1000}
                  value={draft.prompt}
                  onChange={(event) => change("prompt", event.target.value)}
                  placeholder={
                    mode === "edit"
                      ? "Ex.: troque o ambiente por um estúdio claro, preservando o produto e suas cores."
                      : "Ex.: fotografia de um produto sobre pedra clara, luz natural lateral e espaço para um título."
                  }
                />
              </label>
              <div className="is-prompt-meta">
                <small>{draft.prompt.length}/1000</small>
                <button
                  className="is-klic-button"
                  disabled={locked || !draft.prompt.trim()}
                  onClick={() => void run(suggest)}
                >
                  <Sparkles size={14} /> Aprimorar com a KLIC
                </button>
              </div>
            </fieldset>
            {suggestion && (
              <div className="is-suggestion">
                <strong>Sugestão da KLIC</strong>
                <p>{suggestion}</p>
                <small>Seu texto original não foi substituído.</small>
                <div className="is-button-row">
                  <button
                    disabled={locked || suggestion.length > 1000}
                    onClick={() => {
                      change("prompt", suggestion);
                      setSuggestion("");
                    }}
                  >
                    Usar esta sugestão
                  </button>
                  <button disabled={locked} onClick={() => setSuggestion("")}>
                    Manter meu texto
                  </button>
                </div>
                {suggestion.length > 1000 && (
                  <small>
                    A sugestão excede o campo. Adapte o texto antes de usá-lo.
                  </small>
                )}
              </div>
            )}
            {mode === "edit" && (
              <div className="is-source-card">
                <span>Imagem que será editada</span>
                {source ? (
                  <div className="is-selected-source">
                    <AssetThumb asset={source} />
                    <div>
                      <strong>{source.title}</strong>
                      <small>O arquivo original será preservado</small>
                    </div>
                    <button
                      className="is-icon"
                      disabled={locked}
                      aria-label="Trocar imagem original"
                      onClick={() => {
                        setPickerRole("source");
                        setPickerOpen(true);
                      }}
                    >
                      <FolderOpen size={17} />
                    </button>
                  </div>
                ) : (
                  <button
                    disabled={locked}
                    onClick={() => {
                      setPickerRole("source");
                      setPickerOpen(true);
                    }}
                  >
                    <Upload size={16} /> Selecionar ou enviar imagem
                  </button>
                )}
              </div>
            )}
            <fieldset disabled={locked} className="is-essential-fields">
              <ClickoSelectMenu
                label="Finalidade"
                value={draft.purpose}
                options={IMAGE_PURPOSES.map((value) => [value, value])}
                onChange={(value) => change("purpose", value)}
              />
              <ClickoSelectMenu
                label="Enquadramento desejado"
                value={draft.aspect}
                options={IMAGE_FORMATS}
                onChange={(value) => change("aspect", value)}
              />
              <small className="is-field-note">
                Proporção enviada nativamente ao modelo e conferida no arquivo
                recebido. Resolução de geração: 1K; o tamanho do projeto não altera a resolução do provedor.
              </small>
            </fieldset>
            <details className="is-details">
              <summary>
                Referências visuais <span>{references.length}/3 imagens</span>
              </summary>
              <p>
                As referências orientam o modelo. O envio exige autorização de
                uso e revisão dos materiais gerados.
              </p>
              <div className="is-reference-list">
                {selectedAssets.map((asset) => (
                  <div key={asset.id}>
                    <AssetThumb asset={asset} />
                    <span>{asset.title}</span>
                    <button
                      disabled={locked}
                      className="is-icon"
                      aria-label={`Remover referência ${asset.title}`}
                      onClick={() => {
                        setReferences((current) =>
                          current.filter((id) => id !== asset.id),
                        );
                        setAuthorized(false);
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
              <button
                disabled={locked || references.length >= 3}
                onClick={() => {
                  setPickerRole("reference");
                  setPickerOpen(true);
                }}
              >
                <Plus size={14} /> Adicionar referência
              </button>
            </details>
            <details className="is-details">
              <summary>
                Ajustes da criação <span>Estilo, preservação e marca</span>
              </summary>
              <fieldset disabled={locked}>
                <label>
                  Nome do projeto
                  <input
                    value={draft.title}
                    maxLength={180}
                    onChange={(event) => change("title", event.target.value)}
                    placeholder="Opcional · sua descrição também pode dar nome ao projeto"
                  />
                </label>
                <ClickoSelectMenu
                  label="Estilo visual"
                  value={draft.style}
                  options={IMAGE_STYLES.map((value) => [
                    value,
                    value || "Deixar a descrição orientar",
                  ])}
                  onChange={(value) => change("style", value)}
                />
                <label>
                  Instruções adicionais
                  <textarea
                    value={draft.additional}
                    rows={2}
                    maxLength={1000}
                    onChange={(event) =>
                      change("additional", event.target.value)
                    }
                    placeholder="Iluminação, atmosfera, composição e restrições…"
                  />
                </label>
                <label>
                  O que preservar
                  <textarea
                    value={draft.preserve}
                    rows={3}
                    maxLength={4000}
                    onChange={(event) => change("preserve", event.target.value)}
                    placeholder="Uma instrução por linha. Ex.: cores do produto; logotipo; posição da embalagem."
                  />
                </label>
                <small>
                  São instruções ao modelo, não máscaras ou garantias de
                  preservação pixel a pixel. Remoção de fundo, expansão e troca
                  de objetos dependem da resposta real do provedor.
                </small>
                <label className="is-check">
                  <input
                    type="checkbox"
                    checked={draft.brand}
                    disabled={!brandContext || locked}
                    onChange={(event) => change("brand", event.target.checked)}
                  />{" "}
                  Usar as orientações visuais autorizadas da marca
                </label>
                {brandContext ? (
                  <small>
                    Nome, cores, tipografia e referências disponíveis no
                    contexto atual.
                  </small>
                ) : (
                  <small>
                    Nenhuma orientação visual de marca disponível neste
                    contexto.
                  </small>
                )}
                <p className="is-field-note">
                  Resolução: 1K, definida no adaptador. Uma imagem por
                  solicitação. Qualidade, seed e variações em lote não são
                  configuráveis neste contrato.
                </p>
              </fieldset>
            </details>
            {hasInputs && (
              <div className="is-authorization">
                <label>
                  Autorização de uso das imagens
                  <textarea
                    rows={2}
                    disabled={locked}
                    maxLength={1000}
                    value={usageEvidence}
                    onChange={(event) => {
                      setUsageEvidence(event.target.value);
                      setAuthorized(false);
                    }}
                    placeholder="Ex.: fotografias próprias do catálogo, com autorização para este uso."
                  />
                </label>
                <label className="is-check">
                  <input
                    type="checkbox"
                    disabled={locked || usageEvidence.trim().length < 3}
                    checked={authorized}
                    onChange={(event) => setAuthorized(event.target.checked)}
                  />{" "}
                  Confirmo a autorização declarada e o envio da
                  origem/referências ao provedor de IA.
                </label>
              </div>
            )}
            <div className="is-generate">
              <button
                className="is-primary"
                disabled={
                  locked ||
                  !ready ||
                  !draft.prompt.trim() ||
                  (mode === "edit" && !source) ||
                  (hasInputs && !authorized)
                }
                onClick={() => void run(generate)}
              >
                {busy || activeJob ? (
                  <LoaderCircle size={17} className="is-spin" />
                ) : (
                  <Sparkles size={17} />
                )}
                {mode === "edit" ? "Aplicar edição com IA" : "Gerar imagem"}
                <ArrowRight size={16} />
              </button>
              <small>
                {ready
                  ? "Cada solicitação aceita consome 1 imagem da cota, mesmo se falhar ou for cancelada."
                  : loading
                    ? "Conferindo o serviço de imagens…"
                    : "Geração indisponível: configure um provedor com suporte a esta operação no servidor."}
              </small>
            </div>
            <details className="is-details is-service-details">
              <summary>
                Serviço e utilização{" "}
                <span>
                  {ready ? "Provedor configurado" : "Verificação necessária"}
                </span>
              </summary>
              <dl>
                <dt>Provedor desta operação</dt>
                <dd>
                  {status?.stages?.[operation]?.label || "Não confirmado"}
                </dd>
                <dt>Modelo de imagem</dt>
                <dd>{model || "Não confirmado"}</dd>
                <dt>Validação audiovisual/visual</dt>
                <dd>
                  {status?.qualification === "pending_real_media_validation"
                    ? "Validação de mídia real pendente"
                    : status?.qualification || "Não informada"}
                </dd>
              </dl>
              <p>
                Uma unidade da cota de imagens por job aceito. Reenvios do
                mesmo pedido e tentativas do mesmo job não geram novo
                desconto. Os limites do plano e do colaborador são
                validados pelo servidor.
              </p>
              {usage && (
                <small>
                  {usage.jobs.length} solicitações no histórico recente de uso
                  do servidor. Os orçamentos e limites permanecem na
                  infraestrutura existente.
                </small>
              )}
              <button
                disabled={busy}
                onClick={() => setRefresh((value) => value + 1)}
              >
                <RefreshCw size={14} /> Conferir disponibilidade
              </button>
            </details>
          </aside>
        </div>
        {pickerOpen && (
          <AssetPicker
            assets={assets}
            role={pickerRole}
            query={query}
            setQuery={setQuery}
            disabled={locked}
            onSelect={selectAsset}
            onClose={() => setPickerOpen(false)}
            evidence={usageEvidence}
            setEvidence={setUsageEvidence}
            onUpload={() => inputRef.current?.click()}
          />
        )}
        <input
          ref={inputRef}
          type="file"
          hidden
          accept="image/png,image/jpeg,image/webp"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            void run(() => upload(file));
          }}
        />
      </div>
    </section>
  );
}

function imageError(cause: unknown) {
  const message = craftError(cause);
  if (/budget|quota|limit|usage|exhausted/i.test(message))
    return "O limite de uso ou orçamento deste ambiente foi atingido. Confira o consumo e as permissões antes de tentar novamente.";
  if (
    /not_configured|key_required|provider.*unavailable|editing_ai_endpoint|model_required/.test(
      message,
    )
  )
    return "O provedor ou modelo de imagens ainda não está disponível. Seu briefing e seus arquivos foram preservados.";
  if (/conflict|409/.test(message))
    return "O projeto mudou ou o pedido já foi registrado. Atualize o projeto/histórico antes de reenviar para evitar duplicação.";
  if (/rights|required.*source|source.*required/.test(message))
    return "Confira a imagem selecionada, seu vínculo com o projeto e a autorização de uso.";
  if (/queue_unavailable/.test(message))
    return "A fila de processamento está indisponível. O pedido ficou registrado; confira seu estado antes de tentar novamente.";
  return message;
}
function useImageUrl(asset?: AssetRecord) {
  const [state, setState] = React.useState<{
    url?: string;
    error?: string;
    loading: boolean;
  }>({ loading: false });
  React.useEffect(() => {
    const controller = new AbortController();
    let url: string | undefined;
    setState({ loading: Boolean(asset) });
    if (asset)
      void productApi
        .studioAssetBlob(asset.id, controller.signal)
        .then(async (blob) => {
          if (asset.checksumSha256)
            await verifyEditorialBlob(blob, asset.checksumSha256);
          if (controller.signal.aborted) return;
          url = URL.createObjectURL(blob);
          setState({ url, loading: false });
        })
        .catch((cause) => {
          if (!controller.signal.aborted)
            setState({ error: imageError(cause), loading: false });
        });
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [asset?.id, asset?.checksumSha256]);
  return state;
}
function AssetThumb({ asset }: { asset: AssetRecord }) {
  // Avoid eagerly decoding large originals for a small library thumbnail.
  const preview = useImageUrl(
    !asset.sizeBytes || asset.sizeBytes <= 4 * 1024 * 1024 ? asset : undefined,
  );
  return (
    <span className="is-thumb">
      {preview.url ? (
        <img src={preview.url} alt="" decoding="async" loading="lazy" />
      ) : (
        <ImageIcon size={20} />
      )}
    </span>
  );
}
function AssetPicker({
  assets,
  role,
  query,
  setQuery,
  disabled,
  onSelect,
  onClose,
  evidence,
  setEvidence,
  onUpload,
}: {
  assets: AssetRecord[];
  role: "source" | "reference";
  query: string;
  setQuery: (value: string) => void;
  disabled: boolean;
  onSelect: (asset: AssetRecord) => void;
  onClose: () => void;
  evidence: string;
  setEvidence: (value: string) => void;
  onUpload: () => void;
}) {
  const ref = React.useRef<HTMLDialogElement>(null);
  React.useEffect(() => {
    const focused = document.activeElement as HTMLElement | null;
    ref.current?.showModal();
    return () => focused?.focus();
  }, []);
  const filtered = assets
    .filter((asset) =>
      `${asset.title} ${(asset.tags || []).join(" ")}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    )
    .slice(0, 24);
  return (
    <dialog
      ref={ref}
      className="is-picker"
      aria-labelledby="is-picker-title"
      onCancel={onClose}
    >
      <header>
        <div>
          <span className="is-eyebrow">BIBLIOTECA DO AMBIENTE</span>
          <h2 id="is-picker-title">
            {role === "source"
              ? "Qual imagem vamos editar?"
              : "Escolha uma referência visual."}
          </h2>
        </div>
        <button
          className="is-icon"
          aria-label="Fechar seleção de imagens"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </header>
      <label>
        Buscar imagens
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Nome do arquivo ou marcador da marca"
          autoFocus
        />
      </label>
      <div className="is-picker-grid">
        {filtered.map((asset) => (
          <button
            key={asset.id}
            disabled={disabled || requiresImageReview(asset)}
            onClick={() => onSelect(asset)}
          >
            <AssetThumb asset={asset} />
            <strong>{asset.title}</strong>
            <small>
              {requiresImageReview(asset)
                ? "Revisão visual pendente"
                : asset.metadata?.editingResource
                  ? "Material do acervo"
                  : "Arquivo da Biblioteca"}
            </small>
          </button>
        ))}
      </div>
      {!filtered.length && (
        <p>Nenhuma imagem encontrada. Envie um arquivo PNG, JPEG ou WebP.</p>
      )}
      <footer>
        <label>
          Autorização para o arquivo que será enviado
          <input
            value={evidence}
            onChange={(event) => setEvidence(event.target.value)}
            maxLength={1000}
            placeholder="Ex.: fotografia própria, autorizada para este projeto."
          />
        </label>
        <button
          className="is-primary"
          disabled={disabled || evidence.trim().length < 3}
          onClick={onUpload}
        >
          <Upload size={15} /> Enviar imagem do dispositivo
        </button>
        <small>
          Até 12 MB neste fluxo. O original é armazenado na Biblioteca; nenhuma
          imagem é enviada à IA apenas por selecioná-la.
        </small>
      </footer>
    </dialog>
  );
}
