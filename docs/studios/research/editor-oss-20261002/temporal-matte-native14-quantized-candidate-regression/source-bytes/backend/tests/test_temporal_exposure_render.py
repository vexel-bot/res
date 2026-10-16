"""Real canonical exposure fixtures; measured pixels are separate from human scores."""

# ruff: noqa: F811
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


def exposure_direction(samples, shutter=180, policy=None):
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scenes = []
    for index, (background, foreground, y) in enumerate(
        [
            ("#142850", "#dcb446", 40),
            ("#501428", "#28c8dc", 100),
        ]
    ):
        scene = {
            "id": "exposure-" + str(index),
            "purpose": "Original temporal exposure and cut fixture",
            "durationFrames": 30,
            "background": background,
            "entrance": "cut",
            "verification": ["Same authored motion, color and opacity in every sample variant"],
            "elements": [
                {
                    "id": "moving",
                    "kind": "shape",
                    "purpose": "Moving semi-transparent color",
                    "x": 20,
                    "y": y,
                    "width": 64,
                    "height": 64,
                    "fill": foreground,
                    "radius": 0,
                    "durationFrames": 30,
                    "depthTreatment": {"opacity": 0.5},
                    "visualRole": "hero",
                },
                {
                    "id": "still",
                    "kind": "shape",
                    "purpose": "Stationary color and alpha witness",
                    "x": 20,
                    "y": 200,
                    "width": 80,
                    "height": 40,
                    "fill": foreground,
                    "radius": 0,
                    "durationFrames": 30,
                    "depthTreatment": {"opacity": 0.5},
                    "visualRole": "support",
                },
            ],
            "motionRecipes": [
                {
                    "id": "move",
                    "version": 1,
                    "technique": "motion_choreography",
                    "targetIds": ["moving"],
                    "startFrame": 0,
                    "endFrameExclusive": 30,
                    "intent": "Move and hold the same shape",
                    "continuityAnchor": "Authored color and opacity",
                    "parameters": {
                        "tracks": [
                            {
                                "targetId": "moving",
                                "property": "x",
                                "keyframes": [
                                    {"frame": 0, "value": 0, "curve": [0, 0, 1, 1]},
                                    {"frame": 8, "value": 150},
                                    {"frame": 29, "value": 150},
                                ],
                            }
                        ]
                    },
                    "verification": ["Hold remains sharp"],
                }
            ],
        }
        if samples:
            parameters = {"temporalSamples": samples, "shutterDegrees": shutter}
            if policy:
                parameters["temporalExposure"] = policy
            scene["motionRecipes"].append(
                {
                    "id": "exposure",
                    "version": 1,
                    "technique": "velocity_blur",
                    "targetIds": ["moving", "still"],
                    "startFrame": 0,
                    "endFrameExclusive": 30,
                    "intent": "Temporal exposure with inspectable parameters",
                    "continuityAnchor": "Same graphic, no footage or synthetic replacement",
                    "parameters": parameters,
                    "verification": ["Inspect moving edges, paused color and the cut"],
                }
            )
        scenes.append(scene)
    raw["scenes"] = scenes
    return raw


@pytest.mark.parametrize("samples,shutter", [(0, 180), (2, 180), (8, 180), (16, 180), (8, 0)])
def test_temporal_exposure_actual_api_measurement(client, project, monkeypatch, tmp_path, samples, shutter):
    policy = (
        TemporalExposureV1().model_dump(mode="json", by_alias=True)
        if (os.environ.get("TEMPORAL_EXPOSURE_POLICY", "centered") == "centered")
        else None
    )
    if policy is None and shutter == 0:
        pytest.skip("Legacy zero shutter now requires explicit policy; rejection covered by contract test")
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline.tracks = []
        persist_contract(record, doc)
        db.commit()
    headers = {"Authorization": "Bearer " + project["token"]}
    base = f"/api/v1/studios/v1/documents/{project['document']}"
    response = client.post(
        base + "/editing-plans",
        headers={**headers, "Idempotency-Key": "exposure-plan"},
        json=exposure_direction(samples, shutter, policy),
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["status"] == "ready", plan["blockers"]
    applied = client.post(
        base + f"/editing-plans/{plan['id']}/apply", headers=headers, json={"expectedPlanRevision": plan["revision"]}
    )
    assert applied.status_code == 200, applied.text
    inspection = client.get(base + "/editor/inspection?frame=30", headers=headers).json()
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
        headers={**headers, "Idempotency-Key": "exposure-render"},
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
    assert response.status_code == 202, response.text
    deadline = time.monotonic() + 120
    while _active(_read(lease_path())):
        if time.monotonic() >= deadline:
            pytest.skip("Live local operation occupies heavy-media capacity")
        time.sleep(1)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        result = job.result_payload
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        metadata = asset.object_metadata
        assert result["qualityEvaluation"]["status"] == "passed"
        assert result["documentRevision"] == applied.json()["revision"]
        checks = metadata["contextualEditing"]["rendererChecks"]
        assert checks["graphics"]["remotionReceipt"]["encodeQuality"] == "high"
        assert checks["graphics"]["remotionReceipt"]["videoCrf"] == 1
        assert checks["graphics"]["remotionReceipt"]["pixelFormat"] == "yuv444p"
        assert checks["audiovisual"]["encodeQuality"] == "high"
        assert checks["audiovisual"]["videoCrf"] == 14
        geometry = metadata["contextualEditing"]["rendererChecks"]["geometrySamples"]
        assert len(geometry) == 60
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as output:
            assert hashlib.sha256(output.read_bytes()).hexdigest() == result["artifact"]["checksumSha256"]
            pixels = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(output), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                capture_output=True,
                check=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout
            assert len(pixels) == 60 * 320 * 320 * 3

            def pixel(frame, x, y):
                offset = (frame * 320 * 320 + y * 320 + x) * 3
                return list(pixels[offset : offset + 3])

            observations = []
            for frame in [0, 4, 10, 29, 30, 34, 40, 59]:
                scene = int(frame >= 30)
                local = frame - scene * 30
                observations.append(
                    {
                        "frame": frame,
                        "stationaryRgb": pixel(frame, 60, 220),
                        "movingCenterRgb": pixel(frame, round(52 + 150 * min(local / 8, 1)), 52 + scene * 60),
                        "initialPositionRgb": pixel(frame, 27, 52 + scene * 60),
                        "settledPositionRgb": pixel(frame, 182, 52 + scene * 60),
                        "cutPreviousShapeRgb": pixel(frame, 182, 52),
                        "desiredColorAlphaRgb": [120, 110, 75] if not scene else [60, 110, 130],
                    }
                )
            edge_checks = []
            if policy and samples:
                for frame in [4, 34]:
                    part = int(frame >= 30)
                    background = [20, 40, 80] if not part else [80, 20, 40]
                    foreground = [220, 180, 70] if not part else [40, 200, 220]
                    # Independent uniform midpoint quadrature of a translated
                    # rectangle; no worker matrices, phase or DOM bounds used.
                    times = (
                        [frame]
                        if shutter == 0
                        else [
                            frame - shutter / 720 + (index + 0.5) * shutter / 360 / samples for index in range(samples)
                        ]
                    )
                    wrong_phase_errors = []
                    for requested_x in [86, 93, 96, 102, 154, 159, 162, 167]:
                        # Average a complete 2x2 yuv420p chroma block. A single
                        # edge pixel is not a stable color oracle after encode.
                        x = requested_x // 2 * 2
                        coverage = sum(
                            max(
                                0,
                                min(x + 2, 20 + 18.75 * (time - part * 30) + 64)
                                - max(x, 20 + 18.75 * (time - part * 30)),
                            )
                            for time in times
                        ) / len(times) / 2
                        expected = [b + 0.5 * coverage * (f - b) for b, f in zip(background, foreground, strict=True)]
                        observed = [sum(pixel(frame, x + dx, 52 + part * 60 + dy)[channel]
                                        for dx in range(2) for dy in range(2)) / 4 for channel in range(3)]
                        # Colored edges undergo chroma subsampling in H.264.
                        # Phase/coverage uses luminance; hold colors below
                        # retain independent checks of all RGB channels.
                        weights = [0.2126, 0.7152, 0.0722]
                        observed_luma = sum(a * w for a, w in zip(observed, weights, strict=True))
                        expected_luma = sum(a * w for a, w in zip(expected, weights, strict=True))
                        assert abs(observed_luma - expected_luma) < 8, (frame, x, observed, expected)
                        shifted_coverage = sum(max(0, min(x + 2, 20 + 18.75 * (time + 1 - part * 30) + 64)
                                                       - max(x, 20 + 18.75 * (time + 1 - part * 30)))
                                               for time in times) / len(times) / 2
                        shifted_luma = sum((b + .5 * shifted_coverage * (f - b)) * w
                                           for b, f, w in zip(background, foreground, weights, strict=True))
                        wrong_phase_errors.append(abs(observed_luma - shifted_luma))
                        edge_checks.append(
                            {
                                "frame": frame,
                                "x": x,
                                "expectedRgb": expected,
                                "observedRgb": observed,
                                "expectedLuminance": expected_luma,
                                "observedLuminance": observed_luma,
                                "footprint": "aligned_2x2_yuv420p_block",
                                "wrongPhasePlusOneFrameLuminanceError": abs(observed_luma - shifted_luma),
                            }
                        )
                    assert max(wrong_phase_errors) > 20, "Edge oracle must reject a one-frame phase error"
                for observed in observations:
                    expected = observed["desiredColorAlphaRgb"]
                    assert all(abs(a - b) < 12 for a, b in zip(observed["stationaryRgb"], expected, strict=True))
                    if observed["frame"] in [0, 30]:
                        assert all(
                            abs(a - b) < 12 for a, b in zip(observed["initialPositionRgb"], expected, strict=True)
                        )
                    if observed["frame"] in [10, 29, 40, 59]:
                        assert all(
                            abs(a - b) < 12 for a, b in zip(observed["settledPositionRgb"], expected, strict=True)
                        )
                    hero = next(
                        item
                        for item in geometry[observed["frame"]]["elements"]
                        if item["semanticId"] == "moving" and item["present"]
                    )
                    exposure = hero["temporalExposure"]
                    assert not exposure["pixelCoverageObserved"]
                    assert all(
                        0 <= time < 30 if observed["frame"] < 30 else 30 <= time < 60
                        for time in exposure["sampleFrames"]
                    )
                    if shutter == 0 or observed["frame"] in [10, 29, 40, 59]:
                        assert exposure["actualSamples"] == 1
            if directory := os.environ.get("TEMPORAL_EXPOSURE_EVIDENCE_DIR"):
                target = Path(directory) / f"samples-{samples}-shutter-{shutter}"
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output, target / "exposure.mp4")
                (target / "evidence.json").write_text(
                    json.dumps(
                        {
                            "scope": "actual_API_plan_apply_inspection_job_MP4_QC_decoded_pixels",
                            "humanReview": "pending",
                            "samplingPolicy": policy or "legacy_CameraMotionBlur",
                            "samples": samples,
                            "shutterDegrees": shutter,
                            "inspection": inspection,
                            "renderResult": result,
                            "renderMetadata": metadata,
                            "observations": observations,
                            "edgeChecks": edge_checks,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
