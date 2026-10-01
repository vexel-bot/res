from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .artifacts import ProviderCandidateManifestV1, provider_candidate_manifest_digest
from .contracts import StudioContract
from .reality import RealityPrinciple, RealityShotV1

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"
CameraMotion = Literal[
    "static",
    "pan",
    "tilt",
    "roll",
    "dolly",
    "truck",
    "pedestal",
    "zoom",
    "handheld",
    "mixed",
    "unknown",
]
GeneratorKind = Literal[
    "static_textured",
    "pan_textured",
    "tilt_textured",
    "roll_textured",
    "zoom_textured",
    "pan_no_horizon",
    "low_texture",
    "two_shot_cut",
    "blurred_pan",
    "foreground_motion",
    "horizon_distractors",
]
METRIC_IDS = {
    "motion_label_accuracy",
    "horizon_presence_accuracy",
    "gravity_presence_accuracy",
    "track_requirement_accuracy",
    "status_accuracy",
    "abstention_compliance",
}


class SyntheticRealityExpectationV1(StudioContract):
    accepted_motion_by_shot: dict[str, list[CameraMotion]] = Field(min_length=1, max_length=20)
    horizon_present_by_shot: dict[str, bool] = Field(min_length=1, max_length=20)
    gravity_present_by_shot: dict[str, bool] = Field(min_length=1, max_length=20)
    minimum_tracks_by_shot: dict[str, int] = Field(min_length=1, max_length=20)
    maximum_tracks_by_shot: dict[str, int] = Field(min_length=1, max_length=20)
    expected_model_status: Literal["complete", "partial", "incomplete"]
    required_abstentions: list[RealityPrinciple] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_expectation(self) -> SyntheticRealityExpectationV1:
        shot_ids = set(self.accepted_motion_by_shot)
        for label, mapping in (
            ("horizon", self.horizon_present_by_shot),
            ("gravity", self.gravity_present_by_shot),
            ("minimum tracks", self.minimum_tracks_by_shot),
            ("maximum tracks", self.maximum_tracks_by_shot),
        ):
            if set(mapping) != shot_ids:
                raise ValueError(f"Synthetic reality {label} keys must match motion keys")
        if any(not values or len(values) != len(set(values)) for values in self.accepted_motion_by_shot.values()):
            raise ValueError("Accepted camera labels must be non-empty and unique")
        if any(value < 0 or value > 10000 for value in self.minimum_tracks_by_shot.values()):
            raise ValueError("Synthetic minimum tracks are out of bounds")
        if any(value < 0 or value > 10000 for value in self.maximum_tracks_by_shot.values()):
            raise ValueError("Synthetic maximum tracks are out of bounds")
        if any(
            self.minimum_tracks_by_shot[shot_id] > self.maximum_tracks_by_shot[shot_id]
            for shot_id in shot_ids
        ):
            raise ValueError("Synthetic track bounds are inverted")
        if len(self.required_abstentions) != len(set(self.required_abstentions)):
            raise ValueError("Synthetic required abstentions must be unique")
        return self


class SyntheticRealityCaseV1(StudioContract):
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    generator: GeneratorKind
    scenarios: list[str] = Field(min_length=1, max_length=30)
    width: int = Field(default=320, ge=160, le=1920)
    height: int = Field(default=180, ge=90, le=1080)
    total_frames: int = Field(default=48, ge=8, le=600)
    fps: int = Field(default=30, ge=1, le=120)
    shots: list[RealityShotV1] = Field(min_length=1, max_length=20)
    generator_parameters: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        max_length=30,
    )
    expectation: SyntheticRealityExpectationV1

    @model_validator(mode="after")
    def validate_case(self) -> SyntheticRealityCaseV1:
        if len(self.scenarios) != len(set(self.scenarios)):
            raise ValueError("Synthetic reality scenarios must be unique")
        shot_ids = [shot.shot_id for shot in self.shots]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("Synthetic reality shot ids must be unique")
        if set(shot_ids) != set(self.expectation.accepted_motion_by_shot):
            raise ValueError("Synthetic reality expectations must cover every shot")
        ordered = sorted(self.shots, key=lambda item: item.frame_range.start_frame)
        if ordered[0].frame_range.start_frame != 0:
            raise ValueError("Synthetic reality shots must start at frame zero")
        cursor = 0
        for shot in ordered:
            if shot.frame_range.start_frame != cursor:
                raise ValueError("Synthetic reality shots must be contiguous")
            cursor = shot.frame_range.end_frame_exclusive
        if cursor != self.total_frames:
            raise ValueError("Synthetic reality shots must cover the complete video")
        return self


class RealityPerceptionThresholdV1(StudioContract):
    metric_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    minimum: float = Field(ge=0, le=1)
    blocking: bool = True
    rationale: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_metric(self) -> RealityPerceptionThresholdV1:
        if self.metric_id not in METRIC_IDS:
            raise ValueError("Unknown reality perception benchmark metric")
        return self


class SyntheticRealityCorpusV1(StudioContract):
    schema_version: Literal["studio.synthetic-reality-corpus.v1"] = (
        "studio.synthetic-reality-corpus.v1"
    )
    corpus_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    candidate_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    candidate_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    frozen_at: datetime
    frozen_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    cases: list[SyntheticRealityCaseV1] = Field(min_length=1, max_length=1000)
    thresholds: list[RealityPerceptionThresholdV1] = Field(min_length=1, max_length=30)
    required_scenarios: list[str] = Field(min_length=1, max_length=100)
    notes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_corpus(self) -> SyntheticRealityCorpusV1:
        case_ids = [item.case_id for item in self.cases]
        metric_ids = [item.metric_id for item in self.thresholds]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Synthetic reality case ids must be unique")
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("Synthetic reality metric ids must be unique")
        if len(self.required_scenarios) != len(set(self.required_scenarios)):
            raise ValueError("Synthetic reality required scenarios must be unique")
        observed = {scenario for case in self.cases for scenario in case.scenarios}
        missing = sorted(set(self.required_scenarios) - observed)
        if missing:
            raise ValueError(f"Synthetic reality corpus is missing scenarios: {missing}")
        if set(metric_ids) != METRIC_IDS:
            raise ValueError("Synthetic reality corpus must threshold every metric")
        return self


class RealityPerceptionEnvironmentV1(StudioContract):
    python_version: str = Field(min_length=1, max_length=80)
    opencv_version: str = Field(min_length=1, max_length=80)
    numpy_version: str = Field(min_length=1, max_length=80)
    operating_system: str = Field(min_length=1, max_length=160)
    architecture: str = Field(min_length=1, max_length=80)
    dependency_lock_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    isolated_environment: bool
    synthetic_only: bool


class RealityPerceptionObservationV1(StudioContract):
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    motion_by_shot: dict[str, CameraMotion] = Field(min_length=1, max_length=20)
    horizon_present_by_shot: dict[str, bool] = Field(min_length=1, max_length=20)
    gravity_present_by_shot: dict[str, bool] = Field(min_length=1, max_length=20)
    track_count_by_shot: dict[str, int] = Field(min_length=1, max_length=20)
    model_status: Literal["complete", "partial", "incomplete"]
    abstained_principles: list[RealityPrinciple] = Field(default_factory=list, max_length=30)
    provider_versions: dict[str, str] = Field(min_length=1, max_length=20)
    code_digests_sha256: dict[str, str] = Field(min_length=1, max_length=20)
    evidence_digest_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_observation(self) -> RealityPerceptionObservationV1:
        keys = set(self.motion_by_shot)
        if any(
            set(mapping) != keys
            for mapping in (
                self.horizon_present_by_shot,
                self.gravity_present_by_shot,
                self.track_count_by_shot,
            )
        ):
            raise ValueError("Reality observation shot maps must align")
        if any(value < 0 or value > 10000 for value in self.track_count_by_shot.values()):
            raise ValueError("Reality observation track count is out of bounds")
        if set(self.provider_versions) != set(self.code_digests_sha256):
            raise ValueError("Reality observation provider versions and code digests must align")
        if any(
            len(value) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in value)
            for value in self.code_digests_sha256.values()
        ):
            raise ValueError("Reality observation contains an invalid code digest")
        return self


class RealityPerceptionBenchmarkReportV1(StudioContract):
    schema_version: Literal["studio.reality-perception-benchmark-report.v1"] = (
        "studio.reality-perception-benchmark-report.v1"
    )
    report_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    corpus_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    corpus_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    candidate_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    candidate_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    generated_at: datetime
    environment: RealityPerceptionEnvironmentV1
    observations: list[RealityPerceptionObservationV1] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_report(self) -> RealityPerceptionBenchmarkReportV1:
        case_ids = [item.case_id for item in self.observations]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Reality benchmark observation case ids must be unique")
        return self


class RealityPerceptionGateResultV1(StudioContract):
    schema_version: Literal["studio.reality-perception-gate-result.v1"] = (
        "studio.reality-perception-gate-result.v1"
    )
    report_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    report_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    corpus_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    candidate_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    technical_decision: Literal["passed", "failed", "incomplete"]
    activation_decision: Literal["eligible", "blocked", "incomplete"]
    metrics: dict[str, float] = Field(min_length=1, max_length=30)
    failed_metrics: list[str] = Field(default_factory=list, max_length=30)
    failed_cases: list[str] = Field(default_factory=list, max_length=1000)
    blocking_reasons: list[str] = Field(default_factory=list, max_length=100)
    incomplete_reasons: list[str] = Field(default_factory=list, max_length=100)
    evaluator_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    evaluated_at: datetime


def synthetic_reality_corpus_digest(corpus: SyntheticRealityCorpusV1) -> str:
    return _contract_digest(corpus)


def reality_perception_report_digest(report: RealityPerceptionBenchmarkReportV1) -> str:
    return _contract_digest(report)


def evaluate_reality_perception_report(
    corpus: SyntheticRealityCorpusV1,
    candidate: ProviderCandidateManifestV1,
    report: RealityPerceptionBenchmarkReportV1,
    *,
    evaluated_at: datetime,
) -> RealityPerceptionGateResultV1:
    corpus_digest = synthetic_reality_corpus_digest(corpus)
    candidate_digest = provider_candidate_manifest_digest(candidate)
    blocking: list[str] = []
    incomplete: list[str] = []
    if report.corpus_id != corpus.corpus_id or report.corpus_digest_sha256.lower() != corpus_digest:
        blocking.append("corpus_binding_mismatch")
    if (
        report.candidate_id != candidate.candidate_id
        or report.candidate_manifest_digest_sha256.lower() != candidate_digest
        or corpus.candidate_id != candidate.candidate_id
        or corpus.candidate_manifest_digest_sha256.lower() != candidate_digest
    ):
        blocking.append("candidate_binding_mismatch")
    if not report.environment.isolated_environment:
        blocking.append("environment_not_isolated")
    if not report.environment.synthetic_only:
        blocking.append("non_synthetic_input_in_synthetic_benchmark")

    expected = {item.case_id: item for item in corpus.cases}
    observed = {item.case_id: item for item in report.observations}
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    incomplete.extend(f"missing_case:{case_id}" for case_id in missing)
    blocking.extend(f"unscoped_case:{case_id}" for case_id in extra)

    numerators = {metric_id: 0 for metric_id in METRIC_IDS}
    denominators = {metric_id: 0 for metric_id in METRIC_IDS}
    failed_cases: list[str] = []
    for case_id in sorted(set(expected) & set(observed)):
        case = expected[case_id]
        observation = observed[case_id]
        shot_ids = {item.shot_id for item in case.shots}
        case_passed = True
        if set(observation.motion_by_shot) != shot_ids:
            blocking.append(f"observation_shot_set_mismatch:{case_id}")
            failed_cases.append(case_id)
            continue
        for shot_id in sorted(shot_ids):
            checks = {
                "motion_label_accuracy": (
                    observation.motion_by_shot[shot_id]
                    in case.expectation.accepted_motion_by_shot[shot_id]
                ),
                "horizon_presence_accuracy": (
                    observation.horizon_present_by_shot[shot_id]
                    == case.expectation.horizon_present_by_shot[shot_id]
                ),
                "gravity_presence_accuracy": (
                    observation.gravity_present_by_shot[shot_id]
                    == case.expectation.gravity_present_by_shot[shot_id]
                ),
                "track_requirement_accuracy": (
                    case.expectation.minimum_tracks_by_shot[shot_id]
                    <= observation.track_count_by_shot[shot_id]
                    <= case.expectation.maximum_tracks_by_shot[shot_id]
                ),
            }
            for metric_id, passed in checks.items():
                denominators[metric_id] += 1
                numerators[metric_id] += int(passed)
                case_passed = case_passed and passed
        status_passed = observation.model_status == case.expectation.expected_model_status
        denominators["status_accuracy"] += 1
        numerators["status_accuracy"] += int(status_passed)
        case_passed = case_passed and status_passed
        for principle in case.expectation.required_abstentions:
            passed = principle in observation.abstained_principles
            denominators["abstention_compliance"] += 1
            numerators["abstention_compliance"] += int(passed)
            case_passed = case_passed and passed
        if not case_passed:
            failed_cases.append(case_id)

    metrics = {
        metric_id: (
            numerators[metric_id] / denominators[metric_id]
            if denominators[metric_id]
            else 0.0
        )
        for metric_id in sorted(METRIC_IDS)
    }
    failed_metrics = sorted(
        threshold.metric_id
        for threshold in corpus.thresholds
        if threshold.blocking and metrics[threshold.metric_id] < threshold.minimum
    )
    if blocking or failed_metrics:
        technical_decision = "failed"
    elif incomplete:
        technical_decision = "incomplete"
    else:
        technical_decision = "passed"

    if technical_decision == "failed":
        activation_decision = "blocked"
    elif technical_decision == "incomplete" or candidate.status != "approved":
        activation_decision = "incomplete"
        if candidate.status != "approved":
            incomplete.append(f"candidate_status:{candidate.status}")
    else:
        activation_decision = "eligible"
    return RealityPerceptionGateResultV1(
        report_id=report.report_id,
        report_digest_sha256=reality_perception_report_digest(report),
        corpus_digest_sha256=corpus_digest,
        candidate_manifest_digest_sha256=candidate_digest,
        technical_decision=technical_decision,
        activation_decision=activation_decision,
        metrics=metrics,
        failed_metrics=failed_metrics,
        failed_cases=sorted(set(failed_cases)),
        blocking_reasons=sorted(set(blocking)),
        incomplete_reasons=sorted(set(incomplete)),
        evaluator_digest_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        evaluated_at=evaluated_at,
    )


def _contract_digest(contract: StudioContract) -> str:
    canonical = json.dumps(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
