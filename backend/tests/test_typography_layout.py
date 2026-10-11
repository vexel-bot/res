"""Versioned final-font layout policy is part of the canonical recipe binding."""

import copy

import pytest
from test_remotion_native import native_document
from test_typography_units import typography_direction

from app.domain.studios.typography import layout_policy
from app.providers.studios.remotion_projection import compile_remotion_composition


@pytest.fixture(autouse=True)
def clean_database():
    yield


def test_layout_policy_is_bound_to_canvas_and_changes_digest():
    doc, projection = native_document(typography_direction("Uma palavra inteira", "word"))
    manifest = compile_remotion_composition(doc, projection, {})
    hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
    policy = hero["properties"]["recipeTextLayout"]
    assert policy == layout_policy(320).model_dump(mode="json", by_alias=True)
    assert policy["minFontSizePx"] == pytest.approx(320 * 16 / 300)
    assert manifest["nativeRecipeOperations"][0]["typographyLayouts"][hero["id"]] == policy
    legacy = copy.deepcopy(doc)
    old_hero = next(layer for layer in legacy.composition.pages[0].layers if layer.name == "hero")
    old_hero.properties.pop("recipeTextLayout")
    operation = legacy.composition.narrative["editorialV2"]["nativeRecipeOperations"][0]
    operation["compilerVersion"] = "res.native-recipes.v2"
    operation.pop("typographyLayouts")
    old_manifest = compile_remotion_composition(legacy, projection, {})
    assert old_manifest["componentLibraryVersion"] == 4
    assert old_manifest["nativeCompositionDigest"] != manifest["nativeCompositionDigest"]
    assert old_hero.properties["recipeTypography"] == hero["properties"]["recipeTypography"]


@pytest.mark.parametrize("mutation", ["missing", "floor", "layer", "policy", "limit", "downgrade", "orphan"])
def test_stale_or_unbound_layout_is_rejected(mutation):
    doc, projection = native_document(typography_direction("Título"))
    hero = next(layer for layer in doc.composition.pages[0].layers if layer.name == "hero")
    operation = doc.composition.narrative["editorialV2"]["nativeRecipeOperations"][0]
    if mutation == "missing":
        operation.pop("typographyLayouts")
    elif mutation == "floor":
        operation["typographyLayouts"][hero.id]["minFontSizePx"] = 8
    elif mutation == "layer":
        hero.properties["recipeTextLayout"] = {**hero.properties["recipeTextLayout"], "minFontSizePx": 8}
    elif mutation == "policy":
        operation["typographyLayouts"][hero.id]["policy"] = "arbitrary"
    elif mutation == "limit":
        operation["typographyLayouts"][hero.id]["maxLayoutUnits"] = 50000
    elif mutation == "downgrade":
        operation["compilerVersion"] = "res.native-recipes.v2"
    else:
        operation["compilerVersion"] = "res.native-recipes.v2"
        operation.pop("typographyLayouts")
    with pytest.raises(ValueError):
        compile_remotion_composition(doc, projection, {})


def test_oversized_layout_fails_before_render_or_dom_allocation():
    with pytest.raises(ValueError, match="layout_unit_limit"):
        native_document(typography_direction("A" * 2001, duration=30, stagger=0, hold=20))
