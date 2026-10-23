"""Real local acceptance and accounting regressions. No inference or native-engine doubles.

Set CLICKO_VALIDATION_ARTIFACT_DIR to retain the actual MP4, reference and evidence.
The API/database remain isolated by conftest. Manual planning is not AI generation.
"""

import hashlib
import io
import json
import os
import subprocess
from array import array
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from test_clicko_studio_bridge import KEY, headers
from test_video_frontend_contract import draft
from test_video_timeline_real import command

from app.config import get_settings
from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios import timeline_ffmpeg as ff
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.routers import studio_video
from app.services.studios.gemini_editing import measured_request_cost
from app.services.studios.jobs import execute_job_once
from app.studio_app import app


def offline(monkeypatch, tmp_path):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_path", str(tmp_path / "objects"))
    monkeypatch.setattr(settings, "gemini_outbound_enabled", False)
    monkeypatch.setattr(settings, "studio_gemini_enabled", False)
    monkeypatch.setattr(settings, "studio_runway_enabled", False)
    monkeypatch.setattr(studio_video, "dispatch", lambda job: None)


def upload(client, auth, workspace, path, mime):
    response = client.post(
        "/api/v1/studios/v1/craft/assets",
        params={"workspace_id": workspace, "title": path.name, "filename": path.name, "media_type": mime},
        headers={**auth, "Content-Type": mime},
        content=path.read_bytes(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def retain(path, filename):
    configured = os.environ.get("CLICKO_VALIDATION_ARTIFACT_DIR")
    if configured:
        import shutil

        directory = Path(configured).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, directory / filename)


@pytest.mark.parametrize("normalized", [False, True])
def test_gemini_thinking_is_included_once_in_tariff_estimate(normalized):
    usage = {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 80}
    if normalized:
        config = {"protocol": "gemini_generate"}
        usage = UniversalLLMPlanner.__new__(UniversalLLMPlanner)
        usage.config = config
        usage = usage.normalize(
            {
                "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}],
                "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 80},
            }
        )["usage"]
        assert usage["completion_tokens"] == 100
    job = SimpleNamespace(request_payload={"pricing": {"inputUsdPerMillion": 1, "outputUsdPerMillion": 4}})
    assert measured_request_cost(job, usage) == pytest.approx(0.0005)


def test_reference_image_import_storage_download_and_explicit_native_block(monkeypatch, tmp_path):
    offline(monkeypatch, tmp_path)
    auth = headers(module="create-image", client="final-real-image")
    reference = tmp_path / "reference-4x5.png"
    image = Image.new("RGB", (960, 1200), "#101014")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((160, 180, 800, 1020), radius=64, fill="#FF7F50")
    draw.ellipse((290, 410, 670, 790), fill="#6EB8F5")
    image.save(reference)
    original = reference.read_bytes()
    with TestClient(app) as client:
        workspace = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
        payload = draft(workspace)
        payload.update(title="QA imagem local 4:5", contentType="visual")
        payload["composition"].pop("mediaTimeline")
        payload["composition"]["narrative"] = {"imageStudio": {"aspect": "4:5"}}
        payload["composition"]["pages"][0].update(width=960, height=1200)
        doc = client.post("/api/v1/studios/v1/documents", headers=auth, json=payload)
        assert doc.status_code == 201, doc.text
        asset = upload(client, auth, workspace, reference, "image/png")
        response = client.get(f"/api/v1/assets/{asset['id']}/content", headers=auth)
        assert response.status_code == 200 and response.content == original
        assert Image.open(io.BytesIO(response.content)).size == (960, 1200)
        assert hashlib.sha256(response.content).hexdigest() == asset["checksumSha256"]
        assert (
            client.get(f"/api/v1/assets/{asset['id']}/content", headers=headers(client="foreign-image")).status_code
            == 404
        )
        attached = client.post(
            f"/api/v1/studios/v1/documents/{doc.json()['documentId']}/editing-resources",
            headers=auth,
            json={"expectedDocumentRevision": 1, "assetId": asset["id"]},
        )
        assert attached.status_code == 422
        assert attached.json()["detail"]["code"] == "resource_usage_evidence_required"
        licensed = client.post(
            "/api/v1/studios/v1/editing/resources/upload",
            headers=auth,
            data={
                "workspace_id": workspace,
                "title": "Referência própria 4:5",
                "metadata": json.dumps({"kind": "image", "usageEvidence": "Fixture procedural própria de QA"}),
            },
            files={"file": (reference.name, original, "image/png")},
        )
        assert licensed.status_code == 200, licensed.text
        asset = licensed.json()
        attached = client.post(
            f"/api/v1/studios/v1/documents/{doc.json()['documentId']}/editing-resources",
            headers=auth,
            json={"expectedDocumentRevision": 1, "assetId": asset["id"]},
        )
        assert attached.status_code == 200, attached.text
        assert asset["id"] in {item["id"] for item in attached.json()["assets"]}
        # A missing real native project/engine must not produce a fake composition.
        blocked = client.post(
            f"/api/v1/studios/v1/documents/{doc.json()['documentId']}/craft/preview",
            headers=auth,
            json={"frame": 0},
        )
        assert blocked.status_code in {409, 422, 503}, blocked.text
        assert client.get(f"/api/v1/assets/{asset['id']}/content", headers=auth).content == original
    retain(reference, "reference-4x5.png")


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.skipif(not ff.capability()["available"], reason="Actual FFmpeg and H.264/AAC required")
def test_frontend_original_audio_flag_renders_and_really_mutes(monkeypatch, tmp_path, enabled):
    offline(monkeypatch, tmp_path)
    auth = headers(module="create-video", client="original-audio-contract")
    source = tmp_path / "source-with-audio.mp4"
    command(
        [
            "-f",
            "lavfi",
            "-i",
            "color=c=0x303030:s=320x320:r=30:d=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2:sample_rate=48000",
            "-c:v",
            ff.capability()["encoder"],
            "-b:v",
            "250k",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ]
    )
    with TestClient(app) as client:
        workspace = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
        asset = upload(client, auth, workspace, source, "video/mp4")
        payload = draft(workspace)
        payload["composition"]["pages"][0].update(width=320, height=320, durationMs=2000)
        timeline = payload["composition"]["mediaTimeline"]
        timeline.update(
            durationFrames=60,
            tracks=[
                {
                    "id": "video",
                    "kind": "video",
                    "name": "Formato real do frontend",
                    "clips": [
                        {
                            "id": "clip",
                            "assetId": asset["id"],
                            "timeline": {"startFrame": 0, "durationFrames": 60},
                            "source": {"startMicroseconds": 0, "durationMicroseconds": 2_000_000},
                            "transform": {"originalAudioEnabled": enabled},
                        }
                    ],
                },
            ],
        )
        payload["assets"] = [
            {
                "id": asset["id"],
                "mediaType": "video/mp4",
                "checksum": asset["checksumSha256"],
                "rightsStatus": "verified",
            }
        ]
        doc = client.post("/api/v1/studios/v1/documents", headers=auth, json=payload)
        assert doc.status_code == 201, doc.text
        response = client.post(
            f"/api/v1/studios/v1/video/documents/{doc.json()['documentId']}/render-jobs",
            headers={**auth, "Idempotency-Key": "original-audio-render-001"},
            json={"expectedRevision": 1},
        )
        assert response.status_code == 202, response.text
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, response.json()["id"])
            assert execute_job_once(db, job) == "succeeded", job.error_message
            result = dict(job.result_payload)
        output = tmp_path / "result.mp4"
        output.write_bytes(client.get(f"/api/v1/assets/{result['assetId']}/content", headers=auth).content)
        decoded = subprocess.run(
            [
                ff.tool("ffmpeg"),
                "-v",
                "error",
                "-i",
                str(output),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-f",
                "f32le",
                "pipe:1",
            ],
            capture_output=True,
            timeout=30,
        )
        assert decoded.returncode == 0
        samples = array("f", decoded.stdout)[24000:72000]
        assert samples
        rms = (sum(float(value) ** 2 for value in samples) / len(samples)) ** 0.5
        assert rms > 0.04 if enabled else rms < 0.00001


@pytest.mark.skipif(not ff.capability()["available"], reason="Actual FFmpeg and H.264/AAC required")
def test_real_eighteen_second_advertising_reference(monkeypatch, tmp_path):
    offline(monkeypatch, tmp_path)
    auth = headers(module="create-video", client="final-advertising")
    source, music, graphic = (tmp_path / name for name in ("source.mp4", "music.wav", "graphic.png"))
    encoder = ff.capability()["encoder"]
    command(
        [
            "-f",
            "lavfi",
            "-i",
            "color=c=0x241A16:s=1280x720:r=30:d=8",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x10212B:s=1280x720:r=30:d=8",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x161616:s=1280x720:r=30:d=8",
            "-filter_complex",
            "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
            "-map",
            "[v]",
            "-c:v",
            encoder,
            "-b:v",
            "1800k",
            str(source),
        ]
    )
    command(
        [
            "-f",
            "lavfi",
            "-i",
            "aevalsrc=0.05*(sin(2*PI*220*t)+0.5*sin(2*PI*330*t)+0.25*sin(2*PI*440*t)):d=18:s=48000",
            "-c:a",
            "pcm_s16le",
            str(music),
        ]
    )
    picture = Image.new("RGBA", (640, 360), (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    draw.rounded_rectangle((40, 40, 600, 320), radius=35, fill="#FF7F50")
    draw.ellipse((225, 85, 415, 275), fill="#6EB8F5")
    picture.save(graphic)
    with TestClient(app) as client:
        workspace = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
        payload = draft(workspace)
        payload["title"] = "QA · Publicidade local 18s · sem geração IA"
        payload["brief"].update(objective="Apresentar o estúdio e convidar à criação", audience="Criadores")
        payload["composition"]["pages"][0].update(width=1280, height=720, durationMs=18000)
        payload["composition"]["mediaTimeline"]["durationFrames"] = 540
        response = client.post("/api/v1/studios/v1/documents", headers=auth, json=payload)
        assert response.status_code == 201, response.text
        doc = response.json()
        video = upload(client, auth, workspace, source, "video/mp4")
        sound = upload(client, auth, workspace, music, "audio/wav")
        overlay = upload(client, auth, workspace, graphic, "image/png")
        timeline = doc["composition"]["mediaTimeline"]
        texts = [
            "Sua ideia merece ganhar forma.",
            "Imagem. Movimento. Criatividade.",
            "Crie seu próximo conteúdo com a Clicko.",
        ]
        timeline["tracks"] = [
            {
                "id": "video",
                "kind": "video",
                "name": "Cenas locais",
                "clips": [
                    {
                        "id": f"scene-{i}",
                        "assetId": video["id"],
                        "timeline": {"startFrame": i * 180, "durationFrames": 180},
                        "source": {"startMicroseconds": (i * 8 + 1) * 1_000_000, "durationMicroseconds": 6_000_000},
                        "transform": {"fadeInFrames": 12, "fadeOutFrames": 12},
                    }
                    for i in range(3)
                ],
            },
            {
                "id": "graphics",
                "kind": "overlay",
                "name": "Gráfico autorizado",
                "clips": [
                    {
                        "id": "card",
                        "assetId": overlay["id"],
                        "timeline": {"startFrame": 0, "durationFrames": 540},
                        "transform": {"y": -90, "scale": 0.75, "fadeInFrames": 18, "fadeOutFrames": 18},
                        "keyframes": [
                            {"property": "scale", "frame": 0, "value": 0.65},
                            {"property": "scale", "frame": 540, "value": 0.85},
                        ],
                    }
                ],
            },
            {
                "id": "audio",
                "kind": "audio",
                "name": "Trilha sintética própria",
                "clips": [
                    {
                        "id": "track",
                        "assetId": sound["id"],
                        "timeline": {"startFrame": 0, "durationFrames": 540},
                        "gainDb": -6,
                        "fadeInFrames": 30,
                        "fadeOutFrames": 45,
                    }
                ],
            },
            {
                "id": "titles",
                "kind": "caption",
                "name": "Roteiro manual",
                "cues": [
                    {
                        "id": f"title-{i}",
                        "text": text,
                        "timeline": {"startFrame": i * 180, "durationFrames": 180},
                        "style": {"fontFamily": "system", "fontSize": 42, "outlineWidth": 1},
                        "motion": {"fadeInFrames": 12, "fadeOutFrames": 12},
                        "keyframes": [
                            {"property": "y", "frame": 0, "value": 14},
                            {"property": "y", "frame": 18, "value": 0},
                        ],
                    }
                    for i, text in enumerate(texts)
                ],
            },
        ]
        path = f"/api/v1/studios/v1/video/documents/{doc['documentId']}"
        saved = client.put(
            path + "/timeline",
            headers={**auth, "Idempotency-Key": "final-ad-save-001"},
            json={"expectedRevision": 1, "timeline": timeline},
        )
        assert saved.status_code == 200, saved.text
        keyed = {**auth, "Idempotency-Key": "final-ad-render-001"}
        response = client.post(path + "/render-jobs", headers=keyed, json={"expectedRevision": 2})
        assert response.status_code == 202, response.text
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, response.json()["id"])
            assert execute_job_once(db, job) == "succeeded", job.error_message
            result = dict(job.result_payload)
        delivery = f"/api/v1/studios/v1/video/library/{result['assetId']}/content"
        response = client.get(delivery, headers=auth)
        assert response.status_code == 200
        output = tmp_path / "publicidade-local-18s.mp4"
        output.write_bytes(response.content)
        metadata = ff.probe(output)
        assert float(metadata["format"]["duration"]) == pytest.approx(18, abs=0.08)
        stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        assert (stream["width"], stream["height"], stream["codec_name"]) == (1280, 720, "h264")
        assert stream["avg_frame_rate"] == "30/1"
        assert any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in metadata["streams"])
        assert result["generatedVideoSeconds"] == 0 and result["outputVideoSeconds"] == pytest.approx(18)
        assert hashlib.sha256(response.content).hexdigest() == result["checksumSha256"]
        for index, seconds in enumerate((2, 8, 14)):
            frame = tmp_path / f"scene-{index + 1}.png"
            command(["-ss", str(seconds), "-i", str(output), "-frames:v", "1", str(frame)])
            with Image.open(frame) as image:
                assert image.getpixel((640, 240))[2] > 100, "The composited graphic must exist in decoded pixels"
                bright = sum(
                    1 for r, g, b in image.convert("RGB").crop((80, 520, 1200, 650)).getdata() if min(r, g, b) > 180
                )
                assert bright > 400, "Each scene must contain actual rendered text"
            retain(frame, frame.name)
        decoded = subprocess.run(
            [
                ff.tool("ffmpeg"),
                "-v",
                "error",
                "-i",
                str(output),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-f",
                "f32le",
                "pipe:1",
            ],
            capture_output=True,
            timeout=40,
        )
        assert decoded.returncode == 0
        samples = array("f", decoded.stdout)
        assert len(samples) >= 18 * 48000

        def rms(values):
            return (sum(float(v) ** 2 for v in values) / len(values)) ** 0.5

        assert rms(samples[96000:120000]) > 0.01
        assert rms(samples[:2400]) < rms(samples[96000:120000]) * 0.3
        assert client.get(delivery, headers={**auth, "Range": "bytes=0-99"}).status_code == 206
        assert client.get(delivery, headers=headers(module="create-video", client="foreign-ad")).status_code == 404
        assert client.post(path + "/render-jobs", headers=keyed, json={"expectedRevision": 2}).json()["id"] == job.id
        evidence = {
            "kind": "real-local-assembly-not-ai-generation",
            "brief": payload["brief"],
            "script": texts,
            "documentId": doc["documentId"],
            "render": result,
            "probe": metadata,
            "rights": "Procedural test fixtures authored locally; no client media or remote generation",
        }
        record = tmp_path / "evidence.json"
        record.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        retain(record, "evidence.json")
        retain(output, output.name)
        retain(graphic, graphic.name)
    with TestClient(app) as reopened:
        assert reopened.get(delivery, headers=auth).content == response.content
