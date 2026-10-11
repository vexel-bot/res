"""Confer current source, real UI gating/clocks, native job and displayed pixels."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/temporal-matte-composition-preview"
OLD = OUT.parent / "temporal-matte-inspection-browser"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ui(stage):
    raw = read(OUT / f"ui-{stage}.json")
    assert raw["success"] and raw["error"] is None
    result = raw["data"]["result"]
    assert result["url"] == "http://127.0.0.1:3000/content/draft/edit?mode=video"
    return result


freeze = read(OUT / "current-sources.json")
assert all(sha(ROOT / name) == value for name, value in freeze["sources"].items())
prior = read(OUT / "prior-sources.json")
assert sha(OLD / "roundtrip-verification.json") == prior["priorRoundtripSha256"]
assert all(sha(OUT / "prior-bytes" / name) == value for name, value in prior["sources"].items())
assert sha(ROOT / "backend/tests/temporal_matte_kernel_diagnostic.py") == freeze["sources"]["backend/tests/temporal_matte_kernel_diagnostic.py"]

pending = ui("pending-revision4")
assert pending["video"] is None and pending["overlayCount"] == 0
assert "A revisão 4 ainda precisa de render" in pending["stageText"]
inherited = ui("inherited-rig-frame4-pending")
assert inherited["compositionFrame"] == "4" and inherited["video"] is None
assert "Exposição herdada do rig: rig" in inherited["inspectorText"]
assert "Opacidade da fonte no frame 4: 0.75." in inherited["inspectorText"]
assert "ainda não tem MP4 associado" in inherited["inspectorText"]
plan = read(OUT / "rig-plan.json")
assert plan["scope"] == "real_API_typed_plan_not_UI_command" and plan["document"]["revision"] == 4
exposure = next(r for r in plan["request"]["scenes"][0]["motionRecipes"] if r["technique"] == "velocity_blur")
assert exposure["targetIds"] == ["rig"]

pixel_comparisons = []
for revision, directory, stages in [(3, OLD, [0, 4, 15]), (4, OUT, [0, 4, 15])]:
    receipt = read(directory / f"render-revision-{revision}.json")
    result, snapshot, metadata = receipt["renderResult"], receipt["snapshot"], receipt["renderMetadata"]
    assert result["documentRevision"] == snapshot["revision"] == revision
    assert result["documentId"] == snapshot["documentId"] == plan["document"]["documentId"]
    assert result["documentVersion"] == snapshot["version"]
    assert result["providerVersion"] == "4.0.527-native.14" and result["qualityEvaluation"]["status"] == "passed"
    raw_snapshot = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(raw_snapshot).hexdigest() == metadata["documentSnapshotSha256"]
    file = directory / f"preview-revision-{revision}.mp4"
    assert sha(file) == result["artifact"]["checksumSha256"]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(file), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 320, 320, 3)
    assert len(frames) == 16
    for frame in stages:
        observed = ui(f"existing-revision3-frame{frame}" if revision == 3 else f"rendered-revision4-frame{frame}")
        assert "320 × 320 · 30 fps" in observed["toolbar"] and observed["overlayCount"] == 0
        assert f"MP4 da revisão {revision}" in observed["stageText"]
        assert result["artifact"]["checksumSha256"] in observed["stageText"]
        video = observed["video"]
        assert video and video["readyState"] >= 2 and not video["seeking"] and video["paused"]
        assert video["width"] == video["height"] == 320 and video["objectFit"] == "contain"
        assert abs(video["currentTime"] - frame / 30) < 0.001
        assert abs(observed["frameRect"]["width"] / observed["frameRect"]["height"] - 1) < 0.001
        if frame:
            assert observed["compositionFrame"] == str(frame)
            assert observed["inspectorVideo"]["src"] == video["src"]
            assert abs(observed["inspectorVideo"]["currentTime"] - video["currentTime"]) < 0.001
        for pixel in observed["pixels"]:
            reference = frames[frame, pixel["y"], pixel["x"]].astype(int)
            error = int(np.abs(reference - pixel["rgb"]).max())
            # Independent decode vs browser color conversion, not a geometry oracle.
            assert error <= 4, (revision, frame, pixel, reference.tolist())
            pixel_comparisons.append({"revision": revision, "frame": frame, "x": pixel["x"], "y": pixel["y"],
                                      "maxChannelError": error})

new_receipt = read(OUT / "render-revision-4.json")
assert new_receipt["scope"] == "actual_UI_submitted_job_existing_worker"
inspected = read(OUT / "inspection-revision-4-frame-4.json")
assert inspected["document"]["composition"] == new_receipt["snapshot"]["composition"]
loaded = ui("rendered-revision4-frame4")
assert "Exposição herdada do rig: rig" in loaded["inspectorText"]
assert "Render associado à revisão 4" in loaded["inspectorText"]
playback = ui("playback-observation")
assert playback["before"]["centerPaused"] and playback["before"]["inspectorPaused"]
assert not playback["afterCenterButton"]["centerPaused"] and playback["afterCenterButton"]["inspectorPaused"]
assert playback["afterInspectorPlayEvent"]["centerPaused"] and not playback["afterInspectorPlayEvent"]["inspectorPaused"]
assert not playback["afterCenterResumeButton"]["centerPaused"] and playback["afterCenterResumeButton"]["inspectorPaused"]
assert all(sha(ROOT / name) == value for name, value in freeze["sources"].items())
receipt = {"scope": "fixture_specific_real_composition_preview_and_inherited_exposure", "status": "passed",
    "verifiedAt": datetime.now(UTC).isoformat(), "sourceFreezeSha256": sha(OUT / "current-sources.json"),
    "frozenSources": len(freeze["sources"]), "pixelComparisons": pixel_comparisons,
    "maxBrowserDecodeChannelError": max(p["maxChannelError"] for p in pixel_comparisons),
    "jobId": new_receipt["renderResult"]["jobId"], "mp4Sha256": new_receipt["renderResult"]["artifact"]["checksumSha256"],
    "evidence": {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "verification.json"},
    "limitations": ["Square synthetic 320x320 fixture; other aspect ratios and long source cuts not browser-qualified here.",
        "Player arbitration observed on a silent fixture; no new audio listening qualification.",
        "Revision-4 plan applied through the real API; only the render request was submitted by the UI.",
        "Displayed pixels compared to independent FFmpeg decode; this is not aesthetic or raster-oracle approval.",
        "Human four-axis review, blind preference and new-brief autonomy remain pending."]}
target = OUT / "verification.json"
assert not target.exists(), "Preserve the sealed verification"
target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: receipt[k] for k in ["status", "frozenSources", "maxBrowserDecodeChannelError", "jobId"]}))
