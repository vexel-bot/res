import React from "react";
import { apiFetch } from "../../api";
import { productApi } from "../../api/productApi";

export type ProjectFile = { assetId: string; title: string; role: "export" | "material"; available: boolean };

export function useProjectFiles(documentId: string | undefined, refresh: number) {
  const [files, setFiles] = React.useState<ProjectFile[]>([]);
  const [error, setError] = React.useState("");
  React.useEffect(() => {
    setFiles([]);
    setError("");
    if (!documentId) return;
    const controller = new AbortController();
    apiFetch<ProjectFile[]>(`/api/v1/studios/v1/documents/${encodeURIComponent(documentId)}/files`, { signal: controller.signal })
      .then(rows => { if (!controller.signal.aborted) setFiles(rows); })
      .catch(cause => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Não foi possível abrir os arquivos."); });
    return () => controller.abort();
  }, [documentId, refresh]);
  return { files, error };
}

export function saveDownload(blob: Blob, filename: string) {
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

export function ProjectFiles({ files }: { files: ProjectFile[] }) {
  const [downloading, setDownloading] = React.useState<string>();
  const [error, setError] = React.useState("");
  async function get(file: ProjectFile) {
    setError("");
    setDownloading(file.assetId);
    try {
      const blob = await productApi.studioAssetBlob(file.assetId);
      const extensions: Record<string, string> = { "video/mp4": ".mp4", "audio/wav": ".wav", "audio/mpeg": ".mp3", "audio/flac": ".flac", "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp" };
      const extension = extensions[blob.type] || "";
      saveDownload(blob, file.title.toLowerCase().endsWith(extension) ? file.title : file.title + extension);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível baixar o arquivo.");
    } finally {
      setDownloading(undefined);
    }
  }
  return <>
    {error && <p role="alert">{error}</p>}
    {files.length ? <ul>{files.map(file => <li key={file.assetId} className="flex flex-wrap items-center gap-2">
      <span>{file.title} · {file.role === "export" ? "Exportação" : "Material"}</span>
      {file.available
        ? <button type="button" disabled={Boolean(downloading)} onClick={() => void get(file)}>{downloading === file.assetId ? "Baixando…" : "Baixar"}</button>
        : <span>Indisponível</span>}
    </li>)}</ul> : <p>Nenhum arquivo registrado para este projeto.</p>}
  </>;
}
