"""Materialize Unicode units once; renderer consumes canonical units verbatim."""

from __future__ import annotations

import hashlib
from typing import Literal

import regex
from pydantic import Field, model_validator

from .contracts import StudioContract

SEGMENTER_VERSION = "2026.1.15"
SEGMENTATION_POLICY = "unicode17.regex2026.1.15.whitespace-v1"
LAYOUT_POLICY = "dom.units-fit.v1"
_WHITE_SPACE = regex.compile(r"\p{White_Space}+", regex.VERSION1)
_WORD_BLOCKS = regex.compile(r"\p{White_Space}+|[^\p{White_Space}]+", regex.VERSION1)
_GRAPHEMES = regex.compile(r"\X", regex.VERSION1)


class TypographyLayoutPolicyV1(StudioContract):
    schema_version: Literal["studio.typography-layout-policy.v1"] = "studio.typography-layout-policy.v1"
    policy: Literal["dom.units-fit.v1"] = LAYOUT_POLICY
    fit_mode: Literal["wrap_shrink"] = "wrap_shrink"
    min_font_size_px: float = Field(ge=8, le=205)
    max_measure_steps: Literal[18] = 18
    max_layout_units: Literal[2000] = 2000
    tolerance_px: Literal[0.5] = 0.5
    font_quantization_px: Literal[0.015625] = 0.015625


def layout_policy(canvas_width: int) -> TypographyLayoutPolicyV1:
    return TypographyLayoutPolicyV1(min_font_size_px=max(8, canvas_width * 16 / 300))


class TypographyUnitV1(StudioContract):
    text: str = Field(min_length=1, max_length=40000)
    animation_index: int | None = Field(default=None, ge=0, le=40000)


class TypographySegmentationV1(StudioContract):
    schema_version: Literal["studio.typography-units.v1"] = "studio.typography-units.v1"
    policy: Literal["unicode17.regex2026.1.15.whitespace-v1"] = SEGMENTATION_POLICY
    unit: Literal["word", "character"]
    text_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    units: list[TypographyUnitV1] = Field(min_length=1, max_length=40000)
    animated_count: int = Field(ge=1, le=40000)

    @model_validator(mode="after")
    def validate_indices(self):
        index = 0
        for unit in self.units:
            expected = None if _WHITE_SPACE.fullmatch(unit.text) else index
            if unit.animation_index != expected:
                raise ValueError("typography_animation_index_invalid")
            if expected is not None:
                index += 1
        if index != self.animated_count:
            raise ValueError("typography_animated_count_invalid")
        return self


def graphemes(text: str) -> list[str]:
    if regex.__version__ != SEGMENTER_VERSION:
        raise ValueError("typography_segmenter_version_mismatch")
    return _GRAPHEMES.findall(text)


def segment_text(text: str, unit: Literal["word", "character"]) -> TypographySegmentationV1:
    if regex.__version__ != SEGMENTER_VERSION:
        raise ValueError("typography_segmenter_version_mismatch")
    pieces = graphemes(text) if unit == "character" else _WORD_BLOCKS.findall(text)
    units = []
    index = 0
    for piece in pieces:
        whitespace = bool(_WHITE_SPACE.fullmatch(piece))
        units.append(TypographyUnitV1(text=piece, animation_index=None if whitespace else index))
        if not whitespace:
            index += 1
    if index == 0:
        raise ValueError("typography_visible_unit_required")
    return TypographySegmentationV1(
        unit=unit,
        text_checksum_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        units=units,
        animated_count=index,
    )


def validate_segmentation(payload, text: str, unit: Literal["word", "character"]) -> TypographySegmentationV1:
    stored = TypographySegmentationV1.model_validate(payload)
    if stored != segment_text(text, unit):
        raise ValueError("typography_segmentation_stale")
    return stored
