import hashlib
import math
import struct
import subprocess
import wave

import pytest
from conftest import register
from media_fixtures import create_source, ugc_fixture

from app.domain.studios.contracts import CreativeDocumentV1


def make_sound(path, frequency=880):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48000)
        output.writeframes(b"".join(struct.pack("<h", round(8000 * math.sin(2 * math.pi * frequency * i / 48000)))
                                  for i in range(96000)))


def sound_document(paths):
    document, request = ugc_fixture()
    raw = document.model_dump(by_alias=True, mode="json")
    raw["composition"]["mediaTimeline"]["tracks"][1]["muted"] = True
    for index, path in enumerate(paths):
        asset_id = f"sound-{index}"
        raw["assets"].append({
            "id": asset_id, "version": 1, "mediaType": "audio/wav", "origin": "workspace",
            "rightsStatus": "unknown", "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
            "provenance": {"purpose": "natural-sound-candidate", "source": "user-upload"},
        })
        raw["composition"]["mediaTimeline"]["tracks"].append({
            "id": f"audio-natural-{index}", "kind": "audio", "name": "Technical sound fixture",
            "clips": [{"id": f"sound-clip-{index}", "assetId": asset_id,
                       "timeline": {"startFrame": 9 + index * 18, "durationFrames": 9},
                       "source": {"startMicroseconds": 200_000, "durationMicroseconds": 300_000},
                       "gainDb": -6, "fadeInFrames": 1, "fadeOutFrames": 1}],
        })
    request.asset_ids = [asset["id"] for asset in raw["assets"]]
    return CreativeDocumentV1.model_validate(raw), request








def test_audio_ingest_reuses_worker_and_tenant_boundary(client, tmp_path, monkeypatch):
    from app import tasks
    from app.routers import assets as assets_router

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path / "storage"))
    queued = []
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued.append(job_id))
    token, workspace = register(client, "sound-ingest@example.com")
    other, _ = register(client, "sound-ingest-other@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    sound = tmp_path / "sound.wav"
    make_sound(sound)
    upload = client.post("/api/v1/assets/upload", headers=headers,
                         data={"workspace_id": workspace, "title": "Technical sound fixture"},
                         files={"file": ("sound.wav", sound.read_bytes(), "audio/wav")})
    assert upload.status_code == 201, upload.text
    asset_id = upload.json()["id"]
    ingest_headers = {**headers, "Idempotency-Key": "natural-sound-001"}
    payload = {"workspaceId": workspace, "assetId": asset_id}
    response = client.post("/api/v1/studios/v1/media-ingests", headers=ingest_headers, json=payload)
    assert response.status_code == 202, response.text
    ingest = response.json()
    assert ingest["status"] == "pending"
    replay = client.post("/api/v1/studios/v1/media-ingests", headers=ingest_headers, json=payload)
    assert replay.json()["id"] == ingest["id"]
    assert len(queued) == 1
    assert tasks.execute_studio_generation.run(ingest["generationJobId"])["status"] == "succeeded"
    ready = client.get(f"/api/v1/studios/v1/media-ingests/{ingest['id']}", headers=headers).json()
    assert ready["status"] == "ready"
    assert ready["mediaInfo"]["videoStreams"] == []
    assert len(ready["mediaInfo"]["audioStreams"]) == 1
    assert ready["mediaInfo"]["checksumSha256"] == hashlib.sha256(sound.read_bytes()).hexdigest()
    foreign = {"Authorization": f"Bearer {other}", "Idempotency-Key": "foreign-sound"}
    assert client.post("/api/v1/studios/v1/media-ingests", headers=foreign, json=payload).status_code == 404
    assert client.get(f"/api/v1/assets/{asset_id}/content", headers=foreign).status_code == 404
