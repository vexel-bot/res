"""Explicit proposed native.14 contracts; historical assertions stay intact."""
# ruff: noqa: F811
import copy

import pytest
from test_asset_matte import matte_direction
from test_contextual_editing import document, request
from test_contextual_editing import media as media
from test_native_motion_recipes import recipe
from test_remotion_native import native_document
from test_temporal_exposure import POLICY

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2




def test_candidate_matte_under_moving_external_parent_compiles_at_both_scopes():
    direction = matte_direction()
    blur = recipe("velocity_blur", temporalExposure=POLICY, temporalSamples=8)
    blur.update(id="matte-exposure", targetIds=["hero"])
    raw = direction.model_dump(mode="json", by_alias=True)
    raw["scenes"][0]["motionRecipes"].append(blur)
    assets = [{"id": "mask", "mediaType": "image/png", "checksum": "a" * 64, "rightsStatus": "verified"}]
    for target in ["hero", "target-rig"]:
        scoped = copy.deepcopy(raw)
        scoped["scenes"][0]["motionRecipes"][-1]["targetIds"] = [target]
        document, projection = native_document(ContextualPlanRequestV2.model_validate(scoped), assets)
        exposed = [layer for layer in document.composition.pages[0].layers
                   if layer.properties.get("recipeTemporalBlur")]
        assert len(exposed) == 1
        assert exposed[0].properties["recipeTemporalBlur"]["exposurePolicy"] == POLICY
        assert projection is not None
