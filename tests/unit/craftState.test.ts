import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { commandValidation, craftRecoveryKey, readCraftRecovery, initialCommandParams, safeCraftMode, frameCount, studioHeadlines } from "../../src/studios/craft/craftState";
import type { CraftRecovery } from "../../src/studios/craft/craftState";
import type { CraftInspection } from "../../src/studios/craft/craftApi";

const scope = { userId: "user/one", workspaceId: "workspace", documentId: "doc:one", engine: "photocraft" as const };
const recovery: CraftRecovery = { ...scope, schemaVersion: "clicko.craft-recovery.v1", expectedRevision: 3,
  idempotencyKey: "original-request-key", pageId: "page-two", commands: [{ id: "type.setText", params: { layer: "title", text: "Nova direção" } }], updatedAt: "2026-10-11T12:00:00Z" };

test("recovery is isolated by account, workspace, document and motor, and retains the active page", () => {
  assert.deepEqual(readCraftRecovery(JSON.stringify(recovery), scope), recovery);
  for (const field of ["userId", "workspaceId", "documentId", "engine"]) assert.equal(readCraftRecovery(JSON.stringify(recovery), { ...scope, [field]: "other" }), undefined);
  assert.notEqual(craftRecoveryKey("a:b", "c", "d", "photocraft"), craftRecoveryKey("a", "b:c", "d", "photocraft"));
  assert.equal(readCraftRecovery("{bad json", scope), undefined);
  assert.equal(readCraftRecovery(JSON.stringify({ ...recovery, commands: [{ id: "a", params: null }] }), scope), undefined);
  assert.equal(readCraftRecovery(JSON.stringify({ ...recovery, expectedRevision: -1 }), scope), undefined);
});

test("recovery preserves request identity for retry after an interrupted commit", () => {
  const saved = readCraftRecovery(JSON.stringify({ ...recovery, attempted: true }), scope)!;
  assert.equal(saved.idempotencyKey, recovery.idempotencyKey);
  assert.equal(saved.expectedRevision, 3);
  assert.equal(saved.pageId, "page-two");
  assert.equal(saved.attempted, true);
});

test("manual controls seed real upstream selection parameters and nested defaults", () => {
  assert.deepEqual(initialCommandParams({ required: ["style"], properties: { layer: { type: "string" }, clipId: { type: "string" }, x: { type: "number", default: 0 }, other: { type: "string" }, style: { type: "object", properties: { opacity: { type: "number", default: 1 } } } } }, "native-id"), { layer: "native-id", clipId: "native-id", x: 0, style: { opacity: 1 } });
  assert.deepEqual(initialCommandParams({ required: ["rect"], properties: { layer: { type: "integer" }, clipId: { type: "integer" }, rect: { type: "array", minItems: 4, maxItems: 4, items: { type: "number" } } } }, "42"), { layer: 42, clipId: 42, rect: [0, 0, 0, 0] });
  assert.deepEqual(initialCommandParams({ properties: { layer: { type: "integer" } } }, "not-a-number"), {});
});

test("changing a single property never resets optional position or scale vectors", () => {
  const params = initialCommandParams({ required: ["layer"], properties: {
    layer: { type: "integer" }, position: { type: "array", minItems: 3, items: { type: "number" } },
    scale: { type: "array", minItems: 3, items: { type: "number" } }, rotation: { type: "number" },
  } }, "42");
  assert.deepEqual({ ...params, rotation: 30 }, { layer: 42, rotation: 30 });
});

test("required fields, numeric limits and nested array values are checked before sending", () => {
  const schema = { required: ["name"], properties: { name: { type: "string" }, opacity: { type: "number", minimum: 0, maximum: 1 }, mode: { enum: ["regular", "ripple"] }, points: { type: "array", items: { type: "object", required: ["x"], properties: { x: { type: "integer" } } } } } };
  assert.match(commandValidation(schema, {})!, /name/);
  assert.match(commandValidation(schema, { name: "Shape", opacity: 2 })!, /máximo/);
  assert.match(commandValidation(schema, { name: "Shape", mode: "invented" })!, /válido/);
  assert.match(commandValidation(schema, { name: "Shape", points: [{}] })!, /x/);
  assert.match(commandValidation(schema, { name: "Shape", points: [{ x: 1.5 }] })!, /número/);
  assert.equal(commandValidation(schema, { name: "Shape", opacity: 0, points: [{ x: 1 }] }), undefined);
  const vector = { properties: { rect: { type: "array", minItems: 4, maxItems: 4, items: { type: "number" } } } };
  assert.match(commandValidation(vector, { rect: [0, 0] })!, /4 valores/);
  assert.match(commandValidation(vector, { rect: [0, 0, 10, 10, 10] })!, /máximo/);
});

test("studio routes select Craft motors and native frame units", () => {
  assert.equal(safeCraftMode("carousel"), "photocraft");
  assert.equal(safeCraftMode("video"), "filmcraft");
  assert.equal(safeCraftMode("effects"), "effectcraft");
  assert.equal(frameCount({ project: { fps: 30, durationMs: 1000 } } as CraftInspection), 29);
  assert.equal(frameCount(undefined), 0);
  assert.deepEqual(studioHeadlines({ composition: { pages: [{ layers: [{ kind: "text", properties: { text: "Arquivo preservado" } }] }] } }), ["Arquivo preservado"]);
});

test("Clicko media tabs use the imported Studio while preserving previous module sources", () => {
  const app = readFileSync(resolve("src/App.tsx"), "utf8");
  const bridge = readFileSync(resolve("src/studios/ClickoStudioView.tsx"), "utf8");
  const workspace = readFileSync(resolve("src/studios/StudiosWorkspace.tsx"), "utf8");
  assert.ok(app.includes('<StudiosWorkspace'));
  assert.ok(workspace.includes('<ClickoStudioView'));
  assert.ok(workspace.includes('module='));
  assert.ok(bridge.includes("<ImageStudio"));
  assert.ok(bridge.includes("<VideoStudio"));
  const imageStudio = readFileSync(resolve("src/studios/image/ImageStudio.tsx"), "utf8");
  assert.ok(imageStudio.includes("<DepartmentStudio"));
  assert.ok(imageStudio.includes("<CraftStudio"));
  for (const file of ["src/components/ImageStudioView.tsx", "src/components/VideoEditorView.tsx"]) assert.equal(existsSync(resolve(file)), true, file);
});
