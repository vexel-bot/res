import { test } from "node:test";
import assert from "node:assert/strict";
import type { CraftCapability } from "../craft/craftApi";
import {
  audioGain,
  conversionWarnings,
  availableOperations,
  operationFields,
  primaryOperations,
  workflowHint,
} from "./videoUsability";
import type { CraftDocument, CraftInspection } from "../craft/craftApi";

const operation = (id: string, available = true) =>
  ({
    id,
    label: id,
    inputSchema: { type: "object" },
    available,
  }) as CraftCapability;
test("only confirmed existing commands enter the primary tools; unsupported commands are not invented", () => {
  const operations = [
    operation("timeline.trim"),
    operation("captions.add"),
    operation("layer.newText", false),
    operation("host.history.undo"),
    operation("file.import"),
    operation("timeline.custom"),
  ];
  assert.deepEqual(
    primaryOperations(operations, "clip").map((command) => command.id),
    ["timeline.trim"],
  );
  assert.deepEqual(primaryOperations(operations, "text"), []);
  assert.deepEqual(
    availableOperations(operations, "captions").map((command) => command.id),
    ["captions.add"],
  );
  assert.ok(
    availableOperations(operations, "clip").some(
      (command) => command.id === "timeline.custom",
    ),
  );
  assert.ok(
    !availableOperations(operations, "clip").some((command) =>
      /^(host|file)\./.test(command.id),
    ),
  );
});
test("native audio gain and keyframe tools remain available in their own groups", () => {
  const operations = [
    operation("clip.audioGain"),
    operation("timeline.setTrack"),
    operation("prop.addKey"),
    operation("sequence.applyVideoTransition"),
  ];
  assert.deepEqual(
    primaryOperations(operations, "audio").map((command) => command.id),
    ["clip.audioGain", "timeline.setTrack"],
  );
  assert.deepEqual(
    primaryOperations(operations, "effects").map((command) => command.id),
    ["prop.addKey", "sequence.applyVideoTransition"],
  );
});
test("advanced disclosure groups fields without dropping required parameters, defaults, constraints or metadata", () => {
  const schema = {
    type: "object",
    description: "Native command",
    required: ["clips", "db"],
    additionalProperties: true,
    properties: {
      clips: { type: "array", items: { type: "integer" } },
      db: { type: "number", minimum: -60, maximum: 12 },
      mode: { type: "string", default: "set" },
      technicalFlag: { type: "boolean", default: false },
      transform: { type: "object", properties: { x: { type: "number" } } },
    },
  };
  const result = operationFields(schema);
  assert.deepEqual(Object.keys(result.main.properties), [
    "clips",
    "db",
    "mode",
  ]);
  assert.deepEqual(Object.keys(result.advanced.properties), [
    "technicalFlag",
    "transform",
  ]);
  assert.strictEqual(result.main.properties.db, schema.properties.db);
  assert.strictEqual(
    result.advanced.properties.transform,
    schema.properties.transform,
  );
  assert.deepEqual(result.main.required, schema.required);
  assert.equal(result.main.description, schema.description);
  assert.deepEqual(
    Object.keys({ ...result.main.properties, ...result.advanced.properties }),
    Object.keys(schema.properties),
  );
});
test("audio quick control uses the real native contract and rejects invalid selection or excessive gain", () => {
  const clip = {
    id: "42",
    trackId: "3",
    name: "Narração",
    kind: "audio",
    startMs: 0,
    durationMs: 1500,
    properties: {},
  };
  assert.deepEqual(audioGain(clip, -6), {
    id: "clip.audioGain",
    params: { clips: [42], db: -6, mode: "set" },
  });
  for (const db of [NaN, Infinity, -61, 13])
    assert.throws(() => audioGain(clip, db));
  assert.throws(() => audioGain({ ...clip, id: "canonical-id" }, 0));
});
test("workflow guidance differentiates an empty editor from persisted drafts and a working native motor", () => {
  assert.match(workflowHint("editor", false, false).text, /projeto|produção/);
  assert.match(workflowHint("editor", true, false).text, /motor nativo/);
  assert.match(workflowHint("editor", true, true).text, /inspetor/);
  assert.match(
    workflowHint("ai", false, false).text,
    /quando motor e conexão estiverem disponíveis/,
  );
  assert.match(workflowHint("motion", true, false).text, /keyframes nativos/);
  assert.match(workflowHint("ad", false, false).text, /biblioteca/);
});
test("conversion warnings retain original fidelity notes without mixing documents or stale inspections", () => {
  const doc = {
    documentId: "video-1",
    revision: 3,
    nativeEditorState: { migrationWarnings: ["Confira a máscara"] },
  } as CraftDocument;
  const inspection = {
    documentId: "video-1",
    revision: 3,
    migrationWarnings: ["Confira a máscara", "Confira os grupos"],
    project: { warnings: ["Confira o áudio"] },
  } as CraftInspection;
  assert.deepEqual(conversionWarnings(doc, inspection), [
    "Confira a máscara",
    "Confira os grupos",
    "Confira o áudio",
  ]);
  assert.deepEqual(
    conversionWarnings(doc, { ...inspection, documentId: "outro" }),
    ["Confira a máscara"],
  );
  assert.deepEqual(conversionWarnings(doc, { ...inspection, revision: 2 }), [
    "Confira a máscara",
  ]);
});
