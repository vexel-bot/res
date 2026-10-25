"""Real project/job/storage boundaries; speech models are explicit silent fixtures."""

from types import SimpleNamespace

import pytest
from conftest import register
from sqlalchemy import func, select
from test_speech_synthesis_execution import (
    FakeSpeechProvider,
    FakeVoiceCloneProvider,
    FakeVoiceReferenceNormalizer,
    _admit_fake_provider,
    _admit_fake_voice_clone_provider,
    _create_voice_clone_identity,
)

from app.database import SessionLocal
from app.domain.studios.providers import SPEECH_PROVIDERS, VOICE_CLONE_PROVIDERS, VOICE_REFERENCE_NORMALIZERS
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, StudioVoiceProfile, StudioVoiceVersion, User
from app.routers import assets, studio_project_narration
from app.services.object_storage import LocalObjectStorage
from app.services.studios import production_narration, speech
from app.services.studios.compatibility import record_to_contract
from app.services.studios.jobs import execute_job_once

BASE = "/api/v1/studios/v1/projects"


def prepare(client, monkeypatch, tmp_path, kind="cloned", format="image"):
    token, workspace = register(client, "narration@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    monkeypatch.setattr(speech, "get_object_storage", lambda _backend=None: storage)
    monkeypatch.setattr(assets, "get_object_storage", lambda *args, **kwargs: storage)
    monkeypatch.setattr(studio_project_narration, "enqueue_job_task", lambda *args, **kwargs: None)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "narration@example.com"))
        if kind == "cloned":
            provider = FakeVoiceCloneProvider()
            _admit_fake_voice_clone_provider(db, provider.name)
            _, consent, version = _create_voice_clone_identity(db, tmp_path, storage, user, workspace)
            monkeypatch.setitem(VOICE_CLONE_PROVIDERS, provider.name, provider)
            normalizer = FakeVoiceReferenceNormalizer()
            monkeypatch.setitem(VOICE_REFERENCE_NORMALIZERS, normalizer.name, normalizer)
        else:
            provider = FakeSpeechProvider()
            _admit_fake_provider(db, provider.name)
            consent = None
            profile = StudioVoiceProfile(
                workspace_id=workspace,
                display_name="Voz licenciada de teste",
                locale="pt-BR",
                voice_type="stock",
                status="active",
                created_by=user.id,
            )
            db.add(profile)
            db.flush()
            version = StudioVoiceVersion(
                workspace_id=workspace,
                profile_id=profile.id,
                version=1,
                status="active",
                sample_asset_ids=[],
                derived_artifacts=[],
                content_hash="b" * 64,
                pronunciation_profile={"synthesisBinding": {"provider": provider.name, "voiceKey": "licensed-timbre"}},
                created_by=user.id,
            )
            db.add(version)
            db.flush()
            monkeypatch.setitem(SPEECH_PROVIDERS, provider.name, provider)
        provider.execution_environment = "local"
        voice_id, grant_id = version.id, consent.id if consent else None
        db.commit()
    response = client.post(
        BASE,
        headers=headers,
        json={
            "workspaceId": workspace,
            "requestKey": "project-narration-001",
            "title": "Como escolher o café",
            "objective": "Explicar como comparar a origem do café.",
            "audience": "Pessoas que preparam café em casa",
            "format": format,
            "voiceVersionId": voice_id,
        },
    )
    assert response.status_code == 201, response.text
    project = response.json()
    project = client.patch(
        f"{BASE}/{project['id']}",
        headers=headers,
        json={"expectedRevision": project["revision"], "directionId": "guide"},
    ).json()
    path = f"{BASE}/{project['id']}/narration"
    body = {
        "expectedRevision": project["revision"],
        "requestKey": "narration-request-001",
        "text": "Uma fala específica para a marca.",
    }
    return SimpleNamespace(
        headers=headers,
        project=project,
        path=path,
        body=body,
        voice_id=voice_id,
        grant_id=grant_id,
        provider=provider,
        storage=storage,
        workspace=workspace,
    )


@pytest.mark.parametrize(
    "kind,format", [("cloned", "image"), ("cloned", "video"), ("stock", "image"), ("stock", "video")]
)
def test_selected_narration_saves_reopens_and_reuses_the_same_job(client, monkeypatch, tmp_path, kind, format):
    case = prepare(client, monkeypatch, tmp_path, kind, format)
    assert client.get(case.path, headers=case.headers).json()["canGenerate"]
    response = client.post(case.path, headers=case.headers, json=case.body)
    assert response.status_code == 202, response.text
    submitted = response.json()
    replay = client.post(case.path, headers=case.headers, json=case.body)
    assert replay.status_code == 202, replay.text
    assert replay.json()["job"]["id"] == submitted["job"]["id"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 1
        job = db.get(StudioGenerationJob, submitted["job"]["id"])
        assert job.voice_version_id == case.voice_id
        assert job.consent_grant_id == case.grant_id
        assert job.request_payload["voiceKey"] == (case.voice_id if kind == "cloned" else "licensed-timbre")
        assert execute_job_once(db, job) == "succeeded", job.error_message
    loaded = client.get(case.path, headers=case.headers)
    assert loaded.status_code == 200, loaded.text
    result = loaded.json()
    assert result["text"] == case.body["text"]
    assert result["job"]["status"] == "succeeded"
    assert result["assetId"]
    audio = client.get(f"/api/v1/assets/{result['assetId']}/content", headers=case.headers)
    assert audio.status_code == 200, audio.text
    assert audio.content.startswith(b"RIFF")
    with SessionLocal() as db:
        asset = db.get(LibraryAsset, result["assetId"])
        assert asset.object_metadata["voiceVersionId"] == case.voice_id
        assert asset.object_metadata["generationJobId"] == submitted["job"]["id"]


def test_unavailable_or_remote_runtime_never_falls_back_to_another_voice(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    case.provider.execution_environment = "remote"
    state = client.get(case.path, headers=case.headers).json()
    assert not state["canGenerate"]
    assert state["blocker"] == "selected_voice_runtime_unavailable"
    assert client.post(case.path, headers=case.headers, json=case.body).status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 0


def test_narration_text_can_be_saved_without_enabling_an_unavailable_model(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    case.provider.execution_environment = "remote"
    body = {"expectedRevision": case.project["revision"], "text": "Um texto revisado antes de gerar áudio."}
    saved = client.patch(case.path, headers=case.headers, json=body)
    assert saved.status_code == 200, saved.text
    assert not saved.json()["canGenerate"]
    assert saved.json()["text"] == body["text"]
    assert client.get(case.path, headers=case.headers).json()["text"] == body["text"]
    assert (
        client.patch(case.path, headers=case.headers, json=body).json()["project"]["revision"]
        == saved.json()["project"]["revision"]
    )
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 0


def test_revision_conflict_and_changed_idempotency_payload_do_not_duplicate_jobs(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    assert client.post(case.path, headers=case.headers, json={**case.body, "expectedRevision": 1}).status_code == 409
    assert client.post(case.path, headers=case.headers, json=case.body).status_code == 202
    assert client.post(case.path, headers=case.headers, json={**case.body, "text": "Outra fala."}).status_code == 409
    assert (
        client.post(case.path, headers=case.headers, json={**case.body, "requestKey": "second-request-001"}).status_code
        == 409
    )
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 1
    assert client.post(case.path + "/cancel", headers=case.headers).status_code == 200
    current = client.get(case.path, headers=case.headers).json()["project"]
    second = client.post(
        case.path,
        headers=case.headers,
        json={
            **case.body,
            "requestKey": "second-request-001",
            "text": "Uma segunda fala.",
            "expectedRevision": current["revision"],
        },
    )
    assert second.status_code == 202, second.text
    assert client.post(case.path + "/cancel", headers=case.headers).status_code == 200
    old = client.post(
        case.path, headers=case.headers, json={**case.body, "expectedRevision": second.json()["project"]["revision"]}
    )
    assert old.status_code == 409, old.text
    assert client.get(case.path, headers=case.headers).json()["job"]["id"] == second.json()["job"]["id"]


def test_revocation_blocks_use_but_does_not_prevent_cancelling_the_job(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    assert client.post(case.path, headers=case.headers, json=case.body).status_code == 202
    revoked = client.post(
        f"/api/v1/studios/v1/consents/{case.grant_id}/revoke",
        headers=case.headers,
        json={"reason": "Revogação durante a espera na fila."},
    )
    assert revoked.status_code == 200, revoked.text
    assert client.get(case.path, headers=case.headers).status_code == 422
    cancelled = client.post(case.path + "/cancel", headers=case.headers)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["job"]["status"] == "cancelled"
    other_token, _ = register(client, "other-narration@example.com")
    other = {"Authorization": f"Bearer {other_token}"}
    assert client.get(case.path, headers=other).status_code == 404
    assert client.post(case.path + "/cancel", headers=other).status_code == 404


@pytest.mark.parametrize("kind", ["cloned", "stock"])
def test_editorial_narration_uses_the_selected_voice_instead_of_its_default(client, monkeypatch, tmp_path, kind):
    case = prepare(client, monkeypatch, tmp_path, kind)
    response = client.post(
        "/api/v1/studios/v1/documents",
        headers=case.headers,
        json={
            "workspaceId": case.workspace,
            "title": "Vídeo com a voz escolhida",
            "contentType": "video",
            "brief": {"objective": "Explicar a origem do café.", "audience": "Pessoas que preparam café em casa"},
            "composition": {
                "pages": [{"id": "page-1", "width": 1080, "height": 1920, "durationMs": 5000, "layers": []}],
                "tracks": [],
            },
            "voiceRef": case.project["casting"]["voice"],
        },
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["documentId"]
    monkeypatch.setattr(production_narration, "get_object_storage", lambda *args: case.storage)
    state = {
        "id": "editorial-selected-voice-001",
        "jobs": {},
        "artifacts": {"direction": {"beats": [{"id": "one", "narration": case.body["text"]}]}},
    }
    request = SimpleNamespace(
        evaluation_scope="audiovisual",
        narration_asset_id=None,
        stock_voice_provider="wrong-default-provider",
        stock_voice_key="wrong-default-timbre",
    )
    with SessionLocal() as db:
        record = db.get(CreativeDocument, document_id)
        user = db.get(User, record.created_by)
        measurements, job = production_narration.prepare_narration(db, record, state, request, user)
        assert measurements is None
        assert job.voice_version_id == case.voice_id
        assert job.provider == case.provider.name
        assert execute_job_once(db, job) == "succeeded", job.error_message
        measurements, queued = production_narration.prepare_narration(db, record, state, request, user)
        assert queued is None
        assert measurements[0]["voiceVersionId"] == case.voice_id
        assert measurements[0]["durationSeconds"] > 0
        assert record_to_contract(record).voice_ref.id == case.voice_id
        assert job.result_payload["assetId"] in {ref.id for ref in record_to_contract(record).assets}
        request.evaluation_scope = "visual_only"
        with pytest.raises(ValueError, match="production_selected_voice_requires_audio"):
            production_narration.prepare_narration(db, record, state, request, user)


def test_narration_result_cannot_be_relabeled_as_another_selected_voice(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    submitted = client.post(case.path, headers=case.headers, json=case.body).json()
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, submitted["job"]["id"])
        assert execute_job_once(db, job) == "succeeded", job.error_message
        asset = db.get(LibraryAsset, job.result_payload["assetId"])
        asset.object_metadata = {**asset.object_metadata, "voiceVersionId": "another-voice"}
        db.commit()
    response = client.get(case.path, headers=case.headers)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "production_voice_lineage_conflict"
