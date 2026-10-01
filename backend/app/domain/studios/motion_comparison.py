"""Evidence contract for comparing renderers without changing MotionGraph."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract


class MotionRendererRunV1(StudioContract):
    renderer_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,159}$")
    renderer_version: str = Field(min_length=1, max_length=160)
    projection_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    elapsed_milliseconds: int = Field(gt=0)
    technical_blockers: list[str] = Field(default_factory=list, max_length=100)
    human_scores: dict[Literal["clarity", "hierarchy", "naturalness", "fidelity"], int] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def score_range(self):
        if any(value < 1 or value > 5 for value in self.human_scores.values()):
            raise ValueError("motion_comparison_score_out_of_range")
        return self


class MotionComparisonCaseV1(StudioContract):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,159}$")
    capability: Literal[
        "accented_typography",
        "camera_and_groups",
        "cutout_and_occlusion",
        "bound_paths",
        "product_annotation",
        "element_continuity",
    ]
    source_graph_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    required_operations: list[str] = Field(min_length=1, max_length=50)
    runs: list[MotionRendererRunV1] = Field(default_factory=list, max_length=12)


class MotionRendererComparisonV1(StudioContract):
    schema_version: Literal["studio.motion-renderer-comparison.v1"] = (
        "studio.motion-renderer-comparison.v1"
    )
    suite_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,159}$")
    cases: list[MotionComparisonCaseV1] = Field(min_length=6, max_length=6)
    promoted_capabilities: dict[str, list[str]] = Field(default_factory=dict)
    human_review_complete: bool = False

    @model_validator(mode="after")
    def complete_case_set(self):
        expected = {
            "accented_typography",
            "camera_and_groups",
            "cutout_and_occlusion",
            "bound_paths",
            "product_annotation",
            "element_continuity",
        }
        actual = {case.capability for case in self.cases}
        if actual != expected or len({case.case_id for case in self.cases}) != 6:
            raise ValueError("motion_comparison_requires_six_distinct_cases")
        if self.promoted_capabilities and not self.human_review_complete:
            raise ValueError("motion_comparison_promotion_requires_human_review")
        return self
