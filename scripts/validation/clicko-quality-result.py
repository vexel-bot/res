"""Measure the paid MP4 and immutable baseline without external inference."""
import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.studios.craft_flash import inspect_video_flash


def ff(*args):
    return subprocess.check_output(args, timeout=90)


def measure(path, output, label):
    probe = json.loads(ff("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)))
    video = next(item for item in probe["streams"] if item["codec_type"] == "video")
    audio = next((item for item in probe["streams"] if item["codec_type"] == "audio"), None)
    duration = float(probe["format"]["duration"])
    width = 300
    height = round(width * video["height"] / video["width"])
    sheet = Image.new("RGB", (4 * width, 3 * (height + 25)), "#151821")
    draw = ImageDraw.Draw(sheet)
    samples = [round(duration * fraction, 3) for fraction in (.02, .09, .16, .23, .30, .37, .44, .51, .59, .68, .81, .94)]
    for index, at in enumerate(samples):
        frame = ff("ffmpeg", "-v", "error", "-threads", "1", "-ss", str(at), "-i", str(path), "-an",
                   "-frames:v", "1", "-vf", f"scale={width}:{height}", "-threads", "1", "-f", "image2pipe", "-c:v", "png", "-")
        x, y = index % 4 * width, index // 4 * (height + 25)
        sheet.paste(Image.open(BytesIO(frame)), (x, y + 25))
        draw.text((x + 8, y + 6), f"{at:.2f} s", fill="white")
    sheet.save(output / f"{label}-quadros.jpg", quality=90)
    signal = None
    if audio:
        pcm = np.frombuffer(ff("ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                               "-f", "f32le", "-"), dtype="<f4")
        signal = {"codec": audio["codec_name"], "sampleRate": int(audio["sample_rate"]), "durationSeconds": len(pcm) / 16000,
                  "rms": float(np.sqrt(np.mean(pcm**2))), "peak": float(np.abs(pcm).max()), "listening": "pending"}
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "durationSeconds": duration,
            "dimensions": [video["width"], video["height"]], "fps": float(Fraction(video["avg_frame_rate"])),
            "audio": signal, "wideAreaBrightness": inspect_video_flash(path), "visualSampleSeconds": samples}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    baseline = output.parent / "clicko-orbita-independente-2026-11-12" / "orbita-independente-previa-sem-audio.mp4"
    result = {"schemaVersion": "clicko.quality-cycle-measurement.v1", "baseline": measure(baseline, output, "baseline"),
              "new": measure(output / "orbita-opus-quality-cycle.mp4", output, "opus"), "additionalApiSpendUsd": 0}
    (output / "comparison.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
