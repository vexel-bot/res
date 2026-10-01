import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { canSubmitEditorialReview, editorialBlockerLabel, validateEditorialPlan, verifyEditorialBlob } from "../../src/studios/editorialReview";
import type { EditorialPlanInput, EditorialReadiness } from "../../src/api/productApi";

test("o plano exige ação, razão do corte e evidência do documento", () => {
  const plan: EditorialPlanInput = { expectedDocumentRevision: 1, workflow: "ugc-avatar", objective: "Demonstrar", cta: "Solicitar",
    beats: [{ id: "b1", message: "Mudança", visualAction: "Comparar estados", editReason: "Mostrar consequência", evidenceAssetIds: ["a"] }] };
  assert.equal(validateEditorialPlan(plan, new Set(["a"])), undefined);
  assert.match(validateEditorialPlan(plan, new Set(["other"])), /evidências/);
  plan.beats[0].visualAction = "  ";
  assert.match(validateEditorialPlan(plan, new Set(["a"])), /ação visual/);
  plan.beats = [];
  assert.match(validateEditorialPlan(plan, new Set(["a"])), /1 a 40/);
});

test("rejeições podem ser revistas; plano obsoleto ou ausente não pode", () => {
  const state = { managed: true, plan: { id: "p1" }, blockers: ["editorial_voice_rejected"] } as EditorialReadiness;
  assert.equal(canSubmitEditorialReview(state), true);
  state.blockers.push("editorial_plan_stale");
  assert.equal(canSubmitEditorialReview(state), false);
  assert.equal(canSubmitEditorialReview(undefined), false);
  assert.match(editorialBlockerLabel("editorial_voice_rejected"), /Voz: rejeitado/);
  assert.match(editorialBlockerLabel("editorial_assets_changed"), /origem/);
});

test("prévia só aceita os bytes cujo checksum foi registrado", async () => {
  const text = "private technical fixture";
  const hash = createHash("sha256").update(text).digest("hex");
  await verifyEditorialBlob(new Blob([text]), hash.toUpperCase());
  await assert.rejects(verifyEditorialBlob(new Blob(["tampered"]), hash), /Checksum divergente/);
  await assert.rejects(verifyEditorialBlob(new Blob([text]), ""), /checksum válido/);
});
