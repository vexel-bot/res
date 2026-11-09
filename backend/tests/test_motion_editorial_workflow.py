"""Exercise the editorial experiment against authenticated routes and real local renders."""

from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.providers.studios import timeline_ffmpeg
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.studios import agent_orchestrator, motion_gemini
from app.studio_app import app
from test_ad_materials_and_masks import upload
from test_local_agents import BASE, create, prepare

requires_renderer = pytest.mark.skipif(
    not timeline_ffmpeg.capability()["available"], reason="Real FFmpeg required"
)


def setup(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)

    def forbidden(*_args, **_kwargs):
        pytest.fail("The local editorial experiment attempted to invoke a provider")

    monkeypatch.setattr(agent_orchestrator, "local_planner", forbidden)
    monkeypatch.setattr(motion_gemini, "admitted_planner", forbidden)
    monkeypatch.setattr(UniversalLLMPlanner, "plan", forbidden)
    return auth


def seed(client, auth, *, cover=False, material_role="product"):
    document, _ = create(client, auth)
    document_path = BASE + f"/documents/{document['documentId']}"
    materials_path = BASE + f"/materials/document/{document['documentId']}"

    image = Image.new("RGB", (200, 170), "#334455")
    ImageDraw.Draw(image).ellipse((38, 18, 162, 154), fill="#f6b76a")
    asset = upload(client, auth, document["workspaceId"], image)
    kit = {
        "expectedRevision": 0,
        "name": "Produto demonstrável",
        "category": "physical",
        "goal": "showcase",
        "materials": [{"assetId": asset, "role": material_role, "label": "Fotografia"}],
    }
    response = client.put(materials_path + "/kits/editorial-kit", headers=auth, json=kit)
    assert response.status_code == 200, response.text
    response = client.put(
        materials_path + "/binding", headers=auth,
        json={"expectedRevision": 0, "kitId": "editorial-kit", "kitRevision": 1},
    )
    assert response.status_code == 200, response.text
    response = client.post(
        materials_path + "/import", headers=auth,
        json={"expectedRevision": document["revision"], "requestKey": "editorial-import-001"},
    )
    assert response.status_code == 200, response.text
    document = response.json()["document"]
    composition = document["composition"]
    composition["mediaTimeline"]["durationFrames"] = 48
    page = composition["pages"][0]
    page.update(background="#000000", durationMs=2000)
    base = {"schemaVersion": "studio.local-layer.v1", "startFrame": 0, "durationFrames": 48}
    page["layers"] = [
        {
            "id": "product", "kind": "image", "x": 62, "y": 115, "width": 196, "height": 160,
            "zIndex": 0, "properties": {**base, "assetId": asset},
        },
        {
            "id": "title", "kind": "text", "x": 22, "y": 22,
            "width": 230 if cover else 74, "height": 70,
            "zIndex": 1, "properties": {
                **base, "text": "Transformação", "color": "#FFFFFF", "fontSize": 21 if cover else 9,
            },
        },
    ]
    if cover:
        page["layers"].append({
            "id": "black-card", "kind": "shape", "x": 0, "y": 0, "width": 320, "height": 320,
            "zIndex": 20, "properties": {**base, "fill": "#000000"},
        })
    response = client.post(
        document_path + "/local-commands", headers={**auth, "Idempotency-Key": "editorial-seed-001"},
        json={"expectedRevision": document["revision"], "commands": [
            {"id": "composition.replace", "params": {"composition": composition}},
        ]},
    )
    assert response.status_code == 200, response.text
    return document_path, materials_path, response.json(), kit


def plan(client, auth, path, revision, variant="orchestrated"):
    response = client.post(
        path + "/agent-tasks", headers={**auth, "Idempotency-Key": "editorial-plan-001"},
        json={
            "expectedRevision": revision, "instruction": "Mostre a mudança do mesmo produto.",
            "planner": "editorial_experimental", "editorial": {"variant": variant, "format": "auto"},
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "succeeded", result
    assert result["externalCostUsd"] == 0 and result["result"]["inference"] == "none"
    return result


def apply(client, auth, path, task):
    return client.post(
        path + f"/agent-tasks/{task['id']}/apply", headers=auth,
        json={"expectedRevision": task["documentRevision"]},
    )


@requires_renderer
def test_review_renders_repaired_text_and_preserves_editable_project(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        path, _, document, _ = seed(client, auth)
        task = plan(client, auth, path, document["revision"])
        review = task["result"]["editorial"]
        assert review["format"] == "motion"
        assert review["humanVerdict"] == "inconclusive"
        assert review["repairCount"] == 1
        assert any(row["code"] == "text_below_phone_floor" for row in review["initialFindings"])
        preview = review["preview"]
        assert preview["status"] == "passed_technical", preview
        assert len(preview["sampledFrames"]) >= 6
        assert client.get(path, headers=auth).json()["composition"] == document["composition"]
        downloaded = client.get(preview["downloadUrl"], headers=auth)
        assert downloaded.status_code == 200, downloaded.text
        assert downloaded.headers["content-type"].startswith("video/mp4")
        assert sha256(downloaded.content).hexdigest() == preview["renderChecksum"]
        assert client.get(preview["downloadUrl"]).status_code == 401

        saved = apply(client, auth, path, task)
        assert saved.status_code == 200, saved.text
        saved = saved.json()
        assert saved["revision"] == document["revision"] + 1
        assert saved["assets"] == document["assets"]
        assert saved["composition"]["mediaTimeline"] == document["composition"]["mediaTimeline"]
        title = next(layer for layer in saved["composition"]["pages"][0]["layers"] if layer["id"] == "title")
        assert title["properties"]["text"] == "Transformação"
        assert title["properties"]["fontSize"] >= 14 and title["width"] > 74


@requires_renderer
def test_uniform_render_is_blocked_even_with_text_and_media_on_timeline(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        path, _, document, _ = seed(client, auth, cover=True)
        task = plan(client, auth, path, document["revision"])
        assert task["result"]["state"] == "blocked"
        assert task["result"]["commands"] == []
        preview = task["result"]["editorial"]["preview"]
        assert preview["status"] == "blocked"
        empty = [item for item in preview["findings"] if item["code"] == "empty_or_near_uniform_frame"]
        assert empty and all(item["hasPlannedSource"] for item in empty)
        assert apply(client, auth, path, task).status_code == 422
        assert client.get(path, headers=auth).json()["revision"] == document["revision"]


def test_apply_rejects_a_kit_revision_change_even_when_document_is_unchanged(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        path, materials, document, kit = seed(client, auth)
        task = plan(client, auth, path, document["revision"], "knowledge")
        assert task["result"]["commands"], task
        changed = client.put(
            materials + "/kits/editorial-kit", headers=auth,
            json={**kit, "expectedRevision": 1, "name": "Kit revisado"},
        )
        assert changed.status_code == 200, changed.text
        response = apply(client, auth, path, task)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "editorial_material_snapshot_conflict"
        assert client.get(path, headers=auth).json()["revision"] == document["revision"]


def test_knowledge_fits_logo_inside_existing_box_without_cropping(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        path, _, document, _ = seed(client, auth, material_role="logo")
        task = plan(client, auth, path, document["revision"], "knowledge")
        result = apply(client, auth, path, task)
        assert result.status_code == 200, result.text
        layer = result.json()["composition"]["pages"][0]["layers"][0]
        assert layer["width"] / layer["height"] == pytest.approx(200 / 170, abs=.003)
        assert layer["x"] + layer["width"] / 2 == 62 + 196 / 2
        assert layer["y"] == 115 and layer["height"] == 160
