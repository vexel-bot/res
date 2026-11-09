"""FilmCraft acceptance with synthetic cards and tones; no person or model is used."""

import math
import struct
import subprocess
from types import SimpleNamespace

from PIL import Image, ImageChops, ImageStat

from app.providers.studios.craft import call_engine
from app.services.object_storage import LocalObjectStorage
from app.services.studios import project_montage, project_presenter_overlay


def test_filmcraft_overlay_preview_export_and_audio(tmp_path, monkeypatch):
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    monkeypatch.setattr(project_montage, "get_object_storage", lambda *_: storage)
    monkeypatch.setattr(project_presenter_overlay, "get_object_storage", lambda *_: storage)
    root = tmp_path / "craft-job"
    root.mkdir()
    media = []

    def create(name, color, seconds, frequency):
        path = root / f"{name}.mp4"
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color={color}:s=160x90:r=25",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={frequency}:sample_rate=24000",
                "-t",
                str(seconds),
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
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        stored = storage.put_file(path, key=f"workspace/fixtures/{name}.mp4", media_type="video/mp4")
        media.append(
            {
                "assetId": name,
                "relativePath": path.name,
                "path": str(path),
                "checksumSha256": stored.checksum_sha256,
                "mediaType": "video/mp4",
            }
        )
        return SimpleNamespace(
            id=name,
            workspace_id="workspace",
            lifecycle_status="active",
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type="video/mp4",
            checksum_sha256=stored.checksum_sha256,
            object_metadata={"avatarVideoJobResult": {"avatar": {"durationMs": round(seconds * 1000)}}},
        )

    brand, presenter = create("brand", "blue", 1.0, 880), create("presenter", "red", 0.52, 440)
    plan = project_presenter_overlay.plan_presenter_overlay(
        "workspace", brand, presenter, frame_width=320, frame_height=180
    )
    native = root / "overlay.fcproj"
    params = {"mediaRoot": str(root), "media": media}
    created = call_engine(
        "filmcraft",
        "project.new",
        {
            **params,
            "outputPath": str(native),
            "width": 320,
            "height": 180,
            "legacyDocument": {"composition": {"pages": [], "mediaTimeline": plan["timeline"]}},
        },
    )
    assert not created.get("warnings"), created.get("warnings")
    assert native.is_file()
    opened = call_engine("filmcraft", "project.open", {**params, "nativePath": str(native)})
    assert len(opened["inspection"]["timeline"]) >= 3
    preview = root / "preview.png"
    call_engine(
        "filmcraft", "render.frame", {**params, "nativePath": str(native), "outputPath": str(preview), "frame": 6}
    )
    frame = Image.open(preview).convert("RGB")
    blue, red = frame.getpixel((100, 90)), frame.getpixel((250, 145))
    assert blue[2] > 150 and blue[0] < 80, blue
    assert red[0] > 150 and red[2] < 80, red
    output = root / "export.mp4"
    call_engine(
        "filmcraft", "render.export", {**params, "nativePath": str(native), "outputPath": str(output), "format": "mp4"}
    )
    for seconds, name in [(0.2, "during"), (0.8, "after")]:
        decoded = root / f"{name}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(seconds),
                "-i",
                str(output),
                "-frames:v",
                "1",
                "-y",
                str(decoded),
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
        image = Image.open(decoded).convert("RGB")
        if name == "during":
            assert max(ImageStat.Stat(ImageChops.difference(frame, image)).mean) < 6
        else:
            after = image.getpixel((250, 145))
            assert after[2] > 150 and after[0] < 80, after
    pcm = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(output),
            "-vn",
            "-f",
            "s16le",
            "-ac",
            "1",
            "-ar",
            "24000",
            "-",
        ],
        capture_output=True,
        timeout=60,
        check=True,
    ).stdout
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    window = samples[4800:9600]

    def power(freq):
        return math.hypot(
            sum(v * math.sin(2 * math.pi * freq * i / 24000) for i, v in enumerate(window)),
            sum(v * math.cos(2 * math.pi * freq * i / 24000) for i, v in enumerate(window)),
        )

    assert len(window) == 4800 and power(440) > 10 * max(power(880), 1)
    tail = samples[16800:21600]
    assert len(tail) == 4800 and max(abs(value) for value in tail) < 100
