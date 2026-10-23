"""Own synthetic inputs and objective checks of actual Clicko exports, never AI output."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.studios.media_runtime import resolve_tool  # noqa: E402

OUT = ROOT / ".codex-runtime/audit-2026-10-23"
FF = resolve_tool("ffmpeg")
FP = resolve_tool("ffprobe")


def run(args):
    return subprocess.run(
        args, check=True, capture_output=True, timeout=180,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ).stdout


def frame(file, second):
    from io import BytesIO

    return Image.open(BytesIO(run([
        FF, "-v", "error", "-ss", str(second), "-i", str(file),
        "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-threads", "1", "-",
    ]))).convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "fixtures":
        # Bounded, authored fixtures. No commercial footage, download or paid call.
        from app.providers.studios.media_runtime import h264_encoder

        source = OUT / "source-red-blue.mp4"
        tone = OUT / "source-tone.wav"
        if not source.exists():
            run([FF, "-v", "error", "-f", "lavfi", "-i", "color=red:s=320x180:r=24:d=2",
                 "-f", "lavfi", "-i", "color=blue:s=320x180:r=24:d=2", "-filter_complex_threads", "1",
                 "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
                 "-c:v", h264_encoder(FF), "-threads", "1", str(source)])
        if not tone.exists():
            run([FF, "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
                 "-ar", "48000", "-ac", "1", str(tone)])
        image = OUT / "source-card.png"
        if not image.exists():
            bitmap = Image.new("RGB", (256, 128), "#FF7F50")
            ImageDraw.Draw(bitmap).rectangle((16, 16, 240, 112), fill="#6EB8F5")
            bitmap.save(image)
        print(json.dumps({"fixtures": "ready", "externalCostUsd": 0}))
        return

    evidence = json.loads((OUT / "live.json").read_text(encoding="utf8"))
    results = {}
    for name in ("motion-a.mp4", "motion-c.mp4", "motion-c2.mp4", "video-b.mp4"):
        file = OUT / name
        metadata = json.loads(run([FP, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(file)]))
        run([FF, "-v", "error", "-i", str(file), "-f", "null", "-"])
        video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
        expected = 4 if name == "video-b.mp4" else 15
        assert abs(float(metadata["format"]["duration"]) - expected) < 0.1
        assert video["codec_name"] == "h264" and audio["codec_name"] == "aac"
        assert (video["width"], video["height"]) == (1280, 720)
        assert video["avg_frame_rate"] == "24/1"
        assert abs(float(video["duration"]) - float(audio["duration"])) < 0.1
        times = [0.08, 0.5, 1.5, 2.5, 3.8] if expected == 4 else [0.08, 0.5, 2.5, 4.85, 5.5, 7.5, 10.5, 14.5]
        sheet = Image.new("RGB", (640, 204 * ((len(times) + 1) // 2)), "#181818")
        draw = ImageDraw.Draw(sheet)
        for index, second in enumerate(times):
            bitmap = frame(file, second)
            bitmap.thumbnail((320, 180))
            x, y = (index % 2) * 320, (index // 2) * 204
            sheet.paste(bitmap, (x, y))
            draw.text((x + 8, y + 183), f"{name} | {second:.2f} s", fill="white")
        sheet.save(OUT / (name + ".jpg"))
        results[name] = {"duration": expected, "width": video["width"], "height": video["height"],
                         "fps": video["avg_frame_rate"], "codec": video["codec_name"],
                         "audio": audio["codec_name"], "decoded": True,
                         "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                         "streamDurationDelta": abs(float(video["duration"]) - float(audio["duration"]))}
    # Inspect a region outside overlay/title, not just metadata saying cuts exist.
    first = np.asarray(frame(OUT / "video-b.mp4", 0.8))[160:230, 100:200].mean(axis=(0, 1))
    second = np.asarray(frame(OUT / "video-b.mp4", 2.8))[160:230, 100:200].mean(axis=(0, 1))
    assert first[2] > first[0] + 100 and second[0] > second[2] + 100
    raw = run([FF, "-v", "error", "-i", str(OUT / "video-b.mp4"), "-vn", "-ar", "48000",
               "-ac", "1", "-f", "f32le", "-"])
    samples = np.frombuffer(raw, dtype="<f4")

    def rms(start, end):
        values = samples[round(start * 48000):round(end * 48000)]
        return float(np.sqrt(np.mean(values ** 2)))

    quiet, audible, ending = rms(0, 0.04), rms(1, 1.5), rms(3.96, 4)
    assert audible > 0.01 and quiet < audible * 0.3 and ending < audible * 0.3
    results["video-b.mp4"].update(reorderedBlueThenRed=True, audioRms={"start": quiet, "body": audible, "end": ending})
    assert results["motion-a.mp4"]["sha256"] != results["motion-c.mp4"]["sha256"]
    early = np.asarray(frame(OUT / "motion-a.mp4", 1.5), dtype=float)
    later = np.asarray(frame(OUT / "motion-a.mp4", 2.5), dtype=float)
    results["motion-a.mp4"]["meanFrameDelta1_5To2_5Seconds"] = float(np.abs(early - later).mean())
    with Image.open(OUT / "image-i.png") as image:
        assert image.size == (1280, 720) and image.format == "PNG"
        image.verify()
    results["image-i.png"] = {"width": 1280, "height": 720, "verified": True}
    # Snapshot scope and perceptual/artistic conclusions are separate evidence.
    (OUT / "media-analysis.json").write_text(json.dumps({"media": results, "apiEvidence": evidence["summary"]}, indent=2), encoding="utf8")
    print(json.dumps({"decodedVideos": 4, "pngVerified": True, "reorderedCutsVerified": True, "audioFadesVerified": True}))


if __name__ == "__main__":
    main()
