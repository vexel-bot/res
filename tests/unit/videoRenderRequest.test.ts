import assert from "node:assert/strict";
import test from "node:test";
import type { StudioDocumentRecord } from "../../src/api/productApi";
import { videoRenderRequest } from "../../src/studios/videoRenderRequest";

function document(narrative: Record<string, unknown> = {}) {
  return {
    workspaceId: "workspace", documentId: "document", revision: 7, version: 2,
    composition: { narrative, pages: [{ id: "page", width: 1920, height: 1080 }],
      mediaTimeline: { frameRate: { numerator: 24000, denominator: 1001 } } },
  } as unknown as StudioDocumentRecord;
}

test("output action preserves the contextual plan, native engine, canvas and revision", () => {
  const source = document({ contextualPlanId: "plan", editorialV2: { renderer: "remotion.contextual-v2" } });
  const before = JSON.stringify(source);
  const request = videoRenderRequest(source);
  assert.equal(request.provider, "remotion.contextual-v2");
  assert.equal(request.contextualPlanId, "plan");
  assert.equal(request.output.width, 1920);
  assert.equal(request.output.height, 1080);
  assert.equal(request.output.fps, 24000 / 1001);
  assert.equal(request.output.quality, "high");
  assert.equal(request.expectedDocumentRevision, 7);
  assert.equal(request.expectedDocumentVersion, 2);
  assert.equal(JSON.stringify(source), before);
  assert.deepEqual(videoRenderRequest(source, "plan"), request);
});

test("legacy contextual and UGC retain their existing routes", () => {
  assert.equal(videoRenderRequest(document({ contextualPlanId: "legacy" })).provider, "builtin.ffmpeg-contextual-v1");
  assert.equal(videoRenderRequest(document({ contextualPlanId: "v2", editorialV2: {} })).provider, "hyperframes.contextual-v2");
  const request = videoRenderRequest(document());
  assert.equal(request.provider, "builtin.ffmpeg-ugc-v1");
  assert.equal(request.contextualPlanId, undefined);
  assert.equal(request.output.quality, "draft");
  assert.deepEqual([request.output.width, request.output.height], [1080, 1920]);
});

test("unavailable bound engines are retained, never silently replaced", () => {
  const request = videoRenderRequest(document({ contextualPlanId: "plan", editorialV2: { renderer: "alight-motion.contextual-v1" } }));
  assert.equal(request.provider, "alight-motion.contextual-v1");
  assert.equal(request.contextualPlanId, "plan");
});

test("invalid or mismatched bindings stop before a generation request", () => {
  assert.throws(() => videoRenderRequest(document({ editorialV2: { renderer: "remotion.contextual-v2" } })), /plano associado/);
  assert.throws(() => videoRenderRequest(document({ contextualPlanId: "" })), /inválido/);
  assert.throws(() => videoRenderRequest(document({ contextualPlanId: 42 })), /inválido/);
  assert.throws(() => videoRenderRequest(document({ contextualPlanId: "plan" }), "other-plan"), /não corresponde/);
  assert.throws(() => videoRenderRequest(document({ contextualPlanId: "plan", editorialV2: { renderer: "builtin.ffmpeg-ugc-v1" } })), /não é suportado/);
  assert.throws(() => videoRenderRequest(document({ contextualPlanId: "plan", editorialV2: { renderer: "unknown-engine" } })), /não é suportado/);
});
