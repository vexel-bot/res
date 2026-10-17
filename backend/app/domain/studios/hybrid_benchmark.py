"""Frozen benchmark contracts for hybrid video qualification."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract


class HybridBenchmarkCaseV1(StudioContract):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,159}$")
    family: Literal["presenter", "motion", "hybrid"]
    theme: str = Field(min_length=1, max_length=500)
    identity_id: str = Field(min_length=1, max_length=160)
    duration_seconds: int = Field(ge=15, le=20)
    revision_instruction: str = Field(min_length=1, max_length=500)
    required_checks: list[str] = Field(min_length=4, max_length=30)


class HybridBenchmarkPolicyV1(StudioContract):
    schema_version: Literal["studio.hybrid-benchmark-policy.v1"] = (
        "studio.hybrid-benchmark-policy.v1"
    )
    suite_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,159}$")
    cases: list[HybridBenchmarkCaseV1] = Field(min_length=10, max_length=10)
    automatic_correction_limit: Literal[2] = 2
    human_acceptance_threshold: Literal[4] = 4
    screening_only: Literal[True] = True
    avatar_release_minimum_subjects: Literal[10] = 10
    avatar_release_minimum_cases: Literal[30] = 30

    @model_validator(mode="after")
    def family_distribution(self):
        families = ("presenter", "motion", "hybrid")
        counts = {family: sum(case.family == family for case in self.cases) for family in families}
        if counts != {"presenter": 4, "motion": 3, "hybrid": 3}:
            raise ValueError("hybrid_benchmark_requires_4_3_3_distribution")
        if len({case.case_id for case in self.cases}) != 10:
            raise ValueError("hybrid_benchmark_case_ids_duplicate")
        if len({case.identity_id for case in self.cases}) < 2 or len({case.theme for case in self.cases}) < 2:
            raise ValueError("hybrid_benchmark_requires_multiple_themes_and_identities")
        return self


class HybridCostEventV1(StudioContract):
    category: Literal["planning", "api_generation", "gpu", "render", "storage", "human_review"]
    cost_usd: float = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    accepted_output_seconds: float = Field(default=0, ge=0)
    attempt_id: str = Field(min_length=1, max_length=160)


class HybridCostSummaryV1(StudioContract):
    total_cost_usd: float = Field(ge=0)
    accepted_output_seconds: float = Field(ge=0)
    cost_per_accepted_minute_usd: float | None = Field(default=None, ge=0)
    utilization_rate: float = Field(ge=0, le=1)
    attempted_outputs: int = Field(ge=0)
    accepted_outputs: int = Field(ge=0)


def summarize_hybrid_costs(events: list[HybridCostEventV1]) -> HybridCostSummaryV1:
    total = sum(event.cost_usd for event in events)
    accepted = sum(event.accepted_output_seconds for event in events)
    attempts = {event.attempt_id for event in events if event.category in {"api_generation", "gpu", "render"}}
    accepted_attempts = {
        event.attempt_id
        for event in events
        if event.category in {"api_generation", "gpu", "render"} and event.accepted_output_seconds > 0
    }
    return HybridCostSummaryV1(
        total_cost_usd=round(total, 6),
        accepted_output_seconds=accepted,
        cost_per_accepted_minute_usd=round(total / (accepted / 60), 6) if accepted else None,
        utilization_rate=len(accepted_attempts) / len(attempts) if attempts else 0,
        attempted_outputs=len(attempts),
        accepted_outputs=len(accepted_attempts),
    )
