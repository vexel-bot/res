"""Completion audit regressions. These are deterministic contracts, not model inference."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from test_local_agent_stage2 import selected_plan
from test_local_agents import BASE, apply, create, plan, prepare

from app.studio_app import app


def motion(client, auth):
    doc, _ = create(client, auth)
    return apply(client, auth, doc, plan(client, auth, doc, "Crie um motion de 15 segundos"))


def assert_other_layers_unchanged(before, after, target):
    old = {layer["id"]: layer for layer in before["composition"]["pages"][0]["layers"]}
    new = {layer["id"]: layer for layer in after["composition"]["pages"][0]["layers"]}
    assert set(old) == set(new)
    assert all(old[key] == new[key] for key in old if key != target)


def test_shorthand_hex_color_honors_selected_shape(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        before = motion(client, auth)
        task = selected_plan(client, auth, before, "Altere para #F28500", ["scene-2-card"], "selected-short-color")
        after = apply(client, auth, before, task)
        card = next(layer for layer in after["composition"]["pages"][0]["layers"] if layer["id"] == "scene-2-card")
        assert card["properties"]["fill"] == "#F28500"
        assert_other_layers_unchanged(before, after, "scene-2-card")


def test_selected_animation_duration_does_not_retime_the_project(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        before = motion(client, auth)
        task = selected_plan(
            client,
            auth,
            before,
            "Mude a duração dessa animação para 2 segundos",
            ["scene-2-title"],
            "selected-animation-duration",
        )
        after = apply(client, auth, before, task)
        assert after["composition"]["mediaTimeline"] == before["composition"]["mediaTimeline"]
        assert after["composition"]["narrative"] == before["composition"]["narrative"]
        assert_other_layers_unchanged(before, after, "scene-2-title")
        title = next(layer for layer in after["composition"]["pages"][0]["layers"] if layer["id"] == "scene-2-title")
        assert title["properties"]["durationFrames"] == 48
        assert max(key["frame"] for key in title["properties"]["keyframes"]) <= 48


def test_quoted_title_is_literal_not_a_style_command(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        before = motion(client, auth)
        literal = "Coral sem sombra"
        task = selected_plan(
            client, auth, before, f'Mude o título para "{literal}"', ["scene-2-title"], "literal-title-style-words"
        )
        after = apply(client, auth, before, task)
        title = next(layer for layer in after["composition"]["pages"][0]["layers"] if layer["id"] == "scene-2-title")
        old = next(layer for layer in before["composition"]["pages"][0]["layers"] if layer["id"] == "scene-2-title")
        assert title["properties"]["text"] == literal
        assert title["properties"] == {**old["properties"], "text": literal}
        assert_other_layers_unchanged(before, after, "scene-2-title")


def test_invalid_scene_metadata_is_rejected_without_losing_project(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        composition = deepcopy(doc["composition"])
        composition["narrative"]["localProduction"]["scenes"] = {"bad": "not-a-list"}
        response = client.post(
            BASE + f"/documents/{doc['documentId']}/local-commands",
            headers={**auth, "Idempotency-Key": "invalid-scene-metadata"},
            json={
                "expectedRevision": doc["revision"],
                "commands": [{"id": "composition.replace", "params": {"composition": composition}}],
            },
        )
        assert response.status_code == 422
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == doc["revision"]


def test_scope_guard_rejects_other_layers_and_project_commands():
    from app.domain.studios.agents import AgentOperation, AgentTaskRequest
    from app.services.studios.agent_orchestrator import validate_selection_scope

    for command in [
        {"id": "layer.remove", "params": {"layerId": "not-selected"}},
        {"id": "layer.upsert", "params": {"layer": {"id": "not-selected"}}},
        {"id": "project.duration", "params": {"seconds": 20}},
        {"id": "composition.replace", "params": {"composition": {}}},
    ]:
        with pytest.raises(ValueError, match="agent_selection_scope_violation"):
            validate_selection_scope([AgentOperation.model_validate(command)], ["selected"])
    validate_selection_scope([AgentOperation(id="layer.remove", params={"layerId": "selected"})], ["selected"])
    with pytest.raises(ValueError):
        AgentTaskRequest(expectedRevision=1, instruction="test", selectedLayerIds=["x" * 121])


def test_apply_rechecks_selection_even_if_a_saved_plan_was_corrupted(monkeypatch, tmp_path):
    from app.database import SessionLocal
    from app.models import StudioGenerationJob

    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        task = selected_plan(client, auth, doc, "Mude a cor para #FF7F50", ["scene-1-title"], "scope-plan-corrupt")
        assert task["status"] == "succeeded"
        with SessionLocal() as db:
            saved = db.get(StudioGenerationJob, task["id"])
            saved.result_payload = {
                **saved.result_payload,
                "commands": [{"id": "layer.remove", "params": {"layerId": "scene-2-title"}}],
            }
            db.commit()
        response = client.post(
            BASE + f"/documents/{doc['documentId']}/agent-tasks/{task['id']}/apply",
            headers=auth,
            json={"expectedRevision": doc["revision"]},
        )
        assert response.status_code == 422 and "scope_violation" in response.text
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == doc["revision"]


def test_project_duration_with_selection_requests_clear_scope_and_does_not_edit(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        task = selected_plan(
            client,
            auth,
            doc,
            "Mude a duração do projeto para 20 segundos",
            ["scene-1-title"],
            "explicit-global-selected",
        )
        assert task["status"] == "succeeded" and task["result"]["commands"] == []
        assert "Desmarque" in task["result"]["rationale"]
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == doc["revision"]


@pytest.mark.parametrize("scene", ["cena 4", "cena 10", "cena 0", "quarta cena"])
def test_missing_scene_never_becomes_a_global_edit(monkeypatch, tmp_path, scene):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        task = plan(client, auth, doc, f"Adicione uma transição suave na {scene}", "missing-scene-selection")
        assert task["status"] == "succeeded" and task["result"]["commands"] == []
        assert "não existe" in task["result"]["rationale"]
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == doc["revision"]


def test_cancelling_plan_blocks_a_second_compute_until_it_finishes(monkeypatch, tmp_path):
    from app.database import SessionLocal
    from app.models import StudioGenerationJob

    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        task = selected_plan(client, auth, doc, "Mude a cor para #F28500", ["scene-1-title"], "cancel-inflight-plan")
        with SessionLocal() as db:
            row = db.get(StudioGenerationJob, task["id"])
            row.status = "cancel_requested"  # Contract fixture: remote compute has not returned yet.
            db.commit()
        response = client.post(
            BASE + f"/documents/{doc['documentId']}/agent-tasks",
            headers={**auth, "Idempotency-Key": "blocked-second-inference"},
            json={"expectedRevision": doc["revision"], "instruction": "Mude a duração para 20 segundos"},
        )
        assert response.status_code == 409 and "agent_workspace_busy_or_interrupted_task" in response.text


def test_committed_legacy_apply_replays_without_performing_a_new_out_of_scope_edit(monkeypatch, tmp_path):
    from app.database import SessionLocal
    from app.domain.studios.agents import LocalCommandsRequest
    from app.models import CreativeDocument, StudioGenerationJob, User
    from app.services.studios.agent_orchestrator import commit_commands

    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        task = selected_plan(client, auth, doc, "Mude a cor para #F28500", ["scene-1-title"], "legacy-replay-task")
        with SessionLocal() as db:
            saved = db.get(StudioGenerationJob, task["id"])
            # Synthetic receipt fixture for a plan committed before the scope guard.
            commands = [{"id": "project.background", "params": {"color": "#101010"}}]
            saved.result_payload = {**saved.result_payload, "commands": commands}
            db.commit()
            committed = commit_commands(
                db,
                db.get(CreativeDocument, doc["documentId"]),
                LocalCommandsRequest(expectedRevision=doc["revision"], commands=commands),
                db.get(User, saved.requested_by),
                "agent-apply:" + task["id"],
            )
        replayed = apply(client, auth, doc, task)
        assert replayed == committed
        assert (
            client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"]
            == committed["revision"]
        )


@pytest.mark.parametrize("question", ['Explique o título "Coral sem sombra"', 'Qual é a fonte do texto "Exemplo"?'])
def test_informational_question_never_becomes_an_edit(monkeypatch, tmp_path, question):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        task = selected_plan(client, auth, doc, question, ["scene-1-title"], "informational-not-command")
        assert task["status"] == "succeeded" and task["result"]["commands"] == []
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == doc["revision"]
