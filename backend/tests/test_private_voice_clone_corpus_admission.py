from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.benchmarking import (
    BenchmarkCorpusCaseV1,
    BenchmarkCorpusManifestV1,
    BenchmarkPolicyV1,
    benchmark_policy_digest,
    evaluate_voice_clone_corpus_admission,
)
from scripts.validate_private_voice_clone_corpus import validate_private_corpus

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "benchmarks/studios/identity/voice-pt-br-policy.v1.json"
NOW = datetime(2026, 8, 27, 14, 0, tzinfo=UTC)


def _policy() -> BenchmarkPolicyV1:
    return BenchmarkPolicyV1.model_validate_json(POLICY_PATH.read_text(encoding="utf-8"))


def _manifest(policy: BenchmarkPolicyV1) -> BenchmarkCorpusManifestV1:
    cases = []
    scenarios = policy.corpus.required_scenarios
    for subject_index in range(10):
        for case_index in range(6):
            ordinal = subject_index * 6 + case_index
            cases.append(
                BenchmarkCorpusCaseV1(
                    case_id=f"case-{ordinal:03d}",
                    locale="pt-BR",
                    scenarios=[scenarios[ordinal % len(scenarios)]],
                    script_digest_sha256=f"{ordinal + 1:064x}",
                    synthetic=False,
                    pseudonymous_subject_id=f"subject-{subject_index:02d}",
                    reference_asset_id=f"reference-{subject_index:02d}",
                    reference_checksum_sha256=f"{subject_index + 101:064x}",
                    consent_grant_id=f"consent-{subject_index:02d}",
                    consent_evidence_digest_sha256=f"{subject_index + 201:064x}",
                )
            )
    return BenchmarkCorpusManifestV1(
        corpus_id="private-voice-clone-corpus-v1",
        suite_id=policy.suite_id,
        policy_digest_sha256=benchmark_policy_digest(policy),
        created_at=NOW,
        cases=cases,
    )


def test_balanced_private_corpus_is_ready_without_exposing_identifiers() -> None:
    policy = _policy()
    admission = evaluate_voice_clone_corpus_admission(
        policy,
        _manifest(policy),
        evaluated_at=NOW,
    )

    assert admission.decision == "ready"
    assert admission.subject_count == 10
    assert admission.case_count == 60
    assert admission.consent_coverage == 1
    assert admission.scenario_count == len(policy.corpus.required_scenarios)
    assert admission.minimum_cases_per_subject == 6
    serialized = admission.model_dump_json(by_alias=True)
    assert "subject-" not in serialized
    assert "consent-" not in serialized
    assert "reference-" not in serialized


def test_admission_rejects_binding_drift_and_unbalanced_subjects() -> None:
    policy = _policy()
    manifest = _manifest(policy)
    cases = list(manifest.cases)
    cases[0] = cases[0].model_copy(update={"reference_asset_id": "different-reference"})
    cases[6] = cases[6].model_copy(update={"pseudonymous_subject_id": "subject-00"})
    admission = evaluate_voice_clone_corpus_admission(
        policy,
        manifest.model_copy(update={"cases": cases}),
        evaluated_at=NOW,
    )

    assert admission.decision == "rejected"
    assert "subject_reference_or_consent_binding_drift" in admission.blocking_reasons
    assert "cases_per_subject_below_balanced_minimum" in admission.blocking_reasons


def test_cli_boundary_refuses_private_manifest_inside_repository(tmp_path: Path) -> None:
    inside_repository = ROOT / "benchmarks/studios/identity/private-do-not-write.json"
    report = tmp_path / "admission-report.json"

    try:
        validate_private_corpus(POLICY_PATH, inside_repository, report)
    except ValueError as exc:
        assert str(exc) == "private_manifest_must_stay_outside_repository"
    else:
        raise AssertionError("private manifest inside Git must be rejected")


def test_cli_emits_only_safe_report_outside_repository(tmp_path: Path) -> None:
    policy = _policy()
    manifest_path = tmp_path / "private-manifest.json"
    report_path = tmp_path / "admission-report.json"
    manifest_path.write_text(_manifest(policy).model_dump_json(by_alias=True), encoding="utf-8")

    report = validate_private_corpus(POLICY_PATH, manifest_path, report_path)

    assert report["decision"] == "ready"
    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert written == report
    assert "cases" not in written
    assert "subjects" not in written
