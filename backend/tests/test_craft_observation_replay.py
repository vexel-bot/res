import json

import pytest

from app.services.studios import craft_observations as observations
from app.services.studios.craft_history import compact_messages
from app.services.studios.craft_history import has_checkpoint_review
from app.services.studios.craft_history import recent_tool_exchanges
from app.services.studios.craft_history import should_compact
from app.services.studios.craft_history import retain_visible_inspections


def test_large_discovery_survives_repeated_compactions_and_process_serialization():
    args = {"commands": [{"id": "effect.list", "params": {"filter": "Blur"}}]}
    original = {"unchanged": True, "results": [{"id": "blur", "properties": "schema" * 30000}]}
    archive = {}
    identifier = observations.remember(archive, "edit_project", args, original, "build", "sha", "tool")
    result = {"observationArchive": archive, "directorContext": {"latestPlan": {"summary": "rain"}},
              "materialSearches": [{"query": "puddle", "origin": "public", "result": {"sources": [], "searchStatus": "no_matches"}}]}
    messages = []
    for _ in range(4):
        result = json.loads(json.dumps(result))
        messages = compact_messages({"instruction": "test"}, {}, 0, result, messages=messages)
        checkpoint = json.loads(messages[0]["content"][1]["text"])
        assert checkpoint["nativeObservationIndex"][0]["id"] == identifier
        assert checkpoint["materialSearches"][0]["status"] == "no_matches"
        assert len(json.dumps(messages)) < 10000
        assert observations.recall(result["observationArchive"], identifier, "build", "sha") == original
    assert observations.recall(archive, identifier, "build", "new-revision") == original
    with pytest.raises(ValueError):
        observations.recall(archive, identifier, "new-build", "sha")
    assert not observations.eligible("edit_project", {"commands": [{"id": "layer.create"}]})


def test_effect_registry_is_build_scoped_including_legacy_receipts_but_mixed_project_data_is_not():
    args = {"commands": [{"id": "effect.list", "params": {}}]}
    archive = {}
    identifier = observations.remember(archive, "edit_project", args, {"effects": ["tone"]}, "build", "old", "tool")
    assert observations.key("edit_project", args, "build", "old") == observations.key("edit_project", args, "build", "new")
    archive[identifier]["checksum"] = "old"  # Historical receipt.
    assert observations.recall(archive, identifier, "build", "new") == {"effects": ["tone"]}
    assert observations.index(archive)[0]["scope"] == "engine_build"
    mixed = {"commands": [{"id": "effect.list"}, {"id": "comp.info"}]}
    project_id = observations.remember(archive, "edit_project", mixed, {"layers": 2}, "build", "old", "other")
    with pytest.raises(ValueError):
        observations.recall(archive, project_id, "build", "new")


def test_global_contract_survives_edits_but_not_engine_upgrade():
    archive = {}
    identifier = observations.remember(archive, "describe_commands", {"ids": ["script.run"]},
        {"script.run": {"required": ["code"]}}, "build", "sha", "tool")
    assert observations.recall(archive, identifier, "build", "edited")
    with pytest.raises(ValueError):
        observations.recall(archive, identifier, "upgraded", "sha")


def test_large_effect_catalog_is_paged_and_exact_effect_remains_recoverable():
    effect = {"id": "blur", "name": "Blur", "params": ["detailed-parameter"] * 2000}
    value = {"results": [[effect for _ in range(100)]]}
    assert len(json.dumps(observations.present(value))) < 2000
    page = observations.present(value, "/results/0", offset=20, limit=10)
    assert len(page["items"]) == 10 and page["items"][0]["path"] == "/results/0/20"
    # The complete single schema is still available by pointer (and pageable further).
    assert observations.present(value, "/results/0/20/id") == "blur"
    assert value["results"][0][20] == effect


def test_review_identifiers_and_binding_survive_multiple_compactions():
    result = {"reviewArtifacts": [{"assetId": "review-asset", "checksumSha256": "video-sha", "draftBatch": 4,
        "jobId": "job", "documentRevision": 2, "report": {"source": {"nativeChecksumSha256": "native-sha"},
            "interval": {"startSeconds": 0, "durationSeconds": 14}, "audio": {"largeMeasurements": [0] * 10000}}}]}
    messages = []
    for _ in range(3):
        messages = compact_messages({"instruction": "evaluate"}, {}, 4, result, messages=messages)
        entry = json.loads(messages[0]["content"][1]["text"])["reviewArtifactIndex"][0]
        assert entry["assetId"] == "review-asset" and entry["nativeChecksumSha256"] == "native-sha"
        assert entry["interval"]["durationSeconds"] == 14
        assert "largeMeasurements" not in json.dumps(messages)
    assert has_checkpoint_review(result, {"batches": 4, "checksumSha256": "native-sha"})
    assert not has_checkpoint_review(result, {"batches": 5, "checksumSha256": "native-sha"})
    assert not has_checkpoint_review(result, {"batches": 4, "checksumSha256": "edited-sha"})


def test_compaction_preserves_recent_complete_tool_exchanges_without_signed_thinking():
    messages = []
    for i in range(4):
        messages.extend([{"role": "assistant", "content": [
            {"type": "thinking", "thinking": "opaque fixture", "signature": "old-prefix"},
            {"type": "text", "text": "Next decision " + str(i)},
            {"type": "tool_use", "id": str(i), "name": "inspect_project", "input": {"detail": "summary"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": str(i),
                "content": "Observation " + str(i)}]}])
    original = json.dumps(messages)
    compacted = compact_messages({"instruction": "Continue", "retainRecentExchanges": True}, {}, 1, {}, messages=messages)
    assert len(compacted) == 5
    inspection_ids = {("request", i): str(i) for i in range(4)}
    retain_visible_inspections(inspection_ids, compacted)
    assert list(inspection_ids.values()) == ["2", "3"]
    encoded = json.dumps(compacted)
    assert "Next decision 3" in encoded and "Observation 2" in encoded
    assert "Observation 1" not in encoded and "opaque fixture" not in encoded
    assert json.dumps(messages) == original
    assert compact_messages({"retainRecentExchanges": True}, {}, 1, {}, messages=compacted)[1:] == compacted[1:]
    incomplete = [{"role": "assistant", "content": [{"type": "tool_use", "id": "missing", "name": "inspect_project", "input": {}}]},
                  {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "other", "content": "wrong pair"}]}]
    assert recent_tool_exchanges(incomplete) == []


def test_recoverable_checkpoint_keeps_inspection_request_without_replaying_full_dump():
    result = {"nativeInspection": {"draftBatch": 5, "request": {"detail": "full", "layerIds": [7]},
                                   "result": {"nativeProperties": ["full dump"] * 2000}}}
    saved = json.dumps(result)
    context = {"recoverableEvidenceMode": True, "directorContext": {"latestPlan": {"id": "plan"}}}
    messages = compact_messages(context, {}, 5, result)
    state = json.loads(messages[0]["content"][1]["text"])
    assert state["nativeInspection"]["request"] == result["nativeInspection"]["request"]
    assert state["directorContext"]["latestPlan"]["id"] == "plan"
    assert "full dump" not in json.dumps(messages)
    assert json.dumps(result) == saved
    assert "nativeInspection" not in json.loads(compact_messages(context, {}, 6, result)[0]["content"][1]["text"])


def test_recoverable_session_delays_repeat_compaction_but_keeps_pressure_escape():
    messages = [{"role": "user", "content": "checkpoint"}, {"role": "assistant", "content": "test"},
                {"role": "user", "content": "result"}]
    assert not should_compact(messages, 125000, checkpoint_tokens=90000, turns_since_attempt=1)
    assert should_compact(messages, 125000, checkpoint_tokens=90000, turns_since_attempt=8)
    assert should_compact(messages, 240000, checkpoint_tokens=90000, turns_since_attempt=1)
