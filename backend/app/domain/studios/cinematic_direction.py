"""Provider-neutral cinematic intent for mixed footage and motion scenes.

These contracts describe observable decisions. They do not claim that stock
footage was relit, that a digital crop changed the physical camera, or that a
render was reviewed.
"""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract


class EditorialMotionSystemV2(StudioContract):
    """Executable art choices for graphic motion, independent of the brief."""

    schema_version: Literal["studio.editorial-motion-system.v2"] = "studio.editorial-motion-system.v2"
    layout: Literal["editorial_asymmetric", "typography_dominant", "graphic_motif"]
    alignment: Literal["left", "right"] = "left"
    frame: Literal["none", "hairline"] = "none"
    motion_character: Literal["restrained", "rhythmic", "expressive"] = "rhythmic"


class CinematicArtDirectionV1(StudioContract):
    schema_version: Literal["studio.cinematic-art-direction.v1"] = (
        "studio.cinematic-art-direction.v1"
    )
    visual_system: str = Field(min_length=1, max_length=2000)
    palette: list[str] = Field(min_length=1, max_length=12)
    typography: str = Field(min_length=1, max_length=1000)
    contrast_strategy: str = Field(min_length=1, max_length=1000)
    footage_treatment: str = Field(min_length=1, max_length=1000)
    graphics_relationship: str = Field(min_length=1, max_length=1000)
    continuity_rules: list[str] = Field(min_length=1, max_length=20)
    rejected_style_moves: list[str] = Field(default_factory=list, max_length=10)
    motion_system: EditorialMotionSystemV2 | None = None


class CinematicLightingIntentV1(StudioContract):
    quality: Literal["soft", "hard", "mixed", "available", "graphic"]
    direction: Literal["front", "side", "back", "top", "motivated", "not_applicable"]
    contrast: Literal["low", "medium", "high"]
    temperature_relationship: str = Field(min_length=1, max_length=500)
    subject_separation: str = Field(min_length=1, max_length=500)
    execution_mode: Literal[
        "select_existing_footage", "deterministic_composite", "generation_guidance"
    ]


class CinematicShotIntentV1(StudioContract):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    function: Literal["establish", "demonstrate", "detail", "compare", "consequence", "reaction"]
    subject: str = Field(min_length=1, max_length=1000)
    observable_action: str = Field(min_length=1, max_length=1500)
    shot_scale: Literal[
        "extreme_wide", "wide", "medium", "close", "extreme_close", "interface", "graphic"
    ]
    angle: Literal[
        "eye_level", "high", "low", "overhead", "profile", "over_shoulder", "not_applicable"
    ]
    region_of_interest: str = Field(min_length=1, max_length=1000)
    attention_start: str = Field(min_length=1, max_length=1000)
    attention_end: str = Field(min_length=1, max_length=1000)
    lighting: CinematicLightingIntentV1
    cut_motivation: str = Field(min_length=1, max_length=1000)
    continuity: list[str] = Field(default_factory=list, max_length=15)
    material_requirement_ids: list[str] = Field(default_factory=list, max_length=15)
    execution_component_ids: list[str] = Field(default_factory=list, max_length=15)
    target_element_ids: list[str] = Field(default_factory=list, max_length=15)
    verification: list[str] = Field(min_length=1, max_length=15)
    start_frame: int | None = Field(default=None, ge=0, le=108000)
    end_frame_exclusive: int | None = Field(default=None, gt=0, le=108000)

    @model_validator(mode="after")
    def timing_is_complete(self):
        if (self.start_frame is None) != (self.end_frame_exclusive is None):
            raise ValueError("cinematic_shot_timing_incomplete")
        if self.start_frame is not None and self.end_frame_exclusive <= self.start_frame:
            raise ValueError("cinematic_shot_interval_invalid")
        return self
