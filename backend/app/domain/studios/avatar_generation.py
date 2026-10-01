"""Deterministic timing rules shared by avatar planning and receipts."""

from __future__ import annotations

import math

from pydantic import Field

from .contracts import StudioContract


class LongCatSegmentTimingV1(StudioContract):
    schema_version: str = "studio.longcat-segment-timing.v1"
    requested_duration_ms: int = Field(gt=0)
    fps: int = Field(default=25, ge=1)
    segment_frames: int = Field(default=93, gt=1)
    overlap_frames: int = Field(default=13, ge=0)
    segment_count: int = Field(gt=0)
    produced_frames: int = Field(gt=0)
    produced_duration_ms: int = Field(gt=0)
    trim_tail_ms: int = Field(ge=0)


def longcat_segment_timing(
    requested_duration_ms: int,
    *,
    fps: int = 25,
    segment_frames: int = 93,
    overlap_frames: int = 13,
) -> LongCatSegmentTimingV1:
    if requested_duration_ms <= 0:
        raise ValueError("avatar_audio_duration_required")
    stride = segment_frames - overlap_frames
    if stride <= 0:
        raise ValueError("avatar_segment_overlap_invalid")
    requested_frames = math.ceil(requested_duration_ms * fps / 1000)
    additional = max(0, requested_frames - segment_frames)
    segments = 1 + math.ceil(additional / stride)
    produced_frames = segment_frames + (segments - 1) * stride
    produced_ms = math.ceil(produced_frames * 1000 / fps)
    return LongCatSegmentTimingV1(
        requested_duration_ms=requested_duration_ms,
        fps=fps,
        segment_frames=segment_frames,
        overlap_frames=overlap_frames,
        segment_count=segments,
        produced_frames=produced_frames,
        produced_duration_ms=produced_ms,
        trim_tail_ms=max(0, produced_ms - requested_duration_ms),
    )
