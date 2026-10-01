import React from "react";
import { apiFetch } from "../api";

export type MaterialNeed = {
  fontVariant?: string;
  id: string; clipId: string; kind: string; query: string; purpose: string; role: string;
  officialRequired: boolean; exact: boolean; required: boolean; acceptanceCriteria: string[]; assetId?: string | null;
  sourceClass?: string; visualDescription?: string; orientation?: string; durationSeconds?: number | null;
  alphaRequired?: boolean; postProcessing?: string[]; fallbackBehavior?: string;
};
export type MaterialRequest = MaterialNeed & {
  discovery?: { status: string; queriedAt: string; candidates: { providerId: string }[]; nextStep: string;
    reason?: string; providerReceipts?: { provider: string; configured: boolean; status?: string }[] } | null;
  status: string; resolvedAssetId?: string; acquisitionError?: string;
  candidates: { id: string; title: string }[];
  sources: { id: string; title: string }[]; generationAllowed: boolean;
};

export function needFromRequest(request: MaterialRequest): MaterialNeed {
  const { id, clipId, kind, query, purpose, role, officialRequired, exact, required, acceptanceCriteria, assetId,
    fontVariant, sourceClass, visualDescription, orientation, durationSeconds, alphaRequired, postProcessing,
    fallbackBehavior } = request;
  return { id, clipId, kind, query, purpose, role, officialRequired, exact, required, acceptanceCriteria, assetId,
    fontVariant, sourceClass, visualDescription, orientation, durationSeconds, alphaRequired, postProcessing,
    fallbackBehavior };
}

export function EditingMaterialRequests({ requests, workspaceId, disabled, onSelect }: {
  requests: MaterialRequest[]; workspaceId: string; disabled: boolean; onSelect: (need: MaterialNeed) => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState("");
  const alive = React.useRef(true);
  React.useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  async function acquire(request: MaterialRequest, sourceId: string) {
    setBusy(true); setMessage("");
    try {
      const asset = await apiFetch<{ id: string }>(`/api/v1/studios/v1/editing/resource-sources/${sourceId}/acquire?workspace_id=${encodeURIComponent(workspaceId)}`, { method: "POST" });
      if (!alive.current) return;
      onSelect({ ...needFromRequest(request), assetId: asset.id });
      setMessage("Arquivo obtido. Crie novamente a edição para aplicar a escolha.");
    } catch { if (alive.current) setMessage("Não foi possível obter este arquivo. Envie o material pelo acervo ou escolha outra fonte."); }
    finally { if (alive.current) setBusy(false); }
  }
  if (!requests.length) return null;
  return <section aria-label="Materiais necessários para a edição">
    <h3>Materiais para cada cena</h3>
    {requests.map(request => <fieldset key={request.id} disabled={disabled || busy}>
      <legend>{request.query} — {request.status === "resolved" ? "disponível" : "precisa de material"}</legend>
      <p>{request.purpose} Cena: {request.clipId}. Tipo: {request.kind}.</p>
      {request.sourceClass && <p>Origem necessária: {request.sourceClass}. Orientação: {request.orientation ?? "any"}.</p>}
      {request.officialRequired && <p>É necessário o arquivo de origem oficial; uma imagem gerada não substitui esse material.</p>}
      {request.acceptanceCriteria.map((criterion, index) => <p key={index}>{criterion}</p>)}
      {request.acquisitionError && <p>{request.acquisitionError}</p>}
      {request.discovery?.status === "unconfigured" && <p>A busca automática identificou esta necessidade, mas o conector de materiais ainda não está configurado.</p>}
      {request.discovery?.status === "candidates" && <p>O sistema encontrou {request.discovery.candidates.length} candidato(s) externos. A importação e a inspeção ainda estão pendentes.</p>}
      {request.discovery?.status === "unavailable" && <p>A fonte externa está indisponível. Esta necessidade permanece registrada.</p>}
      {request.discovery?.status === "discovery_only" && <p>Há uma prévia para descoberta, mas o arquivo autorizado ainda é necessário para o render.</p>}
      {request.discovery?.status === "generation_candidate" && <p>O sistema pode produzir uma alternativa original e a inspecionará antes de usá-la.</p>}
      {request.discovery?.providerReceipts?.map(receipt => <p key={receipt.provider}>{receipt.provider}: {receipt.configured ? receipt.status ?? "configurado" : "não configurado"}.</p>)}
      {request.candidates.map(asset => <button type="button" key={asset.id} onClick={() => {
        onSelect({ ...needFromRequest(request), assetId: asset.id });
        setMessage("Material escolhido. Crie novamente a edição para aplicar a escolha.");
      }}>Usar {asset.title}</button>)}
      {request.status !== "resolved" && <>
        {request.sources.map(source => <button type="button" key={source.id}
          onClick={() => void acquire(request, source.id)}>Obter {source.title}</button>)}
        <p>Você pode enviar o arquivo ou cadastrar sua fonte no acervo acima. Depois, crie novamente a edição.</p>
        {request.generationAllowed && <p>Se o material não existir, use a geração do acervo com referências e revise o candidato antes de incorporá-lo.</p>}
      </>}
    </fieldset>)}
    {message && <p role="status">{message}</p>}
  </section>;
}
