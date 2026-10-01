import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.studios.artifacts import (
    ProviderCandidateManifestV1,
    provider_candidate_manifest_digest,
)
from app.domain.studios.reality_benchmark import (
    RealityPerceptionBenchmarkReportV1,
    RealityPerceptionEnvironmentV1,
    RealityPerceptionObservationV1,
    SyntheticRealityCorpusV1,
    evaluate_reality_perception_report,
    reality_perception_report_digest,
    synthetic_reality_corpus_digest,
)

ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "benchmarks" / "studios" / "reality" / "opencv-baseline-corpus.v1.json"
CANDIDATE_PATH = ROOT / "workers" / "vision-gpu" / "providers" / "opencv-baseline.provider.json"
EVIDENCE_PATH = (
    ROOT
    / "benchmarks"
    / "studios"
    / "reality"
    / "opencv-baseline-run-2026-08-25.v1.json"
)
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
SHA = "a" * 64


def load_corpus() -> SyntheticRealityCorpusV1:
    return SyntheticRealityCorpusV1.model_validate_json(CORPUS_PATH.read_text(encoding="utf-8"))


def load_candidate() -> ProviderCandidateManifestV1:
    return ProviderCandidateManifestV1.model_validate_json(
        CANDIDATE_PATH.read_text(encoding="utf-8")
    )


def complete_report(corpus: SyntheticRealityCorpusV1) -> RealityPerceptionBenchmarkReportV1:
    observations = []
    for case in corpus.cases:
        expectation = case.expectation
        observations.append(
            RealityPerceptionObservationV1(
                case_id=case.case_id,
                source_checksum_sha256=SHA,
                motion_by_shot={
                    shot_id: labels[0]
                    for shot_id, labels in expectation.accepted_motion_by_shot.items()
                },
                horizon_present_by_shot=expectation.horizon_present_by_shot,
                gravity_present_by_shot=expectation.gravity_present_by_shot,
                track_count_by_shot=expectation.minimum_tracks_by_shot,
                model_status=expectation.expected_model_status,
                abstained_principles=expectation.required_abstentions,
                provider_versions={"opensource.opencv-geometry": "test"},
                code_digests_sha256={"opensource.opencv-geometry": SHA},
                evidence_digest_sha256=SHA,
            )
        )
    return RealityPerceptionBenchmarkReportV1(
        report_id="report-contract-001",
        corpus_id=corpus.corpus_id,
        corpus_digest_sha256=synthetic_reality_corpus_digest(corpus),
        candidate_id=corpus.candidate_id,
        candidate_manifest_digest_sha256=corpus.candidate_manifest_digest_sha256,
        generated_at=NOW,
        environment=RealityPerceptionEnvironmentV1(
            python_version="3.11.9",
            opencv_version="4.13.0",
            numpy_version="2.2.6",
            operating_system="Linux",
            architecture="x86_64",
            dependency_lock_digest_sha256=SHA,
            isolated_environment=True,
            synthetic_only=True,
        ),
        observations=observations,
    )


def test_frozen_corpus_is_versioned_and_covers_every_required_scenario():
    raw = CORPUS_PATH.read_text(encoding="utf-8")
    corpus = SyntheticRealityCorpusV1.model_validate_json(raw)
    assert corpus.schema_version == "studio.synthetic-reality-corpus.v1"
    assert set(corpus.required_scenarios) <= {
        scenario for case in corpus.cases for scenario in case.scenarios
    }
    assert len(synthetic_reality_corpus_digest(corpus)) == 64
    json.loads(raw)


def test_complete_technical_report_cannot_activate_evaluation_candidate():
    corpus = load_corpus()
    candidate = load_candidate()
    report = complete_report(corpus)

    result = evaluate_reality_perception_report(
        corpus,
        candidate,
        report,
        evaluated_at=NOW,
    )

    assert result.technical_decision == "passed"
    assert result.activation_decision == "incomplete"
    assert "candidate_status:evaluation" in result.incomplete_reasons
    assert result.failed_metrics == []
    assert result.failed_cases == []
    assert reality_perception_report_digest(report) == result.report_digest_sha256


def test_tampered_report_binding_is_blocked():
    corpus = load_corpus()
    candidate = load_candidate()
    report = complete_report(corpus).model_copy(
        update={"candidate_manifest_digest_sha256": "b" * 64}
    )

    result = evaluate_reality_perception_report(
        corpus,
        candidate,
        report,
        evaluated_at=NOW,
    )

    assert result.technical_decision == "failed"
    assert result.activation_decision == "blocked"
    assert "candidate_binding_mismatch" in result.blocking_reasons


def test_missing_observation_is_incomplete_and_never_passes():
    corpus = load_corpus()
    candidate = load_candidate()
    report = complete_report(corpus).model_copy(
        update={"observations": complete_report(corpus).observations[:-1]}
    )

    result = evaluate_reality_perception_report(
        corpus,
        candidate,
        report,
        evaluated_at=NOW,
    )

    assert result.technical_decision == "incomplete"
    assert result.activation_decision == "incomplete"
    assert any(item.startswith("missing_case:") for item in result.incomplete_reasons)


def test_candidate_digest_is_the_frozen_manifest_digest():
    corpus = load_corpus()
    candidate = load_candidate()
    assert provider_candidate_manifest_digest(candidate) == corpus.candidate_manifest_digest_sha256


def test_committed_opencv_evidence_matches_the_frozen_contract_and_keeps_activation_blocked():
    corpus = load_corpus()
    candidate = load_candidate()
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    assert evidence["corpus_digest_sha256"] == synthetic_reality_corpus_digest(corpus)
    assert evidence["candidate_manifest_digest_sha256"] == provider_candidate_manifest_digest(candidate)
    assert evidence["technical_decision"] == "passed"
    assert evidence["activation_decision"] == "incomplete"
    assert evidence["incomplete_reasons"] == ["candidate_status:evaluation"]
    assert evidence["corpus"]["case_count"] == len(corpus.cases)
    assert evidence["corpus"]["failed_cases"] == []
    assert evidence["corpus"]["failed_metrics"] == []
    assert evidence["environment"]["isolated_environment"] is True
    assert evidence["environment"]["synthetic_only"] is True


@pytest.mark.parametrize("field", ["corpus_digest_sha256", "candidate_manifest_digest_sha256"])
def test_report_digest_changes_when_binding_changes(field: str):
    corpus = load_corpus()
    report = complete_report(corpus)
    altered = report.model_copy(update={field: "c" * 64})
    assert reality_perception_report_digest(altered) != reality_perception_report_digest(report)


def test_runner_rejects_runtime_that_does_not_match_provider_lock(tmp_path: Path):
    from scripts.run_opencv_reality_benchmark import _assert_runtime_matches_lock

    matching = tmp_path / "matching.lock"
    matching.write_text(
        "numpy==2.4.4 --hash=sha256:" + "a" * 64 + "\n"
        "opencv-python-headless==4.13.0 --hash=sha256:" + "b" * 64 + "\n",
        encoding="utf-8",
    )
    _assert_runtime_matches_lock(matching, SimpleNamespace(__version__="4.13.0"))

    mismatched = tmp_path / "mismatched.lock"
    mismatched.write_text(
        "numpy==0.0.0 --hash=sha256:" + "a" * 64 + "\n"
        "opencv-python-headless==4.13.0 --hash=sha256:" + "b" * 64 + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="evaluation runtime does not match provider lock"):
        _assert_runtime_matches_lock(mismatched, SimpleNamespace(__version__="4.13.0"))
