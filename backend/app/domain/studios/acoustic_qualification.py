from __future__ import annotations

import hashlib
import hmac
import json
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from .contracts import SHA256_PATTERN, StudioContract

OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"
RELATIVE_ASSET_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,499}$"


def _canonical_bytes(contract: StudioContract, *, exclude: set[str] | None = None) -> bytes:
    return json.dumps(
        contract.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
            exclude=exclude or set(),
        ),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def contract_digest(contract: StudioContract) -> str:
    return hashlib.sha256(_canonical_bytes(contract)).hexdigest()


class AcousticMetricLimitsV1(StudioContract):
    speech_false_negative_rate_max: float = Field(ge=0, le=1)
    speech_false_positive_rate_max: float = Field(ge=0, le=1)
    music_false_negative_rate_max: float = Field(ge=0, le=1)
    music_false_positive_rate_max: float = Field(ge=0, le=1)
    inconclusive_rate_max: float = Field(ge=0, le=1)


class AcousticQualificationPolicyV1(StudioContract):
    schema_version: Literal["studio.acoustic-qualification-policy.v1"] = "studio.acoustic-qualification-policy.v1"
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    policy_version: str = Field(pattern=OPAQUE_ID_PATTERN)
    status: Literal["draft", "approved", "retired"]
    approved_at: datetime | None = None
    approved_by: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    minimum_case_count: int = Field(ge=20, le=100_000)
    minimum_cases_per_environment: int = Field(ge=2, le=10_000)
    minimum_positive_cases_per_target: int = Field(ge=2, le=100_000)
    minimum_negative_cases_per_target: int = Field(ge=2, le=100_000)
    required_environments: list[Literal["natural_only", "speech", "music", "speech_music", "silence"]] = Field(
        min_length=5, max_length=5
    )
    required_locales: list[str] = Field(min_length=1, max_length=20)
    limits: AcousticMetricLimitsV1
    require_verified_rights: bool = True
    require_exact_asset_bytes: bool = True
    require_no_egress: bool = True
    require_isolated_tenant: bool = True
    require_ephemeral_workspace: bool = True
    rationale: list[str] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_policy(self) -> AcousticQualificationPolicyV1:
        required = {"natural_only", "speech", "music", "speech_music", "silence"}
        if set(self.required_environments) != required:
            raise ValueError("acoustic_policy_environment_coverage_incomplete")
        if len(self.required_locales) != len(set(self.required_locales)):
            raise ValueError("acoustic_policy_locales_must_be_unique")
        if self.status == "approved" and (not self.approved_at or not self.approved_by):
            raise ValueError("approved_acoustic_policy_requires_approval_provenance")
        return self


class AcousticCorpusCaseV1(StudioContract):
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    relative_asset_path: str = Field(pattern=RELATIVE_ASSET_PATTERN)
    asset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    asset_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    rights_evidence_relative_path: str = Field(pattern=RELATIVE_ASSET_PATTERN)
    rights_evidence_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    rights_status: Literal["verified", "restricted", "unknown"]
    environment: Literal["natural_only", "speech", "music", "speech_music", "silence"]
    speech_present: bool
    music_present: bool
    duration_seconds: float = Field(gt=0, le=3600)
    locale: str = Field(min_length=2, max_length=32)

    @model_validator(mode="after")
    def validate_truth_labels(self) -> AcousticCorpusCaseV1:
        expected = {
            "natural_only": (False, False),
            "speech": (True, False),
            "music": (False, True),
            "speech_music": (True, True),
            "silence": (False, False),
        }[self.environment]
        if (self.speech_present, self.music_present) != expected:
            raise ValueError("acoustic_case_truth_label_environment_mismatch")
        for value in (self.relative_asset_path, self.rights_evidence_relative_path):
            pure = PurePosixPath(value)
            if pure.is_absolute() or ".." in pure.parts or "\\" in value:
                raise ValueError("acoustic_case_paths_must_be_relative")
        return self


class AcousticCorpusManifestV1(StudioContract):
    schema_version: Literal["studio.acoustic-corpus-manifest.v1"] = "studio.acoustic-corpus-manifest.v1"
    corpus_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    created_at: datetime
    repository_contains_media: Literal[False] = False
    cases: list[AcousticCorpusCaseV1] = Field(min_length=1, max_length=100_000)

    @model_validator(mode="after")
    def validate_cases(self) -> AcousticCorpusManifestV1:
        case_ids = [case.case_id for case in self.cases]
        asset_ids = [case.asset_id for case in self.cases]
        paths = [case.relative_asset_path for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("acoustic_corpus_case_ids_must_be_unique")
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("acoustic_corpus_asset_ids_must_be_unique")
        if len(paths) != len(set(paths)):
            raise ValueError("acoustic_corpus_asset_paths_must_be_unique")
        return self


class AcousticCasePredictionV1(StudioContract):
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    input_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    speech_present: bool | None
    music_present: bool | None
    status: Literal["succeeded", "inconclusive", "failed"]
    evidence_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    runtime_milliseconds: int = Field(ge=0, le=86_400_000)
    failure_code: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)

    @model_validator(mode="after")
    def validate_prediction(self) -> AcousticCasePredictionV1:
        if self.status == "succeeded" and (
            self.speech_present is None or self.music_present is None or self.failure_code
        ):
            raise ValueError("successful_acoustic_prediction_requires_both_labels")
        if self.status != "succeeded" and not self.failure_code:
            raise ValueError("unsuccessful_acoustic_prediction_requires_failure_code")
        return self


class AcousticConfusionMatrixV1(StudioContract):
    true_positive: int = Field(ge=0)
    true_negative: int = Field(ge=0)
    false_positive: int = Field(ge=0)
    false_negative: int = Field(ge=0)


class AcousticAggregateMetricsV1(StudioContract):
    case_count: int = Field(ge=0)
    succeeded_count: int = Field(ge=0)
    inconclusive_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    speech: AcousticConfusionMatrixV1
    music: AcousticConfusionMatrixV1
    speech_false_negative_rate: float = Field(ge=0, le=1)
    speech_false_positive_rate: float = Field(ge=0, le=1)
    music_false_negative_rate: float = Field(ge=0, le=1)
    music_false_positive_rate: float = Field(ge=0, le=1)
    inconclusive_rate: float = Field(ge=0, le=1)


class AcousticQualificationRunV1(StudioContract):
    schema_version: Literal["studio.acoustic-qualification-run.v1"] = "studio.acoustic-qualification-run.v1"
    run_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    provider: str = Field(pattern=OPAQUE_ID_PATTERN)
    provider_version: str = Field(min_length=1, max_length=240)
    model_name: str = Field(min_length=1, max_length=240)
    model_version: str = Field(min_length=1, max_length=240)
    model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    corpus_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    license_review_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    conversion_provenance_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    evaluator_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_advertised: bool
    no_egress: bool
    isolated_tenant: bool
    ephemeral_workspace: bool
    started_at: datetime
    completed_at: datetime
    predictions: list[AcousticCasePredictionV1] = Field(min_length=1, max_length=100_000)
    reported_metrics: AcousticAggregateMetricsV1

    @model_validator(mode="after")
    def validate_run(self) -> AcousticQualificationRunV1:
        if self.completed_at < self.started_at:
            raise ValueError("acoustic_run_completion_precedes_start")
        case_ids = [prediction.case_id for prediction in self.predictions]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("acoustic_prediction_case_ids_must_be_unique")
        return self


class AcousticQualificationAssessmentV1(StudioContract):
    schema_version: Literal["studio.acoustic-qualification-assessment.v1"] = (
        "studio.acoustic-qualification-assessment.v1"
    )
    run_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    provider: str = Field(pattern=OPAQUE_ID_PATTERN)
    provider_version: str = Field(min_length=1, max_length=240)
    model_name: str = Field(min_length=1, max_length=240)
    model_version: str = Field(min_length=1, max_length=240)
    model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    corpus_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    run_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    license_review_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    conversion_provenance_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    decision: Literal["passed", "failed", "incomplete"]
    blocking_reasons: list[str] = Field(default_factory=list, max_length=100)
    incomplete_reasons: list[str] = Field(default_factory=list, max_length=100)
    recomputed_metrics: AcousticAggregateMetricsV1
    evaluator_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    evaluated_at: datetime


class AcousticPromotionReceiptV1(StudioContract):
    schema_version: Literal["studio.acoustic-promotion-receipt.v1"] = "studio.acoustic-promotion-receipt.v1"
    assessment: AcousticQualificationAssessmentV1
    signer_key_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    signature_hmac_sha256: str = Field(pattern=SHA256_PATTERN)


def _matrix(truth: list[bool], predicted: list[bool]) -> AcousticConfusionMatrixV1:
    values = Counter(zip(truth, predicted, strict=True))
    return AcousticConfusionMatrixV1(
        true_positive=values[(True, True)],
        true_negative=values[(False, False)],
        false_positive=values[(False, True)],
        false_negative=values[(True, False)],
    )


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def recompute_metrics(
    corpus: AcousticCorpusManifestV1,
    run: AcousticQualificationRunV1,
) -> AcousticAggregateMetricsV1:
    cases = {case.case_id: case for case in corpus.cases}
    succeeded = [prediction for prediction in run.predictions if prediction.status == "succeeded"]
    speech_matrix = _matrix(
        [cases[item.case_id].speech_present for item in succeeded],
        [bool(item.speech_present) for item in succeeded],
    )
    music_matrix = _matrix(
        [cases[item.case_id].music_present for item in succeeded],
        [bool(item.music_present) for item in succeeded],
    )
    speech_positive = speech_matrix.true_positive + speech_matrix.false_negative
    speech_negative = speech_matrix.true_negative + speech_matrix.false_positive
    music_positive = music_matrix.true_positive + music_matrix.false_negative
    music_negative = music_matrix.true_negative + music_matrix.false_positive
    inconclusive_count = sum(item.status == "inconclusive" for item in run.predictions)
    failed_count = sum(item.status == "failed" for item in run.predictions)
    return AcousticAggregateMetricsV1(
        case_count=len(run.predictions),
        succeeded_count=len(succeeded),
        inconclusive_count=inconclusive_count,
        failed_count=failed_count,
        speech=speech_matrix,
        music=music_matrix,
        speech_false_negative_rate=_ratio(speech_matrix.false_negative, speech_positive),
        speech_false_positive_rate=_ratio(speech_matrix.false_positive, speech_negative),
        music_false_negative_rate=_ratio(music_matrix.false_negative, music_positive),
        music_false_positive_rate=_ratio(music_matrix.false_positive, music_negative),
        inconclusive_rate=_ratio(inconclusive_count + failed_count, len(run.predictions)),
    )


def _metrics_equal(left: AcousticAggregateMetricsV1, right: AcousticAggregateMetricsV1) -> bool:
    return _canonical_bytes(left) == _canonical_bytes(right)


def _asset_reasons(corpus: AcousticCorpusManifestV1, asset_root: Path) -> list[str]:
    root = asset_root.resolve()
    reasons: list[str] = []
    for case in corpus.cases:
        for kind, relative_path, expected_digest in (
            ("asset", case.relative_asset_path, case.asset_checksum_sha256),
            (
                "rights_evidence",
                case.rights_evidence_relative_path,
                case.rights_evidence_digest_sha256,
            ),
        ):
            candidate = (root / Path(*PurePosixPath(relative_path).parts)).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                reasons.append(f"{kind}_path_escape:{case.case_id}")
                continue
            if not candidate.is_file():
                reasons.append(f"{kind}_missing:{case.case_id}")
                continue
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if digest != expected_digest.lower():
                reasons.append(f"{kind}_checksum_mismatch:{case.case_id}")
    return reasons


def evaluate_acoustic_qualification(
    policy: AcousticQualificationPolicyV1,
    corpus: AcousticCorpusManifestV1,
    run: AcousticQualificationRunV1,
    *,
    asset_root: Path,
    evaluated_at: datetime,
) -> AcousticQualificationAssessmentV1:
    blocking: list[str] = []
    incomplete: list[str] = []
    policy_digest = contract_digest(policy)
    corpus_digest = contract_digest(corpus)
    run_digest = contract_digest(run)

    if policy.status != "approved":
        incomplete.append(f"policy_status:{policy.status}")
    if corpus.suite_id != policy.suite_id or run.suite_id != policy.suite_id:
        blocking.append("suite_binding_mismatch")
    if corpus.policy_digest_sha256.lower() != policy_digest:
        blocking.append("corpus_policy_binding_mismatch")
    if run.policy_digest_sha256.lower() != policy_digest:
        blocking.append("run_policy_binding_mismatch")
    if run.corpus_manifest_digest_sha256.lower() != corpus_digest:
        blocking.append("run_corpus_binding_mismatch")

    if len(corpus.cases) < policy.minimum_case_count:
        incomplete.append("corpus_case_count_below_minimum")
    counts = Counter(case.environment for case in corpus.cases)
    for environment in policy.required_environments:
        if counts[environment] < policy.minimum_cases_per_environment:
            incomplete.append(f"environment_coverage_below_minimum:{environment}")
    locales = Counter(case.locale for case in corpus.cases)
    for locale in policy.required_locales:
        if locales[locale] < policy.minimum_cases_per_environment:
            incomplete.append(f"locale_coverage_below_minimum:{locale}")
    unexpected_locales = set(locales) - set(policy.required_locales)
    if unexpected_locales:
        blocking.extend(f"unexpected_corpus_locale:{locale}" for locale in unexpected_locales)
    for target in ("speech", "music"):
        positive = sum(bool(getattr(case, f"{target}_present")) for case in corpus.cases)
        negative = len(corpus.cases) - positive
        if positive < policy.minimum_positive_cases_per_target:
            incomplete.append(f"positive_coverage_below_minimum:{target}")
        if negative < policy.minimum_negative_cases_per_target:
            incomplete.append(f"negative_coverage_below_minimum:{target}")
    if policy.require_verified_rights:
        incomplete.extend(
            f"rights_not_verified:{case.case_id}" for case in corpus.cases if case.rights_status != "verified"
        )
    if policy.require_exact_asset_bytes:
        blocking.extend(_asset_reasons(corpus, asset_root))

    corpus_cases = {case.case_id: case for case in corpus.cases}
    prediction_cases = {prediction.case_id: prediction for prediction in run.predictions}
    if set(corpus_cases) != set(prediction_cases):
        blocking.append("prediction_case_set_mismatch")
    for case_id in sorted(set(corpus_cases) & set(prediction_cases)):
        if prediction_cases[case_id].input_checksum_sha256.lower() != (
            corpus_cases[case_id].asset_checksum_sha256.lower()
        ):
            blocking.append(f"prediction_input_checksum_mismatch:{case_id}")

    for passed, reason in (
        (run.worker_advertised, "worker_not_advertised"),
        (not policy.require_no_egress or run.no_egress, "no_egress_not_verified"),
        (not policy.require_isolated_tenant or run.isolated_tenant, "isolated_tenant_not_verified"),
        (
            not policy.require_ephemeral_workspace or run.ephemeral_workspace,
            "ephemeral_workspace_not_verified",
        ),
    ):
        if not passed:
            incomplete.append(reason)

    metrics = recompute_metrics(corpus, run) if set(corpus_cases) == set(prediction_cases) else run.reported_metrics
    if not _metrics_equal(metrics, run.reported_metrics):
        blocking.append("reported_metrics_mismatch")
    limits = policy.limits
    for value, maximum, reason in (
        (metrics.speech_false_negative_rate, limits.speech_false_negative_rate_max, "speech_fnr"),
        (metrics.speech_false_positive_rate, limits.speech_false_positive_rate_max, "speech_fpr"),
        (metrics.music_false_negative_rate, limits.music_false_negative_rate_max, "music_fnr"),
        (metrics.music_false_positive_rate, limits.music_false_positive_rate_max, "music_fpr"),
        (metrics.inconclusive_rate, limits.inconclusive_rate_max, "inconclusive_rate"),
    ):
        if value > maximum:
            blocking.append(f"metric_failed:{reason}")

    blocking = sorted(set(blocking))
    incomplete = sorted(set(incomplete))
    decision = "failed" if blocking else "incomplete" if incomplete else "passed"
    evaluator_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return AcousticQualificationAssessmentV1(
        run_id=run.run_id,
        suite_id=run.suite_id,
        provider=run.provider,
        provider_version=run.provider_version,
        model_name=run.model_name,
        model_version=run.model_version,
        model_digest_sha256=run.model_digest_sha256,
        policy_digest_sha256=policy_digest,
        corpus_manifest_digest_sha256=corpus_digest,
        run_digest_sha256=run_digest,
        worker_manifest_digest_sha256=run.worker_manifest_digest_sha256,
        license_review_digest_sha256=run.license_review_digest_sha256,
        conversion_provenance_digest_sha256=run.conversion_provenance_digest_sha256,
        decision=decision,
        blocking_reasons=blocking,
        incomplete_reasons=incomplete,
        recomputed_metrics=metrics,
        evaluator_digest_sha256=evaluator_digest,
        evaluated_at=evaluated_at,
    )


def sign_acoustic_promotion_receipt(
    assessment: AcousticQualificationAssessmentV1,
    *,
    secret: str,
    signer_key_id: str,
) -> AcousticPromotionReceiptV1:
    if assessment.decision != "passed":
        raise ValueError("only_passed_acoustic_assessments_can_be_signed")
    if len(secret) < 32:
        raise ValueError("acoustic_promotion_secret_too_short")
    payload = _canonical_bytes(assessment)
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return AcousticPromotionReceiptV1(
        assessment=assessment,
        signer_key_id=signer_key_id,
        signature_hmac_sha256=signature,
    )


def verify_acoustic_promotion_receipt(
    receipt: AcousticPromotionReceiptV1,
    *,
    secret: str,
) -> bool:
    if len(secret) < 32 or receipt.assessment.decision != "passed":
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        _canonical_bytes(receipt.assessment),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, receipt.signature_hmac_sha256.lower())


def acoustic_registration_promotion_digest(
    receipt: AcousticPromotionReceiptV1,
    *,
    secret: str,
    signer_key_id: str,
    provider: str,
    provider_version: str,
    model_name: str,
    model_version: str,
    model_digest_sha256: str,
    model_receipt_digest_sha256: str,
) -> str:
    """Return the immutable receipt digest or fail on any registration drift."""
    if receipt.signer_key_id != signer_key_id or not verify_acoustic_promotion_receipt(
        receipt,
        secret=secret,
    ):
        raise ValueError("acoustic_detector_promotion_receipt_invalid")
    assessment = receipt.assessment
    if assessment.provider != provider or assessment.provider_version != provider_version:
        raise ValueError("acoustic_detector_promotion_binding_invalid")
    if (
        assessment.model_name != model_name
        or assessment.model_version != model_version
        or assessment.model_digest_sha256.lower() != model_digest_sha256.lower()
    ):
        raise ValueError("acoustic_model_promotion_binding_invalid")
    receipt_digest = contract_digest(receipt)
    if model_receipt_digest_sha256.lower() != receipt_digest:
        raise ValueError("acoustic_model_promotion_binding_invalid")
    return receipt_digest
