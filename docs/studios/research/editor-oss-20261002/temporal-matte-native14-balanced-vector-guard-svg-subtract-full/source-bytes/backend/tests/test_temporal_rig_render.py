"""Real affine exposure against an original polygon-area oracle."""
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

POLICY = TemporalExposureV1().model_dump(mode="json", by_alias=True)
BACKGROUND, FOREGROUND = [20, 40, 80], [220, 180, 70]
# x/y/width/height and deltas x/y/angle/scale-x/scale-y; authored pivot .5/.5.
GEOMETRY = {"outer": (20, 20, 260, 260, 15, 0, 10, -.1, .05),
            "rig": (30, 40, 160, 120, 35, 5, 20, .1, -.1),
            "hero": (16, 16, 96, 72, 40, 0, -8, 0, 0)}


def rig_direction(scope):
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene.update(id="affine-exposure", durationFrames=30, background="#142850", nativeComponents=[],
                 elements=[], motionRecipes=[])
    for target, values in GEOMETRY.items():
        x, y, width, height, dx, dy, angle, sx, sy = values
        element = {"id": target, "kind": "shape" if target == "hero" else "group", "purpose": "Affine exposure witness",
                   "x": x, "y": y, "width": width, "height": height, "originX": .5, "originY": .5,
                   "durationFrames": 30, "depthTreatment": {"opacity": {"outer": .8, "rig": .75, "hero": .5}[target]}}
        if target != "outer":
            element["parentId"] = "outer" if target == "rig" else "rig"
        if target == "hero":
            element.update(fill="#dcb446", radius=0, visualRole="hero")
        else:
            element.update(borderWidth=4 if target == "outer" else 2, borderColor="#142850")
        scene["elements"].append(element)
        tracks = []
        for prop, first, last in [("x", 0, dx), ("y", 0, dy), ("rotation", 0, angle),
                                  ("scale_x", 1, 1 + sx), ("scale_y", 1, 1 + sy)]:
            tracks.append({"targetId": target, "property": prop, "keyframes": [
                {"frame": 0, "value": first, "curve": [0, 0, 1, 1]}, {"frame": 8, "value": last},
                {"frame": 29, "value": last}]})
        if target == "rig":
            tracks.append({"targetId": target, "property": "opacity", "keyframes": [
                {"frame": 0, "value": .75, "curve": [0, 0, 1, 1]}, {"frame": 8, "value": .65},
                {"frame": 29, "value": .65}]})
        scene["motionRecipes"].append({"id": target + "-move", "version": 1, "technique": "motion_choreography",
                                       "targetIds": [target], "startFrame": 0, "endFrameExclusive": 30,
                                       "intent": "One authored affine transform per ancestor",
                                       "continuityAnchor": "Same rig",
                                       "parameters": {"tracks": tracks, "pivot": [.5, .5]},
                                       "verification": ["No double transform or border offset"]})
    scene["elements"].append({"id": "still", "kind": "shape", "purpose": "Independent alpha witness", "x": 240,
                              "y": 250, "width": 64, "height": 48, "durationFrames": 30, "fill": "#dcb446",
                              "radius": 0, "visualRole": "support", "depthTreatment": {"opacity": .4}})
    for target, start, end in ([] if scope == "control" else
                               [("rig", 0, 6), ("hero", 6, 30)] if scope == "disjoint" else
                               [("hero" if scope == "child" else "rig", 0, 30)]):
        scene["motionRecipes"].append({"id": target + "-exposure", "version": 1, "technique": "velocity_blur",
                                       "targetIds": [target], "startFrame": start, "endFrameExclusive": end,
                                       "intent": "Expose this subtree; external ancestors stay at center",
                                       "continuityAnchor": "Same rig",
                                       "parameters": {"temporalSamples": 8, "shutterDegrees": 180,
                                                      "temporalExposure": POLICY},
                                       "verification": ["Affine geometry, alpha and hold are observed"]})
    return raw


def affine(target, frame):
    x, y, width, height, dx, dy, angle, dsx, dsy = GEOMETRY[target]
    p = max(0, min(frame / 8, 1))
    theta = math.radians(angle * p)
    a, b = math.cos(theta) * (1 + dsx * p), math.sin(theta) * (1 + dsx * p)
    c, d = -math.sin(theta) * (1 + dsy * p), math.cos(theta) * (1 + dsy * p)
    return a, b, c, d, x + dx * p + width / 2 - a * width / 2 - c * height / 2, \
        y + dy * p + height / 2 - b * width / 2 - d * height / 2


def multiply(left, right):
    a, b, c, d, e, f = left
    g, h, i, j, k, m = right
    return a * g + c * h, b * g + d * h, a * i + c * j, b * i + d * j, a * k + c * m + e, b * k + d * m + f


def quadrilateral(frame, sample, scope):
    rig_time = sample if scope == "rig" else frame
    matrix = multiply(multiply(multiply(multiply(affine("outer", frame), (1, 0, 0, 1, 4, 4)),
                                         affine("rig", rig_time)), (1, 0, 0, 1, 2, 2)), affine("hero", sample))
    a, b, c, d, e, f = matrix
    points = [(a * x + c * y + e, b * x + d * y + f) for x, y in [(0, 0), (96, 0), (96, 72), (0, 72)]]
    alpha = .8 * (.75 - .1 * max(0, min(rig_time / 8, 1))) * .5
    return points, alpha


def clipped_area(points, x, y):
    polygon = points
    for axis, boundary, lower in [(0, x, True), (0, x + 2, False), (1, y, True), (1, y + 2, False)]:
        result = []
        for previous, current in zip(polygon[-1:] + polygon[:-1], polygon, strict=True):
            old_inside = previous[axis] >= boundary if lower else previous[axis] <= boundary
            inside = current[axis] >= boundary if lower else current[axis] <= boundary
            if old_inside != inside:
                t = (boundary - previous[axis]) / (current[axis] - previous[axis])
                result.append(tuple(previous[i] + t * (current[i] - previous[i]) for i in [0, 1]))
            if inside:
                result.append(current)
        polygon = result
        if not polygon:
            return 0
    return abs(sum(left[0] * right[1] - right[0] * left[1]
                   for left, right in zip(polygon, polygon[1:] + polygon[:1], strict=True))) / 2


def exposure_model(frame, scope):
    active = "rig" if scope == "disjoint" and frame < 6 else "child" if scope == "disjoint" else scope
    start, end = (0, 6) if scope == "disjoint" and frame < 6 else (6, 30) if scope == "disjoint" else (0, 30)
    low, high = max(start, frame - .25), min(end, frame + .25)
    times = [frame] if active == "control" or frame >= 10 else [low + (i + .5) * (high - low) / 8 for i in range(8)]
    return active, times, [quadrilateral(frame, sample, active) for sample in times]


def probes_for(frame, scope):
    active, times, shapes = exposure_model(frame, scope)
    points = [point for shape, _ in shapes for point in shape]
    left, right = math.floor(min(p[0] for p in points) / 2) * 2, math.ceil(max(p[0] for p in points) / 2) * 2
    top, bottom = math.floor(min(p[1] for p in points) / 2) * 2, math.ceil(max(p[1] for p in points) / 2) * 2

    def expected(x, y):
        coverage = [clipped_area(shape, x, y) / 4 for shape, _ in shapes]
        alpha = sum(cov * shape[1] for cov, shape in zip(coverage, shapes, strict=True)) / len(shapes)
        return [b + alpha * (f - b) for b, f in zip(BACKGROUND, FOREGROUND, strict=True)], sum(coverage) / len(shapes)

    edges = [(x, y) for x in range(left - 2, right + 2, 2) for y in range(top - 2, bottom + 2, 2)
             if .08 < expected(x, y)[1] < .92]
    if edges:
        selected = [edges[round(index * (len(edges) - 1) / 7)] for index in range(8)]
    else:
        # An aligned sharp control has no fractional-coverage grid cells.
        selected = [(x, y) for x in [left - 2, left, right - 2, right] for y in [top, bottom - 2]]
    center, _ = quadrilateral(frame, frame, active)
    a, b, _, d = center
    for fraction in [.3, .5, .7]:
        point = (a[0] + fraction * (b[0] - a[0]) + .5 * (d[0] - a[0]),
                 a[1] + fraction * (b[1] - a[1]) + .5 * (d[1] - a[1]))
        selected.append((int(point[0]) // 2 * 2, int(point[1]) // 2 * 2))
    selected += [(left - 4, (top + bottom) // 4 * 2), (right + 2, (top + bottom) // 4 * 2),
                 ((left + right) // 4 * 2, top - 4), ((left + right) // 4 * 2, bottom + 2)]
    return active, times, [(x, y, *expected(x, y)) for x, y in selected]


@pytest.mark.parametrize("scope", ["control", "rig", "child", "disjoint"])
def test_temporal_rig_actual_api_affine_pixels(client, project, monkeypatch, tmp_path, scope):
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline.tracks = []
        persist_contract(record, doc)
        db.commit()
    headers = {"Authorization": "Bearer " + project["token"]}
    base = f"/api/v1/studios/v1/documents/{project['document']}"
    response = client.post(base + "/editing-plans", headers={**headers, "Idempotency-Key": "rig-plan"},
                           json=rig_direction(scope))
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
        encoded = original_render(*args, **kwargs)
        shutil.copy2(args[3], intermediate)
        return encoded

    monkeypatch.setattr(graphics, "render", retaining_render)
    monkeypatch.setitem(VIDEO_RENDER_PROVIDERS, "remotion.contextual-v2", RemotionNativeContextualRenderProvider(
        graphics, VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"]))
    monkeypatch.setattr("app.tasks.execute_studio_generation.delay", lambda *_: None)
    submitted = client.post("/api/v1/studios/v1/video-renders", headers={**headers, "Idempotency-Key": "rig-render"},
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
        assert result["documentRevision"] == applied.json()["revision"] == inspection["document"]["revision"]
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        metadata = asset.object_metadata
        video = tmp_path / "rig.mp4"
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
            shutil.copy2(source, video)
        assert hashlib.sha256(video.read_bytes()).hexdigest() == result["artifact"]["checksumSha256"]
    evidence = {"scope": "actual_API_plan_apply_inspection_job_MP4_QC_independent_affine_polygon_pixels",
                "variant": scope, "measurementStatus": "in_progress", "humanReview": "pending",
                "inspection": inspection,
                "renderResult": result, "renderMetadata": metadata, "pixelChecks": [], "geometryChecks": []}
    output = None
    if directory := os.environ.get("TEMPORAL_RIG_EVIDENCE_DIR"):
        output = Path(directory) / scope
        output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video, output / "rig.mp4")
        (output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.copy2(intermediate, output / "graphics-intermediate.mp4")
    receipt = metadata["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
    assert hashlib.sha256(intermediate.read_bytes()).hexdigest() == receipt["videoSha256"]
    rgb = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True, timeout=30,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    assert len(rgb) == 30 * 320 * 320 * 3
    geometry = metadata["contextualEditing"]["rendererChecks"]["geometrySamples"]
    assert len(geometry) == 30
    failures = []
    for frame in [0, 4, 6, 7, 10, 29]:
        active, times, probes = probes_for(frame, scope)
        hero = next(item for item in geometry[frame]["elements"] if item["semanticId"] == "hero" and item["present"])
        first = frame
        if active != "control":
            exposure = hero["temporalExposure"]
            assert exposure["sampleFrames"] == pytest.approx(times)
            assert not exposure["pixelCoverageObserved"]
            first = times[0]
            assert exposure["actualSamples"] == len(times)
        polygon, _ = quadrilateral(frame, first, active)
        bounds = {"x": min(p[0] for p in polygon), "y": min(p[1] for p in polygon),
                  "width": max(p[0] for p in polygon) - min(p[0] for p in polygon),
                  "height": max(p[1] for p in polygon) - min(p[1] for p in polygon)}
        error = max(abs(hero["bounds"][key] - value) for key, value in bounds.items())
        evidence["geometryChecks"].append({"frame": frame, "expectedBounds": bounds,
                                           "observedBounds": hero["bounds"], "maximumErrorPx": error})
        if error >= .15:
            failures.append(("geometry", frame, error))
        for x, y, expected, coverage in probes:
            observed = [sum(rgb[(frame * 320 * 320 + (y + dy) * 320 + x + dx) * 3 + channel]
                            for dx in range(2) for dy in range(2)) / 4 for channel in range(3)]
            error = abs(sum((a - b) * w for a, b, w in zip(observed, expected, [.2126, .7152, .0722], strict=True)))
            evidence["pixelChecks"].append({"frame": frame, "x": x, "y": y, "expectedRgb": expected,
                                            "observedRgb": observed, "coverage": coverage, "luminanceError": error,
                                            "footprint": "aligned_2x2_yuv420p_block"})
            if error >= 8:
                failures.append(("pixels", frame, x, y, error))
    evidence["measurementStatus"] = "failed" if failures else "passed"
    evidence["failures"] = failures
    if output:
        (output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    assert not failures, failures
