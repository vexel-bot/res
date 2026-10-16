"""Verify retained real UI/API revisions and an authored MP4 displacement.

This reads receipts and decodes retained files. It submits no job or command.
Draft encoding is checked for a large geometric consequence, not against the
high-quality raster oracle or a human aesthetic score.
"""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/temporal-matte-inspection-browser"
HERO = "ed2-dc4fb9af60c130fbb12fd888"
SOURCE = "ed2-e59dfae8dda971673bcc05cf"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ui(stage):
    data = read(f"ui-{stage}.json")
    assert data["success"] and data["error"] is None
    observed = data["data"]["result"]
    assert observed["inspectorVisible"] and observed["scope"] == "actual_browser_DOM_no_API_mock"
    assert observed["url"] == "http://127.0.0.1:3000/content/draft/edit?mode=video"
    return observed


freeze = read("qualified-sources.json")
assert len(freeze["sources"]) == 57
assert all(sha(ROOT / name) == digest for name, digest in freeze["sources"].items())
fixture = read("fixture.json")
asset_sha = sha(OUT / "original-matte.png")
source = ui("source-frame4")
assert source["selectedLayer"] == SOURCE and source["compositionFrame"] == "4"
assert any(row[0] == "opacity" and row[1] == "0.75 ratio" for row in source["tracks"])
source_parent = ui("source-parent-frame4")
assert source_parent["compositionFrame"] == "4" and "opacidade 0.2" in source_parent["inspectorText"]
for stage, frame, opacity in [("before-frame7", 7, "0.8625"), ("before-hold10", 10, "0.9")]:
    observed = ui(stage)
    assert observed["selectedLayer"] == HERO and observed["compositionFrame"] == str(frame)
    assert f"Opacidade da fonte no frame {frame}: {opacity}." in observed["maskText"]
    assert asset_sha in observed["maskText"] and "inversão: sim" in observed["maskText"]
    assert "Pai da fonte: mask-rig" in observed["maskText"]

changed = ui("changed-hero-revision3-frame0")
assert "Revisão 3 · plano 3" in changed["inspectorText"] and changed["video"] is None
assert "ainda não tem MP4 associado" in changed["inspectorText"]
assert changed["tracks"][0][0:2] == ["position_x", "12 pixels"]
before = read("inspection-revision-2-frame-0.json")
after = read("inspection-revision-3-frame-0.json")
assert before["document"]["documentId"] == after["document"]["documentId"] == fixture["documentId"]
assert before["document"]["revision"] == 2 and after["document"]["revision"] == 3
assert before["documentDigest"] != after["documentDigest"]
assert before["graphDigest"] != after["graphDigest"]
assert before["hashes"]["executableComposition"] != after["hashes"]["executableComposition"]
command = after["history"][0]
assert command["previousDocumentRevision"] == 2 and command["documentRevision"] == 3
assert command["appliedChanges"] == [{"kind": "set_recipe_keyframe", "sceneId": "temporal-matte",
    "recipeId": "hero-move", "targetId": "hero", "property": "x",
    "keyframe": {"frame": 0, "value": 12.0, "curve": [0.0, 0.0, 1.0, 1.0]}}]
assert [r for r in before["recipes"] if r["id"] != "hero-move"] == [
    r for r in after["recipes"] if r["id"] != "hero-move"]

renders, decoded = [], []
for revision in [2, 3]:
    receipt = read(f"render-revision-{revision}.json")
    result, snapshot, metadata = receipt["renderResult"], receipt["snapshot"], receipt["renderMetadata"]
    inspected = read(f"inspection-revision-{revision}-frame-0.json")
    assert result["documentId"] == snapshot["documentId"] == fixture["documentId"]
    assert result["documentRevision"] == snapshot["revision"] == revision
    assert result["documentVersion"] == snapshot["version"] == inspected["document"]["version"]
    assert result["provider"] == "remotion.contextual-v2" and result["providerVersion"] == "4.0.527-native.14"
    assert result["qualityEvaluation"]["status"] == "passed" and result["framesRendered"] == 16
    assert receipt["requestOutput"]["quality"] == "draft"
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == metadata["documentSnapshotSha256"]
    assert snapshot["composition"] == inspected["document"]["composition"]
    assert metadata["sourceAssetBindings"] == [{"assetId": fixture["matteAssetId"],
        "checksumSha256": asset_sha, "role": "canonical-source"}]
    file = OUT / f"preview-revision-{revision}.mp4"
    assert sha(file) == result["artifact"]["checksumSha256"]
    observed = ui(f"rendered-revision{revision}-frame4")
    assert observed["selectedLayer"] == HERO and observed["compositionFrame"] == "4"
    assert f"Render associado à revisão {revision}" in observed["inspectorText"]
    assert result["artifact"]["checksumSha256"] in observed["inspectorText"]
    assert "versão 4.0.527-native.14" in observed["inspectorText"]
    video = observed["video"]
    # Revision 2 was retained at HAVE_METADATA before its seek finished.
    # Only revision 3 has a retained fully loaded browser frame/screenshot.
    assert video and video["readyState"] >= 1 and video["paused"]
    if revision == 3:
        assert video["readyState"] >= 2
    assert video["videoWidth"] == video["videoHeight"] == 320
    assert abs(video["currentTime"] - 4 / 30) < 0.001
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(file), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 320, 320, 3)
    assert len(frames) == 16
    decoded.append(frames)
    renders.append({"revision": revision, "jobId": result["jobId"], "mp4Sha256": sha(file),
                    "snapshotSha256": metadata["documentSnapshotSha256"]})
assert renders[0]["jobId"] != renders[1]["jobId"]
assert renders[0]["mp4Sha256"] != renders[1]["mp4Sha256"]
# Authored frame-0 geometry: outer (18,16), rig (15,18), border 2,
# hero base (10,10), original X=0 / new X=12: left 45 / 57. The
# external matte starts around X=100; inverse coverage is white here.
# A two-pixel block at (50,60) leaves the shape; (64,60) stays inside.
leaving = [float(frames[0, 60:62, 50:52].mean()) for frames in decoded]
interior = [float(frames[0, 60:62, 64:66].mean()) for frames in decoded]
assert leaving[0] > 150 and leaving[1] < 10 and leaving[0] - leaving[1] > 100
assert all(value > 150 for value in interior) and abs(interior[0] - interior[1]) < 10
assert all(sha(ROOT / name) == digest for name, digest in freeze["sources"].items())
receipt = {"scope": "fixture_specific_actual_UI_API_MP4_revision_roundtrip", "verifiedAt": datetime.now(UTC).isoformat(),
           "status": "passed", "frozenSources": 57, "sourceFreezeSha256": sha(OUT / "qualified-sources.json"),
           "verifierSha256": sha(Path(__file__)), "commandId": command["commandId"], "renders": renders,
           "originalAssetSha256": asset_sha, "frame0LeavingBlockMean": leaving, "frame0InteriorBlockMean": interior,
           "evidence": {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "roundtrip-verification.json"},
           "limitations": ["Draft CRF 28; large authored displacement only, no high-quality oracle claim.",
               "The center material preview is not the canonical renderer; inspected MP4 is in the review panel.",
               "Source parent opacity is observed, not changed in this browser fixture.",
               "HMR reloaded the page; stale MP4 absence was observed after recovery, not continuously across the command.",
               "Revision 2 DOM capture has metadata and requested seek at readyState 1; only revision 3 has a retained loaded frame screenshot.",
               "Inherited rig exposure display has not been browser-qualified in this child-scope fixture.",
               "Human audiovisual review, blind preference and new-brief autonomy remain pending."]}
target = OUT / "roundtrip-verification.json"
assert not target.exists(), "Keep the retained verification intact"
target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: receipt[key] for key in ["status", "frozenSources", "frame0LeavingBlockMean", "frame0InteriorBlockMean"]}))
