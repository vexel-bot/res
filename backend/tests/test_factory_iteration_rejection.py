from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.domain.studios.video_factory import (
    FactoryIterationRejectionV1,
    VideoFactoryProgramEvidenceV1,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
)


def test_rejected_iteration_is_durable_and_cannot_promote() -> None:
    program = VideoFactoryProgramEvidenceV1.model_validate_json(
        (FACTORY_ROOT / "current-program-manifest.json").read_text(encoding="utf-8")
    )
    record = FactoryIterationRejectionV1.model_validate_json(
        (FACTORY_ROOT / "iteration-rejection-20260901-v1.json").read_text(
            encoding="utf-8"
        )
    )
    reviewed_jobs = [*program.pilot.jobs, *program.calibration.jobs]

    assert len(record.rejected_job_ids) == 36
    assert all(job.human_review_status == "rejected" for job in reviewed_jobs)
    assert program.human_approved_count == 0
    assert program.pilot.promotion_eligible is False
    assert program.calibration.promotion_eligible is False
    assert program.scale.promotion_eligible is False
    assert all(job.attempts == 0 for job in program.scale.jobs)
    assert program.external_publication_count == 0
    assert "creative_replan_required" in program.blockers
    assert all(job.human_reviewed_by == "workspace-owner" for job in reviewed_jobs)
    payload = program.model_dump(mode="json", by_alias=True)
    digest = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert record.rejected_program_digest_sha256 == digest
