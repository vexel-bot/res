import { timelineFrameToMicroseconds, type VideoTimeline } from "./videoTimeline";

export const NATURAL_SOUND_TRACK_ID = "audio-natural";

export interface NaturalSoundPlacement {
  startFrame: number;
  sourceStartFrame: number;
  durationFrames: number;
  gainDb: number;
  fadeFrames: number;
}

/** Upserts one stable cue; unrelated cues, uploaded bytes and captions are preserved. */
export function placeNaturalSound(
  input: VideoTimeline,
  assetId: string,
  sourceDurationMicroseconds: number,
  placement: NaturalSoundPlacement,
  clipId = "natural-sound-main",
): VideoTimeline {
  if (!clipId || clipId.length > 120) throw new Error("Identificador do som inválido.");
  const { startFrame, sourceStartFrame, durationFrames, gainDb, fadeFrames } = placement;
  if (![startFrame, sourceStartFrame, durationFrames, fadeFrames].every(Number.isSafeInteger)
    || startFrame < 0 || sourceStartFrame < 0 || durationFrames < 1 || fadeFrames < 0
    || startFrame + durationFrames > input.durationFrames || fadeFrames * 2 > durationFrames
    || !Number.isFinite(gainDb) || gainDb < -96 || gainDb > 0) {
    throw new Error("Use um intervalo dentro do vídeo, fades menores que metade do trecho e volume entre -96 e 0 dB.");
  }
  const rate = input.frameRate ?? { numerator: 30, denominator: 1 };
  const startMicroseconds = timelineFrameToMicroseconds(sourceStartFrame, rate);
  const durationMicroseconds = timelineFrameToMicroseconds(durationFrames, rate);
  if (!Number.isFinite(sourceDurationMicroseconds) || startMicroseconds + durationMicroseconds > sourceDurationMicroseconds) {
    throw new Error("O trecho ultrapassa a duração do arquivo de som.");
  }
  const result = structuredClone(input);
  const previous = result.tracks?.find((track) => track.id === NATURAL_SOUND_TRACK_ID);
  if (previous && (previous.kind !== "audio" || previous.locked || previous.clips?.some((clip) => clip.id === clipId && clip.locked))) {
    throw new Error("A track de som natural está bloqueada.");
  }
  const existing = previous?.kind === "audio" ? previous.clips ?? [] : [];
  const current = existing.find((clip) => clip.id === clipId);
  if (!current && existing.length >= 32) throw new Error("Este mix suporta até 32 sons. Ajuste um som existente.");
  result.tracks = (result.tracks ?? []).filter((track) => track.id !== NATURAL_SOUND_TRACK_ID);
  result.tracks.push({
    id: NATURAL_SOUND_TRACK_ID, kind: "audio", name: "Sons naturais · candidatos", muted: previous?.kind === "audio" ? previous.muted : false, locked: false,
    clips: [...existing.filter((clip) => clip.id !== clipId), {
      id: clipId, assetId, label: current?.label ?? "Som natural · escuta pendente",
      timeline: { startFrame, durationFrames }, source: { startMicroseconds, durationMicroseconds },
      enabled: current?.enabled ?? true, locked: false, playbackRate: 1, transform: {}, effects: [], keyframes: [],
      gainDb, pan: 0, fadeInFrames: fadeFrames, fadeOutFrames: fadeFrames,
    }].sort((left, right) => left.timeline.startFrame - right.timeline.startFrame || left.id.localeCompare(right.id)),
  });
  return result;
}

export function setNaturalSoundEnabled(input: VideoTimeline, clipId: string, enabled: boolean): VideoTimeline {
  const result = structuredClone(input);
  const track = result.tracks?.find((item) => item.id === NATURAL_SOUND_TRACK_ID);
  if (track?.kind !== "audio") throw new Error("A track de som natural não está disponível.");
  const clip = track.clips?.find((item) => item.id === clipId);
  if (!clip) throw new Error("Este som não existe mais na revisão atual.");
  if (track.locked || clip.locked) throw new Error("Este som está bloqueado.");
  clip.enabled = enabled;
  return result;
}
