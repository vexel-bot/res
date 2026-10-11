"""Original PNG matte through canonical API/job/MP4, with independent pixel oracle."""

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
from test_asset_matte import matte_direction
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


@pytest.mark.parametrize("mode,invert", [("alpha", False), ("alpha", True), ("luminance", False), ("luminance", True)])
def test_asset_matte_real_api_job_and_intermediate_alpha_pixels(
    client, project, monkeypatch, tmp_path, mode, invert, wide=False, fit="contain", animated=False
):
    mask = Image.new("RGBA", (256 if wide else 128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    draw.polygon([(0, 0), (63, 0), (0, 63)], fill=(255, 255, 255, 255))
    draw.ellipse((13, 13, 27, 27), fill=(255, 255, 255, 0))
    draw.rectangle((64, 0, 127, 63), fill=(0, 0, 0, 255))
    draw.rectangle((0, 64, 63, 127), fill=(128, 128, 128, 128))
    image = tmp_path / "original-matte.png"
    if animated:
        mask.save(image, save_all=True, append_images=[Image.new("RGBA", mask.size)], duration=[100, 100], loop=0)
    else:
        mask.save(image)
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline.tracks = []
        persist_contract(record, doc)
        db.commit()
    headers = {"Authorization": "Bearer " + project["token"]}
    with image.open("rb") as file:
        uploaded = client.post(
            "/api/v1/studios/v1/editing/resources/upload",
            headers=headers,
            data={
                "workspace_id": project["workspace"],
                "title": "Original arbitrary matte fixture",
                "metadata": json.dumps({"kind": "image", "usageEvidence": "Original synthetic matte fixture"}),
            },
            files={"file": (image.name, file, "image/png")},
        )
    assert uploaded.status_code == 200, uploaded.text
    asset_id = uploaded.json()["id"]
    direction = matte_direction(asset_id, mode, invert).model_dump(mode="json", by_alias=True)
    next(element for element in direction["scenes"][0]["elements"] if element["id"] == "matte")["objectFit"] = fit
    base = f"/api/v1/studios/v1/documents/{project['document']}"
    response = client.post(
        base + "/editing-plans", headers={**headers, "Idempotency-Key": "asset-matte-plan"}, json=direction
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["status"] == "ready", plan["blockers"]
    applied = client.post(
        base + f"/editing-plans/{plan['id']}/apply", headers=headers, json={"expectedPlanRevision": plan["revision"]}
    )
    assert applied.status_code == 200, applied.text
    inspection = client.get(base + "/editor/inspection?frame=4", headers=headers).json()
    monkeypatch.setitem(
        VIDEO_RENDER_PROVIDERS,
        "remotion.contextual-v2",
        RemotionNativeContextualRenderProvider(
            RemotionNativeGraphicsProvider("node", "ffmpeg", 180),
            VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"],
        ),
    )
    monkeypatch.setattr("app.tasks.execute_studio_generation.delay", lambda *_: None)
    response = client.post(
        "/api/v1/studios/v1/video-renders",
        headers={**headers, "Idempotency-Key": "asset-matte-render"},
        json={
            "workspaceId": project["workspace"],
            "documentId": project["document"],
            "expectedDocumentRevision": applied.json()["revision"],
            "expectedDocumentVersion": 1,
            "contextualPlanId": plan["id"],
            "provider": "remotion.contextual-v2",
            "output": {"width": 320, "height": 320, "fps": 30},
        },
    )
    assert response.status_code == 202, response.text
    wait_until = time.monotonic() + 120
    while _active(_read(lease_path())):
        if time.monotonic() >= wait_until:
            pytest.skip("Another live local operation occupies heavy-media capacity")
        time.sleep(1)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        execute_job_once(db, job)
        if animated:
            assert job.status in {"failed", "retrying"}
            assert "hybrid_asset_matte_animated_png_pending" in (job.error_message or "")
            assert not job.result_payload
            if directory := os.environ.get("ASSET_MATTE_EVIDENCE_DIR"):
                target = Path(directory) / "animated-negative"
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(image, target / "original-animated-matte.png")
                (target / "evidence.json").write_text(
                    json.dumps(
                        {
                            "scope": "actual_API_plan_apply_job_animated_PNG_rejection",
                            "jobId": str(job.id),
                            "status": job.status,
                            "errorCode": job.error_code,
                            "errorMessage": job.error_message,
                            "publishedArtifact": False,
                            "sourceSha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                            "correction": "Supply a static PNG matte; APNG is unsupported by asset_matte v1.",
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            return
        assert job.status == "succeeded", job.error_message
        result = job.result_payload
        assert result["providerVersion"] == RemotionNativeContextualRenderProvider.version
        assert result["documentRevision"] == applied.json()["revision"]
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        metadata = asset.object_metadata
        samples = metadata["contextualEditing"]["rendererChecks"]["geometrySamples"]
        assert len(samples) == 15
        for frame in [0, 2, 4, 7, 12, 13, 14]:
            hero = next(item for item in samples[frame]["elements"] if item["semanticId"] == "hero")
            assert ("assetMatte" in hero) == (2 <= frame < 13)
            if 2 <= frame < 13:
                observed = hero["assetMatte"]
                assert observed["assetId"] == asset_id and observed["mode"] == mode and observed["invert"] == invert
                assert observed["sourceLocalOpacity"] == 0.5 and not observed["pixelCoverageObserved"]
                part = min(frame / 7, 1)
                source_angle, target_angle = math.radians(90 * part), math.radians(-5 * part)
                scale, delta = 1 + 0.2 * part, source_angle - target_angle
                target_x = 20 + 4 * (math.cos(target_angle) - math.sin(target_angle))
                target_y = 20 + 10 * part + 4 * (math.sin(target_angle) + math.cos(target_angle))
                dx = 80 + 80 * part + 10 * scale * math.cos(source_angle) - target_x
                dy = 80 + 10 * scale * math.sin(source_angle) - target_y
                expected_matrix = [
                    scale * math.cos(delta),
                    scale * math.sin(delta),
                    -scale * math.sin(delta),
                    scale * math.cos(delta),
                    dx * math.cos(target_angle) + dy * math.sin(target_angle),
                    -dx * math.sin(target_angle) + dy * math.cos(target_angle),
                ]
                assert observed["sourceToTargetMatrix"] == pytest.approx(expected_matrix, abs=0.002)
            source_observation = next(item for item in samples[frame]["elements"] if item["semanticId"] == "matte")
            assert source_observation["matteSourceOnly"] and not source_observation["visible"]
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as output:
            assert hashlib.sha256(output.read_bytes()).hexdigest() == result["artifact"]["checksumSha256"]
            pixels = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(output), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                capture_output=True,
                check=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout
            assert len(pixels) == 15 * 320 * 320 * 3
            checks = []
            # Independent spatial oracle uses the authored source parent's
            # rotation/scale/translation, not the worker's matrices or DOM bbox.
            for frame in [0, 2, 4, 7, 12, 13, 14]:
                part = min(frame / 7, 1)
                angle, scale = math.radians(90 * part), 1 + 0.2 * part
                for name, u, v in [
                    # The wide bitmap is reduced by half. Keep the coverage
                    # probe away from the hole/edge filtering in that fixture.
                    ("white-triangle", 42 if wide else 30, 8 if wide else 12),
                    ("hole", 20, 20),
                    ("opaque-black", 90, 20),
                    ("semi-gray", 55 if wide and fit == "cover" else 25, 75 if wide and fit == "cover" else 95),
                    ("transparent", 90, 80),
                ]:
                    local_u, local_v = (u * 0.5, 32 + v * 0.5) if wide else (u, v)
                    if wide and fit == "cover":
                        local_u, local_v = u - 64, v
                    x = round(80 + 80 * part + scale * ((local_u + 10) * math.cos(angle) - local_v * math.sin(angle)))
                    y = round(80 + scale * ((local_u + 10) * math.sin(angle) + local_v * math.cos(angle)))
                    # Confirm each probe is inside the transformed target.
                    target_angle = math.radians(-5 * part)
                    target_x = 20 + 4 * (math.cos(target_angle) - math.sin(target_angle))
                    target_y = 20 + 10 * part + 4 * (math.sin(target_angle) + math.cos(target_angle))
                    dx, dy = x - target_x, y - target_y
                    tx = dx * math.cos(target_angle) + dy * math.sin(target_angle)
                    ty = -dx * math.sin(target_angle) + dy * math.cos(target_angle)
                    assert 2 < tx < 278 and 2 < ty < 278, (frame, name, tx, ty)
                    red, green, blue, alpha = mask.getpixel((u, v))
                    value = alpha / 255 * 0.5
                    if mode == "luminance":
                        value *= (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
                    if wide and fit == "cover" and not 64 <= u < 192:
                        value = 0  # Cover crops the bitmap at its source viewport.
                    if invert:
                        value = 1 - value
                    expected = 204 * value if 2 <= frame < 13 else 204
                    offset = (frame * 320 * 320 + y * 320 + x) * 3
                    observed = tuple(pixels[offset : offset + 3])
                    assert all(abs(channel - expected) < 12 for channel in observed), (frame, name, observed, expected)
                    checks.append(
                        {
                            "frame": frame,
                            "point": name,
                            "sourcePx": [u, v],
                            "worldPx": [x, y],
                            "expectedChannel": expected,
                            "observedRgb": observed,
                        }
                    )
            # Outside the image's footprint, inversion must also expose target.
            offset = (4 * 320 * 320 + 240 * 320 + 250) * 3
            outside = tuple(pixels[offset : offset + 3])
            assert all(abs(channel - (204 if invert else 0)) < 12 for channel in outside)
            if wide:
                # At frame 7, source element point (40, 10) maps to the
                # contain letterbox, but to an opaque PNG pixel with cover.
                offset = (7 * 320 * 320 + 140 * 320 + 148) * 3
                letterbox = tuple(pixels[offset : offset + 3])
                expected_box = 102 if fit == "cover" else 0
                assert all(abs(channel - expected_box) < 12 for channel in letterbox)
            if directory := os.environ.get("ASSET_MATTE_EVIDENCE_DIR"):
                target = Path(directory) / (
                    "alpha-wide-" + fit if wide else mode + ("-inverted" if invert else "-normal")
                )
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output, target / "matte.mp4")
                shutil.copy2(image, target / "original-matte.png")
                (target / "evidence.json").write_text(
                    json.dumps(
                        {
                            "scope": "actual_API_plan_apply_inspection_job_MP4_QC_decoded_pixels",
                            "humanReview": "pending",
                            "inspection": inspection,
                            "renderResult": result,
                            "renderMetadata": metadata,
                            "maskAssetSha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                            "pixelChecks": checks,
                            "outsideFootprintRgb": outside,
                            "mode": mode,
                            "invert": invert,
                            "sourceBitmapSize": list(mask.size),
                            "wideContainFixture": wide and fit == "contain",
                            "sourceObjectFit": fit,
                            "aspectProbeRgb": letterbox if wide else None,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )


def test_asset_matte_preserves_wide_png_aspect_and_letterbox(client, project, monkeypatch, tmp_path):
    test_asset_matte_real_api_job_and_intermediate_alpha_pixels(
        client,
        project,
        monkeypatch,
        tmp_path,
        "alpha",
        False,
        wide=True,
    )


def test_asset_matte_cover_crops_in_source_space(client, project, monkeypatch, tmp_path):
    test_asset_matte_real_api_job_and_intermediate_alpha_pixels(
        client,
        project,
        monkeypatch,
        tmp_path,
        "alpha",
        False,
        wide=True,
        fit="cover",
    )


def test_asset_matte_actual_job_rejects_animated_png_without_publication(client, project, monkeypatch, tmp_path):
    test_asset_matte_real_api_job_and_intermediate_alpha_pixels(
        client,
        project,
        monkeypatch,
        tmp_path,
        "alpha",
        False,
        animated=True,
    )
