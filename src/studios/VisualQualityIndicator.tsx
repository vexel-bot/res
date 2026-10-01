import React from "react";
import { apiFetch } from "../api";
import type { StudioDocumentRecord } from "../api/productApi";
import { VisualComparisonPanel } from "./VisualComparisonPanel";
import "./visual-quality-indicator.css";

type QualityRender = {
  runId: string; documentId: string; documentRevision: number; assetId?: string;
  qualityPhaseId?: string; renderChecksum?: string;
  technicalStatus: string; visualStatus: string; autonomyStatus: string;
  recordedManualInterventions: number;
  humanScores?: Record<string, number | null>; blockers: string[];
  findings: { cause: string; startSeconds: number; endSeconds: number; observation: string; correction: string }[];
};
type QualityProgram = {
  baseline: { visualStatus: string; humanScores: null; limitations: string[]; renders: { brief: string; variant: string; sha256: string }[] };
  targetBriefs: number; phaseStatus: string;
  budget: { limitUsd: number; committedOrReservedUsd: number; attempts: number; remainingUsd: number };
  progress: { distinctBriefs: number; materialsReady: number; rendered: number; visualApproved: number; comparisonPassed: number };
  cases: { documentId: string; title: string; materials: { status: string; blockers: string[] }; renderStatus: string;
    visualStatus: string; comparisonStatus: string }[];
  renders: QualityRender[];
};

const visualLabels: Record<string, string> = {
  not_assessed: "não avaliado", correction_needed: "correção necessária", rejected: "reprovado", approved: "aprovado",
};
const blockerLabels: Record<string, string> = {
  brief_missing: "briefing ausente", brand_identity_missing: "identidade da marca ausente",
  two_distinct_action_sources_required: "faltam dois planos de ação distintos e autorizados",
  observable_action_evidence_missing: "descreva a ação observável na proveniência de dois vídeos",
  authorized_product_or_brand_asset_missing: "falta produto ou marca real autorizada",
  current_render_human_review_missing: "revisão humana desta versão pendente",
  full_playback_and_mobile_review_required: "conferência completa e em celular pendente",
  four_human_scores_required: "faltam notas humanas nos quatro eixos",
  document_revision_stale: "render de uma revisão anterior",
  render_checksum_mismatch: "checksum do render divergente",
  render_document_binding_mismatch: "render vinculado a outro documento ou revisão",
  render_missing: "render pendente", technical_qc_not_passed: "QC técnico pendente ou reprovado",
};

export function VisualQualityIndicator({ document, runId, enabled, refreshKey }: {
  document?: StudioDocumentRecord; runId?: string; enabled: boolean; refreshKey?: number;
}) {
  const [program, setProgram] = React.useState<QualityProgram>();
  const [error, setError] = React.useState("");
  const [comparisonRevision, setComparisonRevision] = React.useState(0);
  const workspaceId = document?.workspaceId;
  const scope = `${workspaceId}:${document?.documentId}:${document?.revision}`;
  const [loadedScope, setLoadedScope] = React.useState<string>();
  React.useEffect(() => {
    if (!enabled || !workspaceId) return;
    const controller = new AbortController();
    apiFetch<QualityProgram>(`/api/v1/studios/v1/workspaces/${encodeURIComponent(workspaceId)}/visual-quality`,
      { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) { setProgram(value); setLoadedScope(scope); setError(""); } })
      .catch(cause => {
        if (controller.signal.aborted) return;
        if (cause?.status === 403 || cause?.status === 404) { setProgram(undefined); setError(""); return; }
        setError("Não foi possível consultar o indicador visual.");
        setLoadedScope(scope);
      });
    return () => controller.abort();
  }, [workspaceId, scope, enabled, refreshKey, comparisonRevision]);
  if (!enabled || loadedScope !== scope || (!program && !error)) return null;
  const current = program?.renders.find(item => item.runId === runId);
  return <section className="vs-visual-quality" aria-label="Indicador interno de qualidade visual">
    <h3>Qualidade visual · fase experimental</h3>
    <p>QC técnico, avaliação visual e autonomia são evidências diferentes. Nenhuma nota é preenchida automaticamente.</p>
    {error && <p role="alert">{error}</p>}
    {program && <>
      <p className="vs-visual-quality-baseline">Ensaio anterior: <strong>reprovado visualmente</strong> · seis fixtures sintéticos,
        quatro segundos, formato quadrado e sem áudio. QC técnico passou; não houve nota humana numérica.</p>
      <dl>
        <div><dt>APIs da fase</dt><dd>US$ {program.budget.committedOrReservedUsd.toFixed(2)}/{program.budget.limitUsd.toFixed(2)} · {program.budget.attempts} tentativas</dd></div>
        <div><dt>Briefs distintos</dt><dd>{program.progress.distinctBriefs}/{program.targetBriefs}</dd></div>
        <div><dt>Materiais prontos</dt><dd>{program.progress.materialsReady}/{program.targetBriefs}</dd></div>
        <div><dt>Renderizados</dt><dd>{program.progress.rendered}/{program.targetBriefs}</dd></div>
        <div><dt>Visual aprovado</dt><dd>{program.progress.visualApproved}/{program.targetBriefs}</dd></div>
        <div><dt>Comparação aprovada</dt><dd>{program.progress.comparisonPassed}/{program.targetBriefs}</dd></div>
      </dl>
      <p>Fase: <strong>{program.phaseStatus === "validated" ? "validada" : "pendente de evidência"}</strong>.</p>
      {current && <article aria-label="Qualidade do render atual">
        <h4>Render atual · SHA {current.renderChecksum?.slice(0, 12) ?? "pendente"}</h4>
        <p>QC técnico: <strong>{current.technicalStatus}</strong> · visual: <strong>{visualLabels[current.visualStatus] ?? current.visualStatus}</strong> · autonomia: <strong>{current.autonomyStatus === "assisted" ? "assistida" : current.autonomyStatus}</strong> ({current.recordedManualInterventions} revisões manuais registradas).</p>
        {current.humanScores && <p>Notas humanas: {Object.entries(current.humanScores).map(([key, value]) => `${key} ${value ?? "—"}`).join(" · ")}.</p>}
        {current.blockers.map(code => <p key={code}>{blockerLabels[code] ?? code}.</p>)}
        {current.findings.map((finding, index) => <p key={`${index}-${finding.startSeconds}`}>
          {finding.startSeconds.toFixed(1)}–{finding.endSeconds.toFixed(1)} s · {finding.cause}: {finding.observation} → {finding.correction}
        </p>)}
      </article>}
      <details><summary>Projetos e materiais pendentes</summary>
        {program.cases.length ? program.cases.map(item => <article key={item.documentId}>
          <b>{item.title}</b><p>Materiais: {item.materials.status} · render: {item.renderStatus} · visual: {visualLabels[item.visualStatus] ?? item.visualStatus} · comparação: {item.comparisonStatus}.</p>
          {item.materials.blockers.map(code => <p key={code}>{blockerLabels[code] ?? code}.</p>)}
        </article>) : <p>Nenhum projeto de vídeo elegível neste workspace.</p>}
      </details>
      {document && <VisualComparisonPanel document={document} renders={program.renders}
        onRecorded={() => setComparisonRevision(value => value + 1)} />}
    </>}
  </section>;
}
