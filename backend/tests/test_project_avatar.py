"""Project orchestration and real storage; silent audio/transport avatar are not model qualification."""

import hashlib

import pytest
from conftest import register
from sqlalchemy import func, select
from test_avatar_independent_cast import prepare as prepare_cast

from app.database import SessionLocal
from app.domain.studios.contracts import SpeechSynthesisRequestV1
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, StudioVoiceVersion, User, WorkspaceResource
from app.routers import studio_project_avatar
from app.services.studios.jobs import execute_job_once

BASE = "/api/v1/studios/v1/projects"


def prepare(client, monkeypatch, tmp_path, face="face", voice="voice"):
    case = prepare_cast(client, monkeypatch, tmp_path, face, voice)
    monkeypatch.setattr(studio_project_avatar, "enqueue_job_task", lambda *args, **kwargs: None)
    payload = case.payload
    response = client.post(
        BASE,
        headers=case.headers,
        json={
            "workspaceId": payload["workspaceId"],
            "requestKey": "project-avatar-cast-001",
            "title": "Café de origem",
            "objective": "Explicar como comparar a origem do café.",
            "audience": "Pessoas que preparam café em casa",
            "format": "video",
            "identityVersionId": payload["identityVersionId"],
            "voiceVersionId": payload["voiceVersionId"],
        },
    )
    assert response.status_code == 201, response.text
    project = response.json()
    project = client.patch(
        f"{BASE}/{project['id']}", headers=case.headers, json={"expectedRevision": 1, "directionId": "guide"}
    ).json()
    script = payload["request"]["script"]
    script_hash = hashlib.sha256(script.encode()).hexdigest()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "cast@example.com"))
        audio = db.get(LibraryAsset, payload["request"]["drivingAudioAssetId"])
        kind = "voice_clone" if voice == "voice" else "stock_voice"
        if kind == "stock_voice":
            db.get(StudioVoiceVersion, payload["voiceVersionId"]).pronunciation_profile = {
                "synthesisBinding": {"provider": "fixture.speech", "voiceKey": payload["voiceVersionId"]}
            }
        job = StudioGenerationJob(
            workspace_id=payload["workspaceId"],
            requested_by=user.id,
            consent_grant_id=case.narrator["consentGrantId"],
            voice_version_id=payload["voiceVersionId"],
            job_type=kind,
            provider="fixture.speech",
            idempotency_key="narration-fixture",
            payload_hash="a" * 64,
            correlation_id=f"department-narration:{project['id']}",
            status="succeeded",
            request_payload=SpeechSynthesisRequestV1(
                text=script, script_digest_sha256=script_hash, voice_key=payload["voiceVersionId"], locale="pt-BR"
            ).model_dump(by_alias=True),
        )
        db.add(job)
        db.flush()
        result = {
            "jobType": kind,
            "assetId": audio.id,
            "scriptDigestSha256": script_hash,
            "checksumSha256": audio.checksum_sha256,
            "speech": {"durationMs": 2800},
        }
        job.result_payload = result
        audio.object_metadata = {
            **(audio.object_metadata or {}),
            "generationJobId": job.id,
            "voiceVersionId": job.voice_version_id,
            "consentGrantId": job.consent_grant_id,
            "scriptDigestSha256": script_hash,
            "speechSynthesisJobResult": result,
        }
        row = db.get(WorkspaceResource, project["id"])
        row.payload = {**row.payload, "narration": {"jobId": job.id, "text": script}}
        db.commit()
    case.project = project
    case.path = f"{BASE}/{project['id']}/avatar"
    return case


def quote(client, case):
    result = client.post(case.path + "/plan", headers=case.headers, json={})
    assert result.status_code == 200, result.text
    return result.json()


def submit(client, case, body=None, key="project-avatar-submit-001"):
    planned = body or quote(client, case)
    return client.post(
        case.path,
        headers={**case.headers, "Idempotency-Key": key},
        json={k: v for k, v in planned.items() if k != "schemaVersion"},
    )


@pytest.mark.parametrize(
    "face,voice", [("face", "voice"), ("face", "stock_voice"), ("character", "voice"), ("character", "stock_voice")]
)
def test_project_avatar_binds_final_audio_and_independent_appearance_atomically(
    client, monkeypatch, tmp_path, face, voice
):
    case = prepare(client, monkeypatch, tmp_path, face, voice)
    planned = quote(client, case)
    assert "binding" not in planned
    assert planned["durationSeconds"] == 2.8
    response = submit(client, case, planned)
    assert response.status_code == 202, response.text
    job = response.json()
    assert submit(client, case, planned).json()["id"] == job["id"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 2
        context = db.get(CreativeDocument, planned["documentId"])
        assert context.canonical_document["voiceRef"]["id"] == case.payload["voiceVersionId"]
        queued = db.get(StudioGenerationJob, job["id"])
        assert queued.request_payload["drivingAudioAssetId"] == case.payload["request"]["drivingAudioAssetId"]
        bound = queued.request_payload["executionBinding"]["cast"]
        assert bound["identity"]["consentGrantId"] == case.appearance["consentGrantId"]
        assert bound["voice"]["consentGrantId"] == case.narrator["consentGrantId"]
        assert execute_job_once(db, queued) == "succeeded", queued.error_message
    loaded = client.get(case.path, headers=case.headers)
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["assetId"]
    monkeypatch.setattr(
        studio_project_avatar.project_avatar, "plan", lambda *args: (_ for _ in ()).throw(ValueError("offline"))
    )
    assert client.get(case.path, headers=case.headers).json()["assetId"] == loaded.json()["assetId"]


@pytest.mark.parametrize(
    "field,value", [("durationSeconds", 0.1), ("planDigestSha256", "b" * 64), ("documentId", "other-context")]
)
def test_plan_tampering_creates_neither_context_nor_job(client, monkeypatch, tmp_path, field, value):
    case = prepare(client, monkeypatch, tmp_path)
    planned = quote(client, case)
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(CreativeDocument))
    result = submit(client, case, {**planned, field: value})
    assert result.status_code == 409, result.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(CreativeDocument)) == before
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 1


def test_new_script_requires_new_final_audio_and_live_rights(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    planned = quote(client, case)
    with SessionLocal() as db:
        row = db.get(WorkspaceResource, case.project["id"])
        row.payload = {**row.payload, "narrationDraft": "Um texto ainda não sintetizado."}
        db.commit()
    assert submit(client, case, planned).status_code == 422
    assert client.get(case.path, headers=case.headers).json()["blocker"] == "avatar_narration_draft_not_generated"
    with SessionLocal() as db:
        row = db.get(WorkspaceResource, case.project["id"])
        row.payload = {**row.payload, "narrationDraft": None}
        db.commit()
    created = submit(client, case, planned)
    assert created.status_code == 202, created.text
    revoked = client.post(
        f"/api/v1/studios/v1/consents/{case.narrator['consentGrantId']}/revoke",
        headers=case.headers,
        json={"reason": "Encerrar a autorização de narração."},
    )
    assert revoked.status_code == 200, revoked.text
    assert submit(client, case, planned).status_code == 422
    assert client.post(case.path + "/cancel", headers=case.headers).json()["status"] == "cancelled"
    other, _ = register(client, "other-avatar@example.com")
    assert client.get(case.path, headers={"Authorization": f"Bearer {other}"}).status_code == 404


def test_stale_revision_rolls_back_the_context_and_generation_job(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    planned = quote(client, case)

    # Simulate a revision change at the transaction's compare-and-swap boundary.
    def conflict(db, row, expected, values):
        from fastapi import HTTPException

        db.rollback()
        raise HTTPException(409, "revision conflict")

    monkeypatch.setattr(studio_project_avatar, "change", conflict)
    assert submit(client, case, planned).status_code == 409
    with SessionLocal() as db:
        assert db.get(CreativeDocument, planned["documentId"]) is None
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 1


def test_current_session_requires_signed_matching_video_admission(client, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from test_clicko_studio_bridge import KEY, headers

    from app import studio_app

    case = prepare(client, monkeypatch, tmp_path)
    planned = quote(client, case)
    body = {k: v for k, v in planned.items() if k != "schemaVersion"}
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "cast@example.com"))
        actor = user.id
        user.password_hash = "!session-bridge-only"
        db.commit()
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    monkeypatch.setattr(studio_app, "scoped_ids", lambda claims: (case.payload["workspaceId"], actor))
    key = "signed-avatar-admission-001"
    admission = {
        "id": "a" * 64,
        "key": key,
        "documentId": planned["documentId"],
        "seconds": 2.8,
        "operation": "generate_avatar",
    }
    with TestClient(studio_app.app) as bridge:
        wrong_module = bridge.post(case.path, json=body, headers={**headers(), "Idempotency-Key": key})
        assert wrong_module.status_code == 403, wrong_module.text
        for claim in [None, {**admission, "seconds": 0.1}, {**admission, "id": "invalid"}]:
            response = bridge.post(
                case.path,
                json=body,
                headers={**headers(module="create-video", mediaAdmission=claim), "Idempotency-Key": key},
            )
            assert response.status_code == 422, response.text
            with SessionLocal() as db:
                assert db.get(CreativeDocument, planned["documentId"]) is None
        response = bridge.post(
            case.path,
            json=body,
            headers={**headers(module="create-video", mediaAdmission=admission), "Idempotency-Key": key},
        )
        assert response.status_code == 202, response.text
        assert response.json()["request"]["executionBinding"]["commercialAdmission"] == admission
        generic = bridge.post(
            "/api/v1/studios/v1/jobs",
            json=case.payload,
            headers={**headers(module="create-video", mediaAdmission=admission), "Idempotency-Key": key},
        )
        assert generic.status_code == 422, generic.text
        assert generic.json()["detail"]["code"] == "use_metered_media_endpoint"


def test_completed_avatar_is_handed_to_native_montage_and_changed_audio_is_rejected(client, monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app.routers import studio_department

    case = prepare(client, monkeypatch, tmp_path)
    response = submit(client, case)
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        assert execute_job_once(db, job) == "succeeded", job.error_message
        asset_id = job.result_payload["assetId"]
        result_asset = db.get(LibraryAsset, asset_id)
        from app.services.object_storage import get_object_storage

        storage = get_object_storage(result_asset.storage_backend)
        with storage.materialize(result_asset.storage_key) as original:
            stored = storage.put_file(
                original, key=f"{job.workspace_id}/uploads/brand-video.mp4", media_type="video/mp4"
            )
        source = LibraryAsset(
            workspace_id=job.workspace_id,
            title="Material original da marca",
            asset_type="video",
            media_type="video/mp4",
            storage_key=stored.key,
            checksum_sha256=result_asset.checksum_sha256,
        )
        db.add(source)
        db.flush()
        source_id = source.id
        row = db.get(WorkspaceResource, case.project["id"])
        row.payload = {**row.payload, "sourceAssetId": source_id}
        db.commit()
    imports = []
    # Native compilation/export is a separate acceptance test. This asserts the
    # real HTTP/DB handoff, not the quality or decoding of the transport fixture.
    monkeypatch.setattr(
        studio_department, "record_to_contract", lambda document: SimpleNamespace(native_editor_state=True)
    )
    monkeypatch.setattr(
        studio_department.craft, "commands", lambda db, document, request, *args: imports.extend(request.commands)
    )
    monkeypatch.setattr(studio_department, "render_job", lambda *args: SimpleNamespace(id="native-render-fixture"))
    current = client.get(f"{BASE}/{case.project['id']}", headers=case.headers).json()
    produced = client.post(
        f"{BASE}/{case.project['id']}/produce", headers=case.headers, json={"expectedRevision": current["revision"]}
    )
    assert produced.status_code == 200, produced.text
    assert imports[0].params["assetId"] == asset_id
    assert imports[1].params["assetId"] == source_id
    with SessionLocal() as db:
        document = db.get(CreativeDocument, produced.json()["documentId"])
        assert document.canonical_document["composition"]["pages"][0]["durationMs"] == 2800
        assert document.canonical_document["voiceRef"]["id"] == case.payload["voiceVersionId"]
        row = db.get(WorkspaceResource, case.project["id"])
        row.payload = {**row.payload, "narrationDraft": "Uma nova fala ainda sem áudio."}
        db.commit()
    state = client.get(case.path, headers=case.headers).json()
    assert state["assetId"] is None
    assert state["blocker"] == "avatar_narration_draft_not_generated"
