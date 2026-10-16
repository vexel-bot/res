"""Verify retained actual UI/API evidence and decoded revision movement."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"
EVIDENCE = DIRECTORY / "spatial-inspection-browser"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


sources = read(EVIDENCE / "qualified-sources.json")
assert all(sha(ROOT / name) == digest for name, digest in sources.items()), "Inspection source drift"
origin = read(EVIDENCE / "runtime-origin.json")
assert all(sha(ROOT / name) == digest for name, digest in origin["sources"].items()), "UI/API source drift"
assert origin["api"] == "http://127.0.0.1:8000" and origin["frontend"] == "http://127.0.0.1:3317"
assert not origin["sharedProcessesStopped"] and not origin["uiAPIMocked"]
typescript = read(EVIDENCE / "typescript-check.json")
assert typescript["exitCode"] == 0 and typescript["uiSourceSha256"] == sources["src/studios/EditorInspectionPanel.tsx"]
native = read(DIRECTORY / "spatial-effects-native12-sources.json")
assert all(sha(ROOT / name) == digest for name, digest in native["sources"].items()), "Native renderer drift"
fixture = read(EVIDENCE / "fixture.json")
before = fixture["inspection"]
after = {frame: read(EVIDENCE / f"inspection-frame-{frame}.json") for frame in (0, 1, 4)}
assert before["document"]["revision"] == before["planRevision"] == 2
assert all(item["document"]["revision"] == item["planRevision"] == 3 for item in after.values())
assert before["documentDigest"] != after[0]["documentDigest"]
assert before["graphDigest"] != after[0]["graphDigest"]
assert before["hashes"]["executableComposition"] != after[0]["hashes"]["executableComposition"]
assert before["versions"] == after[0]["versions"]
history = after[0]["history"]
assert len(history) == 1 and history[0]["previousDocumentRevision"] == 2
assert history[0]["documentRevision"] == history[0]["planRevision"] == 3
assert history[0]["documentDigest"] == after[0]["documentDigest"]
assert history[0]["appliedChanges"] == [{"kind": "set_recipe_keyframe", "sceneId": "spatial-effects",
    "recipeId": "inspect-sharp", "targetId": "sharp", "property": "x",
    "keyframe": {"frame": 0, "value": 4, "curve": [.2, 0, .2, 1]}}]
assert "human_visual_review_required" in history[0]["pending"]


def layers(inspection):
    return {layer["name"]: layer for page in inspection["document"]["composition"]["pages"]
            for layer in page["layers"] if layer["name"] in {"sharp", "hard", "zero", "soft", "blur", "combo", "animated"}}


original_layers, current_layers = layers(before), layers(after[0])
assert len(original_layers) == len(current_layers) == 7
for name, layer in original_layers.items():
    assert layer == current_layers[name], f"Authored layer changed unexpectedly: {name}"
assert current_layers["combo"]["properties"]["editorialDepth"]["blurPx"] == 4
assert current_layers["combo"]["properties"]["editorialShadow"] == {
    "x": 32, "y": 12, "blur": 4, "color": "#0000ff", "opacity": .5}
assert current_layers["zero"]["properties"]["editorialShadow"]["opacity"] == 0
for frame, item in after.items():
    assert item["frame"] == frame
    track = next(t for t in item["tracks"] if t["targetLayerId"] == current_layers["animated"]["id"]
                 and t["property"] == "blur_px")
    assert track["evaluatedLocalValue"] == (0 if frame == 0 else 16)
assert next(t for t in after[0]["tracks"] if t["targetLayerId"] == current_layers["sharp"]["id"]
            and t["property"] == "position_x")["evaluatedLocalValue"] == 4

observations = read(EVIDENCE / "ui-observations.json")
checks = {item["name"]: item for item in observations["checks"]}
required = {"combo-static", "transparent-shadow", "animated-center-0", "animated-center-1",
            "animated-center-4", "isolated-render-revision2", "edited-revision3-stale-render",
            "visible-render-revision3-combo", "visible-animated-revision3-frame4"}
assert required <= checks.keys()
for item in checks.values():
    assert item["status"] == "passed" and all(phrase in item["text"] for phrase in item["expected"])
assert all(checks[name]["observationBasis"] == "visible_panel_DOM" for name in required)
stale = checks["edited-revision3-stale-render"]["text"]
assert "A revisão inspecionada ainda não tem MP4 associado neste painel." in stale
assert "Render associado à revisão 2" not in stale
assert observations["humanReview"] == "pending"

renders, pixels = [], []
for revision, inspection in ((2, before), (3, after[0])):
    evidence = read(EVIDENCE / f"render-revision-{revision}.json")
    result, metadata = evidence["renderResult"], evidence["renderMetadata"]
    video = EVIDENCE / f"preview-revision-{revision}.mp4"
    assert result["documentId"] == fixture["documentId"]
    assert result["workspaceId"] == fixture["workspaceId"]
    assert result["documentRevision"] == evidence["snapshotRevision"] == revision
    assert result["providerVersion"] == "4.0.527-native.12"
    assert result["qualityEvaluation"]["status"] == "passed"
    assert evidence["requestOutput"]["quality"] == "draft"
    assert sha(video) == result["artifact"]["checksumSha256"]
    assert metadata["contextualEditing"]["manifest"]["hashes"] == inspection["hashes"]
    graphics = metadata["contextualEditing"]["rendererChecks"]["graphics"]
    receipt = graphics["remotionReceipt"]
    assert receipt["graphicsBackend"] == "chromium_swangle"
    assert receipt["encodeQuality"] == "draft" and receipt["videoCrf"] == 28
    geometry = {item["frame"]: item for item in graphics["geometrySamples"]}
    element = next(e for e in geometry[0]["elements"] if e["layerId"] == current_layers["sharp"]["id"])
    assert element["bounds"]["x"] == (32 if revision == 2 else 36)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "pipe:1"], check=True, capture_output=True).stdout
    assert len(raw) == 30 * 320 * 320 * 3
    for frame in (0, 29):
        for x in (34, 38, 90):
            offset = (frame * 320 * 320 + 54 * 320 + x) * 3
            rgb = list(raw[offset:offset + 3])
            white = x == 38 or (x == 34 and (revision == 2 or frame == 29)) or (x == 90 and revision == 3 and frame == 0)
            assert min(rgb) > 220 if white else max(rgb) < 30, (revision, frame, x, rgb)
            pixels.append({"revision": revision, "frame": frame, "x": x, "y": 54,
                           "rgb": rgb, "expected": "white" if white else "black"})
    assert evidence["humanReview"] == "pending"
    renders.append({"revision": revision, "jobId": result["jobId"], "checksum": sha(video),
                    "quality": "draft", "qc": "passed", "renderDurationMs": result["renderDurationMs"],
                    "geometryXAtFrame0": element["bounds"]["x"]})
assert renders[0]["checksum"] != renders[1]["checksum"]
report = {"schemaVersion": "res.spatial-inspection-receipt.v1", "generatedAt": datetime.now(UTC).isoformat(),
          "sources": sources, "sourceDrift": False, "nativeRendererDrift": False,
          "runtimeOrigin": origin, "typescript": typescript,
          "documentId": fixture["documentId"], "revisions": [2, 3], "commandId": history[0]["commandId"],
          "uiObservations": len(checks), "requiredObservations": sorted(required),
          "renders": renders, "pixelProbes": pixels, "humanReview": "pending",
          "scope": "Actual UI normal login and command, existing API pipeline, two draft MP4s; no mocks",
          "limitations": ["Pixel probes verify revision movement; not a new Gaussian qualification",
                          "Material preview/canvas in VideoStudio is not the rendered composition preview",
                          "Commercial human comparison and three fresh autonomy briefs remain pending"]}
(DIRECTORY / "spatial-inspection-receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": "passed", "revisions": [2, 3], "actualMP4s": len(renders),
                  "decodedPixelProbes": len(pixels), "sourceDrift": False, "humanReview": "pending"}))
