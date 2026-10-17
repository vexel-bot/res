# ruff: noqa: F811
import json

import httpx
import pytest
from pydantic import SecretStr
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_editing_resources import enable, headers
from test_scene_compiler_v2 import direction

from app.config import get_settings
from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios.editing_ai import CompatibleEditingPlanner, compatible_binding
from app.services.studios.gemini_editing import compact_critique_plan, compact_revision_context
from app.services.studios.jobs import execute_job_once, retry_job


def configure(monkeypatch):
    enable(monkeypatch)
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_editing_ai_planning_provider", "compatible")
    monkeypatch.setattr(settings, "studio_editing_ai_base_url", "http://127.0.0.1:8089/v1")
    monkeypatch.setattr(settings, "studio_editing_ai_model", "local-vision-pinned")
    monkeypatch.setattr(settings, "studio_editing_ai_test_key", SecretStr("local-test"))
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 2)
    monkeypatch.setattr(settings, "studio_editing_ai_price_version", "test-v1")
    monkeypatch.setattr(settings, "studio_editing_ai_input_usd_per_million", 0.10)
    monkeypatch.setattr(settings, "studio_editing_ai_output_usd_per_million", 0.40)
    return settings


def test_critique_context_keeps_scene_evidence_without_material_payloads():
    plan = direction(kind="video", text="Evidence")

    compact = compact_critique_plan(plan)

    assert compact["intent"] == plan.intent.model_dump(mode="json", by_alias=True)
    assert compact["scenes"][0]["elements"][0]["id"] == plan.scenes[0].elements[0].id
    assert "materialNeeds" not in compact["scenes"][0]
    assert "animations" not in compact["scenes"][0]["elements"][0]
    assert len(json.dumps(compact)) < len(plan.model_dump_json())


def test_revision_context_omits_history_and_redundant_evidence():
    context = {
        "document": {
            "schemaVersion": "creative-document.v1",
            "documentId": "doc-1",
            "workspaceId": "ws-1",
            "revision": 4,
            "composition": {"pages": [{"id": "page-1", "width": 720, "height": 1280}]},
            "assets": [
                {
                    "id": "asset-1",
                    "mediaType": "video/mp4",
                    "checksum": "a" * 64,
                    "rightsStatus": "verified",
                    "largeHistoricalPayload": "x" * 10_000,
                }
            ],
            "versions": [{"payload": "x" * 10_000}],
        },
        "sampling": [{"payload": "x" * 10_000}],
        "transcripts": [{"payload": "x" * 10_000}],
        "compositionExamples": [{"payload": "x" * 10_000}],
        "preliminaryMaterialInventory": [{"payload": "x" * 10_000}],
        "materialProviders": [
            {"id": "pexels", "configured": True, "capabilities": ["video"], "verbose": "x" * 10_000}
        ],
    }

    compact = compact_revision_context(context)

    assert compact["document"]["assets"] == [
        {
            "id": "asset-1",
            "mediaType": "video/mp4",
            "checksum": "a" * 64,
            "rightsStatus": "verified",
        }
    ]
    assert "versions" not in compact["document"]
    assert compact["sampling"] == []
    assert compact["transcripts"] == []
    assert compact["compositionExamples"] == []
    assert compact["preliminaryMaterialInventory"] == []
    assert compact["materialProviders"] == [
        {"id": "pexels", "configured": True, "capabilities": ["video"]}
    ]


def test_rejected_response_and_usage_survive_reload_without_resubmission(client, project, monkeypatch):
    configure(monkeypatch)
    calls = []

    def invalid_plan(*args):
        calls.append(1)
        return {"text": "not valid JSON", "usage": {"total_tokens": 73}}

    monkeypatch.setattr(CompatibleEditingPlanner, "plan", invalid_plan)
    identifier = submit(client, project).json()["id"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, identifier)
        execute_job_once(db, job)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, identifier)
        assert job.result_payload["responseKey"]
        assert job.result_payload["usage"]["total_tokens"] == 73
        if job.status == "failed":
            retry_job(db, job, job.requested_by)
        execute_job_once(db, job)
    assert len(calls) == 1


@pytest.mark.parametrize("host,expected", [("api.openai.com", "json_schema"), ("example.com", "json_object")])
def test_schema_output_is_scoped_to_supported_endpoint(host, expected):
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}

    def respond(request):
        body = json.loads(request.content)
        assert body["response_format"]["type"] == expected
        if expected == "json_schema":
            assert body["response_format"]["json_schema"]["strict"] is True
            strict_schema = body["response_format"]["json_schema"]["schema"]
            assert strict_schema["required"] == ["answer"]
            assert strict_schema["additionalProperties"] is False
            user_text = body["messages"][1]["content"][0]["text"]
            assert "outputSchema" not in json.loads(user_text)
        return httpx.Response(
            200,
            json={"model": "pinned", "choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"ok"}'}}]},
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        planner = CompatibleEditingPlanner(f"https://{host}/v1", "test", client=http)
        assert planner.plan("pinned", {"outputSchema": schema}, [])["text"]


def test_compatible_provider_returns_definitive_truncation_for_persisted_reconciliation():
    def respond(request):
        return httpx.Response(
            200,
            json={
                "model": "pinned",
                "choices": [{"finish_reason": "length", "message": {"content": '{"partial":true}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        result = CompatibleEditingPlanner("https://api.openai.com/v1", "test", client=http).plan(
            "pinned", {}, []
        )
    assert result["finishReason"] == "length"
    assert result["usage"]["completion_tokens"] == 20


def submit(client, project, operation="plan"):
    return client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-ai-jobs",
        headers=headers(project),
        json={
            "expectedDocumentRevision": 1,
            "operation": operation,
            "prompt": "Explicar o conteúdo preservando a ressalva",
            "direction": {"expectedDocumentRevision": 1, "intent": {"objective": "Explicar"}},
        },
    )


def test_independent_roles_and_default_gemini(client, project, monkeypatch):
    configure(monkeypatch)
    status = client.get("/api/v1/studios/v1/editing/ai", headers=headers(project)).json()
    assert status["selectedProvider"] == "gemini"
    assert status["stages"]["plan"]["provider"] == "compatible"
    assert status["stages"]["edit_video"]["provider"] == "gemini"
    assert status["renderer"]["requiresAI"] is False
    assert status["automaticFallback"] is False
    monkeypatch.setattr(get_settings(), "studio_editing_ai_video_provider", "none")
    denied = submit(client, project, "generate_video")
    assert denied.status_code == 422
    assert denied.json()["detail"]["alternatives"]


def test_alternate_planner_compiles_and_renders_without_gemini(client, project, monkeypatch):
    settings = configure(monkeypatch)
    monkeypatch.setattr(settings, "studio_gemini_enabled", False)
    monkeypatch.setattr(settings, "studio_gemini_test_key", None)
    captured = []

    def plan(self, model, context, frames):
        captured.append((model, context, frames))
        assert frames and frames[0][0].is_file()
        return {
            "text": json.dumps(
                {
                    "beats": [{"id": "scene", "clipId": "clip", "purpose": "Explicar"}],
                    "rationale": "Preservar a fala original",
                }
            ),
            "usage": {"total_tokens": 42},
        }

    monkeypatch.setattr(CompatibleEditingPlanner, "plan", plan)
    response = submit(client, project)
    assert response.status_code == 202, response.text
    identifier = response.json()["id"]
    assert submit(client, project).json()["id"] == identifier
    with SessionLocal() as db:
        task = db.get(StudioGenerationJob, identifier)
        assert task.provider == "compatible.editing-planner"
        assert execute_job_once(db, task) == "succeeded", task.error_message
        result = task.result_payload
        assert result["usage"]["total_tokens"] == 42
        plan = result["plan"]
        assert plan["status"] == "ready", plan["blockers"]
        assert any(e.get("provider") == task.provider for e in plan["editorialEvidence"])
    applied = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/apply",
        headers=headers(project),
        json={"expectedPlanRevision": plan["revision"]},
    )
    assert applied.status_code == 200, applied.text
    rendered = client.post(
        "/api/v1/studios/v1/video-renders",
        headers=headers(project),
        json={
            "workspaceId": project["workspace"],
            "documentId": project["document"],
            "expectedDocumentRevision": 2,
            "expectedDocumentVersion": 1,
            "contextualPlanId": plan["id"],
            "provider": "builtin.ffmpeg-contextual-v1",
            "output": {"width": 320, "height": 320, "fps": 25},
        },
    )
    assert rendered.status_code == 202, rendered.text
    with SessionLocal() as db:
        task = db.get(StudioGenerationJob, rendered.json()["id"])
        assert execute_job_once(db, task) == "succeeded", task.error_message
    assert len(captured) == 1


def test_changed_endpoint_cannot_receive_existing_job(client, project, monkeypatch):
    settings = configure(monkeypatch)
    response = submit(client, project)
    monkeypatch.setattr(settings, "studio_editing_ai_base_url", "http://127.0.0.1:8090/v1")
    with SessionLocal() as db:
        task = db.get(StudioGenerationJob, response.json()["id"])
        assert execute_job_once(db, task) == "failed"
        assert task.error_message == "editing_ai_provider_binding_conflict"
        assert not (task.result_payload or {}).get("submissionStarted")


def test_replay_after_provider_switch_returns_original_job(client, project, monkeypatch):
    settings = configure(monkeypatch)
    original = submit(client, project)
    monkeypatch.setattr(settings, "studio_editing_ai_planning_provider", "gemini")
    replay = submit(client, project)
    assert replay.status_code == 202, replay.text
    assert replay.json()["id"] == original.json()["id"]
    assert replay.json()["provider"] == "compatible.editing-planner"


def test_timeout_never_switches_or_reposts(client, project, monkeypatch):
    configure(monkeypatch)
    calls = []

    def timeout(*args):
        calls.append(True)
        raise ValueError("editing_ai_transport_outcome_unknown")

    monkeypatch.setattr(CompatibleEditingPlanner, "plan", timeout)
    response = submit(client, project)
    with SessionLocal() as db:
        task = db.get(StudioGenerationJob, response.json()["id"])
        for _ in range(3):
            execute_job_once(db, task)
        retry_job(db, task, task.requested_by)
        execute_job_once(db, task)
        assert task.provider == "compatible.editing-planner"
        assert "outcome_unknown" in task.error_message
    assert len(calls) == 1


def test_definitive_http_rejection_can_retry_without_manual_reconciliation(client, project, monkeypatch):
    configure(monkeypatch)
    calls = []

    def rejected(*args):
        calls.append(True)
        raise ValueError("editing_ai_http_429")

    monkeypatch.setattr(CompatibleEditingPlanner, "plan", rejected)
    identifier = submit(client, project).json()["id"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, identifier)
        outcome = execute_job_once(db, job)
        assert outcome == "retrying", {
            "outcome": outcome,
            "attempts": job.attempts,
            "maxAttempts": job.max_attempts,
            "error": job.error_message,
            "result": job.result_payload,
        }
        assert job.result_payload["submissionOutcome"] == "rejected"
        assert job.result_payload["providerHttpStatus"] == 429
        while job.status == "retrying":
            execute_job_once(db, job)
        assert job.status == "failed"
        assert job.result_payload["submissionOutcome"] == "rejected"
        attempts_before_manual_retry = len(calls)
        retry_job(db, job, job.requested_by)
        assert execute_job_once(db, job) == "failed"
        assert "outcome_unknown" not in (job.error_message or "")
    assert len(calls) == attempts_before_manual_retry + 1


def test_insufficient_quota_is_terminal_on_the_first_rejection(client, project, monkeypatch):
    configure(monkeypatch)
    calls = []

    def rejected(*args):
        calls.append(True)
        raise ValueError("editing_ai_http_429:insufficient_quota")

    monkeypatch.setattr(CompatibleEditingPlanner, "plan", rejected)
    identifier = submit(client, project).json()["id"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, identifier)
        assert execute_job_once(db, job) == "failed"
        assert job.attempts == 1
        assert job.result_payload["providerErrorKind"] == "insufficient_quota"
        assert job.result_payload["submissionOutcome"] == "rejected"
    assert calls == [True]


def test_compatible_transport_is_bounded_and_validates_model():
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.path == "/v1/chat/completions"
        assert json.loads(request.content)["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={
                "model": "pinned",
                "choices": [{"finish_reason": "stop", "message": {"content": '{"beats":[],"rationale":"Silêncio"}'}}],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = CompatibleEditingPlanner("http://127.0.0.1/v1", "secret", client=client)
        assert json.loads(adapter.plan("pinned", {}, [])["text"])["rationale"] == "Silêncio"
        with pytest.raises(ValueError, match="model_mismatch"):
            adapter.plan("another-model", {}, [])
    assert len(calls) == 2


def test_compatible_transport_enforces_prompt_and_output_bounds():
    def respond(request):
        body = json.loads(request.content)
        assert body["max_tokens"] == 512
        return httpx.Response(
            200,
            json={
                "model": "pinned",
                "choices": [{"finish_reason": "stop", "message": {"content": '{"rationale":"ok"}'}}],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = CompatibleEditingPlanner("https://example.com/v1", "secret", client=client)
        adapter.plan("pinned", {"maxOutputTokens": 512, "maxPromptChars": 1_000}, [])
        with pytest.raises(ValueError, match="prompt_too_large"):
            adapter.plan("pinned", {"payload": "x" * 2_000, "maxPromptChars": 1_000}, [])


def test_compatible_transport_allows_contextual_v2_output_budget():
    def respond(request):
        body = json.loads(request.content)
        assert body["max_tokens"] == 10_240
        return httpx.Response(
            200,
            json={
                "model": "pinned",
                "choices": [{"finish_reason": "stop", "message": {"content": '{"rationale":"ok"}'}}],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = CompatibleEditingPlanner("https://example.com/v1", "secret", client=client)
        adapter.plan("pinned", {"maxOutputTokens": 10_240}, [])


def test_compatible_transport_exposes_only_sanitized_http_error_kind():
    def respond(_request):
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": "Sensitive provider detail must not enter the job log",
                    "type": "tokens",
                    "code": "rate_limit_exceeded",
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = CompatibleEditingPlanner("https://api.openai.com/v1", "secret", client=client)
        with pytest.raises(ValueError, match="editing_ai_http_429:rate_limit_exceeded"):
            adapter.plan("pinned", {"maxOutputTokens": 1000}, [])


def test_official_openai_transport_uses_the_reserved_structured_output_budget():
    def respond(request):
        body = json.loads(request.content)
        assert body["max_tokens"] == 14_000
        return httpx.Response(
            200,
            json={
                "model": "gpt-4.1-2025-04-14",
                "choices": [{"finish_reason": "stop", "message": {"content": '{"rationale":"ok"}'}}],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = CompatibleEditingPlanner("https://api.openai.com/v1", "secret", client=client)
        adapter.plan("gpt-4.1-2025-04-14", {"maxOutputTokens": 14_000}, [])


def test_provider_configuration_preserves_production_policy(monkeypatch):
    settings = configure(monkeypatch)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "studio_editing_ai_base_url", "https://api.openai.com/v1")
    with pytest.raises(ValueError, match="local_tests_only"):
        compatible_binding(settings)
    monkeypatch.setattr(settings, "studio_editing_ai_base_url", "https://provider.example/v1")
    with pytest.raises(ValueError, match="key_required"):
        compatible_binding(settings)


def test_versioned_request_keeps_legacy_idempotency_serialization():
    from app.domain.studios.editing_resources import EditingAIRequestV1, GeminiEditingRequestV1

    payload = {"expectedDocumentRevision": 1, "operation": "generate_image", "prompt": "Produto"}
    assert "schemaVersion" not in GeminiEditingRequestV1.model_validate(payload).model_dump(by_alias=True)
    assert (
        EditingAIRequestV1.model_validate(payload).model_dump(by_alias=True)["schemaVersion"]
        == "studio.editing-ai-request.v1"
    )
