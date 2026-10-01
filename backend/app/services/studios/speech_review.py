from __future__ import annotations

import hashlib
import hmac
import math
from datetime import UTC, datetime

from ...domain.studios.benchmarking import (
    BenchmarkCorpusManifestV1,
    BenchmarkEvidenceBundleV1,
    BenchmarkMeasurementV1,
    BenchmarkMetricObservationV1,
    BenchmarkPolicyV1,
    benchmark_corpus_manifest_digest,
    benchmark_evidence_bundle_digest,
)
from ...domain.studios.speech_review import (
    SpeechReviewAssignmentV1,
    SpeechReviewBundleV1,
    SpeechReviewerPacketV1,
    SpeechReviewPlanV1,
    SpeechReviewSubmissionV1,
    speech_review_plan_digest,
)
from .speech_benchmark import StockVoiceBenchmarkArtifacts

_HUMAN_METRICS = {
    "human_naturalness_mos": ("mos_1_5", "mean"),
    "pt_br_intelligibility_word_accuracy": ("ratio", "rate"),
    "critical_term_accuracy": ("ratio", "rate"),
    "critical_off_script_rate": ("ratio", "rate"),
    "repeat_or_truncation_rate": ("ratio", "rate"),
}


def _opaque(secret: bytes, value: str, prefix: str) -> str:
    digest = hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()
    return f"{prefix}-{digest[:32]}"


def build_blinded_review_plan(
    *,
    policy: BenchmarkPolicyV1,
    corpus: BenchmarkCorpusManifestV1,
    artifacts: StockVoiceBenchmarkArtifacts,
    scriptbook: dict,
    reviewer_pseudonyms: list[str],
    blinded_candidate_label: str,
    blinding_secret: bytes,
    generated_at: datetime | None = None,
) -> SpeechReviewPlanV1:
    if len(blinding_secret) < 32:
        raise ValueError("speech_review_blinding_secret_too_short")
    candidate = next(
        (item for item in policy.candidates if item.candidate_id == artifacts.run.candidate_id),
        None,
    )
    if candidate is None:
        raise ValueError("speech_review_candidate_not_in_policy")
    if benchmark_corpus_manifest_digest(corpus) != artifacts.run.corpus_manifest_digest_sha256:
        raise ValueError("speech_review_corpus_manifest_mismatch")
    if candidate.candidate_id.lower() in blinded_candidate_label.lower():
        raise ValueError("speech_review_label_leaks_candidate")
    mos = next(item for item in policy.thresholds if item.metric_id == "human_naturalness_mos")
    required_reviewers = max(3, mos.minimum_unique_reviewers)
    if len(reviewer_pseudonyms) != required_reviewers or len(set(reviewer_pseudonyms)) != len(
        reviewer_pseudonyms
    ):
        raise ValueError("speech_review_requires_exact_distinct_reviewer_count")
    executions = artifacts.evidence_bundle.case_executions
    if any(item.status != "succeeded" for item in executions):
        raise ValueError("speech_review_requires_all_cases_succeeded")
    scripts = {
        str(item.get("caseId")): item
        for item in scriptbook.get("cases", [])
        if isinstance(item, dict)
    }
    if set(scripts) != {item.case_id for item in executions}:
        raise ValueError("speech_review_scriptbook_case_set_mismatch")
    corpus_cases = {item.case_id: item for item in corpus.cases}
    if set(corpus_cases) != set(scripts):
        raise ValueError("speech_review_corpus_case_set_mismatch")
    for case_id, script in scripts.items():
        if script.get("scriptDigestSha256", "").lower() != corpus_cases[
            case_id
        ].script_digest_sha256.lower():
            raise ValueError(f"speech_review_script_digest_mismatch:{case_id}")

    packets = []
    for reviewer in reviewer_pseudonyms:
        assignments = []
        for execution in executions:
            script = scripts[execution.case_id]
            assignments.append(
                SpeechReviewAssignmentV1(
                    assignment_id=_opaque(
                        blinding_secret,
                        f"{artifacts.run.run_id}:{reviewer}:{execution.case_id}",
                        "assignment",
                    ),
                    case_id=execution.case_id,
                    review_clip_id=_opaque(
                        blinding_secret,
                        f"{artifacts.run.run_id}:{execution.case_id}",
                        "clip",
                    ),
                    audio_asset_id=execution.output_asset_id,
                    output_checksum_sha256=execution.output_checksum_sha256,
                    script=script["text"],
                    script_digest_sha256=script["scriptDigestSha256"],
                )
            )
        packets.append(
            SpeechReviewerPacketV1(
                packet_id=_opaque(
                    blinding_secret,
                    f"{artifacts.run.run_id}:{reviewer}:packet",
                    "packet",
                ),
                run_id=artifacts.run.run_id,
                reviewer_pseudonym=reviewer,
                blinded_candidate_label=blinded_candidate_label,
                assignments=assignments,
            )
        )
    return SpeechReviewPlanV1(
        plan_id=_opaque(blinding_secret, f"{artifacts.run.run_id}:plan", "review-plan"),
        run_id=artifacts.run.run_id,
        suite_id=artifacts.run.suite_id,
        candidate_id=artifacts.run.candidate_id,
        evidence_bundle_digest_sha256=benchmark_evidence_bundle_digest(
            artifacts.evidence_bundle
        ),
        generated_at=generated_at or datetime.now(UTC),
        packets=packets,
    )


def _aggregate(values: list[float], aggregation: str) -> float:
    if aggregation in {"mean", "rate"}:
        return sum(values) / len(values)
    if aggregation == "p50":
        return sorted(values)[math.ceil(0.50 * len(values)) - 1]
    if aggregation == "p95":
        return sorted(values)[math.ceil(0.95 * len(values)) - 1]
    if aggregation == "maximum":
        return max(values)
    if aggregation == "minimum":
        return min(values)
    if aggregation == "count":
        return float(len(values))
    raise ValueError(f"unsupported_speech_review_aggregation:{aggregation}")


def append_blinded_review_evidence(
    artifacts: StockVoiceBenchmarkArtifacts,
    policy: BenchmarkPolicyV1,
    plan: SpeechReviewPlanV1,
    submissions: list[SpeechReviewSubmissionV1],
    *,
    review_bundle_id: str,
    review_bundle_asset_id: str,
    evaluator: str,
    evaluator_digest_sha256: str,
    generated_at: datetime | None = None,
) -> tuple[StockVoiceBenchmarkArtifacts, SpeechReviewBundleV1]:
    if plan.run_id != artifacts.run.run_id or plan.candidate_id != artifacts.run.candidate_id:
        raise ValueError("speech_review_plan_run_mismatch")
    if plan.suite_id != policy.suite_id:
        raise ValueError("speech_review_plan_policy_mismatch")
    if plan.evidence_bundle_digest_sha256 != benchmark_evidence_bundle_digest(
        artifacts.evidence_bundle
    ):
        raise ValueError("speech_review_plan_evidence_mismatch")
    plan_digest = speech_review_plan_digest(plan)
    packets = {item.packet_id: item for item in plan.packets}
    if len(submissions) != len(packets):
        raise ValueError("speech_review_submission_count_mismatch")
    observations: list[BenchmarkMetricObservationV1] = []
    seen_reviewers: set[str] = set()
    for submission in submissions:
        packet = packets.get(submission.packet_id)
        if (
            packet is None
            or submission.plan_digest_sha256.lower() != plan_digest
            or submission.reviewer_pseudonym != packet.reviewer_pseudonym
            or submission.reviewer_pseudonym in seen_reviewers
        ):
            raise ValueError("speech_review_submission_binding_mismatch")
        seen_reviewers.add(submission.reviewer_pseudonym)
        assignments = {item.assignment_id: item for item in packet.assignments}
        responses = {item.assignment_id: item for item in submission.responses}
        if set(responses) != set(assignments):
            raise ValueError("speech_review_response_assignment_set_mismatch")
        for assignment_id, response in responses.items():
            assignment = assignments[assignment_id]
            if (
                response.script_digest_sha256.lower() != assignment.script_digest_sha256.lower()
                or response.output_checksum_sha256.lower()
                != assignment.output_checksum_sha256.lower()
            ):
                raise ValueError("speech_review_response_artifact_binding_mismatch")
            values = {
                "human_naturalness_mos": float(response.naturalness_mos),
                "pt_br_intelligibility_word_accuracy": response.intelligibility_word_accuracy,
                "critical_term_accuracy": response.critical_term_accuracy,
                "critical_off_script_rate": float(response.critical_off_script),
                "repeat_or_truncation_rate": float(response.repeat_or_truncation),
            }
            for metric_id, value in values.items():
                observations.append(
                    BenchmarkMetricObservationV1(
                        observation_id=f"obs-{metric_id}-{assignment_id}",
                        metric_id=metric_id,
                        case_id=assignment.case_id,
                        unit=_HUMAN_METRICS[metric_id][0],
                        value=value,
                        evaluator=evaluator,
                        evaluator_digest_sha256=evaluator_digest_sha256,
                        evidence_asset_id=review_bundle_asset_id,
                        reviewer_pseudonym=submission.reviewer_pseudonym,
                        blinded_candidate_label=packet.blinded_candidate_label,
                    )
                )
    generated = generated_at or datetime.now(UTC)
    bundle = SpeechReviewBundleV1(
        bundle_id=review_bundle_id,
        run_id=artifacts.run.run_id,
        plan_digest_sha256=plan_digest,
        generated_at=generated,
        submissions=submissions,
    )
    existing_metric_ids = {item.metric_id for item in artifacts.run.measurements}
    if existing_metric_ids & _HUMAN_METRICS.keys():
        raise ValueError("speech_review_metrics_already_attached")
    measurements = []
    thresholds = {item.metric_id: item for item in policy.thresholds}
    for metric_id, (unit, aggregation) in _HUMAN_METRICS.items():
        threshold = thresholds.get(metric_id)
        if threshold is None or threshold.unit != unit or threshold.aggregation != aggregation:
            raise ValueError(f"speech_review_policy_metric_mismatch:{metric_id}")
        metric_observations = [item for item in observations if item.metric_id == metric_id]
        measurements.append(
            BenchmarkMeasurementV1(
                metric_id=metric_id,
                unit=unit,
                aggregation=aggregation,
                value=_aggregate([item.value for item in metric_observations], aggregation),
                sample_count=len(metric_observations),
                evaluator=evaluator,
                evaluator_digest_sha256=evaluator_digest_sha256,
                case_set_digest_sha256=artifacts.run.corpus_manifest_digest_sha256,
                evidence_asset_ids=[review_bundle_asset_id],
            )
        )
    evidence = BenchmarkEvidenceBundleV1(
        **{
            **artifacts.evidence_bundle.model_dump(mode="python"),
            "generated_at": generated,
            "observations": [*artifacts.evidence_bundle.observations, *observations],
        }
    )
    run = artifacts.run.model_copy(
        update={
            "controls": {**artifacts.run.controls, "human_review_completed": True},
            "evidence_refs": {
                **artifacts.run.evidence_refs,
                "blinded_human_review": review_bundle_asset_id,
            },
            "evidence_bundle_digest_sha256": benchmark_evidence_bundle_digest(evidence),
            "measurements": [*artifacts.run.measurements, *measurements],
        }
    )
    return StockVoiceBenchmarkArtifacts(run=run, evidence_bundle=evidence), bundle
