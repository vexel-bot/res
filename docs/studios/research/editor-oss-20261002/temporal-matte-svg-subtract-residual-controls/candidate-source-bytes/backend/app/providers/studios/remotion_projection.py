"""Project canonical layers into the independent native Remotion runtime."""

from ...domain.studios.asset_matte import validate_mattes
from ...domain.studios.contextual_editing import digest
from ...domain.studios.contextual_editing_v2 import EditorialDepthTreatmentV2, EditorialShadowV2
from ...domain.studios.motion_recipes import MotionRecipeV1
from ...domain.studios.native_scenes import NativeSceneComponentV1
from ...domain.studios.temporal_exposure import validate_temporal_exposures
from ...domain.studios.typography import TypographyLayoutPolicyV1, layout_policy, validate_segmentation
from ...services.studios.native_motion_recipes import supported_recipe_operation


def _validate_typography_operations(document, operations):
    layers = {layer.id: layer for page in document.composition.pages for layer in page.layers}
    expected_v2_targets = set()
    expected_layout_targets = set()
    for operation in operations:
        if operation["technique"] != "integrated_type" or operation["compilerVersion"] not in {
            "res.native-recipes.v2", "res.native-recipes.v3", "res.native-recipes.v4",
        }:
            continue
        parameters = operation["parameters"]
        targets = operation.get("typographyTargets", {})
        if set(targets) != set(operation["targetLayerIds"]):
            raise ValueError("typography_operation_targets_stale")
        measured = operation["compilerVersion"] in {"res.native-recipes.v3", "res.native-recipes.v4"}
        layouts = operation.get("typographyLayouts", {})
        if (measured and set(layouts) != set(targets)) or (not measured and layouts):
            raise ValueError("typography_layout_targets_stale")
        for layer_id, payload in targets.items():
            layer = layers.get(layer_id)
            if layer is None or layer.kind != "text" or layer_id in expected_v2_targets:
                raise ValueError("typography_operation_target_invalid")
            segmentation = validate_segmentation(payload, layer.properties["text"], parameters["textUnit"])
            if measured:
                policy = TypographyLayoutPolicyV1.model_validate(layouts[layer_id])
                page = next(page for page in document.composition.pages if layer in page.layers)
                if (policy != layout_policy(page.width) or layer.properties.get("recipeTextLayout") != layouts[layer_id]
                        or len(segmentation.units) > policy.max_layout_units):
                    raise ValueError("typography_layout_policy_stale")
                expected_layout_targets.add(layer_id)
            reveal = (segmentation.animated_count - 1) * parameters["staggerFrames"] + 10
            expected_spec = {
                "version": 2, "segmentation": segmentation.model_dump(mode="json", by_alias=True),
                "startFrame": operation["startFrame"], "unit": parameters["textUnit"],
                "staggerFrames": parameters["staggerFrames"], "entranceFrames": 10,
                "readingHoldFrames": parameters["readingHoldFrames"],
                "completeFrame": operation["startFrame"] + reveal,
            }
            if layer.properties.get("recipeTypography") != expected_spec:
                raise ValueError("typography_lowered_spec_stale")
            if expected_spec["completeFrame"] + expected_spec["readingHoldFrames"] > operation["endFrameExclusive"]:
                raise ValueError("motion_recipe_complete_reading_hold_required")
            expected_v2_targets.add(layer_id)
    for layer in layers.values():
        spec = layer.properties.get("recipeTypography")
        if spec and spec.get("version") == 2 and layer.id not in expected_v2_targets:
            raise ValueError("typography_operation_binding_required")
        if layer.properties.get("recipeTextLayout") and layer.id not in expected_layout_targets:
            raise ValueError("typography_layout_operation_binding_required")


def compile_remotion_composition(document, projection, asset_files):
    editorial = document.composition.narrative.get("editorialV2", {})
    recipes = editorial.get("motionRecipes", [])
    operations = editorial.get("nativeRecipeOperations", [])
    for recipe in recipes:
        try:
            MotionRecipeV1.model_validate({k: v for k, v in recipe.items() if k != "sceneId"})
        except (ValueError, AttributeError) as error:
            raise ValueError("motion_recipe_invalid_native_contract") from error
    if (recipes or operations) and (
        len(operations) != len(recipes)
        or {(r["sceneId"], r["id"], r["technique"]) for r in recipes}
        != {(r["sceneId"], r["id"], r["technique"]) for r in operations}
        or any(not supported_recipe_operation(r) for r in operations)
    ):
        raise ValueError("motion_recipe_engine_not_qualified")
    operation_by_id = {(op["sceneId"], op["id"]): op for op in operations}
    for recipe in recipes:
        operation = operation_by_id[(recipe["sceneId"], recipe["id"])]
        if recipe["parameters"] != operation["parameters"] or recipe["version"] != operation["version"]:
            raise ValueError("motion_recipe_lowered_parameters_stale")
        if recipe["technique"] == "asset_matte":
            layer_names = {layer.id: layer.name for page in document.composition.pages for layer in page.layers}
            if [layer_names.get(key) for key in operation["targetLayerIds"]] != recipe["targetIds"]:
                raise ValueError("motion_recipe_asset_matte_target_binding_stale")
        if recipe["technique"] == "velocity_blur":
            layer_names = {layer.id: layer.name for page in document.composition.pages for layer in page.layers}
            if [layer_names.get(key) for key in operation["targetLayerIds"]] != recipe["targetIds"]:
                raise ValueError("motion_recipe_temporal_target_binding_stale")
    _validate_typography_operations(document, operations)
    validate_temporal_exposures(
        [layer for page in document.composition.pages for layer in page.layers],
        projection.nodes, operations, projection.tracks,
    )
    validate_mattes(
        [layer for page in document.composition.pages for layer in page.layers], projection.nodes, operations,
        projection.tracks, projection.transitions,
    )
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
    animated_blur_targets = {track.target_layer_id for track in projection.tracks
                             if track.property_path == "filters.blurPx"}
    if len(ids) != len(page.layers):
        raise ValueError("remotion_native_duplicate_layer")
    for layer in page.layers:
        if layer.kind not in {"group", "video", "image", "text", "shape"}:
            raise ValueError("remotion_native_layer_unsupported:" + layer.kind)
        props = layer.properties
        spatial_parameters = {}
        for key, model, diagnostic in [
            ("editorialShadow", EditorialShadowV2, "remotion_native_shadow_invalid:"),
            ("editorialDepth", EditorialDepthTreatmentV2, "remotion_native_depth_invalid:"),
        ]:
            if props.get(key) is not None:
                try:
                    spatial_parameters[key] = model.model_validate(props[key]).model_dump(mode="json", by_alias=True)
                except ValueError as error:
                    raise ValueError(diagnostic + layer.id) from error
        if (layer.id in animated_blur_targets and spatial_parameters.get("editorialDepth", {}).get("blurPx", 0)):
            raise ValueError("remotion_native_blur_authoring_conflict:" + layer.id)
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
        if props.get("matteSourceOnly"):
            binding = asset_files.get(props.get("assetId"))
            ref = refs.get(props.get("assetId"))
            if (binding and binding["mime"] != "image/png") or (ref and ref.media_type != "image/png"):
                raise ValueError("motion_recipe_asset_matte_png_required:" + layer.id)
        data = layer.model_dump(mode="json", by_alias=True)
        data["properties"] = dict(props)
        data["properties"].update(spatial_parameters)
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
        "componentLibraryVersion": (7 if any(op["parameters"].get("temporalExposure") for op in operations)
                                    else 6 if any(op["compilerVersion"] == "res.native-recipes.v4" for op in operations)
                                    else 5 if any(op["compilerVersion"] == "res.native-recipes.v3" for op in operations)
                                    else 4 if any(op["compilerVersion"] == "res.native-recipes.v2" for op in operations)
                                    else 3 if operations else 2),
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
        **({"nativeRecipeOperations": operations} if operations else {}),
    }
    payload["nativeCompositionDigest"] = digest({k: v for k, v in payload.items() if k != "assetFiles"})
    return payload
