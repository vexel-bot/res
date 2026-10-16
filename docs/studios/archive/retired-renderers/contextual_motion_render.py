"""Private draft composition through HyperFrames, followed by canonical FFmpeg mixing."""

import tempfile
import time
from pathlib import Path

from ...domain.studios.contracts import AssetReferenceV1, MediaClipV1, VideoTrackV1
from ...domain.studios.motion import MotionGraphV1, evaluate_motion_graph, project_motion_graph


class ContextualMotionRenderProvider:
    name = "hyperframes.contextual-v2"
    version = "2.0.0"
    projection_target = "hyperframes"

    def __init__(self, graphics, audiovisual):
        self.graphics, self.audiovisual = graphics, audiovisual

    def render(self, document, request, assets, destination, progress, is_cancelled, **kwargs):
        if kwargs:
            raise ValueError("editing_v2_projection_must_be_bound_to_document")
        bound = document.composition.narrative.get("editorialV2", {})
        if bound.get("renderPolicy") != "automatic_draft" or not bound.get("planId"):
            raise ValueError("editing_v2_draft_policy_required")
        graph = MotionGraphV1.model_validate(bound.get("motionGraph"))
        if (
            graph.document_id != document.document_id
            or graph.workspace_id != document.workspace_id
            or graph.document_revision != document.revision
        ):
            raise ValueError("editing_v2_graph_binding_conflict")
        evaluation = evaluate_motion_graph(document, graph)
        if not evaluation.eligible_for_reviewed_projection:
            raise ValueError("editing_v2_motion_constraints_failed")
        projection = project_motion_graph(graph, self.projection_target, evaluation)
        from ...services.object_storage import sha256_file
        from .media_probe import MEDIA_PROBE_PROVIDERS

        refs = {a.id: a for a in document.assets}
        from fontTools.ttLib import TTFont

        for page in document.composition.pages:
            for layer in page.layers:
                font_id = layer.properties.get("fontAssetId")
                if layer.kind == "text" and font_id:
                    if font_id not in assets or sha256_file(assets[font_id]) != refs[font_id].checksum:
                        raise ValueError("editing_v2_font_binding_conflict")
                    with TTFont(assets[font_id]) as font:
                        cmap = font.getBestCmap() or {}
                        if any(ord(c) not in cmap for c in layer.properties.get("text", "") if not c.isspace()):
                            raise ValueError("editing_v2_font_glyph_missing:" + layer.id)
        ranges = []
        for page in document.composition.pages:
            for layer in page.layers:
                if layer.kind == "video" and layer.visible:
                    props = layer.properties
                    timing = props["editorialTiming"]
                    ranges.append(
                        (
                            props["assetId"],
                            props.get("sourceStartSeconds", 0),
                            timing["durationFrames"] / timing["fps"] * props.get("playbackRate", 1),
                            False,
                        )
                    )
        for track in document.composition.media_timeline.tracks:
            if track.kind == "audio" and not track.muted:
                for clip in track.clips:
                    if clip.enabled:
                        ranges.append(
                            (
                                clip.asset_id,
                                clip.source.start_microseconds / 1e6,
                                clip.source.duration_microseconds / 1e6,
                                True,
                            )
                        )
        probes = {}
        for asset_id, offset, duration, require_audio in ranges:
            if (
                asset_id not in assets
                or asset_id not in refs
                or sha256_file(assets[asset_id]) != refs[asset_id].checksum
            ):
                raise ValueError("editing_v2_source_binding_conflict")
            if asset_id not in probes:
                probes[asset_id] = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                    assets[asset_id], asset_id=asset_id, checksum_sha256=refs[asset_id].checksum
                )
            probe = probes[asset_id]
            if offset + duration > probe.duration_microseconds / 1e6 + 0.04:
                raise ValueError("editing_v2_source_interval_out_of_bounds")
            if require_audio and not probe.audio_streams:
                raise ValueError("editing_v2_source_audio_missing")
        graphics = document.model_copy(deep=True)
        graphics.composition.media_timeline.tracks = []
        graphics_request = request.model_copy(deep=True)
        graphics_request.output.audio_codec = "none"
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="res-motion-v2-") as temp:
            visual = Path(temp) / "visual.mp4"
            graphics_result = self.graphics.render(
                graphics,
                graphics_request,
                assets,
                visual,
                lambda value: progress(round(value * 0.7)),
                is_cancelled,
                motion_projection=projection,
                automatic_draft=True,
            )
            mixed = document.model_copy(deep=True)
            mixed.composition.pages[0].layers = []
            checksum = sha256_file(visual)
            asset_id = "compiled-" + checksum[:24]
            mixed.assets.append(
                AssetReferenceV1(
                    id=asset_id, media_type="video/mp4", checksum=checksum, rights_status="verified", origin="derived"
                )
            )
            timeline = mixed.composition.media_timeline
            fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
            timeline.tracks.insert(
                0,
                VideoTrackV1(
                    id="compiled-visual",
                    muted=True,
                    clips=[
                        MediaClipV1(
                            id="compiled-visual",
                            asset_id=asset_id,
                            timeline={"startFrame": 0, "durationFrames": timeline.duration_frames},
                            source={
                                "startMicroseconds": 0,
                                "durationMicroseconds": round(timeline.duration_frames / fps * 1e6),
                            },
                        )
                    ],
                ),
            )
            result = self.audiovisual.render(
                mixed,
                request,
                {**assets, asset_id: visual},
                destination,
                lambda value: progress(70 + round(value * 0.3)),
                is_cancelled,
            )
        return result.model_copy(
            update={
                "provider": self.name,
                "provider_version": self.version,
                "renderer_checks": {
                    "graphics": graphics_result.renderer_checks,
                    "audiovisual": result.renderer_checks,
                    # The final-video auditor consumes top-level observed
                    # geometry. Keep the nested receipts for provenance while
                    # forwarding the samples from the renderer that actually
                    # produced the visual frames.
                    "geometrySchemaVersion": (
                        graphics_result.renderer_checks.get("geometrySchemaVersion")
                        or graphics_result.renderer_checks.get("motionCanvasReceipt", {}).get("geometrySchemaVersion")
                    ),
                    "geometrySamples": (
                        graphics_result.renderer_checks.get("geometrySamples")
                        or graphics_result.renderer_checks.get("motionCanvasReceipt", {}).get("geometrySamples", [])
                    ),
                },
                "render_duration_ms": round((time.monotonic() - start) * 1000),
                "rendered_layer_ids": [
                    layer.id for page in document.composition.pages for layer in page.layers if layer.visible
                ],
                "warnings": [*result.warnings, "Automatic draft; human audiovisual review pending."],
            }
        )
