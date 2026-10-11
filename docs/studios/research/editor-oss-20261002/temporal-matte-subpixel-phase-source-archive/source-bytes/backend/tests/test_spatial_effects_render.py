"""Authored spatial effects through real API/jobs and an independent Gaussian oracle."""
# ruff: noqa: F811
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_remotion_native import native_direction

from app.database import SessionLocal
from app.domain.studios.motion_recipes import TemporalExposureV1
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.providers.studios.remotion_render import RemotionNativeContextualRenderProvider, RemotionNativeGraphicsProvider
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.jobs import execute_job_once

BOXES = {"sharp": (32, 32, 56, 48), "hard": (32, 112, 48, 48), "zero": (200, 112, 48, 48),
         "soft": (200, 32, 32, 48), "blur": (32, 220, 48, 48), "combo": (200, 220, 32, 48),
         "animated": (128, 112, 32, 48)}
SHADOWS = {"hard": {"x": 32, "y": 12, "blur": 0, "color": "#ff0000", "opacity": .5},
           "zero": {"x": 32, "y": 12, "blur": 0, "color": "#0000ff", "opacity": 0},
           "soft": {"x": 32, "y": 12, "blur": 4, "color": "#00ff00", "opacity": .5},
           "combo": {"x": 32, "y": 12, "blur": 4, "color": "#0000ff", "opacity": .5}}


def spatial_direction(variant):
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene.update(id="spatial-effects", durationFrames=30, background="#000000", nativeComponents=[],
                 motionRecipes=[], elements=[])
    for target, (x, y, width, height) in BOXES.items():
        element = {"id": target, "kind": "shape", "purpose": "Canonical spatial effect witness", "x": x, "y": y,
                   "width": width, "height": height, "durationFrames": 30, "fill": "#ffffff", "radius": 0,
                   "visualRole": "hero" if target == "sharp" else "support"}
        if variant != "control":
            if target in SHADOWS:
                element["shadow"] = SHADOWS[target]
            if target in {"blur", "combo"}:
                element["depthTreatment"] = {"blurPx": 4}
            if target == "animated":
                element["animations"] = [{"property": "blur_px", "keyframes": [
                    {"frame": 0, "value": 0, "easing": "linear"}, {"frame": 1, "value": 16},
                    {"frame": 29, "value": 16}]}]
        scene["elements"].append(element)
    if variant == "exposure":
        scene["motionRecipes"] = [{"id": "expose-blur", "technique": "velocity_blur", "targetIds": ["animated"],
                                   "startFrame": 0, "endFrameExclusive": 30,
                                   "intent": "Expose the animated spatial blur",
                                   "continuityAnchor": "Same rectangle and authored blur track",
                                   "parameters": {"temporalSamples": 8, "shutterDegrees": 180,
                                                  "temporalExposure": TemporalExposureV1().model_dump(
                                                      mode="json", by_alias=True)},
                                   "verification": ["Spatial blur is sampled at the same canonical time"]}]
    return raw


def gaussian_pixel_axis(x, start, length, sigma):
    """Average convolution of a unit interval across [x,x+2], analytically."""
    if sigma == 0:
        return max(0, min(x + 2, start + length) - max(x, start)) / 2

    def primitive(value, edge):
        z = (value - edge) / sigma
        cdf = (1 + math.erf(z / math.sqrt(2))) / 2
        return (value - edge) * cdf + sigma * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    return (primitive(x + 2, start) - primitive(x, start)
            - primitive(x + 2, start + length) + primitive(x, start + length)) / 2


def rectangle_alpha(target, x, y, sigma, offset=(0, 0)):
    left, top, width, height = BOXES[target]
    return gaussian_pixel_axis(x, left + offset[0], width, sigma) * gaussian_pixel_axis(
        y, top + offset[1], height, sigma)


def sample_frames(frame, variant, target):
    if variant != "exposure" or target != "animated" or frame >= 4:
        return [frame]
    low, high = max(0, frame - .25), min(30, frame + .25)
    return [low + (i + .5) * (high - low) / 8 for i in range(8)]


def sample_rgba(target, sample, x, y, variant):
    def point_alpha(sigma, offset=(0, 0)):
        left, top, width, height = BOXES[target]
        if sigma == 0:
            return float(left + offset[0] <= x < left + offset[0] + width
                         and top + offset[1] <= y < top + offset[1] + height)
        def axis(value, start, length):
            return (math.erf((value - start) / (sigma * math.sqrt(2)))
                    - math.erf((value - start - length) / (sigma * math.sqrt(2)))) / 2
        return axis(x, left + offset[0], width) * axis(y, top + offset[1], height)

    blur = 0 if variant == "control" else 4 if target in {"blur", "combo"} else (
        16 * min(max(sample, 0), 1) if target == "animated" else 0)
    alpha = point_alpha(blur)
    shadow = SHADOWS.get(target) if variant != "control" else None
    shadow_alpha, color = 0, [0, 0, 0]
    if shadow:
        shadow_alpha = shadow["opacity"] * point_alpha(math.hypot(blur, shadow["blur"]), (shadow["x"], shadow["y"]))
        color = [int(shadow["color"][i:i + 2], 16) for i in [1, 3, 5]]
    return [255 * alpha + c * shadow_alpha * (1 - alpha) for c in color], alpha + shadow_alpha * (1 - alpha)


def expected_rgb(frame, x, y, variant):
    # Original four-point Gauss-Legendre integration per axis across the 2x2 block.
    nodes = [.1388636884059474, .6600189564151437, 1.3399810435848563, 1.8611363115940526]
    weights = [.1739274225687269, .3260725774312731, .3260725774312731, .1739274225687269]
    times = sample_frames(frame, variant, "animated")
    rgb = [0., 0., 0.]
    for dx, wx in zip(nodes, weights, strict=True):
        for dy, wy in zip(nodes, weights, strict=True):
            for sample in times:
                pixel = [0., 0., 0.]
                for target in BOXES:
                    premultiplied, alpha = sample_rgba(target, sample, x + dx, y + dy, variant)
                    pixel = [a + b * (1 - alpha) for a, b in zip(premultiplied, pixel, strict=True)]
                for channel in range(3):
                    rgb[channel] += pixel[channel] * wx * wy / len(times)
    return rgb


PROBES = {"sharp": [(26, 54), (32, 54), (54, 54), (88, 54)],
          "hard": [(42, 132), (90, 148), (108, 162), (92, 172), (120, 148)],
          "zero": [(210, 132), (258, 148), (272, 162)],
          "soft": [(208, 54), (240, 68), (246, 88), (260, 68), (266, 68), (274, 68)],
          "blur": [(24, 242), (28, 242), (32, 242), (54, 242), (76, 242), (82, 242), (32, 216)],
          "combo": [(196, 242), (206, 242), (230, 246), (238, 252), (260, 252), (266, 252), (274, 252)],
          "animated": [(120, 134), (124, 134), (128, 134), (142, 134), (158, 134), (164, 134)]}


@pytest.mark.parametrize("variant", ["control", "spatial", "exposure"])
def test_spatial_effects_actual_api_and_gaussian_pixels(client, project, monkeypatch, tmp_path, variant):
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline.tracks = []
        persist_contract(record, doc)
        db.commit()
    headers = {"Authorization": "Bearer " + project["token"]}
    base = f"/api/v1/studios/v1/documents/{project['document']}"
    response = client.post(base + "/editing-plans", headers={**headers, "Idempotency-Key": "spatial-plan"},
                           json=spatial_direction(variant))
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["status"] == "ready", plan["blockers"]
    applied = client.post(base + f"/editing-plans/{plan['id']}/apply", headers=headers,
                          json={"expectedPlanRevision": plan["revision"]})
    assert applied.status_code == 200, applied.text + json.dumps(plan.get("manifest", {}).get("visualAudit"))
    inspection = client.get(base + "/editor/inspection?frame=4", headers=headers).json()
    graphics = RemotionNativeGraphicsProvider("node", "ffmpeg", 180)
    original_render = graphics.render
    intermediate = tmp_path / "graphics-intermediate.mp4"

    def retaining_render(*args, **kwargs):
        encoded = original_render(*args, **kwargs)
        shutil.copy2(args[3], intermediate)
        return encoded

    monkeypatch.setattr(graphics, "render", retaining_render)
    monkeypatch.setitem(VIDEO_RENDER_PROVIDERS, "remotion.contextual-v2", RemotionNativeContextualRenderProvider(
        graphics, VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"]))
    monkeypatch.setattr("app.tasks.execute_studio_generation.delay", lambda *_: None)
    submitted = client.post("/api/v1/studios/v1/video-renders",
                            headers={**headers, "Idempotency-Key": "spatial-render"},
                            json={"workspaceId": project["workspace"], "documentId": project["document"],
                                  "expectedDocumentRevision": applied.json()["revision"], "expectedDocumentVersion": 1,
                                  "contextualPlanId": plan["id"], "provider": "remotion.contextual-v2",
                                  "output": {"width": 320, "height": 320, "fps": 30, "quality": "high"}})
    assert submitted.status_code == 202, submitted.text
    deadline = time.monotonic() + 120
    while _active(_read(lease_path())):
        if time.monotonic() >= deadline:
            pytest.skip("Live local operation occupies heavy-media capacity")
        time.sleep(1)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, submitted.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        result = job.result_payload
        assert result["qualityEvaluation"]["status"] == "passed"
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        metadata = asset.object_metadata
        video = tmp_path / "spatial.mp4"
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
            shutil.copy2(source, video)
        assert hashlib.sha256(video.read_bytes()).hexdigest() == result["artifact"]["checksumSha256"]
    assert result["documentRevision"] == applied.json()["revision"] == inspection["document"]["revision"]
    remotion_receipt = metadata["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
    assert hashlib.sha256(intermediate.read_bytes()).hexdigest() == remotion_receipt["videoSha256"]
    rgb = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True, timeout=30,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    assert len(rgb) == 30 * 320 * 320 * 3
    checks, failures, temporal_checks = [], [], []
    geometry = metadata["contextualEditing"]["rendererChecks"]["geometrySamples"]
    for frame in [0, 1, 4, 8, 29]:
        if variant == "exposure":
            element = next(item for item in geometry[frame]["elements"] if item["semanticId"] == "animated")
            exposure = element["temporalExposure"]
            assert exposure["sampleFrames"] == pytest.approx(sample_frames(frame, variant, "animated"))
            assert exposure["actualSamples"] == len(sample_frames(frame, variant, "animated"))
            assert not exposure["pixelCoverageObserved"]
            temporal_checks.append({"frame": frame, "exposure": exposure})
        for target, points in PROBES.items():
            for x, y in points:
                expected = expected_rgb(frame, x, y, variant)
                observed = [sum(rgb[(frame * 320 * 320 + (y + dy) * 320 + x + dx) * 3 + channel]
                                for dx in range(2) for dy in range(2)) / 4 for channel in range(3)]
                luma = abs(sum((a - b) * weight for a, b, weight in zip(
                    observed, expected, [.2126, .7152, .0722], strict=True)))
                channel = max(abs(a - b) for a, b in zip(observed, expected, strict=True))
                checks.append({"target": target, "frame": frame, "x": x, "y": y, "expectedRgb": expected,
                               "observedRgb": observed, "luminanceError": luma, "maximumChannelError": channel})
                if luma >= 8 or channel >= 12:
                    failures.append({"target": target, "frame": frame, "x": x, "y": y,
                                     "luminanceError": luma, "maximumChannelError": channel})
    discriminating_probe = None
    if variant == "exposure":
        probe = next(p for p in checks if p["frame"] == 0 and p["target"] == "animated" and p["x"] == 128)
        center = expected_rgb(0, probe["x"], probe["y"], "spatial")
        difference = abs(sum((a - b) * w for a, b, w in zip(
            probe["observedRgb"], center, [.2126, .7152, .0722], strict=True)))
        discriminating_probe = {"frame": 0, "x": probe["x"], "y": probe["y"],
                                "centerFrameExpectedRgb": center, "exposedObservedRgb": probe["observedRgb"],
                                "luminanceDifferenceFromUnexposedCenter": difference}
        if difference <= 12:
            failures.append({"exposureNotPixelDistinguishableFromCenterFrame": difference})
    if directory := os.environ.get("SPATIAL_EFFECTS_EVIDENCE_DIR"):
        output = Path(directory) / variant
        output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video, output / "spatial.mp4")
        shutil.copy2(intermediate, output / "graphics-intermediate.mp4")
        (output / "evidence.json").write_text(json.dumps({
            "scope": "actual_API_plan_apply_inspection_job_MP4_QC_independent_gaussian_pixels", "variant": variant,
            "measurementStatus": "failed" if failures else "passed", "humanReview": "pending",
            "inspection": inspection, "renderResult": result, "renderMetadata": metadata,
            "pixelChecks": checks, "temporalChecks": temporal_checks,
            "discriminatingExposureProbe": discriminating_probe,
            "failures": failures}, ensure_ascii=False, indent=2), encoding="utf-8")
    assert not failures, failures
