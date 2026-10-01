from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"
LOCALE_PATTERN = r"^[a-z]{2,3}(?:-[A-Z]{2})?$"
MAX_SESSION_MICROSECONDS = 4 * 60 * 60 * 1_000_000

DuplexEventType = Literal[
    "session_started",
    "input_audio",
    "agent_audio",
    "agent_text",
    "interrupt_requested",
    "interrupt_acknowledged",
    "backchannel",
    "consent_revoked",
    "session_closing",
    "session_closed",
    "error",
]

DuplexSessionState = Literal[
    "created",
    "listening",
    "speaking",
    "overlap",
    "interrupted",
    "closing",
    "closed",
    "failed",
]


class DuplexAudioFormatV1(StudioContract):
    schema_version: Literal["studio.duplex-audio-format.v1"] = (
        "studio.duplex-audio-format.v1"
    )
    encoding: Literal["pcm_s16le", "opus"]
    sample_rate_hz: int = Field(ge=8_000, le=96_000)
    channels: Literal[1, 2] = 1
    frame_duration_ms: int = Field(ge=5, le=120)


class DuplexRolePromptReferenceV1(StudioContract):
    prompt_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    version: int = Field(ge=1)
    digest_sha256: str = Field(pattern=SHA256_PATTERN)


class DuplexVoiceProfileReferenceV1(StudioContract):
    voice_profile_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    version: int = Field(ge=1)
    digest_sha256: str = Field(pattern=SHA256_PATTERN)
    kind: Literal["stock", "consented_clone"]
    consent_grant_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)

    @model_validator(mode="after")
    def validate_consent_binding(self) -> DuplexVoiceProfileReferenceV1:
        if self.kind == "consented_clone" and self.consent_grant_id is None:
            raise ValueError("Duplex cloned voice requires a consent grant")
        if self.kind == "stock" and self.consent_grant_id is not None:
            raise ValueError("Duplex stock voice cannot claim a consent grant")
        return self


class DuplexRetentionPolicyV1(StudioContract):
    schema_version: Literal["studio.duplex-retention-policy.v1"] = (
        "studio.duplex-retention-policy.v1"
    )
    mode: Literal["zero", "ttl"] = "zero"
    ttl_seconds: int | None = Field(default=None, ge=60, le=31_536_000)
    retain_raw_audio: bool = False
    retain_transcript: bool = False
    deletion_deadline_seconds: int = Field(default=300, ge=1, le=86_400)

    @model_validator(mode="after")
    def validate_retention(self) -> DuplexRetentionPolicyV1:
        if self.mode == "zero":
            if self.ttl_seconds is not None:
                raise ValueError("Zero-retention sessions cannot define a TTL")
            if self.retain_raw_audio or self.retain_transcript:
                raise ValueError("Zero-retention sessions cannot retain content")
        elif self.ttl_seconds is None:
            raise ValueError("TTL retention requires ttl_seconds")
        return self


class DuplexSessionPolicyV1(StudioContract):
    schema_version: Literal["studio.duplex-session-policy.v1"] = (
        "studio.duplex-session-policy.v1"
    )
    policy_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    version: int = Field(ge=1)
    locale: str = Field(default="pt-BR", pattern=LOCALE_PATTERN)
    maximum_session_seconds: int = Field(default=900, ge=10, le=14_400)
    allow_interruptions: bool = True
    allow_backchannels: bool = True
    maximum_agent_continuous_speech_seconds: int = Field(default=45, ge=1, le=300)
    spoken_prompt_injection_action: Literal["ignore", "interrupt", "close"] = (
        "interrupt"
    )
    human_review_required: bool = True
    consent_scope: Literal["voice.converse"] = "voice.converse"
    retention: DuplexRetentionPolicyV1


class DuplexSessionRequestV1(StudioContract):
    schema_version: Literal["studio.duplex-session-request.v1"] = (
        "studio.duplex-session-request.v1"
    )
    session_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    actor_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    idempotency_key: str = Field(pattern=OPAQUE_ID_PATTERN)
    role_prompt: DuplexRolePromptReferenceV1
    voice_profile: DuplexVoiceProfileReferenceV1
    policy: DuplexSessionPolicyV1
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    input_format: DuplexAudioFormatV1
    output_format: DuplexAudioFormatV1
    requested_at: datetime

    @model_validator(mode="after")
    def validate_policy_binding(self) -> DuplexSessionRequestV1:
        if self.policy_digest_sha256 != duplex_policy_digest(self.policy):
            raise ValueError("Duplex session policy digest mismatch")
        return self


class DuplexInputAudioFrameV1(StudioContract):
    schema_version: Literal["studio.duplex-input-audio-frame.v1"] = (
        "studio.duplex-input-audio-frame.v1"
    )
    session_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    sequence: int = Field(ge=0)
    idempotency_key: str = Field(pattern=OPAQUE_ID_PATTERN)
    turn_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    monotonic_timestamp_microseconds: int = Field(
        ge=0,
        le=MAX_SESSION_MICROSECONDS,
    )
    duration_microseconds: int = Field(gt=0, le=10_000_000)
    payload_size_bytes: int = Field(gt=0, le=10 * 1024 * 1024)
    payload_digest_sha256: str = Field(pattern=SHA256_PATTERN)

    def validate_payload(self, payload: bytes) -> None:
        if len(payload) != self.payload_size_bytes:
            raise ValueError("Duplex input audio payload size mismatch")
        if hashlib.sha256(payload).hexdigest() != self.payload_digest_sha256:
            raise ValueError("Duplex input audio payload digest mismatch")


class DuplexInterruptRequestV1(StudioContract):
    schema_version: Literal["studio.duplex-interrupt-request.v1"] = (
        "studio.duplex-interrupt-request.v1"
    )
    session_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    idempotency_key: str = Field(pattern=OPAQUE_ID_PATTERN)
    turn_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    monotonic_timestamp_microseconds: int = Field(
        ge=0,
        le=MAX_SESSION_MICROSECONDS,
    )
    reason: Literal["user_barge_in", "policy", "user_request", "shutdown"]


class DuplexEventV1(StudioContract):
    schema_version: Literal["studio.duplex-event.v1"] = "studio.duplex-event.v1"
    session_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    sequence: int = Field(ge=0)
    idempotency_key: str = Field(pattern=OPAQUE_ID_PATTERN)
    event_type: DuplexEventType
    monotonic_timestamp_microseconds: int = Field(
        ge=0,
        le=MAX_SESSION_MICROSECONDS,
    )
    turn_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    duration_microseconds: int | None = Field(default=None, gt=0, le=10_000_000)
    audio_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    text: str | None = Field(default=None, min_length=1, max_length=20_000)
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    related_sequence: int | None = Field(default=None, ge=0)
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        max_length=30,
    )

    @model_validator(mode="after")
    def validate_event_payload(self) -> DuplexEventV1:
        audio_events = {"input_audio", "agent_audio"}
        turn_events = audio_events | {
            "agent_text",
            "interrupt_requested",
            "interrupt_acknowledged",
            "backchannel",
        }
        if self.event_type in turn_events and self.turn_id is None:
            raise ValueError("Duplex turn event requires turn_id")
        if self.event_type in audio_events:
            if self.duration_microseconds is None or self.audio_digest_sha256 is None:
                raise ValueError("Duplex audio event requires duration and digest")
        elif self.audio_digest_sha256 is not None or self.duration_microseconds is not None:
            if self.event_type != "backchannel":
                raise ValueError("Duplex non-audio event cannot carry audio fields")
        if self.event_type == "agent_text" and self.text is None:
            raise ValueError("Duplex agent_text requires text")
        if self.event_type in {
            "interrupt_requested",
            "interrupt_acknowledged",
            "consent_revoked",
            "session_closing",
            "session_closed",
            "error",
        } and self.reason is None:
            raise ValueError("Duplex event requires reason")
        if self.event_type == "interrupt_acknowledged":
            if self.related_sequence is None:
                raise ValueError("Duplex interrupt acknowledgement requires related_sequence")
        elif self.related_sequence is not None:
            raise ValueError("Only interrupt acknowledgement can relate to a sequence")
        if self.event_type == "backchannel" and not (
            self.text or (self.audio_digest_sha256 and self.duration_microseconds)
        ):
            raise ValueError("Duplex backchannel requires text or audio evidence")
        if self.event_type == "session_started" and self.sequence != 0:
            raise ValueError("Duplex session_started must be sequence zero")
        _validate_safe_metadata(self.metadata)
        return self


class DuplexProviderLineageV1(StudioContract):
    provider: str = Field(min_length=1, max_length=160)
    provider_version: str = Field(min_length=1, max_length=160)
    code_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    parameters_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_manifest_digest_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    model_id: str | None = Field(default=None, max_length=240)
    model_revision: str | None = Field(default=None, max_length=240)
    model_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    generated_at: datetime

    @model_validator(mode="after")
    def validate_model_lineage(self) -> DuplexProviderLineageV1:
        model_fields = (self.model_id, self.model_revision, self.model_digest_sha256)
        if any(model_fields) and not all(model_fields):
            raise ValueError("Duplex model lineage must be atomic")
        return self


class DuplexStateTransitionV1(StudioContract):
    schema_version: Literal["studio.duplex-state-transition.v1"] = (
        "studio.duplex-state-transition.v1"
    )
    event_sequence: int = Field(ge=0)
    event_type: DuplexEventType
    from_state: DuplexSessionState
    to_state: DuplexSessionState
    monotonic_timestamp_microseconds: int = Field(
        ge=0,
        le=MAX_SESSION_MICROSECONDS,
    )


class DuplexRetentionReceiptV1(StudioContract):
    schema_version: Literal["studio.duplex-retention-receipt.v1"] = (
        "studio.duplex-retention-receipt.v1"
    )
    session_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    mode: Literal["zero", "ttl"]
    retained_asset_ids: list[str] = Field(default_factory=list, max_length=100)
    deletion_due_at: datetime | None = None
    deleted_at: datetime | None = None
    receipt_digest_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_receipt(self) -> DuplexRetentionReceiptV1:
        if len(self.retained_asset_ids) != len(set(self.retained_asset_ids)):
            raise ValueError("Duplex retained asset ids must be unique")
        if any(not re.fullmatch(OPAQUE_ID_PATTERN, item) for item in self.retained_asset_ids):
            raise ValueError("Duplex retained asset ids must be opaque")
        if self.mode == "zero":
            if self.retained_asset_ids or self.deletion_due_at is not None:
                raise ValueError("Zero retention cannot retain assets or defer deletion")
            if self.deleted_at is None:
                raise ValueError("Zero retention requires deletion acknowledgement")
        elif self.deletion_due_at is None:
            raise ValueError("TTL retention requires deletion_due_at")
        return self


class DuplexSessionCloseReceiptV1(StudioContract):
    schema_version: Literal["studio.duplex-session-close-receipt.v1"] = (
        "studio.duplex-session-close-receipt.v1"
    )
    session_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    close_reason: Literal["completed", "user", "policy", "error", "cancelled"]
    final_sequence: int = Field(ge=0)
    event_count: int = Field(ge=1)
    retention: DuplexRetentionReceiptV1
    closed_at: datetime

    @model_validator(mode="after")
    def validate_close_receipt(self) -> DuplexSessionCloseReceiptV1:
        if self.retention.session_id != self.session_id:
            raise ValueError("Duplex retention receipt session mismatch")
        if self.final_sequence + 1 != self.event_count:
            raise ValueError("Duplex close receipt sequence/count mismatch")
        return self


class DuplexReplayManifestV1(StudioContract):
    schema_version: Literal["studio.duplex-replay-manifest.v1"] = (
        "studio.duplex-replay-manifest.v1"
    )
    replay_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    session_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    role_prompt_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    voice_profile_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    provider_lineage: DuplexProviderLineageV1
    event_digests_sha256: list[str] = Field(min_length=2, max_length=1_000_000)
    state_transition_digests_sha256: list[str] = Field(
        min_length=2,
        max_length=1_000_000,
    )
    final_state: Literal["closed"]
    event_count: int = Field(ge=2, le=1_000_000)
    first_monotonic_timestamp_microseconds: int = Field(ge=0)
    last_monotonic_timestamp_microseconds: int = Field(ge=0)
    input_audio_events: int = Field(ge=0)
    agent_audio_events: int = Field(ge=0)
    interruption_requests: int = Field(ge=0)
    interruption_acknowledgements: int = Field(ge=0)
    backchannels: int = Field(ge=0)
    raw_audio_retained: bool
    transcript_retained: bool
    close_receipt: DuplexSessionCloseReceiptV1
    generated_at: datetime

    @model_validator(mode="after")
    def validate_replay(self) -> DuplexReplayManifestV1:
        if len(self.event_digests_sha256) != self.event_count:
            raise ValueError("Duplex replay event count mismatch")
        if len(self.state_transition_digests_sha256) != self.event_count:
            raise ValueError("Duplex replay state transition count mismatch")
        if len(set(self.event_digests_sha256)) != len(self.event_digests_sha256):
            raise ValueError("Duplex replay event digests must be unique")
        if any(not re.fullmatch(SHA256_PATTERN, item) for item in self.event_digests_sha256):
            raise ValueError("Duplex replay event digest is invalid")
        if any(
            not re.fullmatch(SHA256_PATTERN, item)
            for item in self.state_transition_digests_sha256
        ):
            raise ValueError("Duplex replay state transition digest is invalid")
        if self.last_monotonic_timestamp_microseconds < (
            self.first_monotonic_timestamp_microseconds
        ):
            raise ValueError("Duplex replay timestamps are inverted")
        if self.close_receipt.session_id != self.session_id:
            raise ValueError("Duplex replay close receipt session mismatch")
        if self.close_receipt.event_count != self.event_count:
            raise ValueError("Duplex replay close receipt count mismatch")
        if self.close_receipt.retention.mode == "zero" and (
            self.raw_audio_retained or self.transcript_retained
        ):
            raise ValueError("Zero-retention replay cannot retain content")
        return self


def duplex_policy_digest(policy: DuplexSessionPolicyV1) -> str:
    return _canonical_digest(
        policy.model_dump(mode="json", by_alias=True, exclude_none=True)
    )


def duplex_event_digest(event: DuplexEventV1) -> str:
    return _canonical_digest(
        event.model_dump(mode="json", by_alias=True, exclude_none=True)
    )


def duplex_state_transition_digest(transition: DuplexStateTransitionV1) -> str:
    return _canonical_digest(
        transition.model_dump(mode="json", by_alias=True, exclude_none=True)
    )


def derive_duplex_state_transitions(
    events: list[DuplexEventV1],
) -> list[DuplexStateTransitionV1]:
    state: DuplexSessionState = "created"
    transitions: list[DuplexStateTransitionV1] = []
    for event in events:
        previous = state
        if event.event_type == "session_started":
            if state != "created":
                raise ValueError("Duplex session can only start from created")
            state = "listening"
        elif event.event_type == "input_audio":
            if state == "speaking":
                state = "overlap"
            elif state not in {"listening", "overlap", "interrupted"}:
                raise ValueError("Duplex input audio is invalid in current state")
        elif event.event_type == "agent_audio":
            if state == "listening":
                state = "speaking"
            elif state not in {"speaking", "overlap"}:
                raise ValueError("Duplex agent audio is invalid in current state")
        elif event.event_type == "agent_text":
            if state not in {"listening", "speaking", "overlap"}:
                raise ValueError("Duplex agent text is invalid in current state")
        elif event.event_type == "interrupt_requested":
            if state not in {"listening", "speaking", "overlap"}:
                raise ValueError("Duplex interruption is invalid in current state")
            state = "interrupted"
        elif event.event_type == "interrupt_acknowledged":
            if state != "interrupted":
                raise ValueError("Duplex interrupt acknowledgement requires interrupted state")
            state = "listening"
        elif event.event_type == "backchannel":
            if state not in {"listening", "speaking", "overlap"}:
                raise ValueError("Duplex backchannel is invalid in current state")
        elif event.event_type in {"consent_revoked", "session_closing"}:
            if state not in {
                "listening",
                "speaking",
                "overlap",
                "interrupted",
                "failed",
            }:
                raise ValueError("Duplex close request is invalid in current state")
            state = "closing"
        elif event.event_type == "error":
            if state in {"created", "closed"}:
                raise ValueError("Duplex error is invalid in current state")
            state = "failed"
        elif event.event_type == "session_closed":
            if state in {"created", "closed"}:
                raise ValueError("Duplex close is invalid in current state")
            state = "closed"
        transitions.append(
            DuplexStateTransitionV1(
                event_sequence=event.sequence,
                event_type=event.event_type,
                from_state=previous,
                to_state=state,
                monotonic_timestamp_microseconds=(
                    event.monotonic_timestamp_microseconds
                ),
            )
        )
    return transitions


def validate_duplex_event_sequence(events: list[DuplexEventV1]) -> None:
    if len(events) < 2:
        raise ValueError("Duplex replay requires at least start and close events")
    session_id = events[0].session_id
    if events[0].event_type != "session_started":
        raise ValueError("Duplex replay must start with session_started")
    if events[-1].event_type != "session_closed":
        raise ValueError("Duplex replay must end with session_closed")
    seen_idempotency: set[str] = set()
    interrupt_requests: dict[int, DuplexEventV1] = {}
    previous_timestamp = -1
    for expected_sequence, event in enumerate(events):
        if event.session_id != session_id:
            raise ValueError("Duplex replay crosses sessions")
        if event.sequence != expected_sequence:
            raise ValueError("Duplex replay sequences must be contiguous")
        if event.monotonic_timestamp_microseconds < previous_timestamp:
            raise ValueError("Duplex replay timestamps must be monotonic")
        if event.idempotency_key in seen_idempotency:
            raise ValueError("Duplex replay idempotency keys must be unique")
        seen_idempotency.add(event.idempotency_key)
        previous_timestamp = event.monotonic_timestamp_microseconds
        if event.event_type == "interrupt_requested":
            interrupt_requests[event.sequence] = event
        elif event.event_type == "interrupt_acknowledged":
            request = interrupt_requests.get(event.related_sequence)
            if request is None or request.turn_id != event.turn_id:
                raise ValueError("Duplex interrupt acknowledgement is unbound")
    transitions = derive_duplex_state_transitions(events)
    if transitions[-1].to_state != "closed":
        raise ValueError("Duplex replay must reach closed state")


def build_duplex_replay_manifest(
    request: DuplexSessionRequestV1,
    events: list[DuplexEventV1],
    provider_lineage: DuplexProviderLineageV1,
    close_receipt: DuplexSessionCloseReceiptV1,
    *,
    generated_at: datetime,
) -> DuplexReplayManifestV1:
    validate_duplex_event_sequence(events)
    if events[0].session_id != request.session_id:
        raise ValueError("Duplex request and replay session mismatch")
    if close_receipt.session_id != request.session_id:
        raise ValueError("Duplex request and close receipt session mismatch")
    event_digests = [duplex_event_digest(event) for event in events]
    transitions = derive_duplex_state_transitions(events)
    return DuplexReplayManifestV1(
        replay_id=(
            "duplex-replay-"
            + hashlib.sha256(
                f"{request.workspace_id}:{request.session_id}".encode()
            ).hexdigest()[:24]
        ),
        session_id=request.session_id,
        workspace_id=request.workspace_id,
        policy_digest_sha256=request.policy_digest_sha256,
        role_prompt_digest_sha256=request.role_prompt.digest_sha256,
        voice_profile_digest_sha256=request.voice_profile.digest_sha256,
        provider_lineage=provider_lineage,
        event_digests_sha256=event_digests,
        state_transition_digests_sha256=[
            duplex_state_transition_digest(transition)
            for transition in transitions
        ],
        final_state="closed",
        event_count=len(events),
        first_monotonic_timestamp_microseconds=(
            events[0].monotonic_timestamp_microseconds
        ),
        last_monotonic_timestamp_microseconds=(
            events[-1].monotonic_timestamp_microseconds
        ),
        input_audio_events=sum(
            event.event_type == "input_audio" for event in events
        ),
        agent_audio_events=sum(
            event.event_type == "agent_audio" for event in events
        ),
        interruption_requests=sum(
            event.event_type == "interrupt_requested" for event in events
        ),
        interruption_acknowledgements=sum(
            event.event_type == "interrupt_acknowledged" for event in events
        ),
        backchannels=sum(event.event_type == "backchannel" for event in events),
        raw_audio_retained=request.policy.retention.retain_raw_audio,
        transcript_retained=request.policy.retention.retain_transcript,
        close_receipt=close_receipt,
        generated_at=generated_at,
    )


def _validate_safe_metadata(metadata: dict[str, str | int | float | bool]) -> None:
    prohibited_keys = {
        "path",
        "url",
        "token",
        "voice_prompt",
        "voice_prompt_path",
        "hub_token",
    }
    for key, value in metadata.items():
        normalized = key.lower().replace("-", "_")
        if normalized in prohibited_keys:
            raise ValueError("Duplex metadata cannot carry paths, URLs or tokens")
        if isinstance(value, str) and (
            value.startswith(("/", "\\", "file://", "http://", "https://"))
            or re.match(r"^[A-Za-z]:[\\/]", value)
        ):
            raise ValueError("Duplex metadata string resembles a path or URL")


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
