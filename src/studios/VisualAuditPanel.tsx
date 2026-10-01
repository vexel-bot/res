import React from "react";

export type VisualAudit = {
  status?: string;
  human?: string;
  coverage?: { requestedFrames: number; observedFrames: number; complete: boolean; wholeVideoInspected?: boolean };
  states?: { sceneId: string; frames: Record<string, number>; observedFrames: Record<string, number>; status: string }[];
  renderedEvidence?: { frame: number; image: string; checksumSha256: string }[];
  findings?: { sceneId: string; elementId: string; code: string; correction: string }[];
  motion?: { cameraTrackIds: string[]; linearCameraTrackIds: string[]; overshootTrackIds: string[];
    keywordCueCount: number; motionCueCount: number; peakSimultaneousSalientElements: number };
  actionVerification?: { status: string; evidence: { sceneId: string; elementId: string; cue: string;
    normalizedPixelDifference?: number | null; status: string }[] };
  executionVerification?: { status: string; evidence: { sceneId: string; elementId: string; cue: string;
    normalizedPixelDifference?: number | null; status: string }[] };
  semanticVerification?: { policy: string; required: boolean; status: string; evidence: {
    assertionId: string; sceneId: string; kind: string; status: string; reason: string;
    checkpoints?: number[]; partVisibility?: Record<string, boolean[]> }[] };
  humanVerification?: { status: string; evidence: unknown[] };
  regionMotion?: { sceneId: string; elementId: string; visualRole: string;
    meanNormalizedPixelDifference: number; maximumNormalizedPixelDifference: number }[];
  materialRegionOfInterest?: { sceneId: string; elementId: string; purpose: string;
    minimumVisibleRatio?: number | null; status: string }[];
};

export function VisualAuditPanel({ audit }: { audit: VisualAudit }) {
  const labels: Record<string, string> = { start: "Entrada", demonstration: "Demonstração", consequence: "Consequência", exit: "Saída" };
  const images = new Map(audit.renderedEvidence?.map(item => [item.frame, item]));
  return <details>
    <summary>Examinar estados do vídeo exportado</summary>
    <p>As imagens foram extraídas do vídeo. Clareza, continuidade e execução das ações ainda precisam de avaliação.</p>
    {audit.status === "unavailable" && <p>Não foi possível extrair os estados. A avaliação permanece pendente.</p>}
    {audit.coverage && !audit.coverage.complete && <p>Cobertura parcial: {audit.coverage.observedFrames} de {audit.coverage.requestedFrames} frames previstos.</p>}
    {audit.coverage && !audit.coverage.wholeVideoInspected && <p>Amostragem temporal: o arquivo inteiro ainda não foi inspecionado continuamente.</p>}
    {audit.motion && <p>Câmera: {audit.motion.cameraTrackIds.length} trilha(s); overshoot: {audit.motion.overshootTrackIds.length}; palavras-chave: {audit.motion.keywordCueCount}; ações de motion: {audit.motion.motionCueCount}.</p>}
    {audit.states?.map(scene => <section key={scene.sceneId} aria-label={`Estados da cena ${scene.sceneId}`}>
      <h4>Cena {scene.sceneId}</h4>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
        {Object.entries(scene.frames).map(([state, frame]) => {
          const evidence = images.get(frame);
          return <figure key={state} style={{ margin: 0, width: 300, maxWidth: "100%" }}>
            <figcaption>{labels[state] ?? state} · frame {frame}</figcaption>
            {evidence?.image.startsWith("data:image/jpeg;base64,")
              ? <img src={evidence.image} width={300} style={{ maxWidth: "100%" }} alt={`${labels[state] ?? state} da cena ${scene.sceneId}`} />
              : <p>Imagem pendente.</p>}
          </figure>;
        })}
      </div>
    </section>)}
    {!!audit.findings?.length && <details><summary>{audit.findings.length} achado(s) visual(is)</summary>
      {audit.findings.map((item, index) => <p key={`${item.sceneId}:${item.elementId}:${item.code}:${index}`}>
        {item.sceneId} · {item.elementId}: {item.code}. {item.correction}
      </p>)}
    </details>}
    {!!audit.materialRegionOfInterest?.length && <details><summary>Enquadramento dos materiais</summary>
      {audit.materialRegionOfInterest.map(item => <p key={`${item.sceneId}:${item.elementId}`}>
        {item.sceneId} · {item.elementId}: {item.status}
        {typeof item.minimumVisibleRatio === "number" ? ` · ${(item.minimumVisibleRatio * 100).toFixed(0)}% da região essencial visível` : ""}.
      </p>)}
    </details>}
    {(audit.executionVerification ?? audit.actionVerification) && <details><summary>Execução do movimento</summary>
      <p>{(audit.executionVerification ?? audit.actionVerification)?.status === "observed" ? "As operações produziram mudanças observáveis." : "Uma ou mais operações precisam de revisão nos frames."} Movimento não comprova sozinho a mensagem.</p>
      {(audit.executionVerification ?? audit.actionVerification)?.evidence.map(item => <p key={`${item.sceneId}:${item.elementId}:${item.cue}`}>
        {item.sceneId} · {item.elementId} · {item.cue}: {item.status}
        {typeof item.normalizedPixelDifference === "number" ? ` (${item.normalizedPixelDifference.toFixed(3)})` : ""}
      </p>)}
    </details>}
    {audit.semanticVerification && <details open><summary>Resultado semântico</summary>
      <p>{audit.semanticVerification.required ? "Verificação obrigatória" : "Política antiga"}: {audit.semanticVerification.status}.</p>
      {!audit.semanticVerification.evidence.length && <p>Nenhuma afirmação falsificável foi vinculada a este vídeo.</p>}
      {audit.semanticVerification.evidence.map(item => <p key={`${item.sceneId}:${item.assertionId}`}>
        {item.sceneId} · {item.kind}: <strong>{item.status}</strong>. {item.reason}
      </p>)}
    </details>}
    {audit.humanVerification && <p>Compreensão humana: {audit.humanVerification.status}.</p>}
  </details>;
}
