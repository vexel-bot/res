"""Native streaming/jobs/review/AI contracts, with isolated engine/provider boundaries."""

import json

import pytest
from conftest import register
from pydantic import SecretStr
from sqlalchemy import event, select
from sqlalchemy.exc import OperationalError
from test_craft_studios import create, headers, migrate, native_boundary  # noqa: F401

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.craft import CraftCommandRequestV1, CraftRenderRequestV1
from app.models import CreativeDocument, User
from app.services.studios import craft, craft_ai
from app.services.studios.jobs import execute_job_once
from app.services.studios.reviews import request_review

pytestmark = pytest.mark.usefixtures("native_boundary")


def test_recovered_effects_preserve_montage_archive_and_reuse_source(client):
    token, workspace = register(client, "craft-recovered-effects@example.com")
    document = create(client, token, workspace)
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"
    timeline = {"schemaVersion": "studio.media-timeline.v1", "frameRate": {"numerator": 30, "denominator": 1}, "durationFrames": 30, "tracks": []}
    layer = {"id": "overlay", "kind": "shape", "name": "Visual overlay", "x": 10, "y": 20, "width": 80, "height": 60, "properties": {"fill": "#ff0000"}}
    with SessionLocal() as db:
        record = db.get(CreativeDocument, document["documentId"])
        original = json.loads(json.dumps(record.canonical_document))
        original["contentType"] = "video"
        original["composition"]["pages"][0]["layers"] = [layer]
        original["composition"]["mediaTimeline"] = timeline
        record.canonical_document = original
        db.commit()
    migrated = client.post(base + "/craft/migrate", headers=headers(token, "recover-film-migration-001"), json={"engine": "filmcraft", "expectedRevision": 1})
    assert migrated.status_code == 200, migrated.text
    revision = migrated.json()["revision"]
    saved_timeline = client.get(base, headers=headers(token)).json()["composition"]["mediaTimeline"]
    before = client.get(base + "/native-project", headers=headers(token)).content
    payload = {"expectedRevision": revision}
    recovered = client.post(base + "/craft/recover-effects", headers=headers(token, "recover-effects-001"), json=payload)
    assert recovered.status_code == 200, recovered.text
    result = recovered.json()
    assert result["document"]["composition"]["mediaTimeline"] == saved_timeline
    assert result["requiresCompositionReview"]
    blocked = client.post(base + "/craft/render-jobs", headers=headers(token, "recover-before-link-export"), json={"expectedRevision": result["document"]["revision"], "format": "png"})
    assert blocked.status_code == 422 and "craft_pending_composition_requires_link" in blocked.text
    from app.domain.studios.contracts import CreateGenerationJobRequest
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.jobs import create_job

    with SessionLocal() as db:
        record = db.get(CreativeDocument, document["documentId"])
        forged = record_to_contract(record).model_dump(by_alias=True, mode="json")
        forged["nativeEditorState"]["dependencies"] = []
        with pytest.raises(ValueError, match="craft_render_snapshot_conflict"):
            create_job(db, CreateGenerationJobRequest(
                workspace_id=workspace, document_id=record.id, job_type="craft_render", provider="craft.filmcraft",
                request={"nativeEditorState": forged["nativeEditorState"], "documentSnapshot": forged},
            ), "recover-forged-snapshot", db.get(User, record.created_by))
    assert client.get(base + "/native-project", headers=headers(token)).content == before
    child = client.get("/api/v1/studios/v1/documents/" + result["compositionDocumentId"], headers=headers(token)).json()
    assert child["nativeEditorState"]["engine"] == "effectcraft"
    assert child["composition"]["mediaTimeline"] is None
    assert child["composition"]["pages"][0]["background"] == "#00000000"
    assert child["composition"]["pages"][0]["layers"][0]["properties"] == layer["properties"]
    replay = client.post(base + "/craft/recover-effects", headers=headers(token, "recover-effects-001"), json=payload)
    assert replay.json()["receiptId"] == result["receiptId"]
    stale = client.post(base + "/craft/recover-effects", headers=headers(token, "recover-effects-stale"), json=payload)
    assert stale.status_code == 409
    again = client.post(base + "/craft/recover-effects", headers=headers(token, "recover-effects-again"), json={"expectedRevision": result["document"]["revision"]})
    assert again.status_code == 200, again.text
    assert again.json()["compositionDocumentId"] == child["documentId"]
    assert again.json()["document"]["revision"] == result["document"]["revision"]
    with SessionLocal() as db:
        assert len(list(db.scalars(select(CreativeDocument.id)))) == 2


def test_render_commit_failure_recovers_transaction_and_records_retry(client):
    token, workspace = register(client, "craft-render-commit-failure@example.com")
    document = create(client, token, workspace)
    state = migrate(client, token, document)
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"
    original = client.get(base + "/native-project", headers=headers(token)).content
    with SessionLocal() as db:
        record = db.get(CreativeDocument, document["documentId"])
        actor = db.get(User, record.created_by)
        job, _ = craft.create_render_job(
            db, record,
            CraftRenderRequestV1(expected_revision=state["revision"], format="png"),
            actor, "render-commit-failure-01",
        )
        injected = False

        def fail_render_commit(connection):
            nonlocal injected
            if not injected and job.progress == 85:
                injected = True
                raise OperationalError("COMMIT", {}, RuntimeError("simulated disk I/O failure"))

        event.listen(db.bind, "commit", fail_render_commit)
        try:
            assert execute_job_once(db, job) == "retrying"
            assert injected
            assert job.error_code == "OperationalError"
            assert "simulated disk I/O failure" in job.error_message
            assert not (job.result_payload or {}).get("artifact")
        finally:
            event.remove(db.bind, "commit", fail_render_commit)
    assert client.get(base + "/native-project", headers=headers(token)).content == original

def test_stream_native_upload_replay_corruption_and_upload_bounds(client, monkeypatch):
    token, workspace = register(client, "craft-native-upload@example.com")
    document = create(client, token, workspace)
    state = migrate(client, token, document)
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"
    raw = json.dumps({"width": 640, "height": 480, "layers": [], "color": "saved"}).encode()
    url = base + f"/native-project?engine=photocraft&expectedRevision={state['revision']}&pageId=page-0"
    saved = client.put(url, headers=headers(token, "stream-native-save-01"), content=raw)
    assert saved.status_code == 200, saved.text
    repeated = client.put(url, headers=headers(token, "stream-native-save-01"), content=raw)
    assert repeated.json()["receiptId"] == saved.json()["receiptId"]
    assert client.get(base + "/native-project", headers=headers(token)).content == raw
    monkeypatch.setattr(get_settings(), "studio_craft_max_upload_bytes", 1024)
    bounded = client.put(url, headers=headers(token, "stream-native-bound-01"), content=b"a" * 1025)
    assert bounded.status_code == 413
    assert client.get(base + "/native-project", headers=headers(token)).content == raw


def test_render_job_immutable_snapshot_and_all_pages_review_binding(client):
    token, workspace = register(client, "craft-render-snapshot@example.com")
    document = create(client, token, workspace, 2)
    state = migrate(client, token, document)
    with SessionLocal() as db:
        record = db.get(CreativeDocument, document["documentId"])
        actor = db.get(User, record.created_by)
        job, created = craft.create_render_job(
            db,
            record,
            CraftRenderRequestV1(expected_revision=state["revision"], format="png_set"),
            actor,
            "render-snapshot-01",
        )
        assert created
        assert execute_job_once(db, job) == "succeeded", job.error_message
        rendered = craft.verified_render(db, record, job.id)
        assert rendered["format"] == "png_set"
        review = request_review(db, record, actor, render_job_id=job.id)
        assert review.render_checksum_sha256 == rendered["artifact"]["checksumSha256"]
        from app.services.studios.review_preview import render_review_page

        assert render_review_page(db, review, "page-1")[:8] == b"\x89PNG\r\n\x1a\n"
        changed = craft.commands(
            db,
            record,
            CraftCommandRequestV1(
                expected_revision=record.revision,
                commands=[{"id": "paint.set", "params": {"color": "green"}}],
                page_id="page-1",
            ),
            actor,
            "render-snapshot-edit-01",
        )
        assert changed["document"]["review"]["status"] != "approved"
        with pytest.raises(ValueError, match="studio_review_render_snapshot_mismatch"):
            craft.verified_render(db, record, job.id)
        assert render_review_page(db, review, "page-1")[:8] == b"\x89PNG\r\n\x1a\n"


def test_real_ai_planner_boundary_validated_commands_and_replay(client, monkeypatch):
    token, workspace = register(client, "craft-ai-contract@example.com")
    document = create(client, token, workspace)
    state = migrate(client, token, document)
    settings = get_settings()
    monkeypatch.setattr(craft_ai, "require_capability", craft.require_capability)
    monkeypatch.setattr(settings, "studio_editing_ai_planning_provider", "compatible")
    monkeypatch.setattr(settings, "studio_editing_ai_base_url", "http://127.0.0.1:19999/v1")
    monkeypatch.setattr(settings, "studio_editing_ai_model", "test-provider-model")
    monkeypatch.setattr(settings, "studio_editing_ai_test_key", SecretStr("test-only-key"))
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 1.0)
    monkeypatch.setattr(settings, "studio_editing_ai_input_usd_per_million", 1.0)
    monkeypatch.setattr(settings, "studio_editing_ai_output_usd_per_million", 1.0)
    for key in ("studio_external_monthly_budget_usd", "studio_external_workspace_monthly_budget_usd",
                "studio_external_user_monthly_budget_usd"):
        monkeypatch.setattr(settings, key, 5)
    monkeypatch.setattr(settings, "studio_external_model_monthly_budgets", {"test-provider-model": 5})
    calls = []

    def plan(self, model, context, media):
        calls.append(context)
        return {
            "text": json.dumps(
                {"commands": [{"id": "paint.set", "params": {"color": "green"}}], "rationale": "Requested color change"}
            ),
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }

    monkeypatch.setattr(craft_ai.CompatibleEditingPlanner, "plan", plan)
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"
    payload = {"expectedRevision": state["revision"], "instruction": "Mudar a cor para verde", "pageId": "page-0"}
    response = client.post(base + "/craft/ai-commands", headers=headers(token, "ai-command-contract-001"), json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["aiTrace"]["provider"] == "compatible.editing-planner"
    assert response.json()["aiTrace"]["usage"]["completion_tokens"] == 20
    repeated = client.post(base + "/craft/ai-commands", headers=headers(token, "ai-command-contract-001"), json=payload)
    assert repeated.json()["receiptId"] == response.json()["receiptId"] and len(calls) == 1
    assert json.loads(client.get(base + "/native-project", headers=headers(token)).content)["color"] == "green"

def test_direct_craft_session_edits_previews_corrects_and_commits_once(client, native_boundary, monkeypatch):
    from types import SimpleNamespace

    from app.services.studios import craft_agent, llm_connections

    token, workspace = register(client, "native-tool-session@example.com")
    document = create(client, token, workspace)
    state = migrate(client, token, document)
    monkeypatch.setattr(craft_ai, "require_capability", craft.require_capability)
    monkeypatch.setattr(craft_agent, "call_engine", craft.call_engine)
    connection = SimpleNamespace(id="native-tool-test", provider="anthropic", revision=1, config={
        "enabled": True, "protocol": "anthropic_messages", "billingMode": "local_free",
        "maxOutputTokens": 500, "inputUsdPerMillion": 1, "outputUsdPerMillion": 1,
    })
    real_refresh = SessionLocal.class_.refresh

    def refresh(self, instance, *args, **kwargs):
        if instance is not connection:
            return real_refresh(self, instance, *args, **kwargs)

    monkeypatch.setattr(SessionLocal.class_, "refresh", refresh)
    calls = []

    def turn(_model, _system, messages, _tools, _tokens, _seconds):
        calls.append(messages.copy())
        index = len(calls)
        name, args = {
            1: ("edit_project", {"commands": [{"id": "paint.set", "params": {"color": "blue"}}]}),
            2: ("preview_frame", {"frame": 0}),
            3: ("edit_project", {"commands": [{"id": "paint.set", "params": {"color": "green"}}]}),
        }.get(index, (None, None))
        if index == 3:
            assert messages[-1]["content"][0]["content"][0]["type"] == "image"
        if name:
            content = [{"type": "tool_use", "id": f"tool-{index}", "name": name, "input": args}]
        else:
            content = [{"type": "text", "text": "Ajustei a cor depois de conferir a prévia."}]
        return {"content": content, "stop_reason": "tool_use" if name else "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 20}, "model": "test-opus"}

    monkeypatch.setattr(llm_connections, "planner", lambda *_: (
        connection, SimpleNamespace(craft_turn=turn), "test-opus", "endpoint",
    ))
    monkeypatch.setattr(craft_agent, "reserve_request", lambda _db, job, *_args, **_kwargs: setattr(job, "result_payload", {}))
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"
    payload = {"expectedRevision": state["revision"], "instruction": "Revise e ajuste a cor", "connectionId": connection.id, "pageId": "page-0"}
    original = client.get(base + "/native-project", headers=headers(token)).content
    response = client.post(base + "/craft/ai-commands", headers=headers(token, "direct-native-session-1"), json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["document"]["revision"] == state["revision"] + 1
    assert [item["name"] for item in result["aiTrace"]["tools"]] == ["edit_project", "preview_frame", "edit_project"]
    assert result["aiTrace"]["measuredCostUsd"] == 0.00012
    assert json.loads(original)["color"] == "original"
    assert json.loads(client.get(base + "/native-project", headers=headers(token)).content)["color"] == "green"
    replay = client.post(base + "/craft/ai-commands", headers=headers(token, "direct-native-session-1"), json=payload)
    assert replay.json()["receiptId"] == result["receiptId"] and len(calls) == 4
