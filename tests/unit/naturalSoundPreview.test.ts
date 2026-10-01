import assert from "node:assert/strict";
import test from "node:test";
import { naturalSoundPreviewPlan, previewSoundGain, scheduleNaturalSoundPreview } from "../../src/studios/naturalSoundPreview.ts";
import { placeNaturalSound, setNaturalSoundEnabled } from "../../src/studios/naturalSoundTimeline.ts";
import type { VideoTimeline } from "../../src/studios/videoTimeline.ts";

const empty: VideoTimeline = { schemaVersion: "studio.media-timeline.v1", durationFrames: 90,
  frameRate: { numerator: 30, denominator: 1 }, tracks: [] };
const asset: any = { id: "sound", checksum: "a".repeat(64), mediaType: "audio/wav",
  provenance: { purpose: "natural-sound-candidate", durationMicroseconds: 2_000_000 } };
const timeline = placeNaturalSound(empty, "sound", 2_000_000,
  { startFrame: 15, sourceStartFrame: 3, durationFrames: 45, gainDb: -6, fadeFrames: 9 }, "a");

test("preview projeta tempo canônico, source offset, ganho e fades sem editar o documento", () => {
  const before = structuredClone(timeline);
  const plan = naturalSoundPreviewPlan(timeline, [asset]);
  assert.deepEqual(timeline, before);
  assert.equal(plan.duration, 3);
  assert.deepEqual(plan.cues[0], { id: "a", assetId: "sound", start: 0.5, duration: 1.5,
    offset: 0.1, gain: 10 ** (-6 / 20), fadeIn: 0.3, fadeOut: 0.3 });
  assert.equal(plan.assets.length, 1);
  assert.equal(previewSoundGain(plan.cues[0], 0), 0);
  assert.equal(previewSoundGain(plan.cues[0], 0.15), plan.cues[0].gain / 2);
  assert.ok(Math.abs(previewSoundGain(plan.cues[0], 1.35) - plan.cues[0].gain / 2) < 1e-12);
});

test("preview omite desativados e track mutada, mas reutiliza a fonte de cues ativos", () => {
  const two = placeNaturalSound(timeline, "sound", 2_000_000,
    { startFrame: 0, sourceStartFrame: 0, durationFrames: 30, gainDb: -12, fadeFrames: 0 }, "b");
  assert.equal(naturalSoundPreviewPlan(two, [asset]).cues.length, 2);
  assert.equal(naturalSoundPreviewPlan(two, [asset]).assets.length, 1);
  assert.equal(naturalSoundPreviewPlan(setNaturalSoundEnabled(two, "a", false), [asset]).cues.length, 1);
  if (two.tracks![0].kind !== "audio") throw new Error();
  two.tracks![0].muted = true;
  assert.deepEqual(naturalSoundPreviewPlan(two, [asset]).assets, []);
});

test("preview rejeita fontes não verificáveis, efeitos e limites; não os ignora", () => {
  assert.throws(() => naturalSoundPreviewPlan(timeline, []), /referência/);
  assert.throws(() => naturalSoundPreviewPlan(timeline, [{ ...asset, checksum: "invalid" }]), /referência/);
  assert.throws(() => naturalSoundPreviewPlan(timeline, [{ ...asset,
    provenance: { ...asset.provenance, durationMicroseconds: 700_000_000 } }]), /10 minutos/);
  const invalid = structuredClone(timeline);
  if (invalid.tracks![0].kind !== "audio") throw new Error();
  invalid.tracks![0].clips![0].pan = 0.5;
  assert.throws(() => naturalSoundPreviewPlan(invalid, [asset]), /efeito/);
});

test("agendamento de seek inicia no source correto e no ganho intermediário, com stop de todos os nós", () => {
  const events: any[] = [];
  const context: any = { currentTime: 10, destination: {},
    createBufferSource: () => ({ buffer: null, connect() {}, disconnect() {},
      start: (...args: any[]) => events.push(["start", ...args]), stop: () => events.push(["stop"]) }),
    createGain: () => ({ connect() {}, disconnect() {}, gain: {
      setValueAtTime: (...args: any[]) => events.push(["set", ...args]),
      linearRampToValueAtTime: (...args: any[]) => events.push(["ramp", ...args]),
    } }),
  };
  const plan = naturalSoundPreviewPlan(timeline, [asset]);
  const stop = scheduleNaturalSoundPreview(context, plan, new Map([["sound", { duration: 2 } as AudioBuffer]]), 0.65);
  const start = events.find(([type]) => type === "start");
  assert.equal(start[1], 10);
  assert.ok(Math.abs(start[2] - 0.25) < 1e-12);
  assert.ok(Math.abs(start[3] - 1.35) < 1e-12);
  assert.ok(Math.abs(events[0][1] - plan.cues[0].gain / 2) < 1e-12);
  stop();
  assert.equal(events.filter(([type]) => type === "stop").length, 1);
  const initialCount = events.length;
  assert.throws(() => scheduleNaturalSoundPreview(context, plan, new Map(), 0), /não cobre/);
  assert.equal(events.length, initialCount);
});
