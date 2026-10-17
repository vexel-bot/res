from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.duplex_benchmark import (
    DuplexBenchmarkCorpusV1,
    DuplexBenchmarkObservationV1,
    DuplexBenchmarkThresholdsV1,
    evaluate_duplex_benchmark,
)
from scripts.run_duplex_benchmark import build_calibration_observation

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = REPO_ROOT / "benchmarks/studios/duplex/duplex-ptbr-corpus.v1.json"


@pytest.fixture(autouse=True)
def clean_database() -> None:
    """Keep benchmark contract tests independent from the application database."""


def _inputs():
    payload = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    corpus = DuplexBenchmarkCorpusV1.model_validate(payload["corpus"])
    thresholds = DuplexBenchmarkThresholdsV1.model_validate(payload["thresholds"])
    observations = [build_calibration_observation(case) for case in corpus.cases]
    return corpus, thresholds, observations


def test_calibration_computes_objective_metrics_but_cannot_activate() -> None:
    corpus, thresholds, observations = _inputs()
    report = evaluate_duplex_benchmark(
        corpus,
        observations,
        thresholds,
        run_id="test-calibration",
        provider="fixture.duplex-calibration",
        provider_version="1.0.0",
        provider_artifact_digest_sha256="a" * 64,
        generated_at=datetime(2026, 8, 28, tzinfo=UTC),
    )

    assert report.metrics.case_count == 10
    assert report.metrics.ttfa_p95_ms == 221.5
    assert report.metrics.interruption_ack_p95_ms == 120
    assert report.metrics.false_interruption_rate == 0
    assert report.metrics.missed_interruption_rate == 0
    assert report.metrics.backchannel_preservation_rate == 1
    assert report.metrics.sequence_validity_rate == 1
    assert report.metrics.role_adherence_mean is None
    assert report.metrics.judged_coverage == 0
    assert report.metrics.overlap_ratio == 0
    assert report.metrics.turn_order_validity_rate == 1
    assert report.metrics.policy_action_accuracy == 1
    assert report.metrics.pause_handling_rate == 1
    assert report.metrics.recovery_rate == 1
    assert report.metrics.prompt_injection_defense_rate == 1
    assert report.metrics.consent_revocation_enforcement_rate == 1
    assert report.metrics.word_error_rate is None
    assert report.metrics.concurrent_sessions is None
    assert report.metrics.peak_vram_mib is None
    assert report.metrics.peak_ram_mib is None
    assert report.metrics.cost_per_minute_usd is None
    assert report.objective_gates_passed is False
    assert report.activation_eligible is False
    assert report.providers_enabled == []
    assert {gate.gate for gate in report.gates if not gate.passed} == {
        "role_adherence_mean",
        "semantic_accuracy_mean",
        "judged_coverage",
        "word_error_rate",
        "concurrent_sessions",
        "peak_vram_mib",
        "peak_ram_mib",
        "cost_per_minute_usd",
    }


def test_corpus_and_observation_validation_fail_closed() -> None:
    corpus, _thresholds, observations = _inputs()
    duplicate = corpus.model_copy(update={"cases": [corpus.cases[0], corpus.cases[0]]})
    with pytest.raises(ValidationError, match="case ids must be unique"):
        DuplexBenchmarkCorpusV1.model_validate(duplicate.model_dump())
    with pytest.raises(ValidationError, match="requires a human reviewer"):
        DuplexBenchmarkObservationV1.model_validate(
            {
                **observations[0].model_dump(),
                "role_adherence_score": 1,
                "semantic_accuracy_score": 1,
            }
        )


def test_cli_writes_a_non_promotable_calibration_report(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_duplex_benchmark",
            "--input",
            str(CORPUS_PATH),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT / "backend",
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["calibrationOnly"] is True
    assert report["activationEligible"] is False
    assert report["providersEnabled"] == []
