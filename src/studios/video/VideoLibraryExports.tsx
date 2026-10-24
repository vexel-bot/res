import React from "react";
import { Download, RefreshCw } from "lucide-react";
import { apiFetch, APIError } from "../../api";
import type { AssetRecord } from "../../api/productApi";
import { useGovernance } from "../../context/GovernanceContext";
import { useOperations } from "../../context/OperationsContext";
import { videoOutputUrl } from "./canonicalVideoApi";

/** A read-through view of the existing Studio asset store, never a second copy. */
export function VideoLibraryExports({
  query,
  sort,
  onCountChange,
}: {
  query: string;
  sort: "recent" | "oldest" | "name";
  onCountChange?: (count: number) => void;
}) {
  const { activeAccount } = useGovernance();
  const { activeClient } = useOperations();
  const [assets, setAssets] = React.useState<AssetRecord[]>([]);
  const [error, setError] = React.useState("");
  const [revision, setRevision] = React.useState(0);
  React.useEffect(() => {
    const controller = new AbortController();
    setAssets([]);
    setError("");
    const headers = new Headers({
      "x-clicko-studio-module": "create-video",
      "x-workspace-id": activeAccount.workspaceId,
    });
    if (activeClient) headers.set("x-clicko-client-id", activeClient.id);
    void apiFetch<AssetRecord[]>("/api/v1/studios/v1/video/library", {
      headers,
      signal: controller.signal,
    })
      .then((value) => {
        if (!controller.signal.aborted) setAssets(value);
      })
      .catch((e) => {
        if (
          !controller.signal.aborted &&
          !(e instanceof APIError && e.status === 403)
        )
          setError("Não foi possível consultar os vídeos do Studio.");
      });
    return () => controller.abort();
  }, [activeAccount.workspaceId, activeClient?.id, revision]);
  React.useEffect(() => {
    const reload = () => setRevision((v) => v + 1);
    window.addEventListener("clicko:video-library-updated", reload);
    return () =>
      window.removeEventListener("clicko:video-library-updated", reload);
  }, []);
  const visible = assets
    .filter((a) =>
      a.title
        .toLocaleLowerCase("pt-BR")
        .includes(query.toLocaleLowerCase("pt-BR")),
    )
    .sort((a, b) =>
      sort === "name"
        ? a.title.localeCompare(b.title, "pt-BR")
        : (sort === "recent" ? -1 : 1) *
          (Date.parse(a.createdAt) - Date.parse(b.createdAt)),
    );
  React.useEffect(() => {
    onCountChange?.(visible.length);
  }, [visible.length, onCountChange]);
  React.useEffect(() => () => onCountChange?.(0), [onCountChange]);
  if (!visible.length && !error) return null;
  return (
    <section
      aria-label="Vídeos exportados pelo Studio"
      style={{ marginBlock: "20px" }}
    >
      <div className="cx-library-section-head">
        <h2>Vídeos do Studio</h2>
        <span>{visible.length} {visible.length === 1 ? "arquivo" : "arquivos"}</span>
      </div>
      {error && (
        <p role="status">
          {error}
          <button
            className="cx-library-button"
            onClick={() => setRevision((v) => v + 1)}
          >
            <RefreshCw size={14} />
            Tentar novamente
          </button>
        </p>
      )}
      <div className="cx-library-assets">
        {visible.map((asset) => {
          const url = videoOutputUrl(
            asset.id,
            activeAccount.workspaceId,
            activeClient?.id,
          );
          return (
            <article
              key={asset.id}
              style={{
                minWidth: 0,
                padding: 12,
                border: "1px solid var(--border-color, #303030)",
                borderRadius: 12,
              }}
            >
              <video
                src={url}
                controls
                playsInline
                preload="none"
                aria-label={asset.title}
                style={{
                  width: "100%",
                  maxHeight: 240,
                  background: "#000",
                  borderRadius: 8,
                }}
              />
              <h3 style={{ fontSize: 14, marginBlock: 10 }}>{asset.title}</h3>
              <a className="cx-library-button" href={url + "&download=1"}>
                <Download size={14} />
                Baixar MP4
              </a>
            </article>
          );
        })}
      </div>
    </section>
  );
}
