import React from "react";
import { BackendRequestError } from "../api/client";
import {
  productApi,
  type StudioDocumentInput,
  type StudioDocumentRecord,
  type StudioDocumentVersionRecord,
} from "../api/productApi";

export type StudioDocumentStatus =
  | "idle"
  | "loading"
  | "ready"
  | "dirty"
  | "saving"
  | "conflict"
  | "offline"
  | "error";

interface StudioDocumentOptions {
  enabled: boolean;
  autoCreate?: boolean;
  workspaceId?: string;
  postId?: string;
  campaignId?: string;
  contentType: "visual" | "carousel";
  title: string;
  initialHeadlines: string[];
  objective?: string;
  audience?: string;
  brandRevision?: number;
  opportunityId?: string;
  autosaveDelay?: number;
}

export interface SaveStudioDocumentInput {
  headlines: string[];
  narrative?: Record<string, unknown>;
  label?: string;
}

function pageForHeadline(headline: string, index: number) {
  const id = `page-${index + 1}`;
  return {
    id,
    role: index === 0 ? "hook" : "content",
    width: 1080,
    height: 1350,
    safeArea: 76,
    background: "#10181c",
    durationMs: null,
    layers: [
      {
        id: `${id}-headline`,
        kind: "text" as const,
        name: headline,
        x: 90,
        y: 120,
        width: 900,
        height: 540,
        rotation: 0,
        opacity: 1,
        visible: true,
        locked: false,
        zIndex: 1,
        properties: {
          type: "text",
          text: headline,
          fontSize: 76,
          minFontSize: 24,
          fontFamily: "DejaVu Sans",
          fontWeight: "bold",
          color: "#ffffff",
          align: "left",
          lineHeight: 0.95,
        },
      },
    ],
  };
}

function motionTimelineFor(headlineCount: number) {
  return {
    schemaVersion: "studio.media-timeline.v1" as const,
    frameRate: { numerator: 30, denominator: 1 },
    durationFrames: Math.max(150, headlineCount * 150),
    tracks: [],
  };
}

export function studioHeadlines(document?: StudioDocumentRecord) {
  return (
    document?.composition.pages.map((page) => {
      const layer = page.layers?.find((candidate) => candidate.kind === "text");
      const text = layer?.properties?.text;
      return typeof text === "string" && text.trim() ? text : layer?.name || "Sem título";
    }) ?? []
  );
}

export function useStudioDocument({
  enabled,
  autoCreate = true,
  workspaceId,
  postId,
  campaignId,
  contentType,
  title,
  initialHeadlines,
  objective = "Criar uma peça visual pronta para revisão",
  audience = "Audiência definida no conteúdo",
  brandRevision = 1,
  opportunityId,
  autosaveDelay = 900,
}: StudioDocumentOptions) {
  const [document, setDocument] = React.useState<StudioDocumentRecord>();
  const [versions, setVersions] = React.useState<StudioDocumentVersionRecord[]>([]);
  const [status, setStatus] = React.useState<StudioDocumentStatus>("idle");
  const [error, setError] = React.useState<string>();
  const initialHeadlinesRef = React.useRef(initialHeadlines);
  const documentRef = React.useRef<StudioDocumentRecord>();
  const pendingRef = React.useRef<SaveStudioDocumentInput>();
  const savingRef = React.useRef(false);
  const [pendingRevision, setPendingRevision] = React.useState(0);

  React.useEffect(() => {
    initialHeadlinesRef.current = initialHeadlines;
  }, [initialHeadlines]);

  React.useEffect(() => {
    if (!enabled || !workspaceId || !postId) {
      setDocument(undefined);
      setVersions([]);
      documentRef.current = undefined;
      setStatus("idle");
      setError(undefined);
      return;
    }
    let current = true;
    const load = async () => {
      setStatus("loading");
      setError(undefined);
      try {
        const records = await productApi.studioDocuments(workspaceId, {
          postId,
          campaignId,
        });
        let record = records.find((candidate) => candidate.contentType === contentType);
        if (!record && autoCreate) {
          const headlines = initialHeadlinesRef.current;
          record = await productApi.createStudioDocument({
            workspaceId,
            title,
            contentType,
            campaignId: campaignId ?? null,
            postId,
            opportunityId: opportunityId ?? null,
            brandRevision,
            brief: {
              schemaVersion: "studio.creative-brief.v1",
              objective,
              audience,
              angle: "",
              promise: "",
              hook: headlines[0] || title,
              cta: "Revisar direção",
              channel: "instagram",
              format: contentType === "carousel" ? "carousel" : "post",
              tone: "claro e autoral",
              restrictions: [],
              hypotheses: [],
              evidence: [],
            },
            composition: {
              pages: headlines.map(pageForHeadline),
              narrative: { headlines },
              tracks: [],
              mediaTimeline: motionTimelineFor(headlines.length),
            },
            assets: [],
            correlationId: crypto.randomUUID(),
          });
        }
        if (!current) return;
        setDocument(record);
        documentRef.current = record;
        setStatus("ready");
      } catch (requestError) {
        if (!current) return;
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Não foi possível abrir o documento do Studio.",
        );
        setStatus("error");
      }
    };
    void load();
    return () => {
      current = false;
    };
  }, [
    audience,
    autoCreate,
    brandRevision,
    campaignId,
    contentType,
    enabled,
    objective,
    opportunityId,
    postId,
    title,
    workspaceId,
  ]);

  const save = React.useCallback(
    async (input?: SaveStudioDocumentInput) => {
      const pendingAtStart = pendingRef.current;
      const activeInput = input ?? pendingAtStart;
      const currentDocument = documentRef.current;
      if (!currentDocument) throw new Error("O documento do Studio ainda não está pronto.");
      if (!activeInput) return currentDocument;
      if (savingRef.current) return currentDocument;
      if (!navigator.onLine) {
        setStatus("offline");
        throw new Error("Sem conexão. As alterações continuam pendentes neste navegador.");
      }
      savingRef.current = true;
      setStatus("saving");
      setError(undefined);
      try {
        const next = {
          ...currentDocument,
          title,
          brief: {
            ...currentDocument.brief,
            hook: activeInput.headlines[0] || currentDocument.brief.hook,
          },
          composition: {
            ...currentDocument.composition,
            pages: activeInput.headlines.map(pageForHeadline),
            narrative: activeInput.narrative ?? { headlines: activeInput.headlines },
            mediaTimeline:
              currentDocument.composition.mediaTimeline ??
              motionTimelineFor(activeInput.headlines.length),
          },
        } as StudioDocumentInput;
        const saved = await productApi.replaceStudioDocument(
          currentDocument.documentId,
          currentDocument.revision,
          next,
        );
        setDocument(saved);
        documentRef.current = saved;
        if (pendingRef.current === pendingAtStart) pendingRef.current = undefined;
        setStatus(pendingRef.current ? "dirty" : "ready");
        return saved;
      } catch (requestError) {
        const conflict = requestError instanceof BackendRequestError && requestError.status === 409;
        setError(conflict
          ? "Há uma revisão mais recente deste documento. Recarregue antes de continuar."
          : requestError instanceof Error
            ? requestError.message
            : "Não foi possível salvar o documento do Studio.");
        setStatus(conflict ? "conflict" : navigator.onLine ? "error" : "offline");
        throw requestError;
      } finally {
        savingRef.current = false;
      }
    },
    [title],
  );

  const queueSave = React.useCallback((input: SaveStudioDocumentInput) => {
    pendingRef.current = input;
    setStatus(navigator.onLine ? "dirty" : "offline");
    setPendingRevision((value) => value + 1);
  }, []);

  React.useEffect(() => {
    if (!pendingRef.current || !["dirty", "offline"].includes(status)) return;
    if (status === "offline") return;
    const timer = window.setTimeout(() => void save().catch(() => undefined), autosaveDelay);
    return () => window.clearTimeout(timer);
  }, [autosaveDelay, pendingRevision, save, status]);

  React.useEffect(() => {
    const online = () => {
      if (pendingRef.current) {
        setStatus("dirty");
        setPendingRevision((value) => value + 1);
      }
    };
    const offline = () => {
      if (pendingRef.current) setStatus("offline");
    };
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);

  React.useEffect(() => {
    const warnUnsaved = (event: BeforeUnloadEvent) => {
      if (!pendingRef.current || !["dirty", "saving", "offline"].includes(status)) return;
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warnUnsaved);
    return () => window.removeEventListener("beforeunload", warnUnsaved);
  }, [status]);

  const reload = React.useCallback(async () => {
    const current = documentRef.current;
    if (!current) throw new Error("O documento do Studio ainda não está pronto.");
    const latest = await productApi.studioDocument(current.documentId);
    pendingRef.current = undefined;
    documentRef.current = latest;
    setDocument(latest);
    setError(undefined);
    setStatus("ready");
    return latest;
  }, []);

  const createVersion = React.useCallback(async (label = "Versão manual") => {
    if (pendingRef.current) await save();
    const current = documentRef.current;
    if (!current) throw new Error("O documento do Studio ainda não está pronto.");
    setStatus("saving");
    const versioned = await productApi.createStudioVersion(current.documentId, label);
    documentRef.current = versioned;
    setDocument(versioned);
    setVersions(await productApi.studioDocumentVersions(versioned.documentId));
    setStatus("ready");
    return versioned;
  }, [save]);

  const loadVersions = React.useCallback(async () => {
    const current = documentRef.current;
    if (!current) return [];
    const history = await productApi.studioDocumentVersions(current.documentId);
    setVersions(history);
    return history;
  }, []);

  const restoreVersion = React.useCallback(async (versionNumber: number) => {
    if (pendingRef.current) await save();
    const current = documentRef.current;
    if (!current) throw new Error("O documento do Studio ainda não está pronto.");
    setStatus("saving");
    try {
      const restored = await productApi.restoreStudioDocumentVersion(
        current.documentId,
        versionNumber,
        current.revision,
        `Restaurada da v${versionNumber}`,
      );
      pendingRef.current = undefined;
      documentRef.current = restored;
      setDocument(restored);
      setVersions(await productApi.studioDocumentVersions(restored.documentId));
      setError(undefined);
      setStatus("ready");
      return restored;
    } catch (requestError) {
      const conflict = requestError instanceof BackendRequestError && requestError.status === 409;
      setError(conflict
        ? "O documento mudou antes da restauração. Recarregue o histórico."
        : requestError instanceof Error
          ? requestError.message
          : "Não foi possível restaurar esta versão.");
      setStatus(conflict ? "conflict" : "error");
      throw requestError;
    }
  }, [save]);

  const requestReview = React.useCallback(async (comment?: string) => {
    if (pendingRef.current) await save();
    const current = documentRef.current;
    if (!current) throw new Error("O documento do Studio ainda não está pronto.");
    return productApi.requestStudioReview(current.documentId, comment);
  }, [save]);

  const exportPng = React.useCallback(async () => {
    if (!document) throw new Error("O documento do Studio ainda não está pronto.");
    const asset = await productApi.exportStudioDocument(
      document.documentId,
      document.contentType === "carousel" ? "png_set" : "png",
    );
    await reload();
    return asset;
  }, [document, reload]);

  return {
    document,
    versions,
    status,
    error,
    save,
    queueSave,
    createVersion,
    loadVersions,
    restoreVersion,
    requestReview,
    reload,
    exportPng,
  };
}
