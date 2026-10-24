"""Protocol transport and tenant/credential/budget contracts; no paid calls."""
# ruff: noqa: F811 -- Shared pytest fixture is imported and injected by name.

import json

import httpx
import pytest
from conftest import register
from pydantic import SecretStr
from sqlalchemy import select
from test_craft_studios import create, headers, migrate, native_boundary  # noqa: F401

from app.config import get_settings
from app.database import SessionLocal
from app.models import Membership, StudioGenerationJob, StudioLLMConnection
from app.providers.studios.llm_catalog import PROVIDERS
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.studios.llm_connections import decrypt

BASE = "/api/v1/studios/v1/craft/llm-connections"
COMMAND = {"commands": [{"id": "paint.set", "params": {"color": "blue"}}], "rationale": "Ajuste solicitado"}


def config(protocol="openai_chat"):
    return {"protocol": protocol, "baseUrl": "https://provider.example/v1", "models": ["chosen-model"],
            "authHeader": "Authorization", "authPrefix": "Bearer", "maxOutputTokens": 1000}


def payload(protocol):
    text = json.dumps(COMMAND)
    if protocol == "openai_chat":
        return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 15, "completion_tokens": 20}, "model": "chosen-model"}
    if protocol == "openai_responses":
        return {"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": text}]},
        ],
                "usage": {"input_tokens": 15, "output_tokens": 20}}
    if protocol == "anthropic_messages":
        return {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}],
                "usage": {"input_tokens": 15, "output_tokens": 20}}
    if protocol == "gemini_generate":
        return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}],
                "usageMetadata": {"promptTokenCount": 15, "candidatesTokenCount": 20}}
    if protocol == "cohere_chat":
        return {"finish_reason": "COMPLETE", "message": {"content": [{"type": "text", "text": text}]},
                "usage": {"billed_units": {"input_tokens": 15, "output_tokens": 20}}}
    if protocol == "ollama_chat":
        return {"done": True, "message": {"content": text}, "prompt_eval_count": 15, "eval_count": 20}
    return {"result": {"text": COMMAND}, "usage": {"input_tokens": 15, "output_tokens": 20}}


@pytest.mark.parametrize("protocol", [
    "openai_chat", "openai_responses", "anthropic_messages", "gemini_generate",
    "cohere_chat", "ollama_chat", "custom_json",
])
def test_real_http_serialization_for_each_protocol(protocol):
    value = config(protocol)
    if protocol == "custom_json":
        value.update(requestPath="/infer/{model}", requestTemplate={"prompt": "${prompt}", "model": "${model}"},
                     responseTextPath="/result/text")
    requests = []

    def transport(request):
        requests.append(request)
        body = json.loads(request.content)
        assert body.get("model", "chosen-model") == "chosen-model"
        assert "Only" not in request.url.query.decode()
        assert "Return only JSON" in json.dumps(body)
        assert request.headers["Authorization"] == "Bearer test-credential"
        return httpx.Response(200, json=payload(protocol))

    client = httpx.Client(transport=httpx.MockTransport(transport))
    result = UniversalLLMPlanner(value, "test-credential", client=client).plan(
        "chosen-model", {"instruction": "Deixe azul", "maxPromptChars": 5000, "maxOutputTokens": 500}, [],
    )
    assert json.loads(result["text"]) == COMMAND
    assert result["usage"] == {"prompt_tokens": 15, "completion_tokens": 20}
    assert len(requests) == 1
    if protocol == "openai_responses":
        assert json.loads(requests[0].content)["store"] is False
    if protocol == "anthropic_messages":
        assert requests[0].headers["anthropic-version"] == "2023-06-01"
    client.close()


def test_redirect_and_error_body_never_forward_or_expose_credentials():
    seen = []

    def transport(request):
        seen.append(request)
        return httpx.Response(302, headers={"Location": "https://different.example/"}, text="test-credential")

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(ValueError, match="^llm_provider_http_302$"):
            UniversalLLMPlanner(config(), "test-credential", client=client).plan("chosen-model", {}, [])
    assert len(seen) == 1


def connection_body(**extra):
    return {"label": "Workspace planner", "provider": "custom", "protocol": "openai_chat",
            "baseUrl": "https://provider.example/v1", "models": ["chosen-model"],
            "apiKey": "private-test-credential", "enabled": True, "budgetUsd": 5,
            "inputUsdPerMillion": 1, "outputUsdPerMillion": 1, **extra}


@pytest.fixture
def encryption(monkeypatch):
    monkeypatch.setattr(
        get_settings(), "studio_llm_credential_key", SecretStr("test-only-credential-encryption-key-" * 2),
    )
    # Explicit finite envelopes for this suite's offline provider doubles.
    settings = get_settings()
    for key in ("studio_external_monthly_budget_usd", "studio_external_workspace_monthly_budget_usd",
                "studio_external_user_monthly_budget_usd"):
        monkeypatch.setattr(settings, key, 5)
    monkeypatch.setattr(settings, "studio_external_model_monthly_budgets", {"chosen-model": 5})


def test_catalog_contains_official_sources_for_at_least_ten_models(client):
    token, _ = register(client, "llm-catalog@example.com")
    response = client.get("/api/v1/studios/v1/craft/llm-catalog", headers=headers(token))
    assert response.status_code == 200
    assert len(PROVIDERS) >= 10
    assert sum(len(p["models"]) for p in response.json()["providers"]) >= 10
    assert all(p["documentationUrl"].startswith("https://") for p in PROVIDERS if p["models"])


def test_prompt_schema_compaction_keeps_property_names_and_literal_constraints():
    from app.services.studios.craft_ai import planning_schema

    original = {"type": "object", "description": "Long annotation", "properties": {
        "description": {"type": "string", "minLength": 1, "description": "Annotation"},
        "object": {"enum": [{"title": "Must remain an exact literal", "description": "Literal value"}]},
    }, "required": ["description"], "additionalProperties": False}
    compact = planning_schema(original)
    assert compact["properties"]["description"] == {"type": "string", "minLength": 1}
    assert compact["properties"]["object"]["enum"] == original["properties"]["object"]["enum"]
    assert compact["required"] == ["description"] and compact["additionalProperties"] is False


def test_credentials_are_encrypted_and_scope_bound_and_not_returned(client, encryption):
    token, workspace = register(client, "llm-owner@example.com")
    other, other_workspace = register(client, "llm-foreign@example.com")
    response = client.post(BASE, params={"workspace_id": workspace}, headers=headers(token), json=connection_body())
    assert response.status_code == 201, response.text
    connection = response.json()
    assert "private-test-credential" not in response.text and "ciphertext" not in response.text
    with SessionLocal() as db:
        row = db.get(StudioLLMConnection, connection["id"])
        assert "private-test-credential" not in row.credential_ciphertext
        assert "private-test-credential" not in json.dumps(row.config)
        assert decrypt(row) == "private-test-credential"
        row.workspace_id = other_workspace
        with pytest.raises(ValueError, match="scope_mismatch"):
            decrypt(row)
    listing = client.get(BASE, params={"workspace_id": workspace}, headers=headers(other))
    assert listing.status_code == 404
    bad = client.put(BASE + "/" + connection["id"], params={"workspace_id": workspace}, headers=headers(token),
                     json=connection_body(baseUrl="https://different.example", apiKey=None, expectedRevision=1))
    assert bad.status_code == 422 and "requires_credential" in bad.text
    malformed = client.post(BASE, params={"workspace_id": workspace}, headers=headers(token),
                            json=connection_body(models=["same", "same"]))
    assert malformed.status_code == 422 and "private-test-credential" not in malformed.text


def test_members_cannot_register_endpoints_or_change_budgets(client, encryption):
    token, workspace = register(client, "llm-member@example.com")
    with SessionLocal() as db:
        membership = db.scalar(select(Membership).where(Membership.workspace_id == workspace))
        membership.role = "member"
        db.commit()
    response = client.post(BASE, params={"workspace_id": workspace}, headers=headers(token), json=connection_body())
    assert response.status_code == 403


def test_llm_plan_uses_the_native_command_history_once(client, encryption, native_boundary, monkeypatch):
    from app.services.studios import craft, craft_ai

    monkeypatch.setattr(craft_ai, "require_capability", craft.require_capability)
    token, workspace = register(client, "llm-native@example.com")
    response = client.post(BASE, params={"workspace_id": workspace}, headers=headers(token), json=connection_body())
    assert response.status_code == 201, response.text
    connection = response.json()
    document = create(client, token, workspace)
    native = migrate(client, token, document)
    calls = []

    def plan(self, model, context, media):
        calls.append(model)
        assert context["project"].get("raw") is None
        return {"text": json.dumps(COMMAND), "usage": {"prompt_tokens": 15, "completion_tokens": 20}}

    monkeypatch.setattr(UniversalLLMPlanner, "plan", plan)
    request = {"expectedRevision": native["revision"], "instruction": "Deixe azul",
               "connectionId": connection["id"], "model": "chosen-model"}
    route = f"/api/v1/studios/v1/documents/{document['documentId']}/craft/ai-commands"
    edited = client.post(route, headers=headers(token, "llm-paid-audit-test-0001"), json=request)
    assert edited.status_code == 200, edited.text
    repeated = client.post(route, headers=headers(token, "llm-paid-audit-test-0001"), json=request)
    assert repeated.status_code == 200 and repeated.json()["receiptId"] == edited.json()["receiptId"]
    recovered = client.get(route.replace("ai-commands", "ai-requests/llm-paid-audit-test-0001"), headers=headers(token))
    assert recovered.status_code == 200 and recovered.json()["status"] == "committed"
    assert recovered.json()["receipt"]["receiptId"] == edited.json()["receiptId"]
    assert calls == ["chosen-model"]
    with SessionLocal() as db:
        job = db.scalar(select(StudioGenerationJob).where(StudioGenerationJob.job_type == "craft_ai"))
        assert job.status == "succeeded" and job.result_payload["llmReservationUsd"] > 0
        assert "private-test-credential" not in json.dumps(job.request_payload)
    bad = client.post(route, headers=headers(token, "llm-model-not-allowed-0001"), json={
        **request, "expectedRevision": edited.json()["document"]["revision"], "model": "not-registered",
    })
    assert bad.status_code == 422 and calls == ["chosen-model"]


def test_unconfigured_budget_returns_validation_error_without_calling_provider(
    client, encryption, native_boundary, monkeypatch,
):
    from app.services.studios import craft, craft_ai

    monkeypatch.setattr(craft_ai, "require_capability", craft.require_capability)
    token, workspace = register(client, "llm-zero-budget@example.com")
    response = client.post(
        BASE, params={"workspace_id": workspace}, headers=headers(token), json=connection_body(budgetUsd=0),
    )
    document = create(client, token, workspace)
    native = migrate(client, token, document)

    def forbidden(*args, **kwargs):
        raise AssertionError("A rejected budget must not submit any paid request")

    monkeypatch.setattr(UniversalLLMPlanner, "plan", forbidden)
    result = client.post(f"/api/v1/studios/v1/documents/{document['documentId']}/craft/ai-commands",
                         headers=headers(token, "llm-no-budget-request-0001"), json={
                             "expectedRevision": native["revision"], "instruction": "Deixe azul",
                             "connectionId": response.json()["id"], "model": "chosen-model",
                         })
    assert result.status_code == 422, result.text
    with SessionLocal() as db:
        job = db.scalar(select(StudioGenerationJob).where(StudioGenerationJob.job_type == "craft_ai"))
        assert job.status == "failed" and not (job.result_payload or {}).get("submissionStarted")


@pytest.mark.parametrize("invalid", [None, [], {}, {"choices": []}, {"choices": [None]}])
def test_malformed_response_is_sanitized(invalid):
    with pytest.raises(ValueError, match="^llm_provider_invalid_response$"):
        UniversalLLMPlanner(config()).normalize(invalid)


def test_provider_cannot_execute_history_or_retry_a_paid_call_after_rejection(
    client, encryption, native_boundary, monkeypatch,
):
    from app.services.studios import craft, craft_ai

    monkeypatch.setattr(craft_ai, "require_capability", craft.require_capability)
    token, workspace = register(client, "llm-rejected@example.com")
    connection = client.post(BASE, params={"workspace_id": workspace}, headers=headers(token),
                             json=connection_body()).json()
    document = create(client, token, workspace)
    native = migrate(client, token, document)
    calls = []

    def malicious(self, model, context, media):
        calls.append(model)
        assert "host.history.undo" not in {item["id"] for item in context["commands"]}
        return {"text": json.dumps({"commands": [{"id": "host.history.undo", "params": {}}]})}

    monkeypatch.setattr(UniversalLLMPlanner, "plan", malicious)
    route = f"/api/v1/studios/v1/documents/{document['documentId']}/craft/ai-commands"
    request = {"expectedRevision": native["revision"], "instruction": "Ajuste a cor",
               "connectionId": connection["id"], "model": "chosen-model"}
    for _ in range(2):
        result = client.post(route, headers=headers(token, "llm-rejected-command-0001"), json=request)
        assert result.status_code == 422 and "commands_rejected" in result.text
    assert calls == ["chosen-model"]
    status = client.get(route.replace("ai-commands", "ai-requests/llm-rejected-command-0001"), headers=headers(token))
    assert status.json()["status"] == "failed" and status.json()["receipt"] is None
    unchanged = client.get(f"/api/v1/studios/v1/documents/{document['documentId']}", headers=headers(token))
    assert unchanged.json()["revision"] == native["revision"]
