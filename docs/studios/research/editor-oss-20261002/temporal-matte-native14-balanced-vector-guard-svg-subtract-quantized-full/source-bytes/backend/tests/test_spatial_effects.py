"""Persisted spatial parameters keep their typed semantics and digest binding."""
import copy

import pytest
from test_remotion_native import native_document
from test_spatial_effects_render import spatial_direction

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.providers.studios.remotion_projection import compile_remotion_composition


@pytest.fixture(autouse=True)
def clean_database():
    yield


def spatial_document():
    doc, projection = native_document(ContextualPlanRequestV2.model_validate(spatial_direction("spatial")))
    return doc, projection, next(layer for layer in doc.composition.pages[0].layers if layer.name == "hard")


def test_spatial_authored_parameters_and_digest_change_without_document_mutation():
    doc, projection, layer = spatial_document()
    before = doc.model_dump(mode="json")
    initial = compile_remotion_composition(doc, projection, {})
    assert doc.model_dump(mode="json") == before
    output = next(item for item in initial["layers"] if item["id"] == layer.id)
    assert output["properties"]["editorialShadow"] == {"x": 32, "y": 12, "blur": 0,
                                                       "color": "#ff0000", "opacity": .5}
    layer.properties["editorialShadow"]["opacity"] = .25
    revised = compile_remotion_composition(doc, projection, {})
    assert initial["nativeCompositionDigest"] != revised["nativeCompositionDigest"]
    assert revised["graphDigestSha256"] == initial["graphDigestSha256"]


@pytest.mark.parametrize("value", [{"offsetX": 32}, {"color": "url(unregistered)"}, {"opacity": 1.01},
                                  {"x": 101}, {"y": -101}, {"blur": 101}, {"blur": -1},
                                  {"opacity": float("nan")}, [], "free CSS"])
def test_persisted_shadow_invalid_values_and_aliases_have_target_diagnostic(value):
    doc, projection, layer = spatial_document()
    layer.properties["editorialShadow"] = value
    with pytest.raises(ValueError, match="remotion_native_shadow_invalid:" + layer.id):
        compile_remotion_composition(doc, projection, {})


@pytest.mark.parametrize("value", [{"blurPx": -1}, {"blurPx": 41}, {"blurPx": float("inf")},
                                  {"opacity": 1.01}, {"freeFilter": "blur(4px)"}, []])
def test_persisted_depth_invalid_values_have_target_diagnostic(value):
    doc, projection, layer = spatial_document()
    layer.properties["editorialDepth"] = value
    with pytest.raises(ValueError, match="remotion_native_depth_invalid:" + layer.id):
        compile_remotion_composition(doc, projection, {})


def test_shadow_defaults_normalize_only_the_manifest_and_none_is_absent():
    doc, projection, layer = spatial_document()
    layer.properties["editorialShadow"] = {"color": "#123456"}
    original = copy.deepcopy(layer.properties)
    manifest = compile_remotion_composition(doc, projection, {})
    output = next(item for item in manifest["layers"] if item["id"] == layer.id)
    assert output["properties"]["editorialShadow"] == {"x": 0, "y": 6, "blur": 12,
                                                       "color": "#123456", "opacity": .18}
    assert layer.properties == original
    layer.properties["editorialShadow"] = None
    compile_remotion_composition(doc, projection, {})


def test_persisted_static_and_animated_blur_cannot_compete():
    doc, projection, _ = spatial_document()
    animated = next(layer for layer in doc.composition.pages[0].layers if layer.name == "animated")
    animated.properties["editorialDepth"]["blurPx"] = 4
    with pytest.raises(ValueError, match="remotion_native_blur_authoring_conflict:" + animated.id):
        compile_remotion_composition(doc, projection, {})


def test_unregistered_effect_stack_still_requires_qualification():
    doc, projection, layer = spatial_document()
    layer.properties["editorialEffects"] = [{"id": "free-stack", "kind": "brightness", "amount": 1.2}]
    with pytest.raises(ValueError, match="remotion_native_effect_unsupported:" + layer.id):
        compile_remotion_composition(doc, projection, {})
