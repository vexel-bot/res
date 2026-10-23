"""Stage 3 deterministic regressions. Never substitutes for authenticated UI QA."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from test_local_agent_stage2 import selected_plan
from test_local_agents import BASE, apply, create, plan, prepare

from app.studio_app import app


def motion(client, auth):
    doc, _ = create(client, auth)
    return apply(client, auth, doc, plan(client, auth, doc, "Crie um motion de 15 segundos"))


def test_history_undo_is_reviewed_versioned_idempotent_and_preserves_other_layers(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        before = motion(client, auth)
        edit = selected_plan(client, auth, before, "Mude a cor para coral", ["scene-2-card"], "stage3-color")
        changed = apply(client, auth, before, edit)
        read_before = client.get(BASE + f"/documents/{changed['documentId']}", headers=auth).json()
        undo = plan(client, auth, changed, "Desfaça a última alteração.", "stage3-undo")
        assert undo["result"]["commands"], undo
        assert undo["result"]["inference"] == "none"
        # Planning never mutates the document.
        assert client.get(BASE + f"/documents/{changed['documentId']}", headers=auth).json() == read_before
        restored = apply(client, auth, changed, undo)
        assert restored["composition"] == before["composition"]
        assert restored["revision"] == changed["revision"] + 1
        assert apply(client, auth, changed, undo) == restored
        versions = client.get(BASE + f"/documents/{changed['documentId']}/versions", headers=auth).json()
        assert len(versions) >= 3


def test_history_undo_does_not_override_a_selection(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        undo = selected_plan(client, auth, doc, "Desfaça a última alteração", ["scene-2-card"], "undo-selection")
        assert not undo["result"]["commands"]
        assert "desmarque" in undo["result"]["rationale"].lower()


def test_undo_without_history_is_an_explicit_noop(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, _ = create(client, auth)
        task = plan(client, auth, doc, "Desfaça a última alteração", "undo-empty")
        assert not task["result"]["commands"]
        assert "anterior" in task["result"]["rationale"]
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 1


def test_undo_cannot_remove_a_current_layer_lock(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        layer = deepcopy(doc["composition"]["pages"][0]["layers"][0])
        layer["locked"] = True
        response = client.post(
            BASE + f"/documents/{doc['documentId']}/local-commands",
            headers={**auth, "Idempotency-Key": "lock-before-undo"},
            json={
                "expectedRevision": doc["revision"],
                "commands": [{"id": "layer.upsert", "params": {"layer": layer}}],
            },
        )
        assert response.status_code == 200, response.text
        locked = response.json()
        task = plan(client, auth, locked, "Desfaça a última alteração", "undo-locked")
        assert task["status"] == "failed" and task["errorCode"] == "agent_layer_locked"
        assert (
            client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == locked["revision"]
        )


@pytest.mark.parametrize(
    "instruction", ["Troque a cor do cartão selecionado", "Altere somente o título da terceira cena"]
)
def test_incomplete_requests_ask_for_the_missing_value_without_mutation(monkeypatch, tmp_path, instruction):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        read_before = client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()
        task = plan(client, auth, doc, instruction, "clarify-value")
        assert not task["result"]["commands"]
        assert "informe" in task["result"]["rationale"].lower()
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json() == read_before


def test_transition_edit_uses_only_selected_layer_and_keeps_scene_metadata(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc = motion(client, auth)
        old = deepcopy(doc)
        task = selected_plan(client, auth, doc, "Deixe as transições mais suaves", ["scene-2-card"], "transitions")
        after = apply(client, auth, doc, task)
        assert after["composition"]["narrative"] == old["composition"]["narrative"]
        for layer in after["composition"]["pages"][0]["layers"]:
            original = next(row for row in old["composition"]["pages"][0]["layers"] if row["id"] == layer["id"])
            if layer["id"] != "scene-2-card":
                assert layer == original
            else:
                assert any(
                    key["easing"] == "ease-in-out" for key in layer["properties"]["keyframes"] if "easing" in key
                )
