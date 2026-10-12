import React from "react";
import { APIError } from "../../api";
import { productApi, type StudioDocumentCreate, type StudioGenerationJobRecord, type StudioDocumentVersionRecord } from "../../api/productApi";
import { craftApi, type CraftCommand, type CraftDocument, type CraftEngine, type CraftEngineDescriptor, type CraftInspection, type CraftReceipt } from "./craftApi";
import { craftRecoveryKey, readCraftRecovery, type CraftRecovery } from "./craftState";

type CraftStatus = "loading" | "ready" | "working" | "dirty" | "offline" | "conflict" | "error";
interface Options {
  engine: CraftEngine;
  workspaceId?: string;
  userId?: string;
  postId?: string;
  requestedDocumentId?: string;
  campaignId?: string;
  contentType: "visual" | "carousel" | "video";
  title: string;
  objective?: string;
  audience?: string;
  brandRevision: number;
  enabled: boolean;
  standalone?: boolean;
  onCreated?: (id: string, postId?: string) => void;
}

export function craftError(cause: unknown) {
  return cause instanceof Error ? cause.message : "Não foi possível concluir a operação do Studio.";
}
function isConflict(cause: unknown) { return cause instanceof APIError && cause.status === 409; }

export function useCraftStudio(options: Options) {
  const [engines, setEngines] = React.useState<CraftEngineDescriptor[]>([]);
  const [document, setDocument] = React.useState<CraftDocument>();
  const [documents, setDocuments] = React.useState<CraftDocument[]>([]);
  const [inspection, setInspection] = React.useState<CraftInspection>();
  const [activePageId, setActivePageId] = React.useState<string>();
  const activePageRef = React.useRef<string>();
  const [status, setStatus] = React.useState<CraftStatus>("loading");
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [pending, setPending] = React.useState<CraftRecovery>();
  const [recovery, setRecovery] = React.useState<CraftRecovery>();
  const [job, setJob] = React.useState<StudioGenerationJobRecord>();
  const [jobRevision, setJobRevision] = React.useState<number>();
  const [versions, setVersions] = React.useState<StudioDocumentVersionRecord[]>([]);
  const documentRef = React.useRef<CraftDocument>();
  const pendingRef = React.useRef<CraftRecovery>();
  const workingRef = React.useRef(false);
  const scopeRef = React.useRef(0);
  const [reload, setReload] = React.useState(0);
  const { engine, workspaceId, userId, postId, requestedDocumentId, enabled } = options;
  const engineInfo = engines.find((item) => item.engine === engine);
  const scope = document && userId && workspaceId ? { userId, workspaceId, documentId: document.documentId, engine } : undefined;
  const recoveryKey = scope ? craftRecoveryKey(userId!, workspaceId!, scope.documentId, engine) : undefined;
  const draftKey = userId && workspaceId ? `clicko:craft-project:${encodeURIComponent(userId)}:${encodeURIComponent(workspaceId)}:${encodeURIComponent(postId || "draft")}:${engine}` : undefined;

  const rememberDocument = React.useCallback((next: CraftDocument) => {
    documentRef.current = next;
    setDocument(next);
    setDocuments((current) => [next, ...current.filter((item) => item.documentId !== next.documentId)]);
  }, []);

  React.useEffect(() => {
    const controller = new AbortController();
    void craftApi.engines(controller.signal).then((value) => setEngines(value.engines)).catch((cause) => {
      if (!controller.signal.aborted) { setEngines([]); setError(craftError(cause)); }
    });
    return () => controller.abort();
  }, [reload]);

  React.useEffect(() => {
    const generation = ++scopeRef.current;
    documentRef.current = undefined;
    pendingRef.current = undefined;
    workingRef.current = false;
    setDocument(undefined); setDocuments([]); setInspection(undefined); setActivePageId(undefined); activePageRef.current = undefined; setJob(undefined); setJobRevision(undefined);
    setPending(undefined); setRecovery(undefined); setError(undefined); setNotice(undefined);
    const controller = new AbortController();
    if (!enabled || !workspaceId || !userId) { setStatus("ready"); return; }
    setStatus("loading");
    async function load() {
      try {
        const records = await productApi.studioDocuments(workspaceId!, postId ? { postId } : {});
        if (scopeRef.current !== generation) return;
        const savedDraft = draftKey && localStorage.getItem(draftKey);
        const candidates = records as CraftDocument[];
        setDocuments(candidates);
        let selected: CraftDocument | undefined;
        if (requestedDocumentId) {
          selected = await productApi.studioDocument(requestedDocumentId);
          if (selected.workspaceId !== workspaceId) throw new Error("O projeto pertence a outro workspace.");
          if (postId && selected.postRef?.id !== postId) throw new Error("Este projeto pertence a outro conteúdo. Abra-o pelo conteúdo correspondente.");
        } else {
          selected = candidates.find((item) => item.documentId === savedDraft && (item.nativeEditorState?.engine === engine || !item.nativeEditorState && item.contentType === options.contentType))
            ?? (postId ? candidates.find((item) => item.nativeEditorState?.engine === engine) : undefined)
            ?? (postId ? candidates.find((item) => !item.nativeEditorState && item.contentType === options.contentType) : undefined);
        }
        if (scopeRef.current !== generation) return;
        if (selected) {
          rememberDocument(selected);
          if (selected.nativeEditorState?.engine === engine) {
            const detail = await craftApi.inspection(selected.documentId, controller.signal);
            if (scopeRef.current !== generation) return;
            setInspection(detail);
            setActivePageId(detail.activePageId); activePageRef.current = detail.activePageId;
          }
          const jobs = await productApi.studioGenerationJobs(workspaceId!, { documentId: selected.documentId, jobType: "craft_render", limit: 10 });
          if (scopeRef.current !== generation) return;
          const recent = jobs.find((item) => item.provider === `craft.${engine}`);
          if (recent) { setJob(recent); setJobRevision(Number(recent.request.documentRevision)); }
        }
        if (scopeRef.current === generation) setStatus("ready");
      } catch (cause) {
        if (scopeRef.current === generation && !controller.signal.aborted) { setError(craftError(cause)); setStatus("error"); }
      }
    }
    void load();
    return () => { controller.abort(); ++scopeRef.current; };
  }, [engine, workspaceId, userId, postId, requestedDocumentId, enabled, options.contentType, draftKey, reload, rememberDocument]);

  React.useEffect(() => {
    if (!scope || !recoveryKey) return;
    try { setRecovery(readCraftRecovery(localStorage.getItem(recoveryKey), scope)); }
    catch { setNotice("A recuperação local está indisponível neste navegador."); }
  }, [recoveryKey]);

  const persistPending = React.useCallback((next: CraftRecovery | undefined) => {
    pendingRef.current = next; setPending(next);
    if (!recoveryKey) return;
    try {
      if (next) localStorage.setItem(recoveryKey, JSON.stringify(next));
      else localStorage.removeItem(recoveryKey);
    } catch {
      setNotice("O navegador não conseguiu guardar a recuperação. Salve as alterações antes de fechar.");
    }
  }, [recoveryKey]);

  const accept = React.useCallback((receipt: CraftReceipt) => {
    rememberDocument(receipt.document); setInspection(receipt.inspection); setStatus("ready");
    setActivePageId(receipt.inspection.activePageId); activePageRef.current = receipt.inspection.activePageId;
  }, [rememberDocument]);

  const save = React.useCallback(async () => {
    const active = documentRef.current;
    const batch = pendingRef.current;
    if (!active || !batch) return active;
    if (workingRef.current) throw new Error("Aguarde a operação em andamento antes de salvar.");
    if (!navigator.onLine) { setStatus("offline"); throw new Error("Sem conexão. As alterações estão guardadas para recuperação."); }
    if (batch.expectedRevision !== active.revision && !batch.attempted) { setStatus("conflict"); throw new Error("O projeto mudou após estas alterações. Guarde a recuperação e abra a revisão atual."); }
    const generation = scopeRef.current;
    workingRef.current = true; setStatus("working"); setError(undefined);
    persistPending({ ...batch, attempted: true });
    try {
      const receipt = await craftApi.commands(active.documentId, batch.expectedRevision, batch.commands, batch.idempotencyKey, "Ajustes manuais no Clicko", batch.pageId);
      if (scopeRef.current !== generation) return active;
      accept(receipt); persistPending(undefined); setRecovery(undefined);
      setNotice("Alterações salvas no projeto.");
      return receipt.document;
    } catch (cause) {
      if (scopeRef.current === generation) { setError(craftError(cause)); setStatus(isConflict(cause) ? "conflict" : !navigator.onLine ? "offline" : "error"); }
      throw cause;
    } finally { if (scopeRef.current === generation) workingRef.current = false; }
  }, [accept, persistPending]);

  React.useEffect(() => {
    if (!pending || status !== "dirty") return;
    const timer = window.setTimeout(() => void save().catch(() => undefined), 5000);
    return () => window.clearTimeout(timer);
  }, [pending, status, save]);
  React.useEffect(() => {
    const reconnect = () => { if (pendingRef.current) { setStatus("dirty"); setNotice("Conexão recuperada. Salvando alterações…"); } };
    const leave = (event: BeforeUnloadEvent) => { if (pendingRef.current || workingRef.current) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("online", reconnect); window.addEventListener("beforeunload", leave);
    return () => { window.removeEventListener("online", reconnect); window.removeEventListener("beforeunload", leave); };
  }, []);

  const queue = (command: CraftCommand) => {
    const active = documentRef.current;
    if (!active || !scope || workingRef.current || recovery || status === "conflict") return;
    if (pendingRef.current?.attempted) { setError("Salve novamente o lote pendente antes de adicionar outros ajustes."); return; }
    const next: CraftRecovery = pendingRef.current ? {
      ...pendingRef.current, commands: [...pendingRef.current.commands, command], updatedAt: new Date().toISOString(),
    } : { ...scope, schemaVersion: "clicko.craft-recovery.v1", expectedRevision: active.revision, idempotencyKey: crypto.randomUUID(), commands: [command], pageId: activePageRef.current, updatedAt: new Date().toISOString() };
    persistPending(next); setStatus(navigator.onLine ? "dirty" : "offline"); setError(undefined);
  };

  async function operate<T>(task: (active: CraftDocument) => Promise<T>, update?: (value: T) => void): Promise<T> {
    if (recovery) throw new Error("Resolva a recuperação local antes de alterar o projeto.");
    await save();
    const active = documentRef.current;
    if (!active) throw new Error("Abra ou crie um projeto primeiro.");
    if (workingRef.current) throw new Error("Outra operação está em andamento.");
    const generation = scopeRef.current;
    workingRef.current = true; setStatus("working"); setError(undefined);
    try {
      const result = await task(active);
      if (scopeRef.current === generation) { update?.(result); setStatus("ready"); }
      return result;
    } catch (cause) {
      if (scopeRef.current === generation) { setError(craftError(cause)); setStatus(isConflict(cause) ? "conflict" : "error"); }
      throw cause;
    } finally { if (scopeRef.current === generation) workingRef.current = false; }
  }

  async function migrate() {
    const generation = scopeRef.current;
    const result = await operate((active) => craftApi.migrate(active.documentId, engine, active.revision, crypto.randomUUID()), (value) => { setInspection(value); setActivePageId(value.activePageId); activePageRef.current = value.activePageId; });
    const next = await productApi.studioDocument(result.documentId);
    if (scopeRef.current === generation) rememberDocument(next);
  }

  async function create(title: string, width: number, height: number) {
    if (!workspaceId || !userId || !engineInfo?.available || workingRef.current) return;
    workingRef.current = true; setStatus("working"); setError(undefined);
    const generation = scopeRef.current;
    try {
      const linkedPostId = postId || (options.standalone ? undefined : (await productApi.createPost({
        workspaceId, title, platform: "instagram", format: options.contentType === "video" ? "video" : options.contentType === "carousel" ? "carousel" : "post",
        copy: "", hashtags: [], status: "draft", author: "Clicko Studios", campaignId: options.campaignId ?? null,
        objective: options.objective || "Criar uma peça pronta para revisão", origin: "manual",
      })).id);
      if (scopeRef.current !== generation) return;
      const body: StudioDocumentCreate = {
        workspaceId, title, engine, contentType: options.contentType, postId: linkedPostId ?? null,
        campaignId: options.campaignId ?? null, brandRevision: options.brandRevision,
        brief: { schemaVersion: "studio.creative-brief.v1", objective: options.objective || "Criar uma peça pronta para revisão", audience: options.audience || "Audiência da marca", angle: "", promise: "", hook: title, cta: "", channel: "instagram", format: options.contentType === "video" ? "video" : options.contentType === "carousel" ? "carousel" : "post", tone: "claro", restrictions: [], hypotheses: [], evidence: [] },
        composition: { pages: Array.from({ length: options.contentType === "carousel" ? 2 : 1 }, (_, index) => ({ id: `page-${index + 1}`, role: "content", width, height, safeArea: 0, background: "#151515", durationMs: options.contentType === "video" ? 5000 : null, layers: [] })), tracks: [], narrative: {}, mediaTimeline: options.contentType === "video" ? { schemaVersion: "studio.media-timeline.v1", frameRate: { numerator: 30, denominator: 1 }, durationFrames: 150, tracks: [] } : null },
        assets: [], correlationId: crypto.randomUUID(),
      };
      const created = await productApi.createStudioDocument(body);
      if (scopeRef.current !== generation) return;
      rememberDocument(created);
      if (draftKey) localStorage.setItem(draftKey, created.documentId);
      const migrated = await craftApi.migrate(created.documentId, engine, created.revision, crypto.randomUUID());
      if (scopeRef.current !== generation) return;
      setInspection(migrated);
      setActivePageId(migrated.activePageId); activePageRef.current = migrated.activePageId;
      rememberDocument(await productApi.studioDocument(created.documentId));
      setStatus("ready"); options.onCreated?.(created.documentId, linkedPostId);
    } catch (cause) { if (scopeRef.current === generation) { setError(craftError(cause)); setStatus("error"); } }
    finally { if (scopeRef.current === generation) workingRef.current = false; }
  }

  React.useEffect(() => {
    if (!job || ["succeeded", "failed", "cancelled"].includes(job.status)) return;
    let active = true;
    const timer = window.setTimeout(() => {
      void productApi.studioGenerationJob(job.id).then((next) => { if (active) setJob(next); }).catch((cause) => { if (active) { setError(craftError(cause)); setNotice("A consulta da exportação falhou. Reabra o projeto para recuperar o job."); } });
    }, 2000);
    return () => { active = false; window.clearTimeout(timer); };
  }, [job]);

  const recover = () => {
    if (!recovery || !documentRef.current) return;
    if (recovery.expectedRevision !== documentRef.current.revision && !recovery.attempted) { setStatus("conflict"); setError("Esta recuperação pertence a uma revisão anterior. Baixe as alterações antes de descartá-las."); return; }
    persistPending(recovery); setRecovery(undefined); setStatus(navigator.onLine ? "dirty" : "offline");
  };
  const discardRecovery = () => { persistPending(undefined); setRecovery(undefined); setStatus("ready"); setError(undefined); };

  return {
    engineInfo, engines, document, documents, inspection, activePageId, status, error, notice, pending, recovery, job, jobRevision, versions,
    busy: status === "working" || status === "loading",
    create, migrate, queue, save, recover, discardRecovery,
    refresh: () => setReload((value) => value + 1),
    undo: () => operate((active) => craftApi.commands(active.documentId, active.revision, [{ id: "host.history.undo", params: {} }], crypto.randomUUID(), undefined, activePageRef.current), accept),
    redo: () => operate((active) => craftApi.commands(active.documentId, active.revision, [{ id: "host.history.redo", params: {} }], crypto.randomUUID(), undefined, activePageRef.current), accept),
    applyAI: (instruction: string) => operate((active) => craftApi.ai(active.documentId, active.revision, instruction, crypto.randomUUID(), activePageRef.current), accept),
    exportProject: (format: string, frame: number) => operate(async (active) => ({ job: await craftApi.render(active.documentId, active.revision, format, crypto.randomUUID(), frame, activePageRef.current), revision: active.revision }), (value) => { setJob(value.job); setJobRevision(value.revision); }),
    cancelJob: async () => { if (job) setJob(await productApi.cancelStudioGenerationJob(job.id)); },
    loadVersions: async () => { if (documentRef.current) setVersions(await productApi.studioDocumentVersions(documentRef.current.documentId)); },
    loadNative: () => operate((active) => craftApi.loadNative(active.documentId, undefined, (active.nativeEditorState?.pageProjects?.length ?? 0) > 1, activePageRef.current)),
    saveNative: (file: File) => operate((active) => craftApi.saveNative(active.documentId, engine, active.revision, file, crypto.randomUUID(), activePageRef.current), accept),
    selectPage: (pageId: string) => operate((active) => craftApi.inspection(active.documentId, undefined, pageId), (value) => { setInspection(value); setActivePageId(value.activePageId || pageId); activePageRef.current = value.activePageId || pageId; }),
    pageCommand: (id: string, params: Record<string, unknown>) => operate((active) => craftApi.commands(active.documentId, active.revision, [{ id, params }], crypto.randomUUID(), "Organização de páginas", activePageRef.current), accept),
    linkComposition: (compositionDocumentId: string) => operate((active) => craftApi.linkComposition(active.documentId, active.revision, compositionDocumentId, crypto.randomUUID()), accept),
    review: async () => operate((active) => {
      if (job?.status !== "succeeded" || jobRevision !== active.revision) throw new Error("Exporte a revisão atual antes de enviá-la para aprovação.");
      return productApi.requestStudioReview(active.documentId, "Criado e editado no Clicko Studios", job.id);
    }),
  };
}
