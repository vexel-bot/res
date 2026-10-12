"""Recipe lowering must change execution, with no duplicate property author."""

import pytest
from pydantic import ValidationError
from test_remotion_native import native_direction, native_document

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2


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




def test_conflicting_recipe_authors_rejected():
    two = choreography()
    two["id"] = "second"
    with pytest.raises(ValueError, match="property_conflict"):
        native_document(direction_with([choreography(), two]))




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
