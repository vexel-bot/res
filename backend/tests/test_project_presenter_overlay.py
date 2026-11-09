"""Planning uses real media; no model or native rendering is claimed here."""

import subprocess
from types import SimpleNamespace

import pytest

from app.services.object_storage import LocalObjectStorage
from app.services.studios import project_montage, project_presenter_overlay


@pytest.fixture
def materials(tmp_path, monkeypatch):
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    monkeypatch.setattr(project_montage, "get_object_storage", lambda *_: storage)
    monkeypatch.setattr(project_presenter_overlay, "get_object_storage", lambda *_: storage)

    def create(name, duration, *, audio=True):
        path = tmp_path / f"{name}.mp4"
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=red:s=160x90:r=25"]
        if audio:
            command += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=24000"]
        command += [
            "-t",
            str(duration),
            "-threads",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-y",
            str(path),
        ]
        result = subprocess.run(command, capture_output=True, timeout=30, check=False)
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        stored = storage.put_file(path, key=f"workspace/fixtures/{name}.mp4", media_type="video/mp4")
        return SimpleNamespace(
            id=name,
            workspace_id="workspace",
            lifecycle_status="active",
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type="video/mp4",
            checksum_sha256=stored.checksum_sha256,
            object_metadata={"avatarVideoJobResult": {"avatar": {"durationMs": round(duration * 1000)}}},
        )

    return create


def test_overlay_plan_keeps_source_video_and_uses_only_presenter_audio(materials):
    brand, presenter = materials("brand", 1.0), materials("presenter", 0.52)
    plan = project_presenter_overlay.plan_presenter_overlay("workspace", brand, presenter)
    tracks = plan["timeline"]["tracks"]
    assert plan["mode"] == "picture_in_picture" and plan["backgroundRemoval"] is False
    assert plan["originalAudioEnabled"] is False
    assert [track["kind"] for track in tracks] == ["video", "overlay", "audio"]
    assert [track["clips"][0]["assetId"] for track in tracks] == [brand.id, presenter.id, presenter.id]
    assert all(track["clips"][0]["timeline"]["startFrame"] == 0 for track in tracks)
    assert tracks[0]["clips"][0]["timeline"]["durationFrames"] >= tracks[1]["clips"][0]["timeline"]["durationFrames"]
    assert tracks[1]["clips"][0]["transform"]["position"][0] > 540


def test_overlay_refuses_short_brand_or_silent_presenter(materials):
    short, presenter = materials("short", 0.52), materials("presenter", 1.0)
    with pytest.raises(ValueError, match="presenter_overlay_brand_video_too_short"):
        project_presenter_overlay.plan_presenter_overlay("workspace", short, presenter)
    silent = materials("silent", 0.52, audio=False)
    with pytest.raises(ValueError, match="avatar_audio_missing"):
        project_presenter_overlay.plan_presenter_overlay("workspace", presenter, silent)
