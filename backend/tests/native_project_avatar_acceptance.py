"""Explicit real FilmCraft acceptance. FFmpeg supplies a test card and tones, never a person/model.

Run: PYTHONPATH=backend python -m pytest backend/tests/native_project_avatar_acceptance.py -o addopts='' -q
Requires the built native Craft runtime. The avatar adapter is an explicit media fixture;
project migration, placement, reopen, preview, export, storage and media decoding are real.
"""

import json
import math
import shutil
import struct
import subprocess
import wave
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageChops, ImageStat
from test_avatar_independent_cast import TransportAvatar
from test_project_avatar import BASE, prepare, submit

from app.database import SessionLocal
from app.domain.studios.contracts import AvatarVideoEncodeResultV1
from app.domain.studios.providers import AVATAR_VIDEO_PROVIDERS
from app.models import LibraryAsset, StudioGenerationJob, WorkspaceResource
from app.routers import studio_department
from app.services.object_storage import get_object_storage, sha256_file
from app.services.studios import craft
from app.services.studios.jobs import execute_job_once

OUTPUT = Path(__file__).resolve().parents[2] / ".codex-runtime/team-sync/native-avatar"


def ffmpeg(*args):
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *map(str, args)], capture_output=True, check=False, timeout=120
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")[-2000:]
    return result.stdout


def tone(path, seconds, frequency):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        out.writeframes(
            b"".join(
                struct.pack("<h", round(8000 * math.sin(2 * math.pi * frequency * i / 24000)))
                for i in range(round(seconds * 24000))
            )
        )


class MediaAvatar(TransportAvatar):
    def render(self, document, request, images, audio, destination, progress, is_cancelled):
        ffmpeg(
            "-f",
            "lavfi",
            "-i",
            f"color=c=red:s={request.width}x{request.height}:r={request.fps}",
            "-i",
            audio,
            "-vf",
            "drawbox=x=0:y=0:w=40:h=ih:color=lime:t=fill,drawbox=x=iw-40:y=0:w=40:h=ih:color=blue:t=fill",
            "-t",
            request.driving_audio_duration_ms / 1000,
            "-threads",
            1,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-y",
            destination,
        )
        return AvatarVideoEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=request.width,
            height=request.height,
            fps=request.fps,
            duration_ms=request.driving_audio_duration_ms,
            artifact_checksum_sha256=sha256_file(destination),
        )


def power(samples, frequency):
    scale = 2 * math.pi * frequency / 24000
    return math.hypot(
        sum(value * math.sin(scale * i) for i, value in enumerate(samples)),
        sum(value * math.cos(scale * i) for i, value in enumerate(samples)),
    ) / len(samples)


@pytest.mark.parametrize("layout", ["sequential", "picture_in_picture"])
def test_presenter_then_brand_clip_preserve_picture_sound_and_native_reopen(client, monkeypatch, tmp_path, layout):
    case = prepare(client, monkeypatch, tmp_path)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    speech = tmp_path / "selected-final.wav"
    tone(speech, 2.8, 440)
    # Replace only the silent fixture's audio and its immutable fixture lineage.
    with SessionLocal() as db:
        row = db.get(WorkspaceResource, case.project["id"])
        narration = db.get(StudioGenerationJob, row.payload["narration"]["jobId"])
        audio = db.get(LibraryAsset, narration.result_payload["assetId"])
        storage = get_object_storage(audio.storage_backend)
        stored = storage.put_file(speech, key=f"{row.workspace_id}/fixtures/final-speech.wav", media_type="audio/wav")
        audio.storage_key = stored.key
        audio.checksum_sha256 = stored.checksum_sha256
        narration.result_payload = {**narration.result_payload, "checksumSha256": stored.checksum_sha256}
        audio.object_metadata = {**audio.object_metadata, "speechSynthesisJobResult": narration.result_payload}
        db.commit()
    monkeypatch.setitem(AVATAR_VIDEO_PROVIDERS, MediaAvatar.name, MediaAvatar())
    generated = submit(client, case)
    assert generated.status_code == 202, generated.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, generated.json()["id"])
        assert execute_job_once(db, job) == "succeeded", job.error_message
        avatar_id = job.result_payload["assetId"]
    brand = tmp_path / "brand.mp4"
    brand_audio = tmp_path / "brand.wav"
    brand_duration = 4.0 if layout == "picture_in_picture" else 1.2
    tone(brand_audio, brand_duration, 880)
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=320x180:r=30",
        "-i",
        brand_audio,
        "-t",
        brand_duration,
        "-threads",
        1,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-y",
        brand,
    )
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=case.headers,
        data={"workspace_id": case.payload["workspaceId"], "title": "Material original da marca"},
        files={"file": ("brand.mp4", brand.read_bytes(), "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    brand_id = uploaded.json()["id"]
    with SessionLocal() as db:
        row = db.get(WorkspaceResource, case.project["id"])
        row.payload = {**row.payload, "sourceAssetId": brand_id}
        db.commit()

    def render_here(document_id, request, key, db, user):
        from app.models import CreativeDocument

        job, _ = craft.create_render_job(db, db.get(CreativeDocument, document_id), request, user, key)
        result = craft.execute_render_job(db, job, lambda _: None, lambda: False)
        job.status, job.progress, job.result_payload = "succeeded", 100, result
        db.commit()
        return SimpleNamespace(id=job.id)

    # Queue transport is inline; the three native operations below are not mocked.
    monkeypatch.setattr(studio_department, "render_job", render_here)
    current = client.get(f"{BASE}/{case.project['id']}", headers=case.headers).json()
    produced = client.post(
        f"{BASE}/{case.project['id']}/produce",
        headers=case.headers,
        json={"expectedRevision": current["revision"], "presentationLayout": layout},
    )
    assert produced.status_code == 200, produced.text
    project = produced.json()
    alternative = "sequential" if layout == "picture_in_picture" else "picture_in_picture"
    changed = client.post(
        f"{BASE}/{case.project['id']}/produce",
        headers=case.headers,
        json={"expectedRevision": project["revision"], "presentationLayout": alternative},
    )
    assert changed.status_code == 409
    with SessionLocal() as db:
        result = db.get(StudioGenerationJob, project["jobId"]).result_payload
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            shutil.copyfile(path, OUTPUT / "montage.mp4")
    exported = client.get(result["artifact"]["downloadUrl"], headers=case.headers)
    assert exported.status_code == 200, exported.text
    assert sha256_file(OUTPUT / "montage.mp4") == result["artifact"]["checksumSha256"]
    assert exported.content == (OUTPUT / "montage.mp4").read_bytes()
    reopened = client.get(f"/api/v1/studios/v1/documents/{project['documentId']}", headers=case.headers).json()
    assert reopened["identityRef"]["id"] == case.payload["identityVersionId"]
    assert reopened["voiceRef"]["id"] == case.payload["voiceVersionId"]
    native = reopened["nativeEditorState"]
    assert native["engine"] == "filmcraft"
    assert {item["assetId"] for item in native["assetManifest"]} >= {avatar_id, brand_id}
    duration = result["artifact"]["durationMs"]
    (OUTPUT / "verification.json").write_text(
        json.dumps({"durationMs": duration, "nativeState": native}, indent=2), encoding="utf8"
    )
    assert abs(duration - 4000) <= 100, duration
    images = []
    for name, seconds in [("presenter", 1), ("brand", 3.2)]:
        png = ffmpeg(
            "-ss", seconds, "-i", OUTPUT / "montage.mp4", "-frames:v", 1, "-f", "image2pipe", "-vcodec", "png", "-"
        )
        (OUTPUT / f"{name}.png").write_bytes(png)
        images.append(Image.open(BytesIO(png)).convert("RGB"))
        preview = client.post(
            f"/api/v1/studios/v1/documents/{project['documentId']}/craft/preview",
            headers=case.headers,
            json={"frame": round(seconds * 30)},
        )
        assert preview.status_code == 200, preview.text[:200]
        (OUTPUT / f"{name}-preview.png").write_bytes(preview.content)
        native_preview = Image.open(BytesIO(preview.content)).convert("RGB")
        assert max(ImageStat.Stat(ImageChops.difference(native_preview, images[-1])).mean) < 3
    assert images[0].size == (1080, 1350)
    center = images[0].getpixel((540, 675))
    if layout == "picture_in_picture":
        assert center[2] > 180 and center[0] < 70, center
        present = images[0].getpixel((840, 1190))
        assert present[0] > 180 and present[1] < 70 and present[2] < 70, present
        later = images[1].getpixel((840, 1190))
        assert later[0] < 70, later
    else:
        assert center[0] > 180 and center[1] < 70 and center[2] < 70, center
    center = images[1].getpixel((540, 675))
    assert center[2] > 180 and center[0] < 70 and center[1] < 70, center
    if layout == "sequential":
        row = [images[0].getpixel((x, 675)) for x in range(1080)]
        assert any(g > 180 and r < 70 and b < 70 for r, g, b in row), "left edge was cropped"
        assert any(b > 180 and r < 70 and g < 70 for r, g, b in row), "right edge was cropped"
        assert row[10][1] > 180 and row[-10][2] > 180, "the picture was not fitted to the output frame"
    pcm = ffmpeg("-i", OUTPUT / "montage.mp4", "-vn", "-f", "s16le", "-ac", 1, "-ar", 24000, "-")
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    checks = [(0.5, 440, 880), (2.5, 440, 880)]
    if layout == "sequential":
        checks.append((3.1, 880, 440))
    else:
        assert max(abs(value) for value in samples[round(3.1 * 24000) : round(3.3 * 24000)]) < 100
    for start, expected, other in checks:
        window = samples[round(start * 24000) : round((start + 0.2) * 24000)]
        assert len(window) == 4800
        assert power(window, expected) > 10 * max(power(window, other), 1), (start, expected)

    # Reusing an already rendered artifact still verifies its bytes and supplies
    # measured metadata, without requiring the renderer to be online again.
    def unavailable(*args, **kwargs):
        raise ValueError("offline")

    real_capability = craft.require_capability
    monkeypatch.setattr(craft, "require_capability", unavailable)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, project["jobId"])
        reused = craft.execute_render_job(db, job, lambda _: None, lambda: False)
        assert reused["artifact"] == result["artifact"]
    monkeypatch.setattr(craft, "require_capability", real_capability)
    revoked = client.post(
        f"/api/v1/studios/v1/consents/{case.appearance['consentGrantId']}/revoke",
        headers=case.headers,
        json={"reason": "End of private native acceptance."},
    )
    assert revoked.status_code == 200, revoked.text
    preview = client.post(
        f"/api/v1/studios/v1/documents/{project['documentId']}/craft/preview", headers=case.headers, json={"frame": 0}
    )
    assert preview.status_code == 422, preview.text
    assert "not_active" in preview.text
