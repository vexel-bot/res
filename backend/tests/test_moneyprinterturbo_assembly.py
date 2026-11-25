"""Integration test with the pinned MoneyPrinterTurbo runtime and real media."""

import subprocess
from array import array

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios import moneyprinterturbo as mpt
from app.providers.studios import timeline_ffmpeg as ff
from app.services.studios.jobs import execute_job_once
from app.studio_app import app
from test_clicko_studio_bridge import headers
from test_video_timeline_real import command, create, setup


def test_directed_assembly_delivery_and_archive(monkeypatch, tmp_path):
    try:
        mpt.runtime()
    except ValueError:
        pytest.skip("Provision the pinned MoneyPrinterTurbo runtime first")
    auth = setup(monkeypatch, tmp_path)
    red, blue, audio = (tmp_path / name for name in ("red.mp4", "blue.mp4", "mix.wav"))
    for path, color in [(red, "red"), (blue, "blue")]:
        command(["-f", "lavfi", "-i", f"color={color}:s=320x320:r=30:d=2",
                 "-c:v", "libx264", "-threads", "2", str(path)])
    command(["-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=1.4", "-af", "adelay=1100", str(audio)])
    with TestClient(app) as client:
        workspace, doc = create(client, auth)
        base = f"/api/v1/studios/v1/video/documents/{doc['documentId']}"

        def upload(path, mime):
            with path.open("rb") as handle:
                response = client.post(base + "/assembly-materials", headers=auth,
                                       data={"title": path.name},
                                       files={"file": (path.name, handle, mime)})
            assert response.status_code == 201, response.text
            return response.json()["id"]

        red_id = upload(red, "video/mp4")
        blue_id = upload(blue, "video/mp4")
        audio_id = upload(audio, "audio/wav")
        request = {"expectedRevision": doc["revision"], "assembly": {"aspect": "1:1", "clips": [
            {"assetId": red_id, "startFrame": 13, "durationFrames": 33},
            {"assetId": blue_id, "startFrame": 8, "durationFrames": 42},
        ], "audioAssetId": audio_id}}
        keyed = {**auth, "Idempotency-Key": "assembly-acceptance-01"}
        first = client.post(base + "/assemblies", json=request, headers=keyed)
        assert first.status_code == 202, first.text
        job_id = first.json()["id"]
        assert client.post(base + "/assemblies", json=request, headers=keyed).json()["id"] == job_id
        request["assembly"]["clips"].reverse()
        assert client.post(base + "/assemblies", json=request, headers=keyed).status_code == 409
        with SessionLocal() as db:
            row = db.get(StudioGenerationJob, job_id)
            assert execute_job_once(db, row) == "succeeded", (row.error_code, row.error_message)
            asset_id = row.result_payload["assetId"]
        archive = f"/api/v1/studios/v1/documents/{doc['documentId']}/files"
        listing = client.get(archive, headers=auth)
        assert listing.status_code == 200
        assert {item["assetId"] for item in listing.json() if item["available"]} == {asset_id, audio_id, red_id, blue_id}
        foreign = headers(module="create-video", client="foreign")
        assert client.get(archive, headers=foreign).status_code == 404
        assert client.get(f"/api/v1/assets/{red_id}/content", headers=auth).content == red.read_bytes()
        response = client.get(f"/api/v1/assets/{asset_id}/content", headers=auth)
        assert response.status_code == 200
        result = tmp_path / "assembly.mp4"
        result.write_bytes(response.content)
    info = ff.probe(result)
    assert float(info["format"]["duration"]) == pytest.approx(2.5, abs=1/30)
    assert any(stream["codec_type"] == "audio" for stream in info["streams"])
    for frame, color in [(32, 0), (33, 2)]:
        pixel = subprocess.check_output([
            ff.tool("ffmpeg"), "-v", "error", "-i", str(result), "-vf",
            f"select=eq(n\\,{frame}),crop=2:2,format=rgb24", "-frames:v", "1", "-f", "rawvideo", "pipe:1",
        ], timeout=30)
        assert pixel[color] > 200
    samples = array("f", subprocess.check_output([
        ff.tool("ffmpeg"), "-v", "error", "-i", str(result), "-vn", "-ac", "1", "-ar", "48000",
        "-f", "f32le", "pipe:1",
    ], timeout=30))
    assert max(abs(sample) for sample in samples[48_000:50_400]) < .005
    assert max(abs(sample) for sample in samples[55_200:57_600]) > .03
