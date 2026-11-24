"""Regression checks for session-scoped Claude visual review."""
import json
from types import SimpleNamespace

import pytest

from app.services.studios import craft_claude_review as review


def response(data):
    return {"model": review.MODEL, "stop_reason": "end_turn", "request_id": "request-fixture",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "content": [{"type": "text", "text": json.dumps(data)}]}


def test_images_sent_and_audio_integration_stays_inconclusive():
    seen = []

    class Provider:
        def craft_turn(self, *args, **kwargs):
            seen.append((args, kwargs))
            return response({"A": {"findings": [
                {"dimension": "technical", "status": "pass", "observation": "The field is magenta"},
                {"dimension": "audiovisual", "status": "pass", "observation": "Unverified sound claim"},
            ]}})

    media = {"A": {"frames": [b"actual image fixture"], "timestamps": [5.5],
                   "sampling": {"fps": 2}, "interval": {"startSeconds": 5, "durationSeconds": 1}}}
    result = review.observe(Provider(), media, [], [])
    assert result["status"] == "succeeded"
    assert result["assessments"]["A"]["findings"][1]["status"] == "inconclusive"
    assert result["costUsd"] == .0014
    assert seen[0][0][0] == "claude-opus-5-5"
    assert seen[0][1]["effort"] == "high"
    blocks = seen[0][0][2][0]["content"]
    assert any(block["type"] == "image" for block in blocks)
    assert any("5.500000" in block.get("text", "") for block in blocks)


def test_invalid_assessment_keeps_known_usage():
    provider = SimpleNamespace(craft_turn=lambda *args, **kwargs: response({"A": {"findings": []}}))
    result = review.observe(provider, {"A": {"frames": [], "timestamps": [],
        "sampling": {}, "interval": {"startSeconds": 0, "durationSeconds": 1}}}, [], [])
    assert result["status"] == "failed" and result["costUsd"] > 0
    assert result["providerRequestId"] == "request-fixture"


def test_unsupported_audio_is_rejected_before_any_request():
    with pytest.raises(ValueError, match="modality_unavailable"):
        review.evaluate(None, None, {"modality": "audiovisual"}, None)


def test_connection_requires_workspace_native_protocol_and_exact_model():
    record = SimpleNamespace(workspace_id="a")
    connection = SimpleNamespace(workspace_id="a", provider="anthropic", config={
        "protocol": "anthropic_messages", "baseUrl": "https://api.anthropic.com/v1",
        "models": [review.MODEL], "enabled": True})
    assert review.valid_connection(connection, record)
    connection.workspace_id = "b"
    assert not review.valid_connection(connection, record)
    connection.workspace_id = "a"
    connection.config["models"] = ["claude-sonnet-5-5"]
    assert not review.valid_connection(connection, record)


def test_sampling_rejects_invalid_windows_and_unbounded_images(tmp_path):
    interval = {"startSeconds": 0, "durationSeconds": 2}
    with pytest.raises(ValueError, match="interval_conflict"):
        review.frames(tmp_path / "unused", interval, {"startSeconds": 1, "durationSeconds": 2}, {})
    with pytest.raises(ValueError, match="sampling_invalid"):
        review.frames(tmp_path / "unused", interval, interval, {"fps": float("nan")})
    with pytest.raises(ValueError, match="shorter_interval"):
        review.frames(tmp_path / "unused", interval, interval, {"fps": 60})


def test_receipt_is_specific_to_session_connection_revision(native, tmp_path, monkeypatch):  # noqa: F811
    from app.config import get_settings
    from app.models import StudioLLMConnection
    db, record, job, _ = native
    connection = StudioLLMConnection(id="claude-fixture", workspace_id=record.workspace_id,
        created_by=record.created_by, label="Fixture", provider="anthropic", revision=1, config={
            "protocol": "anthropic_messages", "baseUrl": "https://api.anthropic.com/v1",
            "models": [review.MODEL], "enabled": True})
    db.add(connection)
    db.flush()
    job.request_payload = {"llmConnectionId": connection.id, "llmConnectionRevision": 1, "model": review.MODEL}
    path = tmp_path / "qualification.json"
    path.write_text(json.dumps({"adapterVersion": review.VERSION, "model": review.MODEL,
        "connectionId": connection.id, "connectionRevision": 1, "qualificationPassed": True,
        "providerRequestId": "request-fixture", "sourceSha256": "a" * 64}))
    monkeypatch.setattr(get_settings(), "studio_craft_claude_qualification_file", str(path))
    provider = review.adapters(db, record, job)[review.PROVIDER_ID]
    assert provider.available(db, record)["status"] == "available"
    job.request_payload["llmConnectionRevision"] = 2
    provider = review.adapters(db, record, job)[review.PROVIDER_ID]
    assert provider.available(db, record)["status"] == "unavailable"


@pytest.mark.parametrize("sampling_key", ["parameters", "sampling"])
def test_qualified_claude_runs_through_the_director_tool(native, tmp_path, monkeypatch, sampling_key):  # noqa: F811
    from contextlib import contextmanager
    from app.config import get_settings
    from app.models import StudioLLMConnection
    from app.services.object_storage import sha256_file
    from test_craft_direction_v2 import add_review, invoke

    db, record, job, _ = native
    connection = StudioLLMConnection(id="session-claude", workspace_id=record.workspace_id,
        created_by=record.created_by, label="Claude", provider="anthropic", revision=1, config={
            "protocol": "anthropic_messages", "baseUrl": "https://api.anthropic.com/v1",
            "models": [review.MODEL], "enabled": True})
    db.add(connection)
    db.flush()
    job.request_payload = {"llmConnectionId": connection.id, "llmConnectionRevision": 1,
                           "model": review.MODEL, "unlimitedNativeSession": True}
    path = tmp_path / "proof.json"
    path.write_text(json.dumps({"adapterVersion": review.VERSION, "model": review.MODEL,
        "connectionId": connection.id, "connectionRevision": 1, "qualificationPassed": True,
        "providerRequestId": "request-fixture", "sourceSha256": "a" * 64}))
    monkeypatch.setattr(get_settings(), "studio_craft_claude_qualification_file", str(path))
    clip = tmp_path / "source.mp4"
    clip.write_bytes(b"verified workspace media fixture")
    asset = add_review(native)
    asset.checksum_sha256 = sha256_file(clip)
    db.commit()

    @contextmanager
    def materialize(key):
        yield clip

    monkeypatch.setattr(review, "get_object_storage", lambda *_: SimpleNamespace(materialize=materialize))
    monkeypatch.setattr(review, "decrypt", lambda _: "test-credential")
    observed = []

    def planner(config, credential):
        assert config is connection.config and credential == "test-credential"
        def craft_turn(*args, **kwargs):
            observed.append(args[0])
            assert json.loads(args[2][0]["content"][-1]["text"])["reviewQuestions"] == ["Is the wave coherent?"]
            return response({"A": {"findings": [
                {"dimension": "technical", "status": "pass", "observation": "A visible object"}]}})
        return SimpleNamespace(craft_turn=craft_turn)

    monkeypatch.setattr(review, "UniversalLLMPlanner", planner)
    monkeypatch.setattr(review, "frames", lambda *args: {
        "frames": [b"pixels"], "timestamps": [0], "sampling": {"fps": 1},
        "interval": {"startSeconds": 0, "durationSeconds": 2}})
    result = invoke(native, "request_direction_evaluation", {
        "providerId": review.PROVIDER_ID, "operationKey": "qualified-claude",
        "reviewAssetId": asset.id, "interval": {"startSeconds": 0, "durationSeconds": 2}, "modality": "visual",
        sampling_key: {"fps": 10, "maximumSide": 720}, "questions": ["Is the wave coherent?"]})
    assert result["operation"]["status"] == "succeeded"
    assert result["evidence"]["providerId"] == review.PROVIDER_ID
    assert result["evidence"]["checksumSha256"] == asset.checksum_sha256
    assert result["operation"]["result"]["observedMedia"]["A"]["frameChecksums"]
    def unreadable(*args):
        raise OSError("local media unavailable")

    monkeypatch.setattr(review, "frames", unreadable)
    failed = invoke(native, "request_direction_evaluation", {"providerId": review.PROVIDER_ID,
        "operationKey": "unreadable-media", "reviewAssetId": asset.id,
        "interval": {"startSeconds": 0, "durationSeconds": 2}, "modality": "visual"})
    assert failed["operation"]["status"] == "failed"
    assert failed["operation"]["costUsd"] == 0 and failed["operation"]["result"]["providerSubmitted"] is False
    assert observed == [review.MODEL]
    assert job.result_payload["directorOperations"]["measuredCostUsd"] == .0014
    assert observed == [review.MODEL]
    assert result["operation"]["request"]["parameters"] == {"fps": 10, "maximumSide": 720}


from test_craft_direction_v2 import native  # noqa: E402,F401

def test_native_review_source_interval_accepts_report_end_seconds(monkeypatch, tmp_path):
    def extract(arguments, **kwargs):
        Path(arguments[-1].replace('%04d', '0000')).write_bytes(b'jpeg fixture')
    from pathlib import Path
    monkeypatch.setattr(review.subprocess, 'run', extract)
    monkeypatch.setattr(review, 'resolve_tool', lambda _: 'ffmpeg')
    result = review.frames(tmp_path / 'source.mp4', {'startSeconds': 0, 'durationSeconds': 1},
                           {'startSeconds': 0, 'endSeconds': 15, 'durationSeconds': 15}, {'fps': 1})
    assert result['timestamps'] == [0] and result['frames'] == [b'jpeg fixture']
