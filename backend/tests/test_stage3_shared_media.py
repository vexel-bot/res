"""Real PNG -> Motion -> canonical Video renders, independent of browser QA."""

import hashlib
import io
import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from test_clicko_studio_bridge import headers
from test_local_agent_stage2 import selected_plan
from test_local_agents import BASE, apply, create, plan, prepare
from test_media_final_validation import retain
from test_video_timeline_real import create as create_video
from test_video_timeline_real import pixels

from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios import timeline_ffmpeg as ff
from app.services.studios.jobs import execute_job_once
from app.studio_app import app


@pytest.mark.skipif(not ff.capability()["available"], reason="Requires actual FFmpeg/ffprobe")
def test_real_image_material_is_shared_to_motion_and_video_without_touching_original(monkeypatch, tmp_path):
    image_auth = prepare(monkeypatch, tmp_path, visual=True)
    video_auth = headers(module="create-video", client="local-agents")
    evidence = {"inference": "none", "authenticatedBrowserQa": False, "externalCostUsd": 0, "exports": []}
    with TestClient(app) as client:
        image, _ = create(client, image_auth, visual=True)
        image = apply(client, image_auth, image, plan(client, image_auth, image, 'Crie um cartão com título "Clicko"'))
        image = apply(
            client,
            image_auth,
            image,
            selected_plan(client, image_auth, image, "Troque a cor para tangerina", ["card"], "shared-color"),
        )
        result = client.post(
            BASE + f"/documents/{image['documentId']}/local-image-export",
            headers={**image_auth, "Idempotency-Key": "stage3-shared-png"},
            json={"expectedRevision": image["revision"]},
        )
        assert result.status_code == 200, result.text
        exported = result.json()
        png = client.get(exported["downloadUrl"], headers=image_auth).content
        assert Image.open(io.BytesIO(png)).getpixel((40, 40))[:3] == (242, 133, 0)
        original_hash = hashlib.sha256(png).hexdigest()
        original_path = tmp_path / "shared-image.png"
        original_path.write_bytes(png)
        retain(original_path, "shared-image.png")

        motion, _ = create(client, video_auth, key="stage3-motion")
        motion = apply(
            client,
            video_auth,
            motion,
            plan(client, video_auth, motion, "Crie um motion de 3 segundos", "stage3-motion-plan"),
        )
        graphic = {
            "id": "shared-image",
            "name": "Image Studio export",
            "kind": "image",
            "x": 0,
            "y": 0,
            "width": 320,
            "height": 320,
            "zIndex": 100,
            "properties": {
                "schemaVersion": "studio.local-layer.v1",
                "assetId": exported["assetId"],
                "durationFrames": 72,
            },
        }
        saved = client.post(
            BASE + f"/documents/{motion['documentId']}/local-commands",
            headers={**video_auth, "Idempotency-Key": "stage3-attach"},
            json={
                "expectedRevision": motion["revision"],
                "commands": [
                    {"id": "asset.attach", "params": {"assetId": exported["assetId"]}},
                    {"id": "layer.upsert", "params": {"layer": graphic}},
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        motion = saved.json()
        _, video = create_video(client, video_auth)
        timeline = deepcopy(video["composition"]["mediaTimeline"])
        timeline["tracks"] = [
            {
                "id": "graphic",
                "name": "Image Studio export",
                "kind": "overlay",
                "clips": [
                    {
                        "id": "graphic-clip",
                        "assetId": exported["assetId"],
                        "timeline": {"startFrame": 0, "durationFrames": 48},
                        "transform": {},
                    }
                ],
            }
        ]
        saved = client.put(
            BASE + f"/video/documents/{video['documentId']}/timeline",
            headers={**video_auth, "Idempotency-Key": "stage3-video-image"},
            json={"expectedRevision": video["revision"], "timeline": timeline},
        )
        assert saved.status_code == 200, saved.text
        video = saved.json()
        for name, doc, seconds in [("shared-motion", motion, 3), ("shared-video", video, 2)]:
            requested = client.post(
                BASE + f"/video/documents/{doc['documentId']}/render-jobs",
                headers={**video_auth, "Idempotency-Key": name},
                json={"expectedRevision": doc["revision"]},
            )
            assert requested.status_code == 202, requested.text
            with SessionLocal() as db:
                row = db.get(StudioGenerationJob, requested.json()["id"])
                assert execute_job_once(db, row) == "succeeded", row.error_message
                delivery = row.result_payload
            response = client.get(delivery["downloadUrl"], headers=video_auth)
            assert response.status_code == 200
            path = tmp_path / f"{name}.mp4"
            path.write_bytes(response.content)
            assert float(ff.probe(path)["format"]["duration"]) == pytest.approx(seconds, abs=0.1)
            r, g, b = pixels(path, 0.5).getpixel((40, 40))
            assert r > 210 and 90 < g < 165 and b < 30, "Shared PNG must appear in actual encoded MP4 pixels"
            assert (
                client.get(
                    delivery["downloadUrl"], headers=headers(module="create-video", client="foreign")
                ).status_code
                == 404
            )
            retain(path, path.name)
            evidence["exports"].append(
                {"name": name, "durationSeconds": seconds, "sha256": hashlib.sha256(response.content).hexdigest()}
            )
        assert (
            hashlib.sha256(client.get(exported["downloadUrl"], headers=image_auth).content).hexdigest() == original_hash
        )
        persisted = client.get(BASE + f"/documents/{image['documentId']}", headers=image_auth).json()
        assert persisted["composition"] == image["composition"] and persisted["revision"] == image["revision"]
        evidence["originalPreserved"] = True
        evidence["originalSha256"] = original_hash
        proof = tmp_path / "shared-evidence.json"
        proof.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        retain(proof, proof.name)
