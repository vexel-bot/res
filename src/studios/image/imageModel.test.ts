import { test } from "node:test";
import assert from "node:assert/strict";
import type {
  AssetRecord,
  StudioGenerationJobRecord,
} from "../../api/productApi";
import type { CraftDocument } from "../craft/craftApi";
import {
  authorizeImageInputs,
  imageDimensions,
  imageDocumentInput,
  imageDraftError,
  imageDraftFromDocument,
  imageJobInput,
  imageJobOperation,
  imagePrompt,
  imageResultId,
  imageSourceReferences,
  imageUploadError,
  initialImageDraft,
  readPendingImageRequest,
  requiresImageReview,
  updateImageBrief,
} from "./imageModel";
const draft = () => ({
  ...initialImageDraft(),
  title: "Produto da marca",
  prompt: "Fotografia de um produto sobre pedra clara",
  preserve: "Cores do produto\nLogotipo",
  additional: "Luz lateral suave",
});
const document = () =>
  ({
    ...imageDocumentInput("ws-image", draft()),
    schemaVersion: "studio.creative-document.v1",
    brandMemoryRef: { id: "brand", revision: 1 },
    documentId: "doc-image",
    revision: 3,
    version: 1,
    status: "draft",
    actorId: "user",
    createdAt: "",
    updatedAt: "",
    review: {},
  }) as unknown as CraftDocument;
const asset = (id = "source") =>
  ({
    id,
    workspaceId: "ws-image",
    title: "Produto.png",
    mediaType: "image/png",
    checksumSha256: "a".repeat(64),
    sizeBytes: 100,
    metadata: {},
  }) as AssetRecord;

test("image drafts validate the persisted brief limits and preservation instructions", () => {
  assert.equal(imageDraftError(draft()), undefined);
  assert.ok(imageDraftError(initialImageDraft()));
  assert.ok(imageDraftError({ ...draft(), prompt: "x".repeat(1001) }));
  assert.ok(
    imageDraftError({
      ...draft(),
      preserve: Array(31).fill("Preservar").join("\n"),
    }),
  );
  assert.ok(imageDraftError({ ...draft(), aspect: "inventado" }));
});
test("image uploads accept only compatible images and bound local input size", () => {
  for (const type of ["image/png", "image/jpeg", "image/webp"])
    assert.equal(imageUploadError({ type, size: 200 }), undefined);
  for (const file of [
    { type: "image/svg+xml", size: 200 },
    { type: "video/mp4", size: 200 },
    { type: "image/png", size: 0 },
    { type: "image/png", size: 12 * 1024 * 1024 + 1 },
  ])
    assert.ok(imageUploadError(file));
});
test("draft creation uses canonical storage without invoking a provider or requiring native runtime", () => {
  const input = imageDocumentInput("ws-image", draft());
  assert.equal(input.contentType, "visual");
  assert.equal(input.engine, undefined);
  assert.deepEqual(input.assets, []);
  assert.deepEqual(imageDimensions("4:5"), [1080, 1350]);
  assert.equal(input.composition.pages[0].layers.length, 0);
  assert.notEqual(
    input.correlationId,
    imageDocumentInput("ws-image", draft()).correlationId,
  );
});
test("brief updates retain native composition, links, evidence and review authorities", () => {
  const doc = document();
  doc.nativeEditorState = {
    engine: "photocraft",
    checksumSha256: "b".repeat(64),
  } as CraftDocument["nativeEditorState"];
  doc.brief.audience = "Público já registrado";
  doc.brief.hypotheses = ["Hipótese preservada"];
  const updated = updateImageBrief(doc, {
    ...draft(),
    aspect: "9:16",
    prompt: "Uma nova descrição autorizada",
  });
  assert.strictEqual(updated.composition, doc.composition);
  assert.strictEqual(updated.nativeEditorState, doc.nativeEditorState);
  assert.strictEqual(updated.assets, doc.assets);
  assert.equal(updated.brief.audience, doc.brief.audience);
  assert.deepEqual(updated.brief.hypotheses, doc.brief.hypotheses);
  assert.equal(imageDraftFromDocument(updated).aspect, "9:16");
  assert.equal(imageDraftFromDocument(updated).preserve, draft().preserve);
});
test("source/reference selection persists without dropping dependencies or automatically certifying rights", () => {
  const refs = [
    {
      id: "dependency",
      mediaType: "image/png",
      origin: "workspace",
      rightsStatus: "unknown" as const,
      provenance: { keep: true },
    },
  ];
  const next = imageSourceReferences(
    refs,
    "source",
    ["reference"],
    [asset(), asset("reference")],
  );
  assert.equal(next.length, 3);
  assert.deepEqual(next[0], refs[0]);
  assert.equal(next[1].rightsStatus, "unknown");
  assert.equal(next[1].provenance.imageStudioRole, "source");
  assert.equal(next[2].provenance.imageStudioRole, "reference");
  assert.doesNotThrow(() =>
    imageSourceReferences([{ ...refs[0], provenance: undefined }], undefined, [], []),
  );
  assert.throws(() => imageSourceReferences([], "missing", [], []));
});
test("sending image inputs requires explicit authorization and never overrides restricted or unreviewed materials", () => {
  const item = asset();
  const refs = imageSourceReferences([], item.id, [], [item]);
  assert.throws(() =>
    authorizeImageInputs(
      refs,
      [item.id],
      [item],
      false,
      "Arquivo próprio",
      "user",
    ),
  );
  assert.throws(() =>
    authorizeImageInputs(refs, [item.id], [item], true, "", "user"),
  );
  assert.throws(() =>
    authorizeImageInputs(
      [{ ...refs[0], rightsStatus: "restricted" }],
      [item.id],
      [item],
      true,
      "Autorizado",
      "user",
    ),
  );
  assert.throws(() =>
    authorizeImageInputs(
      refs,
      [item.id],
      [
        {
          ...item,
          metadata: { generationJobId: "job", visualReview: "pending" },
        },
      ],
      true,
      "Autorizado",
      "user",
    ),
  );
  const approved = authorizeImageInputs(
    refs,
    [item.id],
    [item],
    true,
    "Fotografia própria",
    "user",
  );
  assert.equal(approved[0].rightsStatus, "verified");
  assert.equal(approved[0].provenance.imageStudioRole, "source");
  assert.equal(approved[0].provenance.declaredBy, "user");
  assert.equal(refs[0].rightsStatus, "unknown");
  assert.strictEqual(
    authorizeImageInputs(
      approved,
      [item.id],
      [item],
      true,
      "Fotografia própria",
      "user",
    ),
    approved,
  );
});
test("real image jobs bind revision, original and at most three references to the existing contract", () => {
  const doc = document();
  const images = [asset(), asset("a"), asset("b"), asset("c"), asset("d")];
  doc.assets = authorizeImageInputs(
    [],
    images.map((item) => item.id),
    images,
    true,
    "Arquivos próprios",
    "user",
  );
  const input = imageJobInput(doc, "edit", draft(), "source", [
    "source",
    "a",
    "a",
  ]);
  assert.equal(input.operation, "edit_image");
  assert.equal(input.expectedDocumentRevision, 3);
  assert.deepEqual(input.referenceAssetIds, ["a"]);
  assert.equal(input.sourceAssetId, "source");
  assert.throws(() => imageJobInput(doc, "edit", draft(), undefined, []));
  assert.throws(() =>
    imageJobInput(doc, "create", draft(), undefined, ["a", "b", "c", "d"]),
  );
  assert.throws(() => imageJobInput(document(), "edit", draft(), "source", []));
  assert.deepEqual(
    imageJobInput(doc, "create", draft(), "source", ["source"])
      .referenceAssetIds,
    ["source"],
  );
  assert.equal("model" in input, false);
  assert.equal("quality" in input, false);
  assert.equal("width" in input, false);
});
test("KLIC/brand directions never silently change the user prompt and brand inclusion is opt-in", () => {
  const current = draft();
  const original = current.prompt;
  assert.ok(!imagePrompt(current, "MARCA PRIVADA").includes("MARCA PRIVADA"));
  assert.match(
    imagePrompt({ ...current, brand: true }, "MARCA PRIVADA"),
    /MARCA PRIVADA/,
  );
  assert.equal(current.prompt, original);
});
test("result display requires a confirmed succeeded job with an actual asset ID", () => {
  for (const status of ["queued", "running", "failed", "cancelled"] as const)
    assert.equal(
      imageResultId({ status, result: { assetId: "real" } }),
      undefined,
    );
  assert.equal(imageResultId({ status: "succeeded", result: {} }), undefined);
  assert.equal(
    imageResultId({ status: "succeeded", result: { assetId: "real" } }),
    "real",
  );
  assert.equal(
    imageJobOperation({
      request: { input: { operation: "generate_video" } },
    } as unknown as StudioGenerationJobRecord),
    undefined,
  );
  assert.equal(
    requiresImageReview({
      ...asset(),
      metadata: { generationJobId: "job", visualReview: "failed" },
    }),
    true,
  );
  assert.equal(
    requiresImageReview({
      ...asset(),
      metadata: { generationJobId: "job", visualReview: "passed" },
    }),
    false,
  );
});
test("uncertain image submission recovery retains exact identity and rejects malformed or unsupported payloads", () => {
  const value = {
    documentId: "doc",
    key: "same-request-key",
    input: imageJobInput(document(), "create", draft(), undefined, []),
  };
  assert.deepEqual(
    readPendingImageRequest(JSON.stringify(value)),
    JSON.parse(JSON.stringify(value)),
  );
  for (const bad of [
    null,
    "{",
    JSON.stringify({ ...value, key: "bad" }),
    JSON.stringify({
      ...value,
      input: { ...value.input, operation: "generate_video" },
    }),
    JSON.stringify({
      ...value,
      input: { ...value.input, expectedDocumentRevision: 0 },
    }),
  ])
    assert.equal(readPendingImageRequest(bad), undefined);
});
