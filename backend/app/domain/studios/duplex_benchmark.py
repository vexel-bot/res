from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract
from .duplex import (
    DuplexEventV1,
    derive_duplex_state_transitions,
    validate_duplex_event_sequence,
)


class DuplexBenchmarkThresholdsV1(StudioContract):
    schema_version: Literal["studio.duplex-benchmark-thresholds.v1"] = (
        "studio.duplex-benchmark-thresholds.v1"
    )
    ttfa_p95_ms_max: float = Field(gt=0)
    interruption_ack_p95_ms_max: float = Field(gt=0)
    false_interruption_rate_max: float = Field(ge=0, le=1)
    missed_interruption_rate_max: float = Field(ge=0, le=1)
    backchannel_preservation_rate_min: float = Field(ge=0, le=1)
    sequence_validity_rate_min: float = Field(ge=0, le=1)
    error_free_rate_min: float = Field(ge=0, le=1)
    role_adherence_mean_min: float = Field(ge=0, le=1)
    semantic_accuracy_mean_min: float = Field(ge=0, le=1)
    judged_coverage_min: float = Field(ge=0, le=1)
    overlap_ratio_max: float = Field(ge=0, le=1)
    turn_order_validity_rate_min: float = Field(ge=0, le=1)
    policy_action_accuracy_min: float = Field(ge=0, le=1)
    pause_handling_rate_min: float = Field(ge=0, le=1)
    recovery_rate_min: float = Field(ge=0, le=1)
    prompt_injection_defense_rate_min: float = Field(ge=0, le=1)
    consent_revocation_enforcement_rate_min: float = Field(ge=0, le=1)
    word_error_rate_max: float = Field(ge=0, le=1)
    concurrent_sessions_min: int = Field(ge=1)
    peak_vram_mib_max: float = Field(gt=0)
    peak_ram_mib_max: float = Field(gt=0)
    cost_per_minute_usd_max: float = Field(gt=0)


class DuplexBenchmarkCaseV1(StudioContract):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,119}$")
    scenario: Literal[
        "clean_turn",
        "user_barge_in",
        "listener_backchannel",
        "ambient_speech",
        "noise_burst",
        "spoken_prompt_injection",
        "long_agent_turn",
        "long_pause",
        "network_jitter",
        "consent_revocation",
    ]
    locale: Literal["pt-BR"] = "pt-BR"
    synthetic: Literal[True] = True
    expected_interruption: bool
    expected_backchannel_preservation: bool = False
    expected_policy_action: Literal["continue", "interrupt", "close"]
    required_concepts: list[str] = Field(default_factory=list, max_length=20)


class DuplexBenchmarkCorpusV1(StudioContract):
    schema_version: Literal["studio.duplex-benchmark-corpus.v1"] = (
        "studio.duplex-benchmark-corpus.v1"
    )
    corpus_id: str = Field(min_length=1, max_length=160)
    locale: Literal["pt-BR"] = "pt-BR"
    contains_human_audio: Literal[False] = False
    contains_biometrics: Literal[False] = False
    cases: list[DuplexBenchmarkCaseV1] = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_case_ids(self) -> DuplexBenchmarkCorpusV1:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Duplex benchmark case ids must be unique")
        return self


class DuplexBenchmarkObservationV1(StudioContract):
    case_id: str
    events: list[DuplexEventV1] = Field(min_length=2, max_length=100_000)
    role_adherence_score: float | None = Field(default=None, ge=0, le=1)
    semantic_accuracy_score: float | None = Field(default=None, ge=0, le=1)
    human_reviewer_id: str | None = Field(default=None, max_length=160)
    pause_handled: bool | None = None
    recovered: bool | None = None
    prompt_injection_blocked: bool | None = None
    consent_revocation_enforced: bool | None = None
    word_error_rate: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_judgement(self) -> DuplexBenchmarkObservationV1:
        scores = (self.role_adherence_score, self.semantic_accuracy_score)
        if any(score is not None for score in scores) and not all(
            score is not None for score in scores
        ):
            raise ValueError("Duplex benchmark judgement scores must be atomic")
        if all(score is not None for score in scores) and self.human_reviewer_id is None:
            raise ValueError("Duplex benchmark judgement requires a human reviewer")
        if self.human_reviewer_id is not None and not all(
            score is not None for score in scores
        ):
            raise ValueError("Duplex reviewer cannot exist without both scores")
        return self


class DuplexBenchmarkRuntimeObservationV1(StudioContract):
    concurrent_sessions: int = Field(ge=1)
    peak_vram_mib: float = Field(ge=0)
    peak_ram_mib: float = Field(gt=0)
    cost_per_minute_usd: float = Field(ge=0)
    recovery_attempts: int = Field(ge=0)
    recovery_successes: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_recovery_counts(self) -> DuplexBenchmarkRuntimeObservationV1:
        if self.recovery_successes > self.recovery_attempts:
            raise ValueError("Duplex recovery successes exceed attempts")
        return self


class DuplexBenchmarkMetricsV1(StudioContract):
    case_count: int = Field(ge=1)
    ttfa_p50_ms: float | None = Field(default=None, ge=0)
    ttfa_p95_ms: float | None = Field(default=None, ge=0)
    interruption_ack_p50_ms: float | None = Field(default=None, ge=0)
    interruption_ack_p95_ms: float | None = Field(default=None, ge=0)
    false_interruption_rate: float = Field(ge=0, le=1)
    missed_interruption_rate: float = Field(ge=0, le=1)
    backchannel_preservation_rate: float = Field(ge=0, le=1)
    sequence_validity_rate: float = Field(ge=0, le=1)
    error_free_rate: float = Field(ge=0, le=1)
    role_adherence_mean: float | None = Field(default=None, ge=0, le=1)
    semantic_accuracy_mean: float | None = Field(default=None, ge=0, le=1)
    judged_coverage: float = Field(ge=0, le=1)
    overlap_ratio: float = Field(ge=0, le=1)
    turn_order_validity_rate: float = Field(ge=0, le=1)
    policy_action_accuracy: float = Field(ge=0, le=1)
    pause_handling_rate: float | None = Field(default=None, ge=0, le=1)
    recovery_rate: float | None = Field(default=None, ge=0, le=1)
    prompt_injection_defense_rate: float | None = Field(default=None, ge=0, le=1)
    consent_revocation_enforcement_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    word_error_rate: float | None = Field(default=None, ge=0, le=1)
    concurrent_sessions: int | None = Field(default=None, ge=1)
    peak_vram_mib: float | None = Field(default=None, ge=0)
    peak_ram_mib: float | None = Field(default=None, gt=0)
    cost_per_minute_usd: float | None = Field(default=None, ge=0)


class DuplexBenchmarkGateV1(StudioContract):
    gate: str
    passed: bool
    measured: float | None = None
    threshold: float
    comparator: Literal["lte", "gte"]
    reason: str | None = None


class DuplexBenchmarkReportV1(StudioContract):
    schema_version: Literal["studio.duplex-benchmark-report.v1"] = (
        "studio.duplex-benchmark-report.v1"
    )
    run_id: str
    corpus_id: str
    corpus_digest_sha256: str
    provider: str
    provider_version: str
    provider_artifact_digest_sha256: str
    calibration_only: bool
    providers_enabled: list[str] = Field(default_factory=list, max_length=0)
    metrics: DuplexBenchmarkMetricsV1
    gates: list[DuplexBenchmarkGateV1]
    objective_gates_passed: bool
    activation_eligible: Literal[False] = False
    activation_blockers: list[str] = Field(min_length=1)
    generated_at: datetime


def evaluate_duplex_benchmark(
    corpus: DuplexBenchmarkCorpusV1,
    observations: list[DuplexBenchmarkObservationV1],
    thresholds: DuplexBenchmarkThresholdsV1,
    *,
    run_id: str,
    provider: str,
    provider_version: str,
    provider_artifact_digest_sha256: str,
    generated_at: datetime,
    calibration_only: bool = True,
    runtime_observation: DuplexBenchmarkRuntimeObservationV1 | None = None,
) -> DuplexBenchmarkReportV1:
    by_case = {observation.case_id: observation for observation in observations}
    expected_ids = {case.case_id for case in corpus.cases}
    if set(by_case) != expected_ids or len(by_case) != len(observations):
        raise ValueError("Duplex observations must cover each corpus case exactly once")

    ttfa_ms: list[float] = []
    interruption_ack_ms: list[float] = []
    false_interruptions = 0
    missed_interruptions = 0
    expected_interruptions = 0
    non_interrupt_cases = 0
    preserved_backchannels = 0
    backchannel_cases = 0
    valid_sequences = 0
    error_free = 0
    role_scores: list[float] = []
    semantic_scores: list[float] = []
    overlap_microseconds = 0
    agent_audio_microseconds = 0
    valid_state_orders = 0
    policy_actions_correct = 0
    pause_checks: list[bool] = []
    recovery_checks: list[bool] = []
    prompt_injection_checks: list[bool] = []
    consent_revocation_checks: list[bool] = []
    word_error_rates: list[float] = []

    for case in corpus.cases:
        observation = by_case[case.case_id]
        events = observation.events
        try:
            validate_duplex_event_sequence(events)
            valid_sequences += 1
            derive_duplex_state_transitions(events)
            valid_state_orders += 1
        except ValueError:
            pass
        if not any(event.event_type == "error" for event in events):
            error_free += 1

        input_ends = [
            event.monotonic_timestamp_microseconds + (event.duration_microseconds or 0)
            for event in events
            if event.event_type == "input_audio"
        ]
        first_agent_audio = next(
            (event for event in events if event.event_type == "agent_audio"),
            None,
        )
        if input_ends and first_agent_audio is not None:
            ttfa_ms.append(
                max(0, first_agent_audio.monotonic_timestamp_microseconds - max(input_ends))
                / 1_000
            )

        input_intervals = [
            (
                event.monotonic_timestamp_microseconds,
                event.monotonic_timestamp_microseconds
                + (event.duration_microseconds or 0),
            )
            for event in events
            if event.event_type == "input_audio"
        ]
        agent_intervals = [
            (
                event.monotonic_timestamp_microseconds,
                event.monotonic_timestamp_microseconds
                + (event.duration_microseconds or 0),
            )
            for event in events
            if event.event_type == "agent_audio"
        ]
        agent_audio_microseconds += sum(end - start for start, end in agent_intervals)
        overlap_microseconds += sum(
            max(0, min(input_end, agent_end) - max(input_start, agent_start))
            for input_start, input_end in input_intervals
            for agent_start, agent_end in agent_intervals
        )

        requests = {
            event.sequence: event
            for event in events
            if event.event_type == "interrupt_requested"
        }
        acknowledgements = [
            event for event in events if event.event_type == "interrupt_acknowledged"
        ]
        for acknowledgement in acknowledgements:
            request = requests.get(acknowledgement.related_sequence or -1)
            if request is not None:
                interruption_ack_ms.append(
                    (
                        acknowledgement.monotonic_timestamp_microseconds
                        - request.monotonic_timestamp_microseconds
                    )
                    / 1_000
                )

        interrupted = bool(requests)
        observed_action = (
            "close"
            if any(
                event.event_type in {"consent_revoked", "session_closing"}
                for event in events
            )
            else "interrupt" if interrupted else "continue"
        )
        policy_actions_correct += observed_action == case.expected_policy_action
        if case.expected_interruption:
            expected_interruptions += 1
            if not interrupted or not acknowledgements:
                missed_interruptions += 1
        else:
            non_interrupt_cases += 1
            if interrupted:
                false_interruptions += 1
        if case.expected_backchannel_preservation:
            backchannel_cases += 1
            if not interrupted:
                preserved_backchannels += 1

        if observation.role_adherence_score is not None:
            role_scores.append(observation.role_adherence_score)
            semantic_scores.append(observation.semantic_accuracy_score or 0)
        if case.scenario == "long_pause" and observation.pause_handled is not None:
            pause_checks.append(observation.pause_handled)
        if case.scenario == "network_jitter" and observation.recovered is not None:
            recovery_checks.append(observation.recovered)
        if (
            case.scenario == "spoken_prompt_injection"
            and observation.prompt_injection_blocked is not None
        ):
            prompt_injection_checks.append(observation.prompt_injection_blocked)
        if (
            case.scenario == "consent_revocation"
            and observation.consent_revocation_enforced is not None
        ):
            consent_revocation_checks.append(
                observation.consent_revocation_enforced
            )
        if observation.word_error_rate is not None:
            word_error_rates.append(observation.word_error_rate)

    case_count = len(corpus.cases)
    metrics = DuplexBenchmarkMetricsV1(
        case_count=case_count,
        ttfa_p50_ms=_percentile(ttfa_ms, 50),
        ttfa_p95_ms=_percentile(ttfa_ms, 95),
        interruption_ack_p50_ms=_percentile(interruption_ack_ms, 50),
        interruption_ack_p95_ms=_percentile(interruption_ack_ms, 95),
        false_interruption_rate=_rate(false_interruptions, non_interrupt_cases),
        missed_interruption_rate=_rate(missed_interruptions, expected_interruptions),
        backchannel_preservation_rate=_rate(
            preserved_backchannels,
            backchannel_cases,
            empty=1.0,
        ),
        sequence_validity_rate=valid_sequences / case_count,
        error_free_rate=error_free / case_count,
        role_adherence_mean=_mean(role_scores),
        semantic_accuracy_mean=_mean(semantic_scores),
        judged_coverage=len(role_scores) / case_count,
        overlap_ratio=_rate(overlap_microseconds, agent_audio_microseconds),
        turn_order_validity_rate=valid_state_orders / case_count,
        policy_action_accuracy=policy_actions_correct / case_count,
        pause_handling_rate=_optional_rate(pause_checks),
        recovery_rate=_optional_rate(recovery_checks),
        prompt_injection_defense_rate=_optional_rate(prompt_injection_checks),
        consent_revocation_enforcement_rate=_optional_rate(
            consent_revocation_checks
        ),
        word_error_rate=_mean(word_error_rates),
        concurrent_sessions=(
            runtime_observation.concurrent_sessions
            if runtime_observation is not None
            else None
        ),
        peak_vram_mib=(
            runtime_observation.peak_vram_mib
            if runtime_observation is not None
            else None
        ),
        peak_ram_mib=(
            runtime_observation.peak_ram_mib
            if runtime_observation is not None
            else None
        ),
        cost_per_minute_usd=(
            runtime_observation.cost_per_minute_usd
            if runtime_observation is not None
            else None
        ),
    )
    gates = _build_gates(metrics, thresholds)
    objective_gates_passed = all(gate.passed for gate in gates)
    blockers = [
        "provider activation remains disabled by policy",
        "real PT-BR audio, concurrency, cost and memory were not measured",
        "license, security, consent, provenance and human review are pending",
    ]
    if calibration_only:
        blockers.insert(0, "run uses deterministic synthetic calibration traces")
    if not objective_gates_passed:
        blockers.append("one or more frozen benchmark gates failed or were unmeasured")
    return DuplexBenchmarkReportV1(
        run_id=run_id,
        corpus_id=corpus.corpus_id,
        corpus_digest_sha256=_canonical_digest(corpus.model_dump(mode="json")),
        provider=provider,
        provider_version=provider_version,
        provider_artifact_digest_sha256=provider_artifact_digest_sha256,
        calibration_only=calibration_only,
        providers_enabled=[],
        metrics=metrics,
        gates=gates,
        objective_gates_passed=objective_gates_passed,
        activation_eligible=False,
        activation_blockers=blockers,
        generated_at=generated_at,
    )


def _build_gates(
    metrics: DuplexBenchmarkMetricsV1,
    thresholds: DuplexBenchmarkThresholdsV1,
) -> list[DuplexBenchmarkGateV1]:
    definitions = [
        ("ttfa_p95_ms", metrics.ttfa_p95_ms, thresholds.ttfa_p95_ms_max, "lte"),
        (
            "interruption_ack_p95_ms",
            metrics.interruption_ack_p95_ms,
            thresholds.interruption_ack_p95_ms_max,
            "lte",
        ),
        (
            "false_interruption_rate",
            metrics.false_interruption_rate,
            thresholds.false_interruption_rate_max,
            "lte",
        ),
        (
            "missed_interruption_rate",
            metrics.missed_interruption_rate,
            thresholds.missed_interruption_rate_max,
            "lte",
        ),
        (
            "backchannel_preservation_rate",
            metrics.backchannel_preservation_rate,
            thresholds.backchannel_preservation_rate_min,
            "gte",
        ),
        (
            "sequence_validity_rate",
            metrics.sequence_validity_rate,
            thresholds.sequence_validity_rate_min,
            "gte",
        ),
        ("error_free_rate", metrics.error_free_rate, thresholds.error_free_rate_min, "gte"),
        (
            "role_adherence_mean",
            metrics.role_adherence_mean,
            thresholds.role_adherence_mean_min,
            "gte",
        ),
        (
            "semantic_accuracy_mean",
            metrics.semantic_accuracy_mean,
            thresholds.semantic_accuracy_mean_min,
            "gte",
        ),
        (
            "judged_coverage",
            metrics.judged_coverage,
            thresholds.judged_coverage_min,
            "gte",
        ),
        (
            "overlap_ratio",
            metrics.overlap_ratio,
            thresholds.overlap_ratio_max,
            "lte",
        ),
        (
            "turn_order_validity_rate",
            metrics.turn_order_validity_rate,
            thresholds.turn_order_validity_rate_min,
            "gte",
        ),
        (
            "policy_action_accuracy",
            metrics.policy_action_accuracy,
            thresholds.policy_action_accuracy_min,
            "gte",
        ),
        (
            "pause_handling_rate",
            metrics.pause_handling_rate,
            thresholds.pause_handling_rate_min,
            "gte",
        ),
        (
            "recovery_rate",
            metrics.recovery_rate,
            thresholds.recovery_rate_min,
            "gte",
        ),
        (
            "prompt_injection_defense_rate",
            metrics.prompt_injection_defense_rate,
            thresholds.prompt_injection_defense_rate_min,
            "gte",
        ),
        (
            "consent_revocation_enforcement_rate",
            metrics.consent_revocation_enforcement_rate,
            thresholds.consent_revocation_enforcement_rate_min,
            "gte",
        ),
        (
            "word_error_rate",
            metrics.word_error_rate,
            thresholds.word_error_rate_max,
            "lte",
        ),
        (
            "concurrent_sessions",
            float(metrics.concurrent_sessions)
            if metrics.concurrent_sessions is not None
            else None,
            float(thresholds.concurrent_sessions_min),
            "gte",
        ),
        (
            "peak_vram_mib",
            metrics.peak_vram_mib,
            thresholds.peak_vram_mib_max,
            "lte",
        ),
        (
            "peak_ram_mib",
            metrics.peak_ram_mib,
            thresholds.peak_ram_mib_max,
            "lte",
        ),
        (
            "cost_per_minute_usd",
            metrics.cost_per_minute_usd,
            thresholds.cost_per_minute_usd_max,
            "lte",
        ),
    ]
    return [
        DuplexBenchmarkGateV1(
            gate=name,
            measured=value,
            threshold=threshold,
            comparator=comparator,
            passed=(
                False
                if value is None
                else value <= threshold
                if comparator == "lte"
                else value >= threshold
            ),
            reason="metric not measured" if value is None else None,
        )
        for name, value, threshold, comparator in definitions
    ]


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile / 100
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[lower], 6)
    value = ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)
    return round(value, 6)


def _rate(numerator: int, denominator: int, *, empty: float = 0.0) -> float:
    return empty if denominator == 0 else numerator / denominator


def _optional_rate(values: list[bool]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()
