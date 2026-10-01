"""Project canonical layers into the independent native Remotion runtime."""

from ...domain.studios.contextual_editing import digest
from ...domain.studios.native_scenes import NativeSceneComponentV1


def compile_remotion_composition(document, projection, asset_files):
    timeline = document.composition.media_timeline
    if projection.target != "remotion" or timeline is None or len(document.composition.pages) != 1:
        raise ValueError("remotion_native_projection_required")
    if projection.duration_frames != timeline.duration_frames or projection.frame_rate != timeline.frame_rate:
        raise ValueError("remotion_native_timeline_conflict")
    page = document.composition.pages[0]
    if page.width % 2 or page.height % 2 or max(page.width, page.height) > 3840:
        raise ValueError("remotion_native_dimensions_unsupported")
    layers = []
    fonts = []
    required = set()
    refs = {asset.id: asset for asset in document.assets}
    ids = {layer.id for layer in page.layers}
    if len(ids) != len(page.layers):
        raise ValueError("remotion_native_duplicate_layer")
    for layer in page.layers:
        if layer.kind not in {"group", "video", "image", "text", "shape"}:
            raise ValueError("remotion_native_layer_unsupported:" + layer.kind)
        props = layer.properties
        # These features need their own pixel-level qualification before use.
        if props.get("editorialEffects") or props.get("editorialTextSpans") or props.get("editorialMatch"):
            raise ValueError("remotion_native_effect_unsupported:" + layer.id)
        component = props.get("nativeComponent")
        if component:
            NativeSceneComponentV1.model_validate(component)
        for field in ("assetId", "maskAssetId", "fontAssetId"):
            if props.get(field):
                required.add(props[field])
        if layer.kind in {"video", "image"}:
            ref = refs.get(props.get("assetId"))
            if not ref or not ref.media_type.startswith(layer.kind + "/"):
                raise ValueError("remotion_native_media_binding_invalid:" + layer.id)
        if props.get("fontAssetId"):
            fonts.append(
                {
                    "assetId": props["fontAssetId"],
                    "family": "ResFont_" + props["fontAssetId"],
                    "weight": props.get("fontWeight", 400),
                }
            )
        data = layer.model_dump(mode="json", by_alias=True)
        data["properties"] = dict(props)
        if props.get("fontAssetId"):
            data["properties"]["fontFamily"] = "ResFont_" + props["fontAssetId"]
        layers.append(data)
    for asset_id in required:
        ref = refs.get(asset_id)
        binding = asset_files.get(asset_id)
        if not ref or not ref.checksum or not binding:
            raise ValueError("remotion_native_asset_missing:" + asset_id)
        if ref.checksum.lower() != binding["sha256"].lower():
            raise ValueError("remotion_native_asset_checksum_conflict:" + asset_id)
    for track in projection.tracks:
        if track.target_layer_id not in ids:
            raise ValueError("remotion_native_track_target_missing")
    if any(t.kind not in {"hard_cut", "dissolve", "wipe"} for t in projection.transitions):
        raise ValueError("remotion_native_transition_unsupported")
    payload = {
        "schemaVersion": "res.remotion-native-composition.v2",
        "componentLibraryVersion": 2,
        "documentId": document.document_id,
        "documentRevision": document.revision,
        "width": page.width,
        "height": page.height,
        "fps": timeline.frame_rate.numerator / timeline.frame_rate.denominator,
        "durationFrames": timeline.duration_frames,
        "background": page.background,
        "layers": layers,
        "nodes": [n.model_dump(mode="json", by_alias=True) for n in projection.nodes],
        "tracks": [t.model_dump(mode="json", by_alias=True) for t in projection.tracks],
        "transitions": [t.model_dump(mode="json", by_alias=True) for t in projection.transitions],
        "fonts": fonts,
        "assetFiles": {key: asset_files[key] for key in sorted(required)},
        "graphDigestSha256": projection.source_graph_digest_sha256,
        "editorialOperations": document.composition.narrative.get("editorialV2", {}).get("operationBindings", []),
    }
    payload["nativeCompositionDigest"] = digest({k: v for k, v in payload.items() if k != "assetFiles"})
    return payload
