from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

BenchmarkDecision = Literal["passed", "failed", "incomplete"]
BenchmarkRunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
OPAQUE_REFERENCE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"


def _is_opaque_reference(value: str) -> bool:
    return bool(value) and len(value) <= 160 and all(
        character.isalnum() or character in "._-" for character in value
    )


class BenchmarkComponentV1(StudioContract):
    component_id: str = Field(min_length=1, max_length=160)
    kind: Literal["code", "model", "runtime"]
    source_url: str = Field(min_length=1, max_length=4000)
    source_revision: str = Field(min_length=7, max_length=160)
    license: str = Field(min_length=1, max_length=240)
    commercial_use: Literal["approved", "restricted", "unknown"]
    required: bool = True
    notes: str | None = Field(default=None, max_length=2000)


class BenchmarkCandidateV1(StudioContract):
    candidate_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=240)
    role: str = Field(min_length=1, max_length=120)
    execution_capability: Literal[
        "media_cpu",
        "speech_cpu",
        "speech_gpu",
        "vision_gpu",
        "llm_gpu",
    ]
    license_gate: Literal["approved", "review_required", "rejected"]
    benchmark_scope: Literal["consented_private", "synthetic_only", "evidence_only"]
    components: list[BenchmarkComponentV1] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_components(self) -> BenchmarkCandidateV1:
        component_ids = [component.component_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("Benchmark component ids must be unique")
        if self.license_gate == "approved":
            unresolved = [
                component.component_id
                for component in self.components
                if component.commercial_use != "approved"
                or any(
                    marker in component.source_revision.lower()
                    for marker in ("pending", "unresolved", "unknown", "placeholder")
                )
            ]
            if unresolved:
                raise ValueError(
                    f"Approved benchmark candidates require resolved commercial components: {unresolved}"
                )
        return self


class BenchmarkCorpusRequirementsV1(StudioContract):
    manifest_schema: str = Field(min_length=1, max_length=160)
    minimum_subjects: int = Field(ge=0, le=10000)
    minimum_cases: int = Field(ge=1, le=100000)
    minimum_consent_coverage: float = Field(default=1, ge=0, le=1)
    required_locales: list[str] = Field(min_length=1, max_length=30)
    required_scenarios: list[str] = Field(min_length=1, max_length=100)
    raw_biometric_data_allowed_in_repository: bool = False

    @model_validator(mode="after")
    def reject_repository_biometrics(self) -> BenchmarkCorpusRequirementsV1:
        if self.raw_biometric_data_allowed_in_repository:
            raise ValueError("Raw biometric benchmark data must stay outside the repository")
        if len(self.required_scenarios) != len(set(self.required_scenarios)):
            raise ValueError("Benchmark scenario ids must be unique")
        return self


class BenchmarkMetricThresholdV1(StudioContract):
    metric_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=240)
    unit: str = Field(min_length=1, max_length=80)
    aggregation: Literal["mean", "p50", "p95", "maximum", "minimum", "rate", "count"]
    direction: Literal["minimum", "maximum", "exact"]
    threshold: float
    minimum_samples: int = Field(ge=1, le=1000000)
    minimum_unique_reviewers: int = Field(default=0, ge=0, le=10000)
    minimum_ratings_per_case: int = Field(default=0, ge=0, le=100)
    applies_to_roles: list[str] = Field(default_factory=list, max_length=30)
    blocking: bool = True
    rationale: str = Field(min_length=1, max_length=2000)


class BenchmarkPolicyV1(StudioContract):
    schema_version: Literal["studio.benchmark-policy.v1"] = "studio.benchmark-policy.v1"
    suite_id: str = Field(min_length=1, max_length=160)
    policy_version: str = Field(min_length=1, max_length=80)
    capability: str = Field(min_length=1, max_length=160)
    locale: str = Field(min_length=2, max_length=32)
    status: Literal["draft", "frozen", "approved", "retired"]
    frozen_at: datetime
    frozen_by: str = Field(min_length=1, max_length=240)
    corpus: BenchmarkCorpusRequirementsV1
    candidates: list[BenchmarkCandidateV1] = Field(min_length=1, max_length=30)
    thresholds: list[BenchmarkMetricThresholdV1] = Field(min_length=1, max_length=100)
    required_controls: list[str] = Field(min_length=1, max_length=100)
    required_evidence: list[str] = Field(min_length=1, max_length=100)
    notes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_policy(self) -> BenchmarkPolicyV1:
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        metric_ids = [threshold.metric_id for threshold in self.thresholds]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Benchmark candidate ids must be unique")
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("Benchmark metric ids must be unique")
        if len(self.required_controls) != len(set(self.required_controls)):
            raise ValueError("Required benchmark controls must be unique")
        if len(self.required_evidence) != len(set(self.required_evidence)):
            raise ValueError("Required benchmark evidence must be unique")
        known_roles = {candidate.role for candidate in self.candidates}
        unknown_roles = {
            role for threshold in self.thresholds for role in threshold.applies_to_roles if role not in known_roles
        }
        if unknown_roles:
            raise ValueError(f"Thresholds reference unknown candidate roles: {sorted(unknown_roles)}")
        return self


class BenchmarkEnvironmentV1(StudioContract):
    worker_image_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    dependency_lock_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    operating_system: str = Field(min_length=1, max_length=240)
    architecture: str = Field(min_length=1, max_length=80)
    cpu: str = Field(min_length=1, max_length=240)
    ram_gb: float = Field(gt=0, le=4096)
    accelerator: str = Field(min_length=1, max_length=240)
    accelerator_memory_gb: float = Field(ge=0, le=1024)
    isolated_tenant: bool
    no_egress: bool
    ephemeral_workspace: bool
    cleanup_mechanism_available: bool = False
    cleanup_verified: bool


class BenchmarkMeasurementV1(StudioContract):
    metric_id: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=80)
    aggregation: Literal["mean", "p50", "p95", "maximum", "minimum", "rate", "count"]
    value: float
    sample_count: int = Field(ge=1, le=1000000)
    evaluator: str = Field(min_length=1, max_length=240)
    evaluator_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    case_set_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    evidence_asset_ids: list[str] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_evidence_references(self) -> BenchmarkMeasurementV1:
        if any(not _is_opaque_reference(asset_id) for asset_id in self.evidence_asset_ids):
            raise ValueError("Benchmark evidence must use opaque asset ids, never paths or URLs")
        return self


class BenchmarkCorpusCaseV1(StudioContract):
    case_id: str = Field(min_length=1, max_length=160)
    locale: str = Field(min_length=2, max_length=32)
    scenarios: list[str] = Field(min_length=1, max_length=30)
    script_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    synthetic: bool = False
    pseudonymous_subject_id: str | None = Field(default=None, pattern=OPAQUE_REFERENCE_PATTERN)
    reference_asset_id: str | None = Field(default=None, pattern=OPAQUE_REFERENCE_PATTERN)
    reference_checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    consent_grant_id: str | None = Field(default=None, pattern=OPAQUE_REFERENCE_PATTERN)
    consent_evidence_digest_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
    )

    @model_validator(mode="after")
    def validate_case_boundary(self) -> BenchmarkCorpusCaseV1:
        if len(self.scenarios) != len(set(self.scenarios)):
            raise ValueError("Benchmark case scenarios must be unique")
        consent_bound = (
            self.pseudonymous_subject_id,
            self.reference_asset_id,
            self.reference_checksum_sha256,
            self.consent_grant_id,
            self.consent_evidence_digest_sha256,
        )
        if self.synthetic and any(consent_bound):
            raise ValueError("Synthetic benchmark cases cannot carry biometric or consent references")
        if not self.synthetic and not all(consent_bound):
            raise ValueError("Consent-bound benchmark cases require pseudonym, asset, checksum and consent evidence")
        return self


class BenchmarkCorpusManifestV1(StudioContract):
    schema_version: Literal["studio.benchmark-corpus-manifest.v1"] = (
        "studio.benchmark-corpus-manifest.v1"
    )
    corpus_id: str = Field(min_length=1, max_length=160)
    suite_id: str = Field(min_length=1, max_length=160)
    policy_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    created_at: datetime
    cases: list[BenchmarkCorpusCaseV1] = Field(min_length=1, max_length=100000)

    @model_validator(mode="after")
    def validate_manifest(self) -> BenchmarkCorpusManifestV1:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Benchmark corpus case ids must be unique")
        return self


class VoiceCloneCorpusAdmissionV1(StudioContract):
    schema_version: Literal["studio.voice-clone-corpus-admission.v1"] = (
        "studio.voice-clone-corpus-admission.v1"
    )
    suite_id: str = Field(min_length=1, max_length=160)
    policy_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    corpus_manifest_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    decision: Literal["ready", "rejected"]
    subject_count: int = Field(ge=0, le=10000)
    case_count: int = Field(ge=0, le=100000)
    consent_coverage: float = Field(ge=0, le=1)
    scenario_count: int = Field(ge=0, le=100)
    minimum_cases_per_subject: int = Field(ge=0, le=100000)
    blocking_reasons: list[str] = Field(default_factory=list, max_length=100)
    evaluated_at: datetime


def evaluate_voice_clone_corpus_admission(
    policy: BenchmarkPolicyV1,
    manifest: BenchmarkCorpusManifestV1,
    *,
    evaluated_at: datetime | None = None,
) -> VoiceCloneCorpusAdmissionV1:
    if policy.capability != "voice_clone":
        raise ValueError("voice_clone_policy_required")

    blocking: list[str] = []
    policy_digest = benchmark_policy_digest(policy)
    corpus_digest = benchmark_corpus_manifest_digest(manifest)
    if policy.status not in {"frozen", "approved"}:
        blocking.append(f"policy_not_frozen_or_approved:{policy.status}")
    if manifest.suite_id != policy.suite_id:
        blocking.append("corpus_suite_mismatch")
    if manifest.policy_digest_sha256.lower() != policy_digest:
        blocking.append("corpus_policy_digest_mismatch")

    cases = manifest.cases
    if len(cases) < policy.corpus.minimum_cases:
        blocking.append("corpus_case_count_below_minimum")
    if any(case.synthetic for case in cases):
        blocking.append("voice_clone_corpus_contains_synthetic_case")

    subjects = {case.pseudonymous_subject_id for case in cases if case.pseudonymous_subject_id}
    if len(subjects) < policy.corpus.minimum_subjects:
        blocking.append("corpus_subject_count_below_minimum")
    locales = {case.locale for case in cases}
    if locales != set(policy.corpus.required_locales):
        blocking.append("corpus_locale_set_mismatch")
    scenarios = {scenario for case in cases for scenario in case.scenarios}
    if not set(policy.corpus.required_scenarios).issubset(scenarios):
        blocking.append("corpus_required_scenarios_missing")

    consented = [
        case
        for case in cases
        if not case.synthetic
        and case.consent_grant_id
        and case.consent_evidence_digest_sha256
        and case.reference_asset_id
        and case.reference_checksum_sha256
        and case.pseudonymous_subject_id
    ]
    consent_coverage = len(consented) / len(cases) if cases else 0
    if consent_coverage < policy.corpus.minimum_consent_coverage:
        blocking.append("consent_coverage_below_minimum")

    bindings_by_subject: dict[str, set[tuple[str, str, str, str]]] = {}
    grant_subjects: dict[str, set[str]] = {}
    asset_subjects: dict[str, set[str]] = {}
    cases_by_subject = Counter[str]()
    for case in consented:
        subject = str(case.pseudonymous_subject_id)
        grant = str(case.consent_grant_id)
        asset = str(case.reference_asset_id)
        binding = (
            grant,
            str(case.consent_evidence_digest_sha256).lower(),
            asset,
            str(case.reference_checksum_sha256).lower(),
        )
        bindings_by_subject.setdefault(subject, set()).add(binding)
        grant_subjects.setdefault(grant, set()).add(subject)
        asset_subjects.setdefault(asset, set()).add(subject)
        cases_by_subject[subject] += 1
    if any(len(bindings) != 1 for bindings in bindings_by_subject.values()):
        blocking.append("subject_reference_or_consent_binding_drift")
    if any(len(bound_subjects) != 1 for bound_subjects in grant_subjects.values()):
        blocking.append("consent_grant_shared_across_subjects")
    if any(len(bound_subjects) != 1 for bound_subjects in asset_subjects.values()):
        blocking.append("reference_asset_shared_across_subjects")

    minimum_cases_per_subject = (
        math.ceil(policy.corpus.minimum_cases / policy.corpus.minimum_subjects)
        if policy.corpus.minimum_subjects
        else 0
    )
    if subjects and any(
        cases_by_subject[subject] < minimum_cases_per_subject for subject in subjects
    ):
        blocking.append("cases_per_subject_below_balanced_minimum")

    blocking = sorted(set(blocking))
    return VoiceCloneCorpusAdmissionV1(
        suite_id=policy.suite_id,
        policy_digest_sha256=policy_digest,
        corpus_manifest_digest_sha256=corpus_digest,
        decision="rejected" if blocking else "ready",
        subject_count=len(subjects),
        case_count=len(cases),
        consent_coverage=consent_coverage,
        scenario_count=len(scenarios),
        minimum_cases_per_subject=minimum_cases_per_subject,
        blocking_reasons=blocking,
        evaluated_at=evaluated_at or datetime.now(UTC),
    )


class BenchmarkCaseExecutionV1(StudioContract):
    case_id: str = Field(min_length=1, max_length=160)
    status: Literal["succeeded", "failed", "cancelled"]
    generation_job_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    provider: str = Field(min_length=1, max_length=160)
    provider_version: str = Field(min_length=1, max_length=240)
    started_at: datetime
    completed_at: datetime
    output_asset_id: str | None = Field(default=None, pattern=OPAQUE_REFERENCE_PATTERN)
    output_checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    provenance_asset_id: str | None = Field(default=None, pattern=OPAQUE_REFERENCE_PATTERN)
    output_duration_seconds: float | None = Field(default=None, gt=0, le=86400)
    active_compute_seconds: float = Field(ge=0, le=86400)
    peak_vram_gb: float = Field(ge=0, le=1024)
    direct_cost_usd: float = Field(ge=0, le=1000000)
    failure_code: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def validate_execution(self) -> BenchmarkCaseExecutionV1:
        if self.completed_at < self.started_at:
            raise ValueError("Benchmark case completion cannot precede start")
        outputs = (
            self.output_asset_id,
            self.output_checksum_sha256,
            self.provenance_asset_id,
            self.output_duration_seconds,
        )
        if self.status == "succeeded" and not all(outputs):
            raise ValueError("Successful benchmark cases require output and provenance")
        if self.status != "succeeded" and not self.failure_code:
            raise ValueError("Unsuccessful benchmark cases require a failure code")
        return self


class BenchmarkMetricObservationV1(StudioContract):
    observation_id: str = Field(min_length=1, max_length=200)
    metric_id: str = Field(min_length=1, max_length=160)
    case_id: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=80)
    value: float
    evaluator: str = Field(min_length=1, max_length=240)
    evaluator_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    evidence_asset_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    reviewer_pseudonym: str | None = Field(default=None, max_length=160)
    blinded_candidate_label: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_human_score(self) -> BenchmarkMetricObservationV1:
        if self.unit == "mos_1_5" and not 1 <= self.value <= 5:
            raise ValueError("MOS observations must be between 1 and 5")
        return self


class BenchmarkEvidenceBundleV1(StudioContract):
    schema_version: Literal["studio.benchmark-evidence-bundle.v1"] = (
        "studio.benchmark-evidence-bundle.v1"
    )
    bundle_id: str = Field(min_length=1, max_length=160)
    run_id: str = Field(min_length=1, max_length=160)
    suite_id: str = Field(min_length=1, max_length=160)
    candidate_id: str = Field(min_length=1, max_length=160)
    policy_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    corpus_manifest_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    generated_at: datetime
    case_executions: list[BenchmarkCaseExecutionV1] = Field(min_length=1, max_length=100000)
    observations: list[BenchmarkMetricObservationV1] = Field(min_length=1, max_length=1000000)

    @model_validator(mode="after")
    def validate_bundle(self) -> BenchmarkEvidenceBundleV1:
        case_ids = [case.case_id for case in self.case_executions]
        job_ids = [case.generation_job_id for case in self.case_executions]
        output_ids = [case.output_asset_id for case in self.case_executions if case.output_asset_id]
        provenance_ids = [
            case.provenance_asset_id for case in self.case_executions if case.provenance_asset_id
        ]
        observation_ids = [observation.observation_id for observation in self.observations]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Benchmark evidence case ids must be unique")
        if len(job_ids) != len(set(job_ids)):
            raise ValueError("Benchmark generation job ids must be unique")
        if len(output_ids) != len(set(output_ids)):
            raise ValueError("Benchmark output asset ids must be unique")
        if len(provenance_ids) != len(set(provenance_ids)):
            raise ValueError("Benchmark provenance asset ids must be unique")
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("Benchmark observation ids must be unique")
        unknown_case_ids = {
            observation.case_id for observation in self.observations if observation.case_id not in set(case_ids)
        }
        if unknown_case_ids:
            raise ValueError(f"Benchmark observations reference unknown cases: {sorted(unknown_case_ids)}")
        return self


class SpeechBenchmarkCleanupCaseV1(StudioContract):
    case_id: str = Field(min_length=1, max_length=160)
    output_asset_id: str | None = Field(default=None, pattern=OPAQUE_REFERENCE_PATTERN)
    output_checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    deletion_attempted: bool
    deleted: bool
    verified_absent: bool
    failure_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_cleanup(self) -> SpeechBenchmarkCleanupCaseV1:
        if self.deleted and not self.deletion_attempted:
            raise ValueError("Deleted benchmark output requires a deletion attempt")
        if self.verified_absent and self.failure_reason:
            raise ValueError("Verified cleanup cannot carry a failure reason")
        if not self.verified_absent and not self.failure_reason:
            raise ValueError("Unverified cleanup requires a failure reason")
        return self


class SpeechBenchmarkCleanupBundleV1(StudioContract):
    schema_version: Literal["studio.speech-benchmark-cleanup-bundle.v1"] = (
        "studio.speech-benchmark-cleanup-bundle.v1"
    )
    bundle_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    run_id: str = Field(min_length=1, max_length=160)
    generated_at: datetime
    cases: list[SpeechBenchmarkCleanupCaseV1] = Field(min_length=1, max_length=100000)

    @model_validator(mode="after")
    def validate_cases(self) -> SpeechBenchmarkCleanupBundleV1:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Speech benchmark cleanup case ids must be unique")
        return self


class BenchmarkLicenseComponentV1(StudioContract):
    component_id: str = Field(min_length=1, max_length=160)
    source_url: str = Field(min_length=1, max_length=4000)
    source_revision: str = Field(min_length=7, max_length=160)
    artifact_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    declared_license: str = Field(min_length=1, max_length=240)
    license_text_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    commercial_saas_use_allowed: bool | None = None
    decision: Literal["approved", "review_required", "rejected"]
    redistribution_obligations: list[str] = Field(default_factory=list, max_length=100)
    evidence_asset_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)


class BenchmarkLicenseManifestV1(StudioContract):
    schema_version: Literal["studio.benchmark-license-manifest.v1"] = (
        "studio.benchmark-license-manifest.v1"
    )
    manifest_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    suite_id: str = Field(min_length=1, max_length=160)
    candidate_id: str = Field(min_length=1, max_length=160)
    policy_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    audited_at: datetime
    auditor_pseudonym: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    evidence_asset_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    overall_decision: Literal["approved", "review_required", "rejected"]
    components: list[BenchmarkLicenseComponentV1] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_license_manifest(self) -> BenchmarkLicenseManifestV1:
        component_ids = [component.component_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("Benchmark license component ids must be unique")
        if self.overall_decision == "approved" and any(
            component.decision != "approved" or component.commercial_saas_use_allowed is not True
            for component in self.components
        ):
            raise ValueError("Approved license manifest requires every component to be approved for SaaS use")
        return self


class BenchmarkRunV1(StudioContract):
    schema_version: Literal["studio.benchmark-run.v1"] = "studio.benchmark-run.v1"
    run_id: str = Field(min_length=1, max_length=160)
    suite_id: str = Field(min_length=1, max_length=160)
    policy_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    candidate_id: str = Field(min_length=1, max_length=160)
    status: BenchmarkRunStatus
    corpus_manifest_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    subject_count: int = Field(ge=0, le=10000)
    case_count: int = Field(ge=0, le=100000)
    consent_coverage: float = Field(ge=0, le=1)
    started_at: datetime
    completed_at: datetime | None = None
    environment: BenchmarkEnvironmentV1
    component_digests_sha256: dict[str, str] = Field(default_factory=dict, max_length=100)
    controls: dict[str, bool] = Field(default_factory=dict, max_length=100)
    evidence_refs: dict[str, str] = Field(default_factory=dict, max_length=100)
    evidence_bundle_digest_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    license_manifest_digest_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    measurements: list[BenchmarkMeasurementV1] = Field(default_factory=list, max_length=200)
    failure_reason: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_run(self) -> BenchmarkRunV1:
        if self.status == "completed" and not self.completed_at:
            raise ValueError("Completed benchmark run requires completedAt")
        if self.completed_at and self.completed_at < self.started_at:
            raise ValueError("Benchmark completion cannot precede start")
        metric_ids = [measurement.metric_id for measurement in self.measurements]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("Benchmark measurements must be unique by metric id")
        invalid_digests = [
            component_id
            for component_id, digest in self.component_digests_sha256.items()
            if len(digest) != 64 or any(character not in "0123456789abcdefABCDEF" for character in digest)
        ]
        if invalid_digests:
            raise ValueError(f"Invalid component digests: {sorted(invalid_digests)}")
        invalid_evidence = [
            evidence_id
            for evidence_id in self.evidence_refs.values()
            if not _is_opaque_reference(evidence_id)
        ]
        if invalid_evidence:
            raise ValueError("Benchmark evidence refs must be opaque asset ids, never paths or URLs")
        return self


class BenchmarkGateResultV1(StudioContract):
    schema_version: Literal["studio.benchmark-gate-result.v1"] = "studio.benchmark-gate-result.v1"
    run_id: str
    suite_id: str
    candidate_id: str
    policy_digest_sha256: str
    decision: BenchmarkDecision
    blocking_reasons: list[str] = Field(default_factory=list)
    incomplete_reasons: list[str] = Field(default_factory=list)
    failed_metrics: list[str] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    evaluated_at: datetime


def benchmark_policy_digest(policy: BenchmarkPolicyV1) -> str:
    return _contract_digest(policy)


def benchmark_corpus_manifest_digest(manifest: BenchmarkCorpusManifestV1) -> str:
    return _contract_digest(manifest)


def benchmark_evidence_bundle_digest(bundle: BenchmarkEvidenceBundleV1) -> str:
    return _contract_digest(bundle)


def speech_benchmark_cleanup_bundle_digest(bundle: SpeechBenchmarkCleanupBundleV1) -> str:
    return _contract_digest(bundle)


def benchmark_license_manifest_digest(manifest: BenchmarkLicenseManifestV1) -> str:
    return _contract_digest(manifest)


def _contract_digest(contract: StudioContract) -> str:
    canonical = json.dumps(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _threshold_passed(value: float, direction: str, threshold: float) -> bool:
    if direction == "minimum":
        return value >= threshold
    if direction == "maximum":
        return value <= threshold
    return abs(value - threshold) <= 1e-9


def _aggregate_observations(values: list[float], aggregation: str) -> float:
    if aggregation in {"mean", "rate"}:
        return sum(values) / len(values)
    ordered = sorted(values)
    if aggregation == "p50":
        return ordered[math.ceil(0.50 * len(ordered)) - 1]
    if aggregation == "p95":
        return ordered[math.ceil(0.95 * len(ordered)) - 1]
    if aggregation == "maximum":
        return max(values)
    if aggregation == "minimum":
        return min(values)
    if aggregation == "count":
        return float(len(values))
    raise ValueError(f"Unsupported benchmark aggregation: {aggregation}")


def _corpus_reasons(
    policy: BenchmarkPolicyV1,
    run: BenchmarkRunV1,
    candidate: BenchmarkCandidateV1,
    manifest: BenchmarkCorpusManifestV1 | None,
) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    incomplete: list[str] = []
    if manifest is None:
        return blocking, ["missing_corpus_manifest"]
    digest = benchmark_corpus_manifest_digest(manifest)
    if digest != run.corpus_manifest_digest_sha256.lower():
        blocking.append("corpus_manifest_digest_mismatch")
    if manifest.suite_id != run.suite_id or manifest.policy_digest_sha256.lower() != run.policy_digest_sha256.lower():
        blocking.append("corpus_manifest_identity_mismatch")
    if len(manifest.cases) != run.case_count:
        blocking.append("corpus_case_count_mismatch")
    subjects = {case.pseudonymous_subject_id for case in manifest.cases if case.pseudonymous_subject_id}
    if len(subjects) != run.subject_count:
        blocking.append("corpus_subject_count_mismatch")
    consent_cases = [case for case in manifest.cases if not case.synthetic]
    consented = [case for case in consent_cases if case.consent_grant_id and case.consent_evidence_digest_sha256]
    derived_coverage = len(consented) / len(consent_cases) if consent_cases else 1.0
    if abs(derived_coverage - run.consent_coverage) > 1e-9:
        blocking.append("corpus_consent_coverage_mismatch")
    locales = {case.locale for case in manifest.cases}
    missing_locales = set(policy.corpus.required_locales) - locales
    incomplete.extend(f"missing_corpus_locale:{locale}" for locale in sorted(missing_locales))
    scenarios = {scenario for case in manifest.cases for scenario in case.scenarios}
    missing_scenarios = set(policy.corpus.required_scenarios) - scenarios
    incomplete.extend(f"missing_corpus_scenario:{scenario}" for scenario in sorted(missing_scenarios))
    if candidate.benchmark_scope == "synthetic_only" and any(not case.synthetic for case in manifest.cases):
        blocking.append("synthetic_candidate_received_consent_bound_case")
    if candidate.benchmark_scope == "consented_private" and any(case.synthetic for case in manifest.cases):
        blocking.append("consented_candidate_received_synthetic_case")
    return blocking, incomplete


def _evidence_reasons(
    policy: BenchmarkPolicyV1,
    run: BenchmarkRunV1,
    candidate: BenchmarkCandidateV1,
    bundle: BenchmarkEvidenceBundleV1 | None,
) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    incomplete: list[str] = []
    if bundle is None:
        return blocking, ["missing_evidence_bundle"]
    digest = benchmark_evidence_bundle_digest(bundle)
    if not run.evidence_bundle_digest_sha256:
        incomplete.append("missing_evidence_bundle_digest")
    elif digest != run.evidence_bundle_digest_sha256.lower():
        blocking.append("evidence_bundle_digest_mismatch")
    identity = (
        bundle.run_id == run.run_id
        and bundle.suite_id == run.suite_id
        and bundle.candidate_id == candidate.candidate_id
        and bundle.policy_digest_sha256.lower() == run.policy_digest_sha256.lower()
        and bundle.corpus_manifest_digest_sha256.lower() == run.corpus_manifest_digest_sha256.lower()
    )
    if not identity:
        blocking.append("evidence_bundle_identity_mismatch")
    if len(bundle.case_executions) != run.case_count:
        blocking.append("evidence_case_count_mismatch")

    observations_by_metric: dict[str, list[BenchmarkMetricObservationV1]] = {}
    for observation in bundle.observations:
        observations_by_metric.setdefault(observation.metric_id, []).append(observation)
    measurements = {measurement.metric_id: measurement for measurement in run.measurements}
    applicable = [
        threshold
        for threshold in policy.thresholds
        if not threshold.applies_to_roles or candidate.role in threshold.applies_to_roles
    ]
    known_evidence_asset_ids = set(run.evidence_refs.values())
    known_evidence_asset_ids.update(
        asset_id
        for case in bundle.case_executions
        for asset_id in (case.output_asset_id, case.provenance_asset_id)
        if asset_id
    )
    for threshold in applicable:
        measurement = measurements.get(threshold.metric_id)
        if not measurement:
            continue
        observations = observations_by_metric.get(threshold.metric_id, [])
        if len(observations) != measurement.sample_count:
            incomplete.append(f"observation_count_mismatch:{threshold.metric_id}")
            continue
        if any(observation.unit != measurement.unit for observation in observations):
            blocking.append(f"observation_unit_mismatch:{threshold.metric_id}")
            continue
        if any(observation.evaluator != measurement.evaluator for observation in observations):
            blocking.append(f"observation_evaluator_mismatch:{threshold.metric_id}")
        if any(
            observation.evaluator_digest_sha256.lower()
            != measurement.evaluator_digest_sha256.lower()
            for observation in observations
        ):
            blocking.append(f"observation_evaluator_digest_mismatch:{threshold.metric_id}")
        if measurement.case_set_digest_sha256.lower() != run.corpus_manifest_digest_sha256.lower():
            blocking.append(f"measurement_case_set_digest_mismatch:{threshold.metric_id}")
        observation_evidence = {observation.evidence_asset_id for observation in observations}
        if not observation_evidence.issubset(set(measurement.evidence_asset_ids)):
            blocking.append(f"observation_evidence_mismatch:{threshold.metric_id}")
        if not observation_evidence.issubset(known_evidence_asset_ids):
            blocking.append(f"observation_evidence_unknown:{threshold.metric_id}")
        recomputed = _aggregate_observations(
            [observation.value for observation in observations],
            measurement.aggregation,
        )
        tolerance = max(1e-9, abs(recomputed) * 1e-9)
        if abs(recomputed - measurement.value) > tolerance:
            blocking.append(f"measurement_aggregate_mismatch:{threshold.metric_id}")
        if threshold.minimum_unique_reviewers:
            reviewers = {
                observation.reviewer_pseudonym
                for observation in observations
                if observation.reviewer_pseudonym
            }
            if len(reviewers) < threshold.minimum_unique_reviewers:
                incomplete.append(f"reviewer_count_below_minimum:{threshold.metric_id}")
            if any(not observation.blinded_candidate_label for observation in observations):
                blocking.append(f"human_review_not_blinded:{threshold.metric_id}")
        if threshold.minimum_ratings_per_case:
            counts = Counter(observation.case_id for observation in observations)
            if len(counts) != run.case_count or any(
                count < threshold.minimum_ratings_per_case for count in counts.values()
            ):
                incomplete.append(f"ratings_per_case_below_minimum:{threshold.metric_id}")
    return blocking, incomplete


def _license_reasons(
    policy: BenchmarkPolicyV1,
    run: BenchmarkRunV1,
    candidate: BenchmarkCandidateV1,
    manifest: BenchmarkLicenseManifestV1 | None,
) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    incomplete: list[str] = []
    if manifest is None:
        return blocking, ["missing_license_manifest"]
    digest = benchmark_license_manifest_digest(manifest)
    if not run.license_manifest_digest_sha256:
        incomplete.append("missing_license_manifest_digest")
    elif digest != run.license_manifest_digest_sha256.lower():
        blocking.append("license_manifest_digest_mismatch")
    identity = (
        manifest.suite_id == run.suite_id
        and manifest.candidate_id == candidate.candidate_id
        and manifest.policy_digest_sha256.lower() == run.policy_digest_sha256.lower()
    )
    if not identity:
        blocking.append("license_manifest_identity_mismatch")
    if run.evidence_refs.get("license_manifest") != manifest.evidence_asset_id:
        blocking.append("license_manifest_evidence_mismatch")
    expected = {component.component_id: component for component in candidate.components}
    observed = {component.component_id: component for component in manifest.components}
    missing = set(expected) - set(observed)
    extra = set(observed) - set(expected)
    incomplete.extend(f"missing_license_component:{component_id}" for component_id in sorted(missing))
    blocking.extend(f"unscoped_license_component:{component_id}" for component_id in sorted(extra))
    for component_id in sorted(set(expected) & set(observed)):
        policy_component = expected[component_id]
        audited = observed[component_id]
        if (
            audited.source_url != policy_component.source_url
            or audited.source_revision != policy_component.source_revision
            or audited.declared_license != policy_component.license
        ):
            blocking.append(f"license_component_identity_mismatch:{component_id}")
        if audited.commercial_saas_use_allowed is False or audited.decision == "rejected":
            blocking.append(f"license_component_rejected:{component_id}")
        elif audited.commercial_saas_use_allowed is None or audited.decision == "review_required":
            incomplete.append(f"license_component_review_required:{component_id}")
    if manifest.overall_decision == "rejected":
        blocking.append("license_manifest_rejected")
    elif manifest.overall_decision == "review_required":
        incomplete.append("license_manifest_review_required")
    return blocking, incomplete


def evaluate_benchmark_run(
    policy: BenchmarkPolicyV1,
    run: BenchmarkRunV1,
    *,
    corpus_manifest: BenchmarkCorpusManifestV1 | None = None,
    evidence_bundle: BenchmarkEvidenceBundleV1 | None = None,
    license_manifest: BenchmarkLicenseManifestV1 | None = None,
    evaluated_at: datetime | None = None,
) -> BenchmarkGateResultV1:
    policy_digest = benchmark_policy_digest(policy)
    if run.suite_id != policy.suite_id:
        raise ValueError("benchmark_suite_mismatch")
    candidate = next((item for item in policy.candidates if item.candidate_id == run.candidate_id), None)
    if not candidate:
        raise ValueError("benchmark_candidate_not_in_policy")

    blocking: list[str] = []
    incomplete: list[str] = []
    failed_metrics: list[str] = []
    missing_metrics: list[str] = []

    if run.policy_digest_sha256.lower() != policy_digest:
        blocking.append("policy_digest_mismatch")
    if policy.status != "approved":
        incomplete.append(f"policy_not_approved:{policy.status}")
    if candidate.license_gate == "rejected":
        blocking.append("candidate_license_rejected")
    elif candidate.license_gate == "review_required":
        incomplete.append("candidate_license_review_required")
    if any(component.commercial_use == "restricted" for component in candidate.components if component.required):
        blocking.append("required_component_commercial_use_restricted")
    if any(component.commercial_use == "unknown" for component in candidate.components if component.required):
        incomplete.append("required_component_commercial_use_unknown")

    if run.status in {"failed", "cancelled"}:
        blocking.append(f"run_status:{run.status}")
    elif run.status != "completed":
        incomplete.append(f"run_status:{run.status}")
    if run.subject_count < policy.corpus.minimum_subjects:
        incomplete.append("corpus_subject_count_below_minimum")
    if run.case_count < policy.corpus.minimum_cases:
        incomplete.append("corpus_case_count_below_minimum")
    if run.consent_coverage < policy.corpus.minimum_consent_coverage:
        blocking.append("consent_coverage_below_minimum")

    corpus_blocking, corpus_incomplete = _corpus_reasons(policy, run, candidate, corpus_manifest)
    blocking.extend(corpus_blocking)
    incomplete.extend(corpus_incomplete)

    required_components = {component.component_id for component in candidate.components if component.required}
    missing_components = sorted(required_components - run.component_digests_sha256.keys())
    incomplete.extend(f"missing_component_digest:{component_id}" for component_id in missing_components)

    missing_controls = sorted(set(policy.required_controls) - run.controls.keys())
    incomplete.extend(f"missing_control:{control}" for control in missing_controls)
    blocking.extend(
        f"control_failed:{control}" for control in policy.required_controls if run.controls.get(control) is False
    )
    missing_evidence = sorted(set(policy.required_evidence) - run.evidence_refs.keys())
    incomplete.extend(f"missing_evidence:{evidence}" for evidence in missing_evidence)

    environment_controls = {
        "isolated_tenant": run.environment.isolated_tenant,
        "no_egress": run.environment.no_egress,
        "ephemeral_workspace": run.environment.ephemeral_workspace,
        "cleanup_verified": run.environment.cleanup_verified,
    }
    blocking.extend(
        f"environment_control_failed:{control}" for control, passed in environment_controls.items() if not passed
    )

    evidence_blocking, evidence_incomplete = _evidence_reasons(policy, run, candidate, evidence_bundle)
    blocking.extend(evidence_blocking)
    incomplete.extend(evidence_incomplete)
    if corpus_manifest is not None and evidence_bundle is not None:
        corpus_case_ids = {case.case_id for case in corpus_manifest.cases}
        evidence_case_ids = {case.case_id for case in evidence_bundle.case_executions}
        if corpus_case_ids != evidence_case_ids:
            blocking.append("evidence_case_set_mismatch")
    license_blocking, license_incomplete = _license_reasons(policy, run, candidate, license_manifest)
    blocking.extend(license_blocking)
    incomplete.extend(license_incomplete)

    measurements = {measurement.metric_id: measurement for measurement in run.measurements}
    applicable_thresholds = [
        threshold
        for threshold in policy.thresholds
        if not threshold.applies_to_roles or candidate.role in threshold.applies_to_roles
    ]
    for threshold in applicable_thresholds:
        measurement = measurements.get(threshold.metric_id)
        if not measurement:
            missing_metrics.append(threshold.metric_id)
            continue
        if measurement.unit != threshold.unit or measurement.aggregation != threshold.aggregation:
            blocking.append(f"metric_contract_mismatch:{threshold.metric_id}")
            continue
        if measurement.sample_count < threshold.minimum_samples:
            incomplete.append(f"metric_sample_count_below_minimum:{threshold.metric_id}")
            continue
        if not _threshold_passed(measurement.value, threshold.direction, threshold.threshold):
            if threshold.blocking:
                failed_metrics.append(threshold.metric_id)
            else:
                incomplete.append(f"non_blocking_metric_below_threshold:{threshold.metric_id}")

    incomplete.extend(f"missing_metric:{metric_id}" for metric_id in missing_metrics)
    blocking.extend(f"metric_failed:{metric_id}" for metric_id in failed_metrics)
    blocking = sorted(set(blocking))
    incomplete = sorted(set(incomplete))
    decision: BenchmarkDecision = "failed" if blocking else "incomplete" if incomplete else "passed"
    return BenchmarkGateResultV1(
        run_id=run.run_id,
        suite_id=run.suite_id,
        candidate_id=run.candidate_id,
        policy_digest_sha256=policy_digest,
        decision=decision,
        blocking_reasons=blocking,
        incomplete_reasons=incomplete,
        failed_metrics=sorted(set(failed_metrics)),
        missing_metrics=sorted(set(missing_metrics)),
        evaluated_at=evaluated_at or datetime.now(UTC),
    )
