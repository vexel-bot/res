from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"


class FactoryMachinePreReviewV1(StudioContract):
    job_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    artifact_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    source_animatic_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    verdict: Literal["ready_for_human_quality_review", "storyboard_review_only", "reject"]
    flags: list[
        Literal[
            "source_is_placeholder_animatic",
            "no_authorized_footage",
            "no_final_audio_mix",
            "no_final_motion_composition",
            "not_a_final_edit",
        ]
    ] = Field(min_length=1, max_length=5)
    reviewable_dimensions: list[
        Literal["message", "beat_order", "copy", "shot_intent", "final_audiovisual_quality"]
    ] = Field(min_length=1, max_length=5)
    final_edit_claimed: Literal[False] = False
    human_review_replaced: Literal[False] = False
    recommendation: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_review(self) -> FactoryMachinePreReviewV1:
        if self.verdict == "storyboard_review_only":
            if "source_is_placeholder_animatic" not in self.flags:
                raise ValueError("Storyboard-only pre-review requires placeholder provenance")
            if "final_audiovisual_quality" in self.reviewable_dimensions:
                raise ValueError("Placeholder animatics cannot be reviewed as final audiovisual quality")
        return self


class FactoryMachinePreReviewSuiteV1(StudioContract):
    schema_version: Literal["studio.factory-machine-pre-review-suite.v1"] = (
        "studio.factory-machine-pre-review-suite.v1"
    )
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    reviews: list[FactoryMachinePreReviewV1] = Field(min_length=12, max_length=12)
    ready_for_final_human_review_count: int = Field(ge=0, le=12)
    storyboard_review_only_count: int = Field(ge=0, le=12)
    promotion_eligible: bool
    blockers: list[str] = Field(min_length=1, max_length=100)
    reviewed_at: datetime

    @model_validator(mode="after")
    def validate_suite(self) -> FactoryMachinePreReviewSuiteV1:
        ids = [item.job_id for item in self.reviews]
        if len(ids) != len(set(ids)):
            raise ValueError("Machine pre-review job ids must be unique")
        ready = sum(
            item.verdict == "ready_for_human_quality_review" for item in self.reviews
        )
        storyboard = sum(item.verdict == "storyboard_review_only" for item in self.reviews)
        if ready != self.ready_for_final_human_review_count:
            raise ValueError("Machine pre-review ready count disagrees with reviews")
        if storyboard != self.storyboard_review_only_count:
            raise ValueError("Machine storyboard-only count disagrees with reviews")
        expected = ready == len(self.reviews) and not self.blockers
        if self.promotion_eligible != expected:
            raise ValueError("Machine pre-review promotion eligibility disagrees with evidence")
        return self


def assert_machine_pre_review_allows_human_quality_review(
    suite: FactoryMachinePreReviewSuiteV1,
) -> None:
    if not suite.promotion_eligible:
        raise ValueError("machine_pre_review_blocks_final_human_review")
    if suite.ready_for_final_human_review_count != len(suite.reviews):
        raise ValueError("machine_pre_review_not_all_pilots_ready")
