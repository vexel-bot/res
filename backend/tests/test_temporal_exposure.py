"""Exposure opt-in preserves snapshots and rejects stale or contradictory bindings."""

import copy

import pytest
from pydantic import ValidationError
from test_asset_matte import matte_direction
from test_native_motion_recipes import recipe
from test_remotion_native import native_document
from test_temporal_exposure_render import exposure_direction
from test_temporal_rig_render import rig_direction
from test_typography_units import typography_direction

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.motion_recipes import MotionRecipeV1, RecipeParametersV1, TemporalExposureV1


@pytest.fixture(autouse=True)
def clean_database():
    yield


POLICY = TemporalExposureV1().model_dump(mode="json", by_alias=True)


def compiled(policy=POLICY):
    return native_document(ContextualPlanRequestV2.model_validate(exposure_direction(8, policy=policy)))






@pytest.mark.parametrize(
    "field,value",
    [
        ("sampling", "forward"),
        ("coordinateSpace", "world"),
        ("ancestorTime", "sample_frame"),
        ("compositing", "screen"),
        ("staticReduction", "always"),
        ("schemaVersion", "studio.temporal-exposure.v2"),
    ],
)
def test_unregistered_policy_is_rejected(field, value):
    with pytest.raises(ValidationError):
        TemporalExposureV1.model_validate({**POLICY, field: value})


def test_policy_requires_blur_recipe():
    with pytest.raises(ValidationError, match="temporal_exposure_technique_required"):
        MotionRecipeV1.model_validate(recipe("vector_reveal", temporalExposure=POLICY))


def test_legacy_zero_shutter_has_explicit_correction_instead_of_browser_crash():
    with pytest.raises(ValueError, match="temporal_zero_shutter_requires_policy"):
        native_document(ContextualPlanRequestV2.model_validate(exposure_direction(8, shutter=0)))










def test_matte_under_moving_external_parent_uses_center_frame_ancestors():
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



@pytest.mark.parametrize("shutter,exposure_start,hold,accepted", [(180, 0, 11, False), (180, 0, 10, True),
                                                              (0, 0, 11, True), (180, 19, 11, True)])
def test_typography_hold_counts_the_whole_exposure(shutter, exposure_start, hold, accepted):
    direction = typography_direction("AÇÃO", duration=30, stagger=3, hold=hold).model_dump(mode="json", by_alias=True)
    blur = recipe("velocity_blur", temporalExposure=POLICY, temporalSamples=8, shutterDegrees=shutter)
    blur.update(id="type-exposure", startFrame=exposure_start, endFrameExclusive=30)
    direction["scenes"][0]["motionRecipes"].append(blur)
    if accepted:
        document, _ = native_document(ContextualPlanRequestV2.model_validate(direction))
        assert any(layer.properties.get("recipeTemporalBlur") for layer in document.composition.pages[0].layers)
    else:
        with pytest.raises(ValueError, match="temporal_complete_reading_hold_required"):
            native_document(ContextualPlanRequestV2.model_validate(direction))


@pytest.mark.parametrize("outer_new,inner_new", [(True, True), (True, False), (False, True), (False, False)])
def test_nested_exposure_overlap_is_explicitly_rejected(outer_new, inner_new):
    raw = rig_direction("disjoint")
    for item in raw["scenes"][0]["motionRecipes"]:
        if item["technique"] == "velocity_blur":
            item.update(startFrame=0, endFrameExclusive=30)
            if not (outer_new if item["targetIds"] == ["rig"] else inner_new):
                item["parameters"].pop("temporalExposure")
    diagnostic = "temporal_nested_target_pending" if outer_new or inner_new else "graphic_blur_descendants_required"
    with pytest.raises(ValueError, match=diagnostic):
        native_document(ContextualPlanRequestV2.model_validate(raw))
