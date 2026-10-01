from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from conftest import register
from pydantic import ValidationError
from sqlalchemy import select

from app.database import SessionLocal
from app.domain.studios.contracts import MediaTimelineV1
from app.models import (
    LibraryAsset,
    StudioDomainEvent,
    StudioGenerationJob,
    StudioIdentityVersion,
    StudioVoiceVersion,
    User,
)
from app.services.studios.registry import (
    approve_model,
    approve_provider,
    model_registration_out,
    provider_registration_out,
    register_model,
    register_provider,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_typed_media_timeline_is_frame_exact_and_provider_neutral():
    timeline = MediaTimelineV1.model_validate(
        {
            "durationFrames": 300,
            "frameRate": {"numerator": 30000, "denominator": 1001},
            "tracks": [
                {
                    "id": "video-main",
                    "kind": "video",
                    "clips": [
                        {
                            "id": "clip-1",
                            "assetId": "asset-video",
                            "timeline": {"startFrame": 0, "durationFrames": 300},
                            "source": {"startMicroseconds": 0, "durationMicroseconds": 10_010_000},
                        }
                    ],
                },
                {
                    "id": "mask-main",
                    "kind": "mask",
                    "targetTrackId": "video-main",
                    "artifactAssetId": "asset-mask",
                },
                {
                    "id": "captions-main",
                    "kind": "caption",
                    "cues": [
                        {
                            "id": "cue-1",
                            "timeline": {"startFrame": 0, "durationFrames": 60},
                            "text": "O anúncio continua editável.",
                        }
                    ],
                },
            ],
        }
    )
    encoded = timeline.model_dump(by_alias=True, mode="json")
    assert MediaTimelineV1.model_validate(encoded) == timeline
    assert encoded["frameRate"] == {"numerator": 30000, "denominator": 1001}
    assert "opencut" not in str(encoded).lower()
    assert "hyperframes" not in str(encoded).lower()

    with pytest.raises(ValidationError, match="Mask track target must exist"):
        MediaTimelineV1.model_validate(
            {
                "durationFrames": 30,
                "tracks": [
                    {
                        "id": "mask-orphan",
                        "kind": "mask",
                        "targetTrackId": "missing",
                        "artifactAssetId": "asset-mask",
                    }
                ],
            }
        )

    with pytest.raises(ValidationError, match="Media clip exceeds timeline duration"):
        MediaTimelineV1.model_validate(
            {
                "durationFrames": 30,
                "tracks": [
                    {
                        "id": "video-main",
                        "kind": "video",
                        "clips": [
                            {
                                "id": "clip-overflow",
                                "assetId": "asset-video",
                                "timeline": {"startFrame": 20, "durationFrames": 20},
                            }
                        ],
                    }
                ],
            }
        )


def test_consent_identity_voice_revocation_and_tenant_isolation(client, monkeypatch):
    token, workspace = register(client, "identity-owner@example.com", "Identity Studio")
    other_token, _ = register(client, "identity-other@example.com", "Other Identity Studio")

    with SessionLocal() as db:
        sample = LibraryAsset(
            workspace_id=workspace,
            title="Amostra consentida",
            asset_type="upload",
            tags=["identity-sample"],
        )
        db.add(sample)
        db.commit()
        db.refresh(sample)
        sample_id = sample.id

    consent_payload = {
        "workspaceId": workspace,
        "subjectKey": "subject-ana-001",
        "subjectDisplayName": "Ana",
        "purpose": "Criar anúncios da marca com rosto e voz autorizados.",
        "scopes": ["identity.enroll", "avatar.generate", "voice.enroll", "voice.clone"],
        "channels": ["instagram", "tiktok"],
        "policyVersion": "identity-consent.v1",
        "expiresAt": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
    }
    consent_response = client.post(
        "/api/v1/studios/v1/consents", headers=auth(token), json=consent_payload
    )
    assert consent_response.status_code == 201, consent_response.text
    consent = consent_response.json()
    assert consent["status"] == "active"
    assert consent["scopes"] == consent_payload["scopes"]

    cross_tenant = client.get(
        "/api/v1/studios/v1/consents",
        headers=auth(other_token),
        params={"workspace_id": workspace},
    )
    assert cross_tenant.status_code == 404

    identity_response = client.post(
        "/api/v1/studios/v1/identities",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "subjectKey": consent["subjectKey"],
            "displayName": "Ana — rosto oficial",
            "identityType": "natural_person",
        },
    )
    assert identity_response.status_code == 201, identity_response.text
    identity = identity_response.json()

    missing_sample = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/versions",
        headers=auth(token),
        json={"consentGrantId": consent["id"], "capabilities": ["avatar.generate"]},
    )
    assert missing_sample.status_code == 422
    assert missing_sample.json()["detail"]["code"] == "identity_samples_required"

    identity_version_response = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/versions",
        headers=auth(token),
        json={
            "consentGrantId": consent["id"],
            "capabilities": ["avatar.generate"],
            "sampleAssetIds": [sample_id],
        },
    )
    assert identity_version_response.status_code == 201, identity_version_response.text
    identity_version = identity_version_response.json()
    assert identity_version["status"] == "draft"
    assert len(identity_version["contentHash"]) == 64

    voice_response = client.post(
        "/api/v1/studios/v1/voices",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "identityProfileId": identity["id"],
            "displayName": "Ana — voz PT-BR",
            "locale": "pt-BR",
            "voiceType": "cloned",
        },
    )
    assert voice_response.status_code == 201, voice_response.text
    voice = voice_response.json()
    voice_version_response = client.post(
        f"/api/v1/studios/v1/voices/{voice['id']}/versions",
        headers=auth(token),
        json={"consentGrantId": consent["id"], "sampleAssetIds": [sample_id]},
    )
    assert voice_version_response.status_code == 201, voice_version_response.text
    voice_version = voice_version_response.json()
    assert voice_version["status"] == "draft"

    from app import tasks

    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _job_id: None)
    job_response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "consent-bound-job-001"},
        json={
            "workspaceId": workspace,
            "consentGrantId": consent["id"],
            "jobType": "document_snapshot",
            "provider": "builtin.snapshot",
            "request": {},
        },
    )
    assert job_response.status_code == 202, job_response.text
    assert job_response.json()["status"] == "queued"

    revoked_response = client.post(
        f"/api/v1/studios/v1/consents/{consent['id']}/revoke",
        headers=auth(token),
        json={"reason": "Titular retirou a autorização"},
    )
    assert revoked_response.status_code == 200, revoked_response.text
    assert revoked_response.json()["status"] == "revoked"

    with SessionLocal() as db:
        assert db.get(StudioIdentityVersion, identity_version["id"]).status == "revoked"
        assert db.get(StudioVoiceVersion, voice_version["id"]).status == "revoked"
        assert db.get(StudioGenerationJob, job_response.json()["id"]).status == "cancelled"
        event = db.scalar(
            select(StudioDomainEvent)
            .where(StudioDomainEvent.event_type == "studio.consent.revoked")
            .order_by(StudioDomainEvent.occurred_at.desc())
        )
        assert event.payload["identityVersionsInvalidated"] == 1
        assert event.payload["voiceVersionsInvalidated"] == 1
        assert event.payload["jobsBlocked"] == 1

    after_revocation = client.post(
        f"/api/v1/studios/v1/voices/{voice['id']}/versions",
        headers=auth(token),
        json={"consentGrantId": consent["id"], "sampleAssetIds": [sample_id]},
    )
    assert after_revocation.status_code == 422
    assert after_revocation.json()["detail"]["code"] == "voice_profile_not_usable"


def test_provider_and_model_registry_requires_complete_commercial_evidence(client):
    register(client, "registry-owner@example.com", "Registry Studio")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "registry-owner@example.com"))
        provider = register_provider(
            db,
            capability="VoiceCloneProvider",
            provider="evaluation.chatterbox",
            provider_version="v3",
            source_url="https://github.com/resemble-ai/chatterbox",
            source_revision="5de7a54aa4e5e2baadb0182dde554908b48b85c2",
            code_license="MIT",
            risk_class="biometric",
            manifest={"licenseEvidence": "official-license"},
        )
        with pytest.raises(ValueError, match="provider_manifest_incomplete"):
            approve_provider(db, provider, user=user)
        provider.manifest = {
            "sbom": "pending-spike-sbom",
            "licenseEvidence": "official-license",
            "exitStrategy": "provider-neutral VoiceVersion",
        }
        db.commit()
        approve_provider(db, provider, user=user)
        assert provider_registration_out(provider).status == "approved"

        model = register_model(
            db,
            provider_registration=provider,
            name="Chatterbox Multilingual pt-BR",
            version="v3",
            digest_sha256="b" * 64,
            model_license="MIT",
            commercial_use="unknown",
            languages=["pt-BR"],
            capabilities=["voice.clone"],
            manifest={},
        )
        with pytest.raises(ValueError, match="model_commercial_use_not_approved"):
            approve_model(db, model, user=user)
        model.commercial_use = "approved"
        model.manifest = {
            "weightsSource": "official-model-card",
            "licenseEvidence": "official-model-card",
            "datasetDisclosure": "upstream-aggregate-disclosure",
            "deletionPolicy": "ephemeral-worker-copy",
        }
        db.commit()
        approve_model(db, model, user=user)
        result = model_registration_out(model)
        assert result.status == "approved"
        assert result.approved_by == user.id
        assert result.digest_sha256 == "b" * 64
