from __future__ import annotations

import pytest
from conftest import register
from sqlalchemy import select

from app.database import SessionLocal
from app.domain.studios.contracts import CreateGenerationJobRequest, TranscriptionRequestV1
from app.domain.studios.providers import (
    PROVIDERS,
    SPEECH_PROVIDERS,
    TRANSCRIPTION_PROVIDERS,
    VOICE_CLONE_PROVIDERS,
)
from app.models import User
from app.services.studios.jobs import create_job


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_generic_generation_registry_cannot_satisfy_speech_jobs() -> None:
    assert "builtin.snapshot" in PROVIDERS
    assert SPEECH_PROVIDERS == {}
    assert VOICE_CLONE_PROVIDERS == {}
    assert TRANSCRIPTION_PROVIDERS == {}
    assert "builtin.snapshot" not in SPEECH_PROVIDERS
    assert "builtin.snapshot" not in VOICE_CLONE_PROVIDERS


def test_stock_voice_job_fails_closed_before_a_speech_provider_is_promoted(client) -> None:
    token, workspace = register(client, "speech-job-boundary@example.com", "Speech Boundary")
    response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "speech-boundary-1"},
        json={
            "workspaceId": workspace,
            "jobType": "stock_voice",
            "provider": "kokoro-82m-stock",
            "request": {
                "locale": "pt-BR",
                "text": "Café Aurora.",
                "scriptDigestSha256": "a" * 64,
                "voiceKey": "pt-br-stock-01",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "speech_provider_not_approved"


def test_transcription_job_is_not_routed_through_generic_generation_provider(client) -> None:
    token, workspace = register(client, "transcription-boundary@example.com", "Transcription Boundary")
    response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "transcription-boundary-1"},
        json={
            "workspaceId": workspace,
            "jobType": "transcription",
            "provider": "whisperx.pt-br",
            "request": {
                "schemaVersion": "studio.transcription-request.v1",
                "mediaIngestId": "ingest-not-ready",
                "locale": "pt-BR",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "transcription_provider_not_approved"


def test_transcription_request_has_a_typed_media_boundary() -> None:
    request = TranscriptionRequestV1(
        media_ingest_id="ingest-001",
        source_asset_id="asset-001",
        source_checksum_sha256="a" * 64,
    )
    assert request.schema_version == "studio.transcription-request.v1"
    assert request.locale == "pt-BR"
    assert request.source_asset_id == "asset-001"


def test_voice_clone_job_requires_identity_bound_voice_version(client) -> None:
    token, workspace = register(client, "voice-clone-boundary@example.com", "Voice Clone Boundary")
    response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "voice-clone-boundary-1"},
        json={
            "workspaceId": workspace,
            "jobType": "voice_clone",
            "provider": "candidate.voice-clone",
            "consentGrantId": "consent-not-provided",
            "request": {
                "locale": "pt-BR",
                "text": "Amostra de teste.",
                "scriptDigestSha256": "a" * 64,
                "voiceKey": "clone-01",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "voice_version_required"


def test_voice_clone_job_requires_explicit_consent(client) -> None:
    token, workspace = register(client, "voice-clone-consent@example.com", "Voice Clone Consent")
    response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "voice-clone-consent-1"},
        json={
            "workspaceId": workspace,
            "jobType": "voice_clone",
            "provider": "candidate.voice-clone",
            "voiceVersionId": "voice-version-not-provided",
            "request": {
                "locale": "pt-BR",
                "text": "Amostra de teste.",
                "scriptDigestSha256": "a" * 64,
                "voiceKey": "clone-01",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "consent_required"


def test_direct_job_creation_keeps_voice_clone_boundary(client) -> None:
    _, workspace = register(client, "voice-clone-direct-boundary@example.com", "Voice Clone Direct Boundary")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "voice-clone-direct-boundary@example.com"))
        assert user is not None
        missing_version = CreateGenerationJobRequest(
            workspace_id=workspace,
            job_type="voice_clone",
            provider="candidate.voice-clone",
            consent_grant_id="consent-id",
        )
        with pytest.raises(ValueError, match="voice_version_required"):
            create_job(db, missing_version, "voice-clone-direct-1", user)

        missing_consent = missing_version.model_copy(
            update={"voice_version_id": "voice-version-id", "consent_grant_id": None}
        )
        with pytest.raises(ValueError, match="consent_required"):
            create_job(db, missing_consent, "voice-clone-direct-2", user)
