from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.domain.studios.factory_pre_review import (
    FactoryMachinePreReviewSuiteV1,
    assert_machine_pre_review_allows_human_quality_review,
)
from app.domain.studios.video_factory import (
    FactoryHumanReviewPacketV1,
    FactoryInfrastructureCostPolicyV1,
    VideoFactoryProgramEvidenceV1,
    apply_factory_review_packet,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, default=FACTORY_ROOT / "program-manifest.json")
    parser.add_argument(
        "--pre-review",
        type=Path,
        default=FACTORY_ROOT / "machine-pre-review.json",
    )
    parser.add_argument(
        "--reviews",
        type=Path,
        default=FACTORY_ROOT / "human-review-decisions.json",
    )
    parser.add_argument(
        "--cost-policy",
        type=Path,
        default=FACTORY_ROOT / "infrastructure-cost-policy.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=FACTORY_ROOT / "reviewed-program-manifest.json",
    )
    args = parser.parse_args()
    program = VideoFactoryProgramEvidenceV1.model_validate_json(
        args.program.read_text(encoding="utf-8")
    )
    pre_review = FactoryMachinePreReviewSuiteV1.model_validate_json(
        args.pre_review.read_text(encoding="utf-8")
    )
    assert_machine_pre_review_allows_human_quality_review(pre_review)
    packet = FactoryHumanReviewPacketV1.model_validate_json(
        args.reviews.read_text(encoding="utf-8")
    )
    cost_policy = FactoryInfrastructureCostPolicyV1.model_validate_json(
        args.cost_policy.read_text(encoding="utf-8")
    )
    jobs = {
        job.job_id: job
        for wave in (program.pilot, program.calibration, program.scale)
        for job in wave.jobs
    }
    for review in packet.reviews:
        job = jobs.get(review.job_id)
        if job is None or not job.artifact_path:
            raise ValueError(f"review_job_artifact_missing:{review.job_id}")
        artifact = (REPOSITORY_ROOT / job.artifact_path).resolve()
        if not artifact.is_relative_to(REPOSITORY_ROOT) or not artifact.is_file():
            raise ValueError(f"review_job_artifact_unavailable:{review.job_id}")
        if sha256(artifact) != review.artifact_digest_sha256:
            raise ValueError(f"review_job_artifact_digest_mismatch:{review.job_id}")
    reviewed = apply_factory_review_packet(program, packet, cost_policy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(reviewed.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "humanApproved": reviewed.human_approved_count,
                "pilotPromoted": reviewed.pilot.promotion_eligible,
                "calibrationPromoted": reviewed.calibration.promotion_eligible,
                "scalePromoted": reviewed.scale.promotion_eligible,
                "programCompleted": reviewed.completed,
            }
        )
    )


if __name__ == "__main__":
    main()
