"""Measure the isolated Café Aurora pilot without manufacturing human scores."""

import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/hybrid-aurora-pilot"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def probe(path):
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,codec_type,width,height,r_frame_rate:format=duration",
                "-of",
                "json",
                str(path),
            ]
        )
    )


def evaluate(variant, database):
    path = OUT / f"animatic-{variant}.mp4"
    receipt = read(f"reference-{variant}-render.json")
    document = read(f"reference-{variant}-document.json")
    assert receipt["status"] == "succeeded"
    artifact = receipt["result"]["artifact"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["checksumSha256"]
    metadata = json.loads(
        database.execute("select metadata from library_assets where id=?", (artifact["assetId"],)).fetchone()[0]
    )
    renderer = metadata["contextualEditing"]["rendererChecks"]
    samples = renderer["geometrySamples"]
    assert len(samples) == 450
    observed_action = sum(
        any(element.get("visible") and element.get("semanticId") == "action" for element in sample["elements"])
        for sample in samples
    )
    assert observed_action == 240
    product_bounds = []
    for frame in (300, 390):
        product = [
            element["bounds"]
            for element in samples[frame]["elements"]
            if element.get("visible") and element.get("semanticId") == "package"
        ]
        assert len(product) == 1
        product_bounds.append(product[0])
    assert product_bounds[0] == product_bounds[1]

    video = cv2.VideoCapture(str(path))
    thumb_width, thumb_height = 144, 256
    contact = Image.new("RGB", (thumb_width * 8, (thumb_height + 25) * 2), "#111111")
    drawing = ImageDraw.Draw(contact)
    decoded = 0
    frames = []
    while True:
        ok, frame = video.read()
        if not ok:
            break
        if decoded % 30 == 15:
            frames.append(frame.copy())
        decoded += 1
    video.release()
    assert decoded == 450
    for index, frame in enumerate(frames):
        thumb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        thumb = ImageOps.fit(thumb, (thumb_width, thumb_height))
        x, y = index % 8 * thumb_width, index // 8 * (thumb_height + 25)
        contact.paste(thumb, (x, y))
        drawing.text((x + 5, y + thumb_height + 3), f"{index + 0.5:.1f}s", fill="white")
    contact.save(OUT / f"contact-{variant}.jpg", quality=88)

    segments = [2, 3.5, 5, 8] if variant in {"e", "g"} else [1.2, 3, 4, 6, 8]
    video = cv2.VideoCapture(str(path))
    differences = []
    for second in np.arange(0.25, 8, 0.25):
        if any(abs(second - cut) < 0.22 for cut in segments):
            continue
        pair = []
        for timestamp in (second - 0.15, second):
            video.set(cv2.CAP_PROP_POS_MSEC, float(timestamp * 1000))
            ok, frame = video.read()
            if ok:
                pair.append(cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (180, 320)))
        if len(pair) == 2:
            differences.append(float(np.mean(cv2.absdiff(*pair))))
    video.release()

    sound_tracks = [
        track
        for track in document["composition"]["mediaTimeline"]["tracks"]
        if track["kind"] == "audio" and not track["muted"]
    ]
    sound_events = [
        {
            "role": track["name"],
            "startSeconds": clip["timeline"]["startFrame"] / 30,
            "durationSeconds": clip["timeline"]["durationFrames"] / 30,
            "gainDb": clip["gainDb"],
        }
        for track in sound_tracks
        for clip in track["clips"]
    ]
    media = probe(path)
    assert float(media["format"]["duration"]) == 15
    assert {stream["codec_type"] for stream in media["streams"]} == {"video", "audio"}
    return {
        "variant": variant,
        "status": "technical_pass",
        "video": str(path),
        "durationSeconds": 15,
        "decodedFrames": decoded,
        "rendererObservedFrames": len(samples),
        "resolution": [720, 1280],
        "visibleActionFootageSeconds": observed_action / 30,
        "actionPairMedianPixelDifference": round(float(np.median(differences)), 3),
        "productPositionContinuous": product_bounds[0] == product_bounds[1],
        "soundEvents": sound_events,
        "audioObservation": metadata["audiovisualObservations"]["status"],
        "visualAudit": metadata["visualAudit"]["visualEditorial"],
        "humanReview": metadata["visualAudit"]["human"],
        "assetId": artifact["assetId"],
        "checksumSha256": artifact["checksumSha256"],
    }


def main():
    database = sqlite3.connect(OUT / "pilot.sqlite")
    variants = [evaluate(variant, database) for variant in ("g", "h")]
    database.close()
    result = {
        "schemaVersion": "res.native-hybrid-pilot-evaluation.v1",
        "technical": "passed",
        "visualQuality": "pending_human_review",
        "autonomy": "partial",
        "comparison": {
            "baseline": str(ROOT / "output/remotion-native-scene-pilot/product-story.mp4"),
            "observedChange": (
                "The 9s baseline uses still product photographs with zoom and overlaid text. "
                "Both new 15s variants show 8s of moving preparation and pouring footage, "
                "followed by a product composite over continuous serving footage."
            ),
            "reviewStatus": "qualitative_operator_observation;human_scoring_pending",
        },
        "selectedAnimatic": None,
        "humanScores": None,
        "variants": variants,
        "limitations": [
            "Planner response failed contextual plan validation; the animatics were agent directed.",
            "Gemini video generation and Lyria music returned HTTP 429; "
            "the animatics use licensed stock and CC0 audio.",
            "The genuine product reference is low resolution; commercial clearance "
            "and higher-resolution packaging remain pending.",
            "Pixel difference and recorded geometry do not substitute for normal-speed human viewing.",
        ],
    }
    (OUT / "pilot-evaluation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "technical": result["technical"],
                "variants": len(variants),
                "actionSeconds": [v["visibleActionFootageSeconds"] for v in variants],
            }
        )
    )


if __name__ == "__main__":
    main()
