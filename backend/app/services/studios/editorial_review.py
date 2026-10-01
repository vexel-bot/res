"""Server-owned, append-only reviews for explicitly enrolled UGC-avatar documents.

Enrollment cannot be removed by editing client-side narrative flags. Legacy
documents retain existing gates. Editorial approval never grants asset rights,
admits a generated source, activates a model, or authorizes publication.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import CreativeDocumentV1
from ...domain.studios.editorial_review import (
    EDITORIAL_AXES,
    EditorialPlanRequestV1,
    EditorialPlanV1,
    EditorialReadinessV1,
    EditorialReviewRequestV1,
    EditorialReviewV1,
)
from ...models import CreativeDocument, LibraryAsset, StudioDomainEvent, User
from .compatibility import record_to_contract
from .kernel import emit_event
from .review_binding import publication_digest, reviewable_content
from .review_media import verified_library_asset_path

PLAN_EVENT = "studio.editorial.plan_registered"
REVIEW_EVENT = "studio.editorial.reviewed"


def _events(db: Session, document: CreativeDocument) -> list[StudioDomainEvent]:
    return list(db.scalars(select(StudioDomainEvent).where(
        StudioDomainEvent.workspace_id == document.workspace_id,
        StudioDomainEvent.aggregate_type == "editorial_document",
        StudioDomainEvent.aggregate_id == document.id,
    ).order_by(StudioDomainEvent.occurred_at.desc(), StudioDomainEvent.id.desc())).all())


def _asset_digest(db: Session, snapshot: CreativeDocumentV1) -> str:
    bindings = []
    if not snapshot.assets or len({ref.id for ref in snapshot.assets}) != len(snapshot.assets):
        raise ValueError("editorial_assets_required")
    for ref in sorted(snapshot.assets, key=lambda item: item.id):
        asset = db.scalar(select(LibraryAsset).where(
            LibraryAsset.id == ref.id,
            LibraryAsset.workspace_id == snapshot.workspace_id,
            LibraryAsset.lifecycle_status == "active",
        ))
        if (
            asset is None or not ref.checksum or not asset.checksum_sha256
            or ref.checksum.lower() != asset.checksum_sha256.lower()
        ):
            raise ValueError("editorial_asset_binding_invalid")
        # Bind actual server metadata without relabeling synthetic media as UGC.
        bindings.append({
            "id": asset.id, "checksum": asset.checksum_sha256.lower(),
            "mediaType": asset.media_type, "metadata": asset.object_metadata or {},
            "storageBackend": asset.storage_backend, "storageKey": asset.storage_key,
        })
    return publication_digest({"assets": bindings})


def editorial_readiness(db: Session, document: CreativeDocument) -> EditorialReadinessV1:
    events = _events(db, document)
    event = next((item for item in events if item.event_type == PLAN_EVENT), None)
    if event is None:
        return EditorialReadinessV1(managed=False, blockers=["editorial_plan_not_registered"])
    plan = EditorialPlanV1.model_validate(event.payload["record"])
    snapshot = record_to_contract(document)
    blockers = []
    if (
        document.revision != plan.document_revision
        or publication_digest(reviewable_content(snapshot)) != plan.document_digest_sha256
    ):
        blockers.append("editorial_plan_stale")
    try:
        if _asset_digest(db, snapshot) != plan.assets_digest_sha256:
            blockers.append("editorial_assets_changed")
    except ValueError:
        blockers.append("editorial_assets_unavailable")
    reviews = {}
    for item in events:
        if item.event_type != REVIEW_EVENT:
            continue
        review = EditorialReviewV1.model_validate(item.payload["record"])
        if review.review.plan_id == plan.id:
            reviews.setdefault(review.review.axis, review)
    for axis in EDITORIAL_AXES:
        review = reviews.get(axis)
        if review is None:
            blockers.append(f"editorial_{axis}_pending")
        elif review.review.decision != "approved":
            blockers.append(f"editorial_{axis}_rejected")
    return EditorialReadinessV1(
        managed=True, plan=plan,
        reviews=[reviews[axis] for axis in EDITORIAL_AXES if axis in reviews],
        blockers=blockers, full_render_eligible=not blockers,
    )


def _replay(events, event_type, key, request):
    digest = publication_digest(request.model_dump(mode="json", by_alias=True))
    for event in events:
        if event.event_type == event_type and event.payload.get("idempotencyKey") == key:
            if event.payload.get("requestDigest") != digest:
                raise ValueError("editorial_idempotency_conflict")
            return event.payload["record"]
    return None


def _record(db, document, user, event_type, key, request, record):
    emit_event(
        db, workspace_id=document.workspace_id, aggregate_type="editorial_document",
        aggregate_id=document.id, event_type=event_type,
        correlation_id=record.id, actor_id=user.id,
        payload={"idempotencyKey": key,
                 "requestDigest": publication_digest(request.model_dump(mode="json", by_alias=True)),
                 "record": record.model_dump(mode="json", by_alias=True)},
    )
    db.commit()
    return record


def register_editorial_plan(
    db: Session, document: CreativeDocument, request: EditorialPlanRequestV1,
    user: User, key: str,
) -> EditorialPlanV1:
    db.refresh(document, with_for_update=True)
    replay = _replay(_events(db, document), PLAN_EVENT, key, request)
    if replay:
        return EditorialPlanV1.model_validate(replay)
    if document.revision != request.expected_document_revision:
        raise ValueError("editorial_document_conflict")
    snapshot = record_to_contract(document)
    if snapshot.content_type != "video" or snapshot.composition.media_timeline is None:
        raise ValueError("editorial_video_timeline_required")
    known_assets = {asset.id for asset in snapshot.assets}
    if any(not set(beat.evidence_asset_ids) <= known_assets for beat in request.beats):
        raise ValueError("editorial_evidence_not_in_document")
    plan = EditorialPlanV1(
        id=str(uuid4()), workspace_id=document.workspace_id, document_id=document.id,
        document_revision=document.revision,
        document_digest_sha256=publication_digest(reviewable_content(snapshot)),
        assets_digest_sha256=_asset_digest(db, snapshot), plan=request,
        created_by=user.id, created_at=datetime.now(UTC),
    )
    return _record(db, document, user, PLAN_EVENT, key, request, plan)


def submit_editorial_review(
    db: Session, document: CreativeDocument, request: EditorialReviewRequestV1,
    user: User, key: str,
) -> EditorialReviewV1:
    db.refresh(document, with_for_update=True)
    replay = _replay(_events(db, document), REVIEW_EVENT, key, request)
    if replay:
        return EditorialReviewV1.model_validate(replay)
    state = editorial_readiness(db, document)
    if state.plan is None or state.plan.id != request.plan_id:
        raise ValueError("editorial_plan_conflict")
    if any(code in state.blockers for code in (
        "editorial_plan_stale", "editorial_assets_changed", "editorial_assets_unavailable",
    )):
        raise ValueError("editorial_plan_stale")
    snapshot = record_to_contract(document)
    known_assets = {asset.id: asset for asset in snapshot.assets}
    if not set(request.evidence_asset_ids) <= known_assets.keys():
        raise ValueError("editorial_evidence_not_in_document")
    # Approval is tied to bytes that still exist, not just an old database hash.
    for asset_id in set(request.evidence_asset_ids):
        try:
            with verified_library_asset_path(
                db, workspace_id=document.workspace_id, asset_id=asset_id,
                checksum_sha256=known_assets[asset_id].checksum, max_bytes=100 * 1024 * 1024,
                missing_code="editorial_evidence_missing", changed_code="editorial_evidence_changed",
                too_large_code="editorial_evidence_too_large",
            ):
                pass
        except OSError as error:
            raise ValueError("editorial_evidence_missing") from error
    review = EditorialReviewV1(
        id=str(uuid4()), review=request, reviewed_by=user.id, reviewed_at=datetime.now(UTC),
    )
    return _record(db, document, user, REVIEW_EVENT, key, request, review)


def require_editorial_render_readiness(
    db: Session, document: CreativeDocument, snapshot: CreativeDocumentV1 | None = None,
    *, expected_plan_id: str | None = None,
) -> str | None:
    state = editorial_readiness(db, document)
    if not state.managed:
        return None  # Explicit enrollment; preserve existing non-avatar workflows.
    if not state.full_render_eligible:
        raise ValueError("editorial_full_render_blocked:" + ",".join(state.blockers))
    if snapshot is not None and (
        expected_plan_id != state.plan.id or snapshot.revision != document.revision
        or publication_digest(reviewable_content(snapshot)) != state.plan.document_digest_sha256
    ):
        raise ValueError("editorial_render_snapshot_stale")
    return state.plan.id
