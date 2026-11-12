import json
import time
from types import SimpleNamespace

import pytest

from app.providers.studios.universal_llm import read_craft_stream
from app.providers.studios.craft import filmcraft_command_schema
from app.domain.studios.craft import CraftCommandV1
from app.services.studios.craft import editable_commands, validate_commands
from app.services.studios.craft_agent import can_resume, preview_frames, token_allowance, trim_previews, turn_cost
from app.services.studios.craft_compatibility import scripting_reference


def test_scripting_reference_pages_large_catalog_without_losing_filtered_commands():
    commands = [{"id": f"example.{i}"} for i in range(53)] + [{"id": "script.run"}]
    capability = {"commands": commands, "buildId": "test"}
    offset = 0
    seen = []
    while offset is not None:
        page = scripting_reference("effectcraft", capability, offset=offset)
        assert len(page["nativeCommands"]) <= 24
        assert page["totalCommands"] == len(commands)
        seen.extend(page["nativeCommands"])
        offset = page["nextOffset"]
    assert seen == commands
    result = scripting_reference("effectcraft", capability, query="script.run")
    assert result["nativeCommands"] == [{"id": "script.run"}]


def test_stream_rebuilds_tool_call_and_usage():
    events = [
        {"type": "message_start", "message": {"content": [], "usage": {"input_tokens": 22}}},
        {"type": "content_block_start", "index": 0, "content_block": {
            "type": "tool_use", "name": "preview_frame", "id": "tool-id", "input": {},
        }},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"frame":'}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "12}"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 9}},
        {"type": "message_stop"},
    ]
    result = read_craft_stream(("data: " + json.dumps(item) for item in events), time.monotonic() + 10)
    assert result["content"][0]["input"] == {"frame": 12}
    assert result["usage"] == {"input_tokens": 22, "output_tokens": 9}
    without_marker = read_craft_stream(("data: " + json.dumps(item) for item in events[:-1]), time.monotonic() + 10)
    assert without_marker == result
    with pytest.raises(ValueError, match="llm_provider_incomplete_response"):
        read_craft_stream(("data: " + json.dumps(item) for item in events[:-2]), time.monotonic() + 10)


def test_stream_accepts_empty_arguments_for_inspection_tool():
    events = [
        {"type": "message_start", "message": {"content": [], "usage": {"input_tokens": 5}}},
        {"type": "content_block_start", "index": 0, "content_block": {
            "type": "tool_use", "id": "inspect", "name": "inspect_project", "input": {},
        }},
        {"type": "content_block_delta", "index": 0,
         "delta": {"type": "input_json_delta", "partial_json": ""}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 3}},
        {"type": "message_stop"},
    ]
    message = read_craft_stream(("data: " + json.dumps(item) for item in events), time.monotonic() + 10)
    assert message["content"][0]["input"] == {}
    assert message["usage"]["output_tokens"] == 3


def test_editing_capability_comes_from_isolated_engine_and_host_owns_files():
    commands = [
        {"id": "script.run", "requiresIsolation": True},
        {"id": "prop.setExpression"},
        {"id": "effect.plugins.load", "available": False},
        {"id": "file.open"},
        {"id": "asset.import"},
    ]
    assert [item["id"] for item in editable_commands({"commands": commands})] == [
        "script.run", "prop.setExpression", "asset.import",
    ]


def test_filmcraft_move_schema_requires_native_move_objects():
    schema = filmcraft_command_schema({"id": "timeline.move", "inputSchema": {}})
    capability = {"commands": [schema]}
    valid = CraftCommandV1(id="timeline.move", params={"moves": [{"clip": 8, "track": "V2", "time": 508032000}]})
    validate_commands([valid], capability)
    with pytest.raises(ValueError, match="craft_command_params_invalid"):
        validate_commands([CraftCommandV1(id="timeline.move", params={"moves": [8]})], capability)


def test_session_does_not_offer_tokens_past_remaining_budget():
    connection = SimpleNamespace(config={
        "billingMode": "metered", "inputUsdPerMillion": 5, "outputUsdPerMillion": 25, "maxOutputTokens": 32000,
    })
    messages = [{"role": "user", "content": "Teste motion"}]
    size, tokens = token_allowance(connection, messages, 1.40)
    assert (size * 5 + tokens * 25) / 1_000_000 <= 0.10
    with pytest.raises(ValueError, match="llm_generation_budget_exceeded"):
        token_allowance(connection, messages, 1.50)


def test_budget_guard_can_resume_a_saved_draft_without_new_budget():
    job = SimpleNamespace(
        status="failed", error_code="llm_generation_budget_exceeded",
        request_payload={"generationBudgetUsd": 0.8},
        result_payload={"draft": {"batches": 4}, "measuredCostUsd": 0.68},
    )
    assert can_resume(job)
    job.result_payload["uncertainCostUpperBoundUsd"] = 0.15
    assert not can_resume(job)


def test_opus_cache_cost_uses_reported_usage_but_reserves_for_a_miss():
    pricing = {"inputUsdPerMillion": 4, "outputUsdPerMillion": 20}
    job = SimpleNamespace(request_payload={"pricing": pricing})
    connection = SimpleNamespace(config={**pricing, "billingMode": "metered", "maxOutputTokens": 32000})
    messages = [{"role": "user", "content": "Teste motion"}]
    normal_bound, _ = token_allowance(connection, messages, 1.35)
    cache_bound, tokens = token_allowance(connection, messages, 1.35, prompt_cache=True)
    assert cache_bound >= normal_bound * 1.25
    assert cache_bound * 4 + tokens * 20 <= 150_000
    usage = {"input_tokens": 1000, "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 3000,
             "output_tokens": 4000}
    assert turn_cost(job, usage, True) == pytest.approx(0.0946)
    assert turn_cost(job, usage, False) == pytest.approx(0.104)


def test_preview_times_sample_the_frames_before_and_after_the_cut():
    assert preview_frames({"seconds": [2.12, 2.2, 2.28, 11.99]}, 24, 12000) == [50, 52, 54, 287]
    with pytest.raises(ValueError, match="below 12 seconds"):
        preview_frames({"seconds": [12]}, 24, 12000)
    with pytest.raises(ValueError, match="exactly one"):
        preview_frames({"frames": [1], "seconds": [0]}, 24, 12000)


def test_preview_history_keeps_reference_and_latest_images():
    uses = [{"type": "tool_use", "id": str(n), "name": "preview_frame" if n else "view_image_asset"}
            for n in range(6)]
    results = [{"type": "tool_result", "tool_use_id": item["id"], "content": [{"type": "image"}]} for item in uses]
    messages = [{"role": "assistant", "content": uses}, {"role": "user", "content": results}]
    trim_previews(messages)
    assert [entry["tool_use_id"] for entry in results if isinstance(entry["content"], list)] == ["0", "3", "4", "5"]
    assert [entry["tool_use_id"] for entry in results] == [item["id"] for item in uses]
