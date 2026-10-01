"""Version-bound editorial gates, separate from technical QC and publication."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import SHA256_PATTERN, StudioContract

EditorialAxis = Literal["proof", "script", "storyboard", "animatic", "voice", "face", "scenario"]
EDITORIAL_AXES: tuple[EditorialAxis, ...] = (
    "proof", "script", "storyboard", "animatic", "voice", "face", "scenario",
)


class EditorialBeatV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    visual_action: str = Field(min_length=1, max_length=2000)
    edit_reason: str = Field(min_length=1, max_length=2000)
    evidence_asset_ids: list[str] = Field(min_length=1, max_length=20)


class EditorialPlanRequestV1(StudioContract):
    expected_document_revision: int = Field(ge=1)
    workflow: Literal["ugc-avatar"] = "ugc-avatar"
    objective: str = Field(min_length=1, max_length=2000)
    cta: str = Field(min_length=1, max_length=1000)
    beats: list[EditorialBeatV1] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def unique_beats(self) -> EditorialPlanRequestV1:
        if len({beat.id for beat in self.beats}) != len(self.beats):
            raise ValueError("editorial_duplicate_beat")
        return self


class EditorialPlanV1(StudioContract):
    schema_version: Literal["studio.editorial-plan.v1"] = "studio.editorial-plan.v1"
    id: str
    workspace_id: str
    document_id: str
    document_revision: int
    document_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    assets_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    plan: EditorialPlanRequestV1
    created_by: str
    created_at: datetime


class EditorialReviewRequestV1(StudioContract):
    plan_id: str = Field(min_length=1, max_length=120)
    axis: EditorialAxis
    decision: Literal["approved", "rejected"]
    evidence_asset_ids: list[str] = Field(min_length=1, max_length=20)
    notes: str = Field(min_length=1, max_length=4000)


class EditorialReviewV1(StudioContract):
    id: str
    review: EditorialReviewRequestV1
    reviewed_by: str
    reviewed_at: datetime


class EditorialReadinessV1(StudioContract):
    schema_version: Literal["studio.editorial-readiness.v1"] = "studio.editorial-readiness.v1"
    managed: bool
    plan: EditorialPlanV1 | None = None
    reviews: list[EditorialReviewV1] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    full_render_eligible: bool = False
    publication_authorized: Literal[False] = False
