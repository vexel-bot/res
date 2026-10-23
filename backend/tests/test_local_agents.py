"""Real local production plus authority/idempotency boundaries; no remote inference."""

import io
import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.agents import AgentOutput
from app.domain.studios.contracts import CreativeDocumentV1
from app.models import StudioGenerationJob
from app.providers.studios import timeline_ffmpeg as ff
from app.services.studios.agent_orchestrator import proposed_document
from app.services.studios.jobs import execute_job_once
from app.studio_app import app
from test_clicko_studio_bridge import KEY, headers

BASE = "/api/v1/studios/v1"


def prepare(monkeypatch, tmp_path, visual=False):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path / "objects"))
    from app.routers import studio_video

    monkeypatch.setattr(studio_video, "dispatch", lambda job: None)
    return headers(module="create-image" if visual else "create-video", client="local-agents")


def create(client, auth, visual=False, key="project-create-001"):
    workspace = client.get(BASE + "/bridge/session", headers=auth).json()["workspace"]["id"]
    body = {
        "workspaceId": workspace,
        "title": "Inteligência em movimento",
        "contentType": "visual" if visual else "video",
        "width": 320,
        "height": 320,
    }
    response = client.post(BASE + "/agents/projects", headers={**auth, "Idempotency-Key": key}, json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


def plan(client, auth, doc, instruction, key="task-plan-001"):
    response = client.post(
        BASE + f"/documents/{doc['documentId']}/agent-tasks",
        headers={**auth, "Idempotency-Key": key},
        json={"expectedRevision": doc["revision"], "instruction": instruction},
    )
    assert response.status_code == 200, response.text
    return response.json()


def apply(client, auth, doc, task):
    response = client.post(
        BASE + f"/documents/{doc['documentId']}/agent-tasks/{task['id']}/apply",
        headers=auth,
        json={"expectedRevision": task["documentRevision"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_plan_review_apply_idempotency_stale_revision_and_access(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, body = create(client, auth)
        repeated = client.post(
            BASE + "/agents/projects", headers={**auth, "Idempotency-Key": "project-create-001"}, json=body
        )
        assert repeated.json()["documentId"] == doc["documentId"]
        assert (
            client.post(
                BASE + "/agents/projects",
                headers={**auth, "Idempotency-Key": "project-create-001"},
                json={**body, "title": "Other"},
            ).status_code
            == 409
        )
        task = plan(client, auth, doc, "Crie um motion design de 3 segundos sobre inteligência artificial.")
        assert task["status"] == "succeeded", task
        assert task["externalCostUsd"] == 0 and task["result"]["inference"] == "none"
        assert task["result"]["planning"] == "deterministic_rules"
        assert task["result"]["delegations"] == ["audiovisual", "image"]
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 1
        saved = apply(client, auth, doc, task)
        assert saved["revision"] == 2 and len(saved["composition"]["pages"][0]["layers"]) == 9
        assert saved["composition"]["mediaTimeline"]["durationFrames"] == 72
        assert apply(client, auth, doc, task) == saved
        # Replaying the planning key returns its original task, not another inference.
        assert (
            plan(client, auth, doc, "Crie um motion design de 3 segundos sobre inteligência artificial.")["id"]
            == task["id"]
        )
        assert (
            client.post(
                BASE + f"/documents/{doc['documentId']}/agent-tasks",
                headers={**auth, "Idempotency-Key": "task-plan-other"},
                json={"expectedRevision": 1, "instruction": "Crie outra"},
            ).status_code
            == 409
        )
        for foreign in [
            headers(module="create-video", client="foreign"),
            headers(module="create-image", client="local-agents"),
        ]:
            assert client.get(BASE + f"/documents/{doc['documentId']}/agent-tasks", headers=foreign).status_code in {
                403,
                404,
            }
        assert client.get(BASE + f"/documents/{doc['documentId']}/agent-tasks").status_code == 401


def test_commands_reject_arbitrary_code_unbound_assets_and_locked_layers(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, _ = create(client, auth)
        doc = apply(client, auth, doc, plan(client, auth, doc, "Crie um motion de 3 segundos"))
        path = BASE + f"/documents/{doc['documentId']}/local-commands"

        def send(commands, key):
            return client.post(
                path,
                headers={**auth, "Idempotency-Key": key},
                json={"expectedRevision": doc["revision"], "commands": commands},
            )

        assert send([{"id": "shell.exec", "params": {"code": "echo hello"}}], "reject-command-001").status_code == 422
        layer = deepcopy(doc["composition"]["pages"][0]["layers"][0])
        layer["properties"]["script"] = "movie=/private"
        assert send([{"id": "layer.upsert", "params": {"layer": layer}}], "reject-command-002").status_code == 422
        layer = deepcopy(doc["composition"]["pages"][0]["layers"][0])
        layer["kind"] = "image"
        layer["properties"] = {"schemaVersion": "studio.local-layer.v1", "assetId": "foreign"}
        assert send([{"id": "layer.upsert", "params": {"layer": layer}}], "reject-command-003").status_code == 422
        current = CreativeDocumentV1.model_validate(doc)
        current.composition.pages[0].layers[0].locked = True
        commands = AgentOutput.model_validate(
            {
                "commands": [{"id": "layer.remove", "params": {"layerId": current.composition.pages[0].layers[0].id}}],
                "rationale": "remove",
            }
        ).commands
        with SessionLocal() as db, pytest.raises(ValueError, match="locked"):
            proposed_document(db, current, commands)
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 2


def test_unsupported_operation_has_no_fake_generation_or_edit(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path, visual=True)
    with TestClient(app) as client:
        doc, _ = create(client, auth, True)
        task = plan(client, auth, doc, "Remova o fundo desta imagem")
        assert task["result"]["commands"] == [] and task["result"]["state"] == "unsupported"
        assert (
            client.post(
                BASE + f"/documents/{doc['documentId']}/agent-tasks/{task['id']}/apply",
                headers=auth,
                json={"expectedRevision": 1},
            ).status_code
            == 422
        )
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 1


def test_role_configuration_refuses_remote_and_ollama_cloud_before_inference(monkeypatch, tmp_path):
    from app.models import StudioLLMConnection
    from app.models import Membership
    from sqlalchemy import select

    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, body = create(client, auth)
        workspace = body["workspaceId"]
        for index, config in enumerate(
            [
                {
                    "billingMode": "metered",
                    "protocol": "ollama_chat",
                    "baseUrl": "http://127.0.0.1:11434",
                    "models": ["qwen3:0.6b"],
                },
                {
                    "billingMode": "local_free",
                    "protocol": "ollama_chat",
                    "baseUrl": "https://api.example.com",
                    "models": ["qwen3:0.6b"],
                },
                {
                    "billingMode": "local_free",
                    "protocol": "ollama_chat",
                    "baseUrl": "http://127.0.0.1:11434",
                    "models": ["large:cloud"],
                },
            ]
        ):
            identifier = f"unsafe-{index}"
            with SessionLocal() as db:
                owner = db.scalar(select(Membership.user_id).where(Membership.workspace_id == workspace))
                db.add(
                    StudioLLMConnection(
                        id=identifier,
                        workspace_id=workspace,
                        label="Blocked",
                        provider="ollama",
                        created_by=owner,
                        revision=1,
                        config={"enabled": True, "authHeader": "Authorization", **config},
                    )
                )
                db.commit()
            response = client.put(
                BASE + "/agents/roles",
                params={"workspace_id": workspace},
                headers=auth,
                json={
                    "expectedRevision": 0,
                    "audiovisual": {"mode": "local_model", "connectionId": identifier, "model": config["models"][0]},
                    "image": {"mode": "local_tools"},
                },
            )
            assert response.status_code == 422, response.text
        assert (
            client.get(BASE + "/agents/roles", params={"workspace_id": workspace}, headers=auth).json()["revision"] == 0
        )
        assert (
            client.put(
                BASE + "/agents/roles",
                params={"workspace_id": workspace},
                headers=headers(module="create-video", client="local-agents", role="Member"),
                json={"expectedRevision": 0},
            ).status_code
            == 403
        )


def test_image_import_crop_color_layers_export_versions_and_original(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path, True)
    source = io.BytesIO()
    Image.new("RGB", (80, 100), "red").save(source, format="PNG")
    original = source.getvalue()
    with TestClient(app) as client:
        doc, body = create(client, auth, True)
        uploaded = client.post(
            BASE + "/craft/assets",
            headers={**auth, "Content-Type": "image/png"},
            params={
                "workspace_id": body["workspaceId"],
                "title": "Own image",
                "filename": "own.png",
                "media_type": "image/png",
            },
            content=original,
        )
        assert uploaded.status_code == 201, uploaded.text
        asset = uploaded.json()
        layer = {
            "id": "own-image",
            "kind": "image",
            "name": "Own image",
            "width": 160,
            "height": 200,
            "x": 80,
            "y": 40,
            "properties": {
                "schemaVersion": "studio.local-layer.v1",
                "assetId": asset["id"],
                "brightness": 0.7,
                "contrast": 1.2,
                "crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8},
            },
        }
        response = client.post(
            BASE + f"/documents/{doc['documentId']}/local-commands",
            headers={**auth, "Idempotency-Key": "image-commands-001"},
            json={
                "expectedRevision": 1,
                "commands": [
                    {"id": "asset.attach", "params": {"assetId": asset["id"]}},
                    {"id": "layer.upsert", "params": {"layer": layer}},
                ],
            },
        )
        assert response.status_code == 200, response.text
        saved = response.json()
        path = BASE + f"/documents/{doc['documentId']}/local-image-export"
        exported = client.post(
            path, headers={**auth, "Idempotency-Key": "image-export-001"}, json={"expectedRevision": 2}
        )
        assert exported.status_code == 200, exported.text
        result = exported.json()
        png = client.get(result["downloadUrl"], headers=auth)
        assert png.status_code == 200
        image = Image.open(io.BytesIO(png.content))
        assert image.size == (320, 320)
        assert image.getpixel((160, 100))[0] > 100 and image.getpixel((10, 10))[:3] == (0, 0, 0)
        assert (
            client.post(
                path, headers={**auth, "Idempotency-Key": "image-export-001"}, json={"expectedRevision": 2}
            ).json()["assetId"]
            == result["assetId"]
        )
        assert client.get(f"/api/v1/assets/{asset['id']}/content", headers=auth).content == original
        history = client.get(BASE + f"/documents/{doc['documentId']}/versions", headers=auth).json()
        assert history[0]["number"] == 1 and history[0]["snapshot"]["composition"]["pages"][0]["layers"] == []
        restore = client.post(
            BASE + f"/documents/{doc['documentId']}/versions/1/restore", headers=auth, json={"expectedRevision": 2}
        )
        assert restore.status_code == 200, restore.text
        assert restore.json()["composition"]["pages"][0]["layers"] == []
        assert client.get(result["downloadUrl"], headers=auth).content == png.content


def test_local_llm_contract_mock_is_not_inference_evidence_and_invalid_output_cannot_edit(monkeypatch, tmp_path):
    from app.services.studios import agent_orchestrator
    from app.providers.studios.universal_llm import UniversalLLMPlanner

    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, body = create(client, auth)
        response = client.post(
            BASE + "/craft/llm-connections",
            params={"workspace_id": body["workspaceId"]},
            headers=auth,
            json={
                "label": "Mock contract only",
                "provider": "ollama",
                "protocol": "ollama_chat",
                "baseUrl": "http://127.0.0.1:11434",
                "models": ["test-local-model"],
                "enabled": True,
                "billingMode": "local_free",
            },
        )
        assert response.status_code == 201, response.text
        connection = response.json()
        response = client.put(
            BASE + "/agents/roles",
            params={"workspace_id": body["workspaceId"]},
            headers=auth,
            json={
                "expectedRevision": 0,
                "audiovisual": {"mode": "local_model", "connectionId": connection["id"], "model": "test-local-model"},
                "image": {"mode": "local_tools"},
            },
        )
        assert response.status_code == 200, response.text
        monkeypatch.setattr(agent_orchestrator, "require_installed_model", lambda *args: None)
        calls = []

        def simulated(self, model, context, media):
            assert context["localExecution"] is True and context["outputSchema"]["type"] == "object"
            calls.append(model)
            return {
                "text": json.dumps(
                    {
                        "commands": [{"id": "shell.exec", "params": {"command": "no"}}],
                        "rationale": "Invalid mock output",
                    }
                ),
                "usage": {},
            }

        monkeypatch.setattr(UniversalLLMPlanner, "plan", simulated)
        task = plan(client, auth, doc, "Teste de contrato de modelo simulado")
        assert task["status"] == "failed" and task["errorCode"] == "agent_planning_failed"
        assert calls == ["test-local-model"]
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 1

        def cancelled_model(self, model, context, media):
            from sqlalchemy import select

            with SessionLocal() as db:
                job = db.scalar(
                    select(StudioGenerationJob).where(
                        StudioGenerationJob.document_id == doc["documentId"], StudioGenerationJob.status == "running"
                    )
                )
                job.status = "cancel_requested"
                db.commit()
            return {
                "text": json.dumps(
                    {
                        "commands": [{"id": "project.background", "params": {"color": "#6EB8F5"}}],
                        "rationale": "Contract mock only",
                    }
                ),
                "usage": {},
            }

        monkeypatch.setattr(UniversalLLMPlanner, "plan", cancelled_model)
        task = plan(client, auth, doc, "Cancelamento do contrato simulado", "mock-cancelled-model")
        assert task["status"] == "cancelled" and not task["result"]["commands"]
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 1


def test_duration_edit_preserves_ids_and_binds_keyframes_to_new_scene_bounds(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, _ = create(client, auth)
        doc = apply(client, auth, doc, plan(client, auth, doc, "Crie um motion de 12 segundos"))
        ids = [layer["id"] for layer in doc["composition"]["pages"][0]["layers"]]
        task = plan(client, auth, doc, "Mude a duração para 20 segundos", "duration-plan-002")
        assert task["result"]["delegations"] == ["audiovisual"]
        changed = apply(client, auth, doc, task)
        assert changed["composition"]["mediaTimeline"]["durationFrames"] == 480
        for layer in changed["composition"]["pages"][0]["layers"]:
            assert layer["id"] in ids
            style = layer["properties"]
            assert style["startFrame"] + style["durationFrames"] <= 480
            assert all(key["frame"] <= style["durationFrames"] for key in style["keyframes"])


@pytest.mark.skipif(not ff.capability()["available"], reason="Requires actual FFmpeg and ffprobe")
def test_real_text_to_motion_mp4_change_title_second_export_and_preservation(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, _ = create(client, auth)
        task = plan(client, auth, doc, "Crie um motion de 3 segundos sobre inteligência artificial")
        assert task["status"] == "succeeded", task
        doc = apply(client, auth, doc, task)
        base = BASE + f"/video/documents/{doc['documentId']}/render-jobs"

        def render(doc, key):
            response = client.post(
                base, headers={**auth, "Idempotency-Key": key}, json={"expectedRevision": doc["revision"]}
            )
            assert response.status_code == 202, response.text
            with SessionLocal() as db:
                job = db.get(StudioGenerationJob, response.json()["id"])
                assert execute_job_once(db, job) == "succeeded", job.error_message
                result = job.result_payload
            response = client.get(result["downloadUrl"], headers=auth)
            assert response.status_code == 200
            path = tmp_path / f"{key}.mp4"
            path.write_bytes(response.content)
            info = ff.probe(path)
            assert float(info["format"]["duration"]) == pytest.approx(3, abs=0.1)
            return response.content, result

        first, first_result = render(doc, "motion-render-first")
        updated = apply(
            client, auth, doc, plan(client, auth, doc, 'Mude o primeiro título para "Novo título"', "task-title-002")
        )
        second, _ = render(updated, "motion-render-second")
        assert first != second
        history = client.get(BASE + f"/documents/{doc['documentId']}/versions", headers=auth).json()
        assert history[0]["snapshot"]["composition"]["pages"][0]["layers"][2]["properties"]["text"] != "Novo título"
        assert client.get(first_result["downloadUrl"], headers=auth).content == first
        assert (
            client.get(
                BASE + f"/documents/{doc['documentId']}/local-preview", headers=auth, params={"frame": 16}
            ).headers["content-type"]
            == "image/png"
        )
