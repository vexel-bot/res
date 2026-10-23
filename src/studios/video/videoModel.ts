import type {
  AssetRecord,
  StudioDocumentCreate,
  StudioGenerationJobRecord,
} from "../../api/productApi";
import type {
  CraftCommand,
  CraftDocument,
  CraftInspection,
} from "../craft/craftApi";

export type VideoArea = "ai" | "editor" | "motion" | "ad";
export type VideoKind =
  "social" | "institutional" | "promo" | "product" | "education";
export type AdPath = "own" | "assembly" | "avatar" | "generated";
export interface VideoBrief {
  title: string;
  objective: string;
  audience: string;
  script: string;
  style: string;
  kind: VideoKind;
  aspect: "9:16" | "16:9" | "1:1";
  duration: number;
  locale: string;
  offer: string;
  benefit: string;
  cta: string;
  adPath: AdPath;
}
export const initialVideoBrief = (handoff?: {
  title: string;
  objective: string;
}): VideoBrief => ({
  title: handoff?.title || "",
  objective: handoff?.objective || "",
  audience: "",
  script: "",
  style: "Natural e direto",
  kind: "social",
  aspect: "9:16",
  duration: 15,
  locale: "pt-BR",
  offer: "",
  benefit: "",
  cta: "",
  adPath: "own",
});
export const VIDEO_KINDS: Array<{
  id: VideoKind;
  name: string;
  description: string;
}> = [
  {
    id: "social",
    name: "Redes sociais",
    description: "Reels, stories e conteúdo vertical.",
  },
  {
    id: "institutional",
    name: "Institucional",
    description: "Conte a história da sua marca.",
  },
  {
    id: "promo",
    name: "Promocional",
    description: "Uma oferta que merece atenção.",
  },
  {
    id: "product",
    name: "Produto",
    description: "Mostre como funciona, na prática.",
  },
  {
    id: "education",
    name: "Educativo",
    description: "Transforme conhecimento em vídeo.",
  },
];
export function dimensions(aspect: VideoBrief["aspect"]) {
  return aspect === "16:9"
    ? [1920, 1080]
    : aspect === "1:1"
      ? [1080, 1080]
      : [1080, 1920];
}
export function validateBrief(brief: VideoBrief) {
  if (brief.title.trim().length < 3)
    return "Dê um nome ao projeto com pelo menos 3 caracteres.";
  if (brief.title.length > 180) return "O nome deve ter até 180 caracteres.";
  if (brief.objective.trim().length < 8)
    return "Descreva o objetivo com pelo menos 8 caracteres.";
  if (brief.audience.trim().length < 3) return "Informe o público do vídeo.";
  if (
    brief.objective.length > 1000 ||
    brief.script.length > 1000 ||
    brief.audience.length > 2000 ||
    brief.style.length > 1000 ||
    brief.benefit.length > 1000 ||
    brief.offer.length > 2000 ||
    brief.cta.length > 500
  )
    return "O briefing ultrapassa o limite de texto do projeto.";
  if (
    !Number.isFinite(brief.duration) ||
    brief.duration < 1 ||
    brief.duration > 600
  )
    return "A duração deve estar entre 1 e 600 segundos.";
}
export function documentBrief(doc: CraftDocument): VideoBrief {
  const setup = doc.composition.narrative?.videoStudio as
    Partial<VideoBrief> | undefined;
  const page = doc.composition.pages[0];
  const ratio = page ? page.width / page.height : 9 / 16;
  return {
    ...initialVideoBrief(),
    ...setup,
    title: doc.title,
    objective: doc.brief.objective,
    audience: doc.brief.audience,
    script: doc.brief.angle,
    style: doc.brief.tone || "Natural e direto",
    offer: doc.brief.hook,
    benefit: doc.brief.promise,
    cta: doc.brief.cta,
    aspect: ratio > 1.2 ? "16:9" : ratio < 0.8 ? "9:16" : "1:1",
    duration: Math.max(
      1,
      doc.composition.mediaTimeline
        ? (doc.composition.mediaTimeline.durationFrames *
            doc.composition.mediaTimeline.frameRate.denominator) /
            doc.composition.mediaTimeline.frameRate.numerator
        : (page?.durationMs || 15000) / 1000,
    ),
  };
}
function creativeBrief(brief: VideoBrief): StudioDocumentCreate["brief"] {
  return {
    schemaVersion: "studio.creative-brief.v1",
    objective: brief.objective.trim(),
    audience: brief.audience.trim(),
    angle: brief.script.trim(),
    promise: brief.benefit.trim(),
    hook: brief.offer.trim(),
    cta: brief.cta.trim(),
    channel: brief.aspect === "9:16" ? "instagram" : "youtube",
    format: "video",
    tone: brief.style,
    restrictions: [],
    hypotheses: [],
    evidence: [],
  };
}
export function videoDocumentInput(
  workspaceId: string,
  brief: VideoBrief,
  assets: AssetRecord[],
  motion = false,
): StudioDocumentCreate {
  const [width, height] = dimensions(brief.aspect);
  const durationFrames = Math.round(brief.duration * 30);
  return {
    workspaceId,
    title: brief.title.trim(),
    contentType: "video",
    brandRevision: 1,
    brief: creativeBrief(brief),
    correlationId: crypto.randomUUID(),
    composition: {
      pages: [
        {
          id: "page-1",
          role: "content",
          width,
          height,
          safeArea: 48,
          background: "#000000",
          durationMs: brief.duration * 1000,
          layers: [],
        },
      ],
      narrative: {
        videoStudio: { ...brief, engine: motion ? "effectcraft" : "filmcraft" },
      },
      tracks: [],
      mediaTimeline: {
        schemaVersion: "studio.media-timeline.v1",
        frameRate: { numerator: 30, denominator: 1 },
        durationFrames,
        tracks: assets
          .filter((asset) =>
            /^(video|audio|image)\//.test(asset.mediaType || ""),
          )
          .map((asset, index) => {
            const track = {
              id: `track-${index + 1}`,
              name: asset.title,
              muted: false,
              locked: false,
            };
            const clip = {
              id: `clip-${index + 1}`,
              assetId: asset.id,
              timeline: { startFrame: 0, durationFrames },
              enabled: true,
              locked: false,
              label: asset.title,
              playbackRate: 1,
              transform: {
                originalAudioEnabled:
                  asset.mediaType?.startsWith("video/") || false,
              },
            };
            return asset.mediaType?.startsWith("audio/")
              ? {
                  ...track,
                  kind: "audio" as const,
                  clips: [
                    {
                      ...clip,
                      gainDb: 0,
                      pan: 0,
                      fadeInFrames: 0,
                      fadeOutFrames: 0,
                    },
                  ],
                }
              : { ...track, kind: "video" as const, clips: [clip] };
          }),
      },
    },
    assets: assets.map((asset) => ({
      id: asset.id,
      mediaType: asset.mediaType || "application/octet-stream",
      checksum: asset.checksumSha256,
      origin: "workspace",
      rightsStatus: "unknown",
      provenance: {},
    })),
  };
}
/** Composition is engine-owned. Metadata updates never rewrite the timeline or native state. */
export function updateVideoBrief(
  doc: CraftDocument,
  brief: VideoBrief,
): CraftDocument {
  return {
    ...doc,
    title: brief.title.trim(),
    brief: {
      ...doc.brief,
      ...creativeBrief(brief),
      restrictions: doc.brief.restrictions,
      evidence: doc.brief.evidence,
      hypotheses: doc.brief.hypotheses,
    },
  };
}
export interface VideoClip {
  id: string;
  trackId: string;
  name: string;
  kind: string;
  startMs: number;
  durationMs: number;
  properties: Record<string, unknown>;
}
export interface VideoTrack {
  id: string;
  name: string;
  kind: string;
  muted: boolean;
  clips: VideoClip[];
}
export function timelineTracks(
  inspection?: CraftInspection,
  doc?: CraftDocument,
): VideoTrack[] {
  if (inspection) {
    const layers = inspection.project.layers || [];
    const clips = (inspection.project.timeline || []).map(
      (item, index): VideoClip => ({
        id: String(item.id ?? index),
        trackId: String(item.trackId ?? item.id ?? index),
        name: String(item.name || "Elemento"),
        kind: String(item.kind || "video"),
        startMs: Math.max(0, Number(item.startMs) || 0),
        durationMs: Math.max(1, Number(item.durationMs) || 1),
        properties:
          item.properties && typeof item.properties === "object"
            ? (item.properties as Record<string, unknown>)
            : {},
      }),
    );
    const ids = [
      ...new Set([
        ...layers.map((layer) => layer.id),
        ...clips.map((clip) => clip.trackId),
      ]),
    ];
    return ids.map((id) => {
      const layer = layers.find((item) => item.id === id);
      return {
        id,
        name: layer?.name || "Trilha",
        kind:
          layer?.kind ||
          clips.find((clip) => clip.trackId === id)?.kind ||
          "video",
        muted: Boolean(layer?.properties?.muted),
        clips: clips.filter((clip) => clip.trackId === id),
      };
    });
  }
  const timeline = doc?.composition.mediaTimeline;
  const fps = timeline
    ? timeline.frameRate.numerator / timeline.frameRate.denominator
    : 30;
  return (timeline?.tracks || [])
    .filter((track) => "clips" in track || "cues" in track)
    .map((track) => ({
      id: track.id,
      name: track.name,
      kind: track.kind,
      muted: "muted" in track && Boolean(track.muted),
      clips: ("clips" in track
        ? track.clips || []
        : "cues" in track
          ? track.cues || []
          : []
      ).map((clip) => ({
        id: clip.id,
        trackId: track.id,
        name:
          "text" in clip
            ? String(clip.text)
            : "label" in clip
              ? String(clip.label)
              : "Elemento",
        kind: track.kind,
        startMs: (clip.timeline.startFrame / fps) * 1000,
        durationMs: (clip.timeline.durationFrames / fps) * 1000,
        properties: {},
      })),
    }));
}
// FilmCraft uses 254,016,000,000 ticks per second (not milliseconds or frames).
export const FILM_TICKS_PER_SECOND = 254_016_000_000;
function nativeId(value: string) {
  const id = Number(value);
  if (!Number.isSafeInteger(id) || id < 0)
    throw new Error("Identificador nativo inválido.");
  return id;
}
export function moveClip(clip: VideoClip, seconds: number): CraftCommand {
  if (!Number.isFinite(seconds) || seconds < 0)
    throw new Error("A posição não pode ser negativa.");
  return {
    id: "timeline.move",
    params: {
      moves: [
        {
          clip: nativeId(clip.id),
          track: nativeId(clip.trackId),
          time: Math.round(seconds * FILM_TICKS_PER_SECOND),
        },
      ],
      insert: false,
    },
  };
}
export function splitClip(clip: VideoClip, seconds: number): CraftCommand {
  if (
    seconds * 1000 <= clip.startMs ||
    seconds * 1000 >= clip.startMs + clip.durationMs
  )
    throw new Error("Posicione o cursor dentro do clipe para dividir.");
  return {
    id: "timeline.razor",
    params: {
      clip: nativeId(clip.id),
      time: Math.round(seconds * FILM_TICKS_PER_SECOND),
    },
  };
}
/** Atomic EffectCraft preset. Result references are resolved by the native engine, not guessed IDs. */
export function motionTitleCommand(input: {
  preset: "title" | "lower" | "cta";
  text: string;
  color: string;
  size: number;
  width: number;
  height: number;
  duration: number;
}): CraftCommand {
  if (
    !input.text.trim() ||
    input.text.length > 500 ||
    !/^#[0-9a-f]{6}$/i.test(input.color) ||
    !Number.isFinite(input.size) ||
    input.size < 12 ||
    input.size > 300 ||
    !Number.isFinite(input.duration) ||
    input.duration < 1
  )
    throw new Error(
      "Revise o texto, a cor, o tamanho e a duração da composição.",
    );
  const inset = Math.min(72, input.width * 0.08);
  return {
    id: "engine.batch",
    params: {
      label: "Título animado Clicko",
      atomic: true,
      steps: [
        {
          command: "layer.newText",
          params: {
            name:
              input.preset === "lower"
                ? "Identificação"
                : input.preset === "cta"
                  ? "Chamada final"
                  : "Título de abertura",
            text: input.text.trim(),
            fill: input.color,
            size: input.size,
            box: [
              inset,
              input.preset === "lower"
                ? input.height * 0.77
                : input.preset === "cta"
                  ? input.height * 0.42
                  : input.height * 0.16,
              input.width - inset * 2,
              Math.min(240, input.height * 0.22),
            ],
          },
        },
        ...[
          { time: 0, value: 0 },
          { time: 0.45, value: 100 },
          { time: input.duration - 0.45, value: 100 },
          { time: input.duration, value: 0 },
        ].map((key) => ({
          command: "prop.addKey",
          params: {
            layer: "$1.layer",
            path: "transform/opacity",
            timeBase: "comp",
            ...key,
          },
        })),
      ],
    },
  };
}
export const JOB_LABELS: Record<StudioGenerationJobRecord["status"], string> = {
  queued: "Na fila",
  running: "Processando",
  retrying: "Tentando novamente",
  cancel_requested: "Cancelando",
  cancelled: "Cancelado",
  succeeded: "Concluído",
  failed: "Falha no processamento",
};
export function jobProgress(job: Pick<StudioGenerationJobRecord, "progress">) {
  return Math.max(0, Math.min(100, job.progress));
}
export function outputAsset(
  job?: Pick<StudioGenerationJobRecord, "status" | "result">,
): string | undefined {
  if (job?.status !== "succeeded") return;
  const artifact = job.result?.artifact;
  return artifact &&
    typeof artifact === "object" &&
    "assetId" in artifact &&
    typeof artifact.assetId === "string"
    ? artifact.assetId
    : undefined;
}
