"""Native streaming/jobs/review/AI contracts, with isolated engine/provider boundaries."""

import json

import pytest
from conftest import register
from pydantic import SecretStr
from test_craft_studios import create, headers, migrate, native_boundary  # noqa: F401

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.craft import CraftCommandRequestV1, CraftRenderRequestV1
from app.models import CreativeDocument, User
from app.services.studios import craft, craft_ai
from app.services.studios.jobs import execute_job_once
from app.services.studios.reviews import request_review

pytestmark = pytest.mark.usefixtures("native_boundary")

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
