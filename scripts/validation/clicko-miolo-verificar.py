"""Compare the three Clicko exports with decoded pixels and source timing."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.studios.craft_flash import inspect_video_flash
from app.services.studios.craft_source_media import shot_candidates


def decode(path, width=270, height=480):
    data = subprocess.check_output(["ffmpeg", "-v", "error", "-threads", "1", "-i", str(path), "-an",
        "-vf", f"scale={width}:{height}:flags=area", "-threads", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], timeout=100)
    return np.frombuffer(data, dtype=np.uint8).reshape(-1, height, width, 3)


def audio(path):
    data = subprocess.check_output(["ffmpeg", "-v", "error", "-threads", "1", "-i", str(path), "-vn", "-ac", "1",
                                   "-ar", "48000", "-f", "f32le", "-"], timeout=90)
    return np.frombuffer(data, dtype="<f4")


def metric(a, b):
    delta = np.array([np.abs(left.astype(np.int16) - right).mean() for left, right in zip(a, b, strict=True)])
    return {"frames": len(a), "meanPixelDelta": round(float(delta.mean()), 5),
            "worstFrameMeanDelta": round(float(delta.max()), 5)}


def main(output, previous, selected=None):
    results = {"apiSpendUsd": 0, "cases": {}}
    times = {"orbita": (2.9, 5.7, 7.75, 9.5, 12.4, 15.8), "produto": (.2, 1.2, 2.4, 2.9, 3.8, 4.8),
             "interface": (.2, .95, 1.25, 1.6, 2.35, 4.45)}
    for case in selected or times:
        folder = output/case
        path = folder/f"{case}.mp4"
        frames = decode(path)
        receipt = json.loads((folder/"recibo.json").read_text(encoding="utf-8"))
        if len(frames) != round(receipt["artifact"]["durationMs"] * 0.03):
            raise ValueError(f"Unexpected decoded frame count for {case}: {len(frames)}")
        sheet = Image.new("RGB", (6*180, 344), "#161820")
        draw = ImageDraw.Draw(sheet)
        for i, at in enumerate(times[case]):
            x = i*180
            image = Image.fromarray(frames[round(at*30)]).resize((180, 320))
            sheet.paste(image, (x, 24))
            draw.text((x+5, 5), f"{at:.2f} s", fill="white")
        sheet.save(folder/"quadros.jpg", quality=94)
        item = {"receipt": receipt, "sampleSeconds": times[case], "decodedFrames": len(frames),
                "flash": inspect_video_flash(path)}
        duration = len(frames)/30
        item["exportCandidates"] = shot_candidates({"path": str(path), "assetId": case,
            "checksumSha256": receipt["artifact"]["checksumSha256"]}, duration, time.monotonic()+25)
        if case == "orbita":
            before = decode(previous)
            assert len(before) == len(frames) == 540
            old_audio, new_audio = audio(previous), audio(path)
            item["opening"] = metric(before[:150], frames[:150])
            item["signature"] = metric(before[330:], frames[330:])
            item["middle"] = metric(before[150:330], frames[150:330])
            item["audioOutsideMiddle"] = {}
            # Exclude 60 ms around the two boundaries to account for AAC packets.
            for label, start, end in (("opening", 0, 4.94), ("signature", 11.06, 18)):
                a, b = round(start*48000), round(end*48000)
                err = old_audio[a:b] - new_audio[a:b]
                item["audioOutsideMiddle"][label] = {"rmsDelta": round(float(np.sqrt(np.mean(err**2))), 8)}
            assert item["opening"]["worstFrameMeanDelta"] < 2, item["opening"]
            assert item["signature"]["worstFrameMeanDelta"] < 2, item["signature"]
            assert item["flash"]["status"] == "pass", item["flash"]
        results["cases"][case] = item
    (output/("validacao-" + "-".join(selected) + ".json" if selected else "validacao.json")).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("previous", type=Path)
    parser.add_argument("--case", action="append", choices=("orbita", "produto", "interface"))
    args = parser.parse_args()
    main(args.output.resolve(), args.previous.resolve(), args.case)
