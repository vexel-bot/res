from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.video_factory import (
    FactoryIterationRejectionV1,
    VideoFactoryProgramEvidenceV1,
    reject_factory_iteration,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
)


def canonical_digest(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, default=FACTORY_ROOT / "program-manifest.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=FACTORY_ROOT / "current-program-manifest.json",
    )
    parser.add_argument(
        "--record",
        type=Path,
        default=FACTORY_ROOT / "iteration-rejection-20260901-v1.json",
    )
    parser.add_argument("--reviewed-by", default="workspace-owner")
    parser.add_argument(
        "--reason",
        default=(
            "Iteração rejeitada pelo usuário: os arquivos são provas técnicas baseadas em "
            "placeholders e não atingem o padrão de edição audiovisual esperado. Replanejar."
        ),
    )
    args = parser.parse_args()
    source = VideoFactoryProgramEvidenceV1.model_validate_json(
        args.program.read_text(encoding="utf-8")
    )
    reviewed_at = datetime.now(UTC)
    rejection_id = "factory-iteration-rejection-20260901-v1"
    rejected = reject_factory_iteration(
        source,
        rejection_id=rejection_id,
        reviewed_by=args.reviewed_by,
        reviewed_at=reviewed_at,
        reason=args.reason,
    )
    rejected_payload = rejected.model_dump(mode="json", by_alias=True)
    rejected_jobs = [
        job.job_id for wave in (rejected.pilot, rejected.calibration) for job in wave.jobs
    ]
    record = FactoryIterationRejectionV1.model_validate(
        {
            "rejectionId": rejection_id,
            "programId": rejected.program_id,
            "rejectedJobIds": rejected_jobs,
            "reason": args.reason,
            "reviewedBy": args.reviewed_by,
            "reviewedAt": reviewed_at,
            "rejectedProgramDigestSha256": canonical_digest(rejected_payload),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(rejected_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.record.write_text(
        json.dumps(record.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "rejected": len(rejected_jobs),
                "humanApproved": rejected.human_approved_count,
                "scaleDispatched": sum(job.attempts > 0 for job in rejected.scale.jobs),
                "externalPublication": rejected.external_publication_count,
                "replanRequired": record.replan_required,
            }
        )
    )


if __name__ == "__main__":
    main()
