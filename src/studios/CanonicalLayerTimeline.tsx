import React from "react";
import type { StudioDocumentRecord } from "../api/productApi";

export type LayerSelection = { layerId: string; sceneId: string; nonce: number };

// A read-only projection of the persisted document, never a second timeline model.
export function CanonicalLayerTimeline({ document, frame, onSeek, onSelect }: {
  document: StudioDocumentRecord; frame: number; onSeek: (frame: number) => void;
  onSelect: (layerId: string, sceneId: string) => void;
}) {
  const timeline = document.composition.mediaTimeline;
  if (!timeline) return <p role="status">Timeline canônica indisponível.</p>;
  const lastFrame = Math.max(0, timeline.durationFrames - 1);
  const layers = document.composition.pages.flatMap(page => page.layers);
  return <div className="vs-canonical-timeline" aria-label="Intervalos das camadas canônicas">
    <div className="vs-canonical-ruler" role="slider" tabIndex={0}
      aria-label="Playhead da composição" aria-valuemin={0} aria-valuemax={lastFrame}
      aria-valuenow={Math.min(frame, lastFrame)}
      onPointerDown={event => {
        const rect = event.currentTarget.getBoundingClientRect();
        onSeek(Math.min(lastFrame, Math.max(0, Math.floor((event.clientX - rect.left) / rect.width * timeline.durationFrames))));
      }}
      onKeyDown={event => {
        const target = event.key === "Home" ? 0 : event.key === "End" ? lastFrame
          : event.key === "ArrowLeft" ? frame - 1 : event.key === "ArrowRight" ? frame + 1 : undefined;
        if (target !== undefined) { event.preventDefault(); onSeek(Math.min(lastFrame, Math.max(0, target))); }
      }}>
      <span>Frame 0</span><span>Frame {Math.min(frame, lastFrame)} / {lastFrame}</span>
    </div>
    <p>Intervalos [início, fim) · selecione para inspecionar · revisão {document.revision}</p>
    {layers.map(layer => {
      const properties = (layer.properties ?? {}) as Record<string, unknown>;
      const timing = properties.editorialTiming as { startFrame?: number; durationFrames?: number; fps?: number } | undefined;
      const start = timing?.startFrame;
      const length = timing?.durationFrames;
      const sceneId = typeof properties.editorialSceneId === "string" ? properties.editorialSceneId : "";
      const valid = typeof start === "number" && Number.isInteger(start) && start >= 0
        && typeof length === "number" && Number.isInteger(length) && length > 0
        && start + length <= timeline.durationFrames
        && timing?.fps === timeline.frameRate.numerator / timeline.frameRate.denominator;
      return <div className="vs-canonical-row" key={layer.id}>
        <span title={`${layer.name} · ${layer.kind} · ${layer.id}`}>{layer.name} · {layer.kind}</span>
        <div className="vs-canonical-lane">
          {valid ? <button type="button" data-layer-id={layer.id} data-scene-id={sceneId}
            data-start-frame={start} data-duration-frames={length}
            data-source-start-seconds={typeof properties.sourceStartSeconds === "number" ? properties.sourceStartSeconds : undefined}
            data-playback-rate={typeof properties.playbackRate === "number" ? properties.playbackRate : undefined}
            aria-label={`Inspecionar ${layer.name} · frames [${start}, ${start + length})`}
            title={`${layer.name} · [${start}, ${start + length})${layer.kind === "video" ? ` · fonte ${properties.sourceStartSeconds ?? 0}s · velocidade ${properties.playbackRate ?? 1}×` : ""}`}
            style={{ left: `${start / timeline.durationFrames * 100}%`, width: `${length / timeline.durationFrames * 100}%` }}
            onClick={() => { onSeek(start); onSelect(layer.id, sceneId); }}>
            [{start}, {start + length})
          </button> : <em>Intervalo ausente ou incompatível</em>}
          <i className="vs-canonical-playhead" style={{ left: `${Math.min(frame, lastFrame) / timeline.durationFrames * 100}%` }} />
        </div>
      </div>;
    })}
  </div>;
}
