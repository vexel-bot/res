from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from conftest import register
from PIL import Image
from sqlalchemy import select

from app.database import SessionLocal
from app.domain.studios.contracts import AvatarVideoEncodeResultV1
from app.domain.studios.hybrid_video import (
    CapabilityReadinessV1,
    CapabilityUnitCostV1,
    HybridCapabilityManifestV1,
    HybridExecutionProfileV1,
)
from app.domain.studios.providers import AVATAR_VIDEO_PROVIDERS
from app.models import (
    LibraryAsset,
    StudioConsentGrant,
    StudioGenerationJob,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioVoiceProfile,
    StudioVoiceVersion,
    User,
)
from app.services.object_storage import sha256_file
from app.services.studios.jobs import execute_job_once


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_presenter_document(client, token: str, workspace_id: str) -> dict:
    response = client.post(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        json={
            "workspaceId": workspace_id,
            "title": "Amostra privada de Presenter",
            "contentType": "presenter",
            "brandRevision": 1,
            "brief": {
                "objective": "Validar um anúncio com identidade consentida",
                "audience": "Revisores internos",
                "hook": "Conheça a proposta",
            },
            "composition": {
                "pages": [
                    {
                        "id": "presenter-scene-1",
                        "role": "ugc",
                        "width": 1080,
                        "height": 1920,
                        "safeArea": 48,
                        "background": "#10181c",
                        "layers": [],
                    }
                ]
            },
            "assets": [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_active_presenter_capsule(
    workspace_id: str,
    owner_email: str,
    *,
    identity_sample_ids: list[str] | None = None,
    voice_sample_ids: list[str] | None = None,
) -> tuple[str, str, str]:
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == owner_email))
        assert owner is not None
        grant = StudioConsentGrant(
            workspace_id=workspace_id,
            subject_key="subject-presenter-001",
            subject_display_name="Ana Presenter",
            purpose="Amostras privadas e revisadas de anúncio",
            scopes=["identity.enroll", "avatar.generate", "voice.enroll", "voice.clone"],
            policy_version="identity-consent.v1",
            status="active",
            granted_by=owner.id,
            granted_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        identity = StudioIdentityProfile(
            workspace_id=workspace_id,
            subject_key=grant.subject_key,
            display_name="Ana Presenter",
            identity_type="natural_person",
            status="active",
            owner_user_id=owner.id,
            created_by=owner.id,
        )
        db.add_all([grant, identity])
        db.flush()
        identity_version = StudioIdentityVersion(
            workspace_id=workspace_id,
            profile_id=identity.id,
            version=1,
            consent_grant_id=grant.id,
            status="active",
            capabilities=["avatar.generate"],
            sample_asset_ids=identity_sample_ids or [],
            derived_artifacts=[],
            content_hash="1" * 64,
            created_by=owner.id,
            reviewed_by=owner.id,
            reviewed_at=datetime.now(UTC),
            review_comment="Preview privado aprovado.",
        )
        voice = StudioVoiceProfile(
            workspace_id=workspace_id,
            identity_profile_id=identity.id,
            display_name="Ana Presenter PT-BR",
            locale="pt-BR",
            voice_type="cloned",
            status="active",
            created_by=owner.id,
        )
        db.add_all([identity_version, voice])
        db.flush()
        voice_version = StudioVoiceVersion(
            workspace_id=workspace_id,
            profile_id=voice.id,
            version=1,
            consent_grant_id=grant.id,
            status="active",
            sample_asset_ids=voice_sample_ids or [],
            derived_artifacts=[],
            pronunciation_profile={},
            content_hash="2" * 64,
            created_by=owner.id,
            reviewed_by=owner.id,
            reviewed_at=datetime.now(UTC),
            review_comment="Preview vocal privado aprovado.",
        )
        db.add(voice_version)
        db.commit()
        return grant.id, identity_version.id, voice_version.id


class FakeAvatarVideoProvider:
    name = "candidate.avatar-test"
    version = "1.0.0"

    def render(
        self,
        document,
        request,
        identity_samples,
        voice_sample,
        destination,
        progress,
        is_cancelled,
    ):
        assert document.content_type == "presenter"
        assert request.script == "Conheça a proposta."
        assert identity_samples[0].read_bytes()[4:8] == b"ftyp"
        assert voice_sample.read_bytes()[:4] == b"RIFF"
        assert not is_cancelled()
        progress(60)
        destination.write_bytes(b"\x00\x00\x00\x18ftypisom-avatar-private")
        return AvatarVideoEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=request.width,
            height=request.height,
            fps=request.fps,
            duration_ms=1000,
            artifact_checksum_sha256=sha256_file(destination),
            synthetic_content_disclosed=True,
            metrics={"identitySimilarity": 0.92},
        )


def approve_avatar_candidate(workspace_id: str, owner_email: str) -> None:
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == owner_email))
        assert owner is not None
        registration = StudioProviderRegistration(
            capability="avatar_video",
            provider="candidate.avatar-test",
            provider_version="1.0.0",
            source_url="https://example.invalid/avatar-test",
            source_revision="abcdef1234567",
            code_license="Apache-2.0",
            status="approved",
            risk_class="high",
            manifest={"benchmarkStatus": "passed", "workerAdvertised": True},
            approved_by=owner.id,
            approved_at=datetime.now(UTC),
        )
        db.add(registration)
        db.flush()
        db.add(
            StudioModelRegistration(
                provider_registration_id=registration.id,
                name="avatar-test-model",
                version="1.0.0",
                digest_sha256="3" * 64,
                model_license="Apache-2.0",
                commercial_use="approved",
                languages=["pt-BR"],
                capabilities=["avatar_video"],
                status="approved",
                manifest={"benchmarkStatus": "passed"},
                approved_by=owner.id,
                approved_at=datetime.now(UTC),
            )
        )
        db.commit()


def ready_avatar_manifest(runtime_revision: str = "runtime-a") -> HybridCapabilityManifestV1:
    return HybridCapabilityManifestV1(
        profiles=[
            HybridExecutionProfileV1(
                profileId="candidate-avatar-v2",
                providerId="candidate.avatar-test",
                capability="avatar_video",
                operations=["image_audio_to_avatar"],
                environment="local",
                qualificationState="experimental",
                commercialUse="approved",
                readiness=CapabilityReadinessV1(
                    serviceConfigured=True,
                    serviceAccessible=True,
                    modelInstalled=True,
                    resourcesAvailable=True,
                    inferenceValidated=False,
                ),
                maximumNativeSeconds=10,
                cost=CapabilityUnitCostV1(priceVersion="local-test"),
                modelId="avatar-test-model",
                modelRevision="model-a",
                runtimeRevision=runtime_revision,
            )
        ]
    )


def test_avatar_video_job_is_rights_bound_admitted_and_tenant_scoped(client, monkeypatch):
    owner_email = "avatar-boundary@example.com"
    token, workspace = register(client, owner_email, "Avatar Boundary")
    other_token, _ = register(client, "avatar-boundary-other@example.com", "Other Avatar")
    document = create_presenter_document(client, token, workspace)
    grant_id, identity_version_id, voice_version_id = add_active_presenter_capsule(
        workspace, owner_email
    )
    request = {
        "workspaceId": workspace,
        "documentId": document["documentId"],
        "consentGrantId": grant_id,
        "identityVersionId": identity_version_id,
        "voiceVersionId": voice_version_id,
        "jobType": "avatar_video",
        "provider": "candidate.avatar-test",
        "request": {"script": "Conheça a proposta.", "locale": "pt-BR"},
    }

    unavailable = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "avatar-provider-pending-001"},
        json=request,
    )
    assert unavailable.status_code == 409, unavailable.text
    assert unavailable.json()["detail"]["code"] == "avatar_provider_not_approved"

    approve_avatar_candidate(workspace, owner_email)
    queued: list[str] = []
    from app import tasks

    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued.append(job_id))
    created = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "avatar-admitted-001"},
        json=request,
    )
    assert created.status_code == 202, created.text
    job = created.json()
    assert queued == [job["id"]]
    assert job["status"] == "queued"
    assert job["executionCapability"] == "vision_gpu"
    assert job["queueName"] == "studio.gpu.vision"
    assert job["documentId"] == document["documentId"]
    assert job["consentGrantId"] == grant_id
    assert job["identityVersionId"] == identity_version_id
    assert job["voiceVersionId"] == voice_version_id

    hidden = client.get(f"/api/v1/studios/v1/jobs/{job['id']}", headers=auth(other_token))
    assert hidden.status_code == 404

    revoked = client.post(
        f"/api/v1/studios/v1/consents/{grant_id}/revoke",
        headers=auth(token),
        json={"reason": "Titular revogou antes de uma nova amostra."},
    )
    assert revoked.status_code == 200, revoked.text
    blocked = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "avatar-after-revocation-001"},
        json=request,
    )
    assert blocked.status_code == 422, blocked.text
    assert blocked.json()["detail"]["code"] == "consent_not_active"


def test_avatar_video_requires_all_governed_bindings(client):
    token, workspace = register(client, "avatar-required@example.com", "Avatar Required")
    response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "avatar-required-fields-001"},
        json={
            "workspaceId": workspace,
            "jobType": "avatar_video",
            "provider": "candidate.avatar-test",
            "request": {"script": "Teste."},
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "document_required"


def test_avatar_video_adapter_persists_private_review_artifact(client, tmp_path, monkeypatch):
    from app import tasks
    from app.routers import assets as assets_router

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    owner_email = "avatar-execution@example.com"
    token, workspace = register(client, owner_email, "Avatar Execution")
    document = create_presenter_document(client, token, workspace)
    identity_upload = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Captura privada"},
        files={
            "file": (
                "capture.mp4",
                b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2",
                "video/mp4",
            )
        },
    )
    voice_upload = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Voz privada"},
        files={"file": ("voice.wav", b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32, "audio/wav")},
    )
    assert identity_upload.status_code == 201, identity_upload.text
    assert voice_upload.status_code == 201, voice_upload.text
    grant_id, identity_version_id, voice_version_id = add_active_presenter_capsule(
        workspace,
        owner_email,
        identity_sample_ids=[identity_upload.json()["id"]],
        voice_sample_ids=[voice_upload.json()["id"]],
    )
    approve_avatar_candidate(workspace, owner_email)
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _job_id: None)
    created = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "avatar-execution-001"},
        json={
            "workspaceId": workspace,
            "documentId": document["documentId"],
            "consentGrantId": grant_id,
            "identityVersionId": identity_version_id,
            "voiceVersionId": voice_version_id,
            "jobType": "avatar_video",
            "provider": "candidate.avatar-test",
            "request": {"script": "Conheça a proposta.", "locale": "pt-BR"},
        },
    )
    assert created.status_code == 202, created.text
    AVATAR_VIDEO_PROVIDERS[FakeAvatarVideoProvider.name] = FakeAvatarVideoProvider()
    try:
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, created.json()["id"])
            assert job is not None
            assert execute_job_once(db, job) == "succeeded"
            db.refresh(job)
            result = job.result_payload
            assert result["schemaVersion"] == "studio.avatar-video-job-result.v1"
            artifact = db.get(LibraryAsset, result["assetId"])
            assert artifact is not None
            assert artifact.tags == ["studio-presenter", "private-review", "synthetic-content"]
            assert artifact.object_metadata["reviewRequired"] is True
            assert artifact.object_metadata["identityVersionId"] == identity_version_id
            assert artifact.object_metadata["voiceVersionId"] == voice_version_id
            assert artifact.object_metadata["consentGrantId"] == grant_id
    finally:
        AVATAR_VIDEO_PROVIDERS.pop(FakeAvatarVideoProvider.name, None)


def test_longcat_v2_blocks_before_submission_when_profile_is_unavailable(client, tmp_path, monkeypatch):
    from app import tasks
    from app.routers import assets as assets_router

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _job_id: None)
    owner_email = "longcat-blocked@example.com"
    token, workspace = register(client, owner_email, "LongCat Blocked")
    document = create_presenter_document(client, token, workspace)
    portrait = BytesIO()
    Image.new("RGB", (64, 64), "#6655aa").save(portrait, format="PNG")
    wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32
    image = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Retrato autorizado"},
        files={"file": ("portrait.png", portrait.getvalue(), "image/png")},
    ).json()
    voice_sample = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Amostra de voz"},
        files={"file": ("sample.wav", wav_bytes, "audio/wav")},
    ).json()
    final_audio = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Fala final"},
        files={"file": ("final.wav", wav_bytes + b"final", "audio/wav")},
    ).json()
    grant_id, identity_version_id, voice_version_id = add_active_presenter_capsule(
        workspace,
        owner_email,
        identity_sample_ids=[image["id"]],
        voice_sample_ids=[voice_sample["id"]],
    )
    payload = {
        "workspaceId": workspace,
        "documentId": document["documentId"],
        "consentGrantId": grant_id,
        "identityVersionId": identity_version_id,
        "voiceVersionId": voice_version_id,
        "jobType": "avatar_video",
        "provider": "local.longcat-avatar-1.5",
        "request": {
            "schemaVersion": "studio.avatar-video-request.v2",
            "expectedDocumentRevision": document["revision"],
            "sceneId": "scene-presenter-1",
            "requirementId": "avatar-material-1",
            "operation": "image_audio_to_avatar",
            "script": "Uma ideia encontra seu público.",
            "locale": "pt-BR",
            "referenceImageAssetId": image["id"],
            "referenceImageChecksumSha256": image["checksumSha256"],
            "drivingAudioAssetId": final_audio["id"],
            "drivingAudioChecksumSha256": final_audio["checksumSha256"],
            "drivingAudioDurationMs": 2800,
            "drivingAudioOrigin": "uploaded_final_speech",
            "performanceDirection": "Falar com calma em plano médio.",
            "framing": "medium",
            "preserve": ["identity", "background"],
            "acceptanceCriteria": ["boca sincronizada", "identidade estável"],
            "profileId": "longcat-avatar-1.5-ai2v-480p-int8-experimental-v1",
            "seed": 42,
        },
    }
    response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "longcat-v2-blocked-001"},
        json=payload,
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"].startswith("avatar_profile_unavailable:")
    with SessionLocal() as db:
        assert db.scalar(
            select(StudioGenerationJob).where(
                StudioGenerationJob.workspace_id == workspace,
                StudioGenerationJob.idempotency_key == "longcat-v2-blocked-001",
            )
        ) is None

    payload["request"] = {
        **payload["request"],
        "drivingAudioAssetId": voice_sample["id"],
        "drivingAudioChecksumSha256": voice_sample["checksumSha256"],
    }
    sample_response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "longcat-v2-voice-sample-001"},
        json=payload,
    )
    assert sample_response.status_code == 409
    assert sample_response.json()["detail"]["code"] == "voice_sample_cannot_be_driving_audio"


def test_avatar_v2_pins_profile_and_rejects_runtime_change(client, tmp_path, monkeypatch):
    from app import tasks
    from app.routers import assets as assets_router
    from app.services.studios import hybrid_video as hybrid_service
    from app.services.studios.avatar_video import execute_avatar_video

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _job_id: None)
    monkeypatch.setattr(hybrid_service, "hybrid_capability_manifest", lambda: ready_avatar_manifest())
    owner_email = "avatar-v2-binding@example.com"
    token, workspace = register(client, owner_email, "Avatar V2 Binding")
    document = create_presenter_document(client, token, workspace)
    portrait = BytesIO()
    Image.new("RGB", (64, 64), "#334455").save(portrait, format="PNG")
    wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32

    def upload(name, content, media_type):
        response = client.post(
            "/api/v1/assets/upload",
            headers=auth(token),
            data={"workspace_id": workspace, "title": name},
            files={"file": (name, content, media_type)},
        )
        assert response.status_code == 201, response.text
        return response.json()

    image = upload("portrait.png", portrait.getvalue(), "image/png")
    voice_sample = upload("sample.wav", wav_bytes, "audio/wav")
    final_audio = upload("final.wav", wav_bytes + b"final", "audio/wav")
    grant_id, identity_version_id, voice_version_id = add_active_presenter_capsule(
        workspace,
        owner_email,
        identity_sample_ids=[image["id"]],
        voice_sample_ids=[voice_sample["id"]],
    )
    approve_avatar_candidate(workspace, owner_email)
    AVATAR_VIDEO_PROVIDERS[FakeAvatarVideoProvider.name] = FakeAvatarVideoProvider()
    try:
        created = client.post(
            "/api/v1/studios/v1/jobs",
            headers={**auth(token), "Idempotency-Key": "avatar-v2-binding-001"},
            json={
                "workspaceId": workspace,
                "documentId": document["documentId"],
                "consentGrantId": grant_id,
                "identityVersionId": identity_version_id,
                "voiceVersionId": voice_version_id,
                "jobType": "avatar_video",
                "provider": "candidate.avatar-test",
                "request": {
                    "schemaVersion": "studio.avatar-video-request.v2",
                    "expectedDocumentRevision": document["revision"],
                    "sceneId": "scene-1",
                    "requirementId": "avatar-1",
                    "script": "Uma ideia encontra as pessoas.",
                    "referenceImageAssetId": image["id"],
                    "referenceImageChecksumSha256": image["checksumSha256"],
                    "drivingAudioAssetId": final_audio["id"],
                    "drivingAudioChecksumSha256": final_audio["checksumSha256"],
                    "drivingAudioDurationMs": 2800,
                    "drivingAudioOrigin": "uploaded_final_speech",
                    "performanceDirection": "Plano médio e fala calma.",
                    "acceptanceCriteria": ["Identidade estável"],
                    "profileId": "candidate-avatar-v2",
                },
            },
        )
        assert created.status_code == 202, created.text
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, created.json()["id"])
            assert job.request_payload["executionBinding"]["hybrid"]["runtimeRevision"] == "runtime-a"
            monkeypatch.setattr(
                hybrid_service,
                "hybrid_capability_manifest",
                lambda: ready_avatar_manifest("runtime-b"),
            )
            with pytest.raises(ValueError, match="avatar_execution_profile_changed"):
                execute_avatar_video(db, job, lambda _value: None, lambda: False)
    finally:
        AVATAR_VIDEO_PROVIDERS.pop(FakeAvatarVideoProvider.name, None)
