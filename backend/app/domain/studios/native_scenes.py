"""Versioned, data-only controls for the registered Remotion scene library."""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract


class NativeSceneComponentV1(StudioContract):
    component: Literal[
        "action_montage",
        "product_demonstration",
        "integrated_typography",
        "gesture_occlusion_reveal",
        "moving_variant_mask",
    ]
    version: Literal[1] = 1
    target_ids: list[str] = Field(min_length=1, max_length=20)
    entrance_frames: int = Field(default=12, ge=1, le=120)
    travel_ratio: float = Field(default=0.04, ge=0, le=0.25, allow_inf_nan=False)
    reveal_axis: Literal["horizontal", "vertical"] = "horizontal"
    stagger_frames: int = Field(default=3, ge=0, le=30)
    continuity_key: str | None = Field(default=None, max_length=120)
    base_target_id: str | None = Field(default=None, max_length=80)
    occluder_target_id: str | None = Field(default=None, max_length=80)
    switch_frame: int = Field(default=0, ge=0, le=108000)
    mask_start_x: float = Field(default=0.25, ge=0, le=1)
    mask_start_y: float = Field(default=0.5, ge=0, le=1)
    mask_end_x: float = Field(default=0.75, ge=0, le=1)
    mask_end_y: float = Field(default=0.5, ge=0, le=1)
    mask_radius: float = Field(default=0.25, gt=0, le=1)

    @model_validator(mode="after")
    def registered_recipe(self):
        if self.component in {"gesture_occlusion_reveal", "moving_variant_mask"} and not self.base_target_id:
            raise ValueError("editing_native_variant_base_required")
        if self.component == "gesture_occlusion_reveal" and not self.occluder_target_id:
            raise ValueError("editing_native_occluder_required")
        if self.component == "gesture_occlusion_reveal" and not (
            (self.reveal_axis == "horizontal" and self.mask_start_x == 0 and self.mask_end_x == 1)
            or (self.reveal_axis == "vertical" and self.mask_start_y == 0 and self.mask_end_y == 1)
        ):
            raise ValueError("editing_native_occluder_full_travel_required")
        return self


NATIVE_COMPONENTS = {
    "action_montage": {"version": 1, "kinds": ["video"]},
    "product_demonstration": {"version": 1, "kinds": ["image", "video", "group"]},
    "integrated_typography": {"version": 1, "kinds": ["text"]},
    "gesture_occlusion_reveal": {"version": 1, "kinds": ["image", "video"]},
    "moving_variant_mask": {"version": 1, "kinds": ["image", "video"]},
}
