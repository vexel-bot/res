import React from "react";
import { apiFetch } from "../api";
import { BackendRequestError, type BackendSchema } from "../api/client";
import {
  productApi,
  type AssetRecord,
  type StudioAdvancedCapabilityAuditRecord,
  type StudioAssetRightsReviewInput,
  type StudioAssistedIntelligenceSuiteRecord,
  type StudioDocumentCreate,
  type StudioDocumentInput,
  type StudioDocumentRecord,
  type StudioEditDecisionRecord,
  type StudioGenerationJobRecord,
  type StudioMediaIngestRecord,
  type StudioCreativeCasebookRecord,
  type StudioCreativeReplanStateRecord,
  type StudioTranscriptRecord,
  type StudioVideoFactoryProgramRecord,
  type StudioVideoAutonomyAuditRecord,
} from "../api/productApi";
import {
  applyVideoTimelineCommand,
  setOriginalAudioMuted,
  type VideoTimelineCommand,
} from "./videoTimeline";
import { NATURAL_SOUND_TRACK_ID, placeNaturalSound, setNaturalSoundEnabled, type NaturalSoundPlacement } from "./naturalSoundTimeline";

type VideoStudioStatus =
  | "idle"
  | "loading"
  | "ready"
  | "working"
  | "error";

interface StudioHistoryEntry {
  snapshot: StudioDocumentRecord;
  appliesToRevision: number;
}

export interface AssistedOperationDecisionInput {
  operationId: string;
  decision: "accept" | "reject" | "adjust";
  adjustedText?: string;
}

interface AudioWaveformManifest {
  schemaVersion: "studio.audio-waveform-manifest.v1";
  sourceAssetId: string;
  sampleRate: number;
  bucketCount: number;
  buckets: Array<{ minimum: number; maximum: number; rms?: number | null }>;
}

interface VideoStudioOptions {
  enabled: boolean;
  workspaceId?: string;
  postId?: string;
  campaignId?: string;
  title: string;
  objective: string;
  audience: string;
  tone: string;
  brandRevision: number;
  primaryColor: string;
  initialAsset?: AssetRecord;
}

function messageFrom(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Não foi possível concluir esta operação do Video Studio.";
}

function frameRateFrom(ingest: StudioMediaIngestRecord) {
  return ingest.mediaInfo?.videoStreams?.[0]?.frameRate ?? {
    numerator: 30,
    denominator: 1,
  };
}

function durationFramesFrom(ingest: StudioMediaIngestRecord) {
  const rate = frameRateFrom(ingest);
  const seconds = (ingest.mediaInfo?.durationMicroseconds ?? 1_000_000) / 1_000_000;
  return Math.max(1, Math.round(seconds * (rate.numerator / rate.denominator)));
}

function createVideoDocumentInput(
  options: VideoStudioOptions,
  asset: AssetRecord,
  ingest: StudioMediaIngestRecord,
): StudioDocumentCreate {
  const durationFrames = durationFramesFrom(ingest);
  const durationMicroseconds = ingest.mediaInfo?.durationMicroseconds ?? 1_000_000;
  const durationMs = Math.max(1, Math.round(durationMicroseconds / 1_000));
  const sourceClip = {
    id: `source-${crypto.randomUUID()}`,
    assetId: asset.id,
    timeline: { startFrame: 0, durationFrames },
    source: { startMicroseconds: 0, durationMicroseconds },
    enabled: true,
    locked: false,
    label: asset.title,
    playbackRate: 1,
    transform: { fit: "cover", anchor: "center" },
    effects: [],
    keyframes: [],
  };
  const tracks: NonNullable<
    StudioDocumentCreate["composition"]["mediaTimeline"]
  >["tracks"] = [
    {
      id: "video-main",
      kind: "video",
      name: "Vídeo principal",
      // Audio lives on audio-main when the source has an audio stream. Keeping
      // the video track muted prevents render adapters from mixing it twice.
      muted: Boolean(ingest.mediaInfo?.audioStreams?.length),
      locked: false,
      clips: [sourceClip],
    },
  ];
  if (ingest.mediaInfo?.audioStreams?.length) {
    tracks?.push({
      id: "audio-main",
      kind: "audio",
      name: "Áudio original",
      muted: false,
      locked: false,
      clips: [
        {
          ...sourceClip,
          id: `audio-${crypto.randomUUID()}`,
          transform: {},
          gainDb: 0,
          pan: 0,
          fadeInFrames: 0,
          fadeOutFrames: 0,
        },
      ],
    });
  }

  return {
    workspaceId: options.workspaceId!,
    title: options.title,
    contentType: "video",
    campaignId: options.campaignId ?? null,
    postId: options.postId ?? null,
    opportunityId: null,
    brandRevision: options.brandRevision,
    brief: {
      schemaVersion: "studio.creative-brief.v1",
      objective: options.objective,
      audience: options.audience,
      angle: "UGC direto, humano e confiável",
      promise: "Transformar um take real em uma peça pronta para revisão",
      hook: options.title,
      cta: "Conheça a marca",
      channel: "instagram",
      format: "reel-vertical",
      tone: options.tone,
      restrictions: ["Não publicar sem revisão humana"],
      hypotheses: ["Uma abertura curta aumenta a retenção inicial"],
      evidence: [],
    },
    composition: {
      pages: [
        {
          id: "scene-main",
          role: "ugc-main",
          width: 1080,
          height: 1920,
          safeArea: 96,
          background: "#090b0d",
          durationMs,
          layers: [
            {
              id: "brand-band",
              kind: "shape",
              name: "Faixa da marca",
              x: 72,
              y: 1640,
              width: 936,
              height: 150,
              rotation: 0,
              opacity: 0.94,
              visible: true,
              locked: false,
              zIndex: 10,
              properties: {
                type: "shape",
                shape: "rectangle",
                fill: options.primaryColor,
                radius: 32,
              },
            },
            {
              id: "brand-cta",
              kind: "text",
              name: "CTA da marca",
              x: 120,
              y: 1674,
              width: 840,
              height: 86,
              rotation: 0,
              opacity: 1,
              visible: true,
              locked: false,
              zIndex: 11,
              properties: {
                type: "text",
                text: "Conheça a marca",
                fontSize: 48,
                minFontSize: 24,
                fontFamily: "Liberation Sans",
                fontWeight: "bold",
                color: "#ffffff",
                align: "center",
                lineHeight: 1.05,
              },
            },
          ],
        },
      ],
      narrative: {
        mode: "ugc-assisted",
        sourceAssetId: asset.id,
        originalPreserved: true,
        audioMode: "source-audio-unverified",
        naturalSoundPolicy: "required-before-approval",
        voicePolicy: "prohibited",
        musicPolicy: "prohibited",
      },
      tracks: [],
      mediaTimeline: {
        schemaVersion: "studio.media-timeline.v1",
        frameRate: frameRateFrom(ingest),
        durationFrames,
        tracks,
      },
    },
    assets: [
      {
        id: asset.id,
        version: 1,
        mediaType: asset.mediaType ?? "video/mp4",
        checksum: asset.checksumSha256 ?? null,
        origin: "workspace",
        rightsStatus: "unknown",
        provenance: {
          source: "user-upload",
          originalFilename: asset.title,
          ingestId: ingest.id,
        },
      },
    ],
    correlationId: crypto.randomUUID(),
  };
}

function appendVideoAssetToDocument(
  current: StudioDocumentRecord,
  asset: AssetRecord,
  ingest: StudioMediaIngestRecord,
): StudioDocumentInput {
  const timeline = structuredClone(current.composition.mediaTimeline);
  if (!timeline) throw new Error("A timeline canônica ainda não está disponível.");
  const rate = timeline.frameRate ?? { numerator: 30, denominator: 1 };
  const durationMicroseconds = ingest.mediaInfo?.durationMicroseconds ?? 0;
  if (durationMicroseconds <= 0) throw new Error("A nova mídia não possui duração válida.");
  const durationFrames = Math.max(
    1,
    Math.round(
      (durationMicroseconds * rate.numerator) /
        (1_000_000 * rate.denominator),
    ),
  );
  const startFrame = timeline.durationFrames;
  const sourceClip = {
    id: `source-${crypto.randomUUID()}`,
    assetId: asset.id,
    timeline: { startFrame, durationFrames },
    source: { startMicroseconds: 0, durationMicroseconds },
    enabled: true,
    locked: false,
    label: asset.title,
    playbackRate: 1,
    transform: { fit: "cover", anchor: "center" },
    effects: [],
    keyframes: [],
  };
  const videoTrack = timeline.tracks?.find(
    (track) => track.kind === "video" && track.id === "video-main",
  );
  if (!videoTrack || videoTrack.kind !== "video") {
    throw new Error("A trilha principal de vídeo não está disponível.");
  }
  videoTrack.clips = [...(videoTrack.clips ?? []), sourceClip];

  if (ingest.mediaInfo?.audioStreams?.length) {
    const audioClip = {
      ...sourceClip,
      id: `audio-${crypto.randomUUID()}`,
      transform: {},
      gainDb: 0,
      pan: 0,
      fadeInFrames: 0,
      fadeOutFrames: 0,
    };
    const audioTrack = timeline.tracks?.find(
      (track) => track.kind === "audio" && track.id === "audio-main",
    );
    if (audioTrack?.kind === "audio") {
      audioTrack.clips = [...(audioTrack.clips ?? []), audioClip];
    } else {
      timeline.tracks = [
        ...(timeline.tracks ?? []),
        {
          id: "audio-main",
          kind: "audio",
          name: "Áudio original",
          muted: false,
          locked: false,
          clips: [audioClip],
        },
      ];
    }
    videoTrack.muted = true;
  }
  timeline.durationFrames += durationFrames;
  const durationMs = Math.max(
    1,
    Math.round(
      (timeline.durationFrames * rate.denominator * 1_000) / rate.numerator,
    ),
  );
  return {
    ...current,
    composition: {
      ...current.composition,
      pages: current.composition.pages.map((page, index) =>
        index === 0 ? { ...page, durationMs } : page,
      ),
      narrative: {
        ...current.composition.narrative,
        sourceAssetIds: [
          ...new Set([
            ...(typeof current.composition.narrative?.sourceAssetId === "string"
              ? [current.composition.narrative.sourceAssetId]
              : []),
            ...(Array.isArray(current.composition.narrative?.sourceAssetIds)
              ? current.composition.narrative.sourceAssetIds.filter(
                  (value): value is string => typeof value === "string",
                )
              : []),
            asset.id,
          ]),
        ],
      },
      mediaTimeline: timeline,
    },
    assets: [
      ...current.assets.filter((candidate) => candidate.id !== asset.id),
      {
        id: asset.id,
        version: 1,
        mediaType: asset.mediaType ?? "video/mp4",
        checksum: asset.checksumSha256 ?? null,
        origin: "workspace",
        rightsStatus: "unknown",
        provenance: {
          source: "user-upload",
          originalFilename: asset.title,
          ingestId: ingest.id,
        },
      },
    ],
  } as StudioDocumentInput;
}

export function useVideoStudio(options: VideoStudioOptions) {
  const { enabled, workspaceId, postId, campaignId } = options;
  const [document, setDocument] = React.useState<StudioDocumentRecord>();
  const [asset, setAsset] = React.useState<AssetRecord>();
  const [ingest, setIngest] = React.useState<StudioMediaIngestRecord>();
  const soundUploadRef = React.useRef<{ file: File; workspaceId: string; asset: AssetRecord; ingest?: StudioMediaIngestRecord }>();
  const [soundUndo, setSoundUndo] = React.useState<{ before: StudioDocumentRecord; revision: number; version: number }>();
  const undoHistoryRef = React.useRef<StudioHistoryEntry[]>([]);
  const redoHistoryRef = React.useRef<StudioHistoryEntry[]>([]);
  const [historyRevision, setHistoryRevision] = React.useState(0);
  const [transcript, setTranscript] = React.useState<StudioTranscriptRecord>();
  const [decisionSet, setDecisionSet] = React.useState<StudioEditDecisionRecord>();
  const [job, setJob] = React.useState<StudioGenerationJobRecord>();
  const [renderJob, setRenderJob] = React.useState<StudioGenerationJobRecord>();
  const [creativeCasebook, setCreativeCasebook] = React.useState<StudioCreativeCasebookRecord>();
  const [assistedIntelligence, setAssistedIntelligence] = React.useState<StudioAssistedIntelligenceSuiteRecord>();
  const [videoFactoryProgram, setVideoFactoryProgram] = React.useState<StudioVideoFactoryProgramRecord>();
  const [creativeReplanState, setCreativeReplanState] = React.useState<StudioCreativeReplanStateRecord>();
  const [advancedCapabilityAudit, setAdvancedCapabilityAudit] = React.useState<StudioAdvancedCapabilityAuditRecord>();
  const [videoAutonomyAudit, setVideoAutonomyAudit] = React.useState<StudioVideoAutonomyAuditRecord>();
  const [waveform, setWaveform] = React.useState<AudioWaveformManifest>();
  const [previewUrl, setPreviewUrl] = React.useState<string>();
  const [previewUrlsByAssetId, setPreviewUrlsByAssetId] = React.useState<Record<string, string>>({});
  const [renderPreviewUrl, setRenderPreviewUrl] = React.useState<string>();
  const [animaticPreviewUrl, setAnimaticPreviewUrl] = React.useState<string>();
  const [status, setStatus] = React.useState<VideoStudioStatus>("idle");
  const [operation, setOperation] = React.useState<string>();
  const [error, setError] = React.useState<string>();
  const previewUrlRef = React.useRef<string>();
  const previewUrlsRef = React.useRef<Record<string, string>>({});
  const renderUrlRef = React.useRef<string>();
  const animaticUrlRef = React.useRef<string>();
  const documentRef = React.useRef<StudioDocumentRecord>();
  const jobRef = React.useRef<StudioGenerationJobRecord>();
  const adoptedAssetRef = React.useRef<string>();
  const documentVideoAssetIds = React.useMemo(
    () =>
      (document?.assets ?? [])
        .filter((reference) => reference.mediaType.startsWith("video/"))
        .map((reference) => reference.id)
        .sort(),
    [document?.assets],
  );

  React.useEffect(() => {
    documentRef.current = document;
  }, [document]);

  const recordUndoSnapshot = React.useCallback(
    (before: StudioDocumentRecord, appliesToRevision: number) => {
      undoHistoryRef.current = [
        ...undoHistoryRef.current,
        { snapshot: structuredClone(before), appliesToRevision },
      ].slice(-20);
      redoHistoryRef.current = [];
      setHistoryRevision((value) => value + 1);
    },
    [],
  );

  React.useEffect(() => {
    jobRef.current = job;
  }, [job]);

  const replacePreview = React.useCallback(async (assetId: string) => {
    const existing = previewUrlsRef.current[assetId];
    if (existing) {
      previewUrlRef.current = existing;
      setPreviewUrl(existing);
      return;
    }
    const blob = await productApi.studioAssetBlob(assetId);
    const nextUrl = URL.createObjectURL(blob);
    previewUrlsRef.current = { ...previewUrlsRef.current, [assetId]: nextUrl };
    previewUrlRef.current = nextUrl;
    setPreviewUrlsByAssetId(previewUrlsRef.current);
    setPreviewUrl(nextUrl);
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    const missing = documentVideoAssetIds.filter(
      (assetId) => !previewUrlsRef.current[assetId],
    );
    if (!missing.length) return;
    void Promise.all(
      missing.map(async (assetId) => {
        const blob = await productApi.studioAssetBlob(assetId);
        const url = URL.createObjectURL(blob);
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        previewUrlsRef.current = { ...previewUrlsRef.current, [assetId]: url };
      }),
    )
      .then(() => {
        if (!cancelled) setPreviewUrlsByAssetId({ ...previewUrlsRef.current });
      })
      .catch(() => {
        // A missing preview remains visible as a governed media-bin placeholder.
      });
    return () => {
      cancelled = true;
    };
  }, [documentVideoAssetIds]);

  React.useEffect(
    () => () => {
      Object.values(previewUrlsRef.current).forEach((url) => URL.revokeObjectURL(String(url)));
      if (renderUrlRef.current) URL.revokeObjectURL(renderUrlRef.current);
      if (animaticUrlRef.current) URL.revokeObjectURL(animaticUrlRef.current);
    },
    [],
  );

  const loadWaveform = React.useCallback(async (assetId?: string | null) => {
    if (!assetId) {
      setWaveform(undefined);
      return;
    }
    setWaveform(
      await productApi.studioAssetJson<AudioWaveformManifest>(assetId),
    );
  }, []);

  const replaceRenderPreview = React.useCallback(async (assetId: string) => {
    const blob = await productApi.studioAssetBlob(assetId);
    const nextUrl = URL.createObjectURL(blob);
    if (renderUrlRef.current) URL.revokeObjectURL(renderUrlRef.current);
    renderUrlRef.current = nextUrl;
    setRenderPreviewUrl(nextUrl);
  }, []);

  const clearRenderPreview = React.useCallback(() => {
    if (renderUrlRef.current) URL.revokeObjectURL(renderUrlRef.current);
    renderUrlRef.current = undefined;
    setRenderPreviewUrl(undefined);
  }, []);

  const loadCreativeAnimatic = React.useCallback(async (caseId: string) => {
    const blob = await productApi.studioCreativeAnimatic(caseId);
    const nextUrl = URL.createObjectURL(blob);
    if (animaticUrlRef.current) URL.revokeObjectURL(animaticUrlRef.current);
    animaticUrlRef.current = nextUrl;
    setAnimaticPreviewUrl(nextUrl);
    return nextUrl;
  }, []);

  const loadRelated = React.useCallback(
    async (nextIngest?: StudioMediaIngestRecord) => {
      if (!workspaceId || !nextIngest) {
        setTranscript(undefined);
        setDecisionSet(undefined);
        return;
      }
      const [transcripts, decisions] = await Promise.all([
        productApi.studioTranscripts(workspaceId, nextIngest.id),
        productApi.studioEditDecisionSets(workspaceId, nextIngest.id),
      ]);
      setTranscript(transcripts[0]);
      setDecisionSet(decisions[0]);
    },
    [workspaceId],
  );

  const refresh = React.useCallback(async () => {
    if (!enabled || !workspaceId) return;
    setStatus("loading");
    setError(undefined);
    try {
      const [documents, ingests, nextCasebook, nextAssistedIntelligence, nextFactoryProgram, nextReplanState, nextAdvancedAudit, nextAutonomyAudit] = await Promise.all([
        productApi.studioDocuments(workspaceId, {
          postId,
          campaignId,
        }),
        productApi.studioMediaIngests(workspaceId),
        productApi.studioCreativeCasebook(),
        productApi.studioAssistedIntelligence(),
        productApi.studioVideoFactoryProgram(),
        productApi.studioCreativeReplanState(),
        productApi.studioAdvancedCapabilityAudit(),
        productApi.studioVideoAutonomyAudit(),
      ]);
      const nextDocument = documents.find(
        (candidate) => candidate.contentType === "video",
      );
      const recoveredRenderJobs = nextDocument
        ? await productApi.studioGenerationJobs(workspaceId, {
            documentId: nextDocument.documentId,
            jobType: "video_render",
            limit: 1,
          })
        : [];
      const recoveredRenderJob = recoveredRenderJobs[0];
      const sourceAssetId = nextDocument?.composition.narrative?.sourceAssetId as string | undefined
        ?? nextDocument?.assets?.[0]?.id;
      const nextIngest = sourceAssetId
        ? ingests.find((candidate) => candidate.assetId === sourceAssetId)
        : ingests.find((candidate) => candidate.mediaInfo?.videoStreams?.length);
      setDocument(nextDocument);
      setIngest(nextIngest);
      setRenderJob(recoveredRenderJob);
      setCreativeCasebook(nextCasebook);
      setAssistedIntelligence(nextAssistedIntelligence);
      setVideoFactoryProgram(nextFactoryProgram);
      setCreativeReplanState(nextReplanState);
      setAdvancedCapabilityAudit(nextAdvancedAudit);
      setVideoAutonomyAudit(nextAutonomyAudit);
      if (
        recoveredRenderJob &&
        (!jobRef.current ||
          !["queued", "running", "retrying", "cancel_requested"].includes(
            jobRef.current.status,
          ))
      ) {
        setJob(recoveredRenderJob);
      }
      await loadRelated(nextIngest);
      if (nextIngest) {
        await replacePreview(nextIngest.proxyAssetId ?? nextIngest.assetId);
        await loadWaveform(nextIngest.waveformAssetId);
      }
      const recoveredResult = recoveredRenderJob?.result as
        | { artifact?: { assetId?: string } }
        | null
        | undefined;
      if (recoveredRenderJob?.status === "succeeded" && recoveredResult?.artifact?.assetId) {
        await replaceRenderPreview(recoveredResult.artifact.assetId);
      } else {
        clearRenderPreview();
      }
      setStatus("ready");
    } catch (requestError) {
      setError(messageFrom(requestError));
      setStatus("error");
    }
  }, [
    campaignId,
    clearRenderPreview,
    enabled,
    loadRelated,
    loadWaveform,
    postId,
    replacePreview,
    replaceRenderPreview,
    workspaceId,
  ]);

  React.useEffect(() => {
    if (!enabled || !workspaceId) {
      setStatus("idle");
      return;
    }
    void refresh();
  }, [enabled, refresh, workspaceId]);

  const run = React.useCallback(
    async <T,>(label: string, action: () => Promise<T>) => {
      setOperation(label);
      setStatus("working");
      setError(undefined);
      try {
        const result = await action();
        setStatus("ready");
        return result;
      } catch (requestError) {
        setError(messageFrom(requestError));
        setStatus("error");
        throw requestError;
      } finally {
        setOperation(undefined);
      }
    },
    [],
  );

  const pollIngest = React.useCallback(
    async (ingestId: string) => {
      for (let attempt = 0; attempt < 10; attempt += 1) {
        const current = await productApi.studioMediaIngest(ingestId);
        setIngest(current);
        if (!["pending", "probing"].includes(current.status)) return current;
        await new Promise((resolve) => window.setTimeout(resolve, 1_200));
      }
      return productApi.studioMediaIngest(ingestId);
    },
    [],
  );

  const upload = React.useCallback(
    async (file: File) =>
      run("upload", async () => {
        if (!options.workspaceId)
          throw new Error("Selecione um workspace antes de enviar a mídia.");
        const nextAsset = await productApi.uploadStudioAsset(
          options.workspaceId,
          file,
        );
        setAsset(nextAsset);
        await replacePreview(nextAsset.id);
        const queued = await productApi.enqueueStudioMediaIngest(
          { workspaceId: options.workspaceId, assetId: nextAsset.id },
          `media-ingest-${crypto.randomUUID()}`,
        );
        setIngest(queued);
        const processed = await pollIngest(queued.id);
        setIngest(processed);
        if (processed.status === "ready") {
          const current = documentRef.current;
          const nextDocument = current?.composition.mediaTimeline
            ? await productApi.replaceStudioDocument(
                current.documentId,
                current.revision,
                appendVideoAssetToDocument(current, nextAsset, processed),
              )
            : await productApi.createStudioDocument(
                createVideoDocumentInput(options, nextAsset, processed),
              );
          if (current) recordUndoSnapshot(current, nextDocument.revision);
          documentRef.current = nextDocument;
          setDocument(nextDocument);
          await loadRelated(processed);
        }
        return processed;
      }),
    [loadRelated, options, pollIngest, recordUndoSnapshot, replacePreview, run],
  );

  const adoptAsset = React.useCallback(
    async (nextAsset: AssetRecord) =>
      run("adopt-asset", async () => {
        if (!options.workspaceId)
          throw new Error("Selecione um workspace antes de abrir a amostra.");
        if (!nextAsset.mediaType?.startsWith("video/"))
          throw new Error("O handoff do Presenter não aponta para um vídeo válido.");
        setAsset(nextAsset);
        await replacePreview(nextAsset.id);
        const ingests = await productApi.studioMediaIngests(options.workspaceId);
        let nextIngest = ingests.find((candidate) => candidate.assetId === nextAsset.id);
        if (!nextIngest) {
          nextIngest = await productApi.enqueueStudioMediaIngest(
            { workspaceId: options.workspaceId, assetId: nextAsset.id },
            `media-ingest-${crypto.randomUUID()}`,
          );
        }
        setIngest(nextIngest);
        const processed = ["pending", "probing"].includes(nextIngest.status)
          ? await pollIngest(nextIngest.id)
          : nextIngest;
        setIngest(processed);
        if (processed.status !== "ready")
          throw new Error("A amostra do Presenter não passou pela ingestão técnica.");
        let nextDocument = documentRef.current;
        if (!nextDocument || nextDocument.assets?.[0]?.id !== nextAsset.id) {
          nextDocument = await productApi.createStudioDocument(
            createVideoDocumentInput(options, nextAsset, processed),
          );
          documentRef.current = nextDocument;
          setDocument(nextDocument);
        }
        await loadRelated(processed);
        return processed;
      }),
    [loadRelated, options, pollIngest, replacePreview, run],
  );

  React.useEffect(() => {
    const initialAsset = options.initialAsset;
    if (
      !enabled ||
      status !== "ready" ||
      !initialAsset ||
      adoptedAssetRef.current === initialAsset.id ||
      document?.assets?.[0]?.id === initialAsset.id
    ) return;
    adoptedAssetRef.current = initialAsset.id;
    void adoptAsset(initialAsset).catch(() => {
      adoptedAssetRef.current = undefined;
    });
  }, [adoptAsset, document?.assets, enabled, options.initialAsset, status]);

  const applyEditorialCaptions = React.useCallback(
    async (text: string) =>
      run("captions", async () => {
        const current = documentRef.current;
        const currentTimeline = current?.composition.mediaTimeline;
        if (!options.workspaceId || !ingest || !current || !currentTimeline)
          throw new Error("Conclua a ingestão e crie o projeto antes das legendas.");
        const lines = text
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter(Boolean);
        if (!lines.length) throw new Error("Escreva ao menos uma linha de legenda.");
        if (lines.length > currentTimeline.durationFrames) {
          throw new Error("Há mais linhas de legenda do que frames disponíveis no take.");
        }
        const captionTrack = {
          id: "captions-main",
          kind: "caption" as const,
          name: "Legendas editoriais PT-BR",
          locale: "pt-BR",
          locked: false,
          cues: lines.map((line, index) => {
            const startFrame = Math.floor(
              (index * currentTimeline.durationFrames) / lines.length,
            );
            const endFrame = Math.floor(
              ((index + 1) * currentTimeline.durationFrames) / lines.length,
            );
            return {
              id: `editorial-caption-${index + 1}`,
              timeline: {
                startFrame,
                durationFrames: endFrame - startFrame,
              },
              text: line,
              speaker: null,
              sourceSegmentId: null,
              confidence: null,
              style: {
              schemaVersion: "studio.caption-render-style.v1",
              position: "lower-third",
              color: "#ffffff",
              fontSize: 56,
              fontFamily: "Liberation Sans",
              fontWeight: "bold",
              outlineColor: "#000000",
              outlineWidth: 4,
              maxLines: 3,
              },
            };
          }),
        };
        const nextDocument = {
          ...current,
          composition: {
            ...current.composition,
            narrative: {
              ...(current.composition.narrative ?? {}),
              captionMode: "editorial",
              speechExpected: false,
            },
            mediaTimeline: {
              ...currentTimeline,
              tracks: [
                ...(currentTimeline.tracks ?? []).filter(
                  (track) => track.id !== captionTrack.id,
                ),
                captionTrack,
              ],
            },
          },
        } as StudioDocumentInput;
        try {
          const saved = await productApi.replaceStudioDocument(
            current.documentId,
            current.revision,
            nextDocument,
          );
          documentRef.current = saved;
          setDocument(saved);
          return saved;
        } catch (requestError) {
          if (
            requestError instanceof BackendRequestError &&
            requestError.status === 409
          ) {
            await refresh();
            throw new Error(
              "As legendas mudaram em outra sessão. Recarregamos a revisão atual; revise e aplique novamente.",
            );
          }
          throw requestError;
        }
      }),
    [ingest, options.workspaceId, refresh, run],
  );

  const applyCut = React.useCallback(
    async (startSeconds: number, endSeconds: number) =>
      run("cut", async () => {
        if (!options.workspaceId || !ingest || !document)
          throw new Error("Conclua a ingestão antes de aplicar um corte.");
        if (startSeconds < 0 || endSeconds <= startSeconds)
          throw new Error("O fim do corte precisa ser maior que o início.");
        const durationSeconds =
          (ingest.mediaInfo?.durationMicroseconds ?? 0) / 1_000_000;
        if (durationSeconds && endSeconds > durationSeconds)
          throw new Error("O corte ultrapassa a duração da mídia.");
        const nextDecisionSet = await productApi.createStudioEditDecisionSet(
          {
            workspaceId: options.workspaceId,
            mediaIngestId: ingest.id,
            transcriptId: transcript?.id ?? null,
            documentId: document.documentId,
            decisions: [
              {
                id: `cut-${crypto.randomUUID()}`,
                operation: "remove",
                startMicroseconds: Math.round(startSeconds * 1_000_000),
                endMicroseconds: Math.round(endSeconds * 1_000_000),
                status: "accepted",
                reason: "Corte manual no Video Studio",
                confidence: null,
                source: "manual",
              },
            ],
          },
          `edit-decision-${crypto.randomUUID()}`,
        );
        setDecisionSet(nextDecisionSet);
        const updated = await productApi.applyStudioEditDecisionSet(
          nextDecisionSet.id,
          {
            documentId: document.documentId,
            expectedDocumentRevision: document.revision,
            expectedDecisionRevision: nextDecisionSet.revision,
            sourceTrackId: "video-main",
          },
        );
        setDocument(updated);
        setDecisionSet({
          ...nextDecisionSet,
          status: "applied",
          revision: nextDecisionSet.revision + 1,
          version: nextDecisionSet.version + 1,
        });
        return updated;
      }),
    [document, ingest, options.workspaceId, run, transcript?.id],
  );

  const persistTimeline = React.useCallback(
    async (transform: (input: VideoTimeline) => VideoTimeline) =>
      run("timeline", async () => {
        const current = documentRef.current;
        const currentTimeline = current?.composition.mediaTimeline;
        if (!current || !currentTimeline)
          throw new Error("A timeline canônica ainda não está disponível.");
        const nextTimeline = transform(currentTimeline);
        const rate = nextTimeline.frameRate ?? { numerator: 30, denominator: 1 };
        const durationMs = Math.max(
          1,
          Math.round(
            (nextTimeline.durationFrames * rate.denominator * 1_000) /
              rate.numerator,
          ),
        );
        const nextDocument = {
          ...current,
          composition: {
            ...current.composition,
            pages: current.composition.pages.map((page, index) =>
              index === 0 ? { ...page, durationMs } : page,
            ),
            mediaTimeline: nextTimeline,
          },
        } as StudioDocumentInput;
        try {
          const saved = await productApi.replaceStudioDocument(
            current.documentId,
            current.revision,
            nextDocument,
          );
          documentRef.current = saved;
          setDocument(saved);
          recordUndoSnapshot(current, saved.revision);
          return saved;
        } catch (requestError) {
          if (
            requestError instanceof BackendRequestError &&
            requestError.status === 409
          ) {
            await refresh();
            throw new Error(
              "A timeline mudou em outra sessão. Recarregamos a revisão atual; repita o gesto.",
            );
          }
          throw requestError;
        }
      }),
    [recordUndoSnapshot, refresh, run],
  );

  const commitTimeline = React.useCallback(
    (command: VideoTimelineCommand) => persistTimeline((input) => applyVideoTimelineCommand(input, command)),
    [persistTimeline],
  );

  const bindCreativeCase = React.useCallback(
    (caseId: string) =>
      run("creative-preproduction", async () => {
        const current = documentRef.current;
        const creativeCase = creativeCasebook?.cases.find(
          (candidate) => candidate.caseId === caseId,
        );
        if (!current) throw new Error("Crie ou abra um documento antes de vincular a pré-produção.");
        if (!creativeCase) throw new Error("O caso criativo selecionado não existe no casebook vigente.");
        const nextDocument = {
          ...current,
          composition: {
            ...current.composition,
            narrative: {
              ...current.composition.narrative,
              creativeCaseId: creativeCase.caseId,
              formatRecipeId: creativeCase.recipe.recipeId,
              formatRouteId: creativeCase.formatRoute.routeId,
              storyboardId: creativeCase.storyboard.storyboardId,
              animaticId: creativeCase.animatic.animaticId,
              expensiveRenderEligible: false,
            },
          },
        } as StudioDocumentInput;
        const saved = await productApi.replaceStudioDocument(
          current.documentId,
          current.revision,
          nextDocument,
        );
        documentRef.current = saved;
        setDocument(saved);
        recordUndoSnapshot(current, saved.revision);
        return saved;
      }),
    [creativeCasebook?.cases, recordUndoSnapshot, run],
  );

  const reviewAssistedProposal = React.useCallback(
    (caseId: string, decisions: AssistedOperationDecisionInput[]) =>
      run("assisted-intelligence-review", async () => {
        const current = documentRef.current;
        const assistance = assistedIntelligence?.cases.find(
          (candidate) => candidate.caseId === caseId,
        );
        if (!current) throw new Error("Crie ou abra um documento antes de revisar sugestões.");
        if (!assistance) throw new Error("A assistência selecionada não existe na suite vigente.");
        const operationIds = assistance.proposal.operations.map((item) => item.operationId);
        if (
          decisions.length !== operationIds.length
          || new Set(decisions.map((item) => item.operationId)).size !== operationIds.length
          || !operationIds.every((operationId) => decisions.some((item) => item.operationId === operationId))
        ) {
          throw new Error("Aceite, rejeite ou ajuste cada operação antes de confirmar.");
        }
        const nextDocument = {
          ...current,
          composition: {
            ...current.composition,
            narrative: {
              ...current.composition.narrative,
              assistedIntelligence: {
                suiteId: assistedIntelligence?.suiteId,
                caseId,
                optionSetId: assistance.optionSet.optionSetId,
                selectedOptionId: assistance.optionSet.selectedOptionId,
                repairId: assistance.optionSet.repair?.repairId,
                proposalId: assistance.proposal.proposalId,
                proposalDigestSha256: assistance.reviewedPlan.proposalDigestSha256,
                sourceDocumentRevision: current.revision,
                inverseSnapshotRevision: current.revision,
                decisions,
                humanConfirmed: true,
              },
            },
          },
        } as StudioDocumentInput;
        const saved = await productApi.replaceStudioDocument(
          current.documentId,
          current.revision,
          nextDocument,
        );
        documentRef.current = saved;
        setDocument(saved);
        recordUndoSnapshot(current, saved.revision);
        return saved;
      }),
    [assistedIntelligence, recordUndoSnapshot, run],
  );

  const restoreStudioHistory = React.useCallback(
    (direction: "undo" | "redo") =>
      run(`timeline-${direction}`, async () => {
        const current = documentRef.current;
        if (!current) throw new Error("O documento ainda não está disponível.");
        const source = direction === "undo" ? undoHistoryRef.current : redoHistoryRef.current;
        const destination = direction === "undo" ? redoHistoryRef.current : undoHistoryRef.current;
        const entry = source[source.length - 1];
        if (!entry || entry.appliesToRevision !== current.revision) {
          throw new Error(
            direction === "undo"
              ? "Não há uma edição local segura para desfazer."
              : "Não há uma edição local segura para refazer.",
          );
        }
        source.pop();
        const saved = await productApi.replaceStudioDocument(
          current.documentId,
          current.revision,
          entry.snapshot as StudioDocumentInput,
        );
        destination.push({
          snapshot: structuredClone(current),
          appliesToRevision: saved.revision,
        });
        if (destination.length > 20) destination.splice(0, destination.length - 20);
        const nextSource = source[source.length - 1];
        if (nextSource) nextSource.appliesToRevision = saved.revision;
        documentRef.current = saved;
        setDocument(saved);
        setSoundUndo(undefined);
        clearRenderPreview();
        setHistoryRevision((value) => value + 1);
        return saved;
      }),
    [clearRenderPreview, run],
  );

  const undoTimeline = React.useCallback(
    () => restoreStudioHistory("undo"),
    [restoreStudioHistory],
  );

  const redoTimeline = React.useCallback(
    () => restoreStudioHistory("redo"),
    [restoreStudioHistory],
  );

  const muteOriginalAudio = React.useCallback(
    (muted: boolean) => persistTimeline((input) => setOriginalAudioMuted(input, muted)),
    [persistTimeline],
  );

  const saveNaturalSound = React.useCallback(
    (file: File | undefined, source: string, license: string, placement: NaturalSoundPlacement,
      clipId = "natural-sound-main", reuseAssetId?: string) =>
      run("natural-sound", async () => {
        const current = documentRef.current;
        if (!options.workspaceId || !current?.composition.mediaTimeline)
          throw new Error("Adicione um take antes do som natural.");
        if (!source.trim() || !license.trim()) throw new Error("Informe origem/autoria e licença do som. São declarações ainda não verificadas.");
        const oldTrack = current.composition.mediaTimeline.tracks?.find((track) => track.id === NATURAL_SOUND_TRACK_ID);
        const oldIds = new Set(oldTrack?.kind === "audio" ? oldTrack.clips?.map((clip) => clip.assetId) : []);
        const oldClip = oldTrack?.kind === "audio" ? oldTrack.clips?.find((clip) => clip.id === clipId) : undefined;
        let ref = current.assets.find((candidate) => candidate.id === (reuseAssetId || oldClip?.assetId)
          && candidate.provenance?.purpose === "natural-sound-candidate");
        let durationUs = Number(ref?.provenance?.durationMicroseconds);
        if (file) {
          if (!/\.(wav|mp3|flac)$/i.test(file.name) || file.size > 20 * 1024 * 1024)
            throw new Error("Use WAV, MP3 ou FLAC de até 20 MB.");
          if (soundUploadRef.current?.file !== file || soundUploadRef.current.workspaceId !== options.workspaceId) {
            const uploaded = await productApi.uploadStudioAsset(options.workspaceId, file);
            soundUploadRef.current = { file, workspaceId: options.workspaceId, asset: uploaded };
          }
          const cached = soundUploadRef.current;
          let soundIngest = cached.ingest ?? await productApi.enqueueStudioMediaIngest(
            { workspaceId: options.workspaceId, assetId: cached.asset.id }, `sound-ingest-${cached.asset.id}`,
          );
          cached.ingest = soundIngest;
          if (soundIngest.status === "failed" && soundIngest.generationJobId) {
            const failedJob = await productApi.studioGenerationJob(soundIngest.generationJobId);
            if (["failed", "cancelled"].includes(failedJob.status)) {
              await productApi.retryStudioGenerationJob(failedJob.id);
              soundIngest = await productApi.studioMediaIngest(soundIngest.id);
              cached.ingest = soundIngest;
            }
          }
          for (let attempt = 0; attempt < 10 && ["pending", "probing"].includes(soundIngest.status); attempt += 1) {
            await new Promise((resolve) => window.setTimeout(resolve, 1_200));
            soundIngest = await productApi.studioMediaIngest(soundIngest.id);
            cached.ingest = soundIngest;
          }
          if (soundIngest.status !== "ready" || soundIngest.mediaInfo?.videoStreams?.length
            || soundIngest.mediaInfo?.audioStreams?.length !== 1) {
            throw new Error("O som ainda não está pronto ou não contém uma única stream de áudio. Repita após a análise; o upload foi preservado nesta sessão.");
          }
          durationUs = soundIngest.mediaInfo.durationMicroseconds;
          ref = {
            id: cached.asset.id, version: 1, mediaType: cached.asset.mediaType ?? "audio/wav",
            checksum: cached.asset.checksumSha256, origin: "workspace", rightsStatus: "unknown",
            provenance: { source: "user-upload", originalFilename: cached.asset.title, ingestId: soundIngest.id },
          };
        }
        if (!ref) throw new Error("Escolha o arquivo de som natural.");
        const mediaTimeline = placeNaturalSound(current.composition.mediaTimeline, ref.id, durationUs, placement, clipId);
        const nextRef = { ...ref, rightsStatus: "unknown" as const, provenance: {
          ...ref.provenance, purpose: "natural-sound-candidate", durationMicroseconds: durationUs,
          sourceDeclaration: source.trim(), licenseDeclaration: license.trim(), humanListeningStatus: "pending",
        } };
        const usedIds = new Set(mediaTimeline.tracks?.flatMap((track) => "clips" in track ? track.clips?.map((clip) => clip.assetId) ?? [] : []));
        const nextAssets = [...current.assets.filter((item) => item.id !== ref!.id && (!oldIds.has(item.id) || usedIds.has(item.id))), nextRef];
        if (nextAssets.length > 9) throw new Error("Este render suporta oito arquivos de som além do take. Reutilize um arquivo já importado.");
        try {
          const saved = await productApi.replaceStudioDocument(current.documentId, current.revision, {
            ...current,
            assets: nextAssets,
            composition: { ...current.composition, mediaTimeline, narrative: {
              ...current.composition.narrative, naturalSoundPolicy: "required-before-approval", voicePolicy: "prohibited", musicPolicy: "prohibited",
            } },
          } as StudioDocumentInput);
          documentRef.current = saved;
          setDocument(saved);
          setSoundUndo({ before: current, revision: saved.revision, version: saved.version });
          return saved;
        } catch (requestError) {
          if (requestError instanceof BackendRequestError && requestError.status === 409) {
            await refresh();
            throw new Error("A timeline mudou em outra sessão. Recarregamos a revisão atual; repita a aplicação do som.");
          }
          throw requestError;
        }
      }),
    [options.workspaceId, refresh, run],
  );

  const toggleNaturalSound = React.useCallback(async (clipId: string, enabled: boolean) => {
    const before = documentRef.current;
    const saved = await persistTimeline((input) => setNaturalSoundEnabled(input, clipId, enabled));
    if (before) setSoundUndo({ before, revision: saved.revision, version: saved.version });
    return saved;
  }, [persistTimeline]);

  const reviewNaturalSoundRights = React.useCallback(
    async (
      assetId: string,
      input: Omit<StudioAssetRightsReviewInput, "expectedDocumentRevision" | "assetChecksumSha256">,
      idempotencyKey: string,
    ) => run("natural-sound-rights", async () => {
      const current = documentRef.current;
      const reference = current?.assets.find((candidate) => candidate.id === assetId
        && candidate.provenance?.purpose === "natural-sound-candidate");
      if (!current || !reference?.checksum) throw new Error("O som natural não está disponível nesta revisão.");
      try {
        const result = await productApi.reviewNaturalSoundRights(
          current.documentId,
          assetId,
          {
            ...input,
            expectedDocumentRevision: current.revision,
            assetChecksumSha256: reference.checksum,
          },
          idempotencyKey,
        );
        documentRef.current = result.document;
        setDocument(result.document);
        return result;
      } catch (requestError) {
        if (requestError instanceof BackendRequestError && requestError.status === 403) {
          throw new Error("Somente Owner ou Admin pode confirmar ou restringir direitos de uso.");
        }
        if (requestError instanceof BackendRequestError && requestError.status === 409) {
          await refresh();
          throw new Error("O documento ou a revisão de direitos mudou. Recarregamos o estado atual; confira antes de repetir.");
        }
        throw requestError;
      }
    }),
    [refresh, run],
  );

  const undoNaturalSound = React.useCallback(() => run("natural-sound-undo", async () => {
    const current = documentRef.current;
    if (!soundUndo || !current || current.documentId !== soundUndo.before.documentId
      || current.revision !== soundUndo.revision || current.version !== soundUndo.version) {
      throw new Error("O documento mudou. Desfazer este ajuste não está mais disponível.");
    }
    try {
      const saved = await productApi.replaceStudioDocument(current.documentId, current.revision, {
        ...current, assets: soundUndo.before.assets,
        composition: { ...current.composition, mediaTimeline: soundUndo.before.composition.mediaTimeline },
      } as StudioDocumentInput);
      documentRef.current = saved;
      setDocument(saved);
      setSoundUndo(undefined);
      return saved;
    } catch (requestError) {
      if (requestError instanceof BackendRequestError && requestError.status === 409) {
        setSoundUndo(undefined);
        await refresh();
        throw new Error("A timeline mudou em outra sessão. Recarregamos a revisão atual; nenhum ajuste foi desfeito.");
      }
      throw requestError;
    }
  }), [refresh, run, soundUndo]);

  const createProxy = React.useCallback(
    async () =>
      run("proxy", async () => {
        if (!options.workspaceId || !ingest)
          throw new Error("A mídia precisa estar disponível para criar o proxy.");
        const nextJob = await productApi.enqueueStudioMediaProxy(
          ingest.id,
          {
            workspaceId: options.workspaceId,
            spec: {
              schemaVersion: "studio.media-proxy-spec.v1",
              format: "mp4",
              maxWidth: 1080,
              maxHeight: 1920,
              targetFps: 30,
              videoCodec: "h264",
              audioCodec: "aac",
              quality: "draft",
            },
          },
          `video-proxy-${crypto.randomUUID()}`,
        );
        setJob(nextJob);
        return nextJob;
      }),
    [ingest, options.workspaceId, run],
  );

  const createWaveform = React.useCallback(
    async () =>
      run("waveform", async () => {
        if (!options.workspaceId || !ingest)
          throw new Error("A mídia precisa estar pronta para gerar a waveform.");
        const nextJob = await productApi.enqueueStudioMediaWaveform(
          ingest.id,
          {
            workspaceId: options.workspaceId,
            spec: {
              schemaVersion: "studio.audio-waveform-spec.v1",
              audioStreamIndex: null,
              sampleRate: 48_000,
              pointsPerSecond: 100,
              channelMode: "mono",
              includeRms: true,
            },
          },
          `media-waveform-${crypto.randomUUID()}`,
        );
        setJob(nextJob);
        return nextJob;
      }),
    [ingest, options.workspaceId, run],
  );

  const render = React.useCallback(
    async () =>
      run("render", async () => {
        if (!options.workspaceId || !document)
          throw new Error("Crie o documento de vídeo antes de renderizar.");
        const timelineRate = document.composition.mediaTimeline?.frameRate ?? {
          numerator: 30,
          denominator: 1,
        };
        const nextJob = await productApi.enqueueStudioVideoRender(
          {
            workspaceId: options.workspaceId,
            documentId: document.documentId,
            expectedDocumentRevision: document.revision,
            expectedDocumentVersion: document.version,
            pageIds: document.composition.pages.map((page) => page.id),
            output: {
              schemaVersion: "studio.video-render-spec.v1",
              format: "mp4",
              width: 1080,
              height: 1920,
              fps: timelineRate.numerator / timelineRate.denominator,
              videoCodec: "h264",
              audioCodec: "aac",
              quality: "draft",
            },
            provider: "builtin.ffmpeg-ugc-v1",
            reducedMotion: false,
            correlationId: crypto.randomUUID(),
          },
          `video-render-${crypto.randomUUID()}`,
        );
        setJob(nextJob);
        setRenderJob(nextJob);
        const currentJob = await productApi.studioGenerationJob(nextJob.id);
        setJob(currentJob);
        setRenderJob(currentJob);
        if (currentJob.status === "succeeded") {
          const result = currentJob.result as
            | { artifact?: { assetId?: string } }
            | null
            | undefined;
          if (result?.artifact?.assetId)
            await replaceRenderPreview(result.artifact.assetId);
        }
        return currentJob;
      }),
    [document, options.workspaceId, replaceRenderPreview, run],
  );

  const renderContextual = React.useCallback(async (saved: StudioDocumentRecord, planId: string) =>
    run("render", async () => {
      documentRef.current = saved;
      setDocument(saved);
      const rate = saved.composition.mediaTimeline?.frameRate ?? { numerator: 30, denominator: 1 };
      const page = saved.composition.pages[0];
      const nextJob = await apiFetch<StudioGenerationJobRecord>("/api/v1/studios/v1/video-renders", {
        method: "POST", headers: { "Idempotency-Key": `contextual-render-${planId}-${saved.revision}` },
        body: JSON.stringify({ workspaceId: saved.workspaceId, documentId: saved.documentId,
          expectedDocumentRevision: saved.revision, expectedDocumentVersion: saved.version,
          provider: (saved.composition.narrative?.editorialV2 as { renderer?: string } | undefined)?.renderer
            ?? (saved.composition.narrative?.editorialV2 ? "hyperframes.contextual-v2" : "builtin.ffmpeg-contextual-v1"),
          contextualPlanId: planId, pageIds: [page.id],
          output: { format: "mp4", width: page.width, height: page.height, fps: rate.numerator / rate.denominator,
            videoCodec: "h264", audioCodec: "aac", quality: "draft" } }),
      });
      setJob(nextJob); setRenderJob(nextJob);
      const result = nextJob.result as { artifact?: { assetId?: string } } | undefined;
      if (nextJob.status === "succeeded" && result?.artifact?.assetId) await replaceRenderPreview(result.artifact.assetId);
      return nextJob;
    }), [run, replaceRenderPreview]);

  const refreshJob = React.useCallback(async () => {
    if (!job) return undefined;
    const nextJob = await productApi.studioGenerationJob(job.id);
    setJob(nextJob);
    if (nextJob.jobType === "video_render") setRenderJob(nextJob);
    if (nextJob.status === "succeeded" && nextJob.jobType === "video_render") {
      const result = nextJob.result as
        | { artifact?: { assetId?: string } }
        | null
        | undefined;
      if (result?.artifact?.assetId)
        await replaceRenderPreview(result.artifact.assetId);
    }
    if (nextJob.status === "succeeded" && ingest) {
      const refreshedIngest = await productApi.studioMediaIngest(ingest.id);
      setIngest(refreshedIngest);
      if (refreshedIngest.proxyAssetId)
        await replacePreview(refreshedIngest.proxyAssetId);
      await loadWaveform(refreshedIngest.waveformAssetId);
    }
    return nextJob;
  }, [ingest, job, loadWaveform, replacePreview, replaceRenderPreview]);

  React.useEffect(() => {
    if (!job || !["queued", "running", "retrying"].includes(job.status)) return;
    const timer = window.setTimeout(
      () => void refreshJob().catch(() => undefined),
      900,
    );
    return () => window.clearTimeout(timer);
  }, [job, refreshJob]);

  const cancelJob = React.useCallback(async () => {
    if (!job) return;
    setJob(await productApi.cancelStudioGenerationJob(job.id));
  }, [job]);

  const retryJob = React.useCallback(async () => {
    if (!job) return;
    setJob(await productApi.retryStudioGenerationJob(job.id));
  }, [job]);

  const createVersion = React.useCallback(
    async () =>
      run("version", async () => {
        if (!document) throw new Error("O documento ainda não foi criado.");
        const updated = await productApi.createStudioVersion(
          document.documentId,
          "Checkpoint do Video Studio",
        );
        setDocument(updated);
        return updated;
      }),
    [document, run],
  );

  const requestReview = React.useCallback(
    async () =>
      run("review", async () => {
        if (!document) throw new Error("O documento ainda não foi criado.");
        const result = renderJob?.result as
          | { documentRevision?: number; documentVersion?: number }
          | null
          | undefined;
        if (
          renderJob?.status !== "succeeded" ||
          result?.documentRevision !== document.revision ||
          result?.documentVersion !== document.version
        ) {
          throw new Error(
            "Renderize a revisão atual antes de solicitar a revisão humana.",
          );
        }
        return productApi.requestStudioReview(
          document.documentId,
          "UGC assistido pronto para revisão humana; verificar explicitamente ausência de voz e música e a origem dos sons naturais.",
          renderJob.id,
        );
      }),
    [document, renderJob, run],
  );

  const timeline = document?.composition.mediaTimeline;
  const frameRate = timeline?.frameRate ?? { numerator: 30, denominator: 1 };
  const durationSeconds = timeline
    ? (timeline.durationFrames * frameRate.denominator) / frameRate.numerator
    : (ingest?.mediaInfo?.durationMicroseconds ?? 0) / 1_000_000;

  return {
    document,
    asset,
    ingest,
    transcript,
    decisionSet,
    job,
    renderJob,
    waveform,
    previewUrl,
    previewUrlsByAssetId,
    renderPreviewUrl,
    creativeCasebook,
    assistedIntelligence,
    videoFactoryProgram,
    creativeReplanState,
    advancedCapabilityAudit,
    videoAutonomyAudit,
    animaticPreviewUrl,
    status,
    operation,
    error,
    timeline,
    durationSeconds,
    upload,
    adoptAsset,
    refresh,
    loadCreativeAnimatic,
    applyEditorialCaptions,
    applyCut,
    commitTimeline,
    bindCreativeCase,
    reviewAssistedProposal,
    undoTimeline,
    redoTimeline,
    canUndoTimeline:
      !!historyRevision &&
      undoHistoryRef.current.at(-1)?.appliesToRevision === document?.revision,
    canRedoTimeline:
      !!historyRevision &&
      redoHistoryRef.current.at(-1)?.appliesToRevision === document?.revision,
    muteOriginalAudio,
    saveNaturalSound,
    reviewNaturalSoundRights,
    toggleNaturalSound,
    undoNaturalSound,
    canUndoNaturalSound: !!soundUndo && document?.documentId === soundUndo.before.documentId
      && document?.revision === soundUndo.revision && document?.version === soundUndo.version,
    createProxy,
    createWaveform,
    render,
    refreshJob,
    renderContextual,
    cancelJob,
    retryJob,
    createVersion,
    requestReview,
  };
}

export type VideoTimeline = BackendSchema<"MediaTimelineV1-Output">;
