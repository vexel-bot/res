import React from "react";
import {
  Download,
  History,
  Layers3,
  RefreshCw,
  Send,
  Upload,
} from "lucide-react";
import { productApi } from "../../api/productApi";
import type { CraftDocument } from "../craft/craftApi";
import type { VideoController } from "./VideoStudio";
import { craftError } from "../craft/useCraftStudio";
import { conversionWarnings } from "./videoUsability";

const EditorialReviewPanel = React.lazy(() =>
  import("../EditorialReviewPanel").then((module) => ({
    default: module.EditorialReviewPanel,
  })),
);

/** Reuses the original editor's lifecycle features, disclosed only when requested. */
export function VideoProjectTools({
  studio,
  doc,
  locked,
  run,
  onApprovals,
  onOpenProject,
  draftDirty,
}: {
  studio: VideoController;
  doc: CraftDocument;
  locked: boolean;
  run: (task: () => Promise<unknown>) => Promise<void>;
  onApprovals: () => void;
  onOpenProject: (doc: CraftDocument) => Promise<void>;
  draftDirty: boolean;
}) {
  const [reviewOpen, setReviewOpen] = React.useState(false);
  const [gate, setGate] = React.useState<{
    documentId: string;
    revision: number;
    blocked: boolean;
  }>();
  const [historyError, setHistoryError] = React.useState<string>();
  const [reviewSent, setReviewSent] = React.useState(false);
  const nativeInput = React.useRef<HTMLInputElement>(null);
  const warnings = conversionWarnings(doc, studio.inspection);
  const extension =
    doc.nativeEditorState?.engine === "effectcraft" ? "ecproj" : "fcproj";
  const downloadExtension =
    (doc.nativeEditorState?.pageProjects?.length || 0) > 1 ? "zip" : extension;
  const confirmedRevision =
    studio.job?.status === "succeeded" &&
    studio.job.documentId === doc.documentId &&
    studio.jobRevision === doc.revision;
  const gateReady =
    gate?.documentId === doc.documentId &&
    gate.revision === doc.revision &&
    !gate.blocked;
  // A gate is usable only for its exact document/revision; do not clear a fresh
  // child readiness response when the parent and child effects run together.
  React.useEffect(() => {
    setReviewSent(false);
  }, [doc.documentId, doc.revision]);
  async function history() {
    setHistoryError(undefined);
    try {
      await studio.loadVersions();
    } catch (cause) {
      setHistoryError(craftError(cause));
    }
  }
  async function download() {
    const blob = await studio.loadNative();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${doc.title}.${downloadExtension}`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <div className="vs-project-tools">
      {warnings.length > 0 && (
        <details className="vs-disclosure">
          <summary>
            <Layers3 size={15} />
            <span>
              Observações da conversão
              <small>
                {warnings.length} ponto{warnings.length === 1 ? "" : "s"} para
                conferir no motor nativo
              </small>
            </span>
          </summary>
          <div className="vs-disclosure-body">
            <p>
              O original foi preservado. A abertura do arquivo não comprova
              fidelidade visual; confira as observações antes de finalizar.
            </p>
            <ul>
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
            {doc.nativeEditorState?.engine === "filmcraft" &&
              doc.nativeEditorState.legacyArchiveAssetId && (
                <>
                  <button
                    disabled={locked || draftDirty}
                    onClick={() =>
                      void run(async () => {
                        if (
                          !window.confirm(
                            "Recuperar as camadas visuais do original em uma composição editável? O serviço preservará o arquivo original e verificará a revisão.",
                          )
                        )
                          return;
                        const recovered = await studio.recoverEffects();
                        if (!recovered.compositionDocumentId)
                          throw new Error(
                            "A composição recuperada não foi confirmada pelo servidor.",
                          );
                        await onOpenProject(
                          await productApi.studioDocument(
                            recovered.compositionDocumentId,
                          ),
                        );
                      })
                    }
                  >
                    <Layers3 size={14} /> Recuperar composição do original
                  </button>
                  {draftDirty && (
                    <p className="vs-fine">
                      Salve o briefing antes de recuperar e abrir a composição.
                    </p>
                  )}
                </>
              )}
          </div>
        </details>
      )}
      <details
        className="vs-disclosure"
        onToggle={(event) => {
          if (event.currentTarget.open) void history();
        }}
      >
        <summary>
          <History size={15} />
          <span>
            Histórico e arquivo do projeto
            <small>Versões salvas e formato nativo</small>
          </span>
        </summary>
        <div className="vs-disclosure-body">
          <p className="vs-fine">
            Revisão atual: {doc.revision}. Importar um arquivo substitui o
            estado nativo através do serviço existente, com controle de revisão.
          </p>
          {historyError && <p role="alert">{historyError}</p>}
          <div className="vs-version-list">
            {studio.versions.map((version) => (
              <div key={version.number}>
                <strong>Versão {version.number}</strong>
                <span>{version.label || "Alteração salva"}</span>
                <time>
                  {new Date(version.createdAt).toLocaleString("pt-BR")}
                </time>
              </div>
            ))}
          </div>
          {!studio.versions.length && (
            <p className="vs-fine">
              Nenhuma versão adicional foi retornada pelo serviço.
            </p>
          )}
          <div className="vs-button-row">
            <button disabled={studio.busy} onClick={() => void history()}>
              <RefreshCw size={14} /> Atualizar histórico
            </button>
            {doc.nativeEditorState && (
              <button disabled={studio.busy} onClick={() => void run(download)}>
                <Download size={14} /> Baixar .{downloadExtension}
              </button>
            )}
            {doc.nativeEditorState && (
              <button
                disabled={locked}
                onClick={() => nativeInput.current?.click()}
              >
                <Upload size={14} /> Importar .{extension}
              </button>
            )}
          </div>
          {doc.nativeEditorState?.engine === "effectcraft" &&
            studio.engineInfo?.available &&
            doc.nativeEditorState.buildId !== studio.engineInfo.buildId && (
              <button
                disabled={locked}
                onClick={() => void run(studio.upgradeBuild)}
              >
                Atualizar motor da composição
              </button>
            )}
        </div>
      </details>
      <details
        className="vs-disclosure"
        onToggle={(event) => {
          setReviewOpen(event.currentTarget.open);
          if (!event.currentTarget.open) setGate(undefined);
        }}
      >
        <summary>
          <Send size={15} />
          <span>
            Revisão da produção
            <small>Evidências e aprovação da revisão exportada</small>
          </span>
        </summary>
        <div className="vs-disclosure-body">
          <p>
            {doc.postRef?.id
              ? "Confira as evidências antes de enviar a exportação para aprovação."
              : "Projeto da biblioteca: use a revisão editorial para conferir as evidências. O envio para Aprovações exige um conteúdo vinculado no fluxo existente."}
          </p>
          {reviewOpen && (
            <React.Suspense
              fallback={<p role="status">Carregando revisão editorial…</p>}
            >
              <EditorialReviewPanel
                document={doc}
                disabled={locked}
                active={reviewOpen}
                onGateChange={setGate}
              />
            </React.Suspense>
          )}
          <button
            disabled={
              !doc.postRef?.id ||
              locked ||
              !gateReady ||
              !confirmedRevision ||
              Boolean(studio.pending) ||
              reviewSent
            }
            onClick={() =>
              void run(async () => {
                await studio.review();
                setReviewSent(true);
              })
            }
          >
            <Send size={14} /> Enviar para aprovação
          </button>
          {reviewSent && (
            <p role="status">
              Solicitação confirmada pelo serviço.
              <button className="vs-text-button" onClick={onApprovals}>
                Abrir Aprovações
              </button>
            </p>
          )}
        </div>
      </details>
      <input
        ref={nativeInput}
        type="file"
        hidden
        accept={`.${extension}`}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          if (!file.name.toLowerCase().endsWith(`.${extension}`)) {
            void run(async () => {
              throw new Error(
                `Escolha um arquivo .${extension} compatível com este projeto.`,
              );
            });
            return;
          }
          if (
            window.confirm(
              "Substituir o estado nativo do projeto pelo arquivo selecionado? O serviço verificará compatibilidade e revisão.",
            )
          )
            void run(() => studio.saveNative(file));
        }}
      />
    </div>
  );
}
