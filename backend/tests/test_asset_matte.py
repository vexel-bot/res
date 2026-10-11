"""Canonical image mattes: identity, interval, ownership and compatibility."""

import copy

import pytest
from test_native_motion_recipes import recipe
from test_remotion_native import native_direction, native_document

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.motion_recipes import MotionRecipeV1, RecipeParametersV1
from app.providers.studios.remotion_projection import compile_remotion_composition


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


def test_matte_lowers_source_asset_space_interval_and_digest():
    doc, projection = compiled()
    asset = {"mask": {"sha256": "a" * 64, "mime": "image/png", "path": "fixture.png"}}
    manifest = compile_remotion_composition(doc, projection, asset)
    source = next(layer for layer in manifest["layers"] if layer["name"] == "matte")
    hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
    assert source["properties"]["matteSourceOnly"]
    spec = hero["properties"]["recipeAssetMatte"]
    assert spec["sourceLayerId"] == source["id"] and spec["assetId"] == "mask"
    assert spec["coordinateSpace"] == "composition_world" and spec["opacitySpace"] == "source_layer_only"
    assert (spec["startFrame"], spec["endFrameExclusive"]) == (2, 13)
    assert manifest["componentLibraryVersion"] == 6
    changed, p2 = native_document(matte_direction(invert=True), doc.assets)
    assert (
        compile_remotion_composition(changed, p2, asset)["nativeCompositionDigest"]
        != manifest["nativeCompositionDigest"]
    )


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "checksum",
        "mime",
        "spec",
        "source-role",
        "source-id",
        "legacy",
        "source-stack",
        "mask-conflict",
        "orphan",
        "source-scene",
        "target-id",
        "node",
        "parent-cycle",
        "ref-mime",
    ],
)
def test_unbound_or_unsupported_matte_fails_projection(failure):
    doc, projection = compiled()
    hero = next(layer for layer in doc.composition.pages[0].layers if layer.name == "hero")
    source = next(layer for layer in doc.composition.pages[0].layers if layer.name == "matte")
    op = doc.composition.narrative["editorialV2"]["nativeRecipeOperations"][0]
    asset = {"mask": {"sha256": "a" * 64, "mime": "image/png", "path": "fixture.png"}}
    if failure == "missing":
        asset = {}
    elif failure == "checksum":
        asset["mask"]["sha256"] = "b" * 64
    elif failure == "mime":
        asset["mask"]["mime"] = "image/jpeg"
    elif failure == "spec":
        hero.properties["recipeAssetMatte"]["invert"] = True
    elif failure == "source-role":
        source.properties["matteSourceOnly"] = False
    elif failure == "source-id":
        op["matteSourceLayerId"] = "absent"
    elif failure == "legacy":
        op["compilerVersion"] = "res.native-recipes.v3"
    elif failure == "source-stack":
        source.properties["maskAssetId"] = "mask"
    elif failure == "mask-conflict":
        hero.properties["maskAssetId"] = "mask"
    elif failure == "source-scene":
        source.properties["editorialSceneId"] = "other-scene"
    elif failure == "target-id":
        op["targetLayerIds"] = [source.id]
    elif failure == "node":
        projection.nodes = [node for node in projection.nodes if node.target_layer_id != source.id]
    elif failure == "parent-cycle":
        node = next(node for node in projection.nodes if node.target_layer_id == source.id)
        node.parent_node_id = node.node_id
    elif failure == "ref-mime":
        doc.assets[0].media_type = "image/jpeg"
    else:
        source.properties["recipeAssetMatte"] = copy.deepcopy(hero.properties["recipeAssetMatte"])
    with pytest.raises(ValueError):
        compile_remotion_composition(doc, projection, asset)


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


def test_legacy_v3_measured_typography_remains_readable():
    from test_typography_units import typography_direction

    doc, projection = native_document(typography_direction("Título"))
    for operation in doc.composition.narrative["editorialV2"]["nativeRecipeOperations"]:
        operation["compilerVersion"] = "res.native-recipes.v3"
    manifest = compile_remotion_composition(doc, projection, {})
    assert manifest["componentLibraryVersion"] == 5
    assert next(layer for layer in manifest["layers"] if layer["name"] == "hero")["properties"]["recipeTextLayout"]
