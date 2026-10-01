from __future__ import annotations

import json
from pathlib import Path

from app.domain.studios.benchmarking import BenchmarkPolicyV1, benchmark_policy_digest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "benchmarks/studios/identity/kokoro-pf-dora-local-run-2026-08-26.v1.json"
)


def test_local_kokoro_evidence_is_fail_closed_and_policy_bound():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    policy = BenchmarkPolicyV1.model_validate_json(
        (
            ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json"
        ).read_text(encoding="utf-8")
    )

    assert evidence["policy_digest_sha256"] == benchmark_policy_digest(policy)
    assert evidence["case_count"] == 64
    assert evidence["subject_count"] == 0
    assert evidence["technical_decision"] == "failed"
    assert evidence["activation_decision"] == "failed"
    assert evidence["automated_metrics"]["job_failure_rate"]["value"] == 0
    assert evidence["automated_metrics"]["p95_real_time_factor"]["passed"] is False
    assert evidence["controls"]["provider_advertised"] is False
    assert evidence["controls"]["cleanup_execution_verified"] is False
    assert evidence["controls"]["valid_for_provider_promotion"] is False


def test_benchmark_environment_distinguishes_cleanup_mechanism_from_execution():
    from app.domain.studios.benchmarking import BenchmarkEnvironmentV1

    environment = BenchmarkEnvironmentV1(
        worker_image_digest_sha256="a" * 64,
        dependency_lock_digest_sha256="b" * 64,
        operating_system="linux",
        architecture="amd64",
        cpu="evaluation-cpu",
        ram_gb=3,
        accelerator="none",
        accelerator_memory_gb=0,
        isolated_tenant=True,
        no_egress=True,
        ephemeral_workspace=True,
        cleanup_mechanism_available=True,
        cleanup_verified=False,
    )

    assert environment.cleanup_mechanism_available is True
    assert environment.cleanup_verified is False
