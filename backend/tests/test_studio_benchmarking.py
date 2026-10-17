import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.studios.benchmarking import (
    BenchmarkCaseExecutionV1,
    BenchmarkCorpusCaseV1,
    BenchmarkCorpusManifestV1,
    BenchmarkEnvironmentV1,
    BenchmarkEvidenceBundleV1,
    BenchmarkLicenseComponentV1,
    BenchmarkLicenseManifestV1,
    BenchmarkMeasurementV1,
    BenchmarkMetricObservationV1,
    BenchmarkPolicyV1,
    BenchmarkRunV1,
    benchmark_corpus_manifest_digest,
    benchmark_evidence_bundle_digest,
    benchmark_license_manifest_digest,
    benchmark_policy_digest,
    evaluate_benchmark_run,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = ROOT / "benchmarks" / "studios" / "identity"
NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
SHA = "a" * 64


def load_policy(name: str) -> BenchmarkPolicyV1:
    return BenchmarkPolicyV1.model_validate_json((POLICY_DIR / name).read_text(encoding="utf-8"))


def complete_run(policy: BenchmarkPolicyV1, candidate_id: str) -> BenchmarkRunV1:
    approved = policy.model_copy(update={"status": "approved"})
    candidate = next(candidate for candidate in approved.candidates if candidate.candidate_id == candidate_id)
    measurements = []
    for threshold in approved.thresholds:
        if threshold.applies_to_roles and candidate.role not in threshold.applies_to_roles:
            continue
        if threshold.direction == "minimum":
            value = threshold.threshold
        elif threshold.direction == "maximum":
            value = threshold.threshold
        else:
            value = threshold.threshold
        measurements.append(
            BenchmarkMeasurementV1(
                metric_id=threshold.metric_id,
                unit=threshold.unit,
                aggregation=threshold.aggregation,
                value=value,
                sample_count=threshold.minimum_samples,
                evaluator="clicko.benchmark.fake-contract-v1",
                evaluator_digest_sha256=SHA,
                case_set_digest_sha256=SHA,
                evidence_asset_ids=[f"private-evidence-{threshold.metric_id}"],
            )
        )
    return BenchmarkRunV1(
        run_id="run-contract-001",
        suite_id=approved.suite_id,
        policy_digest_sha256=benchmark_policy_digest(approved),
        candidate_id=candidate_id,
        status="completed",
        corpus_manifest_digest_sha256=SHA,
        subject_count=approved.corpus.minimum_subjects,
        case_count=approved.corpus.minimum_cases,
        consent_coverage=approved.corpus.minimum_consent_coverage,
        started_at=NOW,
        completed_at=NOW,
        environment=BenchmarkEnvironmentV1(
            worker_image_digest_sha256=SHA,
            dependency_lock_digest_sha256=SHA,
            operating_system="Debian 12",
            architecture="amd64",
            cpu="benchmark-cpu",
            ram_gb=64,
            accelerator="NVIDIA benchmark GPU",
            accelerator_memory_gb=24,
            isolated_tenant=True,
            no_egress=True,
            ephemeral_workspace=True,
            cleanup_verified=True,
        ),
        component_digests_sha256={component.component_id: SHA for component in candidate.components},
        controls={control: True for control in approved.required_controls},
        evidence_refs={evidence: f"private-{evidence}-asset" for evidence in approved.required_evidence},
        measurements=measurements,
    )


def complete_evidence(
    policy: BenchmarkPolicyV1,
    candidate_id: str,
) -> tuple[
    BenchmarkRunV1,
    BenchmarkCorpusManifestV1,
    BenchmarkEvidenceBundleV1,
    BenchmarkLicenseManifestV1,
]:
    approved = policy.model_copy(update={"status": "approved"})
    candidate = next(candidate for candidate in approved.candidates if candidate.candidate_id == candidate_id)
    synthetic = candidate.benchmark_scope == "synthetic_only"
    cases = [
        BenchmarkCorpusCaseV1(
            case_id=f"case-{index:03d}",
            locale=approved.locale,
            scenarios=approved.corpus.required_scenarios,
            script_digest_sha256=SHA,
            synthetic=synthetic,
            pseudonymous_subject_id=None if synthetic else f"subject-{index % 10:02d}",
            reference_asset_id=None if synthetic else f"private-reference-{index:03d}",
            reference_checksum_sha256=None if synthetic else SHA,
            consent_grant_id=None if synthetic else f"consent-{index % 10:02d}",
            consent_evidence_digest_sha256=None if synthetic else SHA,
        )
        for index in range(approved.corpus.minimum_cases)
    ]
    manifest = BenchmarkCorpusManifestV1(
        corpus_id="private-corpus-001",
        suite_id=approved.suite_id,
        policy_digest_sha256=benchmark_policy_digest(approved),
        created_at=NOW,
        cases=cases,
    )
    corpus_digest = benchmark_corpus_manifest_digest(manifest)
    run = complete_run(approved, candidate_id)
    measurements = [
        measurement.model_copy(
            update={
                "case_set_digest_sha256": corpus_digest,
                "evidence_asset_ids": [
                    run.evidence_refs[
                        "blinded_human_review"
                        if measurement.unit == "mos_1_5"
                        else "raw_metric_bundle"
                    ]
                ],
            }
        )
        for measurement in run.measurements
    ]
    run = run.model_copy(
        update={
            "corpus_manifest_digest_sha256": corpus_digest,
            "subject_count": 0 if synthetic else 10,
            "consent_coverage": 1,
            "measurements": measurements,
        }
    )
    executions = [
        BenchmarkCaseExecutionV1(
            case_id=case.case_id,
            status="succeeded",
            generation_job_id=f"job-{case.case_id}",
            provider=candidate.candidate_id,
            provider_version="pinned-test-revision",
            started_at=NOW,
            completed_at=NOW,
            output_asset_id=f"private-output-{case.case_id}",
            output_checksum_sha256=SHA,
            provenance_asset_id=f"private-provenance-{case.case_id}",
            output_duration_seconds=1,
            active_compute_seconds=0.5,
            peak_vram_gb=1,
            direct_cost_usd=0.001,
        )
        for case in cases
    ]
    observations: list[BenchmarkMetricObservationV1] = []
    for measurement in measurements:
        for index in range(measurement.sample_count):
            observations.append(
                BenchmarkMetricObservationV1(
                    observation_id=f"{measurement.metric_id}-{index:04d}",
                    metric_id=measurement.metric_id,
                    case_id=cases[index % len(cases)].case_id,
                    unit=measurement.unit,
                    value=measurement.value,
                    evaluator=measurement.evaluator,
                    evaluator_digest_sha256=measurement.evaluator_digest_sha256,
                    evidence_asset_id=measurement.evidence_asset_ids[0],
                    reviewer_pseudonym=(
                        f"reviewer-{index % 3}" if measurement.unit == "mos_1_5" else None
                    ),
                    blinded_candidate_label=(
                        "candidate-A" if measurement.unit == "mos_1_5" else None
                    ),
                )
            )
    bundle = BenchmarkEvidenceBundleV1(
        bundle_id="private-evidence-bundle-001",
        run_id=run.run_id,
        suite_id=run.suite_id,
        candidate_id=run.candidate_id,
        policy_digest_sha256=run.policy_digest_sha256,
        corpus_manifest_digest_sha256=corpus_digest,
        generated_at=NOW,
        case_executions=executions,
        observations=observations,
    )
    license_manifest = BenchmarkLicenseManifestV1(
        manifest_id="license-manifest-001",
        suite_id=run.suite_id,
        candidate_id=run.candidate_id,
        policy_digest_sha256=run.policy_digest_sha256,
        audited_at=NOW,
        auditor_pseudonym="legal-reviewer-001",
        evidence_asset_id=run.evidence_refs["license_manifest"],
        overall_decision="approved",
        components=[
            BenchmarkLicenseComponentV1(
                component_id=component.component_id,
                source_url=component.source_url,
                source_revision=component.source_revision,
                artifact_digest_sha256=SHA,
                declared_license=component.license,
                license_text_digest_sha256=SHA,
                commercial_saas_use_allowed=True,
                decision="approved",
                evidence_asset_id=f"license-evidence-{index:02d}",
            )
            for index, component in enumerate(candidate.components)
        ],
    )
    run = run.model_copy(
        update={
            "evidence_bundle_digest_sha256": benchmark_evidence_bundle_digest(bundle),
            "license_manifest_digest_sha256": benchmark_license_manifest_digest(license_manifest),
        }
    )
    return run, manifest, bundle, license_manifest


def test_committed_benchmark_policies_are_frozen_and_contain_no_private_asset_paths():
    for name in (
        "voice-pt-br-policy.v1.json",
        "voice-stock-pt-br-policy.v1.json",
        "avatar-pt-br-policy.v1.json",
    ):
        raw = (POLICY_DIR / name).read_text(encoding="utf-8")
        policy = BenchmarkPolicyV1.model_validate_json(raw)
        assert policy.status == "frozen"
        assert policy.corpus.raw_biometric_data_allowed_in_repository is False
        assert "s3://" not in raw and "C:\\" not in raw and "/home/" not in raw
        assert len(benchmark_policy_digest(policy)) == 64
        json.loads(raw)


def test_approved_voice_policy_can_pass_only_with_complete_evidence():
    policy = load_policy("voice-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run, manifest, bundle, license_manifest = complete_evidence(policy, "chatterbox-pt-br")
    result = evaluate_benchmark_run(
        policy,
        run,
        corpus_manifest=manifest,
        evidence_bundle=bundle,
        license_manifest=license_manifest,
        evaluated_at=NOW,
    )
    assert result.decision == "passed"
    assert result.blocking_reasons == []
    assert result.incomplete_reasons == []


def test_frozen_policy_and_missing_real_run_never_claim_success():
    policy = load_policy("voice-pt-br-policy.v1.json")
    candidate = policy.candidates[0]
    run = BenchmarkRunV1(
        run_id="run-not-executed",
        suite_id=policy.suite_id,
        policy_digest_sha256=benchmark_policy_digest(policy),
        candidate_id=candidate.candidate_id,
        status="pending",
        corpus_manifest_digest_sha256=SHA,
        subject_count=0,
        case_count=0,
        consent_coverage=0,
        started_at=NOW,
        environment=BenchmarkEnvironmentV1(
            worker_image_digest_sha256=SHA,
            dependency_lock_digest_sha256=SHA,
            operating_system="not-provisioned",
            architecture="amd64",
            cpu="not-provisioned",
            ram_gb=1,
            accelerator="none",
            accelerator_memory_gb=0,
            isolated_tenant=False,
            no_egress=False,
            ephemeral_workspace=False,
            cleanup_verified=False,
        ),
    )
    result = evaluate_benchmark_run(policy, run, evaluated_at=NOW)
    assert result.decision == "failed"
    assert "policy_not_approved:frozen" in result.incomplete_reasons
    assert "consent_coverage_below_minimum" in result.blocking_reasons
    assert result.missing_metrics


def test_failed_blocking_metric_blocks_candidate():
    policy = load_policy("voice-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run = complete_run(policy, "chatterbox-multilingual-v3")
    changed = [
        measurement.model_copy(update={"value": 0.5})
        if measurement.metric_id == "critical_term_accuracy"
        else measurement
        for measurement in run.measurements
    ]
    run = run.model_copy(update={"measurements": changed})
    result = evaluate_benchmark_run(policy, run, evaluated_at=NOW)
    assert result.decision == "failed"
    assert "critical_term_accuracy" in result.failed_metrics


def test_aggregate_only_run_is_incomplete_even_when_thresholds_look_green():
    policy = load_policy("voice-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run = complete_run(policy, "chatterbox-pt-br")
    result = evaluate_benchmark_run(policy, run, evaluated_at=NOW)
    assert result.decision == "incomplete"
    assert "missing_corpus_manifest" in result.incomplete_reasons
    assert "missing_evidence_bundle" in result.incomplete_reasons
    assert "missing_license_manifest" in result.incomplete_reasons


def test_stock_voice_has_separate_synthetic_corpus_and_license_gate():
    policy = load_policy("voice-stock-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run, manifest, bundle, license_manifest = complete_evidence(policy, "kokoro-82m-stock")
    result = evaluate_benchmark_run(
        policy,
        run,
        corpus_manifest=manifest,
        evidence_bundle=bundle,
        license_manifest=license_manifest,
        evaluated_at=NOW,
    )
    assert run.subject_count == 0
    assert all(case.synthetic for case in manifest.cases)
    assert result.decision == "incomplete"
    assert "candidate_license_review_required" in result.incomplete_reasons


def test_tampered_aggregate_is_recomputed_and_blocked():
    policy = load_policy("voice-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run, manifest, bundle, license_manifest = complete_evidence(policy, "chatterbox-pt-br")
    measurements = [
        measurement.model_copy(update={"value": 4.5})
        if measurement.metric_id == "human_naturalness_mos"
        else measurement
        for measurement in run.measurements
    ]
    result = evaluate_benchmark_run(
        policy,
        run.model_copy(update={"measurements": measurements}),
        corpus_manifest=manifest,
        evidence_bundle=bundle,
        license_manifest=license_manifest,
        evaluated_at=NOW,
    )
    assert result.decision == "failed"
    assert "measurement_aggregate_mismatch:human_naturalness_mos" in result.blocking_reasons


def test_human_mos_must_be_blinded_and_have_three_raters_per_case():
    policy = load_policy("voice-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run, manifest, bundle, license_manifest = complete_evidence(policy, "chatterbox-pt-br")
    observations = [
        observation.model_copy(update={"blinded_candidate_label": None})
        if observation.metric_id == "human_naturalness_mos"
        else observation
        for observation in bundle.observations
    ]
    tampered = bundle.model_copy(update={"observations": observations})
    run = run.model_copy(
        update={"evidence_bundle_digest_sha256": benchmark_evidence_bundle_digest(tampered)}
    )
    result = evaluate_benchmark_run(
        policy,
        run,
        corpus_manifest=manifest,
        evidence_bundle=tampered,
        license_manifest=license_manifest,
        evaluated_at=NOW,
    )
    assert result.decision == "failed"
    assert "human_review_not_blinded:human_naturalness_mos" in result.blocking_reasons


def test_corpus_and_evidence_must_contain_the_same_cases():
    policy = load_policy("voice-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run, manifest, bundle, license_manifest = complete_evidence(policy, "chatterbox-pt-br")
    changed_cases = [
        case.model_copy(update={"case_id": "case-replaced"}) if case.case_id == "case-000" else case
        for case in bundle.case_executions
    ]
    changed_observations = [
        observation.model_copy(update={"case_id": "case-replaced"})
        if observation.case_id == "case-000"
        else observation
        for observation in bundle.observations
    ]
    tampered = bundle.model_copy(
        update={"case_executions": changed_cases, "observations": changed_observations}
    )
    run = run.model_copy(
        update={"evidence_bundle_digest_sha256": benchmark_evidence_bundle_digest(tampered)}
    )
    result = evaluate_benchmark_run(
        policy,
        run,
        corpus_manifest=manifest,
        evidence_bundle=tampered,
        license_manifest=license_manifest,
        evaluated_at=NOW,
    )
    assert result.decision == "failed"
    assert "evidence_case_set_mismatch" in result.blocking_reasons


def test_metric_evaluator_digest_and_evidence_asset_are_verified():
    policy = load_policy("voice-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run, manifest, bundle, license_manifest = complete_evidence(policy, "chatterbox-pt-br")
    observations = [
        observation.model_copy(
            update={
                "evaluator_digest_sha256": "b" * 64,
                "evidence_asset_id": "unknown-evidence",
            }
        )
        if observation.metric_id == "critical_term_accuracy"
        else observation
        for observation in bundle.observations
    ]
    tampered = bundle.model_copy(update={"observations": observations})
    run = run.model_copy(
        update={"evidence_bundle_digest_sha256": benchmark_evidence_bundle_digest(tampered)}
    )
    result = evaluate_benchmark_run(
        policy,
        run,
        corpus_manifest=manifest,
        evidence_bundle=tampered,
        license_manifest=license_manifest,
        evaluated_at=NOW,
    )
    assert result.decision == "failed"
    assert "observation_evaluator_digest_mismatch:critical_term_accuracy" in result.blocking_reasons
    assert "observation_evidence_unknown:critical_term_accuracy" in result.blocking_reasons


def test_private_contracts_reject_paths_and_urls_instead_of_asset_ids():
    with pytest.raises(ValueError, match="opaque asset ids"):
        BenchmarkMeasurementV1(
            metric_id="metric",
            unit="ratio",
            aggregation="mean",
            value=1,
            sample_count=1,
            evaluator="evaluator",
            evaluator_digest_sha256=SHA,
            case_set_digest_sha256=SHA,
            evidence_asset_ids=["s3://private-bucket/raw.json"],
        )


def test_license_manifest_is_digest_bound_and_matches_every_policy_component():
    policy = load_policy("voice-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run, manifest, bundle, license_manifest = complete_evidence(policy, "chatterbox-pt-br")
    first = license_manifest.components[0]
    components = [
        first.model_copy(update={"source_revision": "different-revision"}),
        *license_manifest.components[1:],
    ]
    tampered = license_manifest.model_copy(update={"components": components})
    run = run.model_copy(
        update={"license_manifest_digest_sha256": benchmark_license_manifest_digest(tampered)}
    )
    result = evaluate_benchmark_run(
        policy,
        run,
        corpus_manifest=manifest,
        evidence_bundle=bundle,
        license_manifest=tampered,
        evaluated_at=NOW,
    )
    assert result.decision == "failed"
    assert f"license_component_identity_mismatch:{first.component_id}" in result.blocking_reasons


def test_latentsync_weight_and_detector_license_gate_is_explicitly_rejected():
    policy = load_policy("avatar-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run = complete_run(policy, "latentsync-1-6")
    result = evaluate_benchmark_run(policy, run, evaluated_at=NOW)
    assert result.decision == "failed"
    assert "candidate_license_rejected" in result.blocking_reasons
    assert "required_component_commercial_use_restricted" in result.blocking_reasons


def test_musetalk_transitive_syncnet_and_weight_licenses_are_rejected():
    policy = load_policy("avatar-pt-br-policy.v1.json").model_copy(update={"status": "approved"})
    run = complete_run(policy, "musetalk-1-5")
    result = evaluate_benchmark_run(policy, run, evaluated_at=NOW)
    assert result.decision == "failed"
    assert "candidate_license_rejected" in result.blocking_reasons
    assert "required_component_commercial_use_restricted" in result.blocking_reasons
