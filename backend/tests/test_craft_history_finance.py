import json
from types import SimpleNamespace

import httpx
import pytest

from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.studios import craft_history, llm_connections
from app.services.studios.external_policy import committed, reconcile_craft_job
from app.services.studios.craft_learning import promote_local_test


def test_token_count_sends_same_multimodal_input_without_message_submission():
    seen = []
    def respond(request):
        seen.append(request)
        assert request.url.path == "/v1/messages/count_tokens"
        payload = json.loads(request.content)
        assert payload["thinking"] == {"type": "adaptive"}
        assert payload["messages"][0]["content"][0]["source"]["data"] == "fixture"
        assert "stream" not in payload and "max_tokens" not in payload
        assert request.headers["x-api-key"] == "local-test-only"
        return httpx.Response(200, json={"input_tokens": 405})
    config = {"protocol": "anthropic_messages", "models": ["claude-opus-5-5"],
              "baseUrl": "https://api.anthropic.com/v1", "authHeader": "x-api-key", "authPrefix": ""}
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        planner = UniversalLLMPlanner(config, "local-test-only", client=client)
        assert planner.count_craft_tokens("claude-opus-5-5", "direction", [{
            "role": "user", "content": [{"type": "image", "source": {"data": "fixture"}}],
        }], [], 5) == 405
    assert len(seen) == 1


@pytest.mark.parametrize(("model", "thinking", "choice"), [
    ("claude-sonnet-5-5", {"type": "between_tools"}, {"type": "auto"}),
    ("claude-haiku-5-5", None, {"type": "tool", "name": "deliver"}),
])
def test_specialist_tool_choice_respects_model_capabilities(model, thinking, choice):
    payload = {"model": model, "thinking": {"type": "adaptive"}}
    UniversalLLMPlanner._craft_tool_choice(payload, "deliver")
    assert payload.get("thinking") == thinking
    assert payload["tool_choice"] == choice


def test_context_renewal_preserves_plan_and_latest_batch_pixels_without_tool_pairs():
    context = {"instruction": "Original copy", "savedEditorialPlan": "old", "continuation": "old"}
    result = {"editorialPlan": "new plan", "tools": [
        {"name": "preview_sequence", "ok": True, "draftBatch": 4, "sample": {"seconds": [2, 7]}},
    ]}
    messages = [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "edit", "name": "edit_project"}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "edit", "content": "done"}]},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "preview", "name": "preview_sequence"}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "preview",
                                     "content": [{"type": "image", "source": {"data": "latest"}}]}]},
    ]
    first = craft_history.compact_messages(context, {"layers": [{"id": 12}]}, 4, result, messages=messages)
    second = craft_history.compact_messages({**context, "continuation": "new"}, {"layers": []}, 5, {}, messages=())
    assert first[0]["content"][0] == second[0]["content"][0]
    assert json.loads(first[0]["content"][1]["text"])["editorialPlan"] == "new plan"
    assert first[0]["content"][-1]["source"]["data"] == "latest"
    renewed = craft_history.compact_messages(context, {"layers": [{"id": 12}]}, 4, result, messages=first)
    assert renewed[0]["content"][-1]["source"]["data"] == "latest"
    changed = craft_history.compact_messages(context, {"layers": []}, 5, result, messages=first)
    assert "latest" not in json.dumps(changed)
    assert context["savedEditorialPlan"] == "old"
    assert craft_history.should_count_tokens(messages)
    assert craft_history.should_compact(messages, counted_tokens=50000)


def test_contact_sheet_is_counted_before_it_triggers_context_renewal():
    messages = [{"role": "user", "content": "brief"}, {"role": "assistant", "content": []},
                {"role": "user", "content": [{"type": "tool_result", "content": [
                    {"type": "image", "source": {"data": "a" * 400000}},
                ]}]}]
    assert craft_history.should_count_tokens(messages)
    assert not craft_history.should_compact(messages, counted_tokens=12000)


def test_motion_cache_breakpoint_stays_before_changing_evidence():
    context = {"instruction": "Keep the brief", "registeredAssets": ["old"], "recentActions": ["preview"]}
    first = craft_history.start_message(context, prompt_cache=True)[0]["content"]
    context["registeredAssets"] = ["new"]
    renewed = craft_history.compact_messages(context, {}, 2, {}, prompt_cache=True)[0]["content"]
    assert first[0] == renewed[0] == {"type": "text", "text": '{"instruction":"Keep the brief"}',
                                      "cache_control": {"type": "ephemeral"}}
    assert json.loads(renewed[1]["text"])["registeredAssets"] == ["new"]


def test_review_state_counts_only_successful_previews_on_the_current_revision():
    previews = [{"name": "preview_sequence", "ok": True, "draftBatch": 3},
                {"name": "preview_frame", "ok": True, "draftBatch": 3},
                {"name": "preview_sequence", "ok": False, "draftBatch": 3},
                {"name": "review_clip", "ok": True, "draftBatch": 3, "sample": {"assetId": "source"}},
                {"name": "review_clip", "ok": True, "draftBatch": 3, "reusedToolUseId": "clip"},
                {"name": "review_clip", "ok": True, "draftBatch": 2, "sample": {"page": 1}}]
    assert craft_history.reviewed_draft(previews, 3)["completedReviews"] == 2
    assert craft_history.draft_reviews(previews, 3) == previews[:2]
    assert craft_history.reviewed_draft(previews, 4) is None


def test_editorial_snapshot_is_cached_and_survives_temporal_review_compaction():
    context = {"instruction": "Edit", "editorialContext": {"repertoireVersion": "v2", "styleGuides": [{"version": 3}]}}
    first = craft_history.start_message(context, prompt_cache=True)[0]["content"][0]
    messages = [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "clip", "name": "review_clip"}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "clip", "content": [
            {"type": "image", "source": {"data": "temporal-page"}},
        ]}]},
    ]
    messages.extend([
        {"role": "assistant", "content": [{"type": "tool_use", "id": "source", "name": "review_clip",
                                            "input": {"assetId": "source-asset"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "source", "content": [
            {"type": "image", "source": {"data": "source-page"}},
        ]}]},
    ])
    result = {"tools": [{"name": "review_clip", "ok": True, "draftBatch": 2, "sample": {"page": 3}}]}
    compact = craft_history.compact_messages(context, {}, 2, result, messages=messages, prompt_cache=True)
    assert compact[0]["content"][0] == first
    assert json.loads(first["text"])["editorialContext"]["styleGuides"][0]["version"] == 3
    assert compact[0]["content"][-1]["source"]["data"] == "temporal-page"


def test_compaction_before_first_edit_retains_source_pixels_and_hides_audit_scripts():
    evidence = [{"type": "image", "source": {"data": "actual-source"}}]
    messages = [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "source", "name": "inspect_source_media",
                                            "input": {"assetId": "source-id", "seconds": [1]}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "source", "content": evidence}]},
    ]
    result = {"tools": [{"name": "inspect_source_media", "ok": True, "input": {"code": "huge-audit-only-script"}}]}
    compact = craft_history.compact_messages({"instruction": "Edit"}, {"layers": []}, 0, result, messages=messages)
    serialized = json.dumps(compact)
    assert "actual-source" in serialized and "source-id" in serialized
    assert "huge-audit-only-script" not in serialized
    assert "actual-source" in json.dumps(messages)
    assert "native_draft" not in serialized
    renewed = craft_history.compact_messages({"instruction": "Edit"}, {"layers": []}, 0, result, messages=compact)
    assert "actual-source" in json.dumps(renewed)
    assert "huge-audit-only-script" not in json.dumps(renewed)


def test_technical_verification_keeps_the_owners_revision_request():
    row = SimpleNamespace(status="draft", document_metadata={"craftLearning": {
        "artifact": {"checksumSha256": "verified"}, "viewerFeedback": {"comment": "The ad lost its meaning"},
    }})
    db = SimpleNamespace(scalar=lambda _: row, flush=lambda: None)
    promote_local_test(db, "knowledge", "workspace", {
        "passed": True, "artifactChecksum": "verified", "testId": "flash", "observedResult": "No flash",
    })
    assert row.status == "draft"
    assert row.document_metadata["craftLearning"]["state"] == "revision requested"


def known_job():
    return SimpleNamespace(job_type="craft_ai", provider="llm.anthropic", status="succeeded", result_payload={
        "submissionStarted": True, "submissionOutcome": "response_received",
        "financialReservationUsd": 1.5, "llmReservationUsd": 1.5, "measuredCostUsd": 0.21,
        "turns": [{"usage": {"input_tokens": 100, "output_tokens": 20}, "costUsd": 0.21}],
    })


def test_reconciliation_releases_closed_usage_and_preserves_uncertain_holds():
    job = known_job()
    assert committed(job) == 1.5
    report = reconcile_craft_job(job)
    assert report["releasedUsd"] == pytest.approx(1.29)
    assert committed(job) == pytest.approx(0.21)
    assert job.result_payload.get("providerReportedCostUsd") is None
    assert reconcile_craft_job(job) is None
    for changes in ({"submissionOutcome": "unknown"}, {"pendingTurnBudget": {"maxOutputTokens": 50}},
                    {"uncertainCostUpperBoundUsd": 0.2}, {"measuredCostUsd": 0.5}):
        job = known_job()
        job.result_payload.update(changes)
        assert reconcile_craft_job(job) is None
        assert committed(job) == 1.5


def test_console_scope_reserves_each_turn_at_child_tariff_and_keeps_liability(monkeypatch):
    monkeypatch.setattr(llm_connections, "lock_editing_budget", lambda *_: None)
    db = SimpleNamespace(refresh=lambda *_: None)
    connection = SimpleNamespace(workspace_id="w", revision=1, provider="anthropic", config={
        "enabled": True, "billingMode": "metered", "protocol": "anthropic_messages",
        "baseUrl": "https://api.anthropic.com/v1", "models": ["claude-sonnet-5-5"], "budgetUsd": 0,
        "inputUsdPerMillion": 4, "outputUsdPerMillion": 20,
    })
    job = SimpleNamespace(workspace_id="w", provider="llm.anthropic", job_type="agent_plan", request_payload={
        "llmConnectionRevision": 1, "billingPolicy": "anthropic_console", "motionExperiment": "orbita",
        "model": "claude-sonnet-5-5", "pricing": {"inputUsdPerMillion": 2, "outputUsdPerMillion": 10},
    }, result_payload={"measuredCostUsd": 0.3, "uncertainCostUpperBoundUsd": 0.2})
    llm_connections.reserve_request(db, job, connection, 1000, 1000, provider_only=True)
    assert job.result_payload["nextTurnReservationUsd"] == pytest.approx(0.012)
    assert job.result_payload["llmReservationUsd"] == pytest.approx(0.512)
    connection.config["baseUrl"] = "https://other.example/v1"
    with pytest.raises(ValueError, match="scope_invalid"):
        llm_connections.reserve_request(db, job, connection, 1000, 1000, provider_only=True)
