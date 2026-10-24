import React from "react";
import { ArrowRight, Check, Film, RefreshCw } from "lucide-react";
import { productApi } from "../../api/productApi";
import {
  departmentApi,
  type DepartmentProject,
} from "../department/departmentApi";
import type { CraftDocument } from "../craft/craftApi";
import { craftError } from "../craft/useCraftStudio";

/** Read existing department requests without copying them into a second project store. */
export function LegacyVideoProjects({
  workspaceId,
  disabled,
  engineAvailable,
  run,
  onOpen,
  onNotice,
}: {
  workspaceId: string;
  disabled: boolean;
  engineAvailable: boolean;
  run: (task: () => Promise<unknown>) => Promise<void>;
  onOpen: (document: CraftDocument) => Promise<void>;
  onNotice: (message: string) => void;
}) {
  const [projects, setProjects] = React.useState<DepartmentProject[]>([]);
  const [selected, setSelected] = React.useState<DepartmentProject>();
  const [error, setError] = React.useState<string>();
  const [reload, setReload] = React.useState(0);
  React.useEffect(() => {
    const controller = new AbortController();
    setError(undefined);
    void departmentApi
      .list(workspaceId, controller.signal)
      .then((rows) => {
        if (!controller.signal.aborted)
          setProjects(
            rows.filter((row) => row.format === "video" && !row.documentId),
          );
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(craftError(cause));
      });
    return () => controller.abort();
  }, [workspaceId, reload]);
  if (!projects.length && !error) return null;
  return (
    <div className="vs-legacy-projects">
      <h3>Pedidos anteriores</h3>
      <p className="vs-fine">
        Briefings preservados da versão anterior. Produções já convertidas
        aparecem na lista principal.
      </p>
      {error && (
        <div role="alert" className="vs-banner">
          {error}
          <button onClick={() => setReload((value) => value + 1)}>
            <RefreshCw size={13} /> Atualizar pedidos
          </button>
        </div>
      )}
      <div className="vs-project-grid">
        {projects.map((project) => (
          <button
            key={project.id}
            className="vs-project-card"
            disabled={disabled}
            onClick={() => setSelected(project)}
          >
            <Film size={22} />
            <span>
              <strong>{project.title}</strong>
              <small>
                Briefing salvo ·{" "}
                {new Date(project.updatedAt).toLocaleDateString("pt-BR")}
              </small>
            </span>
            <ArrowRight size={14} />
          </button>
        ))}
      </div>
      {selected && (
        <div className="vs-legacy-detail">
          <h4>{selected.title}</h4>
          <p>{selected.objective}</p>
          <p className="vs-fine">Público: {selected.audience}</p>
          <div className="vs-fields">
            {selected.directions.map((direction) => (
              <button
                key={direction.id}
                aria-pressed={selected.directionId === direction.id}
                disabled={disabled}
                onClick={() =>
                  void run(async () => {
                    const next = await departmentApi.choose(
                      selected,
                      direction.id,
                    );
                    setSelected(next);
                    setProjects((rows) =>
                      rows.map((row) => (row.id === next.id ? next : row)),
                    );
                  })
                }
              >
                {selected.directionId === direction.id && <Check size={14} />}
                {direction.title}
              </button>
            ))}
          </div>
          <p className="vs-fine">
            {!selected.sourceAssetId
              ? "Este pedido não possui um vídeo de origem. O contrato anterior exige esse material para produzir; o briefing original permanece preservado."
              : !engineAvailable
                ? "A continuidade da produção exige o runtime nativo. Nenhum projeto ou arquivo foi duplicado."
                : "Continue usando o mesmo pedido, seus materiais e a direção salva."}
          </p>
          <button
            className="vs-primary"
            disabled={
              disabled ||
              !engineAvailable ||
              !selected.directionId ||
              !selected.sourceAssetId
            }
            onClick={() =>
              void run(async () => {
                const next = await departmentApi.produce(selected);
                setSelected(next);
                setProjects((rows) =>
                  rows.map((row) => (row.id === next.id ? next : row)),
                );
                if (!next.documentId)
                  throw new Error(
                    "O serviço ainda não confirmou um documento para este pedido.",
                  );
                await onOpen(await productApi.studioDocument(next.documentId));
                onNotice(
                  next.status === "production_failed"
                    ? "O pedido foi recuperado, mas a produção falhou. Revise o serviço de renderização antes de exportar."
                    : "Pedido anterior recuperado no editor. Acompanhe o estado real da exportação.",
                );
              })
            }
          >
            Continuar pedido no editor <ArrowRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
