import assert from "node:assert/strict";
import test from "node:test";
import { placeNaturalSound, setNaturalSoundEnabled } from "../../src/studios/naturalSoundTimeline.ts";
import { applyVideoTimelineCommand, setOriginalAudioMuted, type VideoTimeline } from "../../src/studios/videoTimeline.ts";

const source = { id: "take", assetId: "video", timeline: { startFrame: 0, durationFrames: 90 },
  source: { startMicroseconds: 0, durationMicroseconds: 3_000_000 }, enabled: true, locked: false, label: "take", playbackRate: 1 };
const fixture: VideoTimeline = { schemaVersion: "studio.media-timeline.v1", frameRate: { numerator: 30, denominator: 1 }, durationFrames: 90,
  tracks: [{ id: "video-main", kind: "video", name: "Video", muted: true, locked: false, clips: [source] },
    { id: "audio-main", kind: "audio", name: "Original", muted: true, locked: false,
      clips: [{ ...source, id: "audio", gainDb: 0, pan: 0, fadeInFrames: 0, fadeOutFrames: 0 }] }] };
const placement = { startFrame: 15, sourceStartFrame: 6, durationFrames: 45, gainDb: -6, fadeFrames: 3 };

test("som externo preserva original e reconfigura track sem duplicar", () => {
  const mixed = placeNaturalSound(fixture, "sound", 2_000_000, placement);
  assert.equal(fixture.tracks?.length, 2);
  const track = mixed.tracks?.find((item) => item.id === "audio-natural");
  assert.equal(track?.kind, "audio");
  if (track?.kind !== "audio") throw new Error();
  assert.deepEqual(track.clips?.[0].source, { startMicroseconds: 200_000, durationMicroseconds: 1_500_000 });
  const again = placeNaturalSound(mixed, "sound", 2_000_000, { ...placement, startFrame: 20 });
  assert.equal(again.tracks?.length, 3);
  const restored = setOriginalAudioMuted(again, false);
  assert.deepEqual(restored.tracks?.[2], again.tracks?.[2]);
});

test("trim mantém origem do som e limita fades ao intervalo restante", () => {
  const mixed = placeNaturalSound(fixture, "sound", 3_000_000, { ...placement, startFrame: 0, sourceStartFrame: 0, durationFrames: 90, fadeFrames: 40 });
  const edited = applyVideoTimelineCommand(mixed, { type: "trim", trackId: "video-main", clipId: "take", edge: "end", targetFrame: 30 });
  const track = edited.tracks?.find((item) => item.id === "audio-natural");
  if (track?.kind !== "audio") throw new Error();
  const clip = track.clips![0];
  assert.equal(clip.timeline.durationFrames, 30);
  assert.equal(clip.source?.durationMicroseconds, 1_000_000);
  assert.ok((clip.fadeInFrames ?? 0) + (clip.fadeOutFrames ?? 0) <= 30);
});

test("intervalo, ganho, fade e origem inválidos não alteram documento", () => {
  for (const change of [{ startFrame: -1 }, { startFrame: 80 }, { durationFrames: 0 }, { gainDb: NaN }, { gainDb: 1 }, { fadeFrames: 30 }, { sourceStartFrame: 50 }]) {
    assert.throws(() => placeNaturalSound(fixture, "sound", 2_000_000, { ...placement, ...change }));
  }
  const locked = placeNaturalSound(fixture, "sound", 2_000_000, placement);
  const track = locked.tracks![2];
  if ("locked" in track) track.locked = true;
  assert.throws(() => placeNaturalSound(locked, "sound", 2_000_000, placement), /bloqueada/);
});

test("cues independentes reutilizam arquivo sem sobrescrever ou reativar outros sons", () => {
  const one = placeNaturalSound(fixture, "sound", 2_000_000, placement, "cue-a");
  const two = placeNaturalSound(one, "sound", 2_000_000, { ...placement, startFrame: 45 }, "cue-b");
  const track = two.tracks!.find((item) => item.id === "audio-natural");
  if (track?.kind !== "audio") throw new Error();
  assert.equal(track.clips?.length, 2);
  const oldSecond = structuredClone(track.clips![1]);
  const disabled = setNaturalSoundEnabled(two, "cue-a", false);
  const edited = placeNaturalSound(disabled, "sound", 2_000_000, { ...placement, gainDb: -12 }, "cue-a");
  const result = edited.tracks!.find((item) => item.id === "audio-natural");
  if (result?.kind !== "audio") throw new Error();
  assert.equal(result.clips![0].enabled, false);
  assert.equal(result.clips![0].gainDb, -12);
  assert.deepEqual(result.clips![1], oldSecond);
  assert.equal(track.clips![0].enabled, true);
  assert.deepEqual(setNaturalSoundEnabled(disabled, "cue-a", true), two);
});

test("lock selecionado e limite são respeitados; lock de outro cue não impede edição", () => {
  let mixed = placeNaturalSound(fixture, "sound", 2_000_000, placement, "cue-a");
  mixed = placeNaturalSound(mixed, "sound", 2_000_000, placement, "cue-b");
  const track = mixed.tracks![2];
  if (track.kind !== "audio") throw new Error();
  track.clips![0].locked = true;
  assert.throws(() => setNaturalSoundEnabled(mixed, "cue-a", false), /bloqueado/);
  assert.throws(() => setNaturalSoundEnabled(mixed, "missing", false), /não existe/);
  assert.doesNotThrow(() => placeNaturalSound(mixed, "sound", 2_000_000, placement, "cue-b"));
  for (let index = 2; index < 32; index += 1) mixed = placeNaturalSound(mixed, "sound", 2_000_000, placement, `cue-${index}`);
  assert.throws(() => placeNaturalSound(mixed, "sound", 2_000_000, placement, "excess"), /32 sons/);
});
