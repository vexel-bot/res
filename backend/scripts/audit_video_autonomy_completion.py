from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.advanced_capabilities import AdvancedCapabilityAuditV1
from app.domain.studios.assisted_intelligence import AssistedIntelligenceSuiteEvidenceV1
from app.domain.studios.autonomy_completion import VideoAutonomyCompletionAuditV1
from app.domain.studios.creative_autonomy import CreativePilotCasebookV1
from app.domain.studios.creative_replan import CreativeReplanStateV1
from app.domain.studios.factory_pre_review import FactoryMachinePreReviewSuiteV1
from app.domain.studios.motion_benchmark import MotionGoldenSuiteEvidenceV1
from app.domain.studios.video_factory import VideoFactoryProgramEvidenceV1

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_ROOT = REPOSITORY_ROOT / "artifacts" / "validation" / "video-creative-pilot"
DEFAULT_OUTPUT = VALIDATION_ROOT / "program-audit-20260901-v1" / "audit.json"


def load(path: Path, model):
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def build_audit() -> VideoAutonomyCompletionAuditV1:
    casebook = load(
        REPOSITORY_ROOT
        / "benchmarks"
        / "studios"
        / "creative"
        / "video-creative-pilot-casebook.v1.json",
        CreativePilotCasebookV1,
    )
    animatics = json.loads(
        (VALIDATION_ROOT / "animatics-20260901-v1" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    motion = load(
        VALIDATION_ROOT / "motion-goldens-20260901-v1" / "manifest.json",
        MotionGoldenSuiteEvidenceV1,
    )
    assistance = load(
        VALIDATION_ROOT / "assisted-intelligence-20260901-v1" / "manifest.json",
        AssistedIntelligenceSuiteEvidenceV1,
    )
    factory = load(
        VALIDATION_ROOT / "factory-20260901-v1" / "current-program-manifest.json",
        VideoFactoryProgramEvidenceV1,
    )
    pre_review = load(
        VALIDATION_ROOT / "factory-20260901-v1" / "machine-pre-review.json",
        FactoryMachinePreReviewSuiteV1,
    )
    replan = load(
        VALIDATION_ROOT
        / "factory-20260901-v1"
        / "creative-replan-state-20260901-v2.json",
        CreativeReplanStateV1,
    )
    advanced = load(
        VALIDATION_ROOT / "advanced-capabilities-20260901-v1" / "audit.json",
        AdvancedCapabilityAuditV1,
    )
    if not animatics["eligible"] or len(animatics["renders"]) != 12:
        raise ValueError("animatic_batch_not_eligible")
    phase_rows = [
        {
            "phase": "P0",
            "implementationStatus": "complete",
            "operationalStatus": "complete",
            "evidencePaths": ["benchmarks/studios/creative/video-creative-pilot-casebook.v1.json"],
        },
        {
            "phase": "P1",
            "implementationStatus": "complete",
            "operationalStatus": "complete",
            "evidencePaths": ["src/studios/videoTimeline.ts", "backend/app/providers/studios/video_render.py"],
        },
        {
            "phase": "P2",
            "implementationStatus": "complete",
            "operationalStatus": "complete",
            "evidencePaths": ["artifacts/validation/video-creative-pilot/animatics-20260901-v1/manifest.json"],
        },
        {
            "phase": "P3",
            "implementationStatus": "complete",
            "operationalStatus": "complete",
            "evidencePaths": ["artifacts/validation/video-creative-pilot/motion-goldens-20260901-v1/manifest.json"],
        },
        {
            "phase": "P4",
            "implementationStatus": "complete",
            "operationalStatus": "complete",
            "evidencePaths": [
                "artifacts/validation/video-creative-pilot/"
                "assisted-intelligence-20260901-v1/manifest.json"
            ],
        },
        {
            "phase": "P5",
            "implementationStatus": "complete",
            "operationalStatus": "rejected_replan_required",
            "evidencePaths": [
                "artifacts/validation/video-creative-pilot/factory-20260901-v1/"
                "current-program-manifest.json",
                "artifacts/validation/video-creative-pilot/factory-20260901-v1/"
                "iteration-rejection-20260901-v1.json",
                "artifacts/validation/video-creative-pilot/factory-20260901-v1/"
                "creative-replan-state-20260901-v2.json",
            ],
            "blockers": [
                "pilot_machine_pre_review_not_final_edit",
                "authorized_media_motion_and_audio_required",
                "current_iteration_rejected",
                "creative_replan_required",
                "new_replan_decisions_pending",
                "golden_video_not_approved",
                "infrastructure_cost_policy_pending",
            ],
        },
        {
            "phase": "P6",
            "implementationStatus": "complete",
            "operationalStatus": "blocked_by_gate",
            "evidencePaths": ["artifacts/validation/video-creative-pilot/factory-20260901-v1/scale-64-manifest.json"],
            "blockers": ["pilot_and_calibration_promotion_required"],
        },
        {
            "phase": "P7",
            "implementationStatus": "complete",
            "operationalStatus": "disabled_fail_closed",
            "evidencePaths": ["artifacts/validation/video-creative-pilot/advanced-capabilities-20260901-v1/audit.json"],
            "blockers": advanced.blockers,
        },
    ]
    scale_dispatched = sum(job.attempts > 0 for job in factory.scale.jobs)
    if pre_review.promotion_eligible or pre_review.ready_for_final_human_review_count:
        raise ValueError("placeholder_pre_review_must_not_be_promotion_eligible")
    if replan.golden_production_eligible or replan.batch_dispatch_authorized:
        raise ValueError("rejected_iteration_restart_gate_must_remain_closed")
    return VideoAutonomyCompletionAuditV1.model_validate(
        {
            "auditId": "clicko-video-autonomy-completion-20260901-v1",
            "phases": phase_rows,
            "casebookCaseCount": len(casebook.cases),
            "animaticCount": len(animatics["renders"]),
            "motionGoldenCount": len(motion.cases),
            "assistedStoryboardOptionCount": sum(
                len(item.option_set.options) for item in assistance.cases
            ),
            "producedPrivateArtifactCount": factory.produced_artifact_count,
            "humanApprovedArtifactCount": factory.human_approved_count,
            "scaleJobCount": len(factory.scale.jobs),
            "dispatchedScaleJobCount": scale_dispatched,
            "advancedCandidateCount": len(advanced.candidates),
            "authorizedIdentityCount": advanced.authorized_identity_count,
            "advancedBenchmarkCaseCount": advanced.executed_benchmark_case_count,
            "enabledAdvancedProviderCount": len(advanced.enabled_provider_ids),
            "externalPublicationCount": factory.external_publication_count,
            "implementationComplete": True,
            "objectiveComplete": False,
            "blockers": [
                "pilot_machine_pre_review_not_final_edit",
                "authorized_media_motion_and_audio_required",
                "current_iteration_rejected",
                "creative_replan_required",
                "new_replan_decisions_pending",
                "golden_video_not_approved",
                "infrastructure_cost_policy_pending",
                "scale_64_not_dispatched_by_hard_gate",
            ],
            "auditedAt": datetime.now(UTC).isoformat(),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit = build_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit.model_dump(mode="json", by_alias=True)))


if __name__ == "__main__":
    main()
