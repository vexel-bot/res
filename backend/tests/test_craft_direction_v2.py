"""Director regression tests: no paid providers and no new video generation."""
import copy
import json
from types import SimpleNamespace

import pytest

from app.database import SessionLocal
from app.domain.studios.craft import CraftAICommandRequestV1
from app.domain.studios.craft_direction_v2 import DirectionPlan
from app.models import CreativeDocument, LibraryAsset
from app.services.studios import craft_director as director
from app.services.studios import craft_director_providers as providers
from app.services.studios import craft_project_context as project
from app.services.studios.craft_discovery import search_result
from app.services.studios.craft_history import compact_messages
from app.services.studios.craft_learning import save_editorial_lesson
from conftest import register
from test_craft_studios import native_boundary  # noqa: F401


def plan():
    return {"summary": "Show a transformation", "audiencePromise": "Discover a world", "desiredExperience": "Curiosity",
            "referenceIds": ["research.model.cinematic_motif"], "referenceInterpretation": "Maintain the subject across scale",
            "chosenDirection": "Physical reveal", "alternatives": ["A title card"], "rejectionReasons": ["Does not demonstrate change"],
            "progression": "Object then world", "payoff": "World inside object", "visualLanguage": "One continuous reveal",
            "soundLanguage": "Perspective follows scale", "uncertainties": ["Occlusion"], "experiment": "Test the reveal",
            "scenes": [{"id": "reveal", "purpose": "Reveal scale", "initialState": "Closed object", "event": "Object opens",
                "finalState": "World visible", "framing": "Close then wide", "lighting": "Interior illuminates object",
                "movement": "Camera retreats", "continuity": "Same object", "sound": "Room widens",
                "interval": {"startSeconds": 0, "durationSeconds": 2}, "acceptance": ["World remains visible behind the opening"]}]}


def create_document(client, token, workspace, **extra):
    response = client.post("/api/v1/studios/v1/documents", headers={"Authorization": "Bearer " + token}, json={
        "workspaceId": workspace, "title": "Director test", "contentType": "video", "brandRevision": 1,
        "brief": {"objective": "A clear transformation", "audience": "Test viewers"},
        "composition": {"pages": [{"id": "main", "width": 320, "height": 320, "durationMs": 2000, "layers": []}]}, **extra})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def native(client, tmp_path):
    token, workspace = register(client, "director-v2@example.com")
    doc = create_document(client, token, workspace)
    path = tmp_path / "native.efx"
    path.write_bytes(b"immutable test native project, not a video")
    with SessionLocal() as db:
        record = db.get(CreativeDocument, doc["documentId"])
        draft = SimpleNamespace(params={"nativePath": str(path), "media": []}, directory=tmp_path, batches=1,
                                project={"durationMs": 2000}, capability={"buildId": "test-build"})
        job = SimpleNamespace(id="test-job", result_payload={"referenceInspections": [
            {"referenceId": "research.model.cinematic_motif"}]})
        yield db, record, job, draft


def invoke(native, name, payload, history=None):
    db, record, job, draft = native
    _, state = project.state(db, record)
    return director.dispatch(db, record, job, draft, name, {"expectedVersion": state["version"], "payload": payload},
                             "Rebuild freely, previous cut is not approved", history or [], [])


def add_review(native):
    db, record, job, draft = native
    bound = director.binding(record, job, draft)
    report = {"source": {"kind": "native_draft", "nativeChecksumSha256": bound["nativeChecksumSha256"]},
              "interval": {"startSeconds": 0, "durationSeconds": 2}}
    asset = LibraryAsset(workspace_id=record.workspace_id, title="Review", asset_type="video", media_type="video/mp4",
                         checksum_sha256="a" * 64, object_metadata={"craftReview": {**bound, "report": report}})
    db.add(asset)
    db.commit()
    return asset


def test_revision_hypothesis_does_not_silently_rewrite_active_plan(native):
    original = invoke(native, "record_direction_plan", {"plan": plan()})["item"]
    answer = invoke(native, "record_revision_hypothesis", {
        "problem": "Physical action was not demonstrated", "change": "Consider a different visual intention",
        "expectedGain": "A feasible direction", "possibleLosses": "The original action remains unrealized"})
    db, record, _, _ = native
    _, saved = project.state(db, record)
    assert len(saved["plans"]) == 1 and saved["plans"][0] == original
    assert answer["planImpact"]["planChanged"] is False
    assert answer["planImpact"]["activePlanId"] == original["id"]
    assert "record a new complete direction plan" in answer["planImpact"]["instruction"]
    assert saved["preferredCandidateId"] is None and saved["humanApproval"] == "not_recorded"


def test_intent_search_finds_multiple_capabilities_and_does_not_claim_absence():
    commands = [{"id": "camera.add", "label": "Camera"}, {"id": "light.add", "label": "Light"},
                {"id": "text.size", "label": "Font size"}, {"id": "audio.levels", "label": "Volume"}]
    assert len(search_result(commands, "câmera luz texto áudio")["commands"]) == 4
    missing = search_result(commands, "unfindablexyz")
    assert missing["searchStatus"] == "no_matches" and missing["suggestedCategories"]
    with pytest.raises(ValueError):
        search_result(commands, "camera", -1)


def test_sampling_rejected_before_operation_or_external_submission(native):
    from app.services.studios.craft_claude_review import validate_request
    asset = add_review(native)
    calls = []
    providers.register(providers.DirectorProvider("sampling-guard-fixture", "1", "evaluator", ("visual",),
        "fixture", lambda *_: {"status": "available"}, lambda *_: calls.append("external"),
        lambda *_: None, metered=False, validate=validate_request))
    with pytest.raises(ValueError, match="shorter_interval_or_lower_fps"):
        invoke(native, "request_direction_evaluation", {"providerId": "sampling-guard-fixture", "reviewAssetId": asset.id,
            "modality": "visual", "interval": {"startSeconds": 0, "durationSeconds": 2},
            "parameters": {"fps": 30}, "operationKey": "invalid-sampling"})
    assert calls == []
    assert project.state(native[0], native[1])[1]["operations"] == []


def test_assessment_identifiers_remain_recoverable_in_compact_context(native):
    db, record, job, draft = native
    _, state = project.state(db, record)
    state["evidence"].append({"id": "evidence", "binding": director.binding(record, job, draft), "planId": None,
        "assessment": {"modality": "visual", "interval": {"startSeconds": 0, "durationSeconds": 2},
            "findings": [{"status": "fail", "dimension": "technical", "observation": "Rings look overlaid"}]}})
    state["operations"].append({"id": "operation", "operationKey": "proof", "kind": "evaluator", "status": "succeeded", "costUsd": .1})
    project.save(db, record, state, state["version"])
    db.commit()
    context = project.context(db, record, "Continue")
    compacted = compact_messages({"instruction": "Continue"}, {}, 1, {"directorContext": context})
    checkpoint = json.loads(compacted[0]["content"][1]["text"])["directorContext"]
    assert checkpoint["evidenceIndex"][0]["id"] == "evidence"
    assert checkpoint["evidenceIndex"][0]["statuses"] == ["fail"]
    assert checkpoint["operationIndex"][0]["id"] == "operation"
    assert context["humanApproval"] == "not_recorded"


def test_compact_context_pages_observations_and_loads_schema_on_demand(native):
    db, record, job, draft = native
    _, state = project.state(db, record)
    state["cycle"] = {"compactEvidence": True, "documentId": record.id}
    project.save(db, record, state, state["version"])
    db.commit()
    history = [{"toolUseId": str(i), "name": "inspect_project", "ok": True} for i in range(100)]
    compact = invoke(native, "inspect_direction", {}, history)
    assert len(compact["completedObservationIndex"]) == 24 and compact["completedObservationTotal"] == 100
    assert "planSchema" not in compact
    assert invoke(native, "inspect_direction", {"kind": "plan_schema"})["planSchema"]
    page = invoke(native, "inspect_direction", {"kind": "observations", "offset": 0, "limit": 10}, history)
    assert page["items"][0]["toolUseId"] == "0" and page["nextOffset"] == 10


def test_lineage_inherits_only_ancestral_preferences_and_preserves_authority(client):
    token, workspace = register(client, "lineage-v2@example.com")
    parent = create_document(client, token, workspace)
    unrelated = create_document(client, token, workspace)
    with SessionLocal() as db:
        for doc, text in [(parent, "Use the user's three references"), (unrelated, "Foreign creative preference")]:
            save_editorial_lesson(db, workspace, {"situation": text, "correction": text, "useWhen": ["This project"]},
                                  0, "document", doc["documentId"], approved=True, actor_id="test-user")
        db.commit()
    child = create_document(client, token, workspace, sourceDocumentId=parent["documentId"],
                            sourceRevision=parent["revision"], branchReason="Reconsider concept")
    with SessionLocal() as db:
        record = db.get(CreativeDocument, child["documentId"])
        context = project.context(db, record, "Earlier version is also far from the target")
        assert context["lineage"]["familyId"] == parent["documentId"]
        assert len(context["approvedPreferences"]) == 1
        assert "three references" in str(context["approvedPreferences"])
        assert "never blanket approval" in context["precedence"]
        assert context["humanApproval"] == "not_recorded"


def test_plan_versioning_conflicts_and_persistent_issue(native):
    db, record, job, draft = native
    first = invoke(native, "record_direction_plan", {"plan": plan()})
    assert first["version"] == 1
    with pytest.raises(ValueError, match="version_conflict"):
        director.dispatch(db, record, job, draft, "record_direction_plan", {"expectedVersion": 0, "payload": {"plan": plan()}}, "", [], [])
    issue = invoke(native, "manage_direction_issue", {"description": "Object detaches", "status": "open"})["item"]
    invoke(native, "record_direction_plan", {"plan": plan()})
    _, state = project.state(db, record)
    report = director.delivery(state, record, job, draft, [], [])
    assert "Object detaches" in report["missing"]
    with pytest.raises(ValueError, match="current_evidence"):
        invoke(native, "manage_direction_issue", {"id": issue["id"], "status": "resolved", "rationale": "It is fine"})
    invoke(native, "manage_direction_issue", {"id": issue["id"], "status": "limitation", "rationale": "Cannot inspect yet"})
    _, state = project.state(db, record)
    assert state["issues"][0]["status"] == "limitation"
    assert "Object detaches" in director.delivery(state, record, job, draft, [], [])["missing"]


def test_review_binding_rejects_stale_batches_and_partial_coverage(native):
    db, record, job, draft = native
    asset = add_review(native)
    director.review_asset(db, record, asset.id, director.binding(record, job, draft))
    draft.batches += 1
    with pytest.raises(ValueError, match="binding_conflict"):
        director.review_asset(db, record, asset.id, director.binding(record, job, draft))
    invoke(native, "record_direction_plan", {"plan": plan()})
    checksum = director.binding(record, job, draft)["nativeChecksumSha256"]
    def review(overview):
        return {"name": "review_clip", "ok": True, "draftBatch": draft.batches, "observation": {
            "source": {"kind": "native_draft", "draftBatch": draft.batches, "nativeChecksumSha256": checksum},
            "interval": {"startSeconds": 0, "endSeconds": 2}, "visual": {
                "sampling": "overview" if overview else "native", "nativeRateRequested": not overview,
                "consecutiveOnRequestedGrid": not overview, "sampleFps": 30, "sampledSeconds": [i/30 for i in range(12)]}}}
    _, state = project.state(db, record)
    result = director.delivery(state, record, job, draft, [], [review(True), review(False)])
    assert result["status"] == "draft"
    assert any("coverage 0–2" in issue for issue in result["missing"])
    assert result["semantic"] == {"reveal": "inconclusive"}
    assert result["audiovisual"] == "inconclusive"


def test_provider_unavailable_is_not_a_fake_listening_result(native, monkeypatch):
    monkeypatch.setattr(providers, "PROVIDERS", {})
    manifest = invoke(native, "inspect_production_capabilities", {})
    assert not next(r for r in manifest["routes"] if r["id"] == "generated_material")["available"]
    with pytest.raises(ValueError, match="provider_unavailable"):
        invoke(native, "request_direction_evaluation", {"providerId": "not-installed", "operationKey": "one", "modality": "audio"})


def test_uncertain_submission_is_polled_not_resubmitted(native, monkeypatch):
    monkeypatch.setattr(providers, "PROVIDERS", {})
    asset = add_review(native)
    calls = []
    def execute(*args):
        calls.append("execute")
        raise TimeoutError("Provider may already have accepted")
    def poll(*args):
        calls.append("poll")
        return {"status": "pending", "costUsd": None}
    providers.register(providers.DirectorProvider("fixture", "1", "evaluator", ("audio",), "offline-fixture",
                       lambda *_: {"status": "available"}, execute, poll, metered=False))
    payload = {"providerId": "fixture", "reviewAssetId": asset.id, "modality": "audio",
               "interval": {"startSeconds": 0, "durationSeconds": 2}, "operationKey": "same-request"}
    result = invoke(native, "request_direction_evaluation", payload)
    assert result["operation"]["status"] == "uncertain"
    invoke(native, "request_direction_evaluation", payload)
    assert calls == ["execute"]
    invoke(native, "request_direction_evaluation", {"operationId": result["operation"]["id"]})
    assert calls == ["execute", "poll"]


def test_evaluator_requires_consumed_media_and_cannot_be_director_self_report(native, monkeypatch):
    monkeypatch.setattr(providers, "PROVIDERS", {})
    asset = add_review(native)
    seen = []
    def evaluate(db, record, request):
        seen.append(request)
        return {"status": "succeeded", "costUsd": 0, "consumedChecksumSha256": request["checksumSha256"],
                "assessment": {"modality": "audiovisual", "interval": request["interval"], "findings": [
                    {"dimension": "intent", "status": "pass", "observation": "World becomes visible", "sceneIds": ["reveal"]},
                    {"dimension": "audiovisual", "status": "inconclusive", "observation": "Audio identity uncertain"}]}}
    providers.register(providers.DirectorProvider("fixture", "1", "evaluator", ("audiovisual",), "offline-fixture",
                       lambda *_: {"status": "available"}, evaluate, evaluate, metered=False))
    invoke(native, "record_direction_plan", {"plan": plan()})
    result = invoke(native, "request_direction_evaluation", {"providerId": "fixture", "reviewAssetId": asset.id,
        "modality": "audiovisual", "interval": {"startSeconds": 0, "durationSeconds": 2}, "operationKey": "assessment",
        "rationale": "My video is amazing", "cost": 100})
    assert result["evidence"]["checksumSha256"] == asset.checksum_sha256
    assert "rationale" not in seen[0] and "cost" not in seen[0]
    db, record, job, draft = native
    _, state = project.state(db, record)
    report = director.delivery(state, record, job, draft, [], [])
    assert report["semantic"]["reveal"] == "pass" and report["audiovisual"] == "inconclusive"
    assert report["status"] == "draft"


def test_compaction_keeps_rejected_alternatives_and_open_problems():
    context = {"instruction": "Autonomous", "directorContext": {"latestPlan": plan(),
               "issues": [{"description": "Still detached"}], "preferredCandidateId": "old-best"}}
    compacted = compact_messages(context, {}, 1, {"directorContext": context["directorContext"]})
    checkpoint = json.loads(compacted[0]["content"][1]["text"])
    assert checkpoint["directorContext"] == context["directorContext"]


def test_version_one_remains_default_and_scene_ids_are_unique():
    assert CraftAICommandRequestV1(expectedRevision=1, instruction="Edit").direction_contract == "v1"
    invalid = plan()
    invalid["scenes"].append(copy.deepcopy(invalid["scenes"][0]))
    with pytest.raises(ValueError, match="duplicate_scene"):
        DirectionPlan.model_validate(invalid)


def test_temporal_reference_without_media_returns_unavailable():
    from app.services.studios.craft_references import review_reference
    result = review_reference(None, "research.model.cinematic_motif", {})
    assert result["status"] == "unavailable"
    assert result["coverage"]["audio"] == "not_audited"


def complete_history(native):
    _, record, job, draft = native
    bound = director.binding(record, job, draft)
    return [{"name": "review_clip", "ok": True, "draftBatch": draft.batches, "observation": {
        "source": {"kind": "native_draft", "draftBatch": draft.batches, "nativeChecksumSha256": bound["nativeChecksumSha256"]},
        "interval": {"startSeconds": 0, "endSeconds": 2},
        "visual": {"sampling": sampling, "nativeRateRequested": sampling == "native",
                   "consecutiveOnRequestedGrid": sampling == "native", "sampleFps": 30,
                   "sampledSeconds": [i/30 for i in range(60)]}}} for sampling in ("overview", "native")]


def test_candidate_promotion_needs_complete_evidence_and_preserves_best(native):
    db, record, job, draft = native
    asset = add_review(native)
    invoke(native, "record_direction_plan", {"plan": plan()})
    history = complete_history(native)
    candidate = invoke(native, "save_direction_candidate", {"reviewAssetId": asset.id, "label": "A"}, history)["item"]
    _, current = project.state(db, record)
    evidence = {"id": "qualified-observation", "binding": director.binding(record, job, draft),
        "planId": current["plans"][-1]["id"], "assessment": {
        "modality": "audiovisual", "interval": {"startSeconds": 0, "durationSeconds": 2},
        "findings": [{"dimension": "intent", "sceneIds": ["reveal"], "status": "pass", "observation": "World revealed"},
                     {"dimension": "audiovisual", "status": "pass", "observation": "Sound follows the event"}]}}
    current["evidence"].append(evidence)
    baseline_binding = {**candidate["binding"], "draftBatch": 0}
    current["candidates"].append({**candidate, "id": "prior-candidate", "binding": baseline_binding})
    current["evidence"].append({**evidence, "id": "prior-observation", "binding": baseline_binding})
    project.save(db, record, current, current["version"])
    db.commit()
    draft_comparison = {"candidateId": candidate["id"], "baselineId": "prior-candidate",
                        "evidenceIds": [evidence["id"], "prior-observation"],
                        "rationale": "Compare two preserved drafts before selection", "decision": "preserve"}
    result = invoke(native, "compare_direction_candidates", draft_comparison, history)
    assert result["item"]["baselineId"] == "prior-candidate" and result["preferredCandidateId"] is None
    with pytest.raises(ValueError, match="candidate_baseline_conflict"):
        invoke(native, "compare_direction_candidates", {**draft_comparison, "decision": "promote"}, history)
    comparison = {"candidateId": candidate["id"], "baselineId": None, "evidenceIds": [evidence["id"]],
                  "rationale": "First observed complete candidate", "decision": "promote"}
    result = invoke(native, "compare_direction_candidates", comparison, history)
    assert result["preferredCandidateId"] == candidate["id"]
    _, current = project.state(db, record)
    assert current["humanApproval"] == "not_recorded"
    assert db.get(LibraryAsset, candidate["nativeAssetId"]).checksum_sha256 == director.binding(record, job, draft)["nativeChecksumSha256"]
    comparison.update(baselineId=candidate["id"], soundComparison="original_and_matched")
    with pytest.raises(ValueError, match="matched_audio_evidence"):
        invoke(native, "compare_direction_candidates", comparison, history)
    comparison.pop("soundComparison")
    draft.batches += 1
    with pytest.raises(ValueError, match="candidate_revision_conflict"):
        invoke(native, "compare_direction_candidates", comparison, history)
    assert project.state(db, record)[1]["preferredCandidateId"] == candidate["id"]


def test_no_automatic_promotion_from_newer_candidate(native):
    asset = add_review(native)
    result = invoke(native, "save_direction_candidate", {"reviewAssetId": asset.id, "label": "Newest"})
    assert result["preferredCandidateId"] is None
    assert result["item"]["delivery"]["status"] == "draft"


def test_perceptual_failure_cannot_close_issue(native):
    db, record, job, draft = native
    issue = invoke(native, "manage_direction_issue", {"description": "World missing"})["item"]
    _, state = project.state(db, record)
    state["evidence"].append({"id": "failed", "binding": director.binding(record, job, draft), "assessment": {
        "interval": {"startSeconds": 0, "durationSeconds": 2}, "findings": [{"status": "fail"}]}})
    project.save(db, record, state, state["version"])
    db.commit()
    with pytest.raises(ValueError, match="resolution_not_established"):
        invoke(native, "manage_direction_issue", {"id": issue["id"], "status": "resolved", "evidenceIds": ["failed"],
                                                 "rationale": "Author claims it works"})
    assert project.state(db, record)[1]["issues"][0]["status"] == "open"


def test_reference_and_native_evidence_are_distinct(native):
    db, record, job, draft = native
    invoke(native, "record_direction_plan", {"plan": plan()})
    job.result_payload["referenceInspections"] = [{"referenceId": "orbita.quality.baseline", "baseline": {"approved": False}}]
    _, state = project.state(db, record)
    report = director.delivery(state, record, job, draft, [], complete_history(native))
    assert not report["externalReferenceObserved"]
    assert "observed external reference selected by the director" in report["missing"]


def test_human_approval_is_an_authenticated_separate_decision(native):
    from app.domain.studios.craft_direction_v2 import HumanApproval
    db, record, job, draft = native
    asset = add_review(native)
    candidate = invoke(native, "save_direction_candidate", {"reviewAssetId": asset.id})["item"]
    _, current = project.state(db, record)
    result = project.human_approval(db, record, SimpleNamespace(id="actual-user"), HumanApproval(
        expectedRevision=record.revision, expectedVersion=current["version"], candidateId=candidate["id"],
        decision="rejected", comment="Still far from the references"))
    assert result["humanApproval"]["decision"] == "rejected"
    assert "director-approval" not in str(director.tools())
    assert project.state(db, record)[1]["preferredCandidateId"] is None
    _, current = project.state(db, record)
    approved = project.human_approval(db, record, SimpleNamespace(id="actual-user"), HumanApproval(
        expectedRevision=record.revision, expectedVersion=current["version"], candidateId=candidate["id"],
        decision="approved", comment="This specific candidate is approved"))
    assert approved["approvedCandidateId"] == candidate["id"]
    newer = invoke(native, "save_direction_candidate", {"reviewAssetId": asset.id})["item"]
    _, current = project.state(db, record)
    rejected = project.human_approval(db, record, SimpleNamespace(id="actual-user"), HumanApproval(
        expectedRevision=record.revision, expectedVersion=current["version"], candidateId=newer["id"],
        decision="rejected", comment="Preserve the approved one"))
    assert rejected["approvedCandidateId"] == candidate["id"]


def test_detail_crop_validation_does_not_invoke_renderer(tmp_path, monkeypatch):
    from app.services.studios import craft_review
    called = []
    monkeypatch.setattr(craft_review, "_run", lambda *_: called.append(True))
    for crop in [[0, 0, 2, 1], [float("nan"), 0, .5, .5], [0, 0, 0, .5]]:
        with pytest.raises(ValueError, match="crop_invalid"):
            craft_review._detail_frame(tmp_path / "unused", tmp_path, 0, {"crop": crop}, 100)
    assert not called


def test_schema_disallows_invented_human_approval_in_plan():
    invalid = plan()
    invalid["humanApproval"] = "approved"
    with pytest.raises(ValueError):
        DirectionPlan.model_validate(invalid)


@pytest.mark.usefixtures("native_boundary")
def test_native_session_exposes_v2_tools_and_stage_specific_effort(client, monkeypatch):
    from app.services.studios import craft, craft_ai, craft_agent, llm_connections
    from test_craft_studios import create, migrate, headers
    token, workspace = register(client, "director-session@example.com")
    document = create(client, token, workspace)
    migrated = migrate(client, token, document)
    monkeypatch.setattr(craft_ai, "require_capability", craft.require_capability)
    monkeypatch.setattr(craft_agent, "call_engine", craft.call_engine)
    connection = SimpleNamespace(id="offline-director", provider="anthropic", revision=1, config={
        "enabled": True, "protocol": "anthropic_messages", "billingMode": "local_free", "maxOutputTokens": 1000,
        "inputUsdPerMillion": 0, "outputUsdPerMillion": 0})
    original_refresh = SessionLocal.class_.refresh
    def refresh(self, instance, *args, **kwargs):
        if instance is not connection:
            return original_refresh(self, instance, *args, **kwargs)
    monkeypatch.setattr(SessionLocal.class_, "refresh", refresh)
    calls = []
    evaluation_versions = []
    dispatch = director.dispatch

    def dispatch_with_fixture(db, record, job, draft, name, args, *rest):
        if name != "request_direction_evaluation":
            return dispatch(db, record, job, draft, name, args, *rest)
        version = args["expectedVersion"]
        evaluation_versions.append(version)
        return {"version": version + 2, "operation": {"status": "succeeded"}, "evidence": {"id": "fixture"}}

    monkeypatch.setattr(director, "dispatch", dispatch_with_fixture)

    def turn(model, system, messages, tools, tokens, seconds, **options):
        calls.append(options)
        assert "record_direction_plan" in {tool["name"] for tool in tools}
        assert options["effort"] == ("high" if len(calls) <= 2 else "medium")
        action = {1: ("inspect_direction", {"payload": {}}),
                  2: ("record_revision_hypothesis", {"expectedVersion": 0, "payload": {
                      "problem": "Missing contrast", "change": "Adjust background", "expectedGain": "Subject visible"}}),
                  3: ("edit_project", {"commands": [{"id": "paint.set", "params": {"color": "blue"}}]})}.get(len(calls))
        content = [{"type": "tool_use", "id": "tool-" + str(len(calls)), "name": action[0], "input": action[1]}] if action else [
            {"type": "text", "text": "Draft saved; audiovisual quality not established."}]
        if len(calls) == 1:
            content.extend({"type": "tool_use", "id": f"evaluation-{i}", "name": "request_direction_evaluation",
                            "input": {"expectedVersion": 0, "payload": {"operationKey": f"window-{i}"}}}
                           for i in range(2))
        return {"content": content, "stop_reason": "tool_use" if action else "end_turn", "usage": {}, "model": model}
    monkeypatch.setattr(llm_connections, "planner", lambda *_: (connection, SimpleNamespace(craft_turn=turn), "test-opus", "offline"))
    monkeypatch.setattr(craft_agent, "reserve_request", lambda *_args, **_kwargs: None)
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"
    payload = {"expectedRevision": migrated["revision"], "instruction": "Choose how to improve freely", "connectionId": connection.id,
               "directionContract": "v2", "pageId": "page-0"}
    result = client.post(base + "/craft/ai-commands", headers=headers(token, "offline-v2"), json=payload)
    assert result.status_code == 200, result.text
    assert len(calls) == 4
    trace = result.json()["aiTrace"]
    assert [t["requestedEffort"] for t in trace["turns"]] == ["high", "high", "medium", "medium"]
    assert all(t["ok"] for t in trace["tools"])
    assert evaluation_versions == [0, 2]
    assert next(t for t in trace["tools"] if t["toolUseId"] == "evaluation-1")["effectiveExpectedVersion"] == 2
    context = client.get(base + "/craft/director-context", headers=headers(token))
    assert context.status_code == 200
    assert context.json()["revisionHypotheses"][0]["hypothesis"]["problem"] == "Missing contrast"
    replay = client.post(base + "/craft/ai-commands", headers=headers(token, "offline-v2"), json=payload)
    assert replay.status_code == 200 and len(calls) == 4


def test_generated_material_is_staged_only_after_verified_completion(native, monkeypatch):
    from PIL import Image
    from app.services.studios.craft import write_asset
    monkeypatch.setattr(providers, "PROVIDERS", {})
    db, record, job, draft = native
    source = draft.directory / "fixture.png"
    Image.new("RGB", (8, 8), "blue").save(source)
    asset, _, _ = write_asset(db, record, source, suffix=".png", media_type="image/png", asset_type="image",
                              metadata={"rightsStatus": "verified", "fixture": True})
    db.commit()
    calls = []
    def execute(*_):
        calls.append("submitted")
        return {"status": "succeeded", "costUsd": 0, "assetId": asset.id, "checksumSha256": asset.checksum_sha256}
    providers.register(providers.DirectorProvider("local-fixture", "1", "production", ("image",), "fixture-only",
        lambda *_: {"status": "available"}, execute, execute, metered=False))
    payload = {"providerId": "local-fixture", "operationKey": "material-one", "requirement": "Color sample"}
    generated = invoke(native, "request_direction_material", payload)
    assert generated["operation"]["result"]["inspectionRequired"]
    invoke(native, "request_direction_material", payload)
    assert calls == ["submitted"]
    with pytest.raises(ValueError, match="key_conflict"):
        invoke(native, "request_direction_material", {**payload, "requirement": "A different sample"})
    manifests = []
    version = project.state(db, record)[1]["version"]
    staged = director.dispatch(db, record, job, draft, "stage_direction_material", {
        "expectedVersion": version, "payload": {"operationId": generated["operation"]["id"]}}, "", [], [], manifests)
    assert staged["material"]["inspectionRequired"]
    assert manifests[0].asset_id == asset.id
    assert len(draft.params["media"]) == 1
    assert (draft.directory / manifests[0].path).read_bytes() == source.read_bytes()


def test_pair_evaluation_requires_both_media_and_measured_audio_matching(native, monkeypatch):
    from app.services.studios.craft_claude_review import validate_request

    monkeypatch.setattr(providers, "PROVIDERS", {})
    first, second = add_review(native), add_review(native)
    db, _, _, _ = native
    metadata = copy.deepcopy(second.object_metadata)
    metadata["craftReview"]["report"]["interval"]["endSeconds"] = 2
    second.object_metadata = metadata
    db.commit()
    seen = []
    def evaluate(db, record, request):
        seen.append(request)
        assessment = {"modality": "audiovisual", "interval": request["interval"], "findings": [
            {"dimension": "audiovisual", "status": "inconclusive", "observation": "Comparable levels, editorial preference unresolved"}]}
        return {"status": "succeeded", "costUsd": 0, "consumedChecksumSha256": request["checksumSha256"],
                "consumedComparisonChecksums": [request["checksumSha256"], request["comparisonMedia"]["checksumSha256"]],
                "assessment": assessment, "baselineAssessment": {**assessment, "interval": request["comparisonMedia"]["interval"]},
                "audioComparison": "original_and_matched",
                "loudnessMatch": {"method": "offline-fixture", "gainDbA": -4, "gainDbB": 0,
                                  "originalAudition": True, "matchedAudition": True}}
    providers.register(providers.DirectorProvider("pair-fixture", "1", "evaluator", ("audiovisual",), "fixture-only",
        lambda *_: {"status": "available"}, evaluate, evaluate, metered=False, validate=validate_request))
    evaluated = invoke(native, "request_direction_evaluation", {"providerId": "pair-fixture", "reviewAssetId": first.id,
        "baselineReviewAssetId": second.id, "modality": "audiovisual", "interval": {"startSeconds": 0, "durationSeconds": 2},
        "operationKey": "pair", "rationale": "The latest cost more, so it must be better"})
    assert "rationale" not in seen[0]
    assert seen[0]["comparisonMedia"]["interval"] == {"startSeconds": 0, "durationSeconds": 2}
    assert evaluated["evidence"]["audioComparison"] == "original_and_matched"
    assert evaluated["baselineEvidence"]["assessment"]["findings"][0]["status"] == "inconclusive"
    focused = {"providerId": "pair-fixture", "reviewAssetId": first.id, "baselineReviewAssetId": second.id,
               "modality": "audiovisual", "interval": {"startSeconds": 0, "durationSeconds": 1},
               "baselineInterval": {"startSeconds": 1, "durationSeconds": 1},
               "parameters": {"fps": 30}, "operationKey": "focused-pair"}
    result = invoke(native, "request_direction_evaluation", focused)
    assert seen[-1]["comparisonMedia"]["sourceInterval"] == {"startSeconds": 0, "durationSeconds": 2}
    assert result["baselineEvidence"]["assessment"]["interval"] == focused["baselineInterval"]
    with pytest.raises(ValueError, match="baseline_interval_conflict"):
        invoke(native, "request_direction_evaluation", {**focused, "operationKey": "bad-window",
            "baselineInterval": {"startSeconds": 1.5, "durationSeconds": 1}})
    assert len(seen) == 2


def test_changed_plan_invalidates_prior_semantic_assessment(native, monkeypatch):
    db, record, job, draft = native
    invoke(native, "record_direction_plan", {"plan": plan()})
    _, state = project.state(db, record)
    state["evidence"].append({"id": "old-plan-review", "binding": director.binding(record, job, draft),
        "planId": state["plans"][-1]["id"], "assessment": {"modality": "visual",
            "interval": {"startSeconds": 0, "durationSeconds": 2},
            "findings": [{"dimension": "intent", "sceneIds": ["reveal"], "status": "pass"}]}})
    project.save(db, record, state, state["version"])
    db.commit()
    changed = plan()
    changed["scenes"][0]["finalState"] = "A different consequence"
    invoke(native, "record_direction_plan", {"plan": changed})
    _, state = project.state(db, record)
    assert director.delivery(state, record, job, draft, [], complete_history(native))["semantic"]["reveal"] == "inconclusive"


def test_invalid_provider_evidence_retains_known_charge_without_promotion(native, monkeypatch):
    monkeypatch.setattr(providers, "PROVIDERS", {})
    asset = add_review(native)
    db, record, job, draft = native
    job.request_payload = {"unlimitedNativeSession": True}
    def evaluate(*_):
        return {"status": "succeeded", "costUsd": .7, "consumedChecksumSha256": "wrong",
                "assessment": {"modality": "audio", "interval": {"startSeconds": 0, "durationSeconds": 2},
                    "findings": [{"dimension": "audiovisual", "status": "pass", "observation": "Unbound claim"}]}}
    providers.register(providers.DirectorProvider("invalid-fixture", "1", "evaluator", ("audio",), "fixture-only",
        lambda *_: {"status": "available"}, evaluate, evaluate))
    result = invoke(native, "request_direction_evaluation", {"providerId": "invalid-fixture", "reviewAssetId": asset.id,
        "modality": "audio", "interval": {"startSeconds": 0, "durationSeconds": 2}, "operationKey": "invalid-result"})
    assert result["operation"]["status"] == "uncertain"
    assert result["operation"]["costUsd"] == .7 and result["evidence"] is None
    assert job.result_payload["directorOperations"]["measuredCostUsd"] == .7
    assert project.state(db, record)[1]["preferredCandidateId"] is None


def test_lineage_receipt_migration_is_read_only_by_default(native, monkeypatch):
    import importlib.util
    from pathlib import Path
    from uuid import uuid4
    from app.services.studios import compatibility
    db, parent, _, _ = native
    child = CreativeDocument(id=str(uuid4()), workspace_id=parent.workspace_id, title="Existing clone", kind="document",
        document=parent.document, canonical_document=parent.canonical_document, revision=1)
    db.add(child)
    db.commit()
    monkeypatch.setattr(compatibility, "record_to_contract", lambda _: SimpleNamespace(
        native_editor_state=SimpleNamespace(checksum_sha256="b" * 64)))
    path = Path(__file__).resolve().parents[2] / "scripts/validation/clicko-director-link-lineage.py"
    spec = importlib.util.spec_from_file_location("link_lineage", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = {"documentId": child.id, "sourceDocumentId": parent.id, "sourceRevision": parent.revision,
               "sourceSha256": "b" * 64, "sourcePreserved": True}
    report = module.link_receipts(db, [receipt])
    assert report[0]["applied"] is False and project.lineage(db, child)["sourceDocumentId"] is None
    with pytest.raises(ValueError, match="not_verified"):
        module.link_receipts(db, [{**receipt, "sourceSha256": "c" * 64}], apply=True)
    module.link_receipts(db, [receipt], apply=True)
    assert project.lineage(db, child)["sourceDocumentId"] == parent.id

def test_cycle_progress_is_persistent_and_history_follows_visual_diagnosis(native):
    db, record, _, _ = native
    _, state = project.state(db, record)
    state['cycle'] = {'documentId': record.id, 'stage': 'diagnosis', 'events': [],
                      'processHistory': [{'label': 'B', 'recordedCostUsd': 2}]}
    project.save(db, record, state, state['version'])
    db.commit()
    assert 'processHistory' not in project.context(db, record, '')['autonomousCycle']
    with pytest.raises(ValueError, match='visual_diagnosis_required'):
        invoke(native, 'inspect_cycle_history', {})
    with pytest.raises(ValueError, match='observations_required'):
        invoke(native, 'record_cycle_progress', {'stage': 'diagnosis', 'summary': 'Observed a regression', 'toolUseIds': ['missing']})
    invoke(native, 'record_cycle_progress', {'stage': 'diagnosis', 'summary': 'The action is unclear',
           'toolUseIds': ['observed']}, [{'toolUseId': 'observed', 'ok': True, 'name': 'review_clip'}])
    assert invoke(native, 'inspect_cycle_history', {})['historicalProcesses'][0]['label'] == 'B'
    assert project.context(db, record, '')['autonomousCycle']['events'][0]['summary'] == 'The action is unclear'

def test_confirmed_response_can_resume_saved_draft_after_internal_failure():
    from app.services.studios.craft_agent import can_resume
    job = SimpleNamespace(status='failed', error_code='craft_agent_failed', request_payload={'generationBudgetUsd': None},
        result_payload={'draft': {'batches': 3}, 'submissionOutcome': 'response_received', 'pendingTurnBudget': None})
    assert can_resume(job)
    job.result_payload['submissionOutcome'] = 'submitting'
    assert not can_resume(job)
    job.result_payload.update(submissionOutcome='response_received', pendingTurnBudget={'maxOutputTokens': 100})
    assert not can_resume(job)
