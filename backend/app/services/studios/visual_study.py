"""Blind comparisons of directed variants and simple graphic/interface controls."""

import secrets
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from ...domain.studios.contextual_editing import digest
from ...domain.studios.engine_qualification import EngineRenderReferenceV1
from ...models import CreativeDocument, StudioDomainEvent
from .engine_qualification import _reference, _visual_approved
from .kernel import emit_event


def sessions(db, workspace_id):
    events = db.scalars(
        select(StudioDomainEvent)
        .where(
            StudioDomainEvent.workspace_id == workspace_id,
            StudioDomainEvent.aggregate_type == "visual-study-comparison",
        )
        .order_by(StudioDomainEvent.occurred_at, StudioDomainEvent.id)
    ).all()
    latest = {}
    for event in events:
        latest[event.aggregate_id] = event.payload
    return latest


def _record(db, workspace_id, value, user):
    emit_event(
        db,
        workspace_id=workspace_id,
        event_type="studio.visual_study.comparison_recorded",
        aggregate_type="visual-study-comparison",
        aggregate_id=value["id"],
        correlation_id=value["id"],
        actor_id=user.id,
        payload=value,
    )
    db.commit()


def create(db, workspace_id, request, user):
    variants = [_reference(db, workspace_id, ref) for ref in request.variants]
    if len({v["briefDigest"] for v in variants}) != 1 or len({v["sourceDigest"] for v in variants}) != 1:
        raise ValueError("visual_study_common_brief_and_materials_required")
    kinds = []
    languages = set()
    for variant in variants:
        doc = db.get(CreativeDocument, variant["reference"]["documentId"])
        payload = doc.canonical_document or doc.document or {}
        editorial = payload.get("composition", {}).get("narrative", {}).get("editorialV2") or {}
        study = editorial.get("visualStudy") or {}
        languages.add(study.get("language"))
        kind = study.get("variant")
        if kind == "control" and editorial.get("motionRecipes"):
            raise ValueError("visual_study_control_not_simple")
        variant["studyVariant"] = kind
        kinds.append(kind)
    if set(kinds) != {"a", "b", "control"} or len(languages) != 1 or None in languages:
        raise ValueError("visual_study_language_and_variants_required")
    if len({v["recipeDigest"] for v in variants}) != 3:
        raise ValueError("visual_study_distinct_editorial_decisions_required")
    secrets.SystemRandom().shuffle(variants)
    value = {
        "id": str(uuid4()),
        "workspaceId": workspace_id,
        "language": languages.pop(),
        "variants": {chr(65 + i): variant for i, variant in enumerate(variants)},
        "createdBy": user.id,
        "at": datetime.now(UTC).isoformat(),
        "status": "not_assessed",
    }
    _record(db, workspace_id, value, user)
    return project(db, workspace_id, value["id"])


def fresh(db, workspace_id, session):
    current = {}
    for label, variant in session["variants"].items():
        value = _reference(db, workspace_id, EngineRenderReferenceV1.model_validate(variant["reference"]))
        if any(value[k] != variant[k] for k in ("sourceDigest", "briefDigest", "recipeDigest", "provider")):
            raise ValueError("visual_study_comparison_snapshot_changed")
        current[label] = value
    return current


def project(db, workspace_id, identifier):
    session = sessions(db, workspace_id).get(identifier)
    if not session:
        raise ValueError("visual_study_comparison_not_found")
    blockers = []
    try:
        current = fresh(db, workspace_id, session)
        review = session.get("review") or {}
        if review.get("status") == "passed" and not _visual_approved(current[review["preferredLabel"]]):
            blockers.append("visual_study_human_review_changed")
    except ValueError as error:
        blockers.append(str(error))
    return {
        "id": identifier,
        "language": session["language"],
        "status": "stale" if blockers else session["status"],
        "blockers": blockers,
        "labels": [
            {
                "label": label,
                "assetId": variant["reference"]["assetId"],
                "checksum": variant["reference"]["checksum"],
                "documentId": variant["reference"]["documentId"],
                "documentRevision": variant["reference"]["documentRevision"],
            }
            for label, variant in session["variants"].items()
        ],
        "review": session.get("review"),
    }


def review(db, workspace_id, identifier, request, user):
    session = sessions(db, workspace_id).get(identifier)
    if not session:
        raise ValueError("visual_study_comparison_not_found")
    current = fresh(db, workspace_id, session)
    selected = session["variants"][request.preferred_label]
    inspected = all(
        (
            request.full_video_inspected,
            request.mobile_inspected,
            request.blind_review_completed,
            request.same_materials_confirmed,
            request.control_simplicity_confirmed,
            not request.unrecorded_manual_corrections,
        )
    )
    status = (
        "passed"
        if inspected and selected["studyVariant"] != "control" and _visual_approved(current[request.preferred_label])
        else "rejected"
        if inspected and selected["studyVariant"] == "control"
        else "pending"
    )
    session["review"] = {
        **request.model_dump(mode="json", by_alias=True),
        "status": status,
        "reviewedBy": user.id,
        "at": datetime.now(UTC).isoformat(),
        "sessionDigest": digest(session["variants"]),
    }
    session["status"] = status
    _record(db, workspace_id, session, user)
    return project(db, workspace_id, identifier)
