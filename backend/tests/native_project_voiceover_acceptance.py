"""Actual FilmCraft picture/audio export. Speech adapters emit test tones, not qualified voices."""

import hashlib
import json
import struct
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from native_project_avatar_acceptance import ffmpeg, power
from PIL import Image, ImageChops, ImageStat
from test_project_voiceover import prepare, produce

from app.database import SessionLocal
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.routers import studio_department
from app.services.object_storage import sha256_file
from app.services.studios import craft

OUTPUT = Path(__file__).resolve().parents[2] / ".codex-runtime/team-sync/native-voiceover"


@pytest.mark.parametrize(
    "kind,source_kind,source_seconds",
    [
        ("cloned", "video", 1.2),
        ("stock", "video", 3.6),
        ("cloned", "image", 0),
        ("stock", "image", 0),
    ],
)
def test_selected_voice_narrates_the_entire_native_video_without_original_sound(
    client, monkeypatch, tmp_path, kind, source_kind, source_seconds
):
    case = prepare(client, monkeypatch, tmp_path, kind, source_kind, source_seconds)

    def inline_render(document_id, request, key, db, user):
        job, _ = craft.create_render_job(db, db.get(CreativeDocument, document_id), request, user, key)
        result = craft.execute_render_job(db, job, lambda _: None, lambda: False)
        job.status, job.progress, job.result_payload = "succeeded", 100, result
        db.commit()
        return SimpleNamespace(id=job.id)

    monkeypatch.setattr(studio_department, "render_job", inline_render)
    response = produce(client, case)
    assert response.status_code == 200, response.text
    project = response.json()
    with SessionLocal() as db:
        result = db.get(StudioGenerationJob, project["jobId"]).result_payload
        source = db.get(LibraryAsset, case.source_id)
        original_checksum = source.checksum_sha256
        with case.storage.materialize(source.storage_key) as path:
            assert sha256_file(path) == original_checksum
    assert result["artifact"]["hasAudio"]
    assert abs(result["artifact"]["durationMs"] - 2800) <= 100
    exported = client.get(result["artifact"]["downloadUrl"], headers=case.headers)
    assert exported.status_code == 200, exported.text
    directory = OUTPUT / f"{kind}-{source_kind}"
    directory.mkdir(parents=True, exist_ok=True)
    video = directory / "narrated.mp4"
    video.write_bytes(exported.content)
    assert sha256_file(video) == result["artifact"]["checksumSha256"]
    frames = []
    for name, seconds in [("start", 0.2), ("end", 2.5)]:
        png = ffmpeg("-ss", seconds, "-i", video, "-frames:v", 1, "-f", "image2pipe", "-vcodec", "png", "-")
        (directory / f"{name}.png").write_bytes(png)
        decoded = Image.open(BytesIO(png)).convert("RGB")
        assert decoded.size == (1080, 1350)
        preview = client.post(
            f"/api/v1/studios/v1/documents/{project['documentId']}/craft/preview",
            headers=case.headers,
            json={"frame": round(seconds * 30)},
        )
        assert preview.status_code == 200, preview.text[:160]
        (directory / f"{name}-preview.png").write_bytes(preview.content)
        assert (
            max(
                ImageStat.Stat(ImageChops.difference(decoded, Image.open(BytesIO(preview.content)).convert("RGB"))).mean
            )
            < 3
        )
        frames.append(decoded)
    if source_kind == "video":
        first, last = [image.getpixel((540, 675)) for image in frames]
        assert first[0] > 180 and first[2] < 70, first
        assert last[2] > 180 and last[0] < 70, last
    else:
        for image in frames:
            r, g, b = image.getpixel((540, 675))
            assert g > 130 and r < 70 and b < 150, (r, g, b)
    pcm = ffmpeg("-i", video, "-vn", "-f", "s16le", "-ac", 1, "-ar", 24000, "-")
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    for start in (0.3, 1.5, 2.5):
        window = samples[round(start * 24000) : round((start + 0.2) * 24000)]
        assert len(window) == 4800
        assert power(window, 440) > 10 * max(power(window, 880), 1), start
    reopened = client.get(f"/api/v1/studios/v1/documents/{project['documentId']}", headers=case.headers).json()
    assert reopened["identityRef"] is None
    assert reopened["voiceRef"]["id"] == case.voice_id
    assert {entry["assetId"] for entry in reopened["nativeEditorState"]["assetManifest"]} >= {
        case.source_id,
        case.audio_id,
    }
    original = client.get(f"/api/v1/assets/{case.source_id}/content", headers=case.headers)
    assert original.status_code == 200
    assert hashlib.sha256(original.content).hexdigest() == original_checksum
    (directory / "verification.json").write_text(
        json.dumps(
            {"result": result, "plan": project["montagePlan"], "sourceChecksumSha256": original_checksum}, indent=2
        ),
        encoding="utf8",
    )
    assert produce(client, case).json()["jobId"] == project["jobId"]
