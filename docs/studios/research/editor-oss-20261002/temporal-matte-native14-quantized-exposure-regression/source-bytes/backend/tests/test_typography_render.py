"""Canonical Unicode typography through actual API, local job, fonts and MP4."""

# ruff: noqa: F811
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_typography_units import typography_direction

from app.database import SessionLocal
from app.domain.studios.motion_recipes import TemporalExposureV1
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.providers.studios.remotion_render import RemotionNativeContextualRenderProvider, RemotionNativeGraphicsProvider
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.jobs import execute_job_once


@pytest.mark.parametrize("variant", ["unicode", "wrapped_words"])
@pytest.mark.parametrize("temporal", [False, True])
def test_typography_real_api_job_mp4_and_complete_hold(client, project, monkeypatch, variant, temporal):
    font = Path(os.environ.get("TYPOGRAPHY_TEST_FONT", "C:/Windows/Fonts/arial.ttf"))
    if not font.is_file():
        pytest.skip("Explicit local Latin font required for real typography qualification")
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline.tracks = []
        persist_contract(record, doc)
        db.commit()
    headers = {"Authorization": "Bearer " + project["token"]}
    # Font is a local licensed installation, uploaded into temporary test storage.
    # The font binary is not copied into retained evidence or committed fixtures.
    with font.open("rb") as file:
        uploaded = client.post(
            "/api/v1/studios/v1/editing/resources/upload",
            headers=headers,
            data={
                "workspace_id": project["workspace"],
                "title": "Typography test Latin font",
                "metadata": json.dumps(
                    {
                        "kind": "font",
                        "usageEvidence": "Licensed local test installation; font binary is not retained in evidence",
                    }
                ),
            },
            files={"file": (font.name, file, "font/ttf")},
        )
    assert uploaded.status_code == 200, uploaded.text
    font_asset = uploaded.json()["id"]
    text = "AC\u0327A\u0303O" if variant == "unicode" else "Uma palavra inteira precisa de espaço para leitura clara"
    word_mode = variant == "wrapped_words"
    expected_units = text.split(" ") if word_mode else ["A", "C\u0327", "A\u0303", "O"]
    complete = 10 if word_mode else 19
    direction = typography_direction(
        text, "word" if word_mode else "character", duration=30,
        stagger=0 if word_mode else 3, hold=(20 if word_mode else 11) - int(temporal),
    ).model_dump(mode="json", by_alias=True)
    scene = direction["scenes"][0]
    hero = scene["elements"][0]
    hero["fontAssetId"] = font_asset
    control = copy.deepcopy(scene)
    control.update(id="control", purpose="Sequential control with identical font and units")
    control_recipe = control["motionRecipes"][0]
    control_recipe["id"] = "control-type"
    control_recipe["parameters"].update(staggerFrames=0, readingHoldFrames=20 - int(temporal))
    direction["scenes"].append(control)
    if temporal:
        for part in direction["scenes"]:
            part["motionRecipes"].append({
                "id": "type-exposure", "version": 1, "technique": "velocity_blur", "targetIds": ["hero"],
                "startFrame": 0, "endFrameExclusive": 30, "intent": "Expose the authored entrance and settle",
                "continuityAnchor": "Same text, font, layout and hold",
                "parameters": {"temporalSamples": 8, "shutterDegrees": 180,
                               "temporalExposure": TemporalExposureV1().model_dump(mode="json", by_alias=True)},
                "verification": ["All exposure samples complete before reading hold"],
            })
    base = f"/api/v1/studios/v1/documents/{project['document']}"
    response = client.post(
        base + "/editing-plans", headers={**headers, "Idempotency-Key": "typography-plan"}, json=direction
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["status"] == "ready", plan["blockers"]
    applied = client.post(
        base + f"/editing-plans/{plan['id']}/apply", headers=headers, json={"expectedPlanRevision": plan["revision"]}
    )
    assert applied.status_code == 200, json.dumps(
        plan.get("manifest", {}).get("visualAudit", {}).get("findings"), ensure_ascii=True
    )
    snapshot = client.get(base + "/editor/inspection?frame=19", headers=headers).json()
    monkeypatch.setitem(
        VIDEO_RENDER_PROVIDERS,
        "remotion.contextual-v2",
        RemotionNativeContextualRenderProvider(
            RemotionNativeGraphicsProvider("node", "ffmpeg", 180),
            VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"],
        ),
    )
    monkeypatch.setattr("app.tasks.execute_studio_generation.delay", lambda *_: None)
    render = client.post(
        "/api/v1/studios/v1/video-renders",
        headers={**headers, "Idempotency-Key": "typography-render"},
        json={
            "workspaceId": project["workspace"],
            "documentId": project["document"],
            "expectedDocumentRevision": applied.json()["revision"],
            "expectedDocumentVersion": 1,
            "contextualPlanId": plan["id"],
            "provider": "remotion.contextual-v2",
            "output": {"width": 320, "height": 320, "fps": 30, "quality": "high"},
        },
    )
    assert render.status_code == 202, render.text
    wait_until = time.monotonic() + 120
    while _active(_read(lease_path())):
        if time.monotonic() >= wait_until:
            pytest.skip("Another live local operation occupies heavy-media capacity")
        time.sleep(1)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, render.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        result = job.result_payload
        assert result["documentRevision"] == applied.json()["revision"]
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        metadata = asset.object_metadata
        checks = metadata["contextualEditing"]["rendererChecks"]
        samples = checks["geometrySamples"]
        assert len(samples) == 60
        observed = []
        for frame in [0, 5, complete - 1, complete, complete + 1, 29]:
            sample = next(sample for sample in samples if sample["frame"] == frame)
            hero_observation = next(
                item for item in sample["elements"] if item["semanticId"] == "hero" and item["present"]
            )
            typography = hero_observation["typography"]
            layout = typography["layout"]
            assert layout["policy"] == "dom.units-fit.v1" and layout["fits"]
            assert layout["fontBindingBasis"] == "checksum_bound_asset"
            assert layout["fontSizePx"] >= layout["minimumFontSizePx"]
            assert layout["fontSizePx"] <= layout["requestedFontSizePx"]
            assert layout["contentHeightPx"] <= hero_observation["bounds"]["height"] + 0.5
            assert len(layout["units"]) == len(expected_units)
            assert all(unit["ink"]["height"] > 0 for unit in layout["units"])
            if word_mode:
                assert len(layout["lines"]) >= 3
                assert layout["fontSizePx"] >= 30
            units = typography["units"]
            assert [unit["text"] for unit in units] == expected_units
            assert typography["animatedCount"] == len(expected_units) and typography["completeFrame"] == complete
            hold_start = complete + int(temporal)
            assert typography["holdEligible"] == (frame >= hold_start)
            observed_time = frame
            if temporal:
                exposure = hero_observation["temporalExposure"]
                observed_time = exposure["sampleFrames"][0]
                assert not exposure["pixelCoverageObserved"]
                if frame >= hold_start:
                    assert exposure["actualSamples"] == 1
                if frame == complete:
                    assert exposure["actualSamples"] == 8 and observed_time < complete
            assert all("ResFont_" + font_asset in unit["fontFamily"] for unit in units)
            assert all(unit["bounds"]["width"] > 0 for unit in units)
            if observed_time >= complete:
                assert all(unit["localOpacity"] == 1 for unit in units)
            elif frame == 0:
                if temporal:
                    assert all(0 <= unit["localOpacity"] < 0.05 for unit in units)
                else:
                    assert all(unit["localOpacity"] == 0 for unit in units)
            else:
                assert units[-1]["localOpacity"] < 1
            observed.append({"frame": frame, "hero": hero_observation})
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            assert checksum == result["artifact"]["checksumSha256"]
            pixels = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                capture_output=True,
                check=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout
            assert len(pixels) == 60 * 320 * 320 * 3

            def frame_pixels(frame):
                size = 320 * 320 * 3
                return pixels[frame * size : (frame + 1) * size]

            hold_begin = frame_pixels(complete + int(temporal))
            hold_end, rest_control = frame_pixels(29), frame_pixels(59)

            def difference(left, right):
                return sum(abs(a - b) for a, b in zip(left, right, strict=True)) / len(left)

            assert difference(hold_begin, hold_end) < 1.5
            assert difference(hold_end, rest_control) < 2.5
            assert sum(value > 180 for value in frame_pixels(0)) == 0
            assert sum(value > 180 for value in hold_end) > 100
            pixel_checks = {
                "holdBeginVsEndMeanAbsoluteChannelError": difference(hold_begin, hold_end),
                "settledVsZeroStaggerControlMeanAbsoluteChannelError": difference(hold_end, rest_control),
                "firstFrameBrightChannels": sum(value > 180 for value in frame_pixels(0)),
                "settledBrightChannels": sum(value > 180 for value in hold_end),
                "scope": "whole decoded frame",
            }
            if output := os.environ.get("TYPOGRAPHY_EVIDENCE_DIR"):
                target = Path(output) / variant
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target / "typography.mp4")
                (target / "evidence.json").write_text(
                    json.dumps(
                        {
                            "scope": "actual_API_plan_job_font_MP4",
                            "humanReview": "pending",
                            "canonicalText": text,
                            "temporalExposure": temporal,
                            "effectiveHoldStartFrame": complete + int(temporal),
                            "inspection": snapshot,
                            "renderResult": result,
                            "renderMetadata": metadata,
                            "font": {
                                "assetId": font_asset,
                                "source": "local licensed test font; binary not retained",
                                "sha256": hashlib.sha256(font.read_bytes()).hexdigest(),
                            },
                            "selectedGeometry": observed,
                            "decodedPixelChecks": pixel_checks,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
