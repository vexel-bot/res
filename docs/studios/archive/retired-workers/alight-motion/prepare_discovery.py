"""Prepare owned technical fixtures; these are not Alight render evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/alight-discovery-20261002/materials"


def run(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Motion inside a generated graphic is a playback/trim fixture, not filmed action.
    for fps in (24, 60):
        run(
            "-f", "lavfi", "-i", f"testsrc2=size=540x960:rate={fps}:duration=3",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", str(OUT / f"trim-source-{fps}fps.mp4"),
        )
    cutout = Image.new("RGBA", (600, 800), (0, 0, 0, 0))
    draw = ImageDraw.Draw(cutout)
    draw.rounded_rectangle((170, 130, 430, 690), radius=60, fill="#194A51")
    draw.rounded_rectangle((210, 60, 390, 165), radius=24, fill="#F3B64A")
    draw.ellipse((220, 300, 380, 460), fill="#F5EFE3")
    cutout.save(OUT / "neutral-object-rgba.png")
    run(
        "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000:duration=0.12",
        "-af", "afade=t=out:st=0.02:d=0.1,adelay=1000,apad=whole_dur=15",
        "-t", "15", "-c:a", "pcm_s16le", str(OUT / "sync-reference-1s.wav"),
    )
    fonts = ROOT / "backend/app/resources/editorial_fonts"
    for name in ("IBMPlexMono-Medium.ttf", "OFL-IBMPlexMono.txt"):
        shutil.copyfile(fonts / name, OUT / name)
    assets = []
    for path in sorted(OUT.iterdir()):
        if path.is_file():
            assets.append({
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "provenance": "repository_font_OFL" if path.suffix == ".ttf" or path.name.startswith("OFL") else "generated_owned_technical_fixture",
            })
    (OUT.parent / "materials-manifest.json").write_text(json.dumps({
        "kind": "alight.discovery_materials.v1",
        "evidenceKind": "preparation_only",
        "renderVerified": False,
        "filmedActionSeconds": 0,
        "apiSpendUsd": 0,
        "output": {"width": 1080, "height": 1920, "fps": 30, "durationSeconds": 15},
        "fontProbeText": "Ação • café • precisão • 0123456789",
        "assets": assets,
        "checksToPerformInApp": [
            "trim_24_and_60fps", "constant_speed", "aspect_preservation", "alpha_image",
            "font_import_portuguese", "text", "mask_overlap", "audio_event_at_1s",
            "editable_export_reimport", "automatic_text_asset_duration_changes", "silent_video_export",
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(assets)} assets at {OUT}; no app execution claimed.")


if __name__ == "__main__":
    main()
