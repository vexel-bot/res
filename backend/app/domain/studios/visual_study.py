"""Comparison receipts reuse canonical render references, never a new project."""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract
from .engine_qualification import EngineRenderReferenceV1


class CreateVisualStudyComparisonV1(StudioContract):
    variants: list[EngineRenderReferenceV1] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def distinct(self):
        if len({ref.asset_id for ref in self.variants}) != 3:
            raise ValueError("visual_study_three_distinct_renders_required")
        return self


class VisualStudyComparisonReviewV1(StudioContract):
    preferred_label: Literal["A", "B", "C"]
    full_video_inspected: bool
    mobile_inspected: bool
    blind_review_completed: bool
    same_materials_confirmed: bool
    control_simplicity_confirmed: bool
    unrecorded_manual_corrections: bool
    notes: str = Field(min_length=1, max_length=4000)
