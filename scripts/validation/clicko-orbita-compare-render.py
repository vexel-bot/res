"""Compare the actual rendered timelines at phone size without using an API."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def run(*args):
    return subprocess.run(args, capture_output=True, check=True, timeout=90).stdout


def inspect(path, output):
    info = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)))
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    fps_parts = stream["avg_frame_rate"].split("/")
    fps = int(fps_parts[0]) / int(fps_parts[1])
    raw = run("ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf", "scale=300:534",
              "-threads", "1", "-c:v", "rawvideo", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1")
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 534, 300, 3)
    reduced = frames[:, ::6, ::6].astype(np.int16)
    deltas = np.abs(np.diff(reduced, axis=0)).mean(axis=(1, 2, 3))
    peaks = []
    for i in np.argsort(deltas)[::-1]:
        moment = (i + 1) / fps
        if deltas[i] < 7 or len(peaks) >= 12:
            break
        if all(abs(moment - peak["seconds"]) > .22 for peak in peaks):
            peaks.append({"seconds": round(moment, 3), "rgbDelta": round(float(deltas[i]), 2)})
    blank = np.std(reduced, axis=(1, 2, 3)) < 2
    seconds = [.583, 1.5, 2.667, 4.833, 6.667, 8.333, 9.833, 11.5, 12.75, 13.917, 15.5, 17.5]
    sheet = Image.new("RGB", (300 * 4, 558 * 3), "#14191f")
    draw = ImageDraw.Draw(sheet)
    for i, t in enumerate(seconds):
        index = min(round(t * fps), len(frames) - 1)
        x, y = i % 4 * 300, i // 4 * 558
        sheet.paste(Image.fromarray(frames[index]), (x, y + 24))
        draw.text((x + 7, y + 6), f"{index / fps:.2f} s", fill="white")
    sheet.save(output / f"{path.stem}-quadros.jpg", quality=89)
    audio = None
    if any(s["codec_type"] == "audio" for s in info["streams"]):
        waveform = np.frombuffer(run("ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
            "-ar", "24000", "-f", "f32le", "pipe:1"), dtype="<f4")
        rms = np.sqrt(np.mean(waveform**2))
        audio = {"peakDbfs": round(float(20 * np.log10(max(1e-9, np.abs(waveform).max()))), 2),
                 "rmsDbfs": round(float(20 * np.log10(max(1e-9, rms))), 2)}
        for hit in (2.25, 4.50, 6.25, 8.0, 9.5, 11, 13.5, 14.5):
            at = round(24000 * hit)
            if at + 2400 < len(waveform):
                before, after = waveform[at-2400:at], waveform[at:at+2400]
                audio.setdefault("accents", []).append({"seconds": hit,
                    "changeDb": round(float(20 * np.log10(max(1e-9,np.linalg.norm(after)) /
                                                          max(1e-9,np.linalg.norm(before)))), 2)})
    result = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": [stream["width"], stream["height"]],
              "fps": fps, "frames": len(frames), "durationSeconds": len(frames) / fps, "nearBlankFrames": int(blank.sum()),
              "imageChanges": sorted(peaks, key=lambda p: p["seconds"]), "audio": audio}
    (output / f"{path.stem}-medicoes.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    for file in args.files:
        inspect(args.output / file, args.output)
