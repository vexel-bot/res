"""Canonical image mattes: identity, interval, ownership and compatibility."""

import copy

import pytest
from test_native_motion_recipes import recipe
from test_remotion_native import native_direction, native_document

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.motion_recipes import MotionRecipeV1, RecipeParametersV1


@pytest.fixture(autouse=True)
def clean_database():
    yield


def matte_direction(asset="mask", mode="alpha", invert=False):
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene["nativeComponents"] = []
    scene["background"] = "#000000"
    scene["elements"] = [
        {
            "id": "target-rig",
            "kind": "group",
            "purpose": "Target parent",
            "x": 20,
            "y": 20,
            "width": 280,
            "height": 280,
            "durationFrames": 15,
            "originX": 0,
            "originY": 0,
            "depthTreatment": {"opacity": 0.8}, "borderWidth": 4, "borderColor": "#000000",
        },
        {
            "id": "hero",
            "kind": "shape",
            "purpose": "Actual masked graphic",
            "x": 0,
            "y": 0,
            "width": 280,
            "height": 280,
            "parentId": "target-rig",
            "durationFrames": 15,
            "visualRole": "hero",
            "fill": "#ffffff",
            "radius": 0,
        },
        {
            "id": "mask-rig",
            "kind": "group",
            "purpose": "Independent mask coordinate space",
            "x": 80,
            "y": 80,
            "width": 128,
            "height": 128,
            "durationFrames": 15,
            "originX": 0,
            "originY": 0,
            "depthTreatment": {"opacity": 0.2},
        },
        {
            "id": "matte",
            "kind": "image",
            "purpose": "Original arbitrary matte asset",
            "x": 10,
            "y": 0,
            "width": 128,
            "height": 128,
            "assetId": asset,
            "parentId": "mask-rig",
            "durationFrames": 15,
            "objectFit": "contain",
            "depthTreatment": {"opacity": 0.5},
        },
    ]
    spec = recipe("asset_matte", assetMatte={"sourceTargetId": "matte", "mode": mode, "invert": invert})
    spec.update(startFrame=2, endFrameExclusive=13)
    scene["motionRecipes"] = [spec]
    for target, values in [
        ("mask-rig", [("x", 0, 80), ("rotation", 0, 90), ("scale_x", 1, 1.2), ("scale_y", 1, 1.2)]),
        ("target-rig", [("y", 0, 10), ("rotation", 0, -5)]),
    ]:
        tracks = [
            {
                "targetId": target,
                "property": prop,
                "keyframes": [
                    {"frame": 0, "value": first, "curve": [0, 0, 1, 1]},
                    {"frame": 7, "value": last, "curve": [0, 0, 1, 1]},
                    {"frame": 14, "value": last},
                ],
            }
            for prop, first, last in values
        ]
        move = recipe("motion_choreography", tracks=tracks, pivot=[0, 0])
        move.update(id=target + "-move", targetIds=[target])
        scene["motionRecipes"].append(move)
    return ContextualPlanRequestV2.model_validate(raw)


def compiled():
    return native_document(
        matte_direction(), [{"id": "mask", "mediaType": "image/png", "checksum": "a" * 64, "rightsStatus": "verified"}]
    )






@pytest.mark.parametrize(
    "failure", ["self", "source-missing", "source-short", "source-repeat", "source-kind", "duplicate"]
)
def test_invalid_matte_scene_is_rejected_before_persist(failure):
    raw = matte_direction().model_dump(mode="json", by_alias=True)
    scene, op = raw["scenes"][0], raw["scenes"][0]["motionRecipes"][0]
    if failure == "self":
        op["parameters"]["assetMatte"]["sourceTargetId"] = "hero"
    elif failure == "source-missing":
        op["parameters"]["assetMatte"]["sourceTargetId"] = "missing"
    elif failure == "source-short":
        scene["elements"][-1]["durationFrames"] = 8
    elif failure == "source-repeat":
        scene["elements"][-1].update(repeatCount=2, durationFrames=7)
        op["endFrameExclusive"] = 7
    elif failure == "source-kind":
        scene["elements"][-1].update(kind="shape", assetId=None)
    else:
        duplicate = copy.deepcopy(op)
        duplicate["id"] = "second-matte"
        scene["motionRecipes"].append(duplicate)
    with pytest.raises(ValueError):
        native_document(ContextualPlanRequestV2.model_validate(raw), [{"id": "mask", "mediaType": "image/png"}])


def test_legacy_parameters_do_not_gain_empty_matte_field():
    assert "assetMatte" not in RecipeParametersV1().model_dump(mode="json", by_alias=True)
    old = MotionRecipeV1.model_validate(recipe("motivated_occlusion", occluderTargetId="cover"))
    assert "assetMatte" not in old.model_dump(mode="json", by_alias=True)["parameters"]
