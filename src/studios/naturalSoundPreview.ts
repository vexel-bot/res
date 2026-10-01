import type { StudioDocumentRecord } from "../api/productApi";
import type { VideoTimeline } from "./videoTimeline";
import { NATURAL_SOUND_TRACK_ID } from "./naturalSoundTimeline";

export interface PreviewSoundCue {
  id: string;
  assetId: string;
  start: number;
  duration: number;
  offset: number;
  gain: number;
  fadeIn: number;
  fadeOut: number;
}
export interface NaturalSoundPreviewPlan {
  duration: number;
  cues: PreviewSoundCue[];
  assets: Array<{ id: string; checksum: string; duration: number }>;
}

/** Ephemeral playback adapter; never a second persisted timeline or approval. */
export function naturalSoundPreviewPlan(
  timeline: VideoTimeline | undefined,
  assets: StudioDocumentRecord["assets"],
): NaturalSoundPreviewPlan {
  const rate = timeline?.frameRate ?? { numerator: 30, denominator: 1 };
  const fps = rate.numerator / rate.denominator;
  if (!Number.isFinite(fps) || fps <= 0) throw new Error("Timebase inválida para escuta.");
  const duration = (timeline?.durationFrames ?? 0) / fps;
  const track = timeline?.tracks?.find((item) => item.id === NATURAL_SOUND_TRACK_ID);
  const cues: PreviewSoundCue[] = [];
  const sources = new Map<string, NaturalSoundPreviewPlan["assets"][number]>();
  if (track?.kind === "audio" && !track.muted) {
    for (const clip of track.clips ?? []) {
      if (clip.enabled === false) continue;
      const ref = assets.find((asset) => asset.id === clip.assetId);
      if (!ref?.mediaType.startsWith("audio/") || ref.provenance?.purpose !== "natural-sound-candidate"
        || !/^[a-f0-9]{64}$/i.test(ref.checksum ?? "") || !clip.source) {
        throw new Error("Som sem referência verificável. Reimporte o arquivo antes de ouvir o preview.");
      }
      if (clip.effects?.length || clip.keyframes?.length || Object.keys(clip.transform ?? {}).length || (clip.pan ?? 0) !== 0) {
        throw new Error("Este efeito de áudio não é suportado no preview. Confira o diagnóstico de render.");
      }
      const cue = { id: clip.id, assetId: clip.assetId, start: clip.timeline.startFrame / fps,
        duration: clip.timeline.durationFrames / fps, offset: clip.source.startMicroseconds / 1_000_000,
        gain: 10 ** ((clip.gainDb ?? 0) / 20), fadeIn: (clip.fadeInFrames ?? 0) / fps, fadeOut: (clip.fadeOutFrames ?? 0) / fps };
      const sourceDuration = Number(ref.provenance.durationMicroseconds) / 1_000_000;
      if (![cue.start, cue.duration, cue.offset, cue.gain, cue.fadeIn, cue.fadeOut, sourceDuration].every(Number.isFinite)
        || cue.start < 0 || cue.duration <= 0 || cue.offset < 0 || cue.start + cue.duration > duration + 0.000001
        || cue.offset + cue.duration > sourceDuration + 0.000001 || cue.fadeIn < 0 || cue.fadeOut < 0
        || cue.fadeIn + cue.fadeOut > cue.duration + 0.000001
        || Math.abs(clip.source.durationMicroseconds / 1_000_000 - cue.duration) > 0.000002) {
        throw new Error("Intervalo de som incompatível com a montagem.");
      }
      // Bound browser decoding before loading; server rendering remains available.
      if (sourceDuration > 600) throw new Error("Preview local aceita fontes de som de até 10 minutos. Use o MP4 em Saída para esta fonte.");
      cues.push(cue);
      sources.set(ref.id, { id: ref.id, checksum: ref.checksum!, duration: sourceDuration });
    }
  }
  if (cues.length > 32 || sources.size > 8) throw new Error("Preview limitado a 32 trechos e oito fontes de som.");
  return { duration, cues, assets: [...sources.values()] };
}

export function previewSoundGain(cue: PreviewSoundCue, elapsed: number) {
  const fadeIn = cue.fadeIn > 0 ? Math.min(1, Math.max(0, elapsed / cue.fadeIn)) : 1;
  const fadeOut = cue.fadeOut > 0 ? Math.min(1, Math.max(0, (cue.duration - elapsed) / cue.fadeOut)) : 1;
  return cue.gain * fadeIn * fadeOut;
}

/** Shared by the live AudioContext and real OfflineAudioContext sample tests. */
export function scheduleNaturalSoundPreview(
  context: BaseAudioContext,
  plan: NaturalSoundPreviewPlan,
  buffers: ReadonlyMap<string, AudioBuffer>,
  timelineSeconds: number,
  at = context.currentTime,
) {
  const nodes: Array<{ source: AudioBufferSourceNode; gain: GainNode }> = [];
  // Validate the whole graph before starting any node: never play a partial mix.
  for (const cue of plan.cues) {
    const buffer = buffers.get(cue.assetId);
    if (!buffer || cue.offset + cue.duration > buffer.duration + 0.002) throw new Error("O som decodificado não cobre o intervalo salvo.");
  }
  for (const cue of plan.cues) {
    const elapsed = Math.max(0, timelineSeconds - cue.start);
    if (elapsed >= cue.duration) continue;
    const buffer = buffers.get(cue.assetId)!;
    const when = at + Math.max(0, cue.start - timelineSeconds);
    const source = context.createBufferSource();
    const gain = context.createGain();
    source.buffer = buffer;
    source.connect(gain);
    gain.connect(context.destination);
    gain.gain.setValueAtTime(previewSoundGain(cue, elapsed), when);
    const points = [cue.fadeIn, cue.duration - cue.fadeOut, cue.duration]
      .filter((point) => point > elapsed).sort((a, b) => a - b);
    for (const point of new Set(points)) gain.gain.linearRampToValueAtTime(previewSoundGain(cue, point), when + point - elapsed);
    source.start(when, cue.offset + elapsed, cue.duration - elapsed);
    nodes.push({ source, gain });
  }
  return () => { for (const { source, gain } of nodes) { source.stop(); source.disconnect(); gain.disconnect(); } };
}

export class NaturalSoundPreview {
  private context?: AudioContext;
  private buffers = new Map<string, AudioBuffer>();
  private checksums = new Map<string, string>();
  private controller?: AbortController;
  private cancelNodes?: () => void;
  private anchor?: { audio: number; timeline: number };
  private plan?: NaturalSoundPreviewPlan;
  private generation = 0;
  private disposed = false;

  constructor(private readonly load: (id: string, signal: AbortSignal) => Promise<Blob>) {}

  async prepare(plan: NaturalSoundPreviewPlan) {
    this.cancel();
    if (this.disposed) throw new DOMException("Preview encerrado", "AbortError");
    const generation = this.generation;
    const controller = new AbortController();
    this.controller = controller;
    const check = () => {
      if (this.disposed || generation !== this.generation || controller.signal.aborted) throw new DOMException("Preview cancelado", "AbortError");
    };
    if (!plan.cues.length) { this.plan = plan; return; }
    if (typeof AudioContext !== "function") throw new Error("Este navegador não suporta o preview de som. Confira o MP4 em Saída.");
    this.context ??= new AudioContext();
    // Called directly from the user's playback gesture, before network awaits.
    const resumed = Promise.race([
      this.context.resume().then(() => undefined, (error: unknown) => error),
      new Promise<unknown>((resolve) => controller.signal.addEventListener("abort", () => resolve(new DOMException("Preview cancelado", "AbortError")), { once: true })),
    ]);
    for (const id of this.buffers.keys()) {
      if (!plan.assets.some((asset) => asset.id === id && asset.checksum === this.checksums.get(id))) {
        this.buffers.delete(id); this.checksums.delete(id);
      }
    }
    for (const asset of plan.assets) {
      if (this.buffers.has(asset.id)) continue;
      const blob = await this.load(asset.id, controller.signal);
      check();
      if (blob.size > 20 * 1024 * 1024) throw new Error("Arquivo acima do limite de 20 MB para preview local.");
      const bytes = await blob.arrayBuffer();
      const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (value) => value.toString(16).padStart(2, "0")).join("");
      check();
      if (hash !== asset.checksum.toLowerCase()) throw new Error("Checksum do som divergente. O preview não foi reproduzido.");
      const buffer = await this.context.decodeAudioData(bytes);
      check();
      const memory = [...this.buffers.values(), buffer].reduce((sum, value) => sum + value.length * value.numberOfChannels * 4, 0);
      if (buffer.numberOfChannels > 2 || memory > 128 * 1024 * 1024) throw new Error("Som excede o limite do preview local (estéreo / 128 MB decodificados). Use o MP4 em Saída.");
      if (Math.abs(buffer.duration - asset.duration) > 0.15) throw new Error("Duração decodificada diverge da fonte analisada.");
      this.buffers.set(asset.id, buffer); this.checksums.set(asset.id, asset.checksum);
    }
    const resumeError = await resumed;
    if (resumeError) throw resumeError;
    check();
    if (this.context.state !== "running") throw new Error("Áudio bloqueado pelo navegador. Reproduza novamente para tentar liberar.");
    this.plan = plan;
  }

  sync(timelineSeconds: number) {
    if (!this.context || !this.plan?.cues.length || this.disposed) return;
    if (this.context.state !== "running") {
      this.stop();
      throw new Error("O navegador interrompeu o áudio. Reproduza novamente para retomar o mix.");
    }
    const now = this.context.currentTime;
    if (this.anchor && Math.abs(this.anchor.timeline + now - this.anchor.audio - timelineSeconds) < 0.06) return;
    this.stop();
    this.cancelNodes = scheduleNaturalSoundPreview(this.context, this.plan, this.buffers, timelineSeconds, now);
    this.anchor = { audio: now, timeline: timelineSeconds };
  }

  stop() { this.cancelNodes?.(); this.cancelNodes = undefined; this.anchor = undefined; }
  cancel() { this.generation += 1; this.controller?.abort(); this.controller = undefined; this.stop(); this.plan = undefined; }
  dispose() {
    this.disposed = true; this.cancel(); this.buffers.clear(); this.checksums.clear();
    if (this.context && this.context.state !== "closed") void this.context.close().catch(() => undefined);
  }
}
