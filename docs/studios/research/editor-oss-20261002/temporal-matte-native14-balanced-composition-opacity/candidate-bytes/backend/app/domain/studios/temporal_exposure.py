"""Keep authored exposure parameters and executable layer bindings consistent."""

from .motion_recipes import TemporalExposureV1


def temporal_spec(operation):
    params = operation["parameters"]
    spec = {
        "startFrame": operation["startFrame"],
        "endFrameExclusive": operation["endFrameExclusive"],
        "samples": params.get("temporalSamples", 8),
        "shutterAngle": params.get("shutterDegrees", 180),
    }
    if params.get("temporalExposure") is not None:
        spec["exposurePolicy"] = TemporalExposureV1.model_validate(params["temporalExposure"]).model_dump(
            mode="json",
            by_alias=True,
        )
    return spec


def validate_temporal_exposures(layers, nodes, operations, tracks):
    by_id = {layer.id: layer for layer in layers}
    by_node = {node.node_id: node for node in nodes}
    by_layer = {node.target_layer_id: node for node in nodes}
    bound = set()
    for operation in operations:
        if operation["technique"] != "velocity_blur":
            continue
        expected = temporal_spec(operation)
        for layer_id in operation["targetLayerIds"]:
            layer = by_id.get(layer_id)
            if (
                layer is None
                or layer.kind not in {"shape", "text", "group"}
                or layer_id in bound
                or layer.properties.get("editorialSceneId") != operation["sceneId"]
            ):
                raise ValueError("motion_recipe_temporal_target_binding_invalid")
            if layer.properties.get("recipeTemporalBlur") != expected:
                raise ValueError("motion_recipe_temporal_lowered_spec_stale")
            if expected["shutterAngle"] == 0 and not expected.get("exposurePolicy"):
                raise ValueError("motion_recipe_temporal_zero_shutter_requires_policy:" + layer_id)
            bound.add(layer_id)
            if expected.get("exposurePolicy"):
                if operation["compilerVersion"] != "res.native-recipes.v4":
                    raise ValueError("motion_recipe_temporal_policy_compiler_required")
                if layer_id not in by_layer:
                    raise ValueError("motion_recipe_temporal_node_binding_required")
                timing = layer.properties.get("editorialTiming")
                if timing and (
                    expected["startFrame"] < timing["startFrame"]
                    or expected["endFrameExclusive"] > timing["startFrame"] + timing["durationFrames"]
                ):
                    raise ValueError("motion_recipe_temporal_target_interval_required")
                # The runtime propagates effective draw times: sampled subtree
                # at subframes, external ancestors/references at center frame.
                descendants, ancestors = {by_layer[layer_id].node_id}, set()
                for _ in nodes:
                    descendants.update(node.node_id for node in nodes if node.parent_node_id in descendants)
                for node_id in descendants:
                    text_layer = by_id[by_node[node_id].target_layer_id]
                    typography = text_layer.properties.get("recipeTypography", {})
                    complete = typography.get("completeFrame")
                    if (typography.get("version") == 2 and expected["shutterAngle"] > 0
                            and expected["startFrame"] < complete < expected["endFrameExclusive"]):
                        type_operation = next((op for op in operations if op["technique"] == "integrated_type"
                                               and text_layer.id in op["targetLayerIds"]), None)
                        if (type_operation is None or complete + 1 + typography["readingHoldFrames"]
                                > type_operation["endFrameExclusive"]):
                            raise ValueError("motion_recipe_temporal_complete_reading_hold_required:" + text_layer.id)
                if any(
                    by_id[by_node[node_id].target_layer_id].properties.get("maskAssetId") for node_id in descendants
                ):
                    raise ValueError("motion_recipe_temporal_legacy_mask_asset_pending")
                current = by_layer[layer_id]
                while current.parent_node_id:
                    if current.parent_node_id in ancestors:
                        raise ValueError("motion_recipe_temporal_parent_cycle")
                    ancestors.add(current.parent_node_id)
                    if current.parent_node_id not in by_node:
                        raise ValueError("motion_recipe_temporal_parent_missing")
                    current = by_node[current.parent_node_id]
    if any(layer.properties.get("recipeTemporalBlur") and layer.id not in bound for layer in layers):
        raise ValueError("motion_recipe_temporal_operation_binding_required")
    for layer_id in bound:
        spec = by_id[layer_id].properties["recipeTemporalBlur"]
        current = by_layer.get(layer_id)
        visited = set()
        while current and current.parent_node_id:
            if current.parent_node_id in visited:
                raise ValueError("motion_recipe_temporal_parent_cycle")
            visited.add(current.parent_node_id)
            current = by_node.get(current.parent_node_id)
            if current is None:
                raise ValueError("motion_recipe_temporal_parent_missing")
            parent_spec = by_id[current.target_layer_id].properties.get("recipeTemporalBlur")
            if (parent_spec and (spec.get("exposurePolicy") or parent_spec.get("exposurePolicy"))
                    and max(spec["startFrame"], parent_spec["startFrame"])
                    < min(spec["endFrameExclusive"], parent_spec["endFrameExclusive"])):
                raise ValueError("motion_recipe_temporal_nested_target_pending:" + layer_id)
