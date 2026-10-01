"""Read every rendered frame; record objective QC separately from human review."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.musetalk_fixed_camera_pilot import cycle_index, validate_render_probe
from scripts.run_musetalk_avatar_pilot import _probe, _sha256, _write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--normalized-source", type=Path, required=True)
    args = parser.parse_args()
    import cv2
    import numpy as np

    video = args.video.resolve()
    manifest = json.loads(video.with_suffix(".result.json").read_text(encoding="utf-8"))
    if manifest["checksumSha256"] != _sha256(video):
        raise ValueError("render_integrity_failed")
    validate_render_probe(_probe(video), manifest["frameCount"])
    source_cap = cv2.VideoCapture(str(args.normalized_source.resolve()))
    source_frames = []
    while True:
        ok, frame = source_cap.read()
        if not ok:
            break
        source_frames.append(cv2.resize(frame, (180, 320), interpolation=cv2.INTER_AREA))
    source_cap.release()
    if len(source_frames) != 300:
        raise ValueError("source_preparation_frame_count_failed")
    mask = np.ones((320, 180), dtype=bool)
    mask[25:190, 15:155] = False  # conservatively exclude head and blend margin
    cap = cv2.VideoCapture(str(video))
    background_errors, lumas = [], []
    sampled, transitions = [], []
    sample_indices = set(np.linspace(0, manifest["frameCount"] - 1, 9).round().astype(int).tolist())
    transition_indices = set()
    for center in [299, 598, 897]:
        transition_indices.update([center - 2, center, center + 2])
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, (180, 320), interpolation=cv2.INTER_AREA)
        expected = source_frames[cycle_index(index, len(source_frames))]
        background_errors.append(float(np.abs(small.astype(np.float32) - expected.astype(np.float32))[mask].mean()))
        lumas.append(float(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).mean()))
        if index in sample_indices or index in transition_indices:
            thumb = cv2.resize(frame, (360, 640))
            cv2.rectangle(thumb, (0, 608), (360, 640), (0, 0, 0), -1)
            cv2.putText(
                thumb,
                f"frame {index} | {index / 25:.2f}s",
                (8, 630),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
            )
            if index in sample_indices:
                sampled.append(thumb)
            if index in transition_indices:
                transitions.append(thumb)
        index += 1
    cap.release()
    if index != manifest["frameCount"]:
        raise ValueError("render_full_decode_incomplete")

    def save_sheet(items, suffix):
        if not items:
            return
        items += [np.zeros_like(items[0])] * (-len(items) % 3)
        sheet = np.vstack([np.hstack(items[i : i + 3]) for i in range(0, len(items), 3)])
        if not cv2.imwrite(str(video.with_suffix(suffix)), sheet):
            raise RuntimeError("contact_sheet_write_failed")

    save_sheet(sampled, ".contact.jpg")
    save_sheet(transitions, ".transitions.jpg")
    result = {
        "schemaVersion": "studio.private-avatar-objective-qc.v1",
        "renderChecksumSha256": manifest["checksumSha256"],
        "framesDecoded": index,
        "expectedFrames": manifest["frameCount"],
        "decodeComplete": True,
        "minimumFrameMeanLuma": min(lumas),
        "maximumFrameMeanLuma": max(lumas),
        "nearBlackFrameCount": sum(value < 3 for value in lumas),
        "outsideHeadMeanAbsolutePixelError": float(np.mean(background_errors)),
        "outsideHeadMaximumFrameMeanAbsolutePixelError": max(background_errors),
        "outsideHeadErrorThreshold": 3.0,
        "outsideHeadPreservationPassed": max(background_errors) < 3.0,
        "measurement": (
            "180x320 area-downsampled BGR; static exclusion x=15:155,y=25:190; "
            "lossy codec differences expected"
        ),
        "finiteMeasurements": all(math.isfinite(value) for value in background_errors + lumas),
        "subjectiveLipSyncApproved": False,
        "humanNaturalnessApproved": False,
        "publicationState": "private_review",
    }
    _write_json(video.with_suffix(".qc.json"), result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
