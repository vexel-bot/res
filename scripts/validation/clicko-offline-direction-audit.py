"""Replay sampling and checkpoint policies against saved Clicko evidence."""

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import file_digest
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw, ImageStat
from io import BytesIO

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.services.studios import craft_claude_review as review  # noqa: E402
from app.services.studios import craft_history as history  # noqa: E402
from app.services.studios.craft_review import _metadata  # noqa: E402


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def sample_report(video, state, output):
    metadata = _metadata(video, float("inf"))
    duration = metadata["durationSeconds"]
    source = {"startSeconds": 0, "durationSeconds": duration}
    operation_keys = {"full-batch40-a-0-7.6", "blind-compare-b40-vs-b25-full"}
    window = (3.8, 4.0)
    prior = []
    for operation in state["operations"]:
        if operation.get("operationKey") not in operation_keys:
            continue
        observed = operation["result"]["observedMedia"]["A"]
        prior.append({"operationKey": operation["operationKey"], "fps": observed["sampling"]["fps"],
                      "mediaSha256": operation["request"]["checksumSha256"],
                      "total": len(observed["timestamps"]),
                      "inPreImpactWindow": [t for t in observed["timestamps"] if window[0] <= t < window[1]]})
    focused = {"startSeconds": 3.5, "durationSeconds": 1.2}
    series = []
    for fps in (1.7, 6, 30):
        result = review.frames(video, focused, source, {"fps": fps, "maximumSide": 720})
        series.append(result)
    sheet = Image.new("RGB", (960, 606), "#141414")
    draw = ImageDraw.Draw(sheet)
    for row, result in enumerate(series):
        y = row * 202
        draw.text((6, y + 5), f'{result["sampling"]["fps"]} fps, focused replay, same source and resolution', fill="white")
        picked = [(t, f) for t, f in zip(result["timestamps"], result["frames"], strict=True) if window[0] <= t < window[1]]
        if not picked:
            draw.text((6, y + 40), "No sampled frame in [3.8 s, 4.0 s)", fill="white")
        for column, (time, frame) in enumerate(picked):
            with Image.open(BytesIO(frame)) as image:
                image.thumbnail((115, 152))
                sheet.paste(image, (column * 150 + 6, y + 32))
            draw.text((column * 150 + 6, y + 184), f"{time:.3f}s (grid)", fill="white")
    sheet.save(output / "amostragem-gota.jpg", quality=92)
    return {"sourceSha256": sha(video), "sourceFps": metadata["fps"], "durationSeconds": duration,
            "preImpactWindow": list(window), "historicalReceipts": prior,
            "offlineReplay": [{"sampling": s["sampling"], "interval": focused, "timestamps": s["timestamps"],
                "inPreImpactWindow": [t for t in s["timestamps"] if window[0] <= t < window[1]]} for s in series],
            "limitations": "Requested output grid, not independent decoded source PTS or perceptual grading."}


def motion_comparison(video, baseline):
    window = {"startSeconds": 11.15, "durationSeconds": 1.3}
    result = {}
    for label, path in (("candidate", video), ("baseline", baseline)):
        source = {"startSeconds": 0, "durationSeconds": _metadata(path, float("inf"))["durationSeconds"]}
        extracted = review.frames(path, window, source, {"fps": 30, "maximumSide": 720})
        frames = [Image.open(BytesIO(data)).convert("L") for data in extracted["frames"]]
        distances = [ImageStat.Stat(ImageChops.difference(a, b)).mean[0] for a, b in zip(frames, frames[1:])]
        result[label] = {"sourceSha256": sha(path), "frameCount": len(frames),
                         "meanAdjacentLumaDifference": round(sum(distances) / len(distances), 4),
                         "endToEndLumaDifference": round(ImageStat.Stat(ImageChops.difference(frames[0], frames[-1])).mean[0], 4)}
    return {"interval": window, "fps": 30, "maximumSide": 720, "values": result,
            "limitations": "Luma differences include noise and grading. They do not prove subject motion or editorial quality."}


def checkpoint_report(result):
    saved = deepcopy(result)
    batch = result["draft"]["batches"]
    context = {"instruction": "Offline replay of a saved revision", "directorContext": result["directorContext"]}
    # The last full inspection can belong to an earlier revision. Replay it on
    # its recorded revision rather than falsely binding it to the delivered batch.
    inspection = result.get("nativeInspection")
    if inspection:
        batch = inspection["draftBatch"]
    legacy = history.compact_messages(context, {}, batch, result)
    compact = history.compact_messages({**context, "recoverableEvidenceMode": True}, {}, batch, result)
    before, after = (json.loads(value[0]["content"][1]["text"]) for value in (legacy, compact))
    for key in ("directorContext", "nativeObservationIndex", "reviewArtifactIndex", "materialSearches", "recentFailures"):
        assert before[key] == after[key], key
    assert result == saved
    sizes = {key: len(history.encoded(value).encode()) for key, value in before.items()}
    previous = 0
    accepted, delayed = [], []
    for entry in result.get("contextRenewals", []):
        # Replay the new cooldown on recorded accepted events only. This is
        # not a counterfactual generation or a prediction of model behavior.
        turn = entry["turn"]
        pressure = (entry.get("beforeTokens") or 0) >= 240_000 or entry["beforeBytes"] >= 12_000_000
        if turn - previous >= 8 or pressure or entry["reason"] != "context_growth":
            accepted.append(turn)
            previous = turn
        else:
            delayed.append(turn)
    return {"historicalAcceptedRenewals": len(accepted) + len(delayed), "cooldownReplayKept": len(accepted),
            "cooldownReplayDelayed": len(delayed), "checkpointBatch": batch,
            "beforeCheckpointBytes": len(legacy[0]["content"][1]["text"].encode()),
            "afterCheckpointBytes": len(compact[0]["content"][1]["text"].encode()),
            "largestFieldsBefore": dict(sorted(sizes.items(), key=lambda entry: entry[1], reverse=True)[:6]),
            "preservationChecks": ["directorContext", "nativeObservationIndex", "reviewArtifactIndex",
                                   "materialSearches", "recentFailures", "originalResultUnchanged"],
            "limitations": "Historical outcomes held fixed. Delayed eligibility does not imply avoided charges."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--candidate-review-video", type=Path)
    parser.add_argument("--baseline-video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = load(args.evidence)["result"]
    state = load(args.state)
    before = sha(args.video)
    if bool(args.candidate_review_video) != bool(args.baseline_video):
        parser.error("Supply both historical A/B videos to compare their motion")
    if args.baseline_video:
        candidate_sha, baseline_sha = sha(args.candidate_review_video), sha(args.baseline_video)
        comparison = next(o for o in state["operations"] if o.get("operationKey") == "blind-compare-b40-vs-b25-full")
        if (candidate_sha != comparison["request"]["checksumSha256"]
                or baseline_sha != comparison["request"]["comparisonMedia"]["checksumSha256"]):
            raise ValueError("Input hash differs from the historical A/B receipt")
    args.output.mkdir(parents=True, exist_ok=False)
    sampling = sample_report(args.video, state, args.output)
    if args.baseline_video:
        sampling["motionControl"] = motion_comparison(args.candidate_review_video, args.baseline_video)
        assert sha(args.candidate_review_video) == candidate_sha and sha(args.baseline_video) == baseline_sha
    assert sha(args.video) == before
    report = {"schemaVersion": "clicko.audit.evidence.v1", "draftBatch": result["draft"]["batches"],
              "claudeCallsInAudit": 0, "sourcePreserved": True, "sampling": sampling,
              "compaction": checkpoint_report(result),
              "logSummary": {"models": dict(Counter(t["model"] for t in result["turns"])),
                  "directorEstimatedUsd": result["measuredCostUsd"],
                  "evaluationEstimatedUsd": result["directorOperations"]["measuredCostUsd"],
                  "tools": dict(Counter(t["name"] for t in result["tools"])),
                  "failedTools": dict(Counter(t["name"] for t in result["tools"] if not t.get("ok")))}}
    (args.output / "audit-packet.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": "completed", "compaction": report["compaction"]}))


if __name__ == "__main__":
    main()
