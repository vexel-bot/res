"""Real media inspection for sequential placement and delivered Craft metadata."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.object_storage import LocalObjectStorage, sha256_file
from app.services.studios import craft, project_montage


@pytest.fixture
def media(tmp_path, monkeypatch):
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    monkeypatch.setattr(project_montage, "get_object_storage", lambda backend: storage)

    def create(*, audio=True, declared=520):
        path = tmp_path / ("audio.mp4" if audio else "silent.mp4")
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=160x90:r=25"]
        if audio:
            args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=24000"]
        args += [
            "-t",
            "0.52",
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
        encoded = subprocess.run(args, capture_output=True, timeout=30, check=False)
        assert encoded.returncode == 0, encoded.stderr.decode(errors="replace")
        stored = storage.put_file(path, key=f"workspace/fixtures/{path.name}", media_type="video/mp4")
        return SimpleNamespace(
            id=path.stem,
            workspace_id="workspace",
            lifecycle_status="active",
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type="video/mp4",
            checksum_sha256=stored.checksum_sha256,
            object_metadata={"avatarVideoJobResult": {"avatar": {"durationMs": declared}}},
        ), path

    return create


def test_fractional_duration_is_measured_and_next_video_starts_after_final_audio(media):
    asset, path = media()
    plan = project_montage.plan_video_montage("workspace", [asset, asset], avatar_asset_id=asset.id)
    first, second = plan["clips"]
    assert first["measuredDurationMicroseconds"] == 520_000
    assert first["durationFrames"] == 16
    assert second["startFrame"] == 16
    assert second["startFrame"] / plan["fps"] >= first["measuredDurationMicroseconds"] / 1e6
    assert project_montage.native_imports(plan)[2]["params"]["seconds"] == 16 / 30
    metadata = craft.validate_render_output(path, "mp4")
    assert metadata["durationMs"] == 520
    assert (metadata["width"], metadata["height"], metadata["fps"], metadata["hasAudio"]) == (160, 90, 25, True)


@pytest.mark.parametrize(
    "audio,declared,code", [(False, 520, "avatar_audio_missing"), (True, 100, "avatar_duration_mismatch")]
)
def test_avatar_cannot_silently_lose_audio_or_change_duration(media, audio, declared, code):
    asset, _ = media(audio=audio, declared=declared)
    with pytest.raises(ValueError, match=code):
        project_montage.plan_video_montage("workspace", [asset], avatar_asset_id=asset.id)


def test_material_changes_are_rejected_before_the_decoder_runs(tmp_path, monkeypatch):
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    path = tmp_path / "sample.mp4"
    path.write_bytes(b"immutable-fixture")
    stored = storage.put_file(path, key="workspace/fixtures/sample.mp4", media_type="video/mp4")
    monkeypatch.setattr(project_montage, "get_object_storage", lambda backend: storage)
    asset = SimpleNamespace(
        id="sample",
        workspace_id="workspace",
        lifecycle_status="active",
        storage_key=stored.key,
        storage_backend=stored.backend,
        media_type="video/mp4",
        checksum_sha256="f" * 64,
    )

    def unexpected(*args, **kwargs):
        pytest.fail("changed media reached the decoder")

    monkeypatch.setitem(project_montage.MEDIA_PROBE_PROVIDERS, "builtin.ffprobe", SimpleNamespace(probe=unexpected))
    with pytest.raises(ValueError, match="checksum_mismatch"):
        project_montage.plan_video_montage("workspace", [asset])
    asset.checksum_sha256 = sha256_file(path)
    with pytest.raises(ValueError, match="material_invalid"):
        project_montage.plan_video_montage("other-workspace", [asset])


def test_container_signature_alone_cannot_pass_as_a_valid_export(tmp_path):
    path = Path(tmp_path) / "fake.mp4"
    path.write_bytes(b"\0\0\0\x18ftypisom" + b"\0" * 24)
    with pytest.raises(ValueError, match="media_probe_failed"):
        craft.validate_render_output(path, "mp4")


def test_decoder_errors_do_not_expose_local_media_paths(media, monkeypatch):
    asset, _ = media()

    def unavailable(*args, **kwargs):
        raise ValueError("media_probe_failed:private-server-path")

    monkeypatch.setitem(project_montage.MEDIA_PROBE_PROVIDERS, "builtin.ffprobe", SimpleNamespace(probe=unavailable))
    with pytest.raises(ValueError) as caught:
        project_montage.plan_video_montage("workspace", [asset])
    assert str(caught.value) == "studio_montage_material_unreadable"
