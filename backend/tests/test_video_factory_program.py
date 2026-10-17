from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.creative_autonomy import CreativePilotCasebookV1
from app.domain.studios.video_factory import (
    FactoryHumanReviewPacketV1,
    FactoryInfrastructureCostPolicyV1,
    VideoFactoryJobV1,
    VideoFactoryProgramEvidenceV1,
    VideoFactoryWaveEvidenceV1,
    apply_factory_review_packet,
    assert_factory_wave_dispatchable,
    record_factory_job_review,
    request_factory_job_cancel,
    retry_factory_job,
)
from scripts.dispatch_scale_video_factory import build_scale_work

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROGRAM_PATH = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
    / "program-manifest.json"
)
CASEBOOK_PATH = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "studios"
    / "creative"
    / "video-creative-pilot-casebook.v1.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def program() -> VideoFactoryProgramEvidenceV1:
    return VideoFactoryProgramEvidenceV1.model_validate_json(
        PROGRAM_PATH.read_text(encoding="utf-8")
    )


def test_factory_materializes_12_plus_24_and_hard_blocks_scale_64() -> None:
    evidence = program()

    assert len(evidence.pilot.jobs) == 12
    assert len(evidence.calibration.jobs) == 24
    assert len(evidence.scale.jobs) == 64
    assert evidence.produced_artifact_count == 36
    assert evidence.human_approved_count == 0
    assert evidence.external_publication_count == 0
    assert evidence.completed is False
    assert evidence.pilot.technical_eligible is True
    assert evidence.calibration.technical_eligible is True
    assert evidence.pilot.promotion_eligible is False
    assert evidence.calibration.promotion_eligible is False
    for wave in (evidence.pilot, evidence.calibration):
        for job in wave.jobs:
            assert job.status == "succeeded"
            assert job.human_review_status == "pending"
            assert job.artifact_path and job.artifact_digest_sha256
            artifact = REPOSITORY_ROOT / job.artifact_path
            assert artifact.is_file() and artifact.stat().st_size > 10_000
            assert _sha256(artifact) == job.artifact_digest_sha256
            assert job.publication_authorized is False
            assert job.identity_synthesis_authorized is False
            assert job.voice_synthesis_authorized is False
    assert all(job.status == "blocked_by_gate" for job in evidence.scale.jobs)
    assert all(job.attempts == 0 and not job.artifact_path for job in evidence.scale.jobs)
    with pytest.raises(ValueError, match="not promoted"):
        assert_factory_wave_dispatchable(
            evidence.scale,
            [evidence.pilot, evidence.calibration],
        )


def test_factory_cancel_retry_and_idempotency_invariants() -> None:
    evidence = program()
    source = evidence.pilot.jobs[0]
    queued = VideoFactoryJobV1.model_validate(
        {
            **source.model_dump(mode="json", by_alias=True),
            "status": "queued",
            "technicalQcPassed": False,
            "blockers": [],
        }
    )

    cancelled = request_factory_job_cancel(queued)
    retried = retry_factory_job(cancelled)

    assert cancelled.status == "cancelled" and cancelled.cancel_requested is True
    assert retried.status == "retrying" and retried.cancel_requested is False
    assert retried.retry_of_job_id == queued.job_id
    assert retried.idempotency_key == queued.idempotency_key
    assert retried.rollback_recipe_id == queued.rollback_recipe_id
    assert retried.rollback_provider == queued.rollback_provider

    reviewed = record_factory_job_review(
        source,
        decision="approved",
        review_id="human-review-pilot-001",
        reviewed_by="reviewer-001",
        reviewed_at=evidence.evaluated_at,
        notes="Artifact reviewed against its exact checksum.",
    )
    assert reviewed.human_review_status == "approved"
    assert reviewed.human_review_id == "human-review-pilot-001"
    with pytest.raises(ValueError, match="already has"):
        record_factory_job_review(
            reviewed,
            decision="rejected",
            review_id="human-review-pilot-002",
            reviewed_by="reviewer-002",
            reviewed_at=evidence.evaluated_at,
            notes="Second decision must be rejected as duplicate.",
        )

    payload = evidence.pilot.model_dump(mode="json", by_alias=True)
    payload["jobs"][1]["idempotencyKey"] = payload["jobs"][0]["idempotencyKey"]
    with pytest.raises(ValidationError, match="idempotency"):
        VideoFactoryWaveEvidenceV1.model_validate(payload)


def test_review_import_promotes_12_and_24_but_not_undispatched_scale() -> None:
    evidence = program()
    jobs = [*evidence.pilot.jobs, *evidence.calibration.jobs]
    packet = FactoryHumanReviewPacketV1.model_validate(
        {
            "programId": evidence.program_id,
            "instructions": "Synthetic contract test only; it does not mutate production evidence.",
            "reviews": [
                {
                    "jobId": job.job_id,
                    "artifactDigestSha256": job.artifact_digest_sha256,
                    "decision": "approved",
                    "reviewId": f"test-review-{index:03d}",
                    "reviewedBy": "test-reviewer",
                    "reviewedAt": evidence.evaluated_at,
                    "notes": "Exact artifact reviewed in the contract fixture.",
                }
                for index, job in enumerate(jobs, start=1)
            ],
        }
    )
    cost_policy = FactoryInfrastructureCostPolicyV1(
        policy_id="test-local-cpu-cost-v1",
        cpu_hourly_cost_usd=0.08,
        calculation_method="Fixture rate multiplied by measured render wall time.",
        approved_by="test-governance-reviewer",
        approved_at=evidence.evaluated_at,
    )

    reviewed = apply_factory_review_packet(evidence, packet, cost_policy)

    assert reviewed.human_approved_count == 36
    assert reviewed.pilot.promotion_eligible is True
    assert reviewed.calibration.promotion_eligible is True
    assert reviewed.scale.promotion_eligible is False
    assert reviewed.completed is False
    assert "scale_64_not_dispatched_by_hard_gate" in reviewed.blockers
    assert reviewed.pilot.infrastructure_cost_usd > 0
    assert reviewed.pilot.cost_policy_id == cost_policy.policy_id

    tampered = packet.model_dump(mode="json", by_alias=True)
    tampered["reviews"][0]["artifactDigestSha256"] = "f" * 64
    with pytest.raises(ValueError, match="artifact digest mismatch"):
        apply_factory_review_packet(
            evidence,
            FactoryHumanReviewPacketV1.model_validate(tampered),
            cost_policy,
        )


def test_scale_dispatch_plan_has_64_stable_jobs_across_all_cases_and_variants() -> None:
    casebook = CreativePilotCasebookV1.model_validate_json(
        CASEBOOK_PATH.read_text(encoding="utf-8")
    )

    work = build_scale_work(casebook)

    assert len(work) == 64
    assert [ordinal for _case, _variant, ordinal in work] == list(range(1, 65))
    assert {variant for _case, variant, _ordinal in work} == {0, 1, 2}
    assert {case.case_id for case, _variant, _ordinal in work} == {
        case.case_id for case in casebook.cases
    }
