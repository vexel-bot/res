import React from "react";
import { productApi, type StudioReviewRecord } from "../api/productApi";

export function ReviewSnapshotPreview({ review, pageId, onReady }: {
  review: StudioReviewRecord;
  pageId?: string;
  onReady: (ready: boolean) => void;
}) {
  const [url, setUrl] = React.useState<string>();
  const [error, setError] = React.useState<string>();
  const video = review.snapshot.contentType === "video" || review.snapshot.contentType === "presenter";
  React.useEffect(() => {
    let active = true;
    let objectUrl: string | undefined;
    setUrl(undefined);
    setError(undefined);
    onReady(false);
    const load = async () => {
      try {
        let blob: Blob;
        if (video) {
          if (!review.renderAssetId || !review.renderChecksumSha256) throw new Error("Render não vinculado");
          blob = await productApi.studioAssetBlob(review.renderAssetId);
          const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
          const checksum = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
          if (checksum !== review.renderChecksumSha256.toLowerCase()) throw new Error("Render divergente");
        } else {
          if (!pageId) throw new Error("Página não encontrada");
          blob = await productApi.studioReviewPageBlob(review.id, pageId);
        }
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch {
        if (active) setError("Não foi possível carregar a mídia desta revisão. Nenhuma arte de demonstração foi usada. Reabra a revisão ou volte ao Studio para verificar as fontes.");
      }
    };
    void load();
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [review.id, review.renderAssetId, review.renderChecksumSha256, pageId, video, onReady]);
  if (error) return <p role="alert">{error}</p>;
  if (!url) return <p role="status">Carregando mídia da versão fixada…</p>;
  if (video) return <video className="cx-review-snapshot-media" data-testid="review-snapshot-video" controls src={url} onLoadedData={() => onReady(true)} onError={() => { onReady(false); setError("O render não pôde ser reproduzido."); }} aria-label={`Render da versão ${review.documentVersion}`} />;
  return <img className="cx-review-snapshot-media" data-testid="review-snapshot-image" src={url} onLoad={() => onReady(true)} onError={() => { onReady(false); setError("A imagem da revisão não pôde ser exibida."); }} alt={`Página ${pageId} da versão ${review.documentVersion}`} />;
}
