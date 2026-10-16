"""Data-only editorial recipes; a recipe is not evidence of rendered pixels."""

from typing import Literal

from pydantic import Field, model_serializer, model_validator

from .contracts import StudioContract

Technique = Literal[
    "motion_choreography",
    "layer_rig",
    "motivated_occlusion",
    "integrated_type",
    "vector_reveal",
    "velocity_blur",
    "depth_camera",
    "localized_refraction",
    "action_sound_cut",
    "asset_matte",
]
RECIPE_CAPABILITIES = {
    "motion_choreography": "recipe.choreography",
    "layer_rig": "recipe.layer_rig",
    "motivated_occlusion": "recipe.occlusion",
    "integrated_type": "recipe.typography",
    "vector_reveal": "recipe.vector_reveal",
    "velocity_blur": "recipe.temporal_blur",
    "depth_camera": "recipe.depth_camera",
    "localized_refraction": "recipe.displacement",
    "action_sound_cut": "recipe.action_sound_cut",
    "asset_matte": "recipe.asset_matte",
}


class RecipeKeyframeV1(StudioContract):
    frame: int = Field(ge=0, le=108000)
    value: float = Field(allow_inf_nan=False)
    curve: tuple[float, float, float, float] = (0.2, 0.0, 0.2, 1.0)

    @model_validator(mode="after")
    def valid_curve(self):
        import math

        if not all(math.isfinite(v) for v in self.curve) or not all(0 <= self.curve[i] <= 1 for i in (0, 2)):
            raise ValueError("motion_recipe_curve_invalid")
        return self


class RecipeTrackV1(StudioContract):
    target_id: str = Field(min_length=1, max_length=120)
    property: Literal["x", "y", "z", "rotation", "scale_x", "scale_y", "opacity", "stroke_progress"]
    keyframes: list[RecipeKeyframeV1] = Field(min_length=2, max_length=60)

    @model_validator(mode="after")
    def ordered(self):
        frames = [k.frame for k in self.keyframes]
        if frames != sorted(set(frames)):
            raise ValueError("motion_recipe_keyframes_must_increase")
        if self.property in {"opacity", "stroke_progress"} and any(not 0 <= k.value <= 1 for k in self.keyframes):
            raise ValueError("motion_recipe_progress_out_of_range")
        return self


class AssetMatteV1(StudioContract):
    schema_version: Literal["studio.asset-matte.v1"] = "studio.asset-matte.v1"
    source_target_id: str = Field(min_length=1, max_length=120)
    mode: Literal["alpha", "luminance"] = "alpha"
    invert: bool = False
    coordinate_space: Literal["composition_world"] = "composition_world"
    opacity_space: Literal["source_layer_only"] = "source_layer_only"


class TemporalExposureV1(StudioContract):
    schema_version: Literal["studio.temporal-exposure.v1"] = "studio.temporal-exposure.v1"
    sampling: Literal["centered_clipped"] = "centered_clipped"
    coordinate_space: Literal["local_subtree"] = "local_subtree"
    ancestor_time: Literal["center_frame"] = "center_frame"
    compositing: Literal["premultiplied_srgb_plus_lighter"] = "premultiplied_srgb_plus_lighter"
    static_reduction: Literal["identical_registered_draw_inputs"] = "identical_registered_draw_inputs"


class RecipeParametersV1(StudioContract):
    tracks: list[RecipeTrackV1] = Field(default_factory=list, max_length=100)
    pivot: tuple[float, float] = (0.5, 0.5)
    parent_target_id: str | None = Field(default=None, max_length=120)
    mask_asset_id: str | None = Field(default=None, max_length=120)
    occluder_target_id: str | None = Field(default=None, max_length=120)
    asset_matte: AssetMatteV1 | None = None
    temporal_exposure: TemporalExposureV1 | None = None
    text_unit: Literal["word", "character"] = "word"
    stagger_frames: int = Field(default=3, ge=0, le=60)
    reading_hold_frames: int = Field(default=30, ge=1, le=108000)
    shutter_degrees: float = Field(default=180, ge=0, le=360, allow_inf_nan=False)
    temporal_samples: int = Field(default=8, ge=2, le=32)
    focus_distance: float = Field(default=1000, gt=0, le=100000, allow_inf_nan=False)
    depth_of_field: float = Field(default=100, gt=0, le=100000, allow_inf_nan=False)
    displacement_ratio: float = Field(default=0.01, ge=0, le=0.05, allow_inf_nan=False)

    @model_serializer(mode="wrap")
    def preserve_legacy_parameters(self, handler, info):
        value = handler(self)
        if self.asset_matte is None:
            value.pop("assetMatte" if info.by_alias else "asset_matte", None)
        if self.temporal_exposure is None:
            value.pop("temporalExposure" if info.by_alias else "temporal_exposure", None)
        return value

    @model_validator(mode="after")
    def valid_pivot(self):
        if any(not 0 <= value <= 1 for value in self.pivot):
            raise ValueError("motion_recipe_pivot_invalid")
        return self


class RecipeSoundEventV1(StudioContract):
    audio_id: str = Field(min_length=1, max_length=120)
    target_id: str = Field(min_length=1, max_length=120)
    frame: int = Field(ge=0, le=108000)
    observable_event: str = Field(min_length=1, max_length=1000)


class MotionRecipeV1(StudioContract):
    schema_version: Literal["studio.motion-recipe.v1"] = "studio.motion-recipe.v1"
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    version: Literal[1] = 1
    technique: Technique
    target_ids: list[str] = Field(min_length=1, max_length=30)
    start_frame: int = Field(ge=0, le=108000)
    end_frame_exclusive: int = Field(gt=0, le=108000)
    intent: str = Field(min_length=1, max_length=2000)
    continuity_anchor: str = Field(min_length=1, max_length=1000)
    parameters: RecipeParametersV1 = Field(default_factory=RecipeParametersV1)
    sound_events: list[RecipeSoundEventV1] = Field(default_factory=list, max_length=30)
    verification: list[str] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def bounded(self):
        if self.start_frame >= self.end_frame_exclusive or len(set(self.target_ids)) != len(self.target_ids):
            raise ValueError("motion_recipe_interval_or_targets_invalid")
        duration = self.end_frame_exclusive - self.start_frame
        if any(k.frame > duration for t in self.parameters.tracks for k in t.keyframes):
            raise ValueError("motion_recipe_track_out_of_range")
        if any(not self.start_frame <= e.frame < self.end_frame_exclusive for e in self.sound_events):
            raise ValueError("motion_recipe_sound_out_of_range")
        if self.technique == "integrated_type" and self.parameters.reading_hold_frames > duration:
            raise ValueError("motion_recipe_reading_hold_out_of_range")
        if self.technique == "motion_choreography" and not self.parameters.tracks:
            raise ValueError("motion_recipe_tracks_required")
        if self.technique == "layer_rig" and (
            not self.parameters.parent_target_id or self.parameters.parent_target_id in self.target_ids
        ):
            raise ValueError("motion_recipe_parent_required")
        if self.technique == "motivated_occlusion" and not self.parameters.occluder_target_id:
            raise ValueError("motion_recipe_occluder_required")
        if self.technique == "asset_matte":
            if not self.parameters.asset_matte or self.parameters.asset_matte.source_target_id in self.target_ids:
                raise ValueError("motion_recipe_asset_matte_source_required")
            if self.parameters.mask_asset_id or self.parameters.occluder_target_id or self.parameters.tracks:
                raise ValueError("motion_recipe_asset_matte_parameter_conflict")
        elif self.parameters.asset_matte is not None:
            raise ValueError("motion_recipe_asset_matte_technique_required")
        if self.parameters.temporal_exposure is not None and self.technique != "velocity_blur":
            raise ValueError("motion_recipe_temporal_exposure_technique_required")
        if self.technique == "localized_refraction" and not self.parameters.mask_asset_id:
            raise ValueError("motion_recipe_displacement_map_required")
        if self.technique == "action_sound_cut" and not self.sound_events:
            raise ValueError("motion_recipe_visible_sound_event_required")
        track_ids = [(track.target_id, track.property) for track in self.parameters.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("motion_recipe_duplicate_track")
        return self


class TechniqueSourceV1(StudioContract):
    url: str = Field(pattern=r"^https://", max_length=4000)
    kind: Literal["documentation", "watched_tutorial", "inference"] = "documentation"
    start_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    end_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    audio_verified: bool = False
    observed_result: str = Field(default="", max_length=4000)
    steps: list[str] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def tutorial_evidence(self):
        if self.kind == "watched_tutorial" and (
            self.start_seconds is None
            or self.end_seconds is None
            or self.end_seconds <= self.start_seconds
            or not self.steps
            or not self.observed_result
        ):
            raise ValueError("motion_tutorial_interval_steps_result_required")
        if self.kind != "watched_tutorial" and self.audio_verified:
            raise ValueError("motion_documentation_cannot_verify_audio")
        return self


class EngineTechniqueQualificationV1(StudioContract):
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=120)
    status: Literal["knowledge_only", "implemented", "render_verified"] = "knowledge_only"
    evidence_asset_id: str | None = None
    evidence_checksum: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def verified_evidence(self):
        if self.status == "render_verified" and not (self.evidence_asset_id and self.evidence_checksum):
            raise ValueError("motion_engine_render_evidence_required")
        return self
