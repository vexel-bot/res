"""Compact read projection preserves the canonical inspector and legacy evidence."""
# ruff: noqa: F811
import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_editor_commands import applied as applied
from test_editor_commands import command

from app.database import SessionLocal
from app.models import CreativeDocument
from app.services.studios import contextual_editing as plans
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.editor_commands import _evaluation_summary


@pytest.mark.parametrize("raw, expected", [
    ({"technical": {"status": "passed", "rendererChecks": [1, 2]}, "human": "pending"},
     ("passed", None, "pending")),
    ({"technical": "pending", "audiovisual": {"status": "rejected"}, "human": {"status": "not_assessed"}},
     ("pending", "rejected", "not_assessed")),
    ({"technical": "passed", "human": {"score": 5}}, ("passed", None, None)),
    ({"technical": {"status": True}, "audiovisual": 4, "human": False}, (None, None, None)),
    ({}, (None, None, None)),
])
def test_summary_preserves_explicit_axis_states_without_inference(raw, expected):
    summary = _evaluation_summary(raw, "document/a é", 4)
    assert (summary["technical"], summary["audiovisual"], summary["human"]) == expected
    assert summary["schemaVersion"] == "studio.editor-evaluation-summary.v1"
    assert summary["detail"] == "summary"
    assert summary["fullInspectionPath"] == (
        "/api/v1/studios/v1/documents/document%2Fa%20%C3%A9/editor/inspection?frame=4"
    )


def test_summary_api_changes_only_evaluation_and_schema_and_full_is_default(client, applied):
    with SessionLocal() as db:
        record = db.get(CreativeDocument, applied["document"])
        current = plans.get_plan(db, record.workspace_id, applied["inspection"]["planId"])
        current.evaluation = {"technical": {"status": "passed", "rendererChecks": {"probe": "x" * 100_000}},
                              "audiovisual": "pending", "human": "pending"}
        plans._save(db, record, current, None)
        db.commit()
    for frame in [0, 4, 14]:
        path = applied["base"] + f"/editor/inspection?frame={frame}"
        full_response = client.get(path, headers=applied["headers"])
        explicit = client.get(path + "&evaluationDetail=full", headers=applied["headers"])
        summary_response = client.get(path + "&evaluationDetail=summary", headers=applied["headers"])
        assert full_response.status_code == explicit.status_code == summary_response.status_code == 200
        full, summary = full_response.json(), summary_response.json()
        assert full == explicit.json()
        assert full["schemaVersion"] == "studio.editor-inspection.v1"
        assert summary["schemaVersion"] == "studio.editor-inspection.v2"
        assert full["evaluation"]["technical"]["rendererChecks"]["probe"] == "x" * 100_000
        assert summary["evaluation"]["technical"] == "passed" and summary["evaluation"]["human"] == "pending"
        assert summary["evaluation"]["fullInspectionPath"].endswith(f"?frame={frame}")
        assert {k: v for k, v in summary.items() if k not in {"schemaVersion", "evaluation"}} == {
            k: v for k, v in full.items() if k not in {"schemaVersion", "evaluation"}}
        assert len(full_response.content) - len(summary_response.content) > 99_000


def test_summary_api_rejects_invalid_option_frame_and_outsider(client, applied):
    from conftest import register

    path = applied["base"] + "/editor/inspection"
    for query in ["?evaluationDetail=unknown", "?frame=-1&evaluationDetail=summary",
                  "?frame=15&evaluationDetail=summary"]:
        assert client.get(path + query, headers=applied["headers"]).status_code == 422
    assert client.get(path + "?evaluationDetail=summary").status_code == 401
    outsider_token, _ = register(client, "summary-outsider@example.com")
    outsider_headers = {"Authorization": "Bearer " + outsider_token}
    assert client.get(path + "?evaluationDetail=summary", headers=outsider_headers).status_code == 404


def test_summary_keeps_plan_document_binding_guards(client, applied):
    with SessionLocal() as db:
        record = db.get(CreativeDocument, applied["document"])
        doc = record_to_contract(record)
        doc.revision += 1
        persist_contract(record, doc)
        db.commit()
    path = applied["base"] + "/editor/inspection"
    full = client.get(path, headers=applied["headers"])
    summary = client.get(path + "?evaluationDetail=summary", headers=applied["headers"])
    assert full.status_code == summary.status_code == 409
    assert full.json() == summary.json()


def test_command_and_summary_keep_exact_revision_document_and_review_pending(client, applied):
    response = client.post(applied["base"] + "/editor/commands", headers=applied["headers"], json=command(applied))
    assert response.status_code == 200
    receipt = response.json()
    result = client.get(applied["base"] + "/editor/inspection?frame=4&evaluationDetail=summary",
                        headers=applied["headers"])
    assert result.status_code == 200
    snapshot = result.json()
    assert snapshot["document"]["revision"] == receipt["documentRevision"]
    assert snapshot["planRevision"] == receipt["planRevision"]
    assert snapshot["documentDigest"] == receipt["documentDigest"]
    assert snapshot["document"]["review"]["status"] == "draft"
    assert snapshot["evaluation"]["human"] == "pending"
    assert snapshot["history"][0]["commandId"] == receipt["commandId"]
