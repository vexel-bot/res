import test from "node:test";
import assert from "node:assert/strict";
import { animate, patchItem, split, moveToTrack, type Timeline } from "./canonicalTimeline";
const timeline: Timeline = {
  schemaVersion: "studio.media-timeline.v1",
  frameRate: { numerator: 24, denominator: 1 },
  durationFrames: 96,
  tracks: [
    {
      id: "v",
      kind: "video",
      name: "V",
      clips: [
        {
          id: "c",
          assetId: "asset",
          playbackRate: 2,
          timeline: { startFrame: 0, durationFrames: 48 },
          source: {
            startMicroseconds: 1_000_000,
            durationMicroseconds: 4_000_000,
          },
        },
      ],
    },
  ],
};
test("splitting preserves time units, speed and source continuity", () => {
  const result = split(timeline, "c", 24, "new");
  const clips = result.tracks[0].clips!;
  assert.equal(clips.length, 2);
  assert.equal(clips[0].timeline.durationFrames, 24);
  assert.equal(clips[1].source?.startMicroseconds, 3_000_000);
  assert.equal(clips[1].source?.durationMicroseconds, 2_000_000);
  assert.equal(timeline.tracks[0].clips?.length, 1);
});
test("locked items and tracks cannot be moved and animated clips are not destructively split", () => {
  const locked = structuredClone(timeline);
  locked.tracks[0].locked = true;
  assert.deepEqual(
    patchItem(locked, "c", (i) => ({ ...i, label: "changed" })),
    locked,
  );
  const animated = patchItem(timeline, "c", (i) => animate(i, "slide", 24));
  assert.equal(split(animated, "c", 24, "new").tracks[0].clips?.length, 1);
});
test("motion presets persist valid endpoint keyframes and bounded fades", () => {
  const item = timeline.tracks[0].clips![0];
  const slide = animate(item, "slide", 24);
  assert.equal(slide.keyframes?.[0].property, "y");
  assert.equal(slide.keyframes?.at(-1)?.frame, 48);
  assert.equal(animate(item, "none", 24).transform?.fadeInFrames, 0);
  assert.equal(animate(item, "zoom", 24).keyframes?.at(-1)?.value, 1.05);
});
test("moving between compatible tracks retains one clip and clamps temporal boundaries", () => {
  const two = { ...timeline, tracks: [...timeline.tracks, { id:"second", kind:"video" as const, name:"Second", clips:[] }] };
  const moved = moveToTrack(two,"c","second",90);
  assert.equal(moved.tracks[0].clips!.length,0);
  assert.equal(moved.tracks[1].clips![0].timeline.startFrame,48);
  assert.equal(moved.tracks[1].clips![0].source?.startMicroseconds,1_000_000);
});
