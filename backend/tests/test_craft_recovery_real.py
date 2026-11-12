"""Offline qualification with the real EffectCraft runtime and a simulated Messages API."""
import json
import os
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from conftest import register
from media_fixtures import create_source

from app.database import SessionLocal
from app.models import LibraryAsset, StudioMediaIngest
from app.services.studios.craft_source_media import read_transcript
from app.services.studios import craft_agent, llm_connections

pytestmark = pytest.mark.skipif(
    os.environ.get("CLICKO_TEST_REAL_CRAFT") != "1", reason="requires the built EffectCraft runtime",
)


def test_filmcraft_reads_source_before_editing_and_exports(client, monkeypatch, tmp_path):
    token, workspace = register(client, "filmcraft-source@example.com")
    headers = {"Authorization": "Bearer " + token}
    root = "/api/v1/studios/v1"
    source = tmp_path / "raw.mp4"
    create_source(source)
    upload = client.post("/api/v1/assets/upload", headers=headers,
                         data={"workspace_id": workspace, "title": "Raw clip"},
                         files={"file": (source.name, source.read_bytes(), "video/mp4")})
    assert upload.status_code == 201, upload.text
    asset_id = upload.json()["id"]
    created = client.post(root + "/documents", headers=headers, json={
        "workspaceId": workspace, "title": "Source footage", "contentType": "video",
        "brief": {"objective": "Inspect and mount a source clip", "audience": "QA"},
        "composition": {"pages": [{"id": "main", "width": 360, "height": 640, "durationMs": 2000,
                                  "layers": [], "background": "#101010"}]},
        "assets": [{"id": asset_id, "version": "1", "mediaType": "video/mp4"}],
    })
    assert created.status_code == 201, created.text
    doc = created.json()
    with SessionLocal() as db:
        asset = db.get(LibraryAsset, asset_id)
        checksum = asset.checksum_sha256
        ingest = StudioMediaIngest(
            workspace_id=workspace, asset_id=asset_id, status="ready", requested_by=doc["actorId"],
            media_info={"checksumSha256": checksum, "durationMicroseconds": 2_000_000},
            idempotency_key="film-source-ingest",
        )
        db.add(ingest)
        db.flush()
        ingest_id = ingest.id
        db.commit()
    created_transcript = client.post(root + "/transcripts", headers={**headers, "Idempotency-Key": "film-transcript"}, json={
        "workspaceId": workspace, "mediaIngestId": ingest_id, "status": "ready", "segments": [{
            "id": "first", "startMicroseconds": 200_000, "endMicroseconds": 700_000, "text": "Órbita",
            "words": [{"id": "first-word", "startMicroseconds": 200_000, "endMicroseconds": 700_000, "text": "Órbita"}],
        }],
    })
    assert created_transcript.status_code == 201, created_transcript.text
    with SessionLocal() as db:
        assert read_transcript(db, workspace, {
            "assetId": asset_id, "checksumSha256": "b" * 64,
        }, 0, "segment")["status"] == "unavailable"
    base = root + "/documents/" + doc["documentId"] + "/craft"
    migrated = client.post(base + "/migrate", headers={**headers, "Idempotency-Key": "film-source-migrate"},
                           json={"engine": "filmcraft", "expectedRevision": doc["revision"]})
    assert migrated.status_code == 200, migrated.text

    connection = SimpleNamespace(id="filmcraft-offline-test", provider="anthropic", revision=1, config={
        "enabled": True, "protocol": "anthropic_messages", "billingMode": "local_free",
        "maxOutputTokens": 4000, "inputUsdPerMillion": 0, "outputUsdPerMillion": 0,
    })
    real_refresh = SessionLocal.class_.refresh
    monkeypatch.setattr(SessionLocal.class_, "refresh", lambda db, instance, *args, **kwargs:
                        real_refresh(db, instance, *args, **kwargs) if instance is not connection else None)
    monkeypatch.setattr(craft_agent, "reserve_request", lambda _db, job, *_args, **_kwargs:
                        setattr(job, "result_payload", {"llmReservationUsd": 0}))
    calls = iter([
        ("inspect_source_media", {"assetId": asset_id, "seconds": [0.2, 1.3]}),
        ("read_source_transcript", {"assetId": asset_id, "unit": "word"}),
        ("edit_project", {"commands": [
            {"id": "asset.import", "params": {"assetId": asset_id, "addToTimeline": True}},
            {"id": "captions.newTrack", "params": {"name": "Legendas"}},
            {"id": "captions.add", "params": {"text": "Órbita", "seconds": 0.2, "durationSeconds": 0.5}},
        ]}),
        ("finish_project", {"rationale": "Fonte conferida e montada."}),
    ])

    def turn(_model, _system, messages, tools, _tokens, _seconds):
        assert {"inspect_source_media", "read_source_transcript", "finish_project"} <= {
            tool["name"] for tool in tools
        }
        name, args = next(calls)
        if name == "read_source_transcript":
            content = messages[-1]["content"][0]["content"]
            assert json.loads(content[0]["text"])["hasAudio"] is True
            assert content[1]["type"] == "image"
        if name == "edit_project":
            assert json.loads(messages[-1]["content"][0]["content"])["items"] == [
                {"startSeconds": 0.2, "endSeconds": 0.7, "text": "Órbita"},
            ]
        if name == "finish_project":
            assert json.loads(messages[-1]["content"][0]["content"])["applied"] == 3
        return {"stop_reason": "tool_use", "usage": {}, "content": [
            {"type": "tool_use", "id": "film-" + name, "name": name, "input": args},
        ]}

    monkeypatch.setattr(llm_connections, "planner", lambda *_: (
        connection, SimpleNamespace(craft_turn=turn), "test-opus", "offline",
    ))
    result = client.post(base + "/ai-commands", headers={**headers, "Idempotency-Key": "film-source-edit"}, json={
        "expectedRevision": migrated.json()["revision"], "instruction": "Confira a fonte e exporte.",
        "connectionId": connection.id,
    })
    assert result.status_code == 200, result.text
    assert result.json()["exportStatus"] == "succeeded", result.text


def test_effectcraft_checkpoint_survives_two_interruptions_and_exports_after_resume(client, monkeypatch):
    token, workspace = register(client, "effectcraft-recovery@example.com")
    headers = {"Authorization": "Bearer " + token}
    root = "/api/v1/studios/v1"
    created = client.post(root + "/documents", headers=headers, json={
        "workspaceId": workspace, "title": "Motion recovery proof", "contentType": "video",
        "brief": {"objective": "Exercise durable editing and export", "audience": "QA"},
        "composition": {"pages": [{"id": "main", "width": 320, "height": 320, "durationMs": 2000,
                                  "layers": [], "background": "#0e1528"}],
                        "mediaTimeline": {"frameRate": {"numerator": 12, "denominator": 1},
                                          "durationFrames": 24, "tracks": []}},
    })
    assert created.status_code == 201, created.text
    doc = created.json()
    base = root + "/documents/" + doc["documentId"] + "/craft"
    migrated = client.post(base + "/migrate", headers={**headers, "Idempotency-Key": "craft-proof-migrate"}, json={
        "engine": "effectcraft", "expectedRevision": doc["revision"],
    })
    assert migrated.status_code == 200, migrated.text
    revision = migrated.json()["revision"]
    connection = SimpleNamespace(id="effectcraft-offline-test", provider="anthropic", revision=1, config={
        "enabled": True, "protocol": "anthropic_messages", "billingMode": "local_free",
        "maxOutputTokens": 4000, "inputUsdPerMillion": 0, "outputUsdPerMillion": 0,
    })
    real_refresh = SessionLocal.class_.refresh
    monkeypatch.setattr(SessionLocal.class_, "refresh", lambda db, instance, *args, **kwargs:
                        real_refresh(db, instance, *args, **kwargs) if instance is not connection else None)
    monkeypatch.setattr(craft_agent, "reserve_request", lambda _db, job, *_args, **_kwargs:
                        setattr(job, "result_payload", {"llmReservationUsd": 0}))
    calls = []

    def edit_script(code):
        return ("edit_project", {"commands": [{"id": "script.run", "params": {"code": code}}]})

    def turn(_model, _system, messages, tools, _tokens, _seconds):
        calls.append(messages)
        number = len(calls)
        assert "finish_project" in {tool["name"] for tool in tools}
        if number in {2, 3}:
            raise ValueError("llm_provider_incomplete_response")
        if number == 4:
            assert "last saved native draft" in messages[0]["content"]
        if number == 5:
            assert "CHECKPOINT" in messages[-1]["content"][0]["content"]
        if number == 7:
            assert messages[-1]["content"][0]["content"][0]["type"] == "image"
        name, args = {
            1: edit_script('var c=app.project.activeItem; c.layers.addText("CHECKPOINT");'),
            4: ("inspect_project", {}),
            5: ("run_motion_script", {"code": 'var l=app.project.activeItem.layer(1);'
                           'var p=l.property("ADBE Transform Group").property("ADBE Position");'
                           'p.setValueAtTime(0,[42,110,0]);p.setValueAtTime(1.5,[155,192,0]);'}),
            6: ("preview_sequence", {"seconds": [0, 0.85, 1.5]}),
            7: ("finish_project", {"rationale": "Reabri e conferi a animação."}),
        }[number]
        return {"stop_reason": "tool_use", "model": "test-opus", "usage": {}, "content": [
            {"type": "tool_use", "id": f"tool-{number}", "name": name, "input": args},
        ]}

    monkeypatch.setattr(llm_connections, "planner", lambda *_: (
        connection, SimpleNamespace(craft_turn=turn), "test-opus", "offline",
    ))
    key = "native-proof-edit-1"
    payload = {"expectedRevision": revision, "instruction": "Anime e exporte", "connectionId": connection.id}
    request_headers = {**headers, "Idempotency-Key": key}
    failure = client.post(base + "/ai-commands", headers=request_headers, json=payload)
    assert failure.status_code == 422, failure.text
    status = client.get(base + f"/ai-requests/{key}", headers=headers).json()
    assert status["canResume"] and status["draftBatches"] == 1 and status["receipt"] is None
    assert client.get(root + "/documents/" + doc["documentId"], headers=headers).json()["revision"] == revision
    archive = client.get(base + f"/ai-requests/{key}/draft", headers=headers)
    assert archive.status_code == 200
    with ZipFile(BytesIO(archive.content)) as bundle:
        assert bundle.read("rascunho.ecproj")
        assert json.loads(bundle.read("manifest.json"))["sourceRevision"] == revision

    finished = client.post(base + "/ai-commands", headers=request_headers, json=payload)
    assert finished.status_code == 200, finished.text
    result = finished.json()
    assert result["document"]["revision"] == revision + 1
    assert result["exportStatus"] == "succeeded"
    job = client.get(root + "/jobs/" + result["exportJobId"], headers=headers).json()
    assert job["result"]["artifact"]["mediaType"] == "video/mp4"
    media = client.get(job["result"]["artifact"]["downloadUrl"], headers=headers)
    assert media.status_code == 200 and b"ftyp" in media.content[:64]
    repeated = client.post(base + "/ai-commands", headers=request_headers, json=payload).json()
    assert repeated["receiptId"] == result["receiptId"] and repeated["exportJobId"] == result["exportJobId"]
    assert len(calls) == 7
