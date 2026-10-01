from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.duplex import DuplexEventV1
from app.domain.studios.duplex_benchmark import (
    DuplexBenchmarkCorpusV1,
    DuplexBenchmarkObservationV1,
    DuplexBenchmarkThresholdsV1,
    evaluate_duplex_benchmark,
)


def _digest(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _event(
    case_id: str,
    sequence: int,
    event_type: str,
    timestamp_us: int,
    **payload: object,
) -> DuplexEventV1:
    return DuplexEventV1.model_validate(
        {
            "sessionId": f"calibration-{case_id}",
            "sequence": sequence,
            "idempotencyKey": f"{case_id}-event-{sequence:03d}",
            "eventType": event_type,
            "monotonicTimestampMicroseconds": timestamp_us,
            **payload,
        }
    )


def build_calibration_observation(case) -> DuplexBenchmarkObservationV1:
    case_id = case.case_id
    events = [
        _event(case_id, 0, "session_started", 0),
        _event(
            case_id,
            1,
            "input_audio",
            100_000,
            turnId="turn-user-001",
            durationMicroseconds=400_000,
            audioDigestSha256=_digest(f"{case_id}:input"),
        ),
        _event(
            case_id,
            2,
            "agent_audio",
            780_000 if case.scenario == "network_jitter" else 650_000,
            turnId="turn-agent-001",
            durationMicroseconds=600_000,
            audioDigestSha256=_digest(f"{case_id}:agent"),
        ),
    ]
    sequence = 3
    if case.scenario == "listener_backchannel":
        events.append(
            _event(
                case_id,
                sequence,
                "backchannel",
                900_000,
                turnId="turn-user-002",
                text="Uhum.",
            )
        )
        sequence += 1
    if case.expected_interruption:
        events.extend(
            [
                _event(
                    case_id,
                    sequence,
                    "interrupt_requested",
                    900_000,
                    turnId="turn-agent-001",
                    reason=(
                        "user_barge_in"
                        if case.scenario == "user_barge_in"
                        else "policy"
                    ),
                ),
                _event(
                    case_id,
                    sequence + 1,
                    "interrupt_acknowledged",
                    1_020_000,
                    turnId="turn-agent-001",
                    reason="audio_stopped",
                    relatedSequence=sequence,
                ),
            ]
        )
        sequence += 2
    if case.scenario == "consent_revocation":
        events.append(
            _event(
                case_id,
                sequence,
                "consent_revoked",
                1_100_000,
                reason="consent_grant_revoked",
            )
        )
        sequence += 1
    events.append(
        _event(
            case_id,
            sequence,
            "session_closed",
            1_300_000,
            reason=(
                "consent_revoked"
                if case.scenario == "consent_revocation"
                else "completed"
            ),
        )
    )
    return DuplexBenchmarkObservationV1(
        case_id=case_id,
        events=events,
        pause_handled=True if case.scenario == "long_pause" else None,
        recovered=True if case.scenario == "network_jitter" else None,
        prompt_injection_blocked=(
            True if case.scenario == "spoken_prompt_injection" else None
        ),
        consent_revocation_enforced=(
            True if case.scenario == "consent_revocation" else None
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    corpus = DuplexBenchmarkCorpusV1.model_validate(payload["corpus"])
    thresholds = DuplexBenchmarkThresholdsV1.model_validate(payload["thresholds"])
    observations = [build_calibration_observation(case) for case in corpus.cases]
    report = evaluate_duplex_benchmark(
        corpus,
        observations,
        thresholds,
        run_id="duplex-ptbr-calibration-2026-08-28",
        provider="fixture.duplex-calibration",
        provider_version="1.0.0",
        provider_artifact_digest_sha256=_digest("fixture.duplex-calibration:1.0.0"),
        generated_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
        calibration_only=True,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
