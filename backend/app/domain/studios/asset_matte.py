"""Bind an image matte to canonical layer identities, transform space and time."""

from .motion_recipes import AssetMatteV1

MATTE_COMPILER_VERSION = "res.native-recipes.v4"


def matte_spec(source, operation):
    parameters = AssetMatteV1.model_validate(operation["parameters"]["assetMatte"])
    return {
        **parameters.model_dump(mode="json", by_alias=True),
        "sourceLayerId": source.id,
        "assetId": source.properties.get("assetId"),
        "objectFit": source.properties.get("objectFit", "contain"),
        "startFrame": operation["startFrame"],
        "endFrameExclusive": operation["endFrameExclusive"],
    }


def validate_mattes(layers, nodes, operations, tracks, transitions=()):
    by_id = {layer.id: layer for layer in layers}
    parents = {node.target_layer_id: node.parent_node_id for node in nodes}
    node_layers = {node.node_id: node.target_layer_id for node in nodes}
    bound_targets, bound_sources = set(), set()
    matte_ops = [op for op in operations if op["technique"] == "asset_matte"]
    if sum(len(op["targetLayerIds"]) for op in matte_ops) > 8:
        raise ValueError("motion_recipe_asset_matte_relation_limit")
    for operation in matte_ops:
        if operation["compilerVersion"] != MATTE_COMPILER_VERSION:
            raise ValueError("motion_recipe_asset_matte_compiler_required")
        source_id = operation.get("matteSourceLayerId")
        source = by_id.get(source_id)
        if source is None or source.kind != "image" or not source.properties.get("assetId"):
            raise ValueError("motion_recipe_asset_matte_image_source_required")
        if (
            source.name != operation["parameters"]["assetMatte"]["sourceTargetId"]
            or source.properties.get("editorialSceneId") != operation["sceneId"]
        ):
            raise ValueError("motion_recipe_asset_matte_source_binding_stale")
        spec = matte_spec(source, operation)
        for target_id in operation["targetLayerIds"]:
            target = by_id.get(target_id)
            if target is None:
                raise ValueError("motion_recipe_asset_matte_target_missing")
            if target.properties.get("editorialSceneId") != operation["sceneId"]:
                raise ValueError("motion_recipe_asset_matte_target_scene_stale")
            if target_id == source_id or target_id in bound_targets or target.width * target.height > 4_194_304:
                raise ValueError("motion_recipe_asset_matte_target_conflict_or_limit")
            if target.properties.get("recipeAssetMatte") != spec:
                raise ValueError("motion_recipe_asset_matte_lowered_spec_stale")
            if target.properties.get("maskAssetId") or target.properties.get("recipeOcclusion"):
                raise ValueError("motion_recipe_asset_matte_mask_author_conflict")
            bound_targets.add(target_id)
            # Only canonical 2D transforms are inputs; unsupported source paint
            # stacks must not disappear silently while using the raw PNG.
            for original in [source, target]:
                current, seen = original, set()
                while current:
                    if current.id in seen:
                        raise ValueError("motion_recipe_asset_matte_parent_cycle")
                    seen.add(current.id)
                    if current.id not in parents:
                        raise ValueError("motion_recipe_asset_matte_node_binding_required")
                    props = current.properties
                    timing = props.get("editorialTiming")
                    if timing and (
                        spec["startFrame"] < timing["startFrame"]
                        or spec["endFrameExclusive"] > timing["startFrame"] + timing["durationFrames"]
                    ):
                        raise ValueError("motion_recipe_asset_matte_source_interval_required")
                    if props.get("nativeComponent"):
                        raise ValueError("motion_recipe_asset_matte_legacy_transform_pending")
                    if original.id == source_id and (
                        props.get("recipeAssetMatte")
                        or props.get("maskAssetId")
                        or props.get("recipeOcclusion")
                        or props.get("recipeTemporalBlur")
                        or props.get("editorialShadow")
                        or props.get("editorialEffects")
                        or props.get("editorialBorder", {}).get("width")
                        or props.get("editorialBlendMode", "normal") != "normal"
                        or props.get("editorialDepth", {}).get("blurPx", 0)
                        or (timing and timing.get("reveal", "none") != "none")
                        or any(
                            t.target_layer_id == current.id
                            and (
                                getattr(t, "property", None) == "blur_px"
                                or getattr(t, "property_path", None) == "filters.blurPx"
                            )
                            for t in tracks
                        )
                        or any(current.id in {t.from_layer_id, t.to_layer_id} for t in transitions)
                    ):
                        raise ValueError("motion_recipe_asset_matte_source_paint_stack_pending")
                    parent = parents.get(current.id)
                    if parent and parent not in node_layers:
                        raise ValueError("motion_recipe_asset_matte_parent_missing")
                    current = by_id.get(node_layers.get(parent)) if parent else None
            bound_sources.add(source_id)
    for layer in layers:
        if layer.properties.get("recipeAssetMatte") and layer.id not in bound_targets:
            raise ValueError("motion_recipe_asset_matte_operation_binding_required")
        if bool(layer.properties.get("matteSourceOnly")) != (layer.id in bound_sources):
            raise ValueError("motion_recipe_asset_matte_source_role_stale")
