"""Native director v2: durable decisions, bound evidence and comparative delivery."""
import copy
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from ...domain.studios.craft_direction_v2 import Comparison, DirectionPlan, Evaluation, Interval
from ...models import CreativeDocument, LibraryAsset
from . import craft_project_context as project
from .craft_delivery import delivery_review
from .craft_history import review_artifact_index
from .craft_director_contracts import tool_schema


def tools():
    definitions = {
        "inspect_direction": "Read compact family context or a full saved plan/candidate/evidence with payload.id. Read before a write to get expectedVersion. payload.kind=plan_schema retrieves the plan schema. payload.kind=observations with offset/limit pages completed tool identifiers; default context shows the recent identifiers.",
        "record_cycle_progress": "Persist the current autonomous-cycle stage and its evidence. payload.stage is diagnosis, experiment, production, comparison or delivered; payload.summary explains findings/decision, payload.toolUseIds cites completed observations or edits. Record a diagnosis before inspecting process history, an experiment result before full production, and a comparison before final draft export. Creative choices remain yours.",
        "inspect_cycle_history": "Read verified historical execution logs and costs after recording your visual diagnosis. Earlier candidate labels remain neutral. This tool does not provide author rationale to the visual evaluator.",
        "record_direction_plan": "Persist a structured craft.direction.v2 plan. payload.plan must include audiencePromise, desiredExperience, referenceIds, referenceInterpretation, chosenDirection, alternatives, rejectionReasons, progression, payoff, visualLanguage, soundLanguage, uncertainties, experiment, summary, scenes. Each scene: id, purpose, initialState, event, finalState, framing, lighting, movement, continuity, sound, interval {startSeconds,durationSeconds}, essential, materials, capabilityIds, unmetNeeds, acceptance. No fixed creative recipe.",
        "manage_direction_issue": "Create/update a persistent issue. payload: id(optional), description, interval(optional), status(open/resolved/refuted/limitation), evidenceIds, rationale. Closure requires current evidence; limitation never passes quality.",
        "record_revision_hypothesis": "Before changing a candidate record payload.problem, change, expectedGain, possibleLosses. This records a proposal, not a plan update or user approval. If essential intentions change, version the complete direction plan with record_direction_plan; preserve unrealized prior intentions and evidence as limitations/issues.",
        "inspect_production_capabilities": "List accessible production routes and qualified evaluators. Documented, available and execution-validated are separate states.",
        "request_direction_evaluation": "Request qualified perception using payload.providerId, reviewAssetId, modality(visual/audio/audiovisual), interval, operationKey. Sampling goes in payload.parameters {fps, maximumSide}; sampling is accepted as an alias. Choose short windows and adequate fps for momentary actions. Optional payload.questions is a list of review questions. For blind comparison add baselineReviewAssetId and, for a focused comparison, baselineInterval {startSeconds,durationSeconds}. If omitted, the full baseline review clip is used. The adapter must consume both media and report original/matched audio evidence to claim loudness matching. Poll using payload.operationId. Uncertain submissions are never resubmitted.",
        "request_direction_material": "Request a qualified material operation using payload.providerId, operationKey, requirement, parameters. Poll with operationId. For native scene creation, animation, composition and effects use run_motion_script or edit_project under your own direction, inspect available engine operations and review the rendered results. To locate/acquire existing sources use find_material_sources/acquire_material.",
        "stage_direction_material": "Stage the verified result of a successful production operation for native editing. payload.operationId. Does not add a layer; inspect the material before use, then asset.import.",
        "save_direction_candidate": "Pin current native draft and a persisted review artifact: payload.reviewAssetId, label. Stores immutable candidate, not an automatic promotion.",
        "compare_direction_candidates": "Record payload candidateId, baselineId, gains, losses, uncertainties, evidenceIds, rationale, decision(preserve/promote/rebuild/combine), soundComparison(original_and_matched/original_only/not_assessed). Promotion checks current revision, full technical coverage and persistent issues. Unknown semantic/audio quality stays inconclusive.",
    }
    definitions["compare_direction_candidates"] += (
        " Use decision=select_draft to choose a complete draft for delivery, comparing any preserved candidate. "
        "This does not promote audiovisual quality or record human approval. Promote requires baselineId to equal "
        "the formal preferredCandidateId (possibly null) and complete evidence; select_draft does not."
    )
    definitions["request_direction_evaluation"] += (
        " interval uses absolute composition seconds by default. Set timeOrigin=clip for seconds relative to the clip start."
    )
    definitions["inspect_direction"] += " payload.kind=execution retrieves persisted execution receipts/checks; kind=costs returns stage usage and uncertain/pending exposure."
    definitions["record_direction_plan"] += (
        " New reference-led motion sessions require referenceObservations [{referenceId,observed,limits}] "
        "bound to actual inspect_reference results, and productionChecks/aestheticCriteria arrays on essential scenes."
    )
    return [{"name": name, "description": description, "input_schema": tool_schema(name)}
            for name, description in definitions.items()]


TOOL_NAMES = {item["name"] for item in tools()}


def binding(record, job, draft):
    return {"documentId": record.id, "documentRevision": record.revision, "jobId": job.id,
            "draftBatch": draft.batches,
            "nativeChecksumSha256": hashlib.sha256(Path(draft.params["nativePath"]).read_bytes()).hexdigest()}


def same_binding(left, right):
    return all(left.get(key) == right.get(key) for key in (
        "documentId", "documentRevision", "jobId", "draftBatch", "nativeChecksumSha256"))


def cycle_evidence_error(code, current, evidence, scenes):
    detail = {"nextAction": "Use review_clip on this native revision, then request_direction_evaluation. "
              "A prior batch or merely rendering the clip does not establish current visual evidence.",
              "currentBinding": current, "currentEvidenceIds": [e["id"] for e in evidence if e.get("id")],
              "requiredScenes": [{"id": s["id"], "interval": s["interval"]} for s in scenes],
              "failedEvidenceIds": [e["id"] for e in evidence if e.get("id") and any(
                  f["status"] == "fail" for f in e["assessment"]["findings"])]}
    return ValueError(code + ": " + json.dumps(detail, ensure_ascii=False, separators=(",", ":")))


def require_cycle_evaluation(state, record, job, draft, *, experiment=False):
    """New cycles cannot bypass current visual evidence by exporting a draft."""
    if not state.get("cycle", {}).get("requireVisualEvaluation"):
        return
    plan = latest_plan(state, record)
    current = binding(record, job, draft)
    evidence = [e for e in state["evidence"] if same_binding(e["binding"], current)
                and plan and e.get("planId") == plan["id"] and e["assessment"]["modality"] == "visual"]
    scenes = [s for s in plan["plan"]["scenes"] if s["essential"]] if plan else []
    if experiment:
        if any(f["status"] == "fail" for e in evidence for f in e["assessment"]["findings"]) or not any(f["dimension"] == "intent" and f["status"] == "pass"
                   for e in evidence for f in e["assessment"]["findings"]):
            raise cycle_evidence_error("craft_cycle_experiment_visual_evidence_required", current, evidence, scenes)
        if getattr(job, "request_payload", {}).get("motionQualityProfile") == "reference-led-v1" and not any(
                f["dimension"] == "craft" and f["status"] == "pass" for e in evidence for f in e["assessment"]["findings"]):
            raise ValueError("craft_motion_experiment_finish_required: Assess craft separately on the chosen short experiment. "
                             "Intent passing does not establish finish. Inspect detail and native-rate movement as needed.")
        return
    if not scenes or any(not any(contains(e["assessment"]["interval"], s["interval"])
            and any(f["dimension"] == "intent" and s["id"] in f["sceneIds"] and f["status"] == "pass"
                    for f in e["assessment"]["findings"]) for e in evidence) for s in scenes):
        raise cycle_evidence_error("craft_cycle_current_visual_intent_evidence_required", current, evidence, scenes)
    if any(f["status"] == "fail" for e in evidence for f in e["assessment"]["findings"]):
        raise cycle_evidence_error("craft_cycle_visual_defects_require_revision", current, evidence, scenes)


def latest_plan(state, record):
    ids = [record.id]
    return next((p for p in reversed(state["plans"]) if p["documentId"] in ids), None)


def review_asset(db, record, identifier, current=None):
    asset = db.scalar(select(LibraryAsset).where(
        LibraryAsset.id == identifier, LibraryAsset.workspace_id == record.workspace_id,
        LibraryAsset.lifecycle_status == "active"))
    origin = (asset.object_metadata or {}).get("craftReview", {}) if asset else {}
    report = origin.get("report", {})
    source = report.get("source", {})
    observed = {"documentId": origin.get("documentId"), "documentRevision": origin.get("documentRevision"),
                "jobId": origin.get("jobId"), "draftBatch": origin.get("draftBatch"),
                "nativeChecksumSha256": source.get("nativeChecksumSha256")}
    if not asset or not origin or (current and not same_binding(observed, current)):
        raise ValueError("craft_review_binding_conflict")
    return asset, report, observed


def delivery(state, record, job, draft, windows, tool_history, *, final=False):
    current = binding(record, job, draft)
    plan = latest_plan(state, record)
    essential = [s for s in plan["plan"]["scenes"] if s["essential"]] if plan else []
    required = [*windows, *(scene["interval"] for scene in essential)]
    unresolved = [issue["description"] for issue in state["issues"]
                  if (issue.get("scope") == "family" or issue.get("binding", {}).get("documentId", record.id) == record.id)
                  and (issue["status"] in {"open", "limitation"}
                       or not same_binding(issue.get("binding", {}), current))]
    current_tools = [t for t in tool_history if t.get("name") != "review_clip" or
                     t.get("observation", {}).get("source", {}).get("nativeChecksumSha256") == current["nativeChecksumSha256"]]
    technical = delivery_review(current_tools, draft.batches, draft.project.get("durationMs", 0) / 1000, required)
    evidence = [e for e in state["evidence"] if same_binding(e["binding"], current)
                and plan and e.get("planId") == plan["id"]]
    semantic = {}
    craft = {}
    for scene in essential:
        findings = [f for e in evidence for f in e["assessment"]["findings"]
                    if f["dimension"] == "intent" and scene["id"] in f["sceneIds"]
                    and contains(e["assessment"]["interval"], scene["interval"])]
        semantic[scene["id"]] = verdict(findings)
        craft[scene["id"]] = verdict([f for e in evidence for f in e["assessment"]["findings"]
            if f["dimension"] == "craft" and scene["id"] in f["sceneIds"]
            and contains(e["assessment"]["interval"], scene["interval"])])
    audiovisual = verdict([f for e in evidence if e["assessment"]["modality"] == "audiovisual"
                           and contains(e["assessment"]["interval"], {"startSeconds": 0,
                               "durationSeconds": draft.project.get("durationMs", 0) / 1000})
                           for f in e["assessment"]["findings"] if f["dimension"] == "audiovisual"])
    references = (job.result_payload or {}).get("referenceInspections", [])
    requested_refs = plan["plan"]["referenceIds"] if plan else []
    external = any(e.get("referenceId") in requested_refs and not e.get("baseline") for e in references)
    missing = [*technical["missing"], *unresolved]
    if not plan:
        missing.append("structured direction plan")
    if not external:
        missing.append("observed external reference selected by the director")
    if not essential or any(value != "pass" for value in semantic.values()):
        missing.append("essential actions not perceptually established")
    if audiovisual != "pass":
        missing.append("complete audiovisual assessment not established")
    if getattr(job, "request_payload", {}).get("motionQualityProfile") == "reference-led-v1" and (
            not craft or any(v != "pass" for v in craft.values())):
        missing.append("motion finish not established for essential scenes")
    selected = next((c for c in state["candidates"] if c["id"] == state["preferredCandidateId"]), None)
    comparison = next((c for c in reversed(state["comparisons"]) if selected and
                       c.get("candidateId") == selected["id"] and c.get("decision") == "promote"), None)
    compared = bool(selected and comparison and same_binding(selected["binding"], current))
    draft_comparison = next((c for c in reversed(state["comparisons"])
        if c.get("decision") in {"preserve", "select_draft"}
        and same_binding(c.get("binding", {}), current)), None)
    if final and not compared:
        missing.append("current candidate has not been selected through evidence-based comparison")
    return {"schemaVersion": "craft.delivery.v2", "status": "draft" if missing else "reviewed",
            "missing": missing, "technical": technical, "semantic": semantic, "craft": craft, "audiovisual": audiovisual,
            "externalReferenceObserved": external, "binding": current,
            "comparison": {"status": "recorded" if compared else "pending", "id": comparison["id"] if comparison else None,
                           "scope": "formal_audiovisual_promotion"},
            "draftComparison": {"status": "recorded" if draft_comparison else "pending",
                "id": draft_comparison["id"] if draft_comparison else None,
                "candidateId": draft_comparison["candidateId"] if draft_comparison else None,
                "selected": bool(draft_comparison and state.get("draftCandidateId") == draft_comparison["candidateId"])},
            "draftCandidateId": state.get("draftCandidateId"),
            "preferredCandidateId": state["preferredCandidateId"], "approvedCandidateId": state.get("approvedCandidateId"),
            "humanApproval": state["humanApproval"]}


def verdict(findings):
    statuses = [item["status"] for item in findings]
    return "fail" if "fail" in statuses else "pass" if statuses and all(s == "pass" for s in statuses) else "inconclusive"


def contains(outer, inner):
    return (outer["startSeconds"] <= inner["startSeconds"] + .002 and
            outer["startSeconds"] + outer["durationSeconds"] >= inner["startSeconds"] + inner["durationSeconds"] - .002)


def capability_manifest(db, record, draft, job=None):
    from .craft_director_providers import capabilities
    providers = capabilities(db, record, job)
    _, state = project.state(db, record)
    for provider in providers:
        completed = [o for o in state["operations"] if o.get("providerId") == provider["id"]
                     and o.get("providerVersion") == provider["version"] and o.get("status") == "succeeded"]
        provider["qualificationExecution"] = provider.get("validatedExecution")
        provider["validatedExecution"] = [{"operationId": o["id"], "binding": o["binding"]} for o in completed]
    return {"schemaVersion": "craft.capabilities.v2", "buildId": draft.capability.get("buildId"),
            "routes": [
                {"id": "existing_footage", "available": True, "tools": ["find_material_sources", "acquire_material", "inspect_source_media"]},
                {"id": "graphics", "available": True, "tools": ["find_commands", "describe_commands", "edit_project"]},
                {"id": "native_scene_generation", "available": getattr(draft, "engine", None) == "effectcraft",
                 "provider": "effectcraft", "director": getattr(job, "request_payload", {}).get("model"),
                 "tools": ["inspect_editor_capabilities", "describe_commands", "run_motion_script", "edit_project",
                           "preview_frame", "review_clip"],
                 "limitations": ["Creates native scenes, layers, animation and effects through scripting. "
                                 "Specific operations must be discovered and rendered before judging quality."]},
                {"id": "depth_models", "available": None, "reason": "Discover native operations; validate the actual scene."},
                {"id": "generated_material", "available": any(p["kind"] == "production" and p["availability"].get("status") == "available" for p in providers),
                 "reason": "Separate material synthesis requires a qualified adapter. Native procedural scene creation "
                           "uses native_scene_generation under the session director."},
                {"id": "audio_editing", "available": True, "tools": ["find_commands", "edit_project"],
                 "limitations": ["Signal measurements do not establish listening."]}],
            "providers": providers, "executionEvidence": [],
            "interpretation": "Availability is not an execution or aesthetic guarantee. Inspect and verify results."}


def dispatch(db, record, job, draft, name, args, instruction, tool_history, windows, manifests=None):
    payload = args.get("payload", {})
    _, state = project.state(db, record)
    if name == "inspect_direction":
        if payload.get("kind") == "execution":
            return {"version": state["version"], "execution": [
                {"toolUseId": t.get("toolUseId"), "draftBatch": t.get("draftBatch"),
                 "receipt": t.get("executionReceipt"), "verification": t.get("verification")}
                for t in tool_history if t.get("executionReceipt") or t.get("verification")][-48:]}
        if payload.get("kind") == "costs":
            from .craft_motion_validation import cost_breakdown
            from .craft_agent import pending_exposure
            costs = cost_breakdown(job.result_payload or {})
            costs["pendingProviderExposureUsd"] = pending_exposure(job)
            return {"version": state["version"], "costs": costs}
        identifier = payload.get("id")
        if payload.get("kind") == "cycle":
            return {"version": state["version"], "cycle": project.document_cycle(state, record.id)}
        if identifier:
            for collection in ("plans", "evidence", "issues", "candidates", "comparisons", "operations"):
                item = next((x for x in state[collection] if x["id"] == identifier), None)
                if item:
                    return {"version": state["version"], "kind": collection, "item": item}
            raise ValueError("craft_direction_item_missing")
        if payload.get("kind") == "plan_schema":
            return {"version": state["version"], "planSchema": DirectionPlan.model_json_schema(by_alias=True)}
        observations = [{"toolUseId": t.get("toolUseId"), "name": t["name"],
                         "sample": t.get("sample"), "draftBatch": t.get("draftBatch")}
                        for t in tool_history if t.get("ok")]
        if payload.get("kind") == "observations":
            offset, limit = payload.get("offset", 0), payload.get("limit", 24)
            if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
                raise ValueError("craft_observation_page_invalid")
            return {"version": state["version"], "items": observations[offset:offset+limit], "total": len(observations),
                    "nextOffset": offset+limit if offset+limit < len(observations) else None}
        compact = state.get("cycle", {}).get("compactEvidence")
        answer = {**project.context(db, record, instruction), "candidateIndex": [
            {k: c[k] for k in ("id", "label", "binding")} for c in state["candidates"]],
            "reviewArtifactIndex": review_artifact_index(job.result_payload or {}),
            "completedObservationIndex": observations[-24:] if compact else observations,
            "completedObservationTotal": len(observations)}
        if not compact or payload.get("includePlanSchema"):
            answer["planSchema"] = DirectionPlan.model_json_schema(by_alias=True)
        else:
            answer["planSchemaAvailableVia"] = {"kind": "plan_schema"}
        return answer
    if name == "inspect_production_capabilities":
        manifest = capability_manifest(db, record, draft, job)
        from .craft_motion_validation import qualification_protocol
        manifest["motionQualification"] = qualification_protocol(draft.capability.get("buildId"))
        manifest["executionVerificationTools"] = ["probe_motion_script", "verify_motion_execution", "inspect_project", "review_clip"]
        manifest["executionEvidence"] = [{"toolUseId": t.get("toolUseId"), "operation": t["name"],
            "draftBatch": t.get("draftBatch"), "meaning": "Operation completed; aesthetic correctness not implied."}
            for t in tool_history if t.get("ok") and t.get("name") in {"edit_project", "run_motion_script", "review_clip"}]
        return manifest
    if name == "inspect_cycle_history":
        cycle = state.get("cycle", {})
        if not any(event["stage"] == "diagnosis" for event in cycle.get("events", [])):
            raise ValueError("craft_cycle_visual_diagnosis_required")
        return {"historicalProcesses": cycle.get("processHistory", [])}
    if args.get("expectedVersion") != state["version"]:
        raise ValueError(f"craft_direction_version_conflict; current expectedVersion={state['version']}; inspect_direction")
    current = binding(record, job, draft)
    if name in {"request_direction_evaluation", "request_direction_material"}:
        return provider_operation(db, record, job, draft, name, payload, state, current)
    if name == "stage_direction_material":
        return stage_material(db, record, job, draft, state, payload["operationId"], manifests)
    identifier = str(uuid4())
    item = {"id": identifier, "binding": current, "createdAt": datetime.now(UTC).isoformat(), "author": "claude"}
    if name == "record_cycle_progress":
        cycle = state.get("cycle")
        if not cycle or cycle.get("documentId") != record.id:
            raise ValueError("craft_cycle_not_configured")
        if payload.get("stage") not in {"diagnosis", "experiment", "production", "comparison", "delivered"}:
            raise ValueError("craft_cycle_stage_invalid")
        if not str(payload.get("summary", "")).strip():
            raise ValueError("craft_cycle_summary_required")
        if cycle.get("requireVisualEvaluation") and payload["stage"] in {"production", "comparison", "delivered"}:
            require_cycle_evaluation(state, record, job, draft, experiment=payload["stage"] == "production")
        citations = payload.get("toolUseIds", [])
        if not citations or any(not any(t.get("toolUseId") == identifier and t.get("ok")
                                        for t in tool_history) for identifier in citations):
            raise ValueError("craft_cycle_observations_required")
        item.update(stage=payload["stage"], summary=payload["summary"], toolUseIds=citations)
        cycle.update(stage=item["stage"])
        cycle.setdefault("events", []).append(item)
    elif name == "record_direction_plan":
        plan = DirectionPlan.model_validate(payload["plan"]).model_dump(mode="json", by_alias=True)
        if getattr(job, "request_payload", {}).get("motionQualityProfile") == "reference-led-v1":
            inspected = {r.get("referenceId") for r in (job.result_payload or {}).get("referenceInspections", [])}
            if not inspected.intersection(plan["referenceIds"]):
                raise ValueError("craft_motion_reference_observation_required: Choose from referenceVisualEvidence, "
                                 "call inspect_reference, then record its id and observed mechanisms. "
                                 "Technique cards and catalog entries alone are not observed references.")
            if any(o["referenceId"] not in inspected.intersection(plan["referenceIds"])
                   for o in plan["referenceObservations"]):
                raise ValueError("craft_motion_reference_binding_required: Interpret only selected references actually inspected in this session.")
            if not plan["referenceObservations"] or any(not s["aestheticCriteria"] or not s["productionChecks"]
                    for s in plan["scenes"] if s["essential"]):
                raise ValueError("craft_motion_observable_plan_required: Provide referenceObservations and essential-scene "
                                 "productionChecks/aestheticCriteria describing execution checks and visible finish.")
        if not any(scene["essential"] for scene in plan["scenes"]):
            raise ValueError("craft_direction_essential_scene_required")
        duration = draft.project.get("durationMs", 0) / 1000
        if any(s["interval"]["startSeconds"] + s["interval"]["durationSeconds"] > duration + .05 for s in plan["scenes"]):
            # Plans may propose a new duration; delivery checks against the eventual draft.
            item["durationChangePlanned"] = True
        item.update(documentId=record.id, plan=plan, version=len(state["plans"]) + 1)
        state["plans"].append(item)
    elif name == "manage_direction_issue":
        status = payload.get("status", "open")
        if status not in {"open", "resolved", "refuted", "limitation"}:
            raise ValueError("craft_issue_status_invalid")
        old = next((i for i in state["issues"] if i["id"] == payload.get("id")), None)
        if payload.get("id") and not old:
            raise ValueError("craft_issue_missing")
        description = payload.get("description", old["description"] if old else "")
        if not description.strip():
            raise ValueError("craft_issue_description_required")
        evidence_ids = payload.get("evidenceIds", [])
        if status in {"resolved", "refuted"}:
            if not payload.get("rationale") or not evidence_ids or any(not any(
                e["id"] == eid and same_binding(e["binding"], current) for e in state["evidence"]
            ) for eid in evidence_ids):
                raise ValueError("craft_issue_current_evidence_required")
            selected = [e for e in state["evidence"] if e["id"] in evidence_ids]
            interval = payload.get("interval", old.get("interval") if old else None)
            if (any(any(f["status"] == "fail" for f in e["assessment"]["findings"]) for e in selected)
                    or not old or not any(any(f["status"] == "pass" and old["id"] in f.get("issueIds", [])
                                              for f in e["assessment"]["findings"]) for e in selected)
                    or (interval and not any(contains(e["assessment"]["interval"], interval) for e in selected))):
                raise ValueError("craft_issue_resolution_not_established")
        item.update(description=description, status=status, interval=payload.get("interval"),
                    evidenceIds=evidence_ids, rationale=payload.get("rationale"), history=[])
        scope = payload.get("scope", old.get("scope", "document") if old else "document")
        if scope not in {"document", "family"}:
            raise ValueError("craft_issue_scope_invalid")
        item["scope"] = scope
        if old:
            item["id"] = old["id"]
            item["history"] = [*old.get("history", []), {k: v for k, v in old.items() if k != "history"}]
            state["issues"] = [item if i["id"] == old["id"] else i for i in state["issues"]]
        else:
            state["issues"].append(item)
    elif name == "record_revision_hypothesis":
        if not all(isinstance(payload.get(k), str) and payload[k].strip() for k in ("problem", "change", "expectedGain")):
            raise ValueError("craft_revision_hypothesis_required")
        item.update(kind="revision_hypothesis", hypothesis=payload)
        state["operations"].append(item)
    elif name == "save_direction_candidate":
        asset, media_report, _ = review_asset(db, record, payload["reviewAssetId"], current)
        if not contains(media_report["interval"], {"startSeconds": 0, "durationSeconds": draft.project.get("durationMs", 0) / 1000}):
            raise ValueError("craft_candidate_complete_review_media_required")
        from .craft import write_asset
        native = Path(draft.params["nativePath"])
        pinned, _, _ = write_asset(db, record, native, suffix=native.suffix,
                                  media_type="application/octet-stream", asset_type="document",
                                  metadata={"craftCandidate": current}, title=record.title + " · candidate")
        report = delivery(state, record, job, draft, windows, tool_history)
        item.update(label=payload.get("label", "Candidate"), nativeAssetId=pinned.id,
                    reviewAssetId=asset.id, delivery=report,
                    planId=(latest_plan(state, record) or {}).get("id"),
                    media=[{k: m[k] for k in ("assetId", "checksumSha256", "mediaType") if k in m}
                           for m in draft.params.get("media", [])])
        state["candidates"].append(item)
    elif name == "compare_direction_candidates":
        comparison = Comparison.model_validate(payload).model_dump(mode="json", by_alias=True)
        candidate = next((c for c in state["candidates"] if c["id"] == comparison["candidateId"]), None)
        baseline = next((c for c in state["candidates"] if c["id"] == comparison["baselineId"]), None)
        if not candidate or (comparison["baselineId"] and not baseline):
            raise ValueError("craft_candidate_missing")
        if comparison["decision"] == "promote" and comparison["baselineId"] != state["preferredCandidateId"]:
            raise ValueError("craft_candidate_baseline_conflict; promote baselineId must equal preferredCandidateId="
                             + str(state["preferredCandidateId"]) + "; use decision=select_draft for draft delivery")
        allowed = [candidate["binding"], *([baseline["binding"]] if baseline else [])]
        if any(not any(e["id"] == eid and any(same_binding(e["binding"], b) for b in allowed)
                       for e in state["evidence"]) for eid in comparison["evidenceIds"]):
            raise ValueError("craft_comparison_evidence_required")
        for compared in allowed:
            if not any(e["id"] in comparison["evidenceIds"] and same_binding(e["binding"], compared)
                       for e in state["evidence"]):
                raise ValueError("craft_comparison_both_candidates_required: " + json.dumps({
                    "missingBinding": compared, "eligibleEvidenceIds": [e["id"] for e in state["evidence"]
                        if same_binding(e["binding"], compared)],
                    "nextAction": "Inspect both preserved candidates and cite evidence for each; do not invent identifiers."}))
        if comparison["soundComparison"] == "original_and_matched" and not any(
            e["id"] in comparison["evidenceIds"] and e.get("audioComparison") == "original_and_matched"
            for e in state["evidence"]
        ):
            raise ValueError("craft_matched_audio_evidence_required")
        if comparison["decision"] == "promote":
            locked = db.scalar(select(CreativeDocument).where(CreativeDocument.id == record.id).with_for_update()
                               .execution_options(populate_existing=True))
            if locked.revision != current["documentRevision"] or not same_binding(candidate["binding"], current):
                raise ValueError("craft_candidate_revision_conflict")
            report = delivery(state, record, job, draft, windows, tool_history)
            if report["status"] != "reviewed":
                raise ValueError("craft_candidate_evidence_incomplete")
            state["preferredCandidateId"] = candidate["id"]
        if comparison["decision"] == "select_draft":
            if not same_binding(candidate["binding"], current):
                raise ValueError("craft_candidate_revision_conflict")
            state["draftCandidateId"] = candidate["id"]
        item.update(comparison)
        state["comparisons"].append(item)
    else:
        raise ValueError("craft_direction_tool_unknown")
    saved = project.save(db, record, state, state["version"])
    db.commit()
    answer = {"version": saved["version"], "item": item, "preferredCandidateId": saved["preferredCandidateId"]}
    if name == "record_revision_hypothesis":
        answer["planImpact"] = {
            "planChanged": False,
            "activePlanId": (latest_plan(saved, record) or {}).get("id"),
            "instruction": "Evaluations still verify the active plan. If your chosen revision changes essential intentions, "
                           "record a new complete direction plan and preserve unrealized prior intentions as limitations/issues. "
                           "A new plan does not erase previous failed evidence or establish reference quality.",
        }
    return answer


def normalize_evaluation_payload(payload):
    payload = copy.deepcopy(payload)
    allowed = {"operationId", "providerId", "reviewAssetId", "modality", "interval", "operationKey", "timeOrigin",
               "parameters", "sampling", "questions", "baselineReviewAssetId", "baselineInterval", "rationale", "cost"}
    if set(payload) - allowed:
        raise ValueError("craft_evaluation_unknown_fields: " + ", ".join(sorted(set(payload) - allowed)))
    if payload.get("timeOrigin", "composition") not in {"composition", "clip"}:
        raise ValueError("craft_evaluation_time_origin_invalid")
    if "sampling" in payload:
        sampling = payload.pop("sampling")
        if "parameters" in payload and payload["parameters"] != sampling:
            raise ValueError("craft_evaluation_sampling_conflict")
        payload["parameters"] = sampling
    if "questions" in payload and (not isinstance(payload["questions"], list)
            or any(not isinstance(q, str) or not q.strip() for q in payload["questions"])):
        raise ValueError("craft_evaluation_questions_invalid")
    if "baselineInterval" in payload:
        if not payload.get("baselineReviewAssetId"):
            raise ValueError("craft_evaluation_baseline_asset_required")
        payload["baselineInterval"] = Interval.model_validate(payload["baselineInterval"]).model_dump(by_alias=True)
    return payload


def next_evaluation_version(submitted_version, used_version, reply):
    """Only chain new, successful observations with exactly two durable writes."""
    operation = reply.get("operation", {})
    if (type(submitted_version) is int and type(used_version) is int
            and reply.get("evidence") and operation.get("status") == "succeeded"
            and reply.get("version") == used_version + 2):
        return submitted_version, reply["version"]
    return None


def provider_operation(db, record, job, draft, name, payload, state, current):
    from .craft_director_providers import qualified

    kind = "evaluator" if name == "request_direction_evaluation" else "production"
    if kind == "evaluator":
        payload = normalize_evaluation_payload(payload)
    previous = next((o for o in state["operations"] if o["id"] == payload.get("operationId")), None)
    if previous:
        if previous.get("kind") != kind:
            raise ValueError("craft_operation_kind_conflict")
        if previous["status"] in {"succeeded", "failed"}:
            return {"version": state["version"], "operation": previous}
        provider = qualified(previous["providerId"], kind, db, record, previous.get("modality"), job)
        if provider.version != previous["providerVersion"]:
            raise ValueError("craft_operation_provider_changed")
        request = {**previous["request"],
                   "providerOperationId": (previous.get("result") or {}).get("providerOperationId")}
        operation = previous
        execute = provider.poll
    else:
        if payload.get("operationId"):
            raise ValueError("craft_operation_missing")
        key = payload.get("operationKey")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("craft_operation_key_required")
        old = next((o for o in state["operations"] if o.get("operationKey") == key), None)
        if old:
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if digest != old.get("requestDigest"):
                raise ValueError("craft_operation_key_conflict")
            return {"version": state["version"], "operation": old, "instruction": "Poll this operation; do not resubmit."}
        provider = qualified(payload["providerId"], kind, db, record, payload.get("modality"), job)
        if provider.metered and not getattr(job, "request_payload", {}).get("unlimitedNativeSession"):
            raise ValueError("craft_metered_operation_requires_uncapped_session")
        request = copy.deepcopy(payload)
        if kind == "evaluator":
            asset, report, observed = review_asset(db, record, payload["reviewAssetId"])
            family_docs = {record.id, *project.lineage(db, record)["ancestors"]}
            family_docs.update(c["binding"]["documentId"] for c in state["candidates"])
            interval = Interval.model_validate(payload["interval"]).model_dump(by_alias=True)
            if payload.get("timeOrigin") == "clip":
                interval["startSeconds"] += report["interval"]["startSeconds"]
            if observed["documentId"] not in family_docs or not contains(report["interval"], interval):
                raise ValueError("craft_evaluation_interval_conflict: " + json.dumps({
                    "timeOrigin": payload.get("timeOrigin", "composition"), "requestedCompositionInterval": interval,
                    "allowedCompositionInterval": report["interval"],
                    "nextAction": "Use absolute composition seconds, or set timeOrigin=clip for a relative offset."}))
            # Blind media handoff: no author rationale, sequence number or production cost.
            request = {"reviewAssetId": asset.id, "checksumSha256": asset.checksum_sha256,
                       "interval": interval, "modality": payload["modality"],
                       "sourceInterval": report["interval"],
                       "operationKey": key,
                       "parameters": payload.get("parameters", {}),
                       "evaluationInstruction": "Observe the media before any author rationale. "
                       "Report uncertainty. Use original and loudness-matched audio for comparisons when available."}
            relevant_plan = latest_plan(state, record)
            request["assertions"] = [{"sceneId": s["id"], "interval": s["interval"], "acceptance": s["acceptance"]}
                                     for s in relevant_plan["plan"]["scenes"]] if relevant_plan else []
            request["issuesToCheck"] = [{"issueId": i["id"], "description": i["description"], "interval": i.get("interval")}
                                        for i in state["issues"]]
            request["reviewQuestions"] = payload.get("questions", [])
            if payload.get("baselineReviewAssetId"):
                baseline_asset, baseline_report, baseline_binding = review_asset(db, record, payload["baselineReviewAssetId"])
                if baseline_binding["documentId"] not in family_docs:
                    raise ValueError("craft_evaluation_family_conflict")
                # The review receipt also includes endSeconds. The evaluator's
                # Interval contract accepts only start and duration.
                baseline_interval = {key: baseline_report["interval"][key]
                                     for key in ("startSeconds", "durationSeconds")}
                comparison_window = payload.get("baselineInterval", baseline_interval)
                if not contains(baseline_interval, comparison_window):
                    raise ValueError("craft_evaluation_baseline_interval_conflict")
                request["comparisonMedia"] = {"label": "B", "reviewAssetId": baseline_asset.id,
                    "checksumSha256": baseline_asset.checksum_sha256, "interval": comparison_window,
                    "sourceInterval": baseline_interval}
                request["label"] = "A"
            current = observed
        elif not payload.get("requirement"):
            raise ValueError("craft_material_requirement_required")
        if provider.validate:
            provider.validate(request)
        operation = {"id": str(uuid4()), "operationKey": key, "kind": kind, "providerId": provider.id,
                     "requestedByJobId": job.id,
                     "providerVersion": provider.version, "qualification": provider.qualification,
                     "modality": payload.get("modality"), "binding": current, "request": request,
                     "requestDigest": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                     "status": "submitted", "costUsd": None}
        if kind == "evaluator" and request.get("comparisonMedia"):
            operation["comparisonBinding"] = baseline_binding
        if kind == "evaluator":
            operation["planId"] = relevant_plan["id"] if relevant_plan else None
            operation["baselinePlanId"] = next((c.get("planId") for c in state["candidates"]
                if c["reviewAssetId"] == payload.get("baselineReviewAssetId")), None)
        state["operations"].append(operation)
        state = project.save(db, record, state, state["version"])
        db.commit()  # durable before external submission; uncertain submissions can only be polled
        execute = provider.execute
    observed_cost = None
    try:
        response = execute(db, record, request)
        if response.get("status") not in {"succeeded", "failed", "pending", "uncertain"}:
            raise ValueError("craft_provider_result_invalid")
        cost = response.get("costUsd")
        if cost is not None and (type(cost) not in (int, float) or cost < 0 or not math.isfinite(cost)):
            raise ValueError("craft_provider_cost_invalid")
        observed_cost = cost
        if response["status"] == "succeeded" and cost is None:
            raise ValueError("craft_provider_cost_unverified")
        if not provider.metered and cost not in {0, None}:
            raise ValueError("craft_free_provider_reported_cost")
        evidence = None
        baseline_evidence = None
        if response["status"] == "succeeded" and kind == "evaluator":
            assessment = Evaluation.model_validate(response["assessment"]).model_dump(mode="json", by_alias=True)
            if (assessment["modality"] != operation["modality"] or not contains(request["interval"], assessment["interval"])
                    or response.get("consumedChecksumSha256") != request["checksumSha256"]):
                raise ValueError("craft_perception_evidence_binding_invalid")
            evidence = {"id": str(uuid4()), "binding": operation["binding"], "providerId": provider.id,
                        "planId": operation.get("planId"),
                        "providerVersion": provider.version, "qualification": provider.qualification,
                        "assetId": request["reviewAssetId"], "checksumSha256": request["checksumSha256"],
                        "audioComparison": "not_assessed",
                        "assessment": assessment}
            if request.get("comparisonMedia"):
                comparison_media = request["comparisonMedia"]
                consumed = response.get("consumedComparisonChecksums", [])
                if set(consumed) != {request["checksumSha256"], comparison_media["checksumSha256"]}:
                    raise ValueError("craft_comparison_media_not_consumed")
                baseline_assessment = Evaluation.model_validate(response["baselineAssessment"]).model_dump(mode="json", by_alias=True)
                if (baseline_assessment["modality"] != operation["modality"] or
                        not contains(comparison_media["interval"], baseline_assessment["interval"])):
                    raise ValueError("craft_comparison_interval_conflict")
                baseline_evidence = {**evidence, "id": str(uuid4()), "binding": operation["comparisonBinding"],
                    "planId": operation.get("baselinePlanId"),
                    "assetId": comparison_media["reviewAssetId"], "checksumSha256": comparison_media["checksumSha256"],
                    "assessment": baseline_assessment}
                if response.get("audioComparison") == "original_only" and operation["modality"] in {"audio", "audiovisual"}:
                    for item in (evidence, baseline_evidence):
                        item["audioComparison"] = "original_only"
                if response.get("audioComparison") == "original_and_matched":
                    match = response.get("loudnessMatch", {})
                    if (operation["modality"] not in {"audio", "audiovisual"} or not match.get("method")
                            or match.get("originalAudition") is not True or match.get("matchedAudition") is not True
                            or any(type(match.get(k)) not in (int, float) or not math.isfinite(match[k])
                                   for k in ("gainDbA", "gainDbB"))):
                        raise ValueError("craft_loudness_match_evidence_required")
                    for item in (evidence, baseline_evidence):
                        item.update(audioComparison="original_and_matched", loudnessMatch=match)
        elif response["status"] == "succeeded":
            db.flush()
            asset = db.scalar(select(LibraryAsset).where(LibraryAsset.id == response.get("assetId"),
                              LibraryAsset.workspace_id == record.workspace_id, LibraryAsset.lifecycle_status == "active"))
            if not asset or asset.checksum_sha256 != response.get("checksumSha256"):
                raise ValueError("craft_production_asset_binding_invalid")
            response["inspectionRequired"] = True
    except Exception as exc:
        response = {"status": "uncertain", "costUsd": observed_cost, "errorType": type(exc).__name__,
                    "instruction": "Submission outcome uncertain; reconcile by operationKey, never blindly resubmit."}
        evidence = None
        baseline_evidence = None
    if previous and request.get("providerOperationId") and not response.get("providerOperationId"):
        response["providerOperationId"] = request["providerOperationId"]
    _, latest = project.state(db, record)
    updated = {**operation, "status": response["status"],
               "costUsd": response.get("costUsd") if response.get("costUsd") is not None else operation.get("costUsd"),
               "result": response}
    latest["operations"] = [updated if o["id"] == operation["id"] else o for o in latest["operations"]]
    if evidence:
        latest["evidence"].append(evidence)
    if baseline_evidence:
        latest["evidence"].append(baseline_evidence)
    saved = project.save(db, record, latest, latest["version"])
    job.result_payload = {**job.result_payload, "directorOperations": {
        "measuredCostUsd": sum(o.get("costUsd") or 0 for o in saved["operations"] if o.get("requestedByJobId") == job.id),
        "uncertainOperationIds": [o["id"] for o in saved["operations"] if o.get("status") == "uncertain"
                                  and o.get("requestedByJobId") == job.id]}}
    db.commit()
    return {"version": saved["version"], "operation": updated, "evidence": evidence, "baselineEvidence": baseline_evidence}


def stage_material(db, record, job, draft, state, operation_id, manifests):
    import shutil
    from ...domain.studios.contracts import NativeMediaReferenceV1
    from ..object_storage import get_object_storage, sha256_file
    from .craft_direction import NATIVE_MEDIA

    operation = next((o for o in state["operations"] if o["id"] == operation_id), None)
    if not operation or operation.get("kind") != "production" or operation.get("status") != "succeeded":
        raise ValueError("craft_generated_material_not_ready")
    result = operation["result"]
    asset = db.scalar(select(LibraryAsset).where(LibraryAsset.id == result["assetId"],
                      LibraryAsset.workspace_id == record.workspace_id, LibraryAsset.lifecycle_status == "active"))
    if (not asset or asset.checksum_sha256 != result["checksumSha256"] or asset.media_type not in NATIVE_MEDIA
            or (asset.object_metadata or {}).get("rightsStatus") == "restricted" or manifests is None):
        raise ValueError("craft_generated_material_unavailable")
    relative = f"assets/{asset.id}{Path(asset.storage_key).suffix}"
    target = draft.directory / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
        if sha256_file(source) != asset.checksum_sha256:
            raise ValueError("craft_generated_material_checksum_conflict")
        shutil.copyfile(source, target)
    if not any(m.asset_id == asset.id for m in manifests):
        manifests.append(NativeMediaReferenceV1(assetId=asset.id, path=relative,
                         checksumSha256=asset.checksum_sha256, mediaType=asset.media_type))
        draft.params["media"].append({"assetId": asset.id, "path": str(target), "relativePath": relative,
                                     "checksumSha256": asset.checksum_sha256, "mediaType": asset.media_type})
    info = {"assetId": asset.id, "operationId": operation_id, "mediaType": asset.media_type,
            "checksumSha256": asset.checksum_sha256, "inspectionRequired": True,
            "instruction": "Inspect this source before judging quality or importing it into a scene."}
    job.result_payload = {**job.result_payload, "acquiredSources": {
        **job.result_payload.get("acquiredSources", {}), "generated:" + operation_id: info}}
    db.commit()
    return {"version": state["version"], "material": info}
