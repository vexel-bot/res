import copy
import json

import pytest
from jsonschema import Draft202012Validator

from app.services.studios import craft_director as director, craft_project_context as project
from app.services.studios.craft_director_contracts import DirectorWriteChain, compact_cycle, record_finish_issues, reconcile_native_commit
from app.services.studios.craft_native_dependencies import font_requirements
from test_craft_direction_v2 import native as _native, invoke, plan, add_review


@pytest.fixture
def native(client, tmp_path):
    yield from _native.__wrapped__(client, tmp_path)


def test_plan_tool_schema_rejects_the_actual_bad_types_before_execution():
    schema = next(t for t in director.tools() if t["name"] == "record_direction_plan")["input_schema"]
    validator = Draft202012Validator(schema)
    value = {"expectedVersion": 0, "payload": {"plan": plan()}}
    validator.validate(value)
    value["payload"]["plan"]["experiment"] = {"interval": {"startSeconds": 0, "durationSeconds": 2}}
    value["payload"]["plan"]["scenes"][0]["acceptance"] = "not an array"
    assert len(list(validator.iter_errors(value))) == 2


def test_schema_makes_draft_selection_distinct_from_promotion():
    tool = next(t for t in director.tools() if t["name"] == "compare_direction_candidates")
    assert "select_draft" in tool["input_schema"]["properties"]["payload"]["properties"]["decision"]["enum"]
    assert "does not promote" in tool["description"]


def test_write_chain_forwards_only_versions_created_by_own_calls():
    chain = DirectorWriteChain()
    original = {"expectedVersion": 3, "payload": {}}
    chain.observe("save_direction_candidate", original, original, {"version": 4})
    assert chain.arguments("request_direction_evaluation", original)["expectedVersion"] == 4
    chain.observe("request_direction_evaluation", original, {**original, "expectedVersion": 4}, {"version": 6})
    assert chain.arguments("manage_direction_issue", original)["expectedVersion"] == 6
    assert chain.arguments("inspect_direction", original) is original
    assert chain.arguments("manage_direction_issue", {**original, "expectedVersion": 2})["expectedVersion"] == 2
    # A provider result containing an unexpected external revision does not extend trust.
    chain.observe("request_direction_evaluation", original, {**original, "expectedVersion": 6}, {"version": 9})
    assert chain.arguments("manage_direction_issue", original) is original


def test_chained_writes_still_reject_a_real_concurrent_change(native):
    db, record, job, draft = native
    chain = DirectorWriteChain()
    args = {"expectedVersion": 0, "payload": {"plan": plan()}}
    reply = director.dispatch(db, record, job, draft, "record_direction_plan", args, "", [], [])
    chain.observe("record_direction_plan", args, args, reply)
    later = {"expectedVersion": 0, "payload": {"description": "first issue"}}
    effective = chain.arguments("manage_direction_issue", later)
    reply = director.dispatch(db, record, job, draft, "manage_direction_issue", effective, "", [], [])
    chain.observe("manage_direction_issue", later, effective, reply)
    invoke(native, "manage_direction_issue", {"description": "external issue"})
    with pytest.raises(ValueError, match="version_conflict"):
        director.dispatch(db, record, job, draft, "manage_direction_issue",
                          chain.arguments("manage_direction_issue", later), "", [], [])


def test_polling_cannot_advance_the_write_chain():
    chain = DirectorWriteChain()
    args = {"expectedVersion": 1, "payload": {"operationId": "uncertain"}}
    chain.observe("request_direction_evaluation", args, args, {"version": 3})
    assert chain.arguments("save_direction_candidate", args) is args


def test_commit_reconciliation_checks_content_without_promoting_or_rewriting_review():
    bound = {"documentId": "doc", "documentRevision": 2, "nativeChecksumSha256": "same"}
    original = copy.deepcopy(bound)
    result = reconcile_native_commit(bound, "doc", 3, "same")
    assert result["sameNativeContent"] and bound == original
    assert result["reviewBinding"]["documentRevision"] == 2 and result["committedRevision"] == 3
    assert not reconcile_native_commit(bound, "doc", 3, "different")["sameNativeContent"]
    assert not reconcile_native_commit(bound, "other", 3, "same")["sameNativeContent"]


def test_draft_selection_records_comparison_without_promoting_or_human_approval(native):
    db, record, job, draft = native
    invoke(native, "record_direction_plan", {"plan": plan()})
    asset = add_review(native)
    candidate = invoke(native, "save_direction_candidate", {"reviewAssetId": asset.id, "label": "draft"})["item"]
    _, state = project.state(db, record)
    state["evidence"].append({"id": "observation", "binding": candidate["binding"], "planId": candidate["planId"],
        "assessment": {"modality": "visual", "interval": {"startSeconds": 0, "durationSeconds": 2},
                       "findings": [{"dimension": "intent", "sceneIds": ["reveal"], "status": "inconclusive"}]}})
    project.save(db, record, state, state["version"])
    db.commit()
    invoke(native, "compare_direction_candidates", {"candidateId": candidate["id"], "baselineId": None,
        "evidenceIds": ["observation"], "decision": "select_draft", "rationale": "Present complete draft with limits"})
    _, state = project.state(db, record)
    report = director.delivery(state, record, job, draft, [], [], final=True)
    assert state["draftCandidateId"] == candidate["id"] and state["preferredCandidateId"] is None
    assert state["humanApproval"] == "not_recorded" and state["approvedCandidateId"] is None
    assert report["draftComparison"]["status"] == "recorded" and report["draftComparison"]["selected"]
    assert report["comparison"]["scope"] == "formal_audiovisual_promotion"
    assert report["status"] == "draft" and "complete audiovisual assessment not established" in report["missing"]


def test_finish_references_existing_defects_without_duplicating_or_closing_them():
    state = {"issues": [{"id": "glyph", "description": "i appears without dot", "status": "open"}]}
    assert not record_finish_issues(state, {}, [], ["glyph"])
    assert not record_finish_issues(state, {}, ["i appears without dot"], ["glyph"])
    assert state["issues"][0]["status"] == "open" and len(state["issues"]) == 1
    with pytest.raises(ValueError, match="issue_reference_invalid"):
        record_finish_issues(state, {}, [], ["missing"])


def test_source_specific_issue_is_preserved_but_does_not_become_global(native):
    db, record, job, draft = native
    invoke(native, "record_direction_plan", {"plan": plan()})
    issue = invoke(native, "manage_direction_issue", {"description": "glyph defect in source"})["item"]
    _, state = project.state(db, record)
    state["issues"][0]["binding"]["documentId"] = "source-document"
    report = director.delivery(state, record, job, draft, [], [])
    assert issue["description"] not in report["missing"]
    assert state["issues"][0]["status"] == "open"
    state["issues"][0]["scope"] = "family"
    assert issue["description"] in director.delivery(state, record, job, draft, [], [])["missing"]


def test_compact_cycle_keeps_current_decision_and_ids_without_repeating_old_summaries():
    cycle = {"stage": "production", "events": [{"id": "proof", "stage": "experiment", "summary": "old-heavy" * 1000},
             {"id": "production", "stage": "production", "summary": "current decision"}], "processHistory": ["logs"]}
    before = copy.deepcopy(cycle)
    compact = compact_cycle(cycle)
    assert compact["latestDecision"] == "current decision" and compact["eventCount"] == 2
    assert "proof" in json.dumps(compact) and "old-heavy" not in json.dumps(compact)
    assert compact["historyAvailableVia"] == {"kind": "cycle"} and cycle == before


def test_new_branch_cycle_archives_source_history_without_rewriting_it(native):
    db, record, _, _ = native
    _, state = project.state(db, record)
    old = {"documentId": "source", "events": [{"id": "decision", "summary": "source decision"}], "stage": "delivered"}
    state["cycle"] = copy.deepcopy(old)
    saved = project.save(db, record, state, state["version"])
    db.commit()
    saved["cycle"] = {"documentId": record.id, "events": [], "stage": "diagnosis"}
    saved = project.save(db, record, saved, saved["version"])
    db.commit()
    assert saved["cycleArchive"] == [old]
    assert project.document_cycle(saved, "source") == old
    assert project.document_cycle(saved, record.id)["events"] == []


def test_missing_experiment_evidence_reports_the_current_binding(native):
    db, record, job, draft = native
    invoke(native, "record_direction_plan", {"plan": plan()})
    _, state = project.state(db, record)
    state["cycle"] = {"requireVisualEvaluation": True}
    with pytest.raises(ValueError) as error:
        director.require_cycle_evaluation(state, record, job, draft, experiment=True)
    assert "craft_cycle_experiment_visual_evidence_required" in str(error.value)
    details = json.loads(str(error.value).split(": ", 1)[1])
    assert details["currentBinding"] == director.binding(record, job, draft)
    assert details["currentEvidenceIds"] == [] and "review_clip" in details["nextAction"]


def test_invalid_time_origin_rejected_without_a_provider_call():
    with pytest.raises(ValueError, match="time_origin_invalid"):
        director.normalize_evaluation_payload({"timeOrigin": "guess"})


def test_clip_relative_evaluation_is_converted_once_and_invalid_absolute_time_is_explained(native, monkeypatch):
    from app.services.studios import craft_director_providers as providers
    monkeypatch.setattr(providers, "PROVIDERS", {})
    db, _, _, _ = native
    asset = add_review(native)
    metadata = copy.deepcopy(asset.object_metadata)
    metadata["craftReview"]["report"]["interval"] = {"startSeconds": 8.5, "durationSeconds": 2.5}
    asset.object_metadata = metadata
    db.commit()
    seen = []

    def observe(db, record, request):
        seen.append(request)
        return {"status": "succeeded", "costUsd": 0, "consumedChecksumSha256": request["checksumSha256"],
            "assessment": {"modality": "visual", "interval": request["interval"], "findings": [
                {"dimension": "intent", "status": "inconclusive", "observation": "Offline fixture"}]}}

    providers.register(providers.DirectorProvider("timeline-fixture", "1", "evaluator", ("visual",), "fixture-only",
        lambda *_: {"status": "available"}, observe, observe, metered=False))
    payload = {"providerId": "timeline-fixture", "reviewAssetId": asset.id, "modality": "visual",
               "interval": {"startSeconds": 0, "durationSeconds": 2.5}, "operationKey": "relative"}
    with pytest.raises(ValueError, match="allowedCompositionInterval"):
        invoke(native, "request_direction_evaluation", payload)
    assert seen == []
    reply = invoke(native, "request_direction_evaluation", {**payload, "timeOrigin": "clip"})
    assert seen[0]["interval"] == {"startSeconds": 8.5, "durationSeconds": 2.5}
    assert reply["evidence"]["assessment"]["interval"] == seen[0]["interval"]


def test_native_font_requirements_preserve_legacy_and_never_claim_embedding(tmp_path):
    file = tmp_path / "native.ecproj"
    file.write_text(json.dumps({"text": {"font": "Inter-Bold"}, "nested": [{"font": "Inter-Bold"}]}))
    requirements = font_requirements(file, "effectcraft", "build")
    assert requirements["requestedFaces"] == ["Inter-Bold"]
    assert requirements["status"] == "declared_not_portability_verified"
    file.write_bytes(b"\xfflegacy")
    assert font_requirements(file, "effectcraft", "build")["status"] == "unavailable_legacy_native_format"


def test_larger_native_contact_sheet_contains_actual_consecutive_frames(tmp_path, monkeypatch):
    import base64
    from io import BytesIO
    from PIL import Image
    from app.services.studios import craft_review

    def extraction(arguments, deadline):
        assert arguments[arguments.index("-frames:v") + 1] == "30"
        for index in range(30):
            Image.new("RGB", (225, 400), (index * 7, 0, 0)).save(tmp_path / f"frame-{index:02d}.png")

    monkeypatch.setattr(craft_review, "_run", extraction)
    seconds, block = craft_review._frames(tmp_path / "fixture.mp4", tmp_path, 7, 1, 30, 0, 30, 30, 100)
    assert len(seconds) == 30 and seconds[0] == 7 and seconds[-1] == pytest.approx(7 + 29 / 30)
    image = Image.open(BytesIO(base64.b64decode(block["source"]["data"])))
    assert image.size == (1860, 2150)
