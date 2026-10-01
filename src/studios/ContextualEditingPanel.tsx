import React from "react";
import { apiFetch, apiFetchBlob } from "../api";
import type { StudioDocumentRecord } from "../api/productApi";
import { EditingResourcesPanel } from "./EditingResourcesPanel";
import { VisualAuditPanel, type VisualAudit } from "./VisualAuditPanel";
import { VisualQualityIndicator } from "./VisualQualityIndicator";
import { EditingMaterialRequests, needFromRequest, type MaterialNeed, type MaterialRequest } from "./EditingMaterialRequests";

type Plan = {
  schemaVersion?: string;
  direction?: { scenes: { id: string; purpose: string; durationFrames: number;
    operationBindings?: { techniqueId: string; version: number; targetIds: string[]; anchorId: string;
      cutMotivation: string; newInformation: string }[] }[];
    semanticVerificationPolicy?: string;
    contentReferences?: { id: string; version: number; purpose: string;
      parts: { id: string; role: string; text?: string; assetId?: string }[] }[];
    executionVersions?: { compiler: string; components: string; runtime: string; visualAuditPolicy: string } };
  materialRequests?: MaterialRequest[];
  id: string; revision: number; documentRevision: number;
  status: "ready" | "awaiting_choice" | "applied";
  estimatedCostCents: number;
  operations: { operationId: string; beatId: string; rationale: string; expectedResult: string }[];
  blockers: { id: string; message: string; alternatives: { id: string; label: string; impact: string; action: string }[] }[];
  editorialEvidence?: { type: string; techniqueId?: string; selection?: string; freshness?: string; sources?: string[];
    sceneId?: string; status?: string; reasons?: string[]; alternative?: string;
    clipId?: string; message?: string; proposedText?: string; proposedOrder?: string[] }[];
  manifest?: { compilerVersion?: string; hashes?: { executableDirection?: string; executableComposition?: string };
    recompilation?: { sourcePlanId: string; sourcePlanRevision: number; editorialDirectionChanged: boolean } };
};
type Transcript = { id: string; assetId: string; revision: number; status: string; segments: { text: string }[] };
type BeatInput = { supportAssetId?: string; maskAssetId?: string; onScreenText?: string;
  audioAssetId?: string; audioRole?: string;
  transcriptId?: string; captionFromTranscript?: boolean; trimStart?: string; trimEnd?: string };
type ProductionRun = {
  visualAudit?: VisualAudit;
  id: string; revision: number; documentRevision?: number; status: string; stage: string; blockers: string[];
  artifacts: { video?: { artifact: { assetId: string; checksumSha256: string } }; animatic?: { artifact: { assetId: string; checksumSha256: string } }; plan?: Plan; direction?: { selectionReason: string;
    beats: { id: string; initialState: string; action: string; consequence: string;
      shotSequence?: { id: string; function: string; observableAction: string; shotScale: string; angle: string }[] }[] };
    preliminaryMaterialInventory?: { beatId: string; requirementId: string; requirementClass: string;
      status: string; visualSuitability: string; candidates: unknown[] }[] };
  providerReadiness?: { id: string; kinds: string[]; capabilities: string[]; configured: boolean }[];
  hybridCapabilities?: { profiles: { profileId: string; capability: string; qualificationState: string;
    commercialUse: string; readiness: { blockingReasons: string[]; qualifiedUseCases: string[] } }[];
    paidFallbackEnabled: false; remoteGpuAuthorized: false };
  budgetEnvelope?: { policy: string; limitUsd?: number | null; allocations: Record<string, number>;
    videoGenerationEnabled: boolean; generatedVideoPolicy?: { mode: string; allowedProfileIds: string[] };
    hybridPolicy?: { mode: string; allowedProfileIds: string[] } };
  productionGates?: { schemaVersion: string; fidelity: ProductionGate; demonstrability: ProductionGate;
    techniqueSuitability: ProductionGate; observedResult: ProductionGate;
    sceneStages?: { sceneId: string; stage: string }[] };
  correctionAction?: string;
  humanReview?: "pending" | { status: string; reviewedBy: string; notes: string };
};
type ProductionGate = { status: "passed" | "failed" | "inconclusive"; reason: string;
  nextAction?: string | null; evidence: unknown[] };
type LocalDiffusionCapability = {
  state: "unavailable" | "experimental" | "qualified";
  serviceAccessible: boolean;
  profileId: string;
  modelReadiness: string;
  resourceAdmission: string;
  adapterSupport: string;
};
type CandidateScores = { relevance: number; subjectIdentity: number; temporalContinuity: number; actionClarity: number };

function editingError(error: unknown) {
  const code = error instanceof Error ? error.message : "";
  if (code.includes("conflict")) return "O projeto mudou. Atualize a edição para usar a versão atual.";
  if (code.includes("choice_required")) return "Resolva as escolhas pendentes antes de gerar o vídeo.";
  if (code.includes("feedback_requires_matching_material")) return "Este ajuste precisa de texto ou apoio visual na cena selecionada.";
  if (code.includes("timeline_required")) return "Adicione um vídeo ou uma sequência de imagens para começar.";
  return "Não foi possível concluir a edição. Seus materiais foram preservados; tente novamente.";
}

export function ContextualEditingPanel({ document: incomingDocument, disabled, onRender }: {
  document?: StudioDocumentRecord; disabled: boolean;
  onRender: (document: StudioDocumentRecord, planId: string) => Promise<unknown>;
}) {
  const [document, setDocument] = React.useState(incomingDocument);
  React.useEffect(() => setDocument(incomingDocument), [incomingDocument]);
  const [objective, setObjective] = React.useState(document?.brief.objective ?? "");
  const [script, setScript] = React.useState("");
  const [lockedFacts, setLockedFacts] = React.useState("");
  const [materialNeeds, setMaterialNeeds] = React.useState<MaterialNeed[]>([]);
  const [pacing, setPacing] = React.useState("balanced");
  const [emphasis, setEmphasis] = React.useState("auto");
  const [reducedMotion, setReducedMotion] = React.useState(false);
  const [plan, setPlan] = React.useState<Plan>();
  const [production, setProduction] = React.useState<ProductionRun>();
  const [productionVideo, setProductionVideo] = React.useState("");
  const [productionFeedback, setProductionFeedback] = React.useState("");
  const [externalReview, setExternalReview] = React.useState("");
  const [externalProvider, setExternalProvider] = React.useState("Gemini");
  const [humanNotes, setHumanNotes] = React.useState("");
  const [humanFailureCause, setHumanFailureCause] = React.useState("none");
  const [fullVideoInspected, setFullVideoInspected] = React.useState(false);
  const [mobileInspected, setMobileInspected] = React.useState(false);
  const [finding, setFinding] = React.useState({ sceneId: "", startSeconds: "", endSeconds: "",
    cause: "material", observation: "", correction: "" });
  const [humanScores, setHumanScores] = React.useState({ clarity: "", rhythm: "", suitability: "",
    continuity: "", finish: "", hierarchy: "", motionNaturalness: "", materialRelevance: "" });
  const humanScoresValid = Object.values(humanScores).every(value => /^[1-5]$/.test(String(value)));
  const correctionRequired = Object.values(humanScores).some(value => /^[1-5]$/.test(String(value)) && Number(value) < 4);
  const findingValid = !!finding.observation.trim() && !!finding.correction.trim()
    && Number.isFinite(Number(finding.startSeconds)) && finding.startSeconds !== ""
    && Number(finding.startSeconds) >= 0 && Number(finding.endSeconds) > Number(finding.startSeconds);
  const [nativeAvailable, setNativeAvailable] = React.useState(false);
  const [qualityIndicatorEnabled, setQualityIndicatorEnabled] = React.useState(false);
  const [qualityPhaseMode, setQualityPhaseMode] = React.useState(false);
  const [nativeEditing, setNativeEditing] = React.useState(false);
  const [visualOnly, setVisualOnly] = React.useState(true);
  const [useLocalDiffusion, setUseLocalDiffusion] = React.useState(false);
  const [localDiffusion, setLocalDiffusion] = React.useState<LocalDiffusionCapability>();
  const [candidateVideo, setCandidateVideo] = React.useState("");
  const [candidateScores, setCandidateScores] = React.useState<Record<keyof CandidateScores, string>>({
    relevance: "", subjectIdentity: "", temporalContinuity: "", actionClarity: "",
  });
  const candidateScoresValid = Object.values(candidateScores).every(value => /^[1-5]$/.test(String(value)));
  const candidateScoresPassing = candidateScoresValid && Object.values(candidateScores).every(value => Number(value) >= 4);
  const evaluatedCandidateScores = Object.fromEntries(
    Object.entries(candidateScores).map(([key, value]) => [key, Number(value)]),
  ) as CandidateScores;
  const [candidateObservation, setCandidateObservation] = React.useState("");
  const [candidateFlicker, setCandidateFlicker] = React.useState(false);
  const [candidateDeformation, setCandidateDeformation] = React.useState(false);
  React.useEffect(() => {
    const controller = new AbortController();
    let objectUrl = "";
    setProductionVideo("");
    setHumanScores({ clarity: "", rhythm: "", suitability: "", continuity: "", finish: "",
      hierarchy: "", motionNaturalness: "", materialRelevance: "" });
    setHumanNotes("");
    setHumanFailureCause("none");
    setFullVideoInspected(false); setMobileInspected(false);
    setFinding({ sceneId: "", startSeconds: "", endSeconds: "", cause: "material", observation: "", correction: "" });
    const assetId = (production?.artifacts.video ?? production?.artifacts.animatic)?.artifact.assetId;
    if (assetId) apiFetchBlob(`/api/v1/assets/${encodeURIComponent(assetId)}/content`, controller.signal)
      .then(blob => { if (!controller.signal.aborted) { objectUrl = URL.createObjectURL(blob); setProductionVideo(objectUrl); } })
      .catch(() => {});
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [production?.artifacts.video?.artifact.assetId, production?.artifacts.animatic?.artifact.assetId]);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [beatInputs, setBeatInputs] = React.useState<Record<string, BeatInput>>({});
  const [transcripts, setTranscripts] = React.useState<Transcript[]>([]);
  const [clipOrder, setClipOrder] = React.useState<string[]>([]);
  const [referenceId, setReferenceId] = React.useState("");
  const [fontId, setFontId] = React.useState("");
  const [useAI, setUseAI] = React.useState(false);
  const [motionEnabled, setMotionEnabled] = React.useState(false);
  const [motionAvailable, setMotionAvailable] = React.useState(false);
  const [aiAvailable, setAIAvailable] = React.useState(false);
  const [providerLabel, setProviderLabel] = React.useState("");
  React.useEffect(() => {
    const controller = new AbortController();
    apiFetch<{ operations: string[]; label: string; qualityIndicatorEnabled?: boolean;
      contextualV2?: { configured: boolean }; remotionNative?: { configured: boolean } }>("/api/v1/studios/v1/editing/ai", { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) {
        const enabled = value.operations.includes("plan");
        setAIAvailable(enabled); setUseAI(enabled); setProviderLabel(value.label);
        setMotionAvailable(!!value.contextualV2?.configured);
        setNativeAvailable(!!value.remotionNative?.configured);
        setQualityIndicatorEnabled(!!value.qualityIndicatorEnabled);
      } })
      .catch(() => {});
    return () => controller.abort();
  }, []);
  React.useEffect(() => {
    const controller = new AbortController();
    apiFetch<LocalDiffusionCapability>("/api/v1/studios/v1/scene-generation-capability", { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) {
        setLocalDiffusion(value);
        setUseLocalDiffusion(value.state !== "unavailable" && value.adapterSupport === "available");
      } })
      .catch(() => { if (!controller.signal.aborted) setUseLocalDiffusion(false); });
    return () => controller.abort();
  }, []);
  const candidateJobId = production?.blockers
    .find(code => code.startsWith("production_local_generation_review_required:"))?.split(":", 2)[1];
  React.useEffect(() => {
    const controller = new AbortController();
    let objectUrl = "";
    setCandidateVideo("");
    setCandidateScores({ relevance: "", subjectIdentity: "", temporalContinuity: "", actionClarity: "" });
    setCandidateObservation("");
    if (candidateJobId) {
      apiFetchBlob(`/api/v1/studios/v1/scene-generation-jobs/${candidateJobId}/candidate`, controller.signal)
        .then(blob => { if (!controller.signal.aborted) {
          objectUrl = URL.createObjectURL(blob); setCandidateVideo(objectUrl);
        } })
        .catch(() => {});
    }
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [candidateJobId]);
  const [references, setReferences] = React.useState<{ id: string; title: string; qualification?: string }[]>([]);
  const [selectedBeats, setSelectedBeats] = React.useState<string[]>([]);
  const loadRevision = React.useRef(0);
  const base = `/api/v1/studios/v1/documents/${document?.documentId}/editing-plans`;
  const clips = document?.composition.mediaTimeline?.tracks.flatMap(t => t.kind === "video" ? t.clips.filter(c => c.enabled) : []) ?? [];

  React.useEffect(() => {
    setObjective(document?.brief.objective ?? "");
    setPlan(undefined); setProduction(undefined); setBeatInputs({}); setSelectedBeats([]); setError("");
    setClipOrder([]); setReferenceId(""); setTranscripts([]); setReferences([]);
    setScript(""); setLockedFacts(""); setMaterialNeeds([]);
  }, [document?.documentId]);

  React.useEffect(() => {
    if (!document) return;
    const controller = new AbortController();
    apiFetch<Transcript[]>(`/api/v1/studios/v1/transcripts?workspace_id=${encodeURIComponent(document.workspaceId)}`, { signal: controller.signal })
      .then(items => { if (!controller.signal.aborted) setTranscripts(items.filter(t => t.status !== "draft")); })
      .catch(e => { if (!controller.signal.aborted) setError(editingError(e)); });
    apiFetch<{ techniques: { id: string; title: string }[] }>(`/api/v1/studios/v1/editing/repertoire?workspace_id=${encodeURIComponent(document.workspaceId)}`, { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) setReferences(value.techniques); })
      .catch(e => { if (!controller.signal.aborted) setError(editingError(e)); });
    return () => controller.abort();
  }, [document?.documentId, document?.revision]);

  React.useEffect(() => {
    if (!document) return;
    const controller = new AbortController();
    const revision = ++loadRevision.current;
    apiFetch<Plan | null>(`${base}/latest`, { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted && revision === loadRevision.current) setPlan(value ?? undefined); })
      .catch(e => { if (!controller.signal.aborted && revision === loadRevision.current) setError(editingError(e)); });
    return () => controller.abort();
  }, [base, document?.revision]);

  async function post<T>(path: string, body: unknown, key?: string): Promise<T> {
    return apiFetch<T>(path, { method: "POST", body: JSON.stringify(body),
      headers: key ? { "Idempotency-Key": key } : undefined });
  }
  async function run(action: () => Promise<void>) {
    ++loadRevision.current;
    setBusy(true); setError("");
    try { await action(); } catch (e) { setError(editingError(e)); }
    finally { setBusy(false); }
  }
  async function finish(next: Plan) {
    setPlan(next);
    setMaterialNeeds((next.materialRequests ?? []).map(needFromRequest));
    if (next.status !== "ready") return;
    const saved = await post<StudioDocumentRecord>(`${base}/${next.id}/apply`, { expectedPlanRevision: next.revision });
    await onRender(saved, next.id);
  }
  function buildDirection() {
    if (!document) return;
    const direction = { expectedDocumentRevision: document.revision, fontAssetId: fontId || null,
      intent: { objective, script, lockedFacts: lockedFacts.split("\n").map(t => t.trim()).filter(Boolean), pacing, emphasis, reducedMotion, preserveMessage: true },
      materialNeeds,
      clipOrder, referenceTechniqueIds: referenceId.trim() ? [referenceId.trim()] : [],
      beats: clips.map(c => {
        const { trimStart, trimEnd, transcriptId, ...input } = beatInputs[c.id] ?? {};
        const transcript = transcripts.find(t => t.id === transcriptId);
        const start = trimStart?.trim() ? Number(trimStart) * 1e6 : c.source?.startMicroseconds ?? 0;
        const end = trimEnd?.trim() ? Number(trimEnd) * 1e6 : (c.source?.startMicroseconds ?? 0) + (c.source?.durationMicroseconds ?? 0);
        return { id: c.id, clipId: c.id, purpose: c.label || objective, ...input,
          ...(transcript ? { transcriptId: transcript.id, transcriptRevision: transcript.revision } : {}),
          sourceDecisions: trimStart?.trim() || trimEnd?.trim() ? [{ id: `selection-${c.id}`, operation: "keep",
            startMicroseconds: Math.round(start), endMicroseconds: Math.round(end), status: "suggested",
            source: "contextual-draft", reason: "Intervalo solicitado na direção da cena" }] : [] };
      }) };
    return direction;
  }
  async function developDirection(mode: "mixed_montage" | "motion" = "mixed_montage") {
    if (!document) return;
    if (qualityPhaseMode && (mode !== "mixed_montage" || visualOnly || !nativeEditing)) {
      throw new Error("A fase visual exige montagem híbrida de 15 s com áudio.");
    }
    const url = `/api/v1/studios/v1/documents/${document.documentId}/production-runs`;
    const current = loadRevision.current;
    let next = await post<ProductionRun>(url, { direction: buildDirection(), durationSeconds: mode === "motion" ? 11 : 15, mode, useSemanticCompositions: true,
      evaluationScope: visualOnly ? "visual_only" : "audiovisual", requireVisualBlueprint: true,
      ...(qualityPhaseMode ? { qualityPhaseId: "visual-quality-2026-10-01" } : {}),
      demonstrationPolicy: "required", materialSemanticsPolicy: mode === "motion" ? "legacy" : "contextual_video_v1",
      cinematicDirectionPolicy: mode === "motion" ? "editorial_motion_v2" : "mixed_motion_v1",
      nativeSceneEditing: mode === "mixed_montage" && nativeEditing,
      ...(useLocalDiffusion ? { hybridPolicy: {
        mode: "auto", allowedProfileIds: ["animatediff-lightning-sd15-a-v1"],
        allowExperimental: true, allowConditionalCommercialUse: true, allowRemoteApi: false,
        maxCandidatesPerNeed: 1, maximumGeneratedSecondsTotal: 1,
      } } : {}) },
      `production-${crypto.randomUUID()}`);
    if (current !== loadRevision.current) return;
    await followProduction(next, current);
  }
  async function followProduction(initial: ProductionRun, current = loadRevision.current) {
    if (!document) return;
    const url = `/api/v1/studios/v1/documents/${document.documentId}/production-runs`;
    let next = initial;
    setProduction(next);
    for (let attempt = 0; attempt < 120 && ["running", "pending"].includes(next.status); attempt++) {
      await new Promise(resolve => window.setTimeout(resolve, 3000));
      if (current !== loadRevision.current) return;
      next = await post<ProductionRun>(`${url}/${next.id}/resume`, {});
      if (current !== loadRevision.current) return;
      setProduction(next);
    }
    if (next.artifacts.plan) setPlan(next.artifacts.plan);
    if (next.documentRevision && next.documentRevision !== document.revision) {
      const updated = await apiFetch<StudioDocumentRecord>(`/api/v1/studios/v1/documents/${document.documentId}`);
      if (current === loadRevision.current) setDocument(updated);
    }
  }
  async function generate() {
    if (!document) return;
    const direction = buildDirection();
    if (useAI) {
      type PlanningJob = { id: string; status: string; result?: { plan?: Plan }; errorMessage?: string };
      let job = await post<PlanningJob>(`/api/v1/studios/v1/documents/${document.documentId}/editing-ai-jobs`, {
        expectedDocumentRevision: document.revision, operation: "plan", prompt: objective, direction,
        planVersion: motionEnabled ? 2 : 1,
      }, `editing-ai-plan-${crypto.randomUUID()}`);
      const current = loadRevision.current;
      for (let attempt = 0; attempt < 120 && !["succeeded", "failed", "cancelled"].includes(job.status); attempt++) {
        await new Promise(resolve => window.setTimeout(resolve, 3000));
        if (current !== loadRevision.current) return;
        job = await apiFetch<PlanningJob>(`/api/v1/studios/v1/jobs/${job.id}`);
      }
      if (!job.result?.plan) throw new Error(job.errorMessage ?? "O planejamento continua na fila. Consulte os jobs do estúdio.");
      await finish(job.result.plan); return;
    }
    const next = await post<Plan>(base, direction, `contextual-${crypto.randomUUID()}`);
    await finish(next);
  }
  async function recompile() {
    if (!document || !plan?.direction) return;
    const derivative = await post<Plan>(`${base}/${plan.id}/recompile`, {
      expectedDocumentRevision: document.revision,
      expectedPlanRevision: plan.revision,
    }, `editing-recompile-${plan.id}-${plan.revision}-${document.revision}`);
    setPlan(derivative);
  }
  const blocked = busy || disabled || !document;
  const stale = !!plan && plan.documentRevision !== document?.revision;
  const orderedClips = clipOrder.length ? clipOrder.flatMap(id => clips.filter(c => c.id === id)) : clips;
  function changeBeat(id: string, value: Partial<BeatInput>) {
    setBeatInputs(old => ({ ...old, [id]: { ...old[id], ...value } }));
  }
  function moveClip(index: number, offset: number) {
    const ids = orderedClips.map(c => c.id);
    [ids[index], ids[index + offset]] = [ids[index + offset], ids[index]];
    setClipOrder(ids);
  }
  return <section className="vs-contextual-editing" aria-label="Edição contextual">
    <h2>Edição com intenção</h2>
    <p>Defina o que o vídeo precisa comunicar. A montagem preserva a mensagem e apresenta o vídeo para sua revisão.</p>
    <VisualQualityIndicator document={document} runId={production?.id}
      refreshKey={production?.revision} enabled={qualityIndicatorEnabled && !disabled} />
    {document && <EditingResourcesPanel document={document} onDocument={setDocument} disabled={blocked} />}
    <label>Roteiro e informações de origem<textarea value={script} onChange={e => setScript(e.target.value)} disabled={blocked} maxLength={100000} /></label>
    <label>Fatos que devem permanecer (um por linha)<textarea value={lockedFacts} onChange={e => setLockedFacts(e.target.value)} disabled={blocked} /></label>
    {aiAvailable && <label><input type="checkbox" checked={useAI} onChange={e => setUseAI(e.target.checked)}
      disabled={blocked} /> Planejamento contextual com {providerLabel}</label>}
    {motionAvailable && useAI && <label><input type="checkbox" checked={motionEnabled}
      onChange={e => setMotionEnabled(e.target.checked)} disabled={blocked} /> Criar cenas com edição e motion</label>}
    {motionEnabled && useAI && <p>As cenas podem começar pelo roteiro, sem vídeo na timeline. Materiais e narração ausentes serão apresentados antes do render.</p>}
    <label>Fonte do projeto<select value={fontId} onChange={e => setFontId(e.target.value)} disabled={blocked}>
      <option value="">Fonte padrão</option>{document?.assets.filter(a => a.mediaType.startsWith("font/")).map(a =>
        <option key={a.id} value={a.id}>{String(a.provenance?.editingResource?.family ?? a.id)}</option>)}
    </select></label>
    <label>Objetivo do vídeo
      <textarea value={objective} onChange={e => setObjective(e.target.value)} disabled={blocked} maxLength={2000} />
    </label>
    <label>Ritmo
      <select value={pacing} onChange={e => setPacing(e.target.value)} disabled={blocked}>
        <option value="calm">Calmo</option><option value="balanced">Equilibrado</option><option value="energetic">Enérgico</option>
      </select>
    </label>
    <label>Prioridade
      <select value={emphasis} onChange={e => setEmphasis(e.target.value)} disabled={blocked}>
        <option value="auto">A partir do objetivo</option>
        <option value="message">Compreender a mensagem</option><option value="demonstration">Observar a demonstração</option>
        <option value="atmosphere">Perceber o ambiente</option>
      </select>
    </label>
    <label><input type="checkbox" checked={reducedMotion} onChange={e => setReducedMotion(e.target.checked)} disabled={blocked} /> Movimento reduzido</label>
    <details><summary>Direção por cena</summary>
      <label>Referência de edição
        <select value={referenceId} disabled={blocked} onChange={e => setReferenceId(e.target.value)}>
          <option value="">A partir do objetivo e dos materiais</option>
          {references.map(reference => <option key={reference.id} value={reference.id}>
            {reference.title}{reference.qualification === "knowledge_only" ? " · estudo" : ""}
          </option>)}
        </select>
      </label>
      {orderedClips.map((clip, index) => <fieldset key={clip.id} disabled={blocked}>
        <legend>{clip.label || `Cena ${index + 1}`}</legend>
        <button type="button" disabled={index === 0} onClick={() => moveClip(index, -1)}>Mover cena para antes</button>
        <button type="button" disabled={index === orderedClips.length - 1} onClick={() => moveClip(index, 1)}>Mover cena para depois</button>
        <label>Imagem ou vídeo de apoio
          <select value={beatInputs[clip.id]?.supportAssetId ?? ""} onChange={e => setBeatInputs(old => ({ ...old,
            [clip.id]: { ...old[clip.id], supportAssetId: e.target.value || undefined } }))}>
            <option value="">Manter o material atual</option>
            {document?.assets.filter(a => a.id !== clip.assetId && /^(image|video)\//.test(a.mediaType)).map(a =>
              <option key={a.id} value={a.id}>{a.id}</option>)}
          </select>
        </label>
        <label>Máscara do apoio
          <select value={beatInputs[clip.id]?.maskAssetId ?? ""} onChange={e => changeBeat(clip.id, { maskAssetId: e.target.value || undefined })}>
            <option value="">Sem máscara</option>
            {document?.assets.filter(a => a.mediaType.startsWith("image/")).map(a => <option key={a.id} value={a.id}>{a.id}</option>)}
          </select>
        </label>
        <label>Áudio de apoio<select value={beatInputs[clip.id]?.audioAssetId ?? ""}
          onChange={e => changeBeat(clip.id, { audioAssetId: e.target.value || undefined })}>
          <option value="">Sem áudio adicional</option>{document?.assets.filter(a => a.mediaType.startsWith("audio/")).map(a =>
            <option key={a.id} value={a.id}>{a.id}</option>)}
        </select></label>
        <label>Função do áudio<select value={beatInputs[clip.id]?.audioRole ?? "effect"}
          onChange={e => changeBeat(clip.id, { audioRole: e.target.value })}>
          <option value="effect">Efeito sonoro</option><option value="music">Música</option>
          <option value="ambience">Ambiente</option><option value="narration">Narração</option>
        </select></label>
        <label>Transcrição da cena
          <select value={beatInputs[clip.id]?.transcriptId ?? ""} onChange={e => changeBeat(clip.id, { transcriptId: e.target.value || undefined })}>
            <option value="">Selecionar transcrição disponível</option>
            {transcripts.filter(t => t.assetId === clip.assetId).map(t => <option key={t.id} value={t.id}>
              {t.segments[0]?.text.slice(0, 70) || "Transcrição"} — revisão {t.revision}{t.status === "reviewed" ? " (revisada)" : ""}
            </option>)}
          </select>
        </label>
        <label><input type="checkbox" checked={beatInputs[clip.id]?.captionFromTranscript ?? false}
          onChange={e => changeBeat(clip.id, { captionFromTranscript: e.target.checked, onScreenText: e.target.checked ? "" : beatInputs[clip.id]?.onScreenText })} /> Legendar a fala</label>
        <label>Início na origem (segundos)
          <input type="number" min="0" step="0.01" value={beatInputs[clip.id]?.trimStart ?? ""} onChange={e => changeBeat(clip.id, { trimStart: e.target.value })} />
        </label>
        <label>Fim na origem (segundos)
          <input type="number" min="0" step="0.01" value={beatInputs[clip.id]?.trimEnd ?? ""} onChange={e => changeBeat(clip.id, { trimEnd: e.target.value })} />
        </label>
        <p>A seleção preserva todas as falas da transcrição revisada. Trechos sem essa evidência mantêm a montagem original após sua escolha.</p>
        <label>Texto de apoio
          <input disabled={beatInputs[clip.id]?.captionFromTranscript} value={beatInputs[clip.id]?.onScreenText ?? ""} maxLength={400} onChange={e => setBeatInputs(old => ({ ...old,
            [clip.id]: { ...old[clip.id], onScreenText: e.target.value } }))} />
        </label>
      </fieldset>)}
    </details>
    <button type="button" className="vs-button primary" disabled={blocked || !objective.trim()} onClick={() => void run(generate)}>
      {busy ? "Preparando edição…" : "Criar vídeo com esta direção"}
    </button>
    {nativeAvailable && <label><input type="checkbox" checked={nativeEditing} disabled={blocked}
      onChange={e => setNativeEditing(e.target.checked)} /> Edição híbrida experimental: filmagem, produto e tipografia</label>}
    {qualityIndicatorEnabled && <label><input type="checkbox" checked={qualityPhaseMode} disabled={blocked || !nativeAvailable}
      onChange={e => { setQualityPhaseMode(e.target.checked); if (e.target.checked) { setNativeEditing(true); setVisualOnly(false); } }} />
      Validar nesta fase: 15 s, montagem híbrida, áudio e teto compartilhado de US$ 10</label>}
    <label><input type="checkbox" checked={visualOnly} disabled={blocked} onChange={e => setVisualOnly(e.target.checked)} />
      Desenvolver somente o visual nesta rodada, sem produzir narração, música ou efeitos sonoros
    </label>
    <label><input type="checkbox" checked={useLocalDiffusion} disabled={blocked || localDiffusion?.adapterSupport !== "available"}
      onChange={e => setUseLocalDiffusion(e.target.checked)} />
      Incluir um trecho experimental criado pelo difusor local
    </label>
    {localDiffusion && <p>
      Difusor local: {localDiffusion.serviceAccessible ? "serviço acessível" : "serviço indisponível"}; modelo {localDiffusion.modelReadiness};
      recursos agora {localDiffusion.resourceAdmission}. O trecho só entra na montagem depois de avaliação.
    </p>}
    <button type="button" disabled={blocked || (qualityPhaseMode && (visualOnly || !nativeEditing)) || !objective.trim() || !script.trim()} onClick={() => void run(() => developDirection("mixed_montage"))}>
      Desenvolver montagem mista
    </button>
    <button type="button" disabled={blocked || qualityPhaseMode || !objective.trim() || !script.trim()} onClick={() => void run(() => developDirection("motion"))}>
      Desenvolver motion editorial
    </button>
    {production && <section aria-label="Direção visual">
      <p>{production.status === "blocked" ? "Produção com pendência" : production.status === "awaiting_review" ? (production.artifacts.video ? "Vídeo disponível para revisão" : "Rascunho precisa de revisão") : production.status === "plan_ready" ? "Plano preparado para edição" : "Desenvolvendo cenas"}.
        A qualidade audiovisual ainda precisa ser avaliada.</p>
      {production.blockers.includes("production_qualified_narration_required") && <p>Falta narração utilizável. A síntese de voz precisa ser qualificada antes do teste de produção completo.</p>}
      {production.blockers.some(code => code.includes("not_configured") || code.includes("disabled")) && <p>Configure o provedor de planejamento para continuar.</p>}
      {production.artifacts.direction && <details><summary>Conceito e cenas</summary>
        <p>{production.artifacts.direction.selectionReason}</p>
        {production.artifacts.direction.beats.map(beat => <div key={beat.id}>
          <p>{beat.initialState} → {beat.action} → {beat.consequence}</p>
          {beat.shotSequence?.map(shot => <p key={shot.id}>Plano {shot.id}: {shot.function} · {shot.observableAction} · {shot.shotScale}/{shot.angle}</p>)}
        </div>)}
      </details>}
      {production.artifacts.preliminaryMaterialInventory?.length ? <details><summary>Descoberta preliminar de materiais</summary>
        {production.artifacts.preliminaryMaterialInventory.map(item => <p key={`${item.beatId}-${item.requirementId}`}>
          {item.beatId} · {item.requirementId}: {item.status} · {item.requirementClass} · {item.candidates.length} candidatos;
          adequação visual {item.visualSuitability}. Nenhum candidato foi aprovado apenas pelos metadados.
        </p>)}
      </details> : null}
      {production.productionGates && <details open><summary>Verificações da produção</summary>
        {([
          ["Fidelidade", production.productionGates.fidelity],
          ["Demonstrabilidade", production.productionGates.demonstrability],
          ["Adequação da técnica", production.productionGates.techniqueSuitability],
          ["Resultado observado", production.productionGates.observedResult],
        ] as [string, ProductionGate][]).map(([label, gate]) => <p key={label}>
          <strong>{label}:</strong> {gate.status === "passed" ? "aprovado" : gate.status === "failed" ? "reprovado" : "inconclusivo"}. {gate.reason}
        </p>)}
        {production.correctionAction && <p>Próxima correção: {production.correctionAction}.</p>}
        {production.productionGates.sceneStages?.map(item => <p key={item.sceneId}>Cena {item.sceneId}: {item.stage}</p>)}
      </details>}
      {production.blockers.length > 0 && <details><summary>Inspeção da pendência</summary><p>{production.blockers.join(", ")}</p></details>}
      {production.providerReadiness && <details><summary>Provedores de materiais</summary>
        {production.providerReadiness.map(provider => <p key={provider.id}>{provider.id}: {provider.configured ? "disponível" : "não configurado"} · {provider.capabilities.join(", ")}</p>)}
      </details>}
      {production.hybridCapabilities && <details><summary>Capacidades híbridas</summary>
        {production.hybridCapabilities.profiles.map(profile => <p key={profile.profileId}>
          {profile.profileId}: {profile.qualificationState} · {profile.capability}
          {profile.profileId.startsWith("longcat-avatar-1.5") ? " · integração preparada; execução e qualidade pendentes" : ""}
          {profile.readiness.blockingReasons.length > 0 ? ` · pendências: ${profile.readiness.blockingReasons.join(", ")}` : ""}
        </p>)}
        <p>Fallback pago: desabilitado. GPU remota: não autorizada.</p>
      </details>}
      {candidateJobId && <section aria-label="Avaliação do trecho gerado localmente">
        <h4>Trecho local aguardando avaliação</h4>
        {candidateVideo ? <video controls src={candidateVideo} aria-label="Candidato do difusor local" style={{ maxWidth: "100%" }} /> :
          <p>O candidato ainda não pôde ser carregado.</p>}
        {(["relevance", "subjectIdentity", "temporalContinuity", "actionClarity"] as const).map(key =>
          <label key={key}>{({ relevance: "Pertinência", subjectIdentity: "Identidade do objeto", temporalContinuity: "Continuidade temporal", actionClarity: "Clareza da ação" })[key]}
            <input type="number" min="1" max="5" value={candidateScores[key]} disabled={blocked}
              onChange={e => setCandidateScores(old => ({ ...old, [key]: e.target.value }))} />
          </label>)}
        <label>Observação da sequência
          <textarea value={candidateObservation} disabled={blocked} onChange={e => setCandidateObservation(e.target.value)} />
        </label>
        <label><input type="checkbox" checked={candidateFlicker} disabled={blocked} onChange={e => setCandidateFlicker(e.target.checked)} /> Flicker visível</label>
        <label><input type="checkbox" checked={candidateDeformation} disabled={blocked} onChange={e => setCandidateDeformation(e.target.checked)} /> Deformação relevante</label>
        <button disabled={blocked || !candidateObservation.trim() || !candidateScoresPassing || candidateFlicker || candidateDeformation}
          onClick={() => void run(async () => {
            await post(`/api/v1/studios/v1/scene-generation-jobs/${candidateJobId}/admission`, {
              expectedDocumentRevision: document?.revision, decision: "accept", comment: candidateObservation,
              evaluation: { ...evaluatedCandidateScores, sequenceInspected: true, flickerObserved: candidateFlicker,
                deformationObserved: candidateDeformation, observation: candidateObservation },
            });
            const next = await post<ProductionRun>(`/api/v1/studios/v1/documents/${document?.documentId}/production-runs/${production.id}/resume`, {});
            await followProduction(next);
          })}>Aprovar trecho e continuar</button>
        <button disabled={blocked || !candidateObservation.trim() || !candidateScoresValid} onClick={() => void run(async () => {
          await post(`/api/v1/studios/v1/scene-generation-jobs/${candidateJobId}/admission`, {
            expectedDocumentRevision: document?.revision, decision: "reject", comment: candidateObservation,
            evaluation: { ...evaluatedCandidateScores, sequenceInspected: true, flickerObserved: candidateFlicker,
              deformationObserved: candidateDeformation, observation: candidateObservation },
          });
          const next = await post<ProductionRun>(`/api/v1/studios/v1/documents/${document?.documentId}/production-runs/${production.id}/resume`, {});
          await followProduction(next);
        })}>Rejeitar e tentar alternativa</button>
      </section>}
      {production.budgetEnvelope && <details><summary>Orçamento desta execução</summary>
        <p>Política {production.budgetEnvelope.policy}. Limite de API: {production.budgetEnvelope.limitUsd == null ? "registro sem bloqueio de produção" : `US$ ${production.budgetEnvelope.limitUsd.toFixed(2)}`}.</p>
        <p>Custos e reservas são contabilizados antes de cada chamada. Vídeo generativo: {production.budgetEnvelope.videoGenerationEnabled ? "habilitado" : "desabilitado neste piloto"}.</p>
      </details>}
      {productionVideo && <video controls src={productionVideo} aria-label="Vídeo da produção" style={{ maxWidth: "100%" }} />}
      {productionVideo && typeof production.humanReview === "string" && <details><summary>Registrar revisão humana</summary>
        {(Object.keys(humanScores) as (keyof typeof humanScores)[]).map(key => <label key={key}>
          {({ clarity: "Clareza", rhythm: "Ritmo", suitability: "Adequação", continuity: "Continuidade",
            finish: "Acabamento",
            hierarchy: "Hierarquia", motionNaturalness: "Naturalidade do movimento",
            materialRelevance: "Pertinência dos materiais" })[key]}
          <input type="number" min="1" max="5" value={humanScores[key]} disabled={blocked}
            onChange={e => setHumanScores(old => ({ ...old, [key]: e.target.value }))} />
        </label>)}
        <label>Motivos da avaliação<textarea value={humanNotes} disabled={blocked}
          onChange={e => setHumanNotes(e.target.value)} /></label>
        <label><input type="checkbox" checked={fullVideoInspected} disabled={blocked}
          onChange={e => setFullVideoInspected(e.target.checked)} /> Assisti ao vídeo inteiro em velocidade normal, com som.</label>
        <label><input type="checkbox" checked={mobileInspected} disabled={blocked}
          onChange={e => setMobileInspected(e.target.checked)} /> Conferi leitura e composição em tamanho de celular.</label>
        <label>Causa principal da correção<select value={humanFailureCause} disabled={blocked}
          onChange={e => setHumanFailureCause(e.target.value)}>
          <option value="none">Nenhuma</option><option value="material">Material</option>
          <option value="cut">Corte</option><option value="framing">Enquadramento</option>
          <option value="motion">Movimento</option><option value="mask">Máscara</option>
          <option value="sound">Som</option><option value="direction">Direção</option>
        </select></label>
        <details open={correctionRequired}><summary>Achado com correção executável {correctionRequired ? "(obrigatório)" : "(opcional)"}</summary>
          <label>Cena<input value={finding.sceneId} disabled={blocked} onChange={e => setFinding(old => ({ ...old, sceneId: e.target.value }))} /></label>
          <label>Início (s)<input type="number" min="0" step="0.1" value={finding.startSeconds} disabled={blocked}
            onChange={e => setFinding(old => ({ ...old, startSeconds: e.target.value }))} /></label>
          <label>Fim (s)<input type="number" min="0.1" step="0.1" value={finding.endSeconds} disabled={blocked}
            onChange={e => setFinding(old => ({ ...old, endSeconds: e.target.value }))} /></label>
          <label>Causa<select value={finding.cause} disabled={blocked} onChange={e => setFinding(old => ({ ...old, cause: e.target.value }))}>
            {(["material", "cut", "framing", "continuity", "motion", "mask", "sound", "direction", "readability"] as const).map(code =>
              <option key={code} value={code}>{code}</option>)}</select></label>
          <label>O que se vê<textarea value={finding.observation} disabled={blocked} maxLength={1000}
            onChange={e => setFinding(old => ({ ...old, observation: e.target.value }))} /></label>
          <label>Mudança proposta<textarea value={finding.correction} disabled={blocked} maxLength={1000}
            onChange={e => setFinding(old => ({ ...old, correction: e.target.value }))} /></label>
        </details>
        <button disabled={blocked || !humanNotes.trim() || !humanScoresValid || !fullVideoInspected || !mobileInspected
          || (correctionRequired && !findingValid) || (finding.observation.trim() && !findingValid)} onClick={() => void run(async () => {
          const rendered = (production.artifacts.video ?? production.artifacts.animatic)?.artifact;
          if (!rendered || !document) return;
          await post(`/api/v1/studios/v1/documents/${document.documentId}/renders/${rendered.assetId}/visual-review`, {
            expectedDocumentRevision: document.revision, renderChecksum: rendered.checksumSha256,
             ...Object.fromEntries(Object.entries(humanScores).map(([key, value]) => [key, Number(value)])),
             notes: humanNotes, failureCause: humanFailureCause, fullVideoInspected, mobileInspected,
             findings: findingValid ? [{ sceneId: finding.sceneId || null, startSeconds: Number(finding.startSeconds),
               endSeconds: Number(finding.endSeconds), cause: finding.cause,
               observation: finding.observation.trim(), correction: finding.correction.trim() }] : [],
          });
          const next = await post<ProductionRun>(`/api/v1/studios/v1/documents/${document.documentId}/production-runs/${production.id}/resume`, {});
          setProduction(next);
        })}>Salvar revisão desta versão</button>
      </details>}
      {(production.artifacts.video || production.artifacts.animatic) && <>
        <button disabled={blocked} onClick={() => void run(async () => {
          const blob = await apiFetchBlob(`/api/v1/studios/v1/documents/${document?.documentId}/production-runs/${production.id}/evidence`);
          const url = URL.createObjectURL(blob);
          const link = window.document.createElement("a");
          link.href = url; link.download = "res-evidencias.zip"; link.click();
          window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        })}>Exportar evidências para avaliação</button>
        <details><summary>Registrar análise do Gemini ou outro avaliador</summary>
          <label>Avaliador<input value={externalProvider} onChange={e => setExternalProvider(e.target.value)} maxLength={120} disabled={blocked} /></label>
          <label>Análise externa<textarea value={externalReview} onChange={e => setExternalReview(e.target.value)} maxLength={40000} disabled={blocked} /></label>
          <p>A análise será vinculada a este vídeo e não aplicará alterações automaticamente.</p>
          <button disabled={blocked || !externalReview.trim() || !externalProvider.trim()} onClick={() => void run(async () => {
            const next = await post<ProductionRun>(`/api/v1/studios/v1/documents/${document?.documentId}/production-runs/${production.id}/external-review`, {
              expectedRunRevision: production.revision,
              renderChecksum: (production.artifacts.video ?? production.artifacts.animatic)?.artifact.checksumSha256,
              text: externalReview,
              providerLabel: externalProvider,
            });
            setProduction(next); setExternalReview("");
          })}>Registrar análise externa</button>
        </details>
      </>}
      {production.visualAudit && <VisualAuditPanel audit={production.visualAudit} />}
      {["running", "blocked", "pending"].includes(production.status) && <button disabled={blocked} onClick={() => void run(async () => {
        const next = await post<ProductionRun>(`/api/v1/studios/v1/documents/${document?.documentId}/production-runs/${production.id}/resume`, {});
        await followProduction(next);
      })}>Retomar produção</button>}
      {production.status === "awaiting_review" && <>
        <fieldset disabled={blocked}><legend>Cenas que receberão o ajuste</legend>
          {production.artifacts.plan?.direction?.scenes.map((scene, i) => <label key={scene.id}>
            <input type="checkbox" checked={selectedBeats.includes(scene.id)} onChange={e => setSelectedBeats(old => e.target.checked ? [...new Set([...old, scene.id])] : old.filter(id => id !== scene.id))} />
            Selecionar cena {i + 1}: {scene.purpose}
          </label>)}
        </fieldset>
        <label>Ajuste das cenas selecionadas<textarea value={productionFeedback} onChange={e => setProductionFeedback(e.target.value)} disabled={blocked} /></label>
        <p>As cenas não selecionadas serão preservadas.</p>
        <button disabled={blocked || !productionFeedback.trim() || !selectedBeats.length} onClick={() => void run(async () => {
          const next = await post<ProductionRun>(`/api/v1/studios/v1/documents/${document?.documentId}/production-runs/${production.id}/revise`, {
            expectedRunRevision: production.revision, sceneIds: selectedBeats, instruction: productionFeedback,
          });
          await followProduction(next);
        })}>Revisar cenas e gerar novo vídeo</button>
      </>}
    </section>}
    {error && <p role="alert">{error}</p>}
    {stale && <p>O documento mudou. Crie uma nova edição para usar os materiais atuais.</p>}
    {plan && <>
      {document && <div key={`${document.documentId}:${document.revision}:${plan.id}`}>
        <EditingMaterialRequests requests={plan.materialRequests ?? []} workspaceId={document.workspaceId}
          disabled={blocked || stale} onSelect={need => {
            if (plan.direction && need.assetId) {
              void run(async () => finish(await post<Plan>(`${base}/${plan.id}/materials`, {
                expectedPlanRevision: plan.revision, needId: need.id, assetId: need.assetId,
              }, `editing-material-${plan.id}-${plan.revision}-${need.id}-${need.assetId}`)));
            } else setMaterialNeeds(old => [...old.filter(n => n.id !== need.id), need]);
          }} />
      </div>}
      {plan.editorialEvidence?.filter(e => e.type === "editorial_admission").map((e, index) => <aside key={index}>
        <p>{e.message} Cena: {e.clipId}.</p>
        {e.proposedText && <blockquote>{e.proposedText}</blockquote>}
        {e.proposedOrder && <p>Ordem proposta: {e.proposedOrder.join(" → ")}</p>}
        <p>Confira a proposta com o roteiro. Para utilizá-la, ajuste o texto ou a ordem nas cenas e crie novamente a edição.</p>
      </aside>)}
      {plan.direction ? <p>O tempo de render e o consumo das APIs serão registrados. A avaliação audiovisual permanece pendente até a revisão do vídeo.</p> :
        <p>Estimativa de processamento local: {(plan.estimatedCostCents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}. O consumo das APIs é registrado separadamente.</p>}
      {plan.direction?.scenes.map((scene, i) => <p key={scene.id}><strong>Cena {i + 1}:</strong> {scene.purpose}</p>)}
      {plan.editorialEvidence?.filter(e => e.type === "operation_decision").map((e, index) =>
        <p key={`${e.sceneId}:${e.techniqueId}:${index}`}>
          Técnica {e.techniqueId} na cena {e.sceneId}: {e.status === "eligible" ? "pré-requisitos atendidos" : "pendente"}.
          {e.reasons?.length ? ` ${e.reasons.join(" ")}` : ""}
          {e.status !== "eligible" && e.alternative ? ` ${e.alternative}` : ""}
        </p>)}
      {plan.blockers.map(b => <fieldset key={b.id} disabled={blocked || stale}>
        <legend>{b.message}</legend>
        {b.alternatives.map(a => <div key={a.id}>
          <button type="button" onClick={() => void run(async () => finish(await post<Plan>(`${base}/${plan.id}/choices`, {
            expectedPlanRevision: plan.revision, blockerId: b.id, alternativeId: a.id,
          })))}>{a.label}</button><p>{a.impact}</p>
        </div>)}
      </fieldset>)}
      {plan.status === "ready" && !stale && <button disabled={blocked} onClick={() => void run(() => finish(plan))}>Gerar vídeo</button>}
      {plan.status === "applied" && !stale && document && <button disabled={blocked}
        onClick={() => void run(async () => { await onRender(document, plan.id); })}>Abrir ou retomar renderização</button>}
      {plan.direction && !stale && <button disabled={blocked} onClick={() => void run(recompile)}>
        Recompilar composição atual
      </button>}
      {plan.manifest?.recompilation && <p>
        Composição recompilada sem novo planejamento. A direção editorial foi preservada e um novo derivado foi criado.
      </p>}
      <details><summary>Decisões de edição e ajustes</summary>
        {plan.direction?.executionVersions && <p>
          Execução fixada: {plan.direction.executionVersions.compiler} · {plan.direction.executionVersions.components} · {plan.direction.executionVersions.runtime} · {plan.direction.executionVersions.visualAuditPolicy}.
        </p>}
        {plan.direction?.semanticVerificationPolicy && <p>
          Verificação semântica: {plan.direction.semanticVerificationPolicy === "canonical_demonstration_v1"
            ? "conteúdo persistente e ações falsificáveis" : "compatibilidade com planos anteriores"}.
        </p>}
        {plan.direction?.contentReferences?.map(reference => <p key={reference.id}>
          Conteúdo {reference.id} v{reference.version}: {reference.parts.map(part => `${part.role} (${part.id})`).join(" · ")}.
        </p>)}
        {plan.direction?.scenes.flatMap(scene => scene.operationBindings?.map(binding =>
          <p key={`${scene.id}:${binding.techniqueId}`}>
            {binding.techniqueId} v{binding.version}: {binding.cutMotivation} Âncora: {binding.anchorId}.
            Informação nova: {binding.newInformation}.
          </p>) ?? [])}
        {plan.editorialEvidence?.filter(e => e.type === "reference").map(e => <p key={e.techniqueId}>
          Referência {e.techniqueId}: {e.selection === "requested" ? "solicitada" : "recuperada na base"}.
          {e.freshness === "historical" && " Observação histórica; não indica tendência atual."}
        </p>)}
        {plan.operations.map(o => <p key={o.operationId}><strong>{o.rationale}</strong> {o.expectedResult}</p>)}
        {[...new Set(plan.operations.map(o => o.beatId))].map((beatId, i) => <label key={beatId}>
          <input type="checkbox" checked={selectedBeats.includes(beatId)} onChange={e => setSelectedBeats(old => e.target.checked ? [...old, beatId] : old.filter(id => id !== beatId))} /> Cena {i + 1}
        </label>)}
        {(["mais calmo", "mostrar melhor o produto", "menos texto"] as const).map(feedback =>
          <button key={feedback} disabled={blocked || stale || !selectedBeats.length} onClick={() => void run(async () => {
            const next = await post<Plan>(`${base}/${plan.id}/feedback`, { expectedPlanRevision: plan.revision, feedback, beatIds: selectedBeats });
            await finish(next);
          })}>{feedback}</button>)}
      </details>
    </>}
  </section>;
}
