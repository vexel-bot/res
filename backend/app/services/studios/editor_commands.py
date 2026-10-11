"""Atomic recipe authoring on the canonical contextual document and event ledger."""

from datetime import UTC, datetime
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ...domain.studios.contextual_editing import digest
from ...domain.studios.contextual_editing_v2 import ContextualEditPlanV2, ContextualPlanRequestV2
from ...domain.studios.contracts import ReviewReferenceV1
from ...domain.studios.editor_commands import (
    EditorCommandReceiptV1,
    EditorEvaluationSummaryV1,
    SetRecipeKeyframeV1,
    SetRecipeParentV1,
    UndoEditorCommandV1,
)
from ...domain.studios.motion import motion_graph_digest
from ...models import CreativeDocument, StudioDomainEvent
from . import contextual_editing as plans
from .compatibility import persist_contract, record_to_contract
from .contextual_assembly import validate_transcript_bindings
from .contextual_editing_v2 import preflight_v2
from .kernel import emit_event
from .review_binding import invalidate_linked_post_review
from .scene_compiler import compile_scenes, target_id

COMMAND_EVENT = "studio.editor.command.applied"


def _event_id(record, command_id):
    return str(uuid5(NAMESPACE_URL, f"res:editor:v1:{record.workspace_id}:{record.id}:{command_id}"))


def _replay(event, request_digest, user):
    if event.actor_id != user.id or event.payload.get("requestDigest") != request_digest:
        raise ValueError("editor_idempotency_conflict")
    return EditorCommandReceiptV1.model_validate(event.payload["receipt"])


def _bound_plan(db, record, document, plan_id):
    plan = plans.get_plan(db, record.workspace_id, plan_id)
    if (not isinstance(plan, ContextualEditPlanV2) or plan.document_id != record.id
            or plan.status != "applied" or plan.blockers
            or document.composition.narrative.get("contextualPlanId") != plan.id):
        raise ValueError("editor_applied_v2_plan_required")
    if plan.source_digest != plans._source_digest(document) or plan.document_revision != document.revision:
        raise ValueError("editor_document_conflict")
    if digest(document.composition.narrative.get("editorialV2", {}).get("motionGraph")) != digest(plan.motion_graph):
        raise ValueError("editor_graph_binding_conflict")
    return plan


def _edit_direction(direction, actions):
    raw = direction.model_dump(mode="json", by_alias=True)
    for action in actions:
        scene = next((s for s in raw["scenes"] if s["id"] == action.scene_id), None)
        recipe = next((r for r in scene["motionRecipes"] if r["id"] == action.recipe_id), None) if scene else None
        if recipe is None:
            raise ValueError("editor_recipe_target_not_found")
        if isinstance(action, SetRecipeKeyframeV1):
            track = next((t for t in recipe["parameters"]["tracks"]
                          if t["targetId"] == action.target_id and t["property"] == action.property), None)
            if track is None:
                raise ValueError("editor_track_target_not_found")
            keys = {k["frame"]: k for k in track["keyframes"]}
            keys[action.keyframe.frame] = action.keyframe.model_dump(mode="json", by_alias=True)
            track["keyframes"] = [keys[f] for f in sorted(keys)]
        elif isinstance(action, SetRecipeParentV1):
            if recipe["technique"] != "layer_rig":
                raise ValueError("editor_parent_recipe_unsupported")
            parent = next((e for e in scene["elements"] if e["id"] == action.parent_target_id), None)
            if parent is None or parent["kind"] != "group":
                raise ValueError("editor_parent_group_required")
            for element in scene["elements"]:
                if element["id"] in recipe["targetIds"]:
                    element["parentId"] = action.parent_target_id
            recipe["parameters"]["parentTargetId"] = action.parent_target_id
        else:
            if recipe["technique"] != "motion_choreography":
                raise ValueError("editor_pivot_recipe_unsupported")
            recipe["parameters"]["pivot"] = list(action.pivot)
    # Revalidate the full existing schema, including ordering, bounds and target dependencies.
    return ContextualPlanRequestV2.model_validate(raw)


def apply_command(db, record, request, user):
    if request.document_id != record.id:
        raise ValueError("editor_document_identity_conflict")
    request_digest = digest(request)
    event_id = _event_id(record, request.command_id)
    existing = db.get(StudioDomainEvent, event_id)
    if existing:
        return _replay(existing, request_digest, user)
    try:
        # A conditional UPDATE obtains a write lock on SQLite too (FOR UPDATE does not).
        # The stored revision is unchanged until all projections and receipts are ready.
        result = db.execute(update(CreativeDocument).where(
            CreativeDocument.id == record.id,
            CreativeDocument.revision == request.expected_document_revision,
        ).values(revision=CreativeDocument.revision).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise ValueError("editor_document_conflict")
        db.refresh(record)
        # Another transaction can have completed this same command while we waited for its lock.
        existing = db.get(StudioDomainEvent, event_id)
        if existing:
            receipt = _replay(existing, request_digest, user)
            db.rollback()
            return receipt
        document = record_to_contract(record)
        plan = _bound_plan(db, record, document, request.plan_id)
        if document.composition.narrative.get("editorialV2", {}).get("renderer") != "remotion.contextual-v2":
            raise ValueError("editor_native_renderer_required")
        if plan.revision != request.expected_plan_revision:
            raise ValueError("editor_plan_revision_conflict")
        validate_transcript_bindings(db, record, plan.source_transcripts)
        before = ContextualPlanRequestV2.model_validate(
            plan.manifest.get("executableDirection") or plan.direction.model_dump(mode="json", by_alias=True)
        )
        if isinstance(request.actions[0], UndoEditorCommandV1):
            previous = db.get(StudioDomainEvent, _event_id(record, request.actions[0].command_id))
            if not previous or previous.payload["receipt"]["planId"] != plan.id:
                raise ValueError("editor_undo_command_not_found")
            old_receipt = previous.payload["receipt"]
            if (old_receipt["documentRevision"] != document.revision
                    or old_receipt["planRevision"] != plan.revision):
                raise ValueError("editor_undo_revision_conflict")
            direction = ContextualPlanRequestV2.model_validate(previous.payload["beforeDirection"])
        else:
            direction = _edit_direction(before, request.actions)
        direction.expected_document_revision = document.revision
        draft, graph, operations, manifest = compile_scenes(document, direction, user.id, plan.id)
        if manifest["missingMaterials"]:
            raise ValueError("editor_material_required")
        draft.revision = document.revision + 1
        draft.actor_id = user.id
        draft.status = "draft"
        draft.review = ReviewReferenceV1()
        draft.updated_at = datetime.now(UTC)
        graph.document_revision = draft.revision
        draft.composition.narrative["editorialV2"]["motionGraph"] = graph.model_dump(mode="json", by_alias=True)
        blockers, _ = preflight_v2(db, draft)
        if blockers:
            raise ValueError("editor_preflight_required:" + ",".join(b.code for b in blockers))
        # Structural/technical checks are admission gates, never an aesthetic approval.
        from ...domain.studios.motion import evaluate_motion_graph
        from ...domain.studios.visual_audit import preflight_visual
        from .production_audit import blocking_visual_findings

        executable = ContextualPlanRequestV2.model_validate(manifest["executableDirection"])
        visual = preflight_visual(executable, graph, canvas_width=graph.canvas_width, canvas_height=graph.canvas_height)
        if blocking_visual_findings(visual):
            raise ValueError("editor_visual_preflight_required")
        from .editorial_operation_selection import evaluate_operation_bindings

        decisions = evaluate_operation_bindings(executable, draft)
        if any(d["status"] == "blocked" for d in decisions):
            raise ValueError("editor_operation_prerequisite_required")
        manifest["visualAudit"] = visual
        manifest["operationDecisions"] = decisions
        manifest["omittedOptionalMaterials"] = plan.manifest.get("omittedOptionalMaterials", [])
        manifest["editorCommand"] = {
            "commandId": request.command_id, "previousPlanRevision": plan.revision,
            "previousSourceDirectionDigest": plan.manifest.get("hashes", {}).get("sourceDirection"),
        }
        if not evaluate_motion_graph(draft, graph).eligible_for_reviewed_projection:
            raise ValueError("editor_motion_preflight_required")
        invalidate_linked_post_review(db, record)
        persist_contract(record, draft)
        plan.direction = executable
        plan.draft_document = draft
        plan.motion_graph = graph
        plan.operations = operations
        plan.manifest = manifest
        plan.document_revision = draft.revision
        plan.source_digest = plans._source_digest(draft)
        plan.revision += 1
        plan.evaluation = {"technical": "pending", "audiovisual": "pending", "human": "pending"}
        plan.human_approved = False
        receipt = EditorCommandReceiptV1(
            command_id=request.command_id, document_id=record.id, plan_id=plan.id, actor_id=user.id,
            previous_document_revision=document.revision, document_revision=draft.revision,
            plan_revision=plan.revision, document_digest=plan.source_digest,
            executable_composition_digest=manifest["hashes"]["executableComposition"], applied_changes=request.actions,
            warnings=list(graph.abstentions),
        )
        plans._save(db, record, plan, user, {"editorCommandId": request.command_id})
        event = emit_event(
            db, workspace_id=record.workspace_id, event_type=COMMAND_EVENT, aggregate_type="creative_document",
            aggregate_id=record.id, correlation_id=f"editor:{request.command_id}", actor_id=user.id,
            payload={"requestDigest": request_digest, "beforeDirection": before.model_dump(mode="json", by_alias=True),
                     "receipt": receipt.model_dump(mode="json", by_alias=True)},
        )
        event.id = event_id
        db.commit()
        return receipt
    except IntegrityError:
        db.rollback()
        existing = db.get(StudioDomainEvent, event_id)
        if existing:
            return _replay(existing, request_digest, user)
        raise
    except ValueError:
        db.rollback()
        # Revision CAS can fail for a concurrent identical request; its immutable receipt wins.
        existing = db.get(StudioDomainEvent, event_id)
        if existing:
            return _replay(existing, request_digest, user)
        raise


def evaluated_value(keys, frame):
    """Local scalar interpolation matching remotion.contextual-v2, including left-key hold."""
    if frame <= keys[0].frame:
        return keys[0].value
    for left, right in zip(keys, keys[1:], strict=False):
        if frame >= right.frame:
            continue
        p = max(0, min(1, (frame - left.frame) / (right.frame - left.frame)))
        if left.easing == "hold":
            p = 0
        elif left.easing == "ease_in":
            p *= p
        elif left.easing == "ease_out":
            p = 1 - (1 - p) ** 2
        elif left.easing == "ease_in_out":
            p = 2 * p * p if p < .5 else 1 - (-2 * p + 2) ** 2 / 2
        elif left.easing == "cubic_bezier":
            x1, y1, x2, y2 = left.cubic_bezier

            def curve(t, u, v):
                return 3 * (1 - t) ** 2 * t * u + 3 * (1 - t) * t * t * v + t ** 3

            low, high = 0, 1
            for _ in range(18):
                middle = (low + high) / 2
                if curve(middle, x1, x2) < p:
                    low = middle
                else:
                    high = middle
            p = curve((low + high) / 2, y1, y2)
        return left.value + (right.value - left.value) * p
    return keys[-1].value


def _evaluation_summary(evaluation, document_id, frame):
    def state(axis):
        value = evaluation.get(axis)
        if isinstance(value, dict):
            value = value.get("status")
        return value if isinstance(value, str) else None

    return EditorEvaluationSummaryV1(
        technical=state("technical"), audiovisual=state("audiovisual"), human=state("human"),
        full_inspection_path=(
            f"/api/v1/studios/v1/documents/{quote(document_id, safe='')}/editor/inspection?frame={frame}"
        ),
    ).model_dump(mode="json", by_alias=True)


def inspect_editor(db, record, frame, *, evaluation_detail="full"):
    if evaluation_detail not in {"full", "summary"}:
        raise ValueError("editor_evaluation_detail_invalid")
    document = record_to_contract(record)
    plan_id = document.composition.narrative.get("contextualPlanId")
    if not plan_id:
        raise ValueError("editor_applied_v2_plan_required")
    plan = _bound_plan(db, record, document, plan_id)
    graph = plan.motion_graph
    if frame >= graph.duration_frames:
        raise ValueError("editor_frame_out_of_range")
    tracks = [{**track.model_dump(mode="json", by_alias=True),
               "evaluatedLocalValue": evaluated_value(track.keyframes, frame)} for track in graph.tracks]
    indexed = {n.node_id: n for n in graph.nodes}
    scene_roots = {"node-" + target_id(s["sceneId"], "scene-root"): s["sceneId"]
                   for s in plan.manifest.get("scenes", [])}
    layer_scenes = {}
    for node in graph.nodes:
        root = node
        while root.parent_node_id:
            root = indexed[root.parent_node_id]
        if root.node_id in scene_roots:
            layer_scenes[node.target_layer_id] = scene_roots[root.node_id]
    events = list(db.scalars(select(StudioDomainEvent).where(
        StudioDomainEvent.workspace_id == record.workspace_id, StudioDomainEvent.aggregate_id == record.id,
        StudioDomainEvent.event_type == COMMAND_EVENT,
    ).order_by(StudioDomainEvent.occurred_at.desc(), StudioDomainEvent.id.desc()).limit(20)).all())
    return {
        "schemaVersion": ("studio.editor-inspection.v1" if evaluation_detail == "full"
                          else "studio.editor-inspection.v2"),
        "document": document.model_dump(mode="json", by_alias=True),
        "renderer": document.composition.narrative["editorialV2"].get("renderer", "hyperframes.contextual-v2"),
        "planId": plan.id, "planRevision": plan.revision, "documentDigest": plan.source_digest,
        "graphDigest": motion_graph_digest(graph), "frame": frame, "durationFrames": graph.duration_frames,
        "frameRate": graph.frame_rate.model_dump(mode="json"),
        "nodes": [n.model_dump(mode="json", by_alias=True) for n in graph.nodes],
        "tracks": tracks, "scenes": plan.manifest.get("scenes", []),
        "layerScenes": layer_scenes,
        "recipes": document.composition.narrative["editorialV2"].get("motionRecipes", []),
        "parentCandidates": [{"sceneId": scene.id, "targetId": element.id}
                             for scene in plan.direction.scenes for element in scene.elements
                             if element.kind == "group"],
        "versions": {k: plan.manifest.get(k) for k in ("compilerVersion", "runtimeVersion", "componentLibraryVersion")},
        "hashes": plan.manifest.get("hashes", {}),
        "evaluation": (plan.evaluation if evaluation_detail == "full"
                       else _evaluation_summary(plan.evaluation, document.document_id, frame)),
        "pending": ["evaluated_values_are_local_scalars", "render_geometry_not_measured",
                    "human_visual_review_required"],
        "history": [e.payload["receipt"] for e in events],
    }
