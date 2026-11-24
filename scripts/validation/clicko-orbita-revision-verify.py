"""Check exported picture and sound for the local ÓRBITA revision."""
import argparse
import importlib.util
import json
import math
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image

spec = importlib.util.spec_from_file_location("quality_result", Path(__file__).with_name("clicko-quality-result.py"))
result = importlib.util.module_from_spec(spec)
spec.loader.exec_module(result)
from app.services.studios.craft_review import _audio_report


def mix(path, work):
    work.mkdir(exist_ok=True)
    report = _audio_report(path, work, 0, 18, time.monotonic() + 90)
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-threads", "1", "-i", str(path),
                                   "-t", "18", "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], timeout=90)
    samples = np.frombuffer(raw, dtype="<f4")
    rate = len(samples) / 18
    windows = {}
    for label, (start, end) in {"lead_in": (4.46, 4.92), "impact": (5, 5.24), "world_change_1": (6.73, 7.28),
                                "world_change_2": (8.73, 9.28), "pullback": (10.76, 11.35),
                                "reveal": (12.18, 12.72), "before_fade": (15.8, 16.4), "tail": (17.75, 17.98)}.items():
        segment = samples[round(rate*start):round(rate*end)]
        rms = float(np.sqrt(np.mean(segment**2)))
        windows[label] = {"startSeconds": start, "endSeconds": end, "rmsDbfs": round(20*math.log10(max(rms, 1e-9)), 2)}
    return {"report": report, "cueWindows": windows,
            "fadeDropDb": round(windows["before_fade"]["rmsDbfs"] - windows["tail"]["rmsDbfs"], 2)}


def rail_clearance(path):
    # Rows just above and below the footage at the central film rail, away from the warm perforations.
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-threads", "1", "-i", str(path), "-an",
                                   "-vf", "crop=20:420:496:428", "-threads", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], timeout=90)
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 420, 20, 3)
    # The native composition sets the settled window to ~298 px high, with rails at center ±165.
    rows = frames[370:535, [41, 379], :, :].astype(np.int16)
    body_rgb = np.array([32, 20, 16])
    distances = np.max(np.abs(rows - body_rgb), axis=-1)
    proportion = (distances <= 16).mean(axis=(1, 2))
    return {"firstFrame": 370, "lastFrame": 534, "sampleRows": [469, 807],
            "framesWithCleanRailSamples": int((proportion >= .95).sum()), "totalFrames": len(proportion),
            "minimumMatchingProportion": round(float(proportion.min()), 3),
            "scope": "Twenty pixels between the central perforations, at the top and bottom rail rows in the settled signature"}


def main(output, original):
    revision = output / "orbita-revisada.mp4"
    measurements = {"original": result.measure(original, output, "opus-original"),
                    "revised": result.measure(revision, output, "revisao"),
                    "apiSpendUsd": 0}
    measurements["originalMix"] = mix(original, output / "sinal-original")
    measurements["revisedMix"] = mix(revision, output / "sinal-revisado")
    measurements["revisedRailClearance"] = rail_clearance(revision)
    receipt = json.loads((output / "recibo-revisao.json").read_text(encoding="utf-8"))
    assert receipt["artifact"]["checksumSha256"] == measurements["revised"]["sha256"]
    assert measurements["revised"]["wideAreaBrightness"]["status"] == "pass"
    assert measurements["revised"]["audio"]["peak"] < 1
    assert measurements["revisedMix"]["fadeDropDb"] > 10
    rail = measurements["revisedRailClearance"]
    assert rail["framesWithCleanRailSamples"] == rail["totalFrames"], rail
    (output / "comparacao-revisao.json").write_text(json.dumps(measurements, indent=2, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(revision), "-vn", "-c:a", "pcm_s16le",
                    str(output / "orbita-mix.wav")], check=True, timeout=60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("original", type=Path)
    args = parser.parse_args()
    main(args.output.resolve(), args.original.resolve())
