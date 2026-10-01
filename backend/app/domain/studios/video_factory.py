from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract
from .creative_autonomy import VideoFamilyV1

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"

FactoryWaveNameV1 = Literal["pilot_12", "calibration_24", "scale_64"]
FactoryJobStatusV1 = Literal[
    "queued",
    "running",
    "retrying",
    "succeeded",
    "failed",
    "cancelled",
    "blocked_by_gate",
]


class VideoFactoryBudgetV1(StudioContract):
    max_direct_cost_usd: float = Field(ge=0, le=1_000_000)
    max_infrastructure_cost_usd: float = Field(default=1_000, ge=0, le=1_000_000)
    max_wall_time_seconds: int = Field(gt=0, le=604_800)
    max_concurrent_jobs: int = Field(ge=1, le=64)
    rate_limit_jobs_per_minute: int = Field(ge=1, le=10_000)
    max_attempts_per_job: int = Field(ge=1, le=10)
    stop_on_budget_exceeded: Literal[True] = True


class VideoFactoryJobV1(StudioContract):
    job_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    wave: FactoryWaveNameV1
    ordinal: int = Field(ge=1, le=100)
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    family: VideoFamilyV1
    recipe_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    recipe_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    idempotency_key: str = Field(pattern=OPAQUE_ID_PATTERN)
    capability: Literal["media_cpu", "motion_browser"]
    provider: Literal["builtin.ffmpeg-calibration-v1", "hyperframes.cli"]
    provider_version: str = Field(min_length=1, max_length=240)
    status: FactoryJobStatusV1
    attempts: int = Field(ge=0, le=10)
    max_attempts: int = Field(ge=1, le=10)
    source_artifact_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    artifact_path: str | None = Field(default=None, max_length=4000)
    artifact_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    render_duration_milliseconds: int | None = Field(default=None, ge=0)
    direct_cost_usd: float = Field(ge=0)
    technical_qc_passed: bool = False
    human_review_status: Literal[
        "pending", "approved", "changes_requested", "rejected"
    ] = "pending"
    human_review_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    human_reviewed_by: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    human_reviewed_at: datetime | None = None
    human_review_notes: str | None = Field(default=None, max_length=4000)
    publication_authorized: Literal[False] = False
    identity_synthesis_authorized: Literal[False] = False
    voice_synthesis_authorized: Literal[False] = False
    cancel_requested: bool = False
    retry_of_job_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    rollback_recipe_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    rollback_provider: Literal[
        "builtin.ffmpeg-calibration-v1", "hyperframes.cli"
    ]
    blockers: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_job(self) -> VideoFactoryJobV1:
        if self.attempts > self.max_attempts:
            raise ValueError("Factory job attempts exceed its retry budget")
        if self.status == "succeeded":
            if not all(
                (
                    self.artifact_path,
                    self.artifact_digest_sha256,
                    self.source_artifact_digest_sha256,
                    self.render_duration_milliseconds is not None,
                    self.technical_qc_passed,
                )
            ):
                raise ValueError("Succeeded factory jobs require artifact, lineage and QC")
            if self.blockers:
                raise ValueError("Succeeded factory jobs cannot retain technical blockers")
        if self.status == "blocked_by_gate" and not self.blockers:
            raise ValueError("Gate-blocked factory jobs require explicit blockers")
        review_bindings = (
            self.human_review_id,
            self.human_reviewed_by,
            self.human_reviewed_at,
            self.human_review_notes,
        )
        if self.human_review_status != "pending" and not all(review_bindings):
            raise ValueError("Human review decisions require durable review metadata")
        if self.human_review_status == "pending" and any(review_bindings):
            raise ValueError("Pending human reviews cannot contain decision metadata")
        if self.status != "succeeded" and self.human_review_status == "approved":
            raise ValueError("Only succeeded factory jobs may be approved")
        return self


class VideoFactoryWaveEvidenceV1(StudioContract):
    schema_version: Literal["studio.video-factory-wave-evidence.v1"] = (
        "studio.video-factory-wave-evidence.v1"
    )
    wave_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    wave: FactoryWaveNameV1
    source_casebook_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    prerequisite_wave_ids: list[str] = Field(default_factory=list, max_length=10)
    budget: VideoFactoryBudgetV1
    jobs: list[VideoFactoryJobV1]
    direct_cost_usd: float = Field(ge=0)
    infrastructure_cost_usd: float = Field(default=0, ge=0)
    cost_policy_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    wall_time_milliseconds: int = Field(ge=0)
    technical_eligible: bool
    promotion_eligible: bool
    blockers: list[str] = Field(default_factory=list, max_length=100)
    started_at: datetime
    completed_at: datetime

    @model_validator(mode="after")
    def validate_wave(self) -> VideoFactoryWaveEvidenceV1:
        expected_count = {"pilot_12": 12, "calibration_24": 24, "scale_64": 64}[self.wave]
        if len(self.jobs) != expected_count:
            raise ValueError(f"Factory wave {self.wave} requires exactly {expected_count} jobs")
        ids = [item.job_id for item in self.jobs]
        idempotency_keys = [item.idempotency_key for item in self.jobs]
        ordinals = [item.ordinal for item in self.jobs]
        if len(ids) != len(set(ids)) or len(idempotency_keys) != len(set(idempotency_keys)):
            raise ValueError("Factory job and idempotency ids must be unique")
        if ordinals != list(range(1, expected_count + 1)):
            raise ValueError("Factory job ordinals must be contiguous")
        if any(item.wave != self.wave for item in self.jobs):
            raise ValueError("Factory jobs must belong to their declared wave")
        calculated_cost = round(sum(item.direct_cost_usd for item in self.jobs), 6)
        if abs(calculated_cost - self.direct_cost_usd) > 0.000001:
            raise ValueError("Factory wave cost disagrees with job receipts")
        if self.direct_cost_usd > self.budget.max_direct_cost_usd:
            raise ValueError("Factory wave exceeded its direct cost budget")
        if self.infrastructure_cost_usd > self.budget.max_infrastructure_cost_usd:
            raise ValueError("Factory wave exceeded its infrastructure cost budget")
        if self.wall_time_milliseconds > self.budget.max_wall_time_seconds * 1000:
            raise ValueError("Factory wave exceeded its wall-time budget")
        expected_technical = all(
            item.status == "succeeded" and item.technical_qc_passed for item in self.jobs
        )
        expected_promotion = (
            expected_technical
            and all(
                item.human_review_status == "approved" and item.human_review_id
                for item in self.jobs
            )
            and self.cost_policy_id is not None
            and not self.blockers
        )
        if self.technical_eligible != expected_technical:
            raise ValueError("Factory technical eligibility disagrees with job evidence")
        if self.promotion_eligible != bool(expected_promotion):
            raise ValueError("Factory promotion eligibility disagrees with human review evidence")
        if self.promotion_eligible and self.blockers:
            raise ValueError("Promoted factory wave cannot retain blockers")
        return self


class VideoFactoryProgramEvidenceV1(StudioContract):
    schema_version: Literal["studio.video-factory-program-evidence.v1"] = (
        "studio.video-factory-program-evidence.v1"
    )
    program_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    pilot: VideoFactoryWaveEvidenceV1
    calibration: VideoFactoryWaveEvidenceV1
    scale: VideoFactoryWaveEvidenceV1
    produced_artifact_count: int = Field(ge=0, le=100)
    human_approved_count: int = Field(ge=0, le=100)
    external_publication_count: Literal[0] = 0
    eligible_for_external_publication: Literal[False] = False
    completed: bool
    blockers: list[str] = Field(default_factory=list, max_length=100)
    evaluated_at: datetime

    @model_validator(mode="after")
    def validate_program(self) -> VideoFactoryProgramEvidenceV1:
        waves = (self.pilot, self.calibration, self.scale)
        produced = sum(
            item.status == "succeeded" and item.artifact_path is not None
            for wave in waves
            for item in wave.jobs
        )
        approved = sum(
            item.human_review_status == "approved" for wave in waves for item in wave.jobs
        )
        if self.produced_artifact_count != produced or self.human_approved_count != approved:
            raise ValueError("Factory program counts disagree with wave evidence")
        expected_completed = all(wave.promotion_eligible for wave in waves)
        if self.completed != expected_completed:
            raise ValueError("Factory completion requires every promoted wave")
        return self


class FactoryHumanReviewDecisionV1(StudioContract):
    job_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    artifact_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    decision: Literal["pending", "approved", "changes_requested", "rejected"]
    review_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    reviewed_by: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    reviewed_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_decision(self) -> FactoryHumanReviewDecisionV1:
        bindings = (self.review_id, self.reviewed_by, self.reviewed_at, self.notes)
        if self.decision == "pending" and any(bindings):
            raise ValueError("Pending factory reviews cannot contain forged review metadata")
        if self.decision != "pending" and not all(bindings):
            raise ValueError("Factory review decisions require id, reviewer, timestamp and notes")
        return self


class FactoryHumanReviewPacketV1(StudioContract):
    schema_version: Literal["clicko.video-factory-human-review-packet.v1"] = (
        "clicko.video-factory-human-review-packet.v1"
    )
    program_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    instructions: str = Field(min_length=1, max_length=4000)
    reviews: list[FactoryHumanReviewDecisionV1] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_packet(self) -> FactoryHumanReviewPacketV1:
        ids = [item.job_id for item in self.reviews]
        review_ids = [item.review_id for item in self.reviews if item.review_id]
        if len(ids) != len(set(ids)):
            raise ValueError("Factory review packet job ids must be unique")
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("Factory human review ids must be unique")
        return self


class FactoryInfrastructureCostPolicyV1(StudioContract):
    schema_version: Literal["studio.factory-infrastructure-cost-policy.v1"] = (
        "studio.factory-infrastructure-cost-policy.v1"
    )
    policy_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    cpu_hourly_cost_usd: float = Field(ge=0, le=10_000)
    calculation_method: str = Field(min_length=1, max_length=2000)
    approved_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    approved_at: datetime


class FactoryIterationRejectionV1(StudioContract):
    schema_version: Literal["studio.factory-iteration-rejection.v1"] = (
        "studio.factory-iteration-rejection.v1"
    )
    rejection_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    program_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    scope: Literal["pilot_12_and_calibration_24"] = "pilot_12_and_calibration_24"
    rejected_job_ids: list[str] = Field(min_length=36, max_length=36)
    reason: str = Field(min_length=1, max_length=4000)
    reviewed_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    reviewed_at: datetime
    rejected_program_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    preserved_as_technical_evidence: Literal[True] = True
    promotion_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    replan_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_rejection(self) -> FactoryIterationRejectionV1:
        if len(self.rejected_job_ids) != len(set(self.rejected_job_ids)):
            raise ValueError("Iteration rejection job ids must be unique")
        return self


def apply_factory_review_packet(
    program: VideoFactoryProgramEvidenceV1,
    packet: FactoryHumanReviewPacketV1,
    cost_policy: FactoryInfrastructureCostPolicyV1,
) -> VideoFactoryProgramEvidenceV1:
    if packet.program_id != program.program_id:
        raise ValueError("Factory review packet program id does not match")
    if any(item.decision == "pending" for item in packet.reviews):
        raise ValueError("Factory review packet still contains pending decisions")
    decisions = {item.job_id: item for item in packet.reviews}
    all_jobs = {
        job.job_id: job
        for wave in (program.pilot, program.calibration, program.scale)
        for job in wave.jobs
    }
    unknown = sorted(set(decisions) - set(all_jobs))
    if unknown:
        raise ValueError(f"Factory review packet references unknown jobs: {unknown}")
    for job_id, decision in decisions.items():
        job = all_jobs[job_id]
        if not job.artifact_digest_sha256:
            raise ValueError(f"Factory review job has no artifact: {job_id}")
        if decision.artifact_digest_sha256 != job.artifact_digest_sha256:
            raise ValueError(f"Factory review artifact digest mismatch: {job_id}")

    def update_wave(wave: VideoFactoryWaveEvidenceV1) -> VideoFactoryWaveEvidenceV1:
        jobs = []
        for job in wave.jobs:
            decision = decisions.get(job.job_id)
            if decision is None:
                jobs.append(job)
                continue
            jobs.append(
                record_factory_job_review(
                    job,
                    decision=decision.decision,
                    review_id=decision.review_id or "",
                    reviewed_by=decision.reviewed_by or "",
                    reviewed_at=decision.reviewed_at,
                    notes=decision.notes or "",
                )
            )
        pending = [job.job_id for job in jobs if job.human_review_status == "pending"]
        rejected = [job.job_id for job in jobs if job.human_review_status == "rejected"]
        changes = [
            job.job_id for job in jobs if job.human_review_status == "changes_requested"
        ]
        blockers = []
        if pending:
            blockers.append(f"human_reviews_pending:{len(pending)}")
        if changes:
            blockers.append(f"human_changes_requested:{len(changes)}")
        if rejected:
            blockers.append(f"human_rejections:{len(rejected)}")
        infrastructure_cost = round(
            sum((job.render_duration_milliseconds or 0) for job in jobs)
            / 3_600_000
            * cost_policy.cpu_hourly_cost_usd,
            6,
        )
        payload = wave.model_dump(mode="json", by_alias=True)
        payload.update(
            {
                "jobs": [job.model_dump(mode="json", by_alias=True) for job in jobs],
                "infrastructureCostUsd": infrastructure_cost,
                "costPolicyId": cost_policy.policy_id,
                "technicalEligible": all(
                    job.status == "succeeded" and job.technical_qc_passed for job in jobs
                ),
                "promotionEligible": not blockers
                and all(job.human_review_status == "approved" for job in jobs),
                "blockers": blockers,
            }
        )
        return VideoFactoryWaveEvidenceV1.model_validate(payload)

    pilot = update_wave(program.pilot)
    calibration = update_wave(program.calibration)
    scale = update_wave(program.scale)
    waves = (pilot, calibration, scale)
    produced = sum(
        job.status == "succeeded" and job.artifact_path is not None
        for wave in waves
        for job in wave.jobs
    )
    approved = sum(
        job.human_review_status == "approved" for wave in waves for job in wave.jobs
    )
    completed = all(wave.promotion_eligible for wave in waves)
    blockers = [
        blocker
        for wave in waves
        for blocker in wave.blockers
    ]
    if not scale.technical_eligible:
        blockers.append("scale_64_not_dispatched_by_hard_gate")
    payload = program.model_dump(mode="json", by_alias=True)
    payload.update(
        {
            "pilot": pilot.model_dump(mode="json", by_alias=True),
            "calibration": calibration.model_dump(mode="json", by_alias=True),
            "scale": scale.model_dump(mode="json", by_alias=True),
            "producedArtifactCount": produced,
            "humanApprovedCount": approved,
            "completed": completed,
            "blockers": sorted(set(blockers)),
            "evaluatedAt": datetime.now(program.evaluated_at.tzinfo),
        }
    )
    return VideoFactoryProgramEvidenceV1.model_validate(payload)


def reject_factory_iteration(
    program: VideoFactoryProgramEvidenceV1,
    *,
    rejection_id: str,
    reviewed_by: str,
    reviewed_at: datetime,
    reason: str,
) -> VideoFactoryProgramEvidenceV1:
    """Reject the current 12+24 iteration without deleting its technical evidence."""

    def reject_wave(wave: VideoFactoryWaveEvidenceV1) -> VideoFactoryWaveEvidenceV1:
        if wave.wave == "scale_64":
            return wave
        jobs = []
        for job in wave.jobs:
            if job.human_review_status == "rejected":
                jobs.append(job)
                continue
            if job.human_review_status != "pending":
                raise ValueError(f"Factory job already has a review decision: {job.job_id}")
            jobs.append(
                record_factory_job_review(
                    job,
                    decision="rejected",
                    review_id=f"{rejection_id}-{wave.wave}-{job.ordinal:03d}",
                    reviewed_by=reviewed_by,
                    reviewed_at=reviewed_at,
                    notes=reason,
                )
            )
        payload = wave.model_dump(mode="json", by_alias=True)
        payload.update(
            {
                "jobs": [job.model_dump(mode="json", by_alias=True) for job in jobs],
                "technicalEligible": all(
                    job.status == "succeeded" and job.technical_qc_passed for job in jobs
                ),
                "promotionEligible": False,
                "blockers": ["iteration_rejected", f"human_rejections:{len(jobs)}"],
            }
        )
        return VideoFactoryWaveEvidenceV1.model_validate(payload)

    pilot = reject_wave(program.pilot)
    calibration = reject_wave(program.calibration)
    scale = reject_wave(program.scale)
    waves = (pilot, calibration, scale)
    payload = program.model_dump(mode="json", by_alias=True)
    payload.update(
        {
            "pilot": pilot.model_dump(mode="json", by_alias=True),
            "calibration": calibration.model_dump(mode="json", by_alias=True),
            "scale": scale.model_dump(mode="json", by_alias=True),
            "producedArtifactCount": sum(
                job.status == "succeeded" and job.artifact_path is not None
                for wave in waves
                for job in wave.jobs
            ),
            "humanApprovedCount": 0,
            "completed": False,
            "blockers": sorted(
                {
                    "iteration_rejected",
                    "creative_replan_required",
                    "scale_64_not_dispatched_by_hard_gate",
                    *(blocker for wave in waves for blocker in wave.blockers),
                }
            ),
            "evaluatedAt": reviewed_at,
        }
    )
    return VideoFactoryProgramEvidenceV1.model_validate(payload)


def request_factory_job_cancel(job: VideoFactoryJobV1) -> VideoFactoryJobV1:
    if job.status not in {"queued", "running", "retrying"}:
        raise ValueError("Only active factory jobs can be cancelled")
    return VideoFactoryJobV1.model_validate(
        {
            **job.model_dump(mode="json", by_alias=True),
            "status": "cancelled",
            "cancelRequested": True,
            "blockers": [*job.blockers, "cancelled_by_operator"],
        }
    )


def retry_factory_job(job: VideoFactoryJobV1) -> VideoFactoryJobV1:
    if job.status not in {"failed", "cancelled"}:
        raise ValueError("Only failed or cancelled factory jobs can be retried")
    if job.attempts >= job.max_attempts:
        raise ValueError("Factory job retry budget exhausted")
    return VideoFactoryJobV1.model_validate(
        {
            **job.model_dump(mode="json", by_alias=True),
            "status": "retrying",
            "attempts": job.attempts + 1,
            "cancelRequested": False,
            "retryOfJobId": job.job_id,
            "blockers": [],
        }
    )


def record_factory_job_review(
    job: VideoFactoryJobV1,
    *,
    decision: Literal["approved", "changes_requested", "rejected"],
    review_id: str,
    reviewed_by: str,
    reviewed_at: datetime | None,
    notes: str,
) -> VideoFactoryJobV1:
    if job.status != "succeeded" or not job.technical_qc_passed:
        raise ValueError("Only technically succeeded factory jobs may receive human review")
    if job.human_review_status != "pending":
        raise ValueError("Factory job already has a human review decision")
    return VideoFactoryJobV1.model_validate(
        {
            **job.model_dump(mode="json", by_alias=True),
            "humanReviewStatus": decision,
            "humanReviewId": review_id,
            "humanReviewedBy": reviewed_by,
            "humanReviewedAt": reviewed_at,
            "humanReviewNotes": notes,
        }
    )


def assert_factory_wave_dispatchable(
    wave: VideoFactoryWaveEvidenceV1,
    prerequisite_waves: list[VideoFactoryWaveEvidenceV1],
) -> None:
    evidence = {item.wave_id: item for item in prerequisite_waves}
    missing = [item for item in wave.prerequisite_wave_ids if item not in evidence]
    if missing:
        raise ValueError(f"Factory prerequisite wave evidence missing: {missing}")
    unapproved = [
        wave_id
        for wave_id in wave.prerequisite_wave_ids
        if not evidence[wave_id].promotion_eligible
    ]
    if unapproved:
        raise ValueError(f"Factory prerequisite wave not promoted: {unapproved}")
