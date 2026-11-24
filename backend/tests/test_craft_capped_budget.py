"""Offline controls for the explicitly capped native editing session."""
import json
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.domain.studios.craft import CraftAICommandRequestV1
from app.services.studios import llm_connections
from app.services.studios.craft_agent import (
    OPEN_ENDED_STALE_SECONDS,
    OPEN_ENDED_TURN_SECONDS,
    RESOURCE_MESSAGE_PREFIX,
    can_resume,
    resource_status,
    token_allowance,
    update_resource_message,
)


@pytest.mark.parametrize("amount", [0, -1, 10.00001, float("nan"), float("inf"), True, "5"])
def test_generation_budget_rejects_invalid_values(amount):
    with pytest.raises(ValidationError):
        CraftAICommandRequestV1(expectedRevision=1, instruction="Exportar", generationBudgetUsd=amount)


def test_additive_controls_do_not_change_legacy_defaults():
    request = CraftAICommandRequestV1(expectedRevision=1, instruction="Editar")
    assert request.generation_budget_usd is None
    assert request.execution_time_limit_seconds is None
    assert request.require_export is False
    assert resource_status(5, 1, 0, float("inf"))["executionSecondsRemaining"] is None
    explicit = CraftAICommandRequestV1(expectedRevision=1, instruction="Exportar", generationBudgetUsd=5,
                                      executionTimeLimitSeconds=3600, requireExport=True)
    assert explicit.generation_budget_usd == 5 and explicit.require_export


def test_resource_status_preserves_submitted_prefix_and_appends_latest_snapshot():
    prefix = {"type": "text", "text": "Stable briefing", "cache_control": {"type": "ephemeral"}}
    messages = [{"role": "user", "content": [prefix]}]
    update_resource_message(messages, resource_status(5, 1, .4, 300))
    assert messages[0]["content"][0] is prefix
    first = messages[0]["content"][1]
    assert json.loads(first["text"][len(RESOURCE_MESSAGE_PREFIX):])["remainingUsd"] == 3.6
    messages.extend([{"role": "assistant", "content": [{"type": "text", "text": "Editing"}]},
                     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "saved"}]}])
    update_resource_message(messages, resource_status(5, 2, .4, 200))
    assert messages[0]["content"] == [prefix, first]
    assert messages[-1]["content"][0]["tool_use_id"] == "x"
    assert json.loads(messages[-1]["content"][-1]["text"][len(RESOURCE_MESSAGE_PREFIX):])["remainingUsd"] == 2.6


def test_explicit_budget_respects_uncertainty_and_pending_turn_when_resuming():
    job = SimpleNamespace(status="failed", error_code="llm_provider_incomplete_response", request_payload={
        "generationBudgetUsd": 5, "billingMode": "metered",
        "pricing": {"inputUsdPerMillion": 4, "outputUsdPerMillion": 20},
    }, result_payload={"draft": {"batches": 1}, "measuredCostUsd": 4,
                       "uncertainCostUpperBoundUsd": .5,
                       "pendingTurnBudget": {"inputTokenBound": 50000, "maxOutputTokens": 20000}})
    assert not can_resume(job)
    job.result_payload["pendingTurnBudget"] = None
    assert can_resume(job)
    connection = SimpleNamespace(config={"billingMode": "metered", "inputUsdPerMillion": 4,
                                         "outputUsdPerMillion": 20, "maxOutputTokens": 32000})
    size, tokens = token_allowance(connection, [], 4.5, 5, tools=[], input_tokens=1000)
    assert size * 4 / 1_000_000 + tokens * 20 / 1_000_000 <= .5


def test_open_ended_resume_requires_inactivity_instead_of_total_age():
    now = datetime.now(UTC)
    job = SimpleNamespace(
        status="running", started_at=now - timedelta(days=1), updated_at=now,
        hard_time_limit_seconds=OPEN_ENDED_STALE_SECONDS,
        request_payload={"directionEffort": "open_ended", "generationBudgetUsd": 5},
        result_payload={"draft": {"batches": 1}},
    )
    assert not can_resume(job)
    job.updated_at -= timedelta(seconds=OPEN_ENDED_STALE_SECONDS + 1)
    assert can_resume(job)


def capped_reservation(monkeypatch):
    from app.services.studios import external_policy

    monkeypatch.setattr(llm_connections, "lock_editing_budget", lambda *_: None)
    monkeypatch.setattr(external_policy, "assert_operation", lambda *_args, **_kwargs: None)
    connection = SimpleNamespace(workspace_id="workspace", revision=1, provider="anthropic", config={
        "enabled": True, "billingMode": "metered", "budgetUsd": 0,
        "inputUsdPerMillion": 4, "outputUsdPerMillion": 20,
        "protocol": "anthropic_messages", "baseUrl": "https://api.anthropic.com/v1",
        "models": ["claude-opus-5-5"],
    })
    job = SimpleNamespace(workspace_id="workspace", job_type="craft_ai", provider="llm.anthropic", request_payload={
        "billingPolicy": "anthropic_console_capped", "boundedNativeSession": True,
        "generationBudgetUsd": 5, "llmConnectionRevision": 1, "model": "claude-opus-5-5",
        "pricing": {"inputUsdPerMillion": 4, "outputUsdPerMillion": 20},
    }, result_payload={"measuredCostUsd": 4.7, "uncertainCostUpperBoundUsd": .1})
    return SimpleNamespace(refresh=lambda *_: None), job, connection


def test_console_capped_reservation_uses_same_job_budget_without_connection_rewrite(monkeypatch):
    db, job, connection = capped_reservation(monkeypatch)
    llm_connections.reserve_request(db, job, connection, 1000, 9000, provider_only=True)
    assert job.result_payload["financialReservationUsd"] == pytest.approx(4.984)
    assert job.result_payload["billingPolicy"] == "anthropic_console_capped"
    assert connection.config["budgetUsd"] == 0
    with pytest.raises(ValueError, match="llm_generation_budget_exceeded"):
        llm_connections.reserve_request(db, job, connection, 1000, 10000, provider_only=True)


@pytest.mark.parametrize("field,value", [
    ("generationBudgetUsd", float("nan")), ("generationBudgetUsd", 0), ("generationBudgetUsd", 10.01),
    ("boundedNativeSession", False), ("motionExperiment", "orbita"),
])
def test_capped_reservation_cannot_become_unlimited_experiment(monkeypatch, field, value):
    db, job, connection = capped_reservation(monkeypatch)
    job.request_payload[field] = value
    with pytest.raises(ValueError, match="craft_provider_only_scope_invalid"):
        llm_connections.reserve_request(db, job, connection, 100, 100, provider_only=True)


def test_capped_reservation_rejects_foreign_workspace_and_custom_endpoint(monkeypatch):
    db, job, connection = capped_reservation(monkeypatch)
    connection.workspace_id = "foreign"
    with pytest.raises(ValueError, match="craft_provider_only_scope_invalid"):
        llm_connections.reserve_request(db, job, connection, 100, 100, provider_only=True)
    connection.workspace_id = "workspace"
    connection.config["baseUrl"] = "https://other.example/v1"
    with pytest.raises(ValueError, match="craft_provider_only_scope_invalid"):
        llm_connections.reserve_request(db, job, connection, 100, 100, provider_only=True)


def test_explicit_budget_in_swarm_is_rejected_before_any_provider_call():
    from app.services.studios.craft_ai import ai_commands
    request = CraftAICommandRequestV1(expectedRevision=1, instruction="Exportar", generationBudgetUsd=5,
                                      workflow="motion_swarm")
    with pytest.raises(ValueError, match="craft_capped_swarm_not_supported"):
        ai_commands(None, None, request, None, "key")


@pytest.mark.skipif(os.environ.get("CLICKO_TEST_REAL_CRAFT") != "1", reason="requires built EffectCraft")
@pytest.mark.parametrize("open_ended,unlimited", [(False, False), (True, False), (True, True)])
def test_capped_native_end_turn_requests_export_and_replay_does_not_renew_budget(client, monkeypatch, tmp_path, open_ended, unlimited):
    import base64
    import hashlib
    import subprocess
    from conftest import register
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import StudioGenerationJob
    from app.services.studios import craft_agent
    from app.services.studios.craft_references import reference_index

    token, workspace = register(client, "capped-native-export@example.com")
    headers = {"Authorization": "Bearer " + token}
    root = "/api/v1/studios/v1"
    sound = tmp_path / "cue.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    str(sound)], check=True)
    upload = client.post(root + "/craft/assets", headers={**headers, "Content-Type": "audio/wav"},
                         params={"workspace_id": workspace, "title": "Cue", "filename": sound.name,
                                 "media_type": "audio/wav"}, content=sound.read_bytes())
    assert upload.status_code == 201, upload.text
    sound_id = upload.json()["id"]
    created = client.post(root + "/documents", headers=headers, json={
        "workspaceId": workspace, "title": "Capped native proof", "contentType": "video",
        "brief": {"objective": "Offline export budget proof", "audience": "QA"},
        "assets": [{"id": sound_id, "version": "1", "mediaType": "audio/wav"}],
        "composition": {"pages": [{"id": "main", "width": 320, "height": 320, "durationMs": 1000,
                                  "layers": [], "background": "#0e1528"}],
                        "mediaTimeline": {"frameRate": {"numerator": 12, "denominator": 1},
                                          "durationFrames": 12, "tracks": []}},
    })
    assert created.status_code == 201, created.text
    document = created.json()
    base = root + "/documents/" + document["documentId"] + "/craft"
    migrated = client.post(base + "/migrate", headers={**headers, "Idempotency-Key": "capped-migrate"},
                           json={"engine": "effectcraft", "expectedRevision": document["revision"]})
    assert migrated.status_code == 200, migrated.text
    connection = SimpleNamespace(id="capped-offline", workspace_id=workspace, provider="anthropic", revision=1, config={
        "enabled": True, "protocol": "anthropic_messages", "billingMode": "local_free", "budgetUsd": 0,
        "baseUrl": "https://api.anthropic.com/v1", "models": ["offline-opus"],
        "maxOutputTokens": 4000, "inputUsdPerMillion": 0, "outputUsdPerMillion": 0,
    })
    real_refresh = SessionLocal.class_.refresh
    monkeypatch.setattr(SessionLocal.class_, "refresh", lambda db, instance, *args, **kwargs:
                        real_refresh(db, instance, *args, **kwargs) if instance is not connection else None)
    turns = []
    references = reference_index()

    elapsed = 0
    real_monotonic = craft_agent.time.monotonic
    if open_ended:
        monkeypatch.setattr(craft_agent, "time", SimpleNamespace(monotonic=lambda: real_monotonic() + elapsed))

    def turn(_model, _system, messages, tools, _tokens, _seconds, **options):
        nonlocal elapsed
        turns.append(json.loads(json.dumps(messages)))
        resources = [block for block in messages[-1]["content"] if block.get("type") == "text"
                     and block.get("text", "").startswith(RESOURCE_MESSAGE_PREFIX)]
        assert len(resources) == 1
        available = json.loads(resources[0]["text"][len(RESOURCE_MESSAGE_PREFIX):])
        assert available["budgetUsd"] == (None if unlimited else 5)
        if open_ended:
            assert available["executionSecondsRemaining"] is None
            assert _seconds == OPEN_ENDED_TURN_SECONDS
            if len(turns) == 1:
                assert options["effort"] == "high"
                assert "editorialPasses" in str(messages[0]["content"])
                assert "instructionAuthority" in str(messages[0]["content"])
                assert "supersedes" in str(messages[0]["content"])
            elapsed += OPEN_ENDED_STALE_SECONDS
        assert {"preview_motion_variant", "apply_motion_variant"} <= {tool["name"] for tool in tools}
        if len(turns) == 1:
            assert "relevantReferences" not in str(messages[0]["content"])
        assert "delegate_motion" not in {tool["name"] for tool in tools}
        assert {"inspect_reference", "inspect_transition"} <= {tool["name"] for tool in tools}
        if len(turns) == 1:
            return {"stop_reason": "tool_use", "model": "offline-opus", "usage": {}, "content": [
                {"type": "tool_use", "id": f"reference-{i}", "name": "inspect_reference",
                 "input": {"referenceId": item["id"]}} for i, item in enumerate(references)
            ]}
        if len(turns) == 2:
            evidence = [item["content"] for item in messages[-1]["content"] if item["type"] == "tool_result"]
            assert len(evidence) == len(references)
            for blocks in evidence:
                metadata = json.loads(blocks[0]["text"])
                assert metadata["role"] == "analysis/reference_only"
                assert hashlib.sha256(base64.b64decode(blocks[1]["source"]["data"])).hexdigest() == metadata["sha256"]
            name, args = "edit_project", {"commands": [
                {"id": "asset.import", "params": {"assetId": sound_id, "addToComp": True}},
                {"id": "script.run", "params": {"code": 'app.project.activeItem.layers.addText("ÓRBITA");'}},
            ]}
        elif open_ended and len(turns) == 3:
            name, args = "preview_sequence", {"seconds": [0.1, 0.5, 0.8]}
        elif open_ended and len(turns) == 4:
            assert any(block["type"] == "image" for block in messages[-1]["content"][0]["content"])
            name, args = "run_motion_script", {"code": 'app.project.activeItem.layer(1).name="Assinatura revisada";'}
        elif len(turns) == (5 if open_ended else 3):
            name, args = "review_clip", {"startSeconds": 0, "durationSeconds": 1, "sampling": "overview"}
        elif len(turns) == (6 if open_ended else 4):
            name, args = "review_clip", {"startSeconds": 0, "durationSeconds": 1, "sampling": "native"}
        elif len(turns) == (7 if open_ended else 5):
            if open_ended:
                assert any(block["type"] == "image" for block in messages[-1]["content"][0]["content"])
            return {"stop_reason": "end_turn", "model": "offline-opus", "usage": {},
                    "content": [{"type": "text", "text": "The edit is ready."}]}
        else:
            assert "finish_project" in str(messages[-1]["content"])
            name, args = "finish_project", {"rationale": "Exportação local solicitada pelo diretor simulado."}
        return {"stop_reason": "tool_use", "model": "offline-opus", "usage": {}, "content": [
            {"type": "tool_use", "id": f"capped-{len(turns)}", "name": name, "input": args},
        ]}

    monkeypatch.setattr(llm_connections, "planner", lambda *_: (
        connection, SimpleNamespace(craft_turn=turn), "offline-opus", "offline",
    ))
    request = {"expectedRevision": migrated.json()["revision"], "instruction": "Crie e exporte um MP4",
               "connectionId": connection.id,
               **({"unlimitedBudget": True} if unlimited else {"generationBudgetUsd": 5}),
               "requireExport": True,
               **({"directionEffort": "open_ended"} if open_ended else {"executionTimeLimitSeconds": 3600})}
    fallback_ranges = []
    if not open_ended:
        from app.services.studios import craft
        original_engine = craft.call_engine

        def memory_limited_engine(engine, method, params, **kwargs):
            if method == "render.export":
                if "reviewWindow" not in params:
                    raise craft.CraftRuntimeError("craft_runtime_failed", "Adapter exited 137")
                fallback_ranges.append(params["reviewWindow"])
            return original_engine(engine, method, params, **kwargs)

        monkeypatch.setattr(craft, "call_engine", memory_limited_engine)
    key = "capped-native-export"
    response = client.post(base + "/ai-commands", headers={**headers, "Idempotency-Key": key}, json=request)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["exportStatus"] == "succeeded"
    if not open_ended:
        assert fallback_ranges and fallback_ranges[0]["resolutionDivisor"] == 1
    assert len(turns) == (8 if open_ended else 6)
    artifact = client.get(root + "/jobs/" + result["exportJobId"], headers=headers).json()["result"]["artifact"]
    video = client.get(artifact["downloadUrl"], headers=headers)
    assert video.status_code == 200
    exported = tmp_path / "export.mp4"
    exported.write_bytes(video.content)
    streams = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                                                 "-of", "json", str(exported)]))["streams"]
    assert {item["codec_type"] for item in streams} == {"video", "audio"}
    repeated = client.post(base + "/ai-commands", headers={**headers, "Idempotency-Key": key}, json=request)
    assert repeated.status_code == 200 and repeated.json()["receiptId"] == result["receiptId"]
    assert len(turns) == (8 if open_ended else 6)
    changed = client.post(base + "/ai-commands", headers={**headers, "Idempotency-Key": key},
                          json={**request, "generationBudgetUsd": 4, **({"unlimitedBudget": False} if unlimited else {})})
    assert changed.status_code == 409, changed.text
    with SessionLocal() as db:
        job = db.scalar(select(StudioGenerationJob).where(StudioGenerationJob.idempotency_key == key))
        assert job.request_payload["generationBudgetUsd"] == (None if unlimited else 5)
        assert job.request_payload["billingPolicy"] == ("anthropic_console_native" if unlimited else "anthropic_console_capped")
        assert job.request_payload["unlimitedNativeSession"] == unlimited
        assert job.hard_time_limit_seconds == 3600
        assert job.result_payload["exportRequested"] is True
        assert job.result_payload["measuredCostUsd"] == 0
        if open_ended:
            assert elapsed > 3600
            assert job.result_payload["draft"]["batches"] == 2
            assert job.result_payload["reviewArtifacts"][0]["draftBatch"] == 2
        assert len(job.result_payload["referenceInspections"]) == len(references)
        assert not {item["assetId"] for item in job.result_payload["referenceInspections"]} & set(job.request_payload["assetIds"])
        assert any(item["name"] == "finish_project" and item["ok"] for item in job.result_payload["tools"])
