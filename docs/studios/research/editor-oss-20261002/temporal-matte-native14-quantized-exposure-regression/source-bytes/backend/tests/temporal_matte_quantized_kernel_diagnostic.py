"""Explicit API qualification for the independently calibrated affine raster profile.

Preserves the historical diagnostic and its verdicts. This new profile uses
unchanged authored fixtures, frames, probes and error limits. It is specific to
the pinned four-bit SwiftShader rasterizer, large affine quads and PNG mattes;
it does not qualify perspective, degenerate meshes or arbitrary paths.
"""
# ruff: noqa: F811
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project

from app.database import SessionLocal
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.providers.studios.remotion_render import RemotionNativeContextualRenderProvider, RemotionNativeGraphicsProvider
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.jobs import execute_job_once
from tests.temporal_matte_kernel_diagnostic import (
    FRAMES,
    VARIANTS,
    direction_for,
    inverse,
    mul,
    original_mask,
    probe_points,
    times_for,
    worlds,
)

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
REFERENCE = ROOT / "scripts/validation/editor-temporal-matte-quantized-reference.py"
spec = importlib.util.spec_from_file_location("quantized_affine_png_reference_v1", REFERENCE)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
expected_pixel = reference.expected_pixel


def reference_profile():
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    raster = ROOT / "scripts/validation/editor-temporal-matte-quad-raster-reference.py"
    geometry = ROOT / "scripts/validation/editor-temporal-matte-uniform-analysis.py"
    runtime_path = STUDY / "swiftshader-subpixel-runtime.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    # Use the declared WebGL precision, never observed output pixels, to select
    # the grid. The runtime receipt also seals the renderer and browser bytes.
    assert runtime["values"]["subpixelBits"] == 4
    browser = (ROOT / "workers/remotion-benchmark/node_modules/.remotion/chrome-headless-shell/win64" /
               "chrome-headless-shell-win64/chrome-headless-shell.exe")
    assert sha(browser) == runtime["browserSha256"]
    quad_path = STUDY / "temporal-matte-quad-raster-conformance.json"
    textured_path = STUDY / "temporal-matte-textured-source-conformance.json"
    quad = json.loads(quad_path.read_text(encoding="utf-8"))
    textured = json.loads(textured_path.read_text(encoding="utf-8"))
    assert quad["referenceScriptSha256"] == textured["rasterReferenceSha256"] == sha(raster)
    assert quad["geometryScriptSha256"] == sha(geometry)
    assert textured["referenceScriptSha256"] == sha(REFERENCE)
    assert quad["calibrationCases"] == 6 and len(quad["records"]) == 28
    assert len(textured["records"]) == 7
    assert sum(row["pixelCount"] for row in textured["records"]) == 716800
    assert all(not row["failedProbesAtOriginalThreshold"] for row in quad["records"] + textured["records"])
    return {"id": "swiftshader4_affine_png_v1", "referenceSha256": sha(REFERENCE),
            "rasterReferenceSha256": sha(raster), "geometryReferenceSha256": sha(geometry),
            "runtimeReceiptSha256": sha(runtime_path), "quadConformanceSha256": sha(quad_path),
            "texturedConformanceSha256": sha(textured_path), "pixelErrorLimitExclusive": 8,
            "matrixErrorLimitExclusive": .002, "historicalDiagnosticChanged": False}


@pytest.mark.parametrize("scope,branch,mode,invert", VARIANTS)
def test_temporal_matte_quantized_actual_api_pixels(
    client, project, monkeypatch, tmp_path, scope, branch, mode, invert,
):
    profile = reference_profile()
    name = f"{scope}-{branch}-{mode}-{'inverted' if invert else 'normal'}"
    directory = os.environ.get("TEMPORAL_MATTE_EVIDENCE_DIR")
    output = Path(directory) / name if directory else None
    if output:
        output.mkdir(parents=True, exist_ok=True)
    mask = original_mask()
    image = tmp_path / "original-matte.png"
    mask.save(image)
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline.tracks = []
        persist_contract(record, doc)
        db.commit()
    headers = {"Authorization": "Bearer " + project["token"]}
    with image.open("rb") as stream:
        uploaded = client.post("/api/v1/studios/v1/editing/resources/upload", headers=headers,
            data={"workspace_id": project["workspace"], "title": "Original temporal matte fixture",
                  "metadata": json.dumps({"kind": "image", "usageEvidence": "Original synthetic fixture"})},
            files={"file": (image.name, stream, "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    asset_id = uploaded.json()["id"]
    base = f"/api/v1/studios/v1/documents/{project['document']}"
    response = client.post(base + "/editing-plans", headers={**headers, "Idempotency-Key": "temporal-matte-plan"},
                           json=direction_for(asset_id, scope, branch, mode, invert))
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["status"] == "ready", plan["blockers"]
    applied = client.post(base + f"/editing-plans/{plan['id']}/apply", headers=headers,
                          json={"expectedPlanRevision": plan["revision"]})
    assert applied.status_code == 200, applied.text
    inspection = client.get(base + "/editor/inspection?frame=4", headers=headers).json()
    graphics = RemotionNativeGraphicsProvider("node", "ffmpeg", 180)
    original_render = graphics.render
    intermediate = tmp_path / "graphics-intermediate.mp4"

    def retaining_render(*args, **kwargs):
        result = original_render(*args, **kwargs)
        shutil.copy2(args[3], intermediate)
        return result

    monkeypatch.setattr(graphics, "render", retaining_render)
    monkeypatch.setitem(VIDEO_RENDER_PROVIDERS, "remotion.contextual-v2", RemotionNativeContextualRenderProvider(
        graphics, VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"]))
    monkeypatch.setattr("app.tasks.execute_studio_generation.delay", lambda *_: None)
    submitted = client.post("/api/v1/studios/v1/video-renders",
        headers={**headers, "Idempotency-Key": "temporal-matte-render"},
        json={"workspaceId": project["workspace"], "documentId": project["document"],
              "expectedDocumentRevision": applied.json()["revision"], "expectedDocumentVersion": 1,
              "contextualPlanId": plan["id"], "provider": "remotion.contextual-v2",
              "output": {"width": 320, "height": 320, "fps": 30, "quality": "high"}})
    assert submitted.status_code == 202, submitted.text
    deadline = time.monotonic()+120
    while _active(_read(lease_path())):
        if time.monotonic() >= deadline:
            pytest.skip("A live operation owns heavy-media capacity")
        time.sleep(1)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, submitted.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        result = job.result_payload
        assert result["documentRevision"] == inspection["document"]["revision"] == applied.json()["revision"]
        assert result["qualityEvaluation"]["status"] == "passed"
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        metadata = asset.object_metadata
        video = tmp_path / "matte-exposure.mp4"
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
            shutil.copy2(source, video)
    assert hashlib.sha256(video.read_bytes()).hexdigest() == result["artifact"]["checksumSha256"]
    evidence = {"scope": "actual_API_plan_apply_inspection_job_MP4_QC_quantized_affine_PNG_v1",
        "pixelReference": profile, "variant": name, "humanReview": "pending", "measurementStatus": "in_progress",
        "inspection": inspection, "renderResult": result, "renderMetadata": metadata,
        "maskAssetSha256": hashlib.sha256(image.read_bytes()).hexdigest(), "pixelChecks": [], "matrixChecks": []}
    if output:
        shutil.copy2(video, output / "matte-exposure.mp4")
        shutil.copy2(intermediate, output / "graphics-intermediate.mp4")
        shutil.copy2(image, output / "original-matte.png")
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                         check=True, capture_output=True, timeout=30).stdout
    assert len(raw) == 16*320*320*3
    geometry = metadata["contextualEditing"]["rendererChecks"]["geometrySamples"]
    failures = []
    for frame in FRAMES:
        times = times_for(frame, scope)
        hero = next(e for e in geometry[frame]["elements"] if e["semanticId"] == "hero" and e["present"])
        if scope != "control":
            assert hero["temporalExposure"]["actualSamples"] == len(times)
            assert hero["temporalExposure"]["sampleFrames"] == pytest.approx(times)
        target, source = worlds(frame, times[0], scope, branch)
        matrix = mul(inverse(target), source)
        observed = hero["assetMatte"]["sourceToTargetMatrix"]
        error = max(abs(a-b) for a, b in zip(matrix, observed, strict=True))
        evidence["matrixChecks"].append({"frame": frame, "expected": matrix, "observed": observed,
                                        "maximumError": error})
        if error >= .002:
            failures.append(("matrix", frame, error))
        for x, y in probe_points(frame, scope, branch):
            expected = expected_pixel(mask, frame, scope, branch, mode, invert, x, y)
            rgb = [sum(raw[(frame*320*320+(y+dy)*320+x+dx)*3+c]
                       for dx in range(2) for dy in range(2))/4 for c in range(3)]
            error = max(abs(channel-expected) for channel in rgb)
            evidence["pixelChecks"].append({"frame": frame, "x": x, "y": y, "expectedChannel": expected,
                                            "observedRgb": rgb, "maximumChannelError": error})
            if error >= 8:
                failures.append(("pixel", frame, x, y, error))
    evidence["failures"] = failures
    evidence["measurementStatus"] = "failed" if failures else "passed"
    if output:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    assert not failures, failures
