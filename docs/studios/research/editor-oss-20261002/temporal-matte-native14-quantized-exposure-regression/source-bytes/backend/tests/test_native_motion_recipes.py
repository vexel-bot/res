"""Recipe lowering must change execution, with no duplicate property author."""

import pytest
from pydantic import ValidationError
from test_remotion_native import native_direction, native_document

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.providers.studios.remotion_projection import compile_remotion_composition


def recipe(technique="motion_choreography", **parameters):
    return {
        "id": "entry",
        "technique": technique,
        "targetIds": ["hero"],
        "startFrame": 0,
        "endFrameExclusive": 15,
        "intent": "Arrive and settle",
        "continuityAnchor": "Same title",
        "parameters": parameters,
        "verification": ["Stable title at the end"],
    }


def direction_with(recipes):
    payload = native_direction().model_dump(mode="json", by_alias=True)
    payload["scenes"][0]["nativeComponents"] = []
    payload["scenes"][0]["motionRecipes"] = recipes
    return ContextualPlanRequestV2.model_validate(payload)


def choreography(value=64):
    return recipe(
        pivot=[0, 1],
        tracks=[
            {
                "targetId": "hero",
                "property": "y",
                "keyframes": [
                    {"frame": 0, "value": value, "curve": [0.22, 0.75, 0.25, 1]},
                    {"frame": 8, "value": 0},
                    {"frame": 14, "value": 0},
                ],
            }
        ],
    )


def test_lowered_tracks_pivot_hash_and_no_double_transform():
    doc, projection = native_document(direction_with([choreography()]))
    manifest = compile_remotion_composition(doc, projection, {})
    layer = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
    node = next(node for node in manifest["nodes"] if node["targetLayerId"] == layer["id"])
    assert (node["transformOriginX"], node["transformOriginY"]) == (0, 1)
    tracks = [t for t in manifest["tracks"] if t["targetLayerId"] == layer["id"]]
    assert len(tracks) == 1
    assert tracks[0]["propertyPath"] == "position.y"
    assert tracks[0]["keyframes"][-1]["value"] == 0
    second, p2 = native_document(direction_with([choreography(80)]))
    assert (
        manifest["nativeCompositionDigest"] != compile_remotion_composition(second, p2, {})["nativeCompositionDigest"]
    )
    assert doc.composition.narrative["editorialV2"]["nativeRecipeOperations"][0]["qualification"] == "implemented"


def test_conflicting_recipe_authors_rejected():
    two = choreography()
    two["id"] = "second"
    with pytest.raises(ValueError, match="property_conflict"):
        native_document(direction_with([choreography(), two]))


def test_recipe_parameters_cannot_diverge_from_lowered_execution():
    doc, projection = native_document(direction_with([choreography()]))
    recipes = doc.composition.narrative["editorialV2"]["motionRecipes"]
    recipes[0]["parameters"]["tracks"][0]["keyframes"][0]["value"] = 999
    with pytest.raises(ValueError, match="lowered_parameters_stale"):
        compile_remotion_composition(doc, projection, {})


def test_missing_capability_is_not_decorative_fallback():
    with pytest.raises(ValueError, match="capability_pending:depth_camera"):
        native_document(direction_with([recipe("depth_camera")]))


def test_typography_requires_complete_reading_hold():
    with pytest.raises(ValueError, match="complete_reading_hold"):
        native_document(direction_with([recipe("integrated_type", readingHoldFrames=14)]))


def test_legacy_shape_unchanged_and_study_needs_direction():
    legacy = native_direction().model_dump(mode="json", by_alias=True)
    assert "visualStudyLanguage" not in legacy
    legacy["visualStudyLanguage"] = "motion_graphics"
    with pytest.raises(ValidationError, match="art_direction"):
        ContextualPlanRequestV2.model_validate(legacy)


def test_sequential_heroes_do_not_weaken_simultaneous_hierarchy_rule():
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene["durationFrames"] = 30
    scene["nativeComponents"] = []
    scene["elements"] = [
        {
            "id": name,
            "kind": "shape",
            "purpose": "One focus per interval",
            "x": 20,
            "y": 20,
            "width": 100,
            "height": 100,
            "visualRole": "hero",
            "startFrame": start,
            "durationFrames": duration,
        }
        for name, start, duration in [("editing", 0, 15), ("result", 15, 15)]
    ]
    ContextualPlanRequestV2.model_validate(raw)
    scene["elements"][1].update(startFrame=14, durationFrames=16)
    with pytest.raises(ValidationError, match="multiple_heroes"):
        ContextualPlanRequestV2.model_validate(raw)


def test_graphics_readiness_does_not_weaken_product_gate():
    from app.services.studios.visual_quality_program import material_readiness

    payload = {
        "brief": {"objective": "Organize"},
        "composition": {
            "narrative": {
                "editorialV2": {
                    "artDirection": {"visualSystem": "Original graphics"},
                    "visualStudy": {"language": "motion_graphics"},
                }
            }
        },
    }
    assert material_readiness(payload)["status"] == "ready"
    payload["composition"]["narrative"]["editorialV2"]["visualStudy"]["language"] = "interface_capture"
    assert "real_test_interface_capture_required" in material_readiness(payload)["blockers"]
    payload.pop("composition")
    assert "two_distinct_action_sources_required" in material_readiness(payload)["blockers"]


def test_real_pixels_mask_stroke_parenting_and_temporal_blur(tmp_path):
    import subprocess

    from app.domain.studios.contracts import VideoRenderRequestV1
    from app.providers.studios.remotion_render import RemotionNativeGraphicsProvider

    raw = native_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene["durationFrames"] = 30
    scene["nativeComponents"] = []
    scene["background"] = "#000000"

    def element(key, kind, x, y, width, height, **extra):
        return {
            "id": key,
            "kind": kind,
            "purpose": "Pixel-level execution proof",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "durationFrames": 30,
            "visualRole": "support",
            **extra,
        }

    scene["elements"] = [
        element("hero", "shape", 30, 20, 24, 24, fill="#ffffff"),
        element("masked", "shape", 40, 110, 100, 40, fill="#00ff00"),
        element("cover", "shape", -20, 100, 20, 70, fill="#000000", zIndex=9),
        element(
            "stroke",
            "path",
            40,
            185,
            100,
            10,
            color="#ffffff",
            strokeWidth=6,
            points=[{"x": 0, "y": 5}, {"x": 100, "y": 5}],
        ),
        element("rig", "group", 20, 250, 100, 50),
        element("child", "shape", 10, 0, 20, 20, fill="#ff0000", parentId="rig"),
    ]

    def track(target, prop, values):
        return {
            "targetId": target,
            "property": prop,
            "keyframes": [{"frame": frame, "value": value, "curve": [0, 0, 1, 1]} for frame, value in values],
        }

    def operation(key, technique, targets, parameters):
        return {
            "id": key,
            "technique": technique,
            "targetIds": targets,
            "startFrame": 0,
            "endFrameExclusive": 30,
            "intent": "Prove actual output",
            "continuityAnchor": "Same shape",
            "parameters": parameters,
            "verification": ["Correct pixels"],
        }

    scene["motionRecipes"] = [
        operation(
            "move", "motion_choreography", ["hero"], {"tracks": [track("hero", "x", [(0, 0), (8, 150), (29, 150)])]}
        ),
        operation("exposure", "velocity_blur", ["hero"], {"temporalSamples": 4, "shutterDegrees": 180}),
        operation(
            "cover-move",
            "motion_choreography",
            ["cover"],
            {"tracks": [track("cover", "x", [(0, 0), (14, 180), (29, 180)])]},
        ),
        operation("matte", "motivated_occlusion", ["masked"], {"occluderTargetId": "cover"}),
        operation(
            "draw",
            "vector_reveal",
            ["stroke"],
            {"tracks": [track("stroke", "stroke_progress", [(0, 0), (14, 1), (29, 1)])]},
        ),
        operation(
            "parent-move", "motion_choreography", ["rig"], {"tracks": [track("rig", "x", [(0, 0), (14, 60), (29, 60)])]}
        ),
        operation("local", "layer_rig", ["child"], {"parentTargetId": "rig"}),
    ]
    doc, projection = native_document(ContextualPlanRequestV2.model_validate(raw))
    request = VideoRenderRequestV1(
        workspace_id=doc.workspace_id,
        document_id=doc.document_id,
        document_revision=doc.revision,
        document_version=doc.version,
        page_ids=["page"],
        correlation_id="recipe-pixel-test",
        output={"width": 320, "height": 320, "fps": 30, "audioCodec": "none"},
    )
    destination = tmp_path / "recipes.mp4"
    result = RemotionNativeGraphicsProvider("node", "ffmpeg", 180).render(
        doc, request, {}, destination, lambda _: None, lambda: False, motion_projection=projection, automatic_draft=True
    )
    pixels = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-i", str(destination), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    )

    def pixel(frame, x, y):
        offset = (frame * 320 * 320 + y * 320 + x) * 3
        return tuple(pixels[offset : offset + 3])

    assert pixel(0, 90, 130)[1] < 20  # Masked, although its authored opacity is 1.
    assert pixel(29, 90, 130)[1] > 200
    assert pixel(29, 90, 190)[0] > 200  # Actual drawn stroke.
    assert pixel(29, 95, 260)[0] > 180  # 20 base + 10 local + 60 parent, once.
    assert pixel(29, 155, 260)[0] < 20  # No duplicated parent displacement.
    moving = [pixel(4, x, 30)[0] for x in range(70, 150)]
    paused = [pixel(29, x, 30)[0] for x in range(150, 240)]
    assert sum(20 < value < 220 for value in moving) > sum(20 < value < 220 for value in paused)
    assert result.frames_rendered == 30
    assert len(result.renderer_checks["geometrySamples"]) == 30
