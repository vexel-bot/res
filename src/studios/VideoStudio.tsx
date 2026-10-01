import React from "react";
import {
  AudioLines,
  Captions,
  CheckCircle2,
  ChevronLeft,
  CircleStop,
  CloudUpload,
  Film,
  GripVertical,
  Layers3,
  LoaderCircle,
  Pause,
  Play,
  RefreshCw,
  Redo2,
  RotateCcw,
  Save,
  Scissors,
  Send,
  SlidersHorizontal,
  Sparkles,
  Upload,
  Undo2,
  Video,
  WandSparkles,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useVideoStudio } from "./useVideoStudio";
import { NaturalSoundPanel } from "./NaturalSoundPanel";
import { ContextualEditingPanel } from "./ContextualEditingPanel";
import { EditorialReviewPanel, type EditorialGateState } from "./EditorialReviewPanel";
import { useNaturalSoundPreview } from "./useNaturalSoundPreview";
import {
  applyVideoTimelineCommand,
  timelineFrameToSourceMicroseconds,
  timelineMicrosecondsToFrame,
  type VideoTimeline,
  type VideoTimelineCommand,
} from "./videoTimeline";
import { experienceActionForId } from "../app/experience/registry";
import { emitExperienceTelemetry } from "../app/experience/telemetry";
import "./video-studio.css";

type AnyRecord = Record<string, any>;

function formatTime(seconds: number) {
  const safe = Math.max(0, Number.isFinite(seconds) ? seconds : 0);
  const minutes = Math.floor(safe / 60);
  const remainder = safe - minutes * 60;
  return `${minutes}:${remainder.toFixed(1).padStart(4, "0")}`;
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    pending: "Na fila",
    probing: "Analisando",
    ready: "Mídia pronta",
    rejected: "Mídia rejeitada",
    failed: "Falhou",
    queued: "Na fila",
    running: "Processando",
    retrying: "Nova tentativa",
    cancel_requested: "Cancelando",
    cancelled: "Cancelado",
    succeeded: "Concluído",
  };
  return status ? labels[status] ?? status : "Aguardando mídia";
}

export function VideoStudio({
  data,
  demo,
  brand,
  pathname,
  navigate,
  setToast,
  params,
}: AnyRecord) {
  const postId = pathname.split("/")[2] || "draft";
  const post = data.snapshot?.posts.find((candidate: AnyRecord) => candidate.id === postId);
  const profile = data.activeWorkspace?.brandProfile;
  const title = post?.title || "Novo vídeo UGC";
  const handoffAssetId = params?.get("sourceAsset") as string | null;
  const handoffAsset = data.snapshot?.assets?.find(
    (candidate: AnyRecord) => candidate.id === handoffAssetId,
  );
  const studio = useVideoStudio({
    enabled: !demo,
    workspaceId: data.activeWorkspace?.id,
    postId: post?.id ?? (postId === "draft" ? undefined : postId),
    campaignId: post?.campaignId ?? undefined,
    title,
    objective: post?.objective || "Criar um anúncio UGC vertical pronto para revisão",
    audience: profile?.targetAudience || "Público da marca",
    tone: profile?.tone || "Humano, direto e autoral",
    brandRevision: Math.max(1, profile?.versions?.length || 1),
    primaryColor: profile?.primaryColor || "#6c5ce7",
    initialAsset: handoffAsset,
  });
  const inputRef = React.useRef<HTMLInputElement>(null);
  const playerRef = React.useRef<HTMLVideoElement>(null);
  const renderedPlayerRef = React.useRef<HTMLVideoElement>(null);
  const trackAreaRef = React.useRef<HTMLDivElement>(null);
  const activeClipIdRef = React.useRef<string>();
  const demoUrlRef = React.useRef<string>();
  const [demoPreview, setDemoPreview] = React.useState<string>();
  const [playing, setPlaying] = React.useState(false);
  const [playheadFrame, setPlayheadFrame] = React.useState(0);
  const [selectedClipId, setSelectedClipId] = React.useState<string>();
  const [selectedCreativeCaseId, setSelectedCreativeCaseId] = React.useState<string>();
  const [assistantDecisions, setAssistantDecisions] = React.useState<Record<string, "accept" | "reject" | "adjust">>({});
  const [assistantAdjustment, setAssistantAdjustment] = React.useState("");
  const [timelineZoom, setTimelineZoom] = React.useState(1);
  const [soundSelectionRequest, setSoundSelectionRequest] = React.useState<{ clipId: string; nonce: number }>();
  const [draftTimeline, setDraftTimeline] = React.useState<VideoTimeline>();
  const [interaction, setInteraction] = React.useState<{
    pointerId: number;
    command: VideoTimelineCommand;
    base: VideoTimeline;
  }>();
  const [inspector, setInspector] = React.useState<
    "preproduction" | "editorial" | "assistant" | "factory" | "captions" | "cuts" | "brand" | "sound" | "render"
  >("captions");
  const [editorialGate, setEditorialGate] = React.useState<EditorialGateState>();
  const editorialRenderBlocked = Boolean(!demo && studio.document && (
    editorialGate?.documentId !== studio.document.documentId ||
    editorialGate?.revision !== studio.document.revision || editorialGate?.blocked
  ));
  const demoCaptionText =
    "Eu achei que produtividade era fazer mais.\nAté perceber que o ritual certo muda tudo.\nConheça a experiência da marca.";
  const [captionText, setCaptionText] = React.useState(demo ? demoCaptionText : "");
  const captionDraftDirtyRef = React.useRef(false);
  const [cutStart, setCutStart] = React.useState("0.0");
  const [cutEnd, setCutEnd] = React.useState("0.8");
  const timeline = studio.timeline;
  const displayTimeline = draftTimeline ?? timeline;
  const soundPreview = useNaturalSoundPreview(
    `${data.activeWorkspace?.id ?? "demo"}/${postId}`,
    displayTimeline, studio.document?.assets ?? [], playerRef,
  );
  const playbackLabel = (play: string, pause: string) => soundPreview.state === "loading" ? "Cancelar carregamento do preview" : playing ? pause : play;
  const timelineRate = displayTimeline?.frameRate ?? {
    numerator: 30,
    denominator: 1,
  };
  const duration = studio.durationSeconds || (demo ? 14.2 : 0);
  const durationFrames =
    displayTimeline?.durationFrames ??
    Math.max(1, Math.round(duration * (timelineRate.numerator / timelineRate.denominator)));
  const currentTime =
    (playheadFrame * timelineRate.denominator) / timelineRate.numerator;
  const videoTracks =
    displayTimeline?.tracks?.filter((track) => track.kind === "video") ?? [];
  const audioTracks =
    displayTimeline?.tracks?.filter((track) => track.kind === "audio") ?? [];
  const originalAudioTracks = audioTracks.filter((track) => track.id !== "audio-natural");
  const originalAudioMuted = originalAudioTracks.length === 0 || originalAudioTracks.every((track) => track.muted);
  const naturalSoundClips = audioTracks.find((track) => track.id === "audio-natural")?.clips ?? [];
  const captionTracks =
    displayTimeline?.tracks?.filter((track) => track.kind === "caption") ?? [];
  const persistedCaptionText = captionTracks[0]?.cues
    ?.map((cue) => cue.text)
    .join("\n") ?? "";
  React.useEffect(() => {
    if (demo || captionDraftDirtyRef.current) return;
    setCaptionText(persistedCaptionText);
  }, [demo, persistedCaptionText, studio.document?.documentId]);
  const previewPage = (studio.document?.composition?.pages?.[0] ?? {
    width: 1080,
    height: 1920,
    layers: [
      {
        id: "brand-band-preview",
        kind: "shape",
        x: 72,
        y: 1640,
        width: 936,
        height: 150,
        opacity: 0.94,
        visible: true,
        properties: {
          shape: "rectangle",
          fill: profile?.primaryColor || "#6c5ce7",
          radius: 32,
        },
      },
      {
        id: "brand-cta-preview",
        kind: "text",
        x: 120,
        y: 1674,
        width: 840,
        height: 86,
        opacity: 1,
        visible: true,
        properties: {
          text: "Conheça a marca",
          fontSize: 48,
          color: "#ffffff",
          align: "center",
        },
      },
    ],
  }) as AnyRecord;
  const previewLayers = (previewPage.layers ?? []).filter(
    (layer: AnyRecord) => layer.visible !== false && Number(layer.opacity ?? 1) > 0,
  );
  const brandShapeLayer = previewLayers.find(
    (layer: AnyRecord) => layer.kind === "shape" && layer.properties?.shape === "rectangle",
  ) as AnyRecord | undefined;
  const brandTextLayer = previewLayers.find(
    (layer: AnyRecord) => layer.kind === "text",
  ) as AnyRecord | undefined;
  const currentCaptionCue = captionTracks
    .flatMap((track) => track.cues ?? [])
    .find(
      (cue: AnyRecord) =>
        cue.timeline.startFrame <= playheadFrame &&
        playheadFrame < cue.timeline.startFrame + cue.timeline.durationFrames,
    ) as AnyRecord | undefined;
  const fallbackCaption = captionText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)[0];
  const previewCaption = currentCaptionCue?.text ?? (demo ? fallbackCaption : "");
  const pageWidth = Number(previewPage.width) || 1080;
  const pageHeight = Number(previewPage.height) || 1920;
  const boxStyle = (layer?: AnyRecord): React.CSSProperties => ({
    left: `${(Number(layer?.x ?? 0) / pageWidth) * 100}%`,
    top: `${(Number(layer?.y ?? 0) / pageHeight) * 100}%`,
    width: `${(Number(layer?.width ?? 0) / pageWidth) * 100}%`,
    height: `${(Number(layer?.height ?? 0) / pageHeight) * 100}%`,
    opacity: Number(layer?.opacity ?? 1),
  });
  const waveformBars = React.useMemo(() => {
    const buckets = studio.waveform?.buckets ?? [];
    if (!buckets.length) return [];
    const count = Math.min(180, buckets.length);
    return Array.from({ length: count }, (_, index) => {
      const bucket = buckets[Math.floor((index / count) * buckets.length)];
      return Math.max(
        0.05,
        Math.min(1, (bucket.maximum - bucket.minimum) / 65_535),
      );
    });
  }, [studio.waveform]);
  const renderResult = studio.renderJob?.result as
    | {
        documentRevision?: number;
        documentVersion?: number;
        artifact?: { assetId?: string; checksumSha256?: string };
        renderedLayerIds?: string[];
        renderedCaptionTrackIds?: string[];
        qualityEvaluation?: {
          status?: "passed" | "failed";
          metrics?: {
            integratedLoudnessLufs?: number;
            truePeakDbfs?: number;
            avDurationDeltaMs?: number;
            blackFrameRatio?: number;
            silenceRatio?: number;
          };
          checks?: Array<{ status?: string; severity?: string }>;
        };
        warnings?: string[];
      }
    | null
    | undefined;
  const renderReady =
    studio.renderJob?.status === "succeeded" &&
    renderResult?.documentRevision === studio.document?.revision &&
    renderResult?.documentVersion === studio.document?.version &&
    renderResult?.qualityEvaluation?.status === "passed";
  const boundCreativeCaseId = studio.document?.composition.narrative?.creativeCaseId as
    | string
    | undefined;
  const selectedCreativeCase = studio.creativeCasebook?.cases.find(
    (candidate) => candidate.caseId === selectedCreativeCaseId,
  );
  const selectedAssistance = studio.assistedIntelligence?.cases.find(
    (candidate) => candidate.caseId === selectedCreativeCaseId,
  );

  React.useEffect(() => {
    if (selectedCreativeCaseId || !studio.creativeCasebook?.cases.length) return;
    setSelectedCreativeCaseId(
      boundCreativeCaseId ?? studio.creativeCasebook.cases[0].caseId,
    );
  }, [boundCreativeCaseId, selectedCreativeCaseId, studio.creativeCasebook?.cases]);

  React.useEffect(() => {
    if (!selectedAssistance) return;
    setAssistantDecisions(Object.fromEntries(
      selectedAssistance.reviewedPlan.decisions.map((decision) => [
        decision.operationId,
        decision.decision,
      ]),
    ));
    const adjustedCaption = selectedAssistance.reviewedPlan.acceptedOperations.find(
      (operation) => operation.kind === "add_caption",
    );
    setAssistantAdjustment(adjustedCaption?.kind === "add_caption" ? adjustedCaption.text : "");
  }, [selectedAssistance]);

  React.useEffect(
    () => () => {
      if (demoUrlRef.current) URL.revokeObjectURL(demoUrlRef.current);
    },
    [],
  );

  const announce = React.useCallback(
    (message: string) => setToast?.(message),
    [setToast],
  );

  const onUpload = async (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith("video/")) {
      announce("Envie um arquivo de vídeo para iniciar o UGC.");
      return;
    }
    if (demo) {
      if (demoUrlRef.current) URL.revokeObjectURL(demoUrlRef.current);
      demoUrlRef.current = URL.createObjectURL(file);
      setDemoPreview(demoUrlRef.current);
      announce("Prévia local carregada. Entre para persistir e processar a mídia.");
      return;
    }
    try {
      const result = await studio.upload(file);
      announce(
        result.status === "ready"
          ? "Mídia validada e projeto UGC criado."
          : `Upload preservado. ${statusLabel(result.status)} no worker de mídia.`,
      );
    } catch {
      announce("O upload não foi concluído. Consulte o diagnóstico do Studio.");
    }
  };

  const sourceClips = React.useMemo(
    () =>
      [...(videoTracks[0]?.clips ?? [])]
        .filter((clip) => clip.enabled)
        .sort(
          (left, right) =>
            left.timeline.startFrame - right.timeline.startFrame,
        ),
    [videoTracks],
  );
  const activeSourceClip =
    playheadFrame === durationFrames
      ? sourceClips.at(-1)
      : sourceClips.find(
          (clip) =>
            clip.timeline.startFrame <= playheadFrame &&
            playheadFrame < clip.timeline.startFrame + clip.timeline.durationFrames,
        );
  const previewUrl =
    demoPreview ||
    (activeSourceClip
      ? studio.previewUrlsByAssetId[activeSourceClip.assetId]
      : undefined) ||
    studio.previewUrl;
  const selectedSourceClip = sourceClips.find((clip) => clip.id === selectedClipId);
  const selectedAudioClip = originalAudioTracks
    .flatMap((track) => track.clips ?? [])
    .find(
      (clip) =>
        selectedSourceClip &&
        clip.assetId === selectedSourceClip.assetId &&
        clip.timeline.startFrame === selectedSourceClip.timeline.startFrame &&
        clip.timeline.durationFrames === selectedSourceClip.timeline.durationFrames,
    );

  React.useEffect(() => {
    setPlayheadFrame((frame) => Math.min(frame, durationFrames));
  }, [durationFrames]);

  const representationSeconds = React.useCallback(
    (sourceMicroseconds: number) => {
      // Proxy clocks are required to carry a validated 1:1 time map. Until a
      // non-linear representation exists, source microseconds are the player
      // clock and the CreativeDocument remains bound to the original asset.
      return sourceMicroseconds / 1_000_000;
    },
    [],
  );

  const seekFrame = React.useCallback(
    (frame: number) => {
      soundPreview.stop();
      const bounded = Math.max(0, Math.min(durationFrames, Math.round(frame)));
      setPlayheadFrame(bounded);
      if (!playerRef.current) return;
      if (displayTimeline && sourceClips.length) {
        try {
          const sourceMicroseconds = timelineFrameToSourceMicroseconds(
            displayTimeline,
            videoTracks[0]?.id ?? "video-main",
            bounded,
          );
          const active =
            bounded === durationFrames
              ? sourceClips.at(-1)
              : sourceClips.find(
                  (clip) =>
                    clip.timeline.startFrame <= bounded &&
                    bounded <
                      clip.timeline.startFrame + clip.timeline.durationFrames,
                );
          activeClipIdRef.current = active?.id;
          playerRef.current.currentTime = representationSeconds(sourceMicroseconds);
          return;
        } catch {
          // Demo/legacy documents still receive a bounded seek below.
        }
      }
      playerRef.current.currentTime =
        (bounded * timelineRate.denominator) / timelineRate.numerator;
    },
    [
      displayTimeline,
      durationFrames,
      representationSeconds,
      sourceClips,
      timelineRate.denominator,
      timelineRate.numerator,
      videoTracks,
    ],
  );

  const playOrPause = async () => {
    const player = playerRef.current;
    if (!player) return;
    if (soundPreview.state === "loading") { soundPreview.cancel(); return; }
    if (player.paused) {
      renderedPlayerRef.current?.pause();
      if (playheadFrame >= durationFrames) seekFrame(0);
      else seekFrame(playheadFrame);
      if (!await soundPreview.prepare()) return;
      try { await player.play(); }
      catch { soundPreview.cancel(); announce("O navegador não reproduziu o preview. Tente novamente."); }
    }
    else { player.pause(); soundPreview.stop(); }
  };

  const seek = (seconds: number) => {
    seekFrame(
      Math.round(
        (seconds * timelineRate.numerator) / timelineRate.denominator,
      ),
    );
  };

  const syncPlayerToTimeline = (player: HTMLVideoElement) => {
    const syncSound = (seconds: number) => {
      if (player.paused || player.seeking || player.ended || player.readyState < 3) soundPreview.stop();
      else soundPreview.sync(seconds);
    };
    if (!displayTimeline || !sourceClips.length) {
      setPlayheadFrame(
        Math.min(
          durationFrames,
          timelineMicrosecondsToFrame(
            Math.round(player.currentTime * 1_000_000),
            timelineRate,
          ),
        ),
      );
      syncSound(player.currentTime);
      return;
    }
    const activeIndex = Math.max(
      0,
      sourceClips.findIndex((clip) => clip.id === activeClipIdRef.current),
    );
    const active = sourceClips[activeIndex];
    if (!active?.source) return;
    const sourceNow = Math.round(player.currentTime * 1_000_000);
    const sourceEnd =
      active.source.startMicroseconds + active.source.durationMicroseconds;
    const oneFrameMicroseconds =
      (1_000_000 * timelineRate.denominator) / timelineRate.numerator;
    if (sourceNow >= sourceEnd - oneFrameMicroseconds / 3) {
      const next = sourceClips[activeIndex + 1];
      if (!next?.source) {
        soundPreview.stop();
        setPlayheadFrame(durationFrames);
        if (!player.paused) player.pause();
        return;
      }
      activeClipIdRef.current = next.id;
      soundPreview.stop();
      setPlayheadFrame(next.timeline.startFrame);
      player.currentTime = representationSeconds(next.source.startMicroseconds);
      return;
    }
    const offset = Math.max(0, sourceNow - active.source.startMicroseconds);
    const offsetFrames = timelineMicrosecondsToFrame(
      offset,
      timelineRate,
      "nearest",
    );
    setPlayheadFrame(
      Math.min(
        active.timeline.startFrame + active.timeline.durationFrames,
        active.timeline.startFrame + offsetFrames,
      ),
    );
    syncSound(active.timeline.startFrame * timelineRate.denominator / timelineRate.numerator + offset / 1_000_000);
  };

  // timeupdate alone can arrive only a few times per second: too late at cuts.
  const syncPlayerRef = React.useRef(syncPlayerToTimeline);
  syncPlayerRef.current = syncPlayerToTimeline;
  React.useEffect(() => {
    if (!playing) return;
    let frame: number;
    const tick = () => {
      if (playerRef.current) syncPlayerRef.current(playerRef.current);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing]);

  const frameAtClientX = React.useCallback(
    (clientX: number, base: VideoTimeline) => {
      const bounds = trackAreaRef.current?.getBoundingClientRect();
      if (!bounds?.width) return 0;
      const ratio = Math.max(0, Math.min(1, (clientX - bounds.left) / bounds.width));
      return Math.round(ratio * base.durationFrames);
    },
    [],
  );

  const beginReorder = (
    event: React.PointerEvent<HTMLButtonElement>,
    clip: AnyRecord,
    index: number,
  ) => {
    if (!timeline || demo || studio.status === "working") return;
    event.preventDefault();
    setSelectedClipId(clip.id);
    seekFrame(clip.timeline.startFrame);
    setInteraction({
      pointerId: event.pointerId,
      base: timeline,
      command: {
        type: "reorder-ripple",
        trackId: videoTracks[0]?.id ?? "video-main",
        clipId: clip.id,
        targetIndex: index,
      },
    });
  };

  const beginTrim = (
    event: React.PointerEvent<HTMLButtonElement>,
    clip: AnyRecord,
    edge: "start" | "end",
  ) => {
    if (!timeline || demo || studio.status === "working") return;
    event.preventDefault();
    event.stopPropagation();
    setSelectedClipId(clip.id);
    setInteraction({
      pointerId: event.pointerId,
      base: timeline,
      command: {
        type: "trim",
        trackId: videoTracks[0]?.id ?? "video-main",
        clipId: clip.id,
        edge,
        targetFrame:
          edge === "start"
            ? clip.timeline.startFrame
            : clip.timeline.startFrame + clip.timeline.durationFrames,
      },
    });
  };

  React.useEffect(() => {
    if (!interaction) return;
    const onMove = (event: PointerEvent) => {
      if (event.pointerId !== interaction.pointerId) return;
      const frame = frameAtClientX(event.clientX, interaction.base);
      let command = interaction.command;
      if (command.type === "trim") {
        const clip = interaction.base.tracks
          ?.find((track) => track.id === command.trackId && track.kind === "video")
          ?.clips?.find((candidate) => candidate.id === command.clipId);
        if (!clip) return;
        const start = clip.timeline.startFrame;
        const end = start + clip.timeline.durationFrames;
        command = {
          ...command,
          targetFrame:
            command.edge === "start"
              ? Math.max(start, Math.min(end - 1, frame))
              : Math.max(start + 1, Math.min(end, frame)),
        };
      } else {
        const count =
          interaction.base.tracks?.find(
            (track) => track.id === command.trackId && track.kind === "video",
          )?.clips?.length ?? 1;
        const targetIndex = Math.max(
          0,
          Math.min(count - 1, Math.floor((frame / interaction.base.durationFrames) * count)),
        );
        command = { ...command, targetIndex };
      }
      try {
        setDraftTimeline(applyVideoTimelineCommand(interaction.base, command));
        setInteraction((current) =>
          current ? { ...current, command } : current,
        );
      } catch {
        // Invalid gestures remain local and never reach the canonical document.
      }
    };
    const finish = (event: PointerEvent) => {
      if (event.pointerId !== interaction.pointerId) return;
      const originalTrack = interaction.base.tracks?.find(
        (track) =>
          track.id === interaction.command.trackId && track.kind === "video",
      );
      const originalIndex =
        originalTrack?.kind === "video"
          ? originalTrack.clips?.findIndex(
              (clip) => clip.id === interaction.command.clipId,
            ) ?? -1
          : -1;
      const command = interaction.command;
      const changed =
        command.type === "reorder-ripple"
          ? command.targetIndex !== originalIndex
          : (() => {
              const clip =
                originalTrack?.kind === "video"
                  ? originalTrack.clips?.find(
                      (candidate) => candidate.id === command.clipId,
                    )
                  : undefined;
              if (!clip) return false;
              const boundary =
                command.edge === "start"
                  ? clip.timeline.startFrame
                  : clip.timeline.startFrame + clip.timeline.durationFrames;
              return command.targetFrame !== boundary;
            })();
      setInteraction(undefined);
      setDraftTimeline(undefined);
      if (!changed) return;
      void runDemoAware(
        "A timeline interativa exige um documento autenticado.",
        () => studio.commitTimeline(command),
        command.type === "trim"
          ? "Trim frame-exact gravado no CreativeDocument."
          : "Ordem dos takes gravada com ripple no CreativeDocument.",
      );
    };
    const cancel = (event: PointerEvent) => {
      if (event.pointerId !== interaction.pointerId) return;
      setInteraction(undefined);
      setDraftTimeline(undefined);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", cancel);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", cancel);
    };
  }, [frameAtClientX, interaction, studio]);

  React.useEffect(() => {
    if (!interaction) return;
    const cancel = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setInteraction(undefined);
      setDraftTimeline(undefined);
      announce("Gesto cancelado; nenhuma revisão foi criada.");
    };
    window.addEventListener("keydown", cancel);
    return () => window.removeEventListener("keydown", cancel);
  }, [announce, interaction]);

  const seekFromPointer = (event: React.PointerEvent<HTMLElement>) => {
    if (!displayTimeline) return;
    seekFrame(frameAtClientX(event.clientX, displayTimeline));
  };

  const runDemoAware = async (
    demoMessage: string,
    action: () => Promise<unknown>,
    successMessage: string,
  ) => {
    if (demo) {
      announce(demoMessage);
      return false;
    }
    try {
      await action();
      announce(successMessage);
      return true;
    } catch {
      announce("A operação foi bloqueada com segurança. Veja o diagnóstico ao lado.");
      return false;
    }
  };

  const splitSelectedClip = () => {
    const clip = sourceClips.find((candidate) => candidate.id === selectedClipId);
    if (!clip) {
      announce("Selecione um take antes de dividir.");
      return;
    }
    const start = clip.timeline.startFrame;
    const end = start + clip.timeline.durationFrames;
    if (playheadFrame <= start || playheadFrame >= end) {
      announce("Posicione o playhead dentro do take selecionado.");
      return;
    }
    void runDemoAware(
      "A divisão interativa exige autenticação.",
      () => studio.commitTimeline({
        type: "split",
        trackId: videoTracks[0]?.id ?? "video-main",
        clipId: clip.id,
        targetFrame: playheadFrame,
      }),
      "Take dividido no frame selecionado.",
    );
  };

  const applyTransformPreset = (
    fit: "cover" | "contain" | "fill",
    anchor: "center" | "top",
  ) => {
    if (!selectedSourceClip) {
      announce("Selecione um take para ajustar o enquadramento.");
      return;
    }
    void runDemoAware(
      "O enquadramento editável exige autenticação.",
      () => studio.commitTimeline({
        type: "set-transform",
        trackId: videoTracks[0]?.id ?? "video-main",
        clipId: selectedSourceClip.id,
        transform: {
          fit,
          anchor,
          x: 0,
          y: 0,
          scale: 1,
          rotation: 0,
          crop: { top: 0, right: 0, bottom: 0, left: 0 },
        },
      }),
      "Enquadramento salvo no take selecionado.",
    );
  };

  const applyAudioPreset = (gainDb: number, fadeFrames: number) => {
    if (!selectedAudioClip) {
      announce("O take selecionado não possui áudio original pareado.");
      return;
    }
    const boundedFade = Math.min(
      fadeFrames,
      Math.floor(selectedAudioClip.timeline.durationFrames / 2),
    );
    void runDemoAware(
      "O mix por take exige autenticação.",
      () => studio.commitTimeline({
        type: "set-audio",
        trackId:
          originalAudioTracks.find((track) =>
            track.clips?.some((clip) => clip.id === selectedAudioClip.id),
          )?.id ?? "audio-main",
        clipId: selectedAudioClip.id,
        gainDb,
        pan: 0,
        fadeInFrames: boundedFade,
        fadeOutFrames: boundedFade,
      }),
      "Mix do take salvo na timeline.",
    );
  };

  const applySpeedPreset = (playbackRate: number) => {
    if (!selectedSourceClip) {
      announce("Selecione um take para ajustar a velocidade.");
      return;
    }
    void runDemoAware(
      "A velocidade editável exige autenticação.",
      () => studio.commitTimeline({
        type: "set-speed",
        trackId: videoTracks[0]?.id ?? "video-main",
        clipId: selectedSourceClip.id,
        playbackRate,
      }),
      `Velocidade ${playbackRate.toLocaleString("pt-BR")}× salva com ripple.`,
    );
  };

  const sendForReview = async () => {
    const completed = await runDemoAware(
      "No modo demonstrativo a revisão não é persistida.",
      studio.requestReview,
      "Versão exata enviada para revisão humana.",
    );
    if (completed) navigate(`/approvals/${postId}?view=creative`);
  };

  const captureExperienceAction = React.useCallback(
    (event: React.MouseEvent<HTMLElement>) => {
      const target = event.target as HTMLElement;
      const control = target.closest<HTMLElement>("[data-action-id]");
      const actionId = control?.dataset.actionId;
      const contract = experienceActionForId(actionId);
      if (!contract) return;
      emitExperienceTelemetry({
        event: contract.analyticsEvent,
        kind: "action",
        route: `${window.location.pathname}${window.location.search}`,
        screenId: "SCREEN-VIDEO",
        actionId: contract.actionId,
      });
    },
    [],
  );

  const operationLabel = studio.operation
    ? {
        upload: "Enviando e analisando",
        captions: "Aplicando legendas",
        cut: "Aplicando corte não destrutivo",
        timeline: "Gravando gesto frame-exact",
        proxy: "Enfileirando proxy",
        waveform: "Extraindo forma de onda; fala e música não são avaliadas aqui",
        "natural-sound": "Analisando e salvando som candidato",
        "natural-sound-undo": "Desfazendo o último ajuste de som",
        render: "Enfileirando render",
        version: "Criando checkpoint",
        review: "Fixando versão para revisão",
      }[studio.operation] || studio.operation
    : undefined;

  return (
    <section
      className="vs-shell"
      aria-label="Video Studio UGC"
      onClickCapture={captureExperienceAction}
    >
      <header className="vs-topbar">
        <button
          className="vs-back"
          data-action-id="VIDEO-BACK-CONTENT"
          onClick={() => navigate("/content")}
        >
          <ChevronLeft size={18} /> Conteúdos
        </button>
        <div className="vs-title">
          <span className="vs-lab-mark"><Film size={16} /></span>
          <div>
            <h1>{title}</h1>
            <p>Video Studio · UGC assistido · 9:16</p>
          </div>
        </div>
        <div className="vs-health" data-state={studio.error ? "error" : "ok"}>
          <span />
          {demo
            ? "Modo demonstração · sem persistência"
            : operationLabel || studio.error || statusLabel(studio.ingest?.status)}
        </div>
        <button
          className="vs-quiet"
          data-action-id="VIDEO-CREATE-CHECKPOINT"
          disabled={(!demo && !studio.document) || studio.status === "working"}
          onClick={() =>
            void runDemoAware(
              "Checkpoint demonstrativo criado localmente.",
              studio.createVersion,
              "Checkpoint versionado criado.",
            )
          }
        >
          <Save size={16} /> v{studio.document?.version ?? 1}
        </button>
        <button
          className="vs-review"
          data-action-id="VIDEO-SEND-REVIEW"
          disabled={(!demo && (!studio.document || !renderReady)) || studio.status === "working"}
          title={renderReady ? "Enviar a prova atual para revisão" : "Renderize a revisão atual e aguarde o QC técnico"}
          onClick={() => void sendForReview()}
        >
          <Send size={16} /> Enviar para revisão
        </button>
      </header>

      <div className="vs-workbench">
        <aside className="vs-media-bin">
          <div className="vs-panel-head">
            <div><small>01</small><b>Materiais</b></div>
            <button
              aria-label="Atualizar mídias"
              data-action-id="VIDEO-REFRESH-MEDIA"
              onClick={() => void studio.refresh()}
            >
              <RefreshCw size={14} />
            </button>
          </div>
          <button
            className="vs-dropzone"
            data-action-id="VIDEO-UPLOAD-SOURCE"
            disabled={!demo && !data.activeWorkspace?.id}
            onClick={() => inputRef.current?.click()}
          >
            <CloudUpload size={25} />
            <b>Adicionar take</b>
            <span>MP4, MOV ou WebM</span>
            <small>O original permanece privado e imutável</small>
          </button>
          <input
            data-action-id="VIDEO-UPLOAD-SOURCE"
            ref={inputRef}
            hidden
            type="file"
            accept="video/mp4,video/quicktime,video/webm,video/*"
            onChange={(event) => void onUpload(event.target.files?.[0])}
          />

          {(studio.document?.assets?.length ? studio.document.assets : [undefined]).map((reference: AnyRecord | undefined, index: number) => {
            const mediaUrl = reference?.id ? studio.previewUrlsByAssetId[reference.id] : previewUrl;
            const usedByActiveClip = reference?.id && activeSourceClip?.assetId === reference.id;
            return (
              <article key={reference?.id ?? "empty"} className={`vs-media-card ${usedByActiveClip || (!reference && previewUrl) ? "is-active" : ""}`}>
                <div className="vs-media-thumb">
                  {mediaUrl ? (
                    <video src={mediaUrl} muted preload="metadata" />
                  ) : (
                    <img src="/canonical/figma/phase2/s06-ugc.png" alt={reference ? "Take aguardando preview" : "Exemplo de take UGC"} />
                  )}
                  <span>{reference ? `FONTE ${index + 1}` : "EXEMPLO"}</span>
                </div>
                <div>
                  <b>{reference?.provenance?.originalFilename || (reference ? `Take ${index + 1}` : "Seu primeiro take")}</b>
                  <small>{reference?.rightsStatus === "verified" ? "direitos verificados" : "direitos pendentes"}</small>
                </div>
              </article>
            );
          })}

          <div className="vs-pipeline-card">
            <p><span>1</span> Original privado <CheckCircle2 size={14} /></p>
            <p className={studio.ingest ? "is-current" : ""}><span>2</span> Probe técnico <i>{statusLabel(studio.ingest?.status)}</i></p>
            <p className={studio.ingest?.proxyAssetId ? "is-done" : ""}><span>3</span> Proxy + time-map <i>{studio.ingest?.proxyAssetId ? "validado" : "pendente"}</i></p>
            <p className={studio.ingest?.waveformAssetId ? "is-done" : ""}><span>4</span> Forma de onda <i>{studio.ingest?.waveformAssetId ? "extraída" : "pendente"}</i></p>
            <p className={studio.document ? "is-done" : ""}><span>5</span> CreativeDocument <i>{studio.document ? `r${studio.document.revision}` : "aguardando"}</i></p>
          </div>
          {!previewUrl && (
            <p className="vs-empty-guidance" role="status">
              Comece adicionando um take. O original ficará privado e todas as edições serão reversíveis.
            </p>
          )}

          <button
            className="vs-secondary-action"
            data-action-id="VIDEO-CREATE-PROXY"
            disabled={(!demo && !studio.ingest) || studio.status === "working"}
            onClick={() =>
              void runDemoAware(
                "O proxy exige um worker autenticado.",
                studio.createProxy,
                "Proxy enviado para a fila media_cpu.",
              )
            }
          >
            <WandSparkles size={15} /> Criar proxy de edição
          </button>
          <button
            className="vs-secondary-action"
            data-action-id="VIDEO-CREATE-WAVEFORM"
            disabled={(!demo && (!studio.ingest || !studio.ingest.mediaInfo?.audioStreams?.length)) || studio.status === "working"}
            onClick={() =>
              void runDemoAware(
                "A waveform exige um worker autenticado.",
                studio.createWaveform,
                "Waveform enviada para a fila media_cpu.",
              )
            }
          >
            <AudioLines size={15} /> Gerar forma de onda
          </button>
        </aside>

        <main className="vs-stage">
          <div className="vs-stage-toolbar">
            <div>
              <button className="is-active" data-action-id="VIDEO-TOGGLE-PLAYBACK" disabled={!previewUrl} title={!previewUrl ? "Adicione um take para reproduzir" : "Ouvir a montagem salva"} onClick={() => void playOrPause()} aria-label={playbackLabel("Reproduzir preview", "Pausar preview")}><Video size={15} /> Preview</button>
              <button data-action-id="VIDEO-SELECT-INSPECTOR" onClick={() => setInspector("brand")}><Layers3 size={15} /> Composição</button>
            </div>
            <span>
              1080 × 1920 · {(timelineRate.numerator / timelineRate.denominator).toFixed(
                timelineRate.denominator === 1 ? 0 : 3,
              )} fps
            </span>
            <button data-action-id="VIDEO-SELECT-INSPECTOR" onClick={() => setInspector("cuts")}><SlidersHorizontal size={15} /> Ajustar</button>
          </div>
          <div className="vs-canvas-wrap">
            <div className="vs-canvas-grid" />
            <div className="vs-phone-frame">
              {previewUrl ? (
                <video
                  ref={playerRef}
                  src={previewUrl}
                  muted={originalAudioMuted}
                  playsInline
                  onPlay={() => setPlaying(true)}
                  onPause={() => { setPlaying(false); soundPreview.stop(); }}
                  onWaiting={() => soundPreview.stop()}
                  onSeeking={() => soundPreview.stop()}
                  onSeeked={(event) => syncPlayerToTimeline(event.currentTarget)}
                  onEnded={() => { setPlaying(false); soundPreview.stop(); }}
                  onTimeUpdate={(event) => syncPlayerToTimeline(event.currentTarget)}
                  onLoadedMetadata={(event) => {
                    if (!duration && Number.isFinite(event.currentTarget.duration))
                      setPlayheadFrame(0);
                  }}
                />
              ) : (
                <img src="/canonical/figma/phase2/s06-ugc.png" alt="Preview do anúncio UGC" />
              )}
              <div className="vs-safe-area" />
              {!!previewCaption && (
                <div
                  className="vs-caption-preview"
                  style={{
                    left: "12%",
                    top: "69%",
                    width: "76%",
                    height: "14%",
                    color: currentCaptionCue?.style?.color || "#ffffff",
                    fontSize: `${(Number(currentCaptionCue?.style?.fontSize ?? 56) / pageWidth) * 100}cqw`,
                  }}
                >
                  {previewCaption}
                </div>
              )}
              {!!brandShapeLayer && (
                <div
                  className="vs-brand-overlay"
                  style={{
                    ...boxStyle(brandShapeLayer),
                    background: brandShapeLayer.properties?.fill || profile?.primaryColor || "#6c5ce7",
                    borderRadius: `${(Number(brandShapeLayer.properties?.radius ?? 0) / Math.min(Number(brandShapeLayer.width), Number(brandShapeLayer.height))) * 100}%`,
                  }}
                />
              )}
              {!!brandTextLayer && (
                <div
                  className="vs-brand-text-overlay"
                  style={{
                    ...boxStyle(brandTextLayer),
                    color: brandTextLayer.properties?.color || "#ffffff",
                    fontSize: `${(Number(brandTextLayer.properties?.fontSize ?? 48) / pageWidth) * 100}cqw`,
                    textAlign: brandTextLayer.properties?.align || "center",
                  }}
                >
                  {brandTextLayer.properties?.text || "Conheça a marca"}
                </div>
              )}
              <button className="vs-play-center" data-action-id="VIDEO-TOGGLE-PLAYBACK" disabled={!previewUrl} title={!previewUrl ? "Adicione um take para reproduzir" : "Ouvir a montagem salva"} onClick={() => void playOrPause()} aria-label={playbackLabel("Reproduzir", "Pausar")}>
                {playing ? <Pause /> : <Play />}
              </button>
            </div>
          </div>
          <div className="vs-player-controls">
            <button data-action-id="VIDEO-TOGGLE-PLAYBACK" disabled={!previewUrl} title={!previewUrl ? "Adicione um take para reproduzir" : "Ouvir a montagem salva"} onClick={() => void playOrPause()} aria-label={playbackLabel("Reproduzir vídeo", "Pausar vídeo")}>{playing ? <Pause size={16} /> : <Play size={16} />}</button>
            <span>{formatTime(currentTime)}</span>
            <input
              data-action-id="VIDEO-SEEK"
              aria-label="Posição do vídeo"
              type="range"
              min="0"
              max={Math.max(duration, 0.1)}
              step={timelineRate.denominator / timelineRate.numerator}
              value={Math.min(currentTime, Math.max(duration, 0.1))}
              onChange={(event) => seek(Number(event.target.value))}
            />
            <span>{formatTime(duration)}</span>
          </div>
          <p className="vs-audio-preview-status" role={soundPreview.error ? "alert" : "status"}>
            {soundPreview.error ? `${soundPreview.error} Tente reproduzir novamente ou confira o MP4 em Saída.`
              : soundPreview.state === "loading" ? "Carregando e verificando os sons privados. Clique em cancelar para interromper."
              : naturalSoundClips.some((clip) => clip.enabled !== false)
                ? "Preview com sons da edição salva. Escuta e direitos pendentes; confira o MP4 final em Saída."
                : "Preview da montagem. Adicione sons naturais na aba Sons; sem geração de voz."}
          </p>
        </main>

        <aside className="vs-inspector">
          <div className="vs-inspector-tabs">
            {[
              ["preproduction", Layers3, "Pré"],
              ["editorial", CheckCircle2, "Revisão"],
              ["assistant", WandSparkles, "Copiloto"],
              ["factory", Layers3, "Fábrica"],
              ["captions", Captions, "Legendas"],
              ["cuts", Scissors, "Cortes"],
              ["brand", Sparkles, "Marca"],
              ["sound", AudioLines, "Sons"],
              ["render", Film, "Saída"],
            ].map(([key, Icon, label]) => (
              <button
                key={String(key)}
                data-action-id="VIDEO-SELECT-INSPECTOR"
                className={inspector === key ? "is-active" : ""}
                onClick={() => setInspector(key as typeof inspector)}
                aria-pressed={inspector === key}
              >
                <Icon size={16} /> {label}
              </button>
            ))}
          </div>

          <div className="vs-inspector-body" hidden={inspector !== "editorial"}
            key={`${studio.document?.documentId}:${studio.document?.revision}`}>
            <ContextualEditingPanel document={studio.document} disabled={demo || studio.status === "working"}
              onRender={async (document, planId) => {
                await studio.renderContextual(document, planId);
                setInspector("render");
              }} />
            <EditorialReviewPanel
              document={studio.document} disabled={demo || studio.status === "working"}
              active={inspector === "editorial"} onGateChange={setEditorialGate} />
          </div>

          {inspector === "preproduction" && (
            <div className="vs-inspector-body">
              <small className="vs-step">ETAPA 00 · STORYBOARD E ANIMATIC</small>
              <h2>Pré-produção executável</h2>
              <p>Escolha um caso autoral, examine beat → shot → clip e só então vincule o plano ao documento. O animatic usa placeholders; geração cara e publicação continuam bloqueadas.</p>
              <label>
                Caso do casebook
                <select
                  value={selectedCreativeCaseId ?? ""}
                  onChange={(event) => {
                    setSelectedCreativeCaseId(event.target.value);
                    void studio.loadCreativeAnimatic(event.target.value).catch(() => {
                      announce("O animatic privado não pôde ser carregado.");
                    });
                  }}
                >
                  {(studio.creativeCasebook?.cases ?? []).map((creativeCase) => (
                    <option key={creativeCase.caseId} value={creativeCase.caseId}>
                      {creativeCase.title}
                    </option>
                  ))}
                </select>
              </label>
              {selectedCreativeCase && (
                <>
                  <div className="vs-preproduction-route">
                    <b>{selectedCreativeCase.recipe.name}</b>
                    <span>{selectedCreativeCase.formatRoute.selectionRationale}</span>
                    <small>
                      Storyboard {selectedCreativeCase.storyboard.status} · animatic {selectedCreativeCase.animatic.status}
                    </small>
                  </div>
                  {studio.animaticPreviewUrl && (
                    <video
                      className="vs-animatic-preview"
                      src={studio.animaticPreviewUrl}
                      controls
                      playsInline
                      aria-label={`Animatic placeholder de ${selectedCreativeCase.title}`}
                    />
                  )}
                  {!studio.animaticPreviewUrl && (
                    <button
                      onClick={() => void studio.loadCreativeAnimatic(selectedCreativeCase.caseId)}
                    >
                      <Play size={14} /> Carregar animatic privado
                    </button>
                  )}
                  <ol className="vs-storyboard-map" aria-label="Mapa de beats, shots e clips">
                    {selectedCreativeCase.storyboard.shots.map((shot) => {
                      const beat = selectedCreativeCase.script.beats.find(
                        (candidate) => candidate.beatId === shot.beatId,
                      );
                      return (
                        <li key={shot.shotId}>
                          <span>{String(shot.order + 1).padStart(2, "0")}</span>
                          <div>
                            <b>Beat · {beat?.narrativeRole} → Shot · {shot.visualFunction}</b>
                            <small>{shot.frameDescription}</small>
                            <i>
                              Clip · {shot.plannedClipIds.length
                                ? shot.plannedClipIds.join(", ")
                                : "placeholder a vincular após direitos"}
                            </i>
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                  <div className="vs-audit-note">
                    <b>Gate de render caro</b>
                    <span>Bloqueado até aprovação humana do storyboard/animatic e verificação de direitos.</span>
                  </div>
                  <button
                    className="vs-primary-action"
                    disabled={!studio.document || studio.status === "working" || boundCreativeCaseId === selectedCreativeCase.caseId}
                    onClick={() => void studio.bindCreativeCase(selectedCreativeCase.caseId)}
                  >
                    <Save size={16} /> {boundCreativeCaseId === selectedCreativeCase.caseId ? "Vinculado ao documento" : "Vincular pré-produção"}
                  </button>
                </>
              )}
            </div>
          )}

          {inspector === "assistant" && (
            <div className="vs-inspector-body">
              <small className="vs-step">ETAPA 01 · DECISÃO EDITORIAL LOCALIZADA</small>
              <h2>Copiloto com evidência</h2>
              <p>Compare três estratégias. A crítica repara só o beat reprovado; cada operação exige aceitar, rejeitar ou ajustar e pode ser desfeita pelo histórico.</p>
              {!selectedAssistance && <div className="vs-audit-note"><b>Selecione um caso em Pré</b><span>A suite assistida acompanha os mesmos 12 casos.</span></div>}
              {selectedAssistance && (
                <>
                  <div className="vs-assistant-options">
                    {selectedAssistance.optionSet.options.map((option) => (
                      <article key={option.optionId} className={option.optionId === selectedAssistance.optionSet.selectedOptionId ? "is-selected" : ""}>
                        <b>{option.strategy.replaceAll("_", " ")}</b>
                        <span>{Math.round(option.score * 100)} pontos</span>
                        <small>{option.critiques.filter((item) => item.verdict === "repair").length} beat(s) para reparar</small>
                      </article>
                    ))}
                  </div>
                  {selectedAssistance.optionSet.repair && (
                    <div className="vs-audit-note">
                      <b>Reparo localizado · {selectedAssistance.optionSet.repair.repairedBeatId}</b>
                      <span>{selectedAssistance.optionSet.repair.preservedBeatIds.length} outros beats preservados por digest.</span>
                    </div>
                  )}
                  <div className="vs-assistant-operations">
                    {selectedAssistance.proposal.operations.map((operation) => (
                      <article key={operation.operationId}>
                        <div><b>{operation.kind.replaceAll("_", " ")}</b><small>{operation.rationale}</small></div>
                        <select
                          aria-label={`Decisão para ${operation.operationId}`}
                          value={assistantDecisions[operation.operationId] ?? "reject"}
                          onChange={(event) => setAssistantDecisions((current) => ({
                            ...current,
                            [operation.operationId]: event.target.value as "accept" | "reject" | "adjust",
                          }))}
                        >
                          <option value="accept">Aceitar</option>
                          <option value="reject">Rejeitar</option>
                          <option value="adjust">Ajustar</option>
                        </select>
                        <small>Evidência: {operation.evidenceIds.join(", ")}</small>
                        {operation.kind === "add_caption" && assistantDecisions[operation.operationId] === "adjust" && (
                          <input value={assistantAdjustment} onChange={(event) => setAssistantAdjustment(event.target.value)} aria-label="Texto ajustado da legenda" />
                        )}
                      </article>
                    ))}
                  </div>
                  <button
                    className="vs-primary-action"
                    disabled={!studio.document || studio.status === "working"}
                    onClick={() => void studio.reviewAssistedProposal(
                      selectedAssistance.caseId,
                      selectedAssistance.proposal.operations.map((operation) => ({
                        operationId: operation.operationId,
                        decision: assistantDecisions[operation.operationId] ?? "reject",
                        adjustedText: operation.kind === "add_caption" ? assistantAdjustment : undefined,
                      })),
                    )}
                  >
                    <CheckCircle2 size={16} /> Confirmar decisões reversíveis
                  </button>
                </>
              )}
            </div>
          )}

          {inspector === "factory" && (
            <div className="vs-inspector-body">
              <small className="vs-step">ETAPA 02 · 12 + 24 + 64</small>
              <h2>Fábrica privada</h2>
              <p>A iteração atual foi rejeitada. Os arquivos permanecem somente como evidência técnica e a escala continua bloqueada até um novo planejamento.</p>
              {studio.videoFactoryProgram && (
                <>
                  <dl className="vs-render-spec">
                    <div><dt>Piloto</dt><dd>{studio.videoFactoryProgram.pilot.jobs.filter((job) => job.humanReviewStatus === "rejected").length} / 12 rejeitados</dd></div>
                    <div><dt>Calibração</dt><dd>{studio.videoFactoryProgram.calibration.jobs.filter((job) => job.humanReviewStatus === "rejected").length} / 24 rejeitados</dd></div>
                    <div><dt>Escala</dt><dd>{studio.videoFactoryProgram.scale.jobs.filter((job) => job.status === "blocked_by_gate").length} / 64 bloqueados</dd></div>
                    <div><dt>Aprovação humana</dt><dd>{studio.videoFactoryProgram.humanApprovedCount} / 100</dd></div>
                    <div><dt>Publicação externa</dt><dd>{studio.videoFactoryProgram.externalPublicationCount}</dd></div>
                  </dl>
                  <div className="vs-audit-note">
                    <b>Hard gate vigente</b>
                    <span>{studio.videoFactoryProgram.blockers.join(" · ")}</span>
                  </div>
                  {studio.creativeReplanState && (
                    <div className="vs-audit-note">
                      <b>Novo ciclo · golden primeiro</b>
                      <span>
                        {studio.creativeReplanState.approvedDecisionCount}/{studio.creativeReplanState.decisions.length} decisões aprovadas · limite {studio.creativeReplanState.goldenJobLimit} golden · lote {studio.creativeReplanState.batchDispatchAuthorized ? "autorizado" : "bloqueado"}
                      </span>
                    </div>
                  )}
                  {studio.videoAutonomyAudit && (
                    <div className="vs-audit-note">
                      <b>Implementação {studio.videoAutonomyAudit.implementationComplete ? "completa" : "incompleta"} · objetivo {studio.videoAutonomyAudit.objectiveComplete ? "concluído" : "não concluído"}</b>
                      <span>{studio.videoAutonomyAudit.producedPrivateArtifactCount} provas técnicas · {studio.videoAutonomyAudit.humanApprovedArtifactCount} aprovações · {studio.videoAutonomyAudit.dispatchedScaleJobCount}/64 escala despachada</span>
                    </div>
                  )}
                  {studio.advancedCapabilityAudit && (
                    <div className="vs-audit-note">
                      <b>Voz/avatar · desativados</b>
                      <span>
                        {studio.advancedCapabilityAudit.candidates.length} candidatos inventariados · {studio.advancedCapabilityAudit.authorizedIdentityCount}/6 identidades autorizadas · {studio.advancedCapabilityAudit.executedBenchmarkCaseCount}/24 casos · nenhum provider habilitado
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {inspector === "captions" && (
            <div className="vs-inspector-body">
              <small className="vs-step">ETAPA 03 · TEXTO EDITORIAL</small>
              <h2>Legendas editoriais</h2>
              <p>Uma linha vira um cue temporizado na duração do take. Este texto comunica a história visual; ele não declara fala nem transcrição.</p>
              <label>
                Texto editorial das legendas
                <textarea data-action-id="VIDEO-EDIT-CAPTIONS" value={captionText} onChange={(event) => {
                  captionDraftDirtyRef.current = true;
                  setCaptionText(event.target.value);
                }} rows={8} />
              </label>
              <div className="vs-caption-style">
                <span>Aa</span><div><b>Lower third</b><small>Branco + contorno de contraste</small></div><CheckCircle2 size={16} />
              </div>
              <button
                className="vs-primary-action"
                data-action-id="VIDEO-APPLY-CAPTIONS"
                disabled={(!demo && !studio.document) || studio.status === "working"}
                onClick={() =>
                  void runDemoAware(
                    "Legenda demonstrativa aplicada à prévia.",
                    async () => {
                      const result = await studio.applyEditorialCaptions(captionText);
                      captionDraftDirtyRef.current = false;
                      return result;
                    },
                    "Legendas editoriais salvas na timeline.",
                  )
                }
              >
                <Captions size={16} /> Aplicar na timeline
              </button>
            </div>
          )}

          {inspector === "cuts" && (
            <div className="vs-inspector-body">
              <small className="vs-step">ETAPA 04 · EDIÇÃO NÃO DESTRUTIVA</small>
              <h2>Remover trecho</h2>
              <p>{sourceClips.length > 1
                ? "A primeira decisão já dividiu o take. Agora selecione, reordene ou ajuste as alças diretamente na timeline."
                : "O corte grava uma decisão frame-exact. O arquivo original nunca é alterado."}</p>
              <div className="vs-cut-fields">
                <label>Início (s)<input data-action-id="VIDEO-SET-CUT-RANGE" type="number" min="0" step="0.1" value={cutStart} onChange={(event) => setCutStart(event.target.value)} /></label>
                <label>Fim (s)<input data-action-id="VIDEO-SET-CUT-RANGE" type="number" min="0" step="0.1" value={cutEnd} onChange={(event) => setCutEnd(event.target.value)} /></label>
              </div>
              <button
                className="vs-primary-action"
                data-action-id="VIDEO-APPLY-CUT"
                disabled={(!demo && (!studio.document || sourceClips.length > 1)) || studio.status === "working"}
                onClick={() =>
                  void runDemoAware(
                    "Corte demonstrativo aplicado sem alterar o original.",
                    () => studio.applyCut(Number(cutStart), Number(cutEnd)),
                    "Corte aplicado e timeline recomposta frame a frame.",
                  )
                }
              >
                <Scissors size={16} /> Aplicar corte
              </button>
              <div className="vs-audit-note">
                <b>Take selecionado</b>
                <span>{selectedSourceClip?.label || "Selecione um take na timeline"}</span>
              </div>
              <div className="vs-property-actions" role="group" aria-label="Ajustes do take selecionado">
                <button disabled={!selectedSourceClip || studio.status === "working"} onClick={splitSelectedClip}>Dividir no playhead</button>
                <button disabled={!selectedSourceClip || studio.status === "working"} onClick={() => applyTransformPreset("cover", "center")}>Preencher</button>
                <button disabled={!selectedSourceClip || studio.status === "working"} onClick={() => applyTransformPreset("contain", "center")}>Conter</button>
                <button disabled={!selectedSourceClip || studio.status === "working"} onClick={() => applyTransformPreset("cover", "top")}>Priorizar topo</button>
                {[0.5, 1, 1.5, 2].map((rate) => (
                  <button
                    key={rate}
                    className={(selectedSourceClip?.playbackRate ?? 1) === rate ? "is-active" : undefined}
                    disabled={!selectedSourceClip || studio.status === "working"}
                    onClick={() => applySpeedPreset(rate)}
                  >
                    {rate.toLocaleString("pt-BR")}×
                  </button>
                ))}
                <button disabled={!selectedAudioClip || studio.status === "working"} onClick={() => applyAudioPreset(0, 0)}>Áudio original</button>
                <button disabled={!selectedAudioClip || studio.status === "working"} onClick={() => applyAudioPreset(-6, Math.round(timelineRate.numerator / timelineRate.denominator / 5))}>−6 dB + fades</button>
              </div>
              <div className="vs-audit-note">
                <b>Histórico auditável</b>
                <span>{studio.decisionSet ? `Decision set ${studio.decisionSet.status} · v${studio.decisionSet.version}` : "Nenhum corte persistido"}</span>
              </div>
            </div>
          )}

          {inspector === "brand" && (
            <div className="vs-inspector-body">
              <small className="vs-step">ETAPA 05 · IDENTIDADE VISUAL</small>
              <h2>Camadas da marca</h2>
              <p>Os overlays pertencem ao documento e podem ser trocados sem reprocessar o take original.</p>
              <div className="vs-brand-card">
                <span style={{ background: profile?.primaryColor || "#6c5ce7" }} />
                <div><b>{brand?.name || "Sua marca"}</b><small>Memória r{Math.max(1, profile?.versions?.length || 1)}</small></div>
              </div>
              <ul className="vs-layer-list">
                <li><span>▰</span><div><b>Faixa da marca</b><small>Shape · lower third</small></div><i>visível</i></li>
                <li><span>T</span><div><b>CTA da marca</b><small>Texto editável</small></div><i>visível</i></li>
                <li><span>CC</span><div><b>Legendas editoriais PT-BR</b><small>Track sincronizada, sem fala presumida</small></div><i>{captionTracks[0]?.cues?.length ? "aplicada" : "pendente"}</i></li>
              </ul>
            </div>
          )}

          {inspector === "render" && (
            <div className="vs-inspector-body">
              <small className="vs-step">ETAPA 06 · WORKER ISOLADO</small>
              <h2>Render vertical</h2>
              <p>O renderer FFmpeg recompõe os source ranges e materializa as legendas e camadas versionadas. O áudio do take continua não verificado: encode e waveform não comprovam ausência de voz ou música.</p>
              <div className="vs-audit-note">
                <b>Perfil vigente: foley natural + legenda</b>
                <span>{originalAudioMuted
                  ? "Som original removido. Confira o som natural no MP4 renderizado; o mix continua pendente de revisão."
                  : "Som original não verificado. Voz e música não pertencem a este perfil; revise a captação antes da produção."}</span>
              </div>
              <button
                className="vs-secondary-action"
                data-action-id="VIDEO-MUTE-ORIGINAL"
                aria-pressed={originalAudioMuted}
                disabled={demo || !studio.document || originalAudioTracks.length !== 1 || studio.status === "working"}
                title={demo ? "O controle exige um projeto autenticado" : originalAudioTracks.length !== 1 ? "Adicione um take com áudio" : "Altera a edição; o arquivo original é preservado"}
                onClick={() => void runDemoAware(
                  "O controle de som exige um documento autenticado.",
                  () => studio.muteOriginalAudio(!originalAudioMuted),
                  originalAudioMuted ? "Som original restaurado na edição; revisão acústica pendente." : "Som original removido da edição. O arquivo permanece intacto.",
                )}
              >
                <AudioLines size={15} /> {originalAudioMuted ? "Restaurar som original" : "Remover som original"}
              </button>
              <dl className="vs-render-spec">
                <div><dt>Formato</dt><dd>MP4 · H.264/AAC</dd></div>
                <div><dt>Canvas</dt><dd>1080 × 1920</dd></div>
                <div><dt>Fila</dt><dd>media_cpu</dd></div>
                <div><dt>Provider</dt><dd>builtin.ffmpeg-ugc-v1</dd></div>
                <div><dt>Custo</dt><dd>Não medido neste worker</dd></div>
              </dl>
              <button
                className="vs-primary-action"
                data-action-id="VIDEO-RENDER-PREVIEW"
                disabled={(!demo && !studio.document) || studio.status === "working" || editorialRenderBlocked}
                onClick={() =>
                  void runDemoAware(
                    "O render real exige autenticação e o worker media_cpu.",
                    studio.render,
                    "Render enviado para o worker isolado.",
                  )
                }
              >
                <Film size={16} /> Renderizar prova privada
              </button>
              {editorialRenderBlocked && <p role="status">Consulte a aba Revisão: a prontidão editorial está pendente ou bloqueada.</p>}
              {studio.job && (
                <article className="vs-job-card" aria-live="polite">
                  <header><span className={`is-${studio.job.status}`} /> <b>{statusLabel(studio.job.status)}</b><small>{studio.job.progress}%</small></header>
                  <div><i style={{ width: `${studio.job.progress}%` }} /></div>
                  <p>{studio.job.executionCapability} · tentativa {studio.job.attempts}/{studio.job.maxAttempts}</p>
                  {studio.job.errorMessage && <strong>{studio.job.errorMessage}</strong>}
                  <footer>
                    <button data-action-id="VIDEO-REFRESH-JOB" onClick={() => void studio.refreshJob()}><RefreshCw size={14} /> Atualizar</button>
                    {["queued", "running", "retrying"].includes(studio.job.status) && <button data-action-id="VIDEO-CANCEL-JOB" onClick={() => void studio.cancelJob()}><CircleStop size={14} /> Cancelar</button>}
                    {["failed", "cancelled"].includes(studio.job.status) && <button data-action-id="VIDEO-RETRY-JOB" onClick={() => void studio.retryJob()}><RotateCcw size={14} /> Tentar novamente</button>}
                  </footer>
                </article>
              )}
              {studio.renderPreviewUrl && renderResult?.artifact && (
                <article className="vs-render-artifact">
                  <b>{renderReady ? "Prova privada vinculável" : "Prova de uma revisão anterior ou com QC pendente"}</b>
                  <video ref={renderedPlayerRef} className="vs-rendered-player" controls preload="metadata" src={studio.renderPreviewUrl} aria-label="MP4 renderizado com o mix de áudio" onPlay={() => soundPreview.cancel()} />
                  {renderResult.warnings?.includes("ffmpeg_ugc_natural_sound_review_pending") && <span>Som externo materializado · origem e escuta pendentes</span>}
                  {renderResult.warnings?.includes("ffmpeg_ugc_original_audio_muted") && (
                    <span>Prova sem som original · não é mix natural aprovado</span>
                  )}
                  <span>SHA-256 {renderResult.artifact.checksumSha256?.slice(0, 12)}…</span>
                  <span>
                    {renderResult.renderedLayerIds?.length ?? 0} camadas · {renderResult.renderedCaptionTrackIds?.length ?? 0} track de legenda materializada
                  </span>
                  <span className={`vs-qc-status is-${renderResult.qualityEvaluation?.status ?? "pending"}`}>
                    {renderResult.qualityEvaluation?.status === "passed"
                      ? "QC técnico aprovado · escuta pendente"
                      : "QC técnico bloqueou a revisão"}
                  </span>
                  {renderResult.qualityEvaluation?.metrics && (
                    <span>
                      {renderResult.qualityEvaluation.metrics.integratedLoudnessLufs?.toFixed(1)} LUFS · sync {renderResult.qualityEvaluation.metrics.avDurationDeltaMs?.toFixed(0)} ms · black {((renderResult.qualityEvaluation.metrics.blackFrameRatio ?? 0) * 100).toFixed(1)}%
                    </span>
                  )}
                  <a href={studio.renderPreviewUrl} download={`${title}-prova.mp4`}>Baixar MP4 renderizado</a>
                  {!!renderResult.warnings?.length && (
                    <small>{renderResult.warnings.length} limitações registradas no artefato</small>
                  )}
                </article>
              )}
            </div>
          )}

          <div className="vs-inspector-body" hidden={inspector !== "sound"}>
            <NaturalSoundPanel document={studio.document} disabled={demo || !studio.document || studio.status === "working"}
              save={studio.saveNaturalSound} notify={setToast} toggle={studio.toggleNaturalSound}
              reviewRights={studio.reviewNaturalSoundRights}
              undo={studio.undoNaturalSound} canUndo={studio.canUndoNaturalSound} selectionRequest={soundSelectionRequest} />
          </div>
          {studio.error && (
            <div className="vs-error-box" role="alert">
              <b>Gate de segurança</b>
              <span>{studio.error}</span>
            </div>
          )}
        </aside>
      </div>

      <footer className="vs-timeline">
        <div className="vs-timeline-head">
          <div><b>Timeline</b><span>OpenCut como referência de UX · CreativeDocument como fonte de verdade</span></div>
          <div>
            <button aria-label="Desfazer edição da timeline" disabled={!studio.canUndoTimeline || studio.status === "working"} onClick={() => void studio.undoTimeline()}><Undo2 size={14} /></button>
            <button aria-label="Refazer edição da timeline" disabled={!studio.canRedoTimeline || studio.status === "working"} onClick={() => void studio.redoTimeline()}><Redo2 size={14} /></button>
            <button aria-label="Dividir take no playhead" disabled={!selectedClipId || studio.status === "working"} onClick={splitSelectedClip}><Scissors size={14} /></button>
            <button aria-label="Diminuir zoom da timeline" disabled={timelineZoom <= 1} onClick={() => setTimelineZoom((value) => Math.max(1, value - 0.5))}><ZoomOut size={14} /></button>
            <button aria-label="Aumentar zoom da timeline" disabled={timelineZoom >= 4} onClick={() => setTimelineZoom((value) => Math.min(4, value + 0.5))}><ZoomIn size={14} /></button>
            <button aria-label="Abrir ajustes de corte" data-action-id="VIDEO-SELECT-INSPECTOR" onClick={() => setInspector("cuts")}><SlidersHorizontal size={14} /></button>
            <button aria-label="Importar outro arquivo" data-action-id="VIDEO-UPLOAD-SOURCE" onClick={() => inputRef.current?.click()}><Upload size={14} /></button>
            <span>{timelineZoom.toFixed(1)}× · {formatTime(currentTime)} / {formatTime(duration)}</span>
          </div>
        </div>
        <div className={`vs-timeline-grid ${naturalSoundClips.length ? "has-natural-sound" : ""}`}>
          <div className="vs-track-labels">
            <span>Régua</span><span><Video size={13} /> Vídeo</span><span><AudioLines size={13} /> {originalAudioMuted ? "Original mudo" : "Original"}</span>
            {!!naturalSoundClips.length && <span><AudioLines size={13} /> Som natural</span>}
            <span><Captions size={13} /> Legendas</span><span><Sparkles size={13} /> Marca</span>
          </div>
          <div className="vs-track-scroll">
          <div className="vs-track-area" ref={trackAreaRef} style={{ width: `${timelineZoom * 100}%` }}>
            <div
              className="vs-ruler"
              role="slider"
              tabIndex={0}
              aria-label="Playhead da timeline"
              aria-valuemin={0}
              aria-valuemax={durationFrames}
              aria-valuenow={playheadFrame}
              onPointerDown={seekFromPointer}
              onKeyDown={(event) => {
                if (event.key === "ArrowLeft") seekFrame(playheadFrame - 1);
                if (event.key === "ArrowRight") seekFrame(playheadFrame + 1);
              }}
            >
              {Array.from({ length: 8 }, (_, index) => <i key={index}>{formatTime((duration / 7) * index)}</i>)}
            </div>
            <div className="vs-track vs-video-track">
              {(videoTracks[0]?.clips?.length ? videoTracks[0].clips : [{ id: "demo", timeline: { startFrame: 0, durationFrames: 100 } }]).map((clip: AnyRecord, index: number) => (
                <div
                  key={clip.id}
                  className={`vs-video-clip ${selectedClipId === clip.id ? "is-selected" : ""}`}
                  role="group"
                  tabIndex={0}
                  aria-label={`TAKE ${String(index + 1).padStart(2, "0")} · ${selectedClipId === clip.id ? "selecionado" : "não selecionado"} · pressione Enter para selecionar; use Alt e setas para reordenar`}
                  data-clip-id={clip.id}
                  data-start-frame={clip.timeline.startFrame}
                  data-duration-frames={clip.timeline.durationFrames}
                  data-source-start-microseconds={clip.source?.startMicroseconds ?? 0}
                  style={{
                    left: `${(clip.timeline.startFrame / durationFrames) * 100}%`,
                    width: `${(clip.timeline.durationFrames / durationFrames) * 100}%`,
                  }}
                  onPointerDown={(event) => beginReorder(event as unknown as React.PointerEvent<HTMLButtonElement>, clip, index)}
                  onClick={() => {
                    setSelectedClipId(clip.id);
                    seekFrame(clip.timeline.startFrame);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedClipId(clip.id);
                      seekFrame(clip.timeline.startFrame);
                    }
                    if (event.altKey && event.key === "ArrowLeft" && index > 0) {
                      void runDemoAware(
                        "A timeline interativa exige autenticação.",
                        () => studio.commitTimeline({ type: "reorder-ripple", trackId: videoTracks[0]?.id ?? "video-main", clipId: clip.id, targetIndex: index - 1 }),
                        "Take movido um passo para a esquerda.",
                      );
                    }
                    if (event.altKey && event.key === "ArrowRight" && index < sourceClips.length - 1) {
                      void runDemoAware(
                        "A timeline interativa exige autenticação.",
                        () => studio.commitTimeline({ type: "reorder-ripple", trackId: videoTracks[0]?.id ?? "video-main", clipId: clip.id, targetIndex: index + 1 }),
                        "Take movido um passo para a direita.",
                      );
                    }
                  }}
                >
                  <span
                    className="vs-trim-handle is-start"
                    role="slider"
                    tabIndex={0}
                    aria-label={`Ajustar início de TAKE ${String(index + 1).padStart(2, "0")}`}
                    aria-valuemin={clip.timeline.startFrame}
                    aria-valuemax={clip.timeline.startFrame + clip.timeline.durationFrames - 1}
                    aria-valuenow={clip.timeline.startFrame}
                    onPointerDown={(event) => beginTrim(event as unknown as React.PointerEvent<HTMLButtonElement>, clip, "start")}
                    onKeyDown={(event) => {
                      if (event.key !== "ArrowRight") return;
                      event.stopPropagation();
                      void studio.commitTimeline({ type: "trim", trackId: videoTracks[0]?.id ?? "video-main", clipId: clip.id, edge: "start", targetFrame: clip.timeline.startFrame + 1 });
                    }}
                  />
                  <GripVertical size={11} />
                  <span className="vs-clip-copy"><b>TAKE {String(index + 1).padStart(2, "0")}</b><small>{clip.label || studio.asset?.title || "UGC principal"}</small></span>
                  <span
                    className="vs-trim-handle is-end"
                    role="slider"
                    tabIndex={0}
                    aria-label={`Ajustar fim de TAKE ${String(index + 1).padStart(2, "0")}`}
                    aria-valuemin={clip.timeline.startFrame + 1}
                    aria-valuemax={clip.timeline.startFrame + clip.timeline.durationFrames}
                    aria-valuenow={clip.timeline.startFrame + clip.timeline.durationFrames}
                    onPointerDown={(event) => beginTrim(event as unknown as React.PointerEvent<HTMLButtonElement>, clip, "end")}
                    onKeyDown={(event) => {
                      if (event.key !== "ArrowLeft") return;
                      event.stopPropagation();
                      void studio.commitTimeline({ type: "trim", trackId: videoTracks[0]?.id ?? "video-main", clipId: clip.id, edge: "end", targetFrame: clip.timeline.startFrame + clip.timeline.durationFrames - 1 });
                    }}
                  />
                </div>
              ))}
            </div>
            <div className="vs-track vs-audio-track">
              {!!waveformBars.length && (
                <span className="vs-waveform-bars" style={{ left: 0, width: "100%" }}>
                  {waveformBars.map((height, index) => (
                    <i key={index} style={{ height: `${height * 100}%` }} />
                  ))}
                </span>
              )}
              {!waveformBars.length && <em>Waveform após preparar a mídia</em>}
            </div>
            {!!naturalSoundClips.length && <div className="vs-track vs-natural-track">
              {naturalSoundClips.map((clip) => <button key={clip.id} data-action-id="VIDEO-SOUND-SELECT"
                aria-label={`Editar som natural no frame ${clip.timeline.startFrame}`}
                className={clip.enabled === false ? "is-disabled-cue" : undefined}
                onClick={() => { setInspector("sound"); setSoundSelectionRequest({ clipId: clip.id, nonce: Date.now() }); }}
                style={{ left: `${clip.timeline.startFrame / durationFrames * 100}%`, width: `${clip.timeline.durationFrames / durationFrames * 100}%` }}>
                {clip.enabled === false ? "Desativado" : `Som · ${clip.gainDb ?? 0} dB`}
              </button>)}
            </div>}
            <div className="vs-track vs-caption-track">
              {(captionTracks[0]?.cues?.length
                ? captionTracks[0].cues
                : demo
                  ? captionText.split(/\r?\n/).filter(Boolean).map((text, index, lines) => ({ id: index, text, timeline: { startFrame: Math.floor((durationFrames / lines.length) * index), durationFrames: Math.max(1, Math.floor((durationFrames / lines.length) * (index + 1)) - Math.floor((durationFrames / lines.length) * index)) } }))
                  : []).map((cue: AnyRecord) => <span key={cue.id} style={{ left: `${(cue.timeline.startFrame / durationFrames) * 100}%`, width: `${(cue.timeline.durationFrames / durationFrames) * 100}%` }}>{cue.text}</span>)}
            </div>
            <div className="vs-track vs-brand-track"><span>Faixa + CTA da marca</span></div>
            <button
              className="vs-playhead"
              data-action-id="VIDEO-SEEK"
              aria-label="Posição atual"
              style={{ left: `${Math.min(100, (playheadFrame / durationFrames) * 100)}%` }}
              onPointerDown={seekFromPointer}
            ><i /></button>
          </div>
          </div>
        </div>
      </footer>

      {studio.status === "working" && (
        <div className="vs-operation" role="status"><LoaderCircle /> {operationLabel}</div>
      )}
    </section>
  );
}
