from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.creative_autonomy import (
    AnimaticBatchEvidenceV1,
    CreativePilotCasebookV1,
)
from app.domain.studios.factory_pre_review import FactoryMachinePreReviewSuiteV1
from app.domain.studios.video_factory import VideoFactoryProgramEvidenceV1

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_ROOT = REPOSITORY_ROOT / "artifacts" / "validation" / "video-creative-pilot"
FACTORY_ROOT = VALIDATION_ROOT / "factory-20260901-v1"
ANIMATICS_PATH = VALIDATION_ROOT / "animatics-20260901-v1" / "manifest.json"
CASEBOOK_PATH = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "studios"
    / "creative"
    / "video-creative-pilot-casebook.v1.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, default=FACTORY_ROOT / "program-manifest.json")
    parser.add_argument("--casebook", type=Path, default=CASEBOOK_PATH)
    parser.add_argument("--animatics", type=Path, default=ANIMATICS_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=FACTORY_ROOT / "machine-pre-review.json",
    )
    args = parser.parse_args()
    program = VideoFactoryProgramEvidenceV1.model_validate_json(
        args.program.read_text(encoding="utf-8")
    )
    casebook = CreativePilotCasebookV1.model_validate_json(
        args.casebook.read_text(encoding="utf-8")
    )
    animatics = AnimaticBatchEvidenceV1.model_validate_json(
        args.animatics.read_text(encoding="utf-8")
    )
    cases = {item.case_id: item for item in casebook.cases}
    animatic_renders = {item.case_id: item for item in animatics.renders}
    reviews = []
    for job in program.pilot.jobs:
        case = cases[job.case_id]
        animatic_render = animatic_renders[job.case_id]
        if not case.animatic.render_digest_sha256 or not job.source_artifact_digest_sha256:
            raise ValueError(f"pre_review_lineage_missing:{job.job_id}")
        if case.animatic.render_digest_sha256 != job.source_artifact_digest_sha256:
            raise ValueError(f"pre_review_source_digest_mismatch:{job.job_id}")
        if animatic_render.artifact_digest_sha256 != job.source_artifact_digest_sha256:
            raise ValueError(f"pre_review_animatic_manifest_digest_mismatch:{job.job_id}")
        if not animatic_render.placeholder_only:
            raise ValueError(f"pre_review_source_not_placeholder:{job.job_id}")
        if not job.artifact_path or not job.artifact_digest_sha256:
            raise ValueError(f"pre_review_artifact_missing:{job.job_id}")
        artifact_path = (REPOSITORY_ROOT / job.artifact_path).resolve()
        if not artifact_path.is_file():
            raise ValueError(f"pre_review_artifact_file_missing:{job.job_id}")
        artifact_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if artifact_digest != job.artifact_digest_sha256:
            raise ValueError(f"pre_review_artifact_digest_mismatch:{job.job_id}")
        reviews.append(
            {
                "jobId": job.job_id,
                "caseId": job.case_id,
                "artifactDigestSha256": job.artifact_digest_sha256,
                "sourceAnimaticDigestSha256": job.source_artifact_digest_sha256,
                "verdict": "storyboard_review_only",
                "flags": [
                    "source_is_placeholder_animatic",
                    "no_authorized_footage",
                    "no_final_audio_mix",
                    "no_final_motion_composition",
                    "not_a_final_edit",
                ],
                "reviewableDimensions": ["message", "beat_order", "copy", "shot_intent"],
                "recommendation": (
                    "Revisar apenas mensagem, ordem dos beats, copy e intenção de shot. "
                    "Não aprovar como edição final; substituir placeholders por mídia autorizada, "
                    "motion executado e mix revisado antes do gate audiovisual humano."
                ),
            }
        )
    suite = FactoryMachinePreReviewSuiteV1.model_validate(
        {
            "suiteId": "clicko-pilot-12-machine-pre-review-v1",
            "reviews": reviews,
            "readyForFinalHumanReviewCount": 0,
            "storyboardReviewOnlyCount": 12,
            "promotionEligible": False,
            "blockers": [
                "authorized_footage_or_generated_assets_required",
                "final_motion_composition_required",
                "final_audio_mix_and_listening_review_required",
            ],
            "reviewedAt": datetime.now(UTC),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(suite.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "readyForFinalHumanReview": suite.ready_for_final_human_review_count,
                "storyboardReviewOnly": suite.storyboard_review_only_count,
                "promotionEligible": suite.promotion_eligible,
            }
        )
    )


if __name__ == "__main__":
    main()
