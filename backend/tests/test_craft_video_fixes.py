"""Offline regressions for video progress; all provider calls remain disabled."""
import copy
import json
import shutil
import subprocess

import pytest

from app.services.studios import craft_history
from app.services.studios.craft_agent import update_resource_message
from app.services.studios.craft_delivery import delivery_review
from app.services.studios.craft_media_prepare import prepare_video_excerpt


@pytest.fixture(autouse=True)
def clean_database():
    # These tests exercise pure context/review code and local files, not the database.
    yield


def test_resource_updates_preserve_previously_submitted_history():
    messages = craft_history.start_message({"instruction": "Keep the subject visible"}, prompt_cache=True)
    update_resource_message(messages, {"remainingUsd": 5})
    submitted = copy.deepcopy(messages)
    messages.extend([{"role": "assistant", "content": []}, {"role": "user", "content": []}])
    update_resource_message(messages, {"remainingUsd": 4.8})
    assert messages[:1] == submitted
    update_resource_message(messages, {"remainingUsd": 4.7})
    assert messages[:1] == submitted
    assert len(messages[-1]["content"]) == 1


def test_large_retained_evidence_does_not_immediately_recompact():
    messages = [{"role": "user", "content": "checkpoint"}, {"role": "assistant", "content": []},
                {"role": "user", "content": []}]
    assert not craft_history.should_compact(messages, 54000, checkpoint_tokens=53000)
    assert craft_history.should_compact(messages, 63000, checkpoint_tokens=53000)


def test_renewal_keeps_contracts_and_discards_stale_layer_observations():
    remembered = [{"name": "inspect_motion_fonts", "draftBatch": None, "result": {"family": "Unbounded"}},
                  {"name": "inspect_project", "draftBatch": 1, "result": {"position": [10, 20]}}]
    messages = craft_history.compact_messages({"instruction": "Edit"}, {}, 2, {"inspectionMemory": remembered})
    checkpoint = json.loads(messages[0]["content"][1]["text"])
    assert checkpoint["inspectionMemory"] == remembered[:1]


def test_empty_review_windows_preserve_legacy_request_hash(monkeypatch):
    from app.domain.studios.craft import CraftAICommandRequestV1
    from app.services.studios import craft_ai
    from app.services.studios.craft import operation_digest
    request = CraftAICommandRequestV1(expectedRevision=1, instruction="Edit")
    legacy = request.model_dump(mode="json")
    for name in ("generation_budget_usd", "execution_time_limit_seconds", "require_export", "review_windows", "unlimited_budget", "workflow", "direction_effort", "direction_contract"):
        legacy.pop(name)
    expected = operation_digest("ai-commands", legacy)
    class Captured(Exception):
        pass
    def receipt(_db, _record, _key, digest):
        assert digest == expected
        raise Captured
    monkeypatch.setattr(craft_ai, "receipt", receipt)
    with pytest.raises(Captured):
        craft_ai.ai_commands(None, None, request, None, "existing-key")


def test_effectcraft_concurrency_is_bounded_in_the_worker_environment(monkeypatch, tmp_path):
    from app.providers.studios import craft
    observed = {}
    class Process:
        returncode = 0
        def __init__(self, _argv, **kwargs):
            observed.update(kwargs["env"])
        def communicate(self, payload, timeout=None):
            request = json.loads(payload)
            return json.dumps({"protocolVersion": 1, "requestId": request["requestId"], "result": {"checked": True}}), ""
        def poll(self):
            return 0
    monkeypatch.setattr(craft.subprocess, "Popen", Process)
    assert craft.call_engine("effectcraft", "engine.capabilities", {"mediaRoot": str(tmp_path)}) == {"checked": True}
    assert observed["RAYON_NUM_THREADS"] == "1"


def reviewed_tool(batch=2, overview=False, start=5, samples=None):
    return {"name": "review_clip", "ok": True, "draftBatch": batch,
            "observation": {"source": {"kind": "native_draft", "draftBatch": batch, "nativeChecksumSha256": "current"},
                "interval": {"startSeconds": 0 if overview else start, "endSeconds": 18 if overview else start+.4},
                "visual": {"sampling": "overview" if overview else "native", "sampleFps": 30,
                           "nativeRateRequested": not overview, "consecutiveOnRequestedGrid": not overview,
                           "sampledSeconds": samples or [start+i/30 for i in range(12)]}}}


def test_delivery_rejects_stills_stale_revisions_and_source_only_reviews():
    assert delivery_review([{"name": "preview_sequence", "ok": True, "draftBatch": 2}], 2, 18)["status"] == "draft"
    assert delivery_review([reviewed_tool(1, True), reviewed_tool(1)], 2, 18)["status"] == "draft"
    source = reviewed_tool()
    source["input"] = {"assetId": "footage"}
    assert delivery_review([reviewed_tool(overview=True), source], 2, 18)["status"] == "draft"


def test_delivery_checks_actual_page_coverage_not_requested_interval():
    tools = [reviewed_tool(overview=True), reviewed_tool()]
    window = [{"startSeconds": 5, "durationSeconds": .8}]
    assert delivery_review(tools, 2, 18, window)["status"] == "draft"
    tools.append(reviewed_tool(start=5.4))
    result = delivery_review(tools, 2, 18, window)
    assert result["status"] == "reviewed" and result["editorialApproval"] == "pending"
    assert delivery_review(tools, 2, 18, window, ["Known text overlap"])["status"] == "draft"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="requires local FFmpeg")
def test_production_preparation_keeps_full_frame_native_cadence_and_duration(tmp_path):
    source, output = tmp_path / "master.mp4", tmp_path / "production.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=2",
                    "-threads", "2", "-c:v", "libx264", str(source)], check=True, timeout=30)
    receipt = prepare_video_excerpt(source, output, .25, 1)
    assert receipt["outputDimensions"] == [640, 360]
    assert receipt["frameRate"] == "24" and receipt["speed"] == 1 and receipt["crop"] is None
    assert abs(receipt["outputDurationSeconds"] - 1) <= 1/24
    with pytest.raises(ValueError, match="output_must_be_new"):
        prepare_video_excerpt(source, source, 0, 1)
