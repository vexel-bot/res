"""Lower registered recipes into the canonical graph before composition hashes.

Coordinates are local to an explicit parent. Conflicting property authors are
rejected rather than summed. These capabilities are implemented, not visually
qualified. Unsupported recipes never fall back to decorative animation.
"""

from ...domain.studios.asset_matte import matte_spec, validate_mattes
from ...domain.studios.motion import PROPERTY_UNITS, MotionKeyframeV1, MotionTrackV1
from ...domain.studios.typography import layout_policy, segment_text

RECIPE_COMPILER_VERSION = "res.native-recipes.v4"
SUPPORTED_RECIPE_COMPILER_VERSIONS = {
    "res.native-recipes.v1", "res.native-recipes.v2", "res.native-recipes.v3", RECIPE_COMPILER_VERSION,
}
SUPPORTED_RECIPES = {
    "motion_choreography",
    "layer_rig",
    "integrated_type",
    "motivated_occlusion",
    "vector_reveal",
    "velocity_blur",
    "action_sound_cut",
    "asset_matte",
}
PROPERTIES = {
    "x": "position_x",
    "y": "position_y",
    "rotation": "rotation_degrees",
    "scale_x": "scale_x",
    "scale_y": "scale_y",
    "opacity": "opacity",
}


def supported_recipe_operation(operation):
    return (operation.get("compilerVersion") in SUPPORTED_RECIPE_COMPILER_VERSIONS
            and operation.get("technique") in SUPPORTED_RECIPES)


def lower_native_recipes(page, nodes, tracks, scenes, target_id):
    by_id = {layer.id: layer for layer in page.layers}
    node_by_layer = {node.target_layer_id: node for node in nodes}
    cursor = 0
    operations = []
    for scene in scenes:
        if scene.entrance != "cut":
            cursor -= scene.transition_frames
        elements = {element.id: element for element in scene.elements}
        for recipe in scene.motion_recipes:
            if recipe.technique not in SUPPORTED_RECIPES:
                raise ValueError("motion_recipe_capability_pending:" + recipe.technique)
            p = recipe.parameters
            if p.mask_asset_id:
                raise ValueError("motion_recipe_asset_matte_pending")
            targets = [by_id[target_id(scene.id, key)] for key in recipe.target_ids]
            if any(elements[key].repeat_count != 1 for key in recipe.target_ids):
                raise ValueError("motion_recipe_repeated_target_unsupported")
            operation = {
                "id": recipe.id,
                "sceneId": scene.id,
                "technique": recipe.technique,
                "version": 1,
                "compilerVersion": RECIPE_COMPILER_VERSION,
                "startFrame": cursor + recipe.start_frame,
                "endFrameExclusive": cursor + recipe.end_frame_exclusive,
                "targetLayerIds": [layer.id for layer in targets],
                "parameters": p.model_dump(mode="json", by_alias=True),
                "qualification": "implemented",
                "knowledgeTechniqueId": (
                    "res.asset_matte" if recipe.technique == "asset_matte" else "alight." + recipe.technique
                ),
                "evidenceClassification": "documentation_and_editorial_inference",
            }
            if recipe.technique == "asset_matte":
                source = by_id[target_id(scene.id, p.asset_matte.source_target_id)]
                if elements[p.asset_matte.source_target_id].repeat_count != 1:
                    raise ValueError("motion_recipe_asset_matte_repeated_source_unsupported")
                operation["matteSourceLayerId"] = source.id
                source.properties["matteSourceOnly"] = True
            for layer in targets:
                node = node_by_layer[layer.id]
                if recipe.technique == "motion_choreography":
                    node.transform_origin_x, node.transform_origin_y = p.pivot
                elif recipe.technique == "asset_matte":
                    if layer.properties.get("recipeAssetMatte"):
                        raise ValueError("motion_recipe_asset_matte_target_conflict_or_limit")
                    layer.properties["recipeAssetMatte"] = matte_spec(source, operation)
                elif recipe.technique == "layer_rig":
                    parent = by_id[target_id(scene.id, p.parent_target_id)]
                    if parent.kind != "group":
                        raise ValueError("motion_recipe_parent_group_required")
                    # Changing a coordinate space implicitly would move children.
                    if elements[layer.name].parent_id != p.parent_target_id:
                        raise ValueError("motion_recipe_explicit_local_parent_required")
                    node.parent_node_id = node_by_layer[parent.id].node_id
                elif recipe.technique == "integrated_type":
                    if (layer.kind != "text" or layer.properties.get("nativeComponent")
                            or layer.properties.get("recipeTypography")):
                        raise ValueError("motion_recipe_typography_target_conflict")
                    element = elements[layer.name]
                    if (recipe.start_frame < element.start_frame or
                            recipe.end_frame_exclusive > element.start_frame + element.duration_frames):
                        raise ValueError("motion_recipe_reading_hold_target_interval_required")
                    text = layer.properties["text"]
                    segmentation = segment_text(text, p.text_unit)
                    policy = layout_policy(page.width)
                    if len(segmentation.units) > policy.max_layout_units:
                        raise ValueError("motion_recipe_typography_layout_unit_limit:" + layer.id)
                    layer.properties["recipeTextLayout"] = policy.model_dump(mode="json", by_alias=True)
                    operation.setdefault("typographyLayouts", {})[layer.id] = layer.properties["recipeTextLayout"]
                    entrance = 10
                    reveal = (segmentation.animated_count - 1) * p.stagger_frames + entrance
                    if reveal + p.reading_hold_frames > recipe.end_frame_exclusive - recipe.start_frame:
                        raise ValueError("motion_recipe_complete_reading_hold_required")
                    layer.properties["recipeTypography"] = {
                        "version": 2,
                        "segmentation": segmentation.model_dump(mode="json", by_alias=True),
                        "startFrame": cursor + recipe.start_frame,
                        "unit": p.text_unit,
                        "staggerFrames": p.stagger_frames,
                        "entranceFrames": entrance,
                        "readingHoldFrames": p.reading_hold_frames,
                        "completeFrame": cursor + recipe.start_frame + reveal,
                    }
                    operation.setdefault("typographyTargets", {})[layer.id] = segmentation.model_dump(
                        mode="json", by_alias=True,
                    )
                elif recipe.technique == "motivated_occlusion":
                    occluder = by_id[target_id(scene.id, p.occluder_target_id)]
                    if (
                        occluder.kind != "shape"
                        or occluder.properties.get("shape") == "ellipse"
                        or occluder.properties.get("editorialPath")
                        or occluder.rotation
                        or occluder.z_index <= layer.z_index
                        or node_by_layer[occluder.id].parent_node_id != node.parent_node_id
                    ):
                        raise ValueError("motion_recipe_rectangular_sibling_occluder_required")
                    if any(
                        t.target_layer_id == occluder.id
                        and t.property
                        in {
                            "rotation_degrees",
                            "scale_x",
                            "scale_y",
                        }
                        for t in tracks
                    ):
                        raise ValueError("motion_recipe_occluder_transform_unsupported")
                    layer.properties["recipeOcclusion"] = {
                        "occluderLayerId": occluder.id,
                        "startFrame": cursor + recipe.start_frame,
                        "endFrameExclusive": cursor + recipe.end_frame_exclusive,
                    }
                elif recipe.technique == "vector_reveal":
                    if not layer.properties.get("editorialPath"):
                        raise ValueError("motion_recipe_vector_path_required")
                elif recipe.technique == "velocity_blur":
                    if layer.kind not in {"shape", "text", "group"}:
                        raise ValueError("motion_recipe_graphic_blur_only")
                    layer.properties["recipeTemporalBlur"] = {
                        "startFrame": cursor + recipe.start_frame,
                        "endFrameExclusive": cursor + recipe.end_frame_exclusive,
                        "samples": p.temporal_samples,
                        "shutterAngle": p.shutter_degrees,
                    }
                    if p.temporal_exposure:
                        layer.properties["recipeTemporalBlur"]["exposurePolicy"] = p.temporal_exposure.model_dump(
                            mode="json", by_alias=True,
                        )
            for track in p.tracks:
                if track.target_id not in recipe.target_ids:
                    raise ValueError("motion_recipe_track_requires_declared_target")
                layer = by_id[target_id(scene.id, track.target_id)]
                keys = [
                    {
                        "frame": cursor + recipe.start_frame + key.frame,
                        "value": key.value,
                        "easing": "cubic_bezier",
                        "cubicBezier": list(key.curve),
                    }
                    for key in track.keyframes
                ]
                if track.property == "stroke_progress" and layer.properties.get("editorialPath"):
                    if layer.properties.get("recipeStroke"):
                        raise ValueError("motion_recipe_property_conflict:stroke_progress")
                    layer.properties["recipeStroke"] = keys
                    continue
                property_name = PROPERTIES.get(track.property)
                if not property_name:
                    raise ValueError("motion_recipe_property_pending:" + track.property)
                # The compiler's inert opacity binding may be replaced; authored
                # animation, camera and composition bindings may not.
                tracks[:] = [
                    t for t in tracks if not (t.target_layer_id == layer.id and t.track_id.endswith("-static"))
                ]
                if any(t.target_layer_id == layer.id and t.property == property_name for t in tracks):
                    raise ValueError("motion_recipe_property_conflict:" + property_name)
                tracks.append(
                    MotionTrackV1(
                        track_id=layer.id + "-recipe-" + track.property,
                        target_layer_id=layer.id,
                        property=property_name,
                        unit=PROPERTY_UNITS[property_name],
                        keyframes=[MotionKeyframeV1.model_validate(key) for key in keys],
                    )
                )
            operations.append(operation)
        cursor += scene.duration_frames
    # Validate the final graph, including tracks authored by other recipes.
    for layer in page.layers:
        p = layer.properties
        occlusion = p.get("recipeOcclusion")
        if occlusion:
            cover_id = occlusion["occluderLayerId"]
            cover_tracks = [t for t in tracks if t.target_layer_id == cover_id]
            moving = [
                t
                for t in cover_tracks
                if t.property in {"position_x", "position_y"} and t.keyframes[0].value != t.keyframes[-1].value
            ]
            if len(moving) != 1 or moving[0].keyframes[-1].value < moving[0].keyframes[0].value:
                raise ValueError("motion_recipe_forward_axis_occlusion_required")
            if layer.rotation or any(
                t.target_layer_id in {cover_id, layer.id} and t.property in {"rotation_degrees", "scale_x", "scale_y"}
                for t in tracks
            ):
                raise ValueError("motion_recipe_occlusion_transform_pending")
            occlusion["axis"] = "horizontal" if moving[0].property == "position_x" else "vertical"
        if p.get("recipeTemporalBlur"):
            descendants = {node_by_layer[layer.id].node_id}
            for _ in nodes:
                descendants.update(n.node_id for n in nodes if n.parent_node_id in descendants)
            if any(
                by_id[n.target_layer_id].kind in {"video", "image"}
                or (n.target_layer_id != layer.id and by_id[n.target_layer_id].properties.get("recipeTemporalBlur")
                    and not (p["recipeTemporalBlur"].get("exposurePolicy")
                             or by_id[n.target_layer_id].properties["recipeTemporalBlur"].get("exposurePolicy")))
                for n in nodes
                if n.node_id in descendants
            ):
                raise ValueError("motion_recipe_graphic_blur_descendants_required")
    validate_mattes(page.layers, nodes, operations, tracks)
    from ...domain.studios.temporal_exposure import validate_temporal_exposures

    validate_temporal_exposures(page.layers, nodes, operations, tracks)
    return operations
