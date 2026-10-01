from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.studios.duplex import (
    DuplexAudioFormatV1,
    DuplexEventV1,
    DuplexInputAudioFrameV1,
    DuplexInterruptRequestV1,
    DuplexProviderLineageV1,
    DuplexRetentionPolicyV1,
    DuplexRetentionReceiptV1,
    DuplexRolePromptReferenceV1,
    DuplexSessionCloseReceiptV1,
    DuplexSessionPolicyV1,
    DuplexSessionRequestV1,
    DuplexVoiceProfileReferenceV1,
    build_duplex_replay_manifest,
    derive_duplex_state_transitions,
    duplex_policy_digest,
    validate_duplex_event_sequence,
)

FROZEN_TIME = datetime(2026, 8, 28, 1, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    """Keep this pure contract suite independent from the application database."""


def _policy(*, retention: DuplexRetentionPolicyV1 | None = None) -> DuplexSessionPolicyV1:
    return DuplexSessionPolicyV1(
        policy_id="duplex-policy-ptbr-v1",
        version=1,
        locale="pt-BR",
        retention=retention or DuplexRetentionPolicyV1(mode="zero"),
    )


def _request(*, voice_kind: str = "stock") -> DuplexSessionRequestV1:
    policy = _policy()
    voice = (
        DuplexVoiceProfileReferenceV1(
            voice_profile_id="voice-stock-bruna",
            version=1,
            digest_sha256="b" * 64,
            kind="stock",
        )
        if voice_kind == "stock"
        else DuplexVoiceProfileReferenceV1(
            voice_profile_id="voice-private-consented",
            version=2,
            digest_sha256="b" * 64,
            kind="consented_clone",
            consent_grant_id="consent-voice-converse-001",
        )
    )
    return DuplexSessionRequestV1(
        session_id="duplex-session-001",
        workspace_id="workspace-duplex-test",
        actor_id="actor-duplex-test",
        idempotency_key="duplex-start-001",
        role_prompt=DuplexRolePromptReferenceV1(
            prompt_id="role-sales-director-ptbr",
            version=3,
            digest_sha256="a" * 64,
        ),
        voice_profile=voice,
        policy=policy,
        policy_digest_sha256=duplex_policy_digest(policy),
        input_format=DuplexAudioFormatV1(
            encoding="pcm_s16le",
            sample_rate_hz=24_000,
            channels=1,
            frame_duration_ms=20,
        ),
        output_format=DuplexAudioFormatV1(
            encoding="opus",
            sample_rate_hz=24_000,
            channels=1,
            frame_duration_ms=20,
        ),
        requested_at=FROZEN_TIME,
    )


def _events() -> list[DuplexEventV1]:
    return [
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=0,
            idempotency_key="event-000",
            event_type="session_started",
            monotonic_timestamp_microseconds=0,
        ),
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=1,
            idempotency_key="event-001",
            event_type="input_audio",
            monotonic_timestamp_microseconds=100_000,
            turn_id="turn-user-001",
            duration_microseconds=400_000,
            audio_digest_sha256="1" * 64,
        ),
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=2,
            idempotency_key="event-002",
            event_type="agent_audio",
            monotonic_timestamp_microseconds=550_000,
            turn_id="turn-agent-001",
            duration_microseconds=500_000,
            audio_digest_sha256="2" * 64,
        ),
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=3,
            idempotency_key="event-003",
            event_type="interrupt_requested",
            monotonic_timestamp_microseconds=700_000,
            turn_id="turn-agent-001",
            reason="user_barge_in",
        ),
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=4,
            idempotency_key="event-004",
            event_type="interrupt_acknowledged",
            monotonic_timestamp_microseconds=760_000,
            turn_id="turn-agent-001",
            reason="audio_stopped",
            related_sequence=3,
        ),
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=5,
            idempotency_key="event-005",
            event_type="backchannel",
            monotonic_timestamp_microseconds=900_000,
            turn_id="turn-user-002",
            text="Entendi.",
        ),
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=6,
            idempotency_key="event-006",
            event_type="agent_text",
            monotonic_timestamp_microseconds=1_000_000,
            turn_id="turn-agent-002",
            text="Vamos ajustar o anúncio.",
        ),
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=7,
            idempotency_key="event-007",
            event_type="session_closed",
            monotonic_timestamp_microseconds=1_200_000,
            reason="completed",
        ),
    ]


def _close_receipt() -> DuplexSessionCloseReceiptV1:
    return DuplexSessionCloseReceiptV1(
        session_id="duplex-session-001",
        close_reason="completed",
        final_sequence=7,
        event_count=8,
        retention=DuplexRetentionReceiptV1(
            session_id="duplex-session-001",
            mode="zero",
            deleted_at=FROZEN_TIME,
            receipt_digest_sha256="f" * 64,
        ),
        closed_at=FROZEN_TIME,
    )


def _lineage() -> DuplexProviderLineageV1:
    return DuplexProviderLineageV1(
        provider="fake.duplex-provider",
        provider_version="1.0.0",
        code_digest_sha256="c" * 64,
        parameters_digest_sha256="d" * 64,
        worker_manifest_digest_sha256="e" * 64,
        generated_at=FROZEN_TIME,
    )


def test_session_contract_binds_policy_role_voice_and_consent() -> None:
    stock = _request()
    cloned = _request(voice_kind="consented_clone")

    assert stock.policy.locale == "pt-BR"
    assert stock.policy_digest_sha256 == duplex_policy_digest(stock.policy)
    assert stock.role_prompt.digest_sha256 == "a" * 64
    assert stock.voice_profile.kind == "stock"
    assert cloned.voice_profile.consent_grant_id == "consent-voice-converse-001"

    with pytest.raises(ValidationError, match="requires a consent grant"):
        DuplexVoiceProfileReferenceV1(
            voice_profile_id="invalid-clone",
            version=1,
            digest_sha256="a" * 64,
            kind="consented_clone",
        )


def test_policy_digest_and_zero_retention_fail_closed() -> None:
    valid = _request().model_dump(mode="python")
    valid["policy_digest_sha256"] = "0" * 64

    with pytest.raises(ValidationError, match="policy digest mismatch"):
        DuplexSessionRequestV1.model_validate(valid)
    with pytest.raises(ValidationError, match="cannot retain content"):
        DuplexRetentionPolicyV1(
            mode="zero",
            retain_raw_audio=True,
        )
    with pytest.raises(ValidationError, match="requires ttl_seconds"):
        DuplexRetentionPolicyV1(mode="ttl")


def test_input_audio_payload_is_bound_by_size_and_checksum() -> None:
    payload = b"synthetic-pcm-frame"
    frame = DuplexInputAudioFrameV1(
        session_id="duplex-session-001",
        sequence=1,
        idempotency_key="input-frame-001",
        turn_id="turn-user-001",
        monotonic_timestamp_microseconds=100_000,
        duration_microseconds=20_000,
        payload_size_bytes=len(payload),
        payload_digest_sha256=hashlib.sha256(payload).hexdigest(),
    )

    frame.validate_payload(payload)
    with pytest.raises(ValueError, match="size mismatch"):
        frame.validate_payload(payload + b"x")
    with pytest.raises(ValueError, match="digest mismatch"):
        frame.validate_payload(b"synthetic-pcm-framf")


def test_replay_is_deterministic_and_contains_no_inline_audio() -> None:
    request = _request()
    events = _events()
    first = build_duplex_replay_manifest(
        request,
        events,
        _lineage(),
        _close_receipt(),
        generated_at=FROZEN_TIME,
    )
    second = build_duplex_replay_manifest(
        request,
        events,
        _lineage(),
        _close_receipt(),
        generated_at=FROZEN_TIME,
    )

    assert first == second
    assert first.event_count == 8
    assert first.input_audio_events == 1
    assert first.agent_audio_events == 1
    assert first.interruption_requests == 1
    assert first.interruption_acknowledgements == 1
    assert first.backchannels == 1
    assert first.final_state == "closed"
    assert len(first.state_transition_digests_sha256) == first.event_count
    assert first.raw_audio_retained is False
    assert first.transcript_retained is False
    assert all(len(item) == 64 for item in first.event_digests_sha256)
    assert not hasattr(first, "audio")

    other_workspace = request.model_copy(update={"workspace_id": "workspace-other"})
    other = build_duplex_replay_manifest(
        other_workspace,
        events,
        _lineage(),
        _close_receipt(),
        generated_at=FROZEN_TIME,
    )
    assert other.replay_id != first.replay_id
    assert other.workspace_id == "workspace-other"


def test_explicit_state_machine_covers_interruption_and_consent_revocation() -> None:
    transitions = derive_duplex_state_transitions(_events())
    assert transitions[0].from_state == "created"
    assert transitions[0].to_state == "listening"
    assert transitions[2].to_state == "speaking"
    assert transitions[3].to_state == "interrupted"
    assert transitions[4].to_state == "listening"
    assert transitions[-1].to_state == "closed"

    consent_events = [
        _events()[0],
        _events()[1],
        _events()[2],
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=3,
            idempotency_key="event-consent-revoked",
            event_type="consent_revoked",
            monotonic_timestamp_microseconds=700_000,
            reason="consent_grant_revoked",
        ),
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=4,
            idempotency_key="event-consent-closed",
            event_type="session_closed",
            monotonic_timestamp_microseconds=710_000,
            reason="consent_revoked",
        ),
    ]
    consent_transitions = derive_duplex_state_transitions(consent_events)
    assert consent_transitions[-2].to_state == "closing"
    assert consent_transitions[-1].to_state == "closed"
    validate_duplex_event_sequence(consent_events)


def test_sequence_and_interrupt_bindings_fail_closed() -> None:
    events = _events()
    invalid_sequence = [event.model_copy(deep=True) for event in events]
    invalid_sequence[2] = invalid_sequence[2].model_copy(update={"sequence": 8})
    with pytest.raises(ValueError, match="contiguous"):
        validate_duplex_event_sequence(invalid_sequence)

    invalid_time = [event.model_copy(deep=True) for event in events]
    invalid_time[4] = invalid_time[4].model_copy(
        update={"monotonic_timestamp_microseconds": 1}
    )
    with pytest.raises(ValueError, match="monotonic"):
        validate_duplex_event_sequence(invalid_time)

    invalid_ack = [event.model_copy(deep=True) for event in events]
    invalid_ack[4] = invalid_ack[4].model_copy(update={"related_sequence": 2})
    with pytest.raises(ValueError, match="unbound"):
        validate_duplex_event_sequence(invalid_ack)


@pytest.mark.parametrize(
    "metadata",
    [
        {"path": "voice.pt"},
        {"source": "C:\\voices\\voice.pt"},
        {"source": "https://model-host.invalid/file"},
        {"hub_token": "secret"},
    ],
)
def test_event_metadata_rejects_paths_urls_and_tokens(
    metadata: dict[str, str],
) -> None:
    with pytest.raises(ValidationError, match="paths, URLs or tokens|resembles"):
        DuplexEventV1(
            session_id="duplex-session-001",
            sequence=0,
            idempotency_key="event-metadata-invalid",
            event_type="session_started",
            monotonic_timestamp_microseconds=0,
            metadata=metadata,
        )


class _FakeDuplexSession:
    session_id = "duplex-session-001"

    def __init__(self) -> None:
        self.received: list[bytes] = []

    async def push_audio(
        self,
        frame: DuplexInputAudioFrameV1,
        payload: bytes,
        progress,
        is_cancelled,
    ) -> None:
        if is_cancelled():
            raise InterruptedError("fake_duplex_cancelled")
        frame.validate_payload(payload)
        self.received.append(payload)
        progress(100)

    async def events(self) -> AsyncIterator[DuplexEventV1]:
        for event in _events():
            yield event

    async def interrupt(self, request, progress, is_cancelled) -> DuplexEventV1:
        assert isinstance(request, DuplexInterruptRequestV1)
        assert not is_cancelled()
        progress(100)
        return _events()[4]

    async def close(self, reason, progress, is_cancelled) -> DuplexSessionCloseReceiptV1:
        assert reason == "completed"
        assert not is_cancelled()
        progress(100)
        return _close_receipt()


class _FakeDuplexProvider:
    name = "fake.duplex-provider"
    version = "1.0.0"

    async def start(self, request, progress, is_cancelled) -> _FakeDuplexSession:
        assert request == _request()
        assert not is_cancelled()
        progress(100)
        return _FakeDuplexSession()


class _AlternateFakeDuplexSession(_FakeDuplexSession):
    async def events(self) -> AsyncIterator[DuplexEventV1]:
        alternate = [event.model_copy(deep=True) for event in _events()]
        alternate[2] = alternate[2].model_copy(
            update={"monotonic_timestamp_microseconds": 600_000}
        )
        for event in alternate:
            yield event


class _AlternateFakeDuplexProvider:
    name = "fake.alternate-duplex-provider"
    version = "2.0.0"

    async def start(self, request, progress, is_cancelled) -> _AlternateFakeDuplexSession:
        assert request == _request()
        assert not is_cancelled()
        progress(100)
        return _AlternateFakeDuplexSession()


def test_fake_provider_exercises_async_session_boundary() -> None:
    async def exercise() -> None:
        progress: list[int] = []
        session = await _FakeDuplexProvider().start(
            _request(),
            progress.append,
            lambda: False,
        )
        payload = b"synthetic-pcm-frame"
        frame = DuplexInputAudioFrameV1(
            session_id=session.session_id,
            sequence=1,
            idempotency_key="input-frame-001",
            turn_id="turn-user-001",
            monotonic_timestamp_microseconds=100_000,
            duration_microseconds=20_000,
            payload_size_bytes=len(payload),
            payload_digest_sha256=hashlib.sha256(payload).hexdigest(),
        )
        await session.push_audio(frame, payload, progress.append, lambda: False)
        observed = [event async for event in session.events()]
        interrupt = await session.interrupt(
            DuplexInterruptRequestV1(
                session_id=session.session_id,
                idempotency_key="interrupt-001",
                turn_id="turn-agent-001",
                monotonic_timestamp_microseconds=700_000,
                reason="user_barge_in",
            ),
            progress.append,
            lambda: False,
        )
        close = await session.close("completed", progress.append, lambda: False)

        assert session.received == [payload]
        assert observed == _events()
        assert interrupt.event_type == "interrupt_acknowledged"
        assert close.close_reason == "completed"
        assert progress == [100, 100, 100, 100]

    asyncio.run(exercise())


def test_two_behaviorally_distinct_fake_providers_pass_the_same_contract() -> None:
    async def exercise() -> None:
        observed_timings: list[int] = []
        for provider in (_FakeDuplexProvider(), _AlternateFakeDuplexProvider()):
            progress: list[int] = []
            session = await provider.start(_request(), progress.append, lambda: False)
            events = [event async for event in session.events()]
            validate_duplex_event_sequence(events)
            transitions = derive_duplex_state_transitions(events)
            assert transitions[-1].to_state == "closed"
            assert progress == [100]
            observed_timings.append(events[2].monotonic_timestamp_microseconds)
        assert len(set(observed_timings)) == 2

    asyncio.run(exercise())
