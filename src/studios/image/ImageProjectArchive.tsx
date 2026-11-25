import React from "react";
import { productApi, type StudioDocumentRecord } from "../../api/productApi";
import { useProductData } from "../../context/ProductDataContext";
import { ProjectFiles, useProjectFiles } from "../shared/ProjectFiles";

export function ImageProjectArchive() {
  const workspaceId = useProductData().activeWorkspace?.id;
  const [projects, setProjects] = React.useState<StudioDocumentRecord[]>([]);
  const [selected, setSelected] = React.useState("");
  const [error, setError] = React.useState("");
  const { files, error: filesError } = useProjectFiles(selected || undefined, 0);

  React.useEffect(() => {
    setProjects([]);
    setSelected("");
    setError("");
    if (!workspaceId) return;
    let current = true;
    productApi.studioDocuments(workspaceId).then(rows => {
      if (current) setProjects(rows.filter(row => row.contentType === "visual" || row.contentType === "carousel"));
    }).catch(cause => {
      if (current) setError(cause instanceof Error ? cause.message : "Não foi possível abrir os projetos.");
    });
    return () => { current = false; };
  }, [workspaceId]);

  return <section className="space-y-4">
    <h1 className="text-2xl font-semibold">Projetos de imagem</h1>
    {(error || filesError) && <p role="alert">{error || filesError}</p>}
    <label className="grid w-fit gap-1">Projeto
      <select value={selected} onChange={event => setSelected(event.target.value)}>
        <option value="">Selecione um projeto</option>
        {projects.map(row => <option key={row.documentId} value={row.documentId}>{row.title}</option>)}
      </select>
    </label>
    {selected && <ProjectFiles key={selected} files={files} />}
  </section>;
}
