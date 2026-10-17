import type { EditorialPlanInput, EditorialReadiness, EditorialReviewInput } from "../api/productApi";
import { BackendRequestError } from "../api/client";

export const editorialAxes: Array<{ id: EditorialReviewInput["axis"]; label: string }> = [
  { id: "proof", label: "Prova do produto" }, { id: "script", label: "Roteiro" },
  { id: "storyboard", label: "Storyboard" }, { id: "animatic", label: "Animatic" },
  { id: "voice", label: "Voz" }, { id: "face", label: "Rosto e atuação" },
  { id: "scenario", label: "Cenário" },
];

export function editorialBlockerLabel(code: string): string {
  const fixed: Record<string, string> = {
    editorial_plan_not_registered: "Este documento ainda não está inscrito no fluxo UGC/avatar.",
    editorial_plan_stale: "O documento mudou. Registre um novo plano e revise suas evidências.",
    editorial_assets_changed: "A origem ou os dados dos assets mudaram. O plano está desatualizado.",
    editorial_assets_unavailable: "Uma fonte está ausente, excluída ou com checksum divergente.",
    editorial_plan_conflict: "O plano mudou. Atualize o estado antes de revisar.",
    editorial_document_conflict: "A revisão do documento mudou. Recarregue o documento antes de registrar.",
    editorial_evidence_missing: "A evidência não está mais disponível.",
    editorial_evidence_changed: "Os bytes da evidência não correspondem ao checksum registrado.",
    editorial_evidence_too_large: "A evidência ultrapassa o limite de 100 MiB.",
    editorial_idempotency_conflict: "Esta operação já foi registrada com outro conteúdo. Atualize o estado.",
    identity_governance_role_required: "Somente owner ou admin pode registrar planos e decisões.",
  };
  if (fixed[code]) return fixed[code];
  for (const axis of editorialAxes) {
    if (code === `editorial_${axis.id}_pending`) return `${axis.label}: revisão pendente.`;
    if (code === `editorial_${axis.id}_rejected`) return `${axis.label}: rejeitado na revisão vigente.`;
  }
  return code;
}

export function editorialError(error: unknown): string {
  if (error instanceof BackendRequestError) {
    const body = error.detail as { detail?: { code?: string } } | undefined;
    if (body?.detail?.code) return editorialBlockerLabel(body.detail.code);
    if (error.status === 403) return "Somente owner ou admin pode registrar esta decisão.";
    if (error.status === 404) return "Documento ou recurso editorial indisponível neste workspace.";
  }
  return error instanceof Error ? error.message : "Não foi possível consultar o controle editorial.";
}

export function canSubmitEditorialReview(state?: EditorialReadiness): boolean {
  return Boolean(state?.managed && state.plan && !(state.blockers ?? []).some((code) =>
    ["editorial_plan_stale", "editorial_assets_changed", "editorial_assets_unavailable"].includes(code)));
}

export function validateEditorialPlan(plan: EditorialPlanInput, assetIds: Set<string>): string | undefined {
  if (!plan.objective.trim() || !plan.cta.trim()) return "Preencha objetivo e CTA.";
  if (!plan.beats.length || plan.beats.length > 40) return "O plano deve ter de 1 a 40 beats.";
  if (new Set(plan.beats.map((beat) => beat.id)).size !== plan.beats.length) return "Os beats precisam de IDs únicos.";
  for (const [index, beat] of plan.beats.entries()) {
    if (![beat.message, beat.visualAction, beat.editReason].every((text) => text.trim()))
      return `Preencha mensagem, ação visual e motivo do corte do beat ${index + 1}.`;
    if (!beat.evidenceAssetIds.length || beat.evidenceAssetIds.some((id) => !assetIds.has(id)))
      return `Selecione evidências do documento para o beat ${index + 1}.`;
  }
}

export async function verifyEditorialBlob(blob: Blob, checksum: string): Promise<void> {
  if (!/^[a-f0-9]{64}$/i.test(checksum)) throw new Error("A evidência não tem checksum válido.");
  if (blob.size > 100 * 1024 * 1024) throw new Error("A evidência ultrapassa o limite de 100 MiB.");
  const hash = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  const actual = Array.from(new Uint8Array(hash), (value) => value.toString(16).padStart(2, "0")).join("");
  if (actual !== checksum.toLowerCase()) throw new Error("Checksum divergente: a prévia foi bloqueada.");
}
