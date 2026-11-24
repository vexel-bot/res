import React from "react";
import { craftApi, type CraftReview } from "./craftApi";

const reviewLabels: Record<string, string> = {
  candidate_review: "Variante de edição",
  isolated_audio_review: "Áudio isolado",
  native_draft: "Corte com mixagem",
  edit_join: "Emenda com mixagem",
};
const labelFor = (review: CraftReview) =>
  review.report.source?.label || reviewLabels[review.report.source?.kind ?? ""] || "Prévia";

export function CraftEditReviews({ documentId, revision }: { documentId: string; revision: number }) {
  const [reviews, setReviews] = React.useState<CraftReview[]>([]);
  const [assetId, setAssetId] = React.useState("");
  const [url, setUrl] = React.useState<string>();
  const [failed, setFailed] = React.useState(false);
  const selected = reviews.find((review) => review.assetId === assetId);
  React.useEffect(() => {
    const controller = new AbortController();
    void craftApi.reviews(documentId, controller.signal).then(({ reviews }) => {
      if (!controller.signal.aborted) setReviews(reviews.filter((review) => {
        const kind = review.report.source?.kind;
        return kind != null && Object.prototype.hasOwnProperty.call(reviewLabels, kind);
      }));
    }).catch(() => {
      if (!controller.signal.aborted) setReviews([]);
    });
    return () => controller.abort();
  }, [documentId, revision]);
  React.useEffect(() => {
    setUrl(undefined);
    setFailed(false);
    if (!assetId) return;
    const controller = new AbortController();
    let objectUrl: string | undefined;
    void craftApi.reviewMedia(documentId, assetId, controller.signal).then((blob) => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
    }).catch(() => {
      if (!controller.signal.aborted) setFailed(true);
    });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, assetId]);
  if (!reviews.length) return null;
  return (
    <div className="craft-export-options">
      <h2>Prévias da edição</h2>
      <label>Trecho
        <select value={assetId} onChange={(event) => setAssetId(event.target.value)}>
          <option value="">Escolher uma prévia</option>
          {reviews.map((review) => {
            const interval = review.report.interval;
            return <option key={review.assetId} value={review.assetId}>
              {labelFor(review)} · {interval.startSeconds}s a {interval.endSeconds}s
            </option>;
          })}
        </select>
      </label>
      {failed && <p role="alert">Não foi possível reproduzir o trecho.</p>}
      {selected && url && (selected.mediaType.startsWith("audio/")
        ? <audio controls src={url} aria-label={labelFor(selected)} style={{ width: "100%" }} />
        : <video controls playsInline src={url} aria-label={labelFor(selected)} style={{ width: "100%" }} />)}
    </div>
  );
}
