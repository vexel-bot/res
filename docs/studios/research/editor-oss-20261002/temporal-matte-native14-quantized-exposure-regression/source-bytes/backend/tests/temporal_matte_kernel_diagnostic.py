"""Explicit qualification experiment; combined admission gate remains pending.

Not collected by the default suite. The retained API experiments preceded
restoration of the admission diagnostic after unresolved raster edge probes.
"""
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
from PIL import Image, ImageDraw
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

# x/y/w/h, animated dx/dy/rotation/scale-x delta/scale-y delta.
GEOMETRY = {"outer": (18, 16, 240, 260, 70, 8, 12, -.05, .1),
            "rig": (15, 18, 210, 200, 20, -4, -10, .08, -.04),
            "hero": (10, 10, 170, 150, 24, 8, 10, .05, 0),
            "mask-rig": (100, 74, 80, 96, 20, 12, -8, .1, .1),
            "matte": (0, 0, 80, 96, 10, 0, 0, 0, 0)}
VARIANTS = [("control", "external", "alpha", False), ("child", "external", "alpha", False),
            ("child", "external", "alpha", True), ("rig", "external", "alpha", False),
            ("rig", "external", "luminance", True), ("child", "common", "alpha", False),
            ("rig", "common", "luminance", False)]
FRAMES = (0, 4, 7, 8, 10, 15)


def original_mask():
    mask = Image.new("RGBA", (80, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    draw.polygon([(0, 0), (39, 0), (0, 47)], fill=(255, 255, 255, 255))
    draw.ellipse((13, 13, 29, 29), fill=(255, 255, 255, 0))
    draw.rectangle((40, 0, 79, 47), fill=(0, 0, 0, 255))
    draw.rectangle((0, 48, 39, 95), fill=(128, 128, 128, 128))
    return mask


def direction_for(asset, scope, source_branch, mode, invert):
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene.update(id="temporal-matte", durationFrames=16, background="#000000", nativeComponents=[],
                 elements=[], motionRecipes=[])
    for target, values in GEOMETRY.items():
        x, y, width, height, dx, dy, angle, sx, sy = values
        if target == "mask-rig" and source_branch == "common":
            x, y = 80, 60
        element = {"id": target, "kind": "shape" if target == "hero" else "image" if target == "matte" else "group",
                   "purpose": "Original affine matte exposure witness", "x": x, "y": y,
                   "width": width, "height": height, "durationFrames": 16, "originX": .5, "originY": .5,
                   "depthTreatment": {"opacity": {"outer": .9, "rig": .9, "hero": .85,
                                                  "mask-rig": .2, "matte": .6}[target]}}
        if target in {"rig", "hero", "matte"}:
            element["parentId"] = {"rig": "outer", "hero": "rig", "matte": "mask-rig"}[target]
        if target == "mask-rig" and source_branch == "common":
            element["parentId"] = "outer"
        if target == "rig":
            element.update(borderWidth=2, borderColor="#000000")
        if target == "hero":
            element.update(fill="#ffffff", radius=0, visualRole="hero")
        if target == "matte":
            element.update(assetId=asset, objectFit="contain")
        scene["elements"].append(element)
        tracks = [{"targetId": target, "property": prop, "keyframes": [
            {"frame": 0, "value": first, "curve": [0, 0, 1, 1]}, {"frame": 8, "value": last},
            {"frame": 15, "value": last}]} for prop, first, last in
            [("x", 0, dx), ("y", 0, dy), ("rotation", 0, angle), ("scale_x", 1, 1 + sx), ("scale_y", 1, 1 + sy)]]
        if target == "matte":
            tracks.append({"targetId": target, "property": "opacity", "keyframes": [
                {"frame": 0, "value": .6, "curve": [0, 0, 1, 1]}, {"frame": 8, "value": .9},
                {"frame": 15, "value": .9}]})
        scene["motionRecipes"].append({"id": target + "-move", "technique": "motion_choreography",
            "targetIds": [target], "startFrame": 0, "endFrameExclusive": 16,
            "intent": "Affine motion and hold", "continuityAnchor": "Same target and original pixels",
            "parameters": {"pivot": [.5, .5], "tracks": tracks}, "verification": ["Pixels retain matte identity"]})
    scene["motionRecipes"].append({"id": "world-matte", "technique": "asset_matte", "targetIds": ["hero"],
        "startFrame": 0, "endFrameExclusive": 16, "intent": "World-space original matte",
        "continuityAnchor": "Same bitmap", "parameters": {"assetMatte": {
            "sourceTargetId": "matte", "mode": mode, "invert": invert}}, "verification": ["Mask does not drift"]})
    if scope != "control":
        scene["motionRecipes"].append({"id": "local-exposure", "technique": "velocity_blur",
            "targetIds": ["hero" if scope == "child" else "rig"], "startFrame": 0, "endFrameExclusive": 16,
            "intent": "Expose local subtree while external world stays at center", "continuityAnchor": "Same matte",
            "parameters": {"temporalSamples": 8, "shutterDegrees": 180,
                           "temporalExposure": TemporalExposureV1().model_dump(mode="json", by_alias=True)},
            "verification": ["World matte and sampled target agree"]})
    return raw


def mul(left, right):
    a, b, c, d, e, f = left
    g, h, i, j, k, m = right
    return a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j, a*k+c*m+e, b*k+d*m+f


def inverse(matrix):
    a, b, c, d, e, f = matrix
    det = a*d-b*c
    return d/det, -b/det, -c/det, a/det, (c*f-d*e)/det, (b*e-a*f)/det


def point(matrix, x, y):
    a, b, c, d, e, f = matrix
    return a*x+c*y+e, b*x+d*y+f


def local(target, frame, branch):
    x, y, w, h, dx, dy, degrees, dsx, dsy = GEOMETRY[target]
    if target == "mask-rig" and branch == "common":
        x, y = 80, 60
    p = max(0, min(frame / 8, 1))
    angle = math.radians(degrees * p)
    a, b = math.cos(angle)*(1+dsx*p), math.sin(angle)*(1+dsx*p)
    c, d = -math.sin(angle)*(1+dsy*p), math.cos(angle)*(1+dsy*p)
    return a, b, c, d, x+dx*p+w/2-a*w/2-c*h/2, y+dy*p+h/2-b*w/2-d*h/2


def worlds(frame, sample, scope, branch):
    outer = local("outer", frame, branch)
    rig = mul(outer, local("rig", sample if scope == "rig" else frame, branch))
    target = mul(mul(rig, (1, 0, 0, 1, 2, 2)), local("hero", sample, branch))
    source = mul(local("mask-rig", frame, branch), local("matte", frame, branch))
    if branch == "common":
        source = mul(outer, source)
    return target, source


def times_for(frame, scope):
    if scope == "control" or frame >= 10:
        return [frame]
    low, high = max(0, frame-.25), min(16, frame+.25)
    return [low+(i+.5)*(high-low)/8 for i in range(8)]


def raster_value(mask, u, v, mode):
    # The SVG image viewport clips coverage. Within it, texture interpolation
    # clamps edge texels; it does not fade into fictitious transparent texels.
    if not (0 <= u < mask.width and 0 <= v < mask.height):
        return 0
    u, v = u-.5, v-.5
    left, top = math.floor(u), math.floor(v)
    total = 0
    for x in (left, left+1):
        for y in (top, top+1):
            red, green, blue, alpha = mask.getpixel((max(0, min(mask.width-1, x)), max(0, min(mask.height-1, y))))
            value = alpha/255
            if mode == "luminance":
                value *= (.2126*red+.7152*green+.0722*blue)/255
            total += value*(1-abs(u-x))*(1-abs(v-y))
    return total


def expected_pixel(mask, frame, scope, branch, mode, invert, x, y, grid=8):
    alpha = .9*.9*.85
    source_opacity = .6+.3*min(frame/8, 1)
    matrices = [(inverse(target), inverse(source)) for sample in times_for(frame, scope)
                for target, source in [worlds(frame, sample, scope, branch)]]
    value = 0
    # Rasterize content and the clipped mask as separate alpha images, then
    # multiply per pixel. Multiplying continuous geometry before rasterization
    # incorrectly removes the second antialiased silhouette at mask bounds.
    # Neither DOM matrices nor observed pixels define this original oracle.
    for target, source in matrices:
        for px in range(2):
            for py in range(2):
                content_coverage = mask_coverage = 0
                for dx in range(grid):
                    for dy in range(grid):
                        wx, wy = x+px+(dx+.5)/grid, y+py+(dy+.5)/grid
                        tx, ty = point(target, wx, wy)
                        if not (0 <= tx < 170 and 0 <= ty < 150):
                            continue
                        content_coverage += 1
                        u, v = point(source, wx, wy)
                        coverage = raster_value(mask, u, v, mode)*source_opacity
                        mask_coverage += 1-coverage if invert else coverage
                value += content_coverage/grid**2 * mask_coverage/grid**2 * alpha*255
    return value/(len(matrices)*4)


def probe_points(frame, scope, branch):
    target, source = worlds(frame, frame, scope, branch)
    source_uv = [(4, 4), (20, 12), (20, 30), (39, 8), (40, 8), (42, 8), (60, 8),
                 (8, 60), (20, 60), (39, 60), (45, 60), (60, 60), (-2, 20), (0, 20),
                 (1, 20), (79, 20), (80, 20), (82, 20), (20, -2), (20, 0), (20, 94), (20, 96), (20, 98)]
    authored = [point(source, u, v) for u, v in source_uv]
    authored += [point(target, u, v) for u, v in [(-1, 50), (0, 50), (1, 50), (169, 50), (170, 50),
                                                (50, -1), (50, 0), (50, 149), (50, 150)]]
    return sorted({(int(x)//2*2, int(y)//2*2) for x, y in authored if 2 <= x < 317 and 2 <= y < 317})


@pytest.mark.parametrize("scope,branch,mode,invert", VARIANTS)
def test_temporal_matte_actual_api_pixels(client, project, monkeypatch, tmp_path, scope, branch, mode, invert):
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
    if os.environ.get("TEMPORAL_MATTE_BASELINE") == "1":
        assert scope != "control" and response.status_code == 422, response.text
        assert "temporal_matte_moving_external_ancestor_pending" in response.text
        assert output is not None
        (output / "negative.json").write_text(json.dumps({"scope": "actual_API_native12_plan_rejection",
            "httpStatus": response.status_code, "response": response.json(), "publishedArtifact": False}, indent=2),
            encoding="utf-8")
        return
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
    evidence = {"scope": "actual_API_plan_apply_inspection_job_MP4_QC_independent_authored_PNG_raster",
        "variant": name, "humanReview": "pending", "measurementStatus": "in_progress",
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
