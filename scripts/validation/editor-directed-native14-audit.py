"""Checksum-bound decoding evidence; never assigns human quality or preference."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/visual-directed-native14-20261004"
OLD = ROOT / "output/visual-distance-20261002"
FREEZE = ROOT / "docs/studios/research/editor-oss-20261002/temporal-matte-composition-preview/current-sources.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retain(path, value):
    assert not path.exists(), "Preserve existing evidence: " + str(path)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sources():
    frozen = read(FREEZE)["sources"]
    assert all(sha(ROOT / path) == digest for path, digest in frozen.items())
    return {**frozen, **{path: sha(ROOT / path) for path in [
        "scripts/validation/editor-directed-native14.py",
        "scripts/validation/editor-directed-native14-audit.py",
        "scripts/validation/editor-directed-native14-review.py",
        "scripts/validation/visual-distance-study.py"]}}


parser = argparse.ArgumentParser()
parser.add_argument("--key", required=True)
args = parser.parse_args()
frozen = sources()
state = read(OUT / "execution.json")
assert sha(OLD / "execution.json") == state["historicalExecutionSha256"]
value = state["variants"][args.key]
assert value.get("artifact") and value["status"] == "succeeded"
target = OUT / (args.key + "-technical-audit.json")
assert not target.exists()
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.studios.heavy_media_lease import heavy_media_lease  # noqa: E402

receipt = read(OUT / (args.key + "-render.json"))
result, snapshot, metadata = receipt["renderResult"], receipt["snapshot"], receipt["renderMetadata"]
video = OUT / (args.key + ".mp4")
assert sha(video) == value["artifact"]["checksumSha256"] == result["artifact"]["checksumSha256"]
assert result["documentId"] == snapshot["documentId"] == value["documentId"]
assert result["documentRevision"] == snapshot["revision"] == value["revision"]
assert result["providerVersion"] == "4.0.527-native.14" and result["framesRendered"] == 450
assert result["qualityEvaluation"]["status"] == "passed"
snapshot_bytes = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
assert hashlib.sha256(snapshot_bytes).hexdigest() == metadata["documentSnapshotSha256"]
request = read(OUT / (args.key + "-request.json"))
prior = read(OUT / (args.key + "-source-plan.json"))["direction"]
assert {k: v for k, v in request.items() if k != "expectedDocumentRevision"} == {
    k: v for k, v in prior.items() if k != "expectedDocumentRevision"}
assert sha(OLD / (args.key + ".mp4")) == value["historicalMp4Sha256"]
assert {b["assetId"]: b["checksumSha256"] for b in metadata["sourceAssetBindings"]} == value["sourceChecksums"]
geometry = metadata["contextualEditing"]["rendererChecks"]["geometrySamples"]
assert [g["frame"] for g in geometry] == list(range(450))
outside_canvas = []
for sample in geometry:
    for element in sample["elements"]:
        if not element.get("present") or not element.get("visible") or element.get("opacity", 0) <= 0:
            continue
        b = element["bounds"]
        assert all(np.isfinite(b[k]) for k in ["x", "y", "width", "height"])
        if b["x"] < 0 or b["y"] < 0 or b["x"] + b["width"] > 1080 or b["y"] + b["height"] > 1920:
            outside_canvas.append({"frame": sample["frame"], "semanticId": element["semanticId"], "bounds": b})

contact_frames = [0, 59, 79, 109, 139, 179, 219, 244, 279, 309, 329, 359, 389, 419, 449]
contact = Image.new("RGB", (1350, 1524), "#202426")
draw = ImageDraw.Draw(contact)
measurements = []
previous = None
frame_bytes = 270 * 480 * 3
with heavy_media_lease("study_artifact_decode", "directed-native14-audit-" + args.key):
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames",
        "-show_streams", "-show_format", "-of", "json", str(video)], text=True))
    stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert (stream["width"], stream["height"], stream["r_frame_rate"], int(stream["nb_read_frames"])) == (
        1080, 1920, "30/1", 450)
    assert sum(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in probe["streams"]) == 1
    timing = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_frames", "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(video)], text=True))
    pts = [float(f["best_effort_timestamp_time"]) for f in timing["frames"]]
    assert len(pts) == 450 and max(abs(t - i / 30) for i, t in enumerate(pts)) <= 0.000001
    process = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-vf", "scale=270:480",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in range(450):
            raw = process.stdout.read(frame_bytes)
            assert len(raw) == frame_bytes, "Missing decoded frame " + str(frame)
            pixels = np.frombuffer(raw, dtype=np.uint8).reshape(480, 270, 3)
            delta = None if previous is None else float(np.abs(pixels.astype(np.int16) - previous).mean())
            measurements.append({"frame": frame, "ptsSeconds": pts[frame],
                "scaledRgbSha256": hashlib.sha256(raw).hexdigest(), "meanAbsoluteChannelDelta": delta,
                "minimumChannel": int(pixels.min()), "maximumChannel": int(pixels.max())})
            previous = pixels.astype(np.int16)
            if frame in contact_frames:
                i = contact_frames.index(frame)
                x, y = i % 5 * 270, i // 5 * 508
                contact.paste(Image.frombytes("RGB", (270, 480), raw), (x, y))
                draw.text((x + 8, y + 485), f"frame {frame} / {frame / 30:.2f}s", fill="white")
        assert process.stdout.read(1) == b"", "Unexpected extra decoded frame"
        assert process.wait(timeout=30) == 0, process.stderr.read().decode(errors="replace")
    finally:
        if process.poll() is None:
            process.terminate()
        process.stdout.close()
        process.stderr.close()
    audio_raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(video), "-vn",
        "-ac", "1", "-ar", "48000", "-f", "f32le", "pipe:1"])
    audio = np.frombuffer(audio_raw, dtype="<f4")
    assert len(audio) >= 720000 and np.isfinite(audio).all()
    bins = np.sqrt(np.square(audio[:720000].reshape(750, 960).astype(np.float64)).mean(axis=1))

assert frozen == sources(), "Sources changed during decode"
image_path = OUT / (args.key + "-analysis-contact.png")
assert not image_path.exists()
contact.save(image_path)
retain(target, {"scope": "complete_decode_at_270x480_no_human_approval", "key": args.key,
    "artifactSha256": sha(video), "documentId": value["documentId"], "revision": value["revision"],
    "jobId": value["jobId"], "snapshotSha256": metadata["documentSnapshotSha256"], "sources": frozen,
    "unchangedDirectionExceptExpectedRevision": True, "sourceBindings": metadata["sourceAssetBindings"],
    "historicalMp4Sha256": value["historicalMp4Sha256"], "probe": probe,
    "decodeWidth": 270, "decodeHeight": 480, "decodedFrames": measurements,
    "geometry": {"sampledFrames": 450, "basis": "dom_bounding_box",
        "visibleBoundsOutsideCanvas": outside_canvas, "glyphOrMaskCoverageProvenByBounds": False},
    "contactFrames": contact_frames, "contactSha256": sha(image_path),
    "audio": {"decodedMonoSampleRate": 48000, "decodedSampleCount": len(audio),
        "paddingSamplesAfter15Seconds": len(audio) - 720000, "rmsBinSeconds": 0.02,
        "first15SecondsRms": bins.tolist(), "decodedPeak": float(np.abs(audio).max()),
        "soundCausality": "not_assessed"},
    "qcWarnings": [c for c in result["qualityEvaluation"]["checks"] if c["status"] != "passed"],
    "semanticAssertions": [{"sceneId": s["id"], "assertions": s["semanticAssertions"]} for s in request["scenes"]],
    "semanticAction": "not_certified_by_frame_hashes_or_sparse_contact_sheet", "humanReview": "not_assessed",
    "blindPreference": "not_assessed", "autonomy": "not_demonstrated"})
print(json.dumps({"key": args.key, "decodedFrames": 450, "audioSamples": len(audio), "humanReview": "not_assessed"}))
