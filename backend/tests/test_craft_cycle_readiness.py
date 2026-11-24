import copy
from types import SimpleNamespace

import pytest

from app.services.studios.craft_execution import native_equivalent
from app.services.studios.craft_execution import require_storage
from app.services.studios import craft_director as director


def test_http_503_recovery_retains_pending_financial_exposure():
    from app.services.studios import craft_agent
    job = SimpleNamespace(status="failed", error_code="llm_provider_http_503",
        request_payload={"generationBudgetUsd": None}, result_payload={
            "draft": {"batches": 8}, "submissionOutcome": "unknown", "pendingTurnBudget": {
                "inputTokenBound": 112593, "maxOutputTokens": 20000}, "nextTurnReservationUsd": .850372})
    before = copy.deepcopy(job.result_payload)
    assert craft_agent.can_resume(job)
    assert job.result_payload == before
    assert job.result_payload["pendingTurnBudget"] is not None


def test_uncertain_exposure_includes_possible_cache_write():
    from app.services.studios.craft_agent import pending_exposure
    job = SimpleNamespace(request_payload={"promptCache": True,
        "pricing": {"inputUsdPerMillion": 4, "outputUsdPerMillion": 20}}, result_payload={
        "pendingTurnBudget": {"inputTokenBound": 112593, "maxOutputTokens": 20000}})
    assert pending_exposure(job) == pytest.approx(.962965)
    job.request_payload["promptCache"] = False
    assert pending_exposure(job) == pytest.approx(.850372)


def test_evaluation_sampling_alias_is_honored_without_silent_fallback():
    payload = {"sampling": {"fps": 10, "maximumSide": 720}, "questions": ["Is the wave coherent?"]}
    normalized = director.normalize_evaluation_payload(payload)
    assert normalized["parameters"] == payload["sampling"] and "sampling" not in normalized
    assert normalized["questions"] == payload["questions"]
    with pytest.raises(ValueError, match="sampling_conflict"):
        director.normalize_evaluation_payload({**payload, "parameters": {"fps": 4}})
    with pytest.raises(ValueError, match="unknown_fields"):
        director.normalize_evaluation_payload({"samplng": {"fps": 10}})


def test_noop_formatting_and_selection(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text('{"layers": [], "clickoActiveComp": "a"}')
    b.write_text('{"clickoActiveComp":"a","layers":[]}')
    assert native_equivalent(a, b)
    b.write_text('{"clickoActiveComp":"b","layers":[]}')
    assert not native_equivalent(a, b)
    b.write_text('{"clickoActiveComp":"a","layers":[1]}')
    assert not native_equivalent(a, b)


def test_storage_reserve_blocks_execution_before_native_request(monkeypatch, tmp_path):
    from app.services.studios import craft_execution, craft_agent
    monkeypatch.setattr(craft_execution.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(ValueError, match="storage_exhausted"):
        require_storage(tmp_path)
    calls = []
    monkeypatch.setattr(craft_agent, "call_engine", lambda *a, **k: calls.append(a))
    draft = object.__new__(craft_agent.Draft)
    draft.directory = tmp_path
    with pytest.raises(ValueError, match="storage_exhausted"):
        draft.call("render.video", outputPath=str(tmp_path / "video.mp4"))
    assert calls == [] and not (tmp_path / "video.mp4").exists()


def test_cycle_requires_current_complete_visual_evidence(tmp_path):
    path = tmp_path / "native"
    path.write_bytes(b"revision-one")
    record, job = SimpleNamespace(id="doc", revision=2), SimpleNamespace(id="job")
    draft = SimpleNamespace(batches=1, params={"nativePath": str(path)})
    bound = director.binding(record, job, draft)
    state = {"cycle": {"requireVisualEvaluation": True}, "plans": [{"id": "plan", "documentId": "doc",
        "plan": {"scenes": [{"id": "scene", "essential": True,
            "interval": {"startSeconds": 0, "durationSeconds": 2}}]}}], "evidence": []}
    with pytest.raises(ValueError):
        director.require_cycle_evaluation(state, record, job, draft)
    evidence = {"planId": "plan", "binding": bound, "assessment": {"modality": "visual",
        "interval": {"startSeconds": 0, "durationSeconds": 2}, "findings": [
            {"dimension": "intent", "sceneIds": ["scene"], "status": "pass"}]}}
    state["evidence"] = [evidence]
    director.require_cycle_evaluation(state, record, job, draft)
    partial = copy.deepcopy(evidence)
    partial["assessment"]["interval"]["durationSeconds"] = .4
    state["evidence"] = [partial]
    with pytest.raises(ValueError):
        director.require_cycle_evaluation(state, record, job, draft)
    state["evidence"] = [evidence]
    evidence["assessment"]["findings"].append({"dimension": "technical", "sceneIds": [], "status": "fail"})
    with pytest.raises(ValueError):
        director.require_cycle_evaluation(state, record, job, draft)
    evidence["assessment"]["findings"].pop()
    path.write_bytes(b"revision-two")
    with pytest.raises(ValueError):
        director.require_cycle_evaluation(state, record, job, draft)
