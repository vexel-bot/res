"""Real CPU media acceptance. Never substitutes a mock for FFmpeg or ffprobe."""
import json
import subprocess
from array import array

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios import timeline_ffmpeg as ff
from app.routers import studio_video
from app.services.studios.jobs import execute_job_once
from app.studio_app import app
from test_clicko_studio_bridge import KEY, headers
from test_video_frontend_contract import draft


def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path / "objects"))
    monkeypatch.setattr(studio_video, "dispatch", lambda job: None)
    return headers(module="create-video", client="timeline-real")


def create(client, auth):
    ws = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
    payload = draft(ws)
    payload["composition"]["pages"][0].update(width=320, height=320, durationMs=2000)
    payload["composition"]["mediaTimeline"].update(durationFrames=48, frameRate={"numerator": 24, "denominator": 1})
    response = client.post("/api/v1/studios/v1/documents", headers=auth, json=payload)
    assert response.status_code == 201, response.text
    return ws, response.json()


def test_timeline_revision_isolation_and_unsupported_effects(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, doc = create(client, auth)
        path = f"/api/v1/studios/v1/video/documents/{doc['documentId']}/timeline"
        body = {"expectedRevision": 1, "timeline": doc["composition"]["mediaTimeline"]}
        keyed = {**auth, "Idempotency-Key": "save-timeline-001"}
        saved = client.put(path, headers=keyed, json=body)
        assert saved.status_code == 200, saved.text
        assert saved.json()["revision"] == 2
        assert client.put(path, headers=keyed, json=body).json()["revision"] == 2
        assert client.put(path, headers={**auth, "Idempotency-Key": "save-timeline-002"}, json=body).status_code == 409
        assert client.put(path, headers={**headers(module="create-image", client="timeline-real"), "Idempotency-Key": "save-timeline-003"}, json=body).status_code == 403
        assert client.put(path, headers={**headers(module="create-video", client="foreign"), "Idempotency-Key": "save-timeline-004"}, json=body).status_code == 404
        malformed = json.loads(json.dumps(body))
        malformed["expectedRevision"] = 2
        malformed["timeline"]["tracks"] = [{"id": "bad", "kind": "video", "name": "Bad", "clips": [{"id": "clip", "assetId": "unknown", "timeline": {"startFrame": 0, "durationFrames": 24}, "transform": {"filter": "movie=/private"}}]}]
        assert client.put(path, headers={**auth, "Idempotency-Key": "save-timeline-005"}, json=malformed).status_code == 422


def test_concurrent_studio_bootstrap_reuses_the_same_identity(monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import select, func
    from app.models import User, Workspace, Membership
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(pool.map(lambda _: client.get("/api/v1/studios/v1/bridge/session", headers=auth), range(12)))
        assert all(response.status_code == 200 for response in responses)
        assert len({response.json()["workspace"]["id"] for response in responses}) == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(Workspace)) == 1
        assert db.scalar(select(func.count()).select_from(Membership)) == 1


@pytest.mark.skipif(not ff.capability()["available"], reason="Actual FFmpeg readiness is required")
def test_cancel_and_interrupted_restart_keep_the_same_job_retryable(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, doc = create(client, auth)
        timeline = doc["composition"]["mediaTimeline"]
        timeline["tracks"] = [{"id": "title", "kind": "caption", "name": "Título", "cues": [{"id": "cue", "text": "Clicko", "timeline": {"startFrame": 0, "durationFrames": 48}, "style": {"fontFamily": "system", "fontSize": 26}}]}]
        path = f"/api/v1/studios/v1/video/documents/{doc['documentId']}"
        assert client.put(path+"/timeline", headers={**auth,"Idempotency-Key":"cancel-save-001"}, json={"expectedRevision":1,"timeline":timeline}).status_code == 200
        queued = client.post(path+"/render-jobs", headers={**auth,"Idempotency-Key":"cancel-render-001"}, json={"expectedRevision":2}).json()
        cancelled = client.post(f"/api/v1/studios/v1/jobs/{queued['id']}/cancel", headers=auth, json={"reason":"Cancelar teste"})
        assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
        assert client.get("/api/v1/studios/v1/video/library", headers=auth).json() == []
        queued = client.post(path+"/render-jobs", headers={**auth,"Idempotency-Key":"restart-render-001"}, json={"expectedRevision":2}).json()
        with SessionLocal() as db:
            row = db.get(StudioGenerationJob,queued["id"])
            row.status = "running"
            row.worker_execution_context = {
                "mode": "embedded", "attested": False, "jobType": "timeline_render",
                "capability": "media_cpu", "queueName": row.queue_name,
                "verifiedAt": "2026-10-17T00:00:00Z", "processId": 2_000_000_000,
            }
            db.commit()
        monkeypatch.setattr(get_settings(), "celery_task_always_eager", True)
        studio_video.recover_interrupted_local_jobs()
        recovered = client.get(f"/api/v1/studios/v1/jobs/{queued['id']}", headers=auth).json()
        assert recovered["status"] == "failed" and recovered["errorCode"] == "timeline_interrupted_restart"
        retried = client.post(f"/api/v1/studios/v1/jobs/{queued['id']}/retry", headers=auth)
        assert retried.status_code == 202 and retried.json()["id"] == queued["id"]


def command(args):
    process = subprocess.run([ff.tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *args], capture_output=True, timeout=90)
    assert process.returncode == 0, process.stderr.decode(errors="replace")


def pixels(path, time):
    process = subprocess.run([ff.tool("ffmpeg"), "-v", "error", "-ss", str(time), "-i", str(path), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], capture_output=True, timeout=30)
    assert process.returncode == 0
    return Image.frombytes("RGB", (320, 320), process.stdout)


@pytest.mark.skipif(not ff.capability()["available"], reason="Actual FFmpeg/ffprobe and H.264/AAC are required")
def test_real_upload_trim_title_audio_render_download_library_restart_and_replay(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    source = tmp_path / "source.mp4"
    audio = tmp_path / "music.wav"
    overlay = tmp_path / "overlay.png"
    Image.new("RGB", (64,64), "lime").save(overlay)
    encoder = ff.capability()["encoder"]
    command(["-f", "lavfi", "-i", "color=c=red:s=320x320:r=24:d=2", "-f", "lavfi", "-i", "color=c=blue:s=320x320:r=24:d=2", "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-c:v", encoder, "-b:v", "500k", str(source)])
    command(["-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:a", "pcm_s16le", str(audio)])
    with TestClient(app) as client:
        workspace, doc = create(client, auth)
        def upload(path, mime):
            response = client.post("/api/v1/studios/v1/craft/assets", params={"workspace_id": workspace, "title": path.name, "filename": path.name, "media_type": mime}, headers={**auth, "Content-Type": mime}, content=path.read_bytes())
            assert response.status_code == 201, response.text
            return response.json()
        video = upload(source, "video/mp4")
        music = upload(audio, "audio/wav")
        graphic = upload(overlay, "image/png")
        info = client.get(f"/api/v1/studios/v1/video/assets/{video['id']}/probe", params={"workspace_id": workspace}, headers=auth)
        assert info.status_code == 200, info.text
        assert info.json()["durationSeconds"] == pytest.approx(4, abs=.1)
        timeline = doc["composition"]["mediaTimeline"]
        def clip(identifier, asset_id, start, source_start):
            return {"id": identifier, "assetId": asset_id, "timeline": {"startFrame": start, "durationFrames": 24}, "source": {"startMicroseconds": source_start, "durationMicroseconds": 1_000_000}, "transform": {}, "keyframes": []}
        timeline["tracks"] = [
            {"id": "v", "kind": "video", "name": "Vídeo", "clips": [clip("red-cut", video["id"], 0, 500_000), clip("blue-cut", video["id"], 24, 2_000_000)]},
            {"id": "graphic", "kind": "overlay", "name": "Gráfico", "clips": [{"id": "graphic-clip", "assetId": graphic["id"], "timeline": {"startFrame": 0, "durationFrames": 48}, "transform": {"scale": .25, "rotation": 15}, "keyframes": [{"property": "opacity", "frame": 0, "value": 0}, {"property": "opacity", "frame": 12, "value": 1}, {"property": "scale", "frame": 0, "value": .2}, {"property": "scale", "frame": 48, "value": .3}]}]},
            {"id": "a", "kind": "audio", "name": "Áudio", "clips": [{"id": "music", "assetId": music["id"], "timeline": {"startFrame": 0, "durationFrames": 48}, "gainDb": -6, "fadeInFrames": 6, "fadeOutFrames": 6}]},
            {"id": "t", "kind": "caption", "name": "Título", "cues": [{"id": "title", "text": "Clicko Studios", "timeline": {"startFrame": 0, "durationFrames": 48}, "style": {"fontSize": 26, "fontFamily": "system", "outlineWidth": 1}, "motion": {"fadeInFrames": 5, "fadeOutFrames": 5}, "keyframes": [{"property": "y", "frame": 0, "value": 25}, {"property": "y", "frame": 10, "value": 0}]}]},
        ]
        path = f"/api/v1/studios/v1/video/documents/{doc['documentId']}"
        saved = client.put(path+"/timeline", headers={**auth, "Idempotency-Key": "real-edit-001"}, json={"expectedRevision": 1, "timeline": timeline})
        assert saved.status_code == 200, saved.text
        assert saved.json()["composition"]["mediaTimeline"]["tracks"][3]["cues"][0]["keyframes"][0]["value"] == 25
        request_headers = {**auth, "Idempotency-Key": "real-render-001"}
        job = client.post(path+"/render-jobs", headers=request_headers, json={"expectedRevision": 2})
        assert job.status_code == 202, job.text
        assert client.post(path+"/render-jobs", headers=request_headers, json={"expectedRevision": 2}).json()["id"] == job.json()["id"]
        with SessionLocal() as db:
            row = db.get(StudioGenerationJob, job.json()["id"])
            assert execute_job_once(db, row) == "succeeded", row.error_message
            result = row.result_payload
        delivery = f"/api/v1/studios/v1/video/library/{result['assetId']}/content"
        response = client.get(delivery, headers=auth)
        assert response.status_code == 200
        assert response.headers["content-type"] == "video/mp4"
        output = tmp_path / "edited.mp4"
        output.write_bytes(response.content)
        metadata = ff.probe(output)
        assert float(metadata["format"]["duration"]) == pytest.approx(2, abs=.1)
        assert any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in metadata["streams"])
        first, second = pixels(output, .6), pixels(output, 1.5)
        assert first.getpixel((10, 10))[0] > 180
        assert second.getpixel((10, 10))[2] > 180
        assert first.getpixel((160, 160))[1] > 180, "Actual overlay/keyframe pixels must be green at the midpoint"
        assert sum(1 for r,g,b in first.crop((10, 200, 310, 310)).getdata() if min(r,g,b)>180) > 100, "The title must exist in actual output pixels"
        decoded = subprocess.run([ff.tool("ffmpeg"), "-v", "error", "-i", str(output), "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "pipe:1"], capture_output=True, timeout=30)
        samples = array("f", decoded.stdout)
        rms = lambda values: (sum(float(v)**2 for v in values)/len(values))**.5
        assert rms(samples[24_000:30_000]) > .01, "The result must contain actual audible samples"
        assert rms(samples[:2400]) < rms(samples[24_000:30_000]) * .5, "The persisted audio fade must affect the waveform"
        assert client.get(delivery, headers=headers(module="create-video", client="foreign")).status_code == 404
        ranged = client.get(delivery, headers={**auth, "Range": "bytes=0-99"})
        assert ranged.status_code == 206 and len(ranged.content) == 100
        assert client.get("/api/v1/studios/v1/video/library", headers=auth).json()[0]["id"] == result["assetId"]
        # An interrupted acknowledgement after durable delivery must not render a second asset.
        with SessionLocal() as db:
            row = db.get(StudioGenerationJob, job.json()["id"])
            row.status, row.result_payload = "retrying", None
            db.commit()
            monkeypatch.setattr(ff, "render", lambda *args: (_ for _ in ()).throw(AssertionError("A delivered job must not render again")))
            assert execute_job_once(db, row) == "succeeded"
            assert row.result_payload["assetId"] == result["assetId"]
    # New API/client and DB sessions must recover the same assets, job and project.
    with TestClient(app) as reopened:
        assert reopened.get("/api/v1/studios/v1/video/library", headers=auth).json()[0]["id"] == result["assetId"]
        assert reopened.get(f"/api/v1/studios/v1/jobs/{job.json()['id']}", headers=auth).json()["status"] == "succeeded"
        assert reopened.post(path+"/render-jobs", headers=request_headers, json={"expectedRevision": 2}).json()["id"] == job.json()["id"]
