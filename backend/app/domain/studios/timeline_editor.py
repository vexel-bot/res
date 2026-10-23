"""Validated capabilities of Clicko's canonical-timeline CPU renderer.

These are constraints on MediaTimelineV1, not another project format.
"""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import MediaTimelineV1, StudioContract


class MotionKey(StudioContract):
    property: Literal["x", "y", "scale", "opacity", "rotation"]
    frame: int = Field(ge=0, le=108_000)
    value: float = Field(ge=-8192, le=8192, allow_inf_nan=False)
    easing: Literal["linear", "ease-in-out", "ease-out"] = "linear"

    @model_validator(mode="after")
    def bounded_property(self):
        if self.property == "scale" and not 0.1 <= self.value <= 4:
            raise ValueError("timeline_scale_invalid")
        if self.property == "opacity" and not 0 <= self.value <= 1:
            raise ValueError("timeline_opacity_invalid")
        if self.property == "rotation" and not -360 <= self.value <= 360:
            raise ValueError("timeline_rotation_invalid")
        return self


class VisualMotion(StudioContract):
    original_audio_enabled: bool = Field(default=True, strict=True)
    background_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    x: float = Field(default=0, ge=-8192, le=8192, allow_inf_nan=False)
    y: float = Field(default=0, ge=-8192, le=8192, allow_inf_nan=False)
    scale: float = Field(default=1, ge=0.1, le=4, allow_inf_nan=False)
    opacity: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    rotation: float = Field(default=0, ge=-360, le=360, allow_inf_nan=False)
    gain_db: float = Field(default=0, ge=-60, le=12, allow_inf_nan=False)
    fade_in_frames: int = Field(default=0, ge=0, le=108_000)
    fade_out_frames: int = Field(default=0, ge=0, le=108_000)


class TimelineEditRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    timeline: MediaTimelineV1


class TimelineRenderRequest(StudioContract):
    expected_revision: int = Field(ge=1)


PROVIDER = "ffmpeg.timeline-v1"
JOB_TYPE = "timeline_render"
