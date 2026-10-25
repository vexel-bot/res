"""Project narration and montage admission use real stored media, explicit speech fixtures."""

from io import BytesIO
from types import SimpleNamespace

import pytest
from native_project_avatar_acceptance import ffmpeg, tone
from PIL import Image
from sqlalchemy import func, select
from test_project_narration import prepare as prepare_narration

from app.database import SessionLocal
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, WorkspaceResource
from app.routers import studio_department
from app.services.object_storage import sha256_file
from app.services.studios import craft, project_montage, project_voiceover
from app.services.studios.jobs import execute_job_once

BASE = "/api/v1/studios/v1/projects"


def prepare(client, monkeypatch, tmp_path, kind="cloned", source_kind="video", video_seconds=1.2, speak=True):
    case = prepare_narration(client, monkeypatch, tmp_path, kind, "video")
    for module in (craft, project_montage, project_voiceover):
        monkeypatch.setattr(module, "get_object_storage", lambda *args, **kwargs: case.storage)
    method = "clone" if kind == "cloned" else "synthesize"
    original = getattr(case.provider, method)

    def generate(*args, **kwargs):
        result = original(*args, **kwargs)
        destination = args[3] if kind == "cloned" else args[1]
        tone(destination, 2.8, 440)
        return result.model_copy(update={"duration_ms": 2800, "artifact_checksum_sha256": sha256_file(destination)})

    monkeypatch.setattr(case.provider, method, generate)
    if source_kind == "image":
        buffer = BytesIO()
        Image.new("RGB", (320, 180), "#14a56e").save(buffer, "PNG")
        filename, data, mime = "brand.png", buffer.getvalue(), "image/png"
    else:
        video = tmp_path / "brand-voiceover.mp4"
        audio = tmp_path / "original-sound.wav"
        tone(audio, video_seconds, 880)
        # The source changes red -> blue; a short source must hold the final blue frame.
        ffmpeg(
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x180:r=30",
            "-i",
            audio,
            "-vf",
            "drawbox=x=0:y=0:w=iw:h=ih:color=blue:t=fill:enable='gte(t,0.6)'",
            "-t",
            video_seconds,
            "-threads",
            1,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-y",
            video,
        )
        filename, data, mime = "brand.mp4", video.read_bytes(), "video/mp4"
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=case.headers,
        data={"workspace_id": case.workspace, "title": "Material da marca"},
        files={"file": (filename, data, mime)},
    )
    assert uploaded.status_code == 201, uploaded.text
    case.source_id = uploaded.json()["id"]
    created = client.post(
        BASE,
        headers=case.headers,
        json={
            "workspaceId": case.workspace,
            "requestKey": "voiceover-complete-001",
            "title": "Uma fala para a marca",
            "objective": "Explicar a origem do café com a voz escolhida.",
            "audience": "Pessoas que preparam café em casa",
            "format": "video",
            "voiceVersionId": case.voice_id,
            "sourceAssetId": case.source_id,
        },
    )
    assert created.status_code == 201, created.text
    case.project = created.json()
    chosen = client.patch(
        f"{BASE}/{case.project['id']}", headers=case.headers, json={"expectedRevision": 1, "directionId": "guide"}
    )
    assert chosen.status_code == 200, chosen.text
    case.project = chosen.json()
    case.path = f"{BASE}/{case.project['id']}/narration"
    case.body = {**case.body, "expectedRevision": case.project["revision"]}
    if speak:
        response = client.post(case.path, headers=case.headers, json=case.body)
        assert response.status_code == 202, response.text
        case.speech_job_id = response.json()["job"]["id"]
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, case.speech_job_id)
            assert execute_job_once(db, job) == "succeeded", job.error_message
            case.audio_id = job.result_payload["assetId"]
        case.project = client.get(f"{BASE}/{case.project['id']}", headers=case.headers).json()
    return case


def produce(client, case):
    current = client.get(f"{BASE}/{case.project['id']}", headers=case.headers).json()
    return client.post(
        f"{BASE}/{case.project['id']}/produce", headers=case.headers, json={"expectedRevision": current["revision"]}
    )


@pytest.mark.parametrize(
    "kind,source_kind", [("cloned", "video"), ("stock", "video"), ("cloned", "image"), ("stock", "image")]
)
def test_selected_voice_is_a_separate_native_audio_track_without_an_avatar(
    client, monkeypatch, tmp_path, kind, source_kind
):
    case = prepare(client, monkeypatch, tmp_path, kind, source_kind)
    commands = []
    # Contract handoff only. Native decoding/export is covered by the explicit acceptance.
    monkeypatch.setattr(
        studio_department, "record_to_contract", lambda record: SimpleNamespace(native_editor_state=True)
    )
    monkeypatch.setattr(craft, "commands", lambda db, document, request, *args: commands.extend(request.commands))
    monkeypatch.setattr(studio_department, "render_job", lambda *args: SimpleNamespace(id="voiceover-render-fixture"))
    response = produce(client, case)
    assert response.status_code == 200, response.text
    project = response.json()
    plan = project["montagePlan"]
    assert plan["audioAssetId"] == case.audio_id
    assert plan["narrationJobId"] == case.speech_job_id
    assert plan["durationMs"] == 2800
    assert not plan["originalAudioEnabled"]
    assert (plan["holdFromFrame"] is None) == (source_kind == "image")
    with SessionLocal() as db:
        document = db.get(CreativeDocument, project["documentId"])
        timeline = document.canonical_document["composition"]["mediaTimeline"]
        assert timeline["tracks"][0]["clips"][0]["assetId"] == case.source_id
        assert timeline["tracks"][1]["clips"][0]["assetId"] == case.audio_id
        assert document.canonical_document["voiceRef"]["id"] == case.voice_id
        assert document.canonical_document["identityRef"] is None
        assert db.get(LibraryAsset, case.source_id).lifecycle_status == "active"
    assert [item.id for item in commands][:2] == ["edit.selectAll", "clip.fitToFrame"]
    assert produce(client, case).json()["jobId"] == project["jobId"]


def test_unsynthesized_script_and_revoked_voice_cannot_create_a_montage(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path, speak=False)
    assert produce(client, case).json()["detail"]["code"] == "voiceover_final_narration_required"
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(CreativeDocument)) == 0
    response = client.post(case.path, headers=case.headers, json=case.body)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["job"]["id"])
        assert execute_job_once(db, job) == "succeeded", job.error_message
        row = db.get(WorkspaceResource, case.project["id"])
        row.payload = {**row.payload, "narrationDraft": "Uma nova fala ainda sem áudio."}
        db.commit()
    assert produce(client, case).json()["detail"]["code"] == "voiceover_narration_draft_not_generated"
    client.post(
        f"/api/v1/studios/v1/consents/{case.grant_id}/revoke",
        headers=case.headers,
        json={"reason": "Encerrar o uso da voz de teste."},
    )
    assert produce(client, case).status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(CreativeDocument)) == 0


def test_unknown_picture_duration_is_not_replaced_by_the_original_audio_duration(client, monkeypatch, tmp_path):
    case = prepare(client, monkeypatch, tmp_path)
    original = project_voiceover.MEDIA_PROBE_PROVIDERS["builtin.ffprobe"]

    def probe(path, *, asset_id, checksum_sha256):
        value = original.probe(path, asset_id=asset_id, checksum_sha256=checksum_sha256)
        if asset_id == case.source_id:
            value = value.model_copy(
                update={"video_streams": [value.video_streams[0].model_copy(update={"duration_microseconds": None})]}
            )
        return value

    monkeypatch.setitem(project_voiceover.MEDIA_PROBE_PROVIDERS, "builtin.ffprobe", SimpleNamespace(probe=probe))
    response = produce(client, case)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "voiceover_video_duration_unverified"
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(CreativeDocument)) == 0
