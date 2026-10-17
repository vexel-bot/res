from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import SHA256_PATTERN, StudioContract
from .intelligence import PlanningCopyRequestV1, PlanningCopyResultV1

AVATAR_CANDIDATE_IDS = {"lia", "maya", "nina", "caio", "theo", "bento"}


class UgcAvatarCatalogSlotV1(StudioContract):
    """Non-biometric catalog slot. It cannot authorize presenter inference."""

    candidate_id: Literal["lia", "maya", "nina", "caio", "theo", "bento"]
    display_name: str = Field(min_length=1, max_length=80)
    presentation: Literal["woman", "man"]
    direction: str = Field(min_length=1, max_length=240)
    catalog_only: Literal[True] = True
    production_eligible: Literal[False] = False
    identity_version_id: None = None
    voice_version_id: None = None


class UgcScenePlanV1(StudioContract):
    setting: str = Field(min_length=1, max_length=400)
    background_direction: str = Field(min_length=1, max_length=1000)
    lighting: str = Field(min_length=1, max_length=500)
    framing: str = Field(min_length=1, max_length=500)
    wardrobe: str = Field(min_length=1, max_length=500)
    props: list[str] = Field(default_factory=list, max_length=20)
    continuity_constraints: list[str] = Field(min_length=1, max_length=20)


class UgcDeliverablePlanV1(StudioContract):
    visual_width: Literal[1080] = 1080
    visual_height: Literal[1350] = 1350
    carousel_pages: int = Field(default=5, ge=3, le=10)
    carousel_width: Literal[1080] = 1080
    carousel_height: Literal[1350] = 1350
    video_width: Literal[1080] = 1080
    video_height: Literal[1920] = 1920
    video_duration_seconds: Literal[15, 20, 30]
    video_fps: Literal[25, 30] = 30


class UgcCopyExpectationV1(StudioContract):
    archetype: Literal["problem-solution", "demo", "offer", "education", "founder-led", "discovery"]
    required_hook: bool = True
    required_cta: bool = True
    minimum_storyboard_beats: int = Field(default=4, ge=3, le=12)
    required_terms: list[str] = Field(default_factory=list, max_length=20)
    forbidden_claims: list[str] = Field(default_factory=list, max_length=40)
    sensitive_category: Literal["none", "health", "finance"] = "none"
    unsupported_claims_require_human_review: Literal[True] = True


class UgcAdAcceptanceCaseV1(StudioContract):
    schema_version: Literal["studio.ugc-ad-acceptance-case.v1"] = "studio.ugc-ad-acceptance-case.v1"
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    niche: str = Field(min_length=1, max_length=160)
    concept: str = Field(min_length=1, max_length=240)
    avatar: UgcAvatarCatalogSlotV1
    scene: UgcScenePlanV1
    request: PlanningCopyRequestV1
    deliverables: UgcDeliverablePlanV1
    expectation: UgcCopyExpectationV1

    @model_validator(mode="after")
    def validate_request_binding(self) -> UgcAdAcceptanceCaseV1:
        if self.request.request_id != self.case_id:
            raise ValueError("UGC acceptance request id must match case id")
        if self.request.format != "ugc-ad-kit":
            raise ValueError("UGC acceptance cases must request the complete ad kit")
        context = self.request.production_context
        if context is None:
            raise ValueError("UGC acceptance cases require non-biometric production context")
        if context.target_duration_seconds != self.deliverables.video_duration_seconds:
            raise ValueError("UGC production duration must match deliverable duration")
        if context.avatar_catalog_slot != self.avatar.candidate_id:
            raise ValueError("UGC production context must bind the avatar catalog slot")
        if context.scene_setting != self.scene.setting:
            raise ValueError("UGC production context must bind the scene setting")
        return self


class UgcAdAcceptanceCasebookV1(StudioContract):
    schema_version: Literal["studio.ugc-ad-acceptance-casebook.v1"] = "studio.ugc-ad-acceptance-casebook.v1"
    suite_id: str = Field(min_length=1, max_length=160)
    status: Literal["frozen"] = "frozen"
    frozen_at: datetime
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    publication_enabled: Literal[False] = False
    real_biometric_data_allowed: Literal[False] = False
    cases: list[UgcAdAcceptanceCaseV1] = Field(min_length=10, max_length=10)

    @model_validator(mode="after")
    def validate_matrix(self) -> UgcAdAcceptanceCasebookV1:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("UGC acceptance case ids must be unique")
        candidate_ids = {case.avatar.candidate_id for case in self.cases}
        if candidate_ids != AVATAR_CANDIDATE_IDS:
            raise ValueError("UGC acceptance matrix must cover all six catalog slots")
        if len({case.niche for case in self.cases}) != 10:
            raise ValueError("UGC acceptance matrix must cover ten distinct niches")
        if not {case.expectation.sensitive_category for case in self.cases}.issuperset({"health", "finance"}):
            raise ValueError("UGC acceptance matrix must exercise health and finance safety")
        return self


class UgcCriterionResultV1(StudioContract):
    criterion_id: str = Field(min_length=1, max_length=120)
    status: Literal["pass", "fail", "blocked", "manual_review"]
    score: float | None = Field(default=None, ge=0, le=5)
    weight: float = Field(default=1, gt=0, le=10)
    evidence: list[str] = Field(default_factory=list, max_length=30)
    notes: list[str] = Field(default_factory=list, max_length=30)


class UgcArtifactEvidenceV1(StudioContract):
    artifact_type: Literal["planning-json", "visual-png", "carousel-zip", "animatic-mp4", "manifest-json"]
    path: str = Field(min_length=1, max_length=2000)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=1)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    duration_seconds: float | None = Field(default=None, gt=0)
    page_count: int | None = Field(default=None, ge=1)


class UgcCapabilityGateV1(StudioContract):
    capability: Literal[
        "planning_copy",
        "static_composition",
        "carousel_export",
        "video_animatic",
        "avatar_inference",
        "voice_clone",
        "lip_sync",
    ]
    status: Literal["executed", "blocked"]
    reason: str = Field(min_length=1, max_length=1000)


class UgcAdAcceptanceCaseResultV1(StudioContract):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    planning_result: PlanningCopyResultV1 | None = None
    criteria: list[UgcCriterionResultV1] = Field(min_length=1, max_length=100)
    artifacts: list[UgcArtifactEvidenceV1] = Field(default_factory=list, max_length=100)
    capability_gates: list[UgcCapabilityGateV1] = Field(min_length=7, max_length=7)
    weighted_score: float = Field(ge=0, le=5)
    automated_status: Literal["pass", "fail", "blocked"]
    human_review_required: Literal[True] = True


class UgcAdAcceptanceRunV1(StudioContract):
    schema_version: Literal["studio.ugc-ad-acceptance-run.v1"] = "studio.ugc-ad-acceptance-run.v1"
    suite_id: str = Field(min_length=1, max_length=160)
    run_id: str = Field(min_length=1, max_length=160)
    casebook_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    started_at: datetime
    completed_at: datetime
    results: list[UgcAdAcceptanceCaseResultV1] = Field(min_length=10, max_length=10)
    publication_enabled: Literal[False] = False
    production_avatar_claim_allowed: Literal[False] = False
