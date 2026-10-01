import json
from pathlib import Path

from app.domain.studios.hybrid_benchmark import (
    HybridBenchmarkPolicyV1,
    HybridCostEventV1,
    summarize_hybrid_costs,
)

ROOT = Path(__file__).resolve().parents[2]


def test_hybrid_screening_policy_is_frozen_and_not_avatar_release_evidence():
    payload = json.loads((ROOT / "benchmarks/studios/hybrid/hybrid-video-screening-policy.v1.json").read_text("utf-8"))
    policy = HybridBenchmarkPolicyV1.model_validate(payload)
    assert policy.screening_only is True
    assert len(policy.cases) == 10
    assert policy.avatar_release_minimum_cases == 30


def test_cost_per_accepted_minute_includes_rejected_attempts():
    summary = summarize_hybrid_costs(
        [
            HybridCostEventV1(category="api_generation", costUsd=0.50, elapsedSeconds=30, attemptId="bad"),
            HybridCostEventV1(
                category="api_generation", costUsd=0.50, elapsedSeconds=30,
                acceptedOutputSeconds=15, attemptId="good",
            ),
            HybridCostEventV1(category="human_review", costUsd=0.25, elapsedSeconds=120, attemptId="review"),
        ]
    )
    assert summary.total_cost_usd == 1.25
    assert summary.cost_per_accepted_minute_usd == 5
    assert summary.utilization_rate == 0.5
