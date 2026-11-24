"""Revision-bound technical review; never substitutes for editorial acceptance."""
import math


def delivery_review(tools, batch, duration, windows=(), issues=()):
    reviews = [entry.get("observation", {}) for entry in tools
               if entry.get("ok") and entry.get("name") == "review_clip"
               and entry.get("draftBatch") == batch and not entry.get("reusedToolUseId")
               and not (entry.get("input") or {}).get("assetId")]
    reviews = [review for review in reviews if review.get("source", {}).get("kind") == "native_draft"
               and review.get("source", {}).get("draftBatch") == batch]
    overview = any(review.get("visual", {}).get("sampling") == "overview"
                   and review.get("interval", {}).get("startSeconds", 1) <= 0.001
                   and review.get("interval", {}).get("endSeconds", 0) >= duration - 0.05 for review in reviews)
    spans = []
    for review in reviews:
        visual = review.get("visual", {})
        samples = visual.get("sampledSeconds", [])
        fps = visual.get("sampleFps")
        if (visual.get("nativeRateRequested") and visual.get("consecutiveOnRequestedGrid")
                and isinstance(fps, (float, int)) and math.isfinite(fps) and fps > 0 and len(samples) >= 2):
            spans.append((min(samples), max(samples) + 1 / fps))
    spans.sort()
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + 0.002:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    missing = []
    if not overview:
        missing.append("review_clip overview of the complete current draft")
    if not spans:
        missing.append("review_clip native-rate consecutive frames of the important motion")
    for window in windows:
        start, end = window["startSeconds"], window["startSeconds"] + window["durationSeconds"]
        if end > duration + 0.05 or not any(a <= start + 0.002 and b >= end - 0.002 for a, b in merged):
            missing.append(f"native-rate coverage {start:g}–{end:g} seconds on this revision")
    if not math.isfinite(duration) or duration <= 0:
        missing.append("current draft duration must be known and positive")
    if issues:
        missing.extend(str(issue) for issue in issues)
    return {"draftBatch": batch, "status": "reviewed" if not missing else "draft",
            "missing": missing, "overview": overview, "nativeCoverage": merged,
            "reviewChecksums": list(dict.fromkeys(review["source"].get("nativeChecksumSha256")
                                                   for review in reviews)),
            "editorialApproval": "pending", "perceptualAudioListening": "pending"}
