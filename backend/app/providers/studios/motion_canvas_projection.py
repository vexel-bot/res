"""Validated data projection for the isolated Motion Canvas worker.

The worker runs registered TypeScript components, never model-authored code.
Unsupported operations fail before frames are rendered.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from ...domain.studios.motion import MotionGraphProjectionV1
from ...domain.studios.contracts import CreativeDocumentV1

SUPPORTED_PATHS = {
    "position.x",
    "position.y",
    "scale.x",
    "scale.y",
    "rotation.degrees",
    "opacity",
    "filters.blurPx",
    "fontSize.px",
    "letterSpacing.px",
    "lineHeight.ratio",
    "fontWeight",
}
SUPPORTED_TRANSITIONS = {"hard_cut", "dissolve"}


def compile_motion_canvas_manifest(projection: MotionGraphProjectionV1) -> dict:
    if projection.target != "motion_canvas":
        raise ValueError("motion_canvas_projection_target_required")
    unsupported_paths = sorted({track.property_path for track in projection.tracks} - SUPPORTED_PATHS)
    unsupported_transitions = sorted({item.kind for item in projection.transitions} - SUPPORTED_TRANSITIONS)
    blockers = [
        *["unsupported_property:" + value for value in unsupported_paths],
        *["unsupported_transition:" + value for value in unsupported_transitions],
    ]
    if blockers:
        raise ValueError("motion_canvas_projection_unsupported:" + ",".join(blockers))
    payload = projection.model_dump(mode="json", by_alias=True, exclude_none=True)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schemaVersion": "studio.motion-canvas-execution-manifest.v1",
        "sourceProjectionDigestSha256": hashlib.sha256(canonical).hexdigest(),
        "runtimeStatus": "adapter_only",
        "executableCodeIncluded": False,
        "projection": payload,
    }


def compile_motion_canvas_composition(
    document: CreativeDocumentV1,
    projection: MotionGraphProjectionV1,
    asset_files: dict[str, dict[str, str]],
) -> dict:
    """Bind one document page and its graph to the worker's finite component set."""
    compile_motion_canvas_manifest(projection)
    timeline = document.composition.media_timeline
    if timeline is None or len(document.composition.pages) != 1:
        raise ValueError("motion_canvas_single_video_page_required")
    page = document.composition.pages[0]
    if projection.duration_frames != timeline.duration_frames or projection.frame_rate != timeline.frame_rate:
        raise ValueError("motion_canvas_timeline_binding_conflict")
    fps = projection.frame_rate.numerator / projection.frame_rate.denominator
    if fps != int(fps):
        raise ValueError("motion_canvas_integer_frame_rate_required")
    layer_ids = {layer.id for layer in page.layers}
    if len(layer_ids) != len(page.layers):
        raise ValueError("motion_canvas_duplicate_layer_id")
    for track in projection.tracks:
        if track.target_layer_id not in layer_ids:
            raise ValueError("motion_canvas_track_target_missing:" + track.target_layer_id)
    for transition in projection.transitions:
        if transition.from_layer_id not in layer_ids or transition.to_layer_id not in layer_ids:
            raise ValueError("motion_canvas_transition_target_missing")
    bound_assets: set[str] = set()
    fonts: list[dict] = []
    layers = []
    image_sizes: dict[str, tuple[int, int]] = {}
    for layer in page.layers:
        if layer.kind not in {"text", "shape", "image", "group"}:
            raise ValueError("motion_canvas_layer_unsupported:" + layer.id + ":" + layer.kind)
        props = dict(layer.properties)
        if (
            props.get("maskAssetId")
            or props.get("editorialEffects")
            or props.get("editorialTextSpans")
            or props.get("editorialBlendMode", "normal") != "normal"
            or props.get("editorialShadow")
            or (props.get("editorialBorder") or {}).get("width", 0) > 0
        ):
            raise ValueError("motion_canvas_layer_effect_unsupported:" + layer.id)
        timing = props.get("editorialTiming") or {}
        reveal = timing.get("reveal", "none")
        if reveal not in {"none", "words", "path"}:
            raise ValueError("motion_canvas_reveal_unsupported:" + layer.id + ":" + reveal)
        if reveal == "words" and layer.kind != "text":
            raise ValueError("motion_canvas_word_reveal_requires_text:" + layer.id)
        if reveal == "path" and not props.get("editorialPath"):
            raise ValueError("motion_canvas_path_reveal_requires_path:" + layer.id)
        if layer.kind == "image":
            asset_id = props.get("assetId")
            if not isinstance(asset_id, str) or not asset_id:
                raise ValueError("motion_canvas_image_asset_required:" + layer.id)
            object_fit = props.get("objectFit", "cover")
            if object_fit not in {"contain", "cover", "fill"}:
                raise ValueError("motion_canvas_image_fit_unsupported:" + layer.id)
            if asset_id not in asset_files:
                raise ValueError("motion_canvas_asset_missing:" + asset_id)
            if asset_id not in image_sizes:
                try:
                    with Image.open(Path(asset_files[asset_id]["path"])) as image:
                        image_sizes[asset_id] = image.size
                        if max(image.size) > 16384:
                            raise ValueError("image_dimensions_too_large")
                        image.verify()
                except (OSError, UnidentifiedImageError, KeyError, ValueError) as exc:
                    raise ValueError("motion_canvas_image_decode_failed:" + asset_id) from exc
            if min(image_sizes[asset_id]) < 1:
                raise ValueError("motion_canvas_image_dimensions_invalid:" + asset_id)
            props["objectFit"] = object_fit
            props["naturalWidth"], props["naturalHeight"] = image_sizes[asset_id]
            bound_assets.add(asset_id)
        if layer.kind == "text":
            if not isinstance(props.get("text"), str):
                raise ValueError("motion_canvas_text_required:" + layer.id)
            font_id = props.get("fontAssetId")
            if font_id:
                bound_assets.add(font_id)
                fonts.append({
                    "assetId": font_id,
                    "family": str(props.get("fontFamily") or "ResProjectFont"),
                    "weight": props.get("fontWeight", 400),
                })
        if props.get("editorialPath") and layer.kind != "shape":
            raise ValueError("motion_canvas_path_requires_shape:" + layer.id)
        layer_data = layer.model_dump(mode="json", by_alias=True)
        layer_data["properties"] = props
        layers.append(layer_data)
    if missing := sorted(bound_assets - asset_files.keys()):
        raise ValueError("motion_canvas_asset_missing:" + ",".join(missing))
    refs = {asset.id: asset for asset in document.assets}
    for asset_id in bound_assets:
        if asset_id not in refs or not refs[asset_id].checksum:
            raise ValueError("motion_canvas_asset_checksum_required:" + asset_id)
        if refs[asset_id].checksum.lower() != asset_files[asset_id]["sha256"].lower():
            raise ValueError("motion_canvas_asset_checksum_conflict:" + asset_id)
    return {
        "schemaVersion": "res.motion-canvas-composition.v1",
        "documentId": document.document_id,
        "documentRevision": document.revision,
        "graphDigestSha256": projection.source_graph_digest_sha256,
        "width": page.width,
        "height": page.height,
        "fps": int(fps),
        "durationFrames": timeline.duration_frames,
        "background": page.background,
        "layers": layers,
        "nodes": [node.model_dump(mode="json", by_alias=True) for node in projection.nodes],
        "tracks": [track.model_dump(mode="json", by_alias=True) for track in projection.tracks],
        "transitions": [item.model_dump(mode="json", by_alias=True) for item in projection.transitions],
        "fonts": fonts,
        "assetFiles": {asset_id: asset_files[asset_id] for asset_id in sorted(bound_assets)},
    }
