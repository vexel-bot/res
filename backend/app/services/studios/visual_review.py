"""Human assessments bind to one export and never approve publication."""

from datetime import UTC, datetime

from ...domain.studios.visual_audit import VisualAuditPolicyV1
from ...models import StudioDomainEvent
from .kernel import emit_event


def record_visual_review(db, document, asset, request, user):
    metadata = asset.object_metadata or {}
    if (
        asset.workspace_id != document.workspace_id
        or asset.lifecycle_status != "active"
        or metadata.get("derivation") != "video_render"
        or metadata.get("documentId") != document.id
        or metadata.get("documentRevision") != document.revision
        or request.expected_document_revision != document.revision
        or request.render_checksum != asset.checksum_sha256
    ):
        raise ValueError("visual_review_binding_conflict")
    minimum = VisualAuditPolicyV1().minimum_human_score
    if metadata.get("provider") == "remotion.contextual-v2" and request.finish is None:
        raise ValueError("visual_review_finish_score_required")
    optional_scores = [request.hierarchy, request.motion_naturalness, request.material_relevance]
    supplied_optional_scores = [score for score in optional_scores if score is not None]
    all_scores = [request.clarity, request.rhythm, request.suitability, request.continuity]
    if request.finish is not None:
        all_scores.append(request.finish)
    all_scores.extend(supplied_optional_scores)
    inspected = request.full_video_inspected and request.mobile_inspected
    scores_complete = request.finish is not None
    receipt = {
        "schemaVersion": "studio.visual-human-review.v1",
        **request.model_dump(mode="json", by_alias=True),
        "assetId": asset.id,
        "reviewedBy": user.id,
        "at": datetime.now(UTC).isoformat(),
        "status": (
            "requires_correction" if min(all_scores) < minimum
            else "incomplete_review" if not inspected or not scores_complete
            else "meets_human_criteria"
        ),
    }
    # Persist history as existing domain events; metadata points to the latest receipt.
    emit_event(
        db,
        workspace_id=document.workspace_id,
        event_type="studio.visual_review.recorded",
        aggregate_type="creative_document",
        aggregate_id=document.id,
        correlation_id=asset.id,
        actor_id=user.id,
        payload=receipt,
    )
    asset.object_metadata = {**metadata, "visualHumanReview": receipt}
    db.flush()
    if not hasattr(db, "query"):
        return receipt
    # Project the review onto every current production run that references this
    # exact export. A later render has a different checksum and cannot inherit it.
    events = db.query(StudioDomainEvent).filter(
        StudioDomainEvent.workspace_id == document.workspace_id,
        StudioDomainEvent.aggregate_type == "editorial-production",
    ).all()
    latest = {}
    for event in events:
        state = event.payload or {}
        if state.get("documentId") != document.id:
            continue
        previous = latest.get(event.aggregate_id)
        if previous is None or state.get("revision", 0) > previous.get("revision", 0):
            latest[event.aggregate_id] = state
    for state in latest.values():
        artifacts = state.get("artifacts", {})
        bound = next(
            (
                value.get("artifact", {})
                for value in (artifacts.get("video"), artifacts.get("animatic"))
                if isinstance(value, dict)
                and value.get("artifact", {}).get("assetId") == asset.id
                and value.get("artifact", {}).get("checksumSha256") == asset.checksum_sha256
            ),
            None,
        )
        if not bound:
            continue
        visual_findings = (state.get("visualAudit") or {}).get("findings", [])
        technical = state.get("technicalEvaluation") or {}
        qualified = bool(
            receipt["status"] == "meets_human_criteria"
            and isinstance(technical, dict)
            and technical.get("status") == "passed"
            and not any(
                finding.get("severity") in {"correction", "blocker"}
                for finding in visual_findings
            )
            and (
                state.get("request", {}).get("demonstrationPolicy") != "required"
                or (len(supplied_optional_scores) == 3 and min(supplied_optional_scores) >= minimum)
            )
            and (
                state.get("request", {}).get("demonstrationPolicy") != "required"
                or state.get("productionGates", {}).get("observedResult", {}).get("status") == "passed"
            )
        )
        from .editing_repertoire import store_render_example
        from .editorial_production import save

        projected = dict(state)
        projected.update(
            humanReview=receipt,
            autonomousProductionQualified=qualified,
            reviewRenderChecksum=asset.checksum_sha256,
        )
        gates = dict(projected.get("productionGates") or {})
        gates["sceneStages"] = [
            {**item, "stage": "human_reviewed"} if item.get("stage") == "observed" else item
            for item in gates.get("sceneStages", [])
        ]
        projected["productionGates"] = gates
        save(db, document, user, projected)
        store_render_example(db, document.workspace_id, projected, receipt)
    return receipt
