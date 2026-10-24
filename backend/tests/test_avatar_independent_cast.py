"""Transport/rights tests; fixtures do not qualify model output or biometric quality."""

import hashlib
import wave
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image
from sqlalchemy import select
from test_avatar_video_job_boundary import (
    approve_avatar_candidate,
    create_presenter_document,
    ready_avatar_manifest,
)
from test_studio_identity_library import activate_for_binding_test, enroll, setup

from app.database import SessionLocal
from app.domain.studios.contracts import AvatarVideoEncodeResultV1
from app.domain.studios.providers import AVATAR_VIDEO_PROVIDERS
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, StudioVoiceVersion
from app.services.object_storage import sha256_file
from app.services.studios.avatar_video import execute_avatar_video
from app.services.studios.jobs import (
    require_avatar_v2_media_binding,
    require_stock_voice_binding,
    require_voice_clone_binding,
)


class TransportAvatar:
    name = "candidate.avatar-test"
    version = "1.0.0"

    def render(self, document, request, images, audio, destination, progress, is_cancelled):
        assert images[0].read_bytes().startswith(b"\x89PNG")
        assert audio.read_bytes().startswith(b"RIFF")
        destination.write_bytes(b"transport-fixture-not-a-qualified-video")
        return AvatarVideoEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=request.width,
            height=request.height,
            fps=request.fps,
            duration_ms=2800,
            artifact_checksum_sha256=sha256_file(destination),
            synthetic_content_disclosed=True,
        )


def prepare(client, monkeypatch, tmp_path, face="face", voice="voice"):
    from app import tasks
    from app.routers import assets
    from app.services.studios import hybrid_video

    monkeypatch.setattr(assets.settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _id: None)
    monkeypatch.setattr(hybrid_video, "hybrid_capability_manifest", ready_avatar_manifest)
    monkeypatch.setitem(AVATAR_VIDEO_PROVIDERS, TransportAvatar.name, TransportAvatar())
    headers, body = setup(client)
    token = headers["Authorization"].split()[1]
    document = create_presenter_document(client, token, body["workspaceId"])

    def enroll_mode(mode):
        request = {**body, "requestKey": f"independent-enroll-{mode}", "mode": mode}
        request.pop("audioAssetId" if mode in {"face", "character"} else "imageAssetId")
        if mode in {"character", "stock_voice"}:
            request.pop("expiresAt")
            request["rightsReference"] = "Conteúdo próprio; comprovante separado para revisão."
        receipt = enroll(client, headers, request)
        activate_for_binding_test(receipt)
        return receipt

    appearance, narrator = enroll_mode(face), enroll_mode(voice)

    def upload(name, content, mime):
        response = client.post(
            "/api/v1/assets/upload",
            headers=headers,
            data={"workspace_id": body["workspaceId"], "title": name},
            files={"file": (name, content, mime)},
        )
        assert response.status_code == 201, response.text
        return response.json()

    portrait = BytesIO()
    Image.new("RGB", (64, 64), "#334455").save(portrait, format="PNG")
    speech = BytesIO()
    with wave.open(speech, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\0\0" * 67200)
    image = upload("portrait.png", portrait.getvalue(), "image/png")
    audio = upload("final.wav", speech.getvalue(), "audio/wav")
    with SessionLocal() as db:
        from app.models import StudioIdentityVersion

        db.get(StudioIdentityVersion, appearance["identityVersionId"]).sample_asset_ids = [image["id"]]
        db.commit()
    approve_avatar_candidate(body["workspaceId"], "cast@example.com")
    payload = {
        "workspaceId": body["workspaceId"],
        "documentId": document["documentId"],
        "identityVersionId": appearance["identityVersionId"],
        "voiceVersionId": narrator["voiceVersionId"],
        "consentGrantId": appearance["consentGrantId"] or narrator["consentGrantId"],
        "jobType": "avatar_video",
        "provider": TransportAvatar.name,
        "request": {
            "schemaVersion": "studio.avatar-video-request.v2",
            "expectedDocumentRevision": document["revision"],
            "sceneId": "scene-1",
            "requirementId": "avatar-1",
            "script": "Uma ideia encontra as pessoas.",
            "referenceImageAssetId": image["id"],
            "referenceImageChecksumSha256": image["checksumSha256"],
            "drivingAudioAssetId": audio["id"],
            "drivingAudioChecksumSha256": audio["checksumSha256"],
            "drivingAudioDurationMs": 2800,
            "drivingAudioOrigin": "uploaded_final_speech",
            "performanceDirection": "Plano médio e fala calma.",
            "acceptanceCriteria": ["Identidade estável"],
            "profileId": "candidate-avatar-v2",
        },
    }
    return SimpleNamespace(headers=headers, payload=payload, appearance=appearance, narrator=narrator)


def enqueue(client, case, key="avatar-independent-001"):
    return client.post("/api/v1/studios/v1/jobs", headers={**case.headers, "Idempotency-Key": key}, json=case.payload)


@pytest.mark.parametrize(
    "face,voice", [("face", "voice"), ("face", "stock_voice"), ("character", "voice"), ("character", "stock_voice")]
)
def test_avatar_independent_cast_roundtrip_and_revocation(client, monkeypatch, tmp_path, face, voice):
    case = prepare(client, monkeypatch, tmp_path, face, voice)
    response = enqueue(client, case)
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        binding = job.request_payload["executionBinding"]["cast"]
        assert binding["identity"]["consentGrantId"] == case.appearance["consentGrantId"]
        assert binding["voice"]["consentGrantId"] == case.narrator["consentGrantId"]
        result = execute_avatar_video(db, job, lambda _: None, lambda: False)
        artifact = db.get(LibraryAsset, result["assetId"])
        assert artifact.object_metadata["castBinding"] == binding
        assert result["voiceVersionId"] == case.narrator["voiceVersionId"]
        # Synthetic/licensed subjects legitimately have no natural-person grant.
        assert result["consentGrantId"] == case.payload["consentGrantId"]
        assert execute_avatar_video(db, job, lambda _: None, lambda: False) == result
        if case.narrator["consentGrantId"]:
            revoked = client.post(
                f"/api/v1/studios/v1/consents/{case.narrator['consentGrantId']}/revoke",
                headers=case.headers,
                json={"reason": "Fim da autorização de narração."},
            )
            assert revoked.status_code == 200, revoked.text
            with pytest.raises(ValueError, match="not_active"):
                execute_avatar_video(db, job, lambda _: None, lambda: False)


def test_primary_grant_cannot_replace_the_appearance_authorization(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    case.payload["consentGrantId"] = case.narrator["consentGrantId"]
    response = enqueue(client, case)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "identity_version_consent_mismatch"


def test_avatar_cannot_override_the_cast_saved_in_the_document(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    with SessionLocal() as db:
        record = db.get(CreativeDocument, case.payload["documentId"])
        record.canonical_document = {
            **record.canonical_document,
            "voiceRef": {
                "id": "another-saved-voice",
                "version": 1,
                "consentGrantId": case.narrator["consentGrantId"],
            },
        }
        db.commit()
    response = enqueue(client, case)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "cast_version_reference_mismatch"


@pytest.mark.parametrize(
    "change,expected", [("voice_revoked", "not_active"), ("document_edited", "studio_document_conflict")]
)
def test_changes_during_inference_discard_the_artifact(client, monkeypatch, tmp_path, change, expected):
    case = prepare(client, monkeypatch, tmp_path)
    response = enqueue(client, case)
    assert response.status_code == 202, response.text
    provider = TransportAvatar()

    def render(*args):
        result = provider.render(*args)
        if change == "voice_revoked":
            revoked = client.post(
                f"/api/v1/studios/v1/consents/{case.narrator['consentGrantId']}/revoke",
                headers=case.headers,
                json={"reason": "Encerramento durante a execução."},
            )
            assert revoked.status_code == 200, revoked.text
        else:
            with SessionLocal() as update:
                update.get(CreativeDocument, case.payload["documentId"]).revision += 1
                update.commit()
        return result

    monkeypatch.setitem(
        AVATAR_VIDEO_PROVIDERS,
        TransportAvatar.name,
        SimpleNamespace(name=provider.name, version=provider.version, render=render),
    )
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        with pytest.raises(ValueError, match=expected):
            execute_avatar_video(db, job, lambda _: None, lambda: False)
        assets = db.scalars(select(LibraryAsset).where(LibraryAsset.asset_type == "video")).all()
        assert not assets


def test_execution_rejects_a_changed_cast_binding_before_calling_the_provider(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    response = enqueue(client, case)
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        binding = job.request_payload["executionBinding"]
        job.request_payload = {**job.request_payload, "executionBinding": {**binding, "cast": {}}}
        db.commit()
        with pytest.raises(ValueError, match="avatar_cast_binding_changed"):
            execute_avatar_video(db, job, lambda _: None, lambda: False)


@pytest.mark.parametrize(
    "voice,origin,job_type",
    [("voice", "cloned_voice_synthesis", "voice_clone"), ("stock_voice", "stock_voice_synthesis", "stock_voice")],
)
def test_synthesized_audio_must_match_the_exact_selected_voice(client, monkeypatch, tmp_path, voice, origin, job_type):
    case = prepare(client, monkeypatch, tmp_path, voice=voice)
    request = case.payload["request"]
    request["drivingAudioOrigin"] = origin
    with SessionLocal() as db:
        audio = db.get(LibraryAsset, request["drivingAudioAssetId"])
        metadata = {
            "voiceVersionId": "a-different-voice",
            "speechSynthesisJobResult": {
                "jobType": job_type,
                "scriptDigestSha256": hashlib.sha256(request["script"].encode()).hexdigest(),
                "speech": {"durationMs": 2800},
            },
        }
        audio.object_metadata = metadata
        db.commit()
    response = enqueue(client, case)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "avatar_driving_audio_voice_mismatch"
    with SessionLocal() as db:
        audio = db.get(LibraryAsset, request["drivingAudioAssetId"])
        audio.object_metadata = {**metadata, "voiceVersionId": case.payload["voiceVersionId"]}
        db.commit()
        require_avatar_v2_media_binding(
            db,
            workspace_id=case.payload["workspaceId"],
            document_id=case.payload["documentId"],
            identity_version_id=case.payload["identityVersionId"],
            voice_version_id=case.payload["voiceVersionId"],
            payload=request,
        )
    assert enqueue(client, case, "avatar-correct-voice-001").status_code == 202


def test_bound_stock_synthesis_cannot_use_another_provider_or_timbre(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path, voice="stock_voice")
    with SessionLocal() as db:
        version = db.get(StudioVoiceVersion, case.narrator["voiceVersionId"])
        version.pronunciation_profile = {"synthesisBinding": {"provider": "candidate.voice", "voiceKey": "narrator-a"}}
        db.commit()
        args = dict(workspace_id=case.payload["workspaceId"], voice_version_id=version.id)
        speech = {
            "locale": "pt-BR",
            "text": "Uma ideia.",
            "scriptDigestSha256": hashlib.sha256(b"Uma ideia.").hexdigest(),
        }
        assert (
            require_stock_voice_binding(
                db, **args, provider="candidate.voice", payload={**speech, "voiceKey": "narrator-a"}
            )
            == version
        )
        for provider, key in [("another.provider", "narrator-a"), ("candidate.voice", "narrator-b")]:
            with pytest.raises(ValueError, match="stock_voice_synthesis_binding_mismatch"):
                require_stock_voice_binding(db, **args, provider=provider, payload={**speech, "voiceKey": key})


def test_clone_binding_refreshes_a_version_deleted_by_another_session(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    args = dict(
        workspace_id=case.payload["workspaceId"],
        voice_version_id=case.narrator["voiceVersionId"],
        consent_grant_id=case.narrator["consentGrantId"],
    )
    with SessionLocal() as db:
        cached = require_voice_clone_binding(db, **args)
        assert cached.status == "active"
        with SessionLocal() as change:
            change.get(StudioVoiceVersion, cached.id).status = "deleting"
            change.commit()
        with pytest.raises(ValueError, match="identity_version_not_active"):
            require_voice_clone_binding(db, **args)
