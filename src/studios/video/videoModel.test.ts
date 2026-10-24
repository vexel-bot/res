import { test } from "node:test";
import assert from "node:assert/strict";
import type { AssetRecord } from "../../api/productApi";
import type { CraftDocument, CraftInspection } from "../craft/craftApi";
import {
  dimensions,
  documentBrief,
  FILM_TICKS_PER_SECOND,
  initialVideoBrief,
  jobProgress,
  motionTitleCommand,
  moveClip,
  outputAsset,
  splitClip,
  timelineTracks,
  updateVideoBrief,
  validateBrief,
  videoDocumentInput,
} from "./videoModel";

const brief = {
  ...initialVideoBrief(),
  title: "Vídeo da coleção",
  objective: "Apresentar a coleção com clareza",
  audience: "Clientes da marca",
  script: "Abertura. Demonstração. Convite.",
};
const asset = (id: string, mediaType: string): AssetRecord => ({
  id,
  title: id,
  workspaceId: "workspace-a",
  type: "upload",
  mediaType,
  createdAt: "2026-10-17T12:00:00Z",
  updatedAt: "2026-10-17T12:00:00Z",
});
function document(): CraftDocument {
  const input = videoDocumentInput("workspace-a", brief, []);
  return {
    ...input,
    schemaVersion: "studio.creative-document.v1",
    documentId: "document-a",
    workspaceId: "workspace-a",
    contentType: "video",
    revision: 4,
    version: 1,
    status: "draft",
    correlationId: "test",
    brandMemoryRef: { id: "brand-a", revision: 1 },
    createdAt: "2026-10-17T12:00:00Z",
    updatedAt: "2026-10-17T12:00:00Z",
  } as CraftDocument;
}
test("brief validation rejects empty/oversized fields and invalid durations before sending", () => {
  assert.ok(validateBrief(initialVideoBrief()));
  assert.equal(validateBrief(brief), undefined);
  for (const duration of [NaN, Infinity, 0, -1, 601])
    assert.ok(validateBrief({ ...brief, duration }));
  assert.ok(validateBrief({ ...brief, script: "x".repeat(1001) }));
});
test("aspect ratios have exact dimensions and never distort the composition", () => {
  assert.deepEqual(dimensions("9:16"), [1080, 1920]);
  assert.deepEqual(dimensions("16:9"), [1920, 1080]);
  assert.deepEqual(dimensions("1:1"), [1080, 1080]);
});
test("draft creation uses the existing canonical schema without invoking paid providers or native runtimes", () => {
  const input = videoDocumentInput("workspace-a", brief, [
    asset("v", "video/mp4"),
    asset("a", "audio/wav"),
    asset("i", "image/png"),
  ]);
  assert.equal(input.workspaceId, "workspace-a");
  assert.equal(input.contentType, "video");
  assert.equal(input.engine, undefined);
  assert.equal(input.composition.mediaTimeline?.durationFrames, 450);
  assert.deepEqual(
    input.composition.mediaTimeline?.tracks?.map((track) => track.kind),
    ["video", "audio", "video"],
  );
  assert.equal(input.assets?.length, 3);
  assert.equal(input.assets?.[0].rightsStatus, "unknown");
  assert.equal(
    input.composition.narrative?.videoStudio &&
      (input.composition.narrative.videoStudio as { engine: string }).engine,
    "filmcraft",
  );
});
test("motion and video use the same persistence; only the intended engine changes", () => {
  const input = videoDocumentInput("workspace-a", brief, [], true);
  assert.equal(
    (input.composition.narrative?.videoStudio as { engine: string }).engine,
    "effectcraft",
  );
  assert.equal(input.contentType, "video");
});
test("brief updates retain engine-owned composition, IDs, assets, references and revision", () => {
  const doc = document();
  doc.postRef = { id: "post-a" };
  const updated = updateVideoBrief(doc, {
    ...brief,
    title: "Novo nome",
    script: "Novo roteiro",
    aspect: "1:1",
    duration: 60,
  });
  assert.equal(updated.title, "Novo nome");
  assert.equal(updated.brief.angle, "Novo roteiro");
  assert.strictEqual(updated.composition, doc.composition);
  assert.strictEqual(updated.assets, doc.assets);
  assert.strictEqual(updated.postRef, doc.postRef);
  assert.equal(updated.documentId, doc.documentId);
  assert.equal(updated.revision, 4);
  assert.equal(documentBrief(updated).duration, 15);
  assert.equal(documentBrief(updated).aspect, "9:16");
});
test("project reopen respects non-30fps existing timelines", () => {
  const doc = document();
  doc.composition.mediaTimeline!.frameRate = { numerator: 25, denominator: 1 };
  doc.composition.mediaTimeline!.durationFrames = 250;
  assert.equal(documentBrief(doc).duration, 10);
});
test("canonical timeline projection contains only persisted clips and real time ranges", () => {
  const doc = {
    ...document(),
    composition: videoDocumentInput("workspace-a", brief, [
      asset("v", "video/mp4"),
    ]).composition,
  } as CraftDocument;
  const tracks = timelineTracks(undefined, doc);
  assert.equal(tracks.length, 1);
  assert.equal(tracks[0].clips[0].durationMs, 15000);
  assert.equal(tracks[0].clips[0].name, "v");
  assert.deepEqual(timelineTracks(undefined, document()), []);
});
test("native projection groups flat FilmCraft inspection clips into their actual tracks", () => {
  const inspection = {
    project: {
      layers: [
        {
          id: "2",
          name: "Trilha A",
          kind: "audio",
          properties: { muted: true },
        },
      ],
      timeline: [
        {
          id: "7",
          trackId: "2",
          kind: "audio",
          name: "Narração",
          startMs: 1200,
          durationMs: 3000,
        },
      ],
    },
  } as unknown as CraftInspection;
  const tracks = timelineTracks(inspection);
  assert.equal(tracks[0].muted, true);
  assert.equal(tracks[0].clips[0].startMs, 1200);
  assert.equal(tracks[0].clips[0].durationMs, 3000);
});
test("move and split use exact FilmCraft ticks, not frames or milliseconds", () => {
  const clip = {
    id: "7",
    trackId: "2",
    name: "Clipe",
    kind: "video",
    startMs: 1000,
    durationMs: 4000,
    properties: {},
  };
  assert.deepEqual(moveClip(clip, 2).params.moves, [
    { clip: 7, track: 2, time: FILM_TICKS_PER_SECOND * 2 },
  ]);
  assert.equal(splitClip(clip, 3).params.time, FILM_TICKS_PER_SECOND * 3);
  assert.throws(() => splitClip(clip, 1));
  assert.throws(() => splitClip(clip, 5));
  assert.throws(() => moveClip(clip, NaN));
  assert.throws(() => moveClip({ ...clip, id: "canonical-not-native" }, 2));
});
test("motion presets are atomic engine batches with result-bound real opacity keyframes", () => {
  const command = motionTitleCommand({
    preset: "lower",
    text: "Coleção",
    color: "#FF7F50",
    size: 72,
    width: 1080,
    height: 1920,
    duration: 5,
  });
  assert.equal(command.id, "engine.batch");
  assert.equal(command.params.atomic, true);
  const steps = command.params.steps as Array<{
    command: string;
    params: Record<string, unknown>;
  }>;
  assert.equal(steps[0].command, "layer.newText");
  assert.equal(steps[1].params.layer, "$1.layer");
  assert.deepEqual(
    steps.slice(1).map((step) => step.params.value),
    [0, 100, 100, 0],
  );
  assert.deepEqual(
    steps.slice(1).map((step) => step.params.time),
    [0, 0.45, 4.55, 5],
  );
  assert.throws(() =>
    motionTitleCommand({
      preset: "title",
      text: "",
      color: "#FF7F50",
      size: 72,
      width: 1080,
      height: 1920,
      duration: 5,
    }),
  );
});
test("job progress is the backend 0-100 scale, including 1 percent, and outputs require confirmed success", () => {
  assert.equal(jobProgress({ progress: 1 }), 1);
  assert.equal(jobProgress({ progress: 150 }), 100);
  assert.equal(jobProgress({ progress: -1 }), 0);
  const job = {
    status: "running" as const,
    result: { artifact: { assetId: "output-a" } },
  };
  assert.equal(outputAsset(job), undefined);
  assert.equal(outputAsset({ ...job, status: "succeeded" }), "output-a");
  assert.equal(outputAsset({ ...job, status: "failed" }), undefined);
});
