"""Cuts and a finished audio mix passed by the director to the assembler."""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract


class AssemblyClip(StudioContract):
    asset_id: str = Field(min_length=1, max_length=128)
    start_frame: int = Field(default=0, ge=0, le=324_000)
    duration_frames: int = Field(gt=0, le=18_000)
    fit: Literal["contain", "cover"] = "contain"


class VideoAssembly(StudioContract):
    aspect: Literal["9:16", "16:9", "1:1"] = "9:16"
    clips: list[AssemblyClip] = Field(min_length=1, max_length=100)
    audio_asset_id: str | None = Field(default=None, min_length=1, max_length=128)

    @property
    def asset_ids(self):
        return {clip.asset_id for clip in self.clips} | ({self.audio_asset_id} if self.audio_asset_id else set())

    @model_validator(mode="after")
    def check_duration(self):
        if sum(clip.duration_frames for clip in self.clips) > 18_000:
            raise ValueError("moneyprinterturbo_duration_limit")
        return self


class AssemblyRenderRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    assembly: VideoAssembly
