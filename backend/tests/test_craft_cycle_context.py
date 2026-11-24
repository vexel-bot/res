import json

from app.services.studios.craft_history import compact_messages
from app.services.studios.craft_compatibility import scripting_reference


def test_new_cycle_compaction_keeps_decisions_and_recoverable_source_ids():
    messages = [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "ref", "name": "inspect_reference",
            "input": {"referenceId": "external"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "ref", "content": [
            {"type": "image", "source": {"data": "large-recoverable-pixels"}}]}]}]
    result = {"directorContext": {"latestPlan": {"chosenDirection": "rain transforms the space"},
        "issues": [{"id": "crop", "description": "subject clipped"}], "preferredCandidateId": "candidate"}}
    compact = compact_messages({"instruction": "new theme", "recoverableEvidenceMode": True}, {}, 1,
                               result, messages=messages)
    encoded = json.dumps(compact)
    assert "large-recoverable-pixels" not in encoded
    assert all(value in encoded for value in ["external", "rain transforms", "subject clipped", "candidate"])


def test_compaction_keeps_empty_search_results_without_large_material_metadata():
    result = {"materialSearches": [{"query": "puddle", "origin": "public", "result": {
        "searchStatus": "no_matches", "sources": []}}, {"query": "rain", "origin": "workspace", "result": {
        "searchStatus": "matches", "sources": [{"id": "source", "description": "large-description"}]}}]}
    compact = compact_messages({"instruction": "test"}, {}, 0, result)
    checkpoint = json.loads(compact[0]["content"][1]["text"])
    assert checkpoint["materialSearches"][0]["status"] == "no_matches"
    assert checkpoint["materialSearches"][1]["sourceIds"] == ["source"]
    assert "large-description" not in json.dumps(compact)


def test_capability_search_points_to_full_schema_without_repeating_it():
    cap = {"commands": [{"id": "script.run", "inputSchema": {"required": ["code"],
        "description": "large-schema" * 1000}}]}
    value = scripting_reference("uninstalled-test", cap, "script")
    assert value["nativeCommands"][0]["id"] == "script.run"
    assert "large-schema" not in json.dumps(value)
