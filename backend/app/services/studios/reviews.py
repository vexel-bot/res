from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    CreativeDocumentV1,
    ReviewReferenceV1,
    StudioListeningReviewRecordV1,
    StudioListeningReviewSubmissionV1,
    StudioReviewRequestV1,
    VideoRenderResultV1,
)
from ...models import (
    ApprovalEvent,
    CreativeDocument,
    FeedbackEvent,
    LibraryAsset,
    Post,
    StudioDomainEvent,
    StudioGenerationJob,
    StudioReviewRequest,
    User,
)
from .acoustic_analysis import (
    acoustic_analysis_out,
    natural_sound_admission_out,
    try_admit_natural_sound_review,
)
from .compatibility import persist_contract, record_to_contract
from .kernel import emit_event
from .review_binding import publication_handoff, requires_natural_sound_review, reviewable_content
from .review_media import verified_review_video_path


def _snapshot_checksum(review: StudioReviewRequest) -> str:
    canonical = json.dumps(review.snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def listening_review_out(db: Session, review: StudioReviewRequest) -> StudioListeningReviewRecordV1 | None:
    event = db.scalars(
        select(StudioDomainEvent)
        .where(
            StudioDomainEvent.workspace_id == review.workspace_id,
            StudioDomainEvent.aggregate_type == "studio_review",
            StudioDomainEvent.aggregate_id == review.id,
            StudioDomainEvent.event_type == "studio.review.listening_recorded",
        )
        .order_by(StudioDomainEvent.occurred_at.desc())
        .limit(1)
    ).first()
    return StudioListeningReviewRecordV1.model_validate(event.payload) if event else None


def review_out(db: Session, review: StudioReviewRequest) -> StudioReviewRequestV1:
    return StudioReviewRequestV1(
        id=review.id,
        workspace_id=review.workspace_id,
        document_id=review.document_id,
        document_version=review.document_version,
        post_id=review.post_id,
        status=review.status,
        snapshot=CreativeDocumentV1.model_validate(review.snapshot),
        render_job_id=review.render_job_id,
        render_asset_id=review.render_asset_id,
        render_checksum_sha256=review.render_checksum_sha256,
        requested_by=review.requested_by,
        decided_by=review.decided_by,
        decision_comment=review.decision_comment,
        requested_at=review.requested_at,
        decided_at=review.decided_at,
        listening_review=listening_review_out(db, review),
        acoustic_analysis=acoustic_analysis_out(db, review),
        natural_sound_admission=natural_sound_admission_out(db, review),
    )


def request_review(
    db: Session,
    record: CreativeDocument,
    user: User,
    *,
    comment: str | None = None,
    render_job_id: str | None = None,
) -> StudioReviewRequest:
    db.refresh(record, with_for_update=True)
    contract = record_to_contract(record)
    existing = db.scalars(
        select(StudioReviewRequest)
        .where(
            StudioReviewRequest.document_id == record.id,
            StudioReviewRequest.document_version == record.version,
            StudioReviewRequest.status == "requested",
        )
        .order_by(StudioReviewRequest.requested_at.desc())
        .limit(1)
    ).first()
    if (
        existing
        and reviewable_content(CreativeDocumentV1.model_validate(existing.snapshot)) == reviewable_content(contract)
        and contract.review.approval_id == existing.id
    ):
        if render_job_id and existing.render_job_id != render_job_id:
            raise ValueError("studio_review_render_conflict")
        return existing

    render_result = None
    if render_job_id:
        render_job = db.scalar(
            select(StudioGenerationJob).where(
                StudioGenerationJob.id == render_job_id,
                StudioGenerationJob.workspace_id == record.workspace_id,
                StudioGenerationJob.document_id == record.id,
            )
        )
        if not render_job or render_job.job_type != "video_render":
            raise ValueError("studio_review_render_not_found")
        if render_job.status != "succeeded" or not render_job.result_payload:
            raise ValueError("studio_review_render_not_ready")
        render_result = VideoRenderResultV1.model_validate(render_job.result_payload)
        if (
            render_result.document_id != record.id
            or render_result.document_revision != record.revision
            or render_result.document_version != record.version
        ):
            raise ValueError("studio_review_render_snapshot_mismatch")
        artifact = db.scalar(
            select(LibraryAsset).where(
                LibraryAsset.id == render_result.artifact.asset_id,
                LibraryAsset.workspace_id == record.workspace_id,
                LibraryAsset.lifecycle_status == "active",
            )
        )
        if (
            not artifact
            or not artifact.storage_key
            or not artifact.checksum_sha256
            or artifact.checksum_sha256.lower() != render_result.artifact.checksum_sha256.lower()
        ):
            raise ValueError("studio_review_render_artifact_mismatch")
        if render_result.quality_evaluation is None or render_result.quality_evaluation.status != "passed":
            raise ValueError("studio_review_render_quality_failed")
    elif contract.content_type in {"video", "presenter"}:
        raise ValueError("studio_review_video_render_required")
    immutable_snapshot = contract.model_copy(deep=True)
    if record.post_id:
        linked_post = db.get(Post, record.post_id)
        if not linked_post or linked_post.workspace_id != record.workspace_id:
            raise ValueError("studio_review_post_missing")
        immutable_snapshot.composition.narrative["publicationHandoff"] = publication_handoff(linked_post)
    review = StudioReviewRequest(
        workspace_id=record.workspace_id,
        document_id=record.id,
        document_version=record.version,
        post_id=record.post_id,
        status="requested",
        snapshot=immutable_snapshot.model_dump(by_alias=True, mode="json"),
        render_job_id=render_job_id,
        render_asset_id=(render_result.artifact.asset_id if render_result else None),
        render_checksum_sha256=(render_result.artifact.checksum_sha256 if render_result else None),
        requested_by=user.id,
        decision_comment=(comment or "").strip() or None,
    )
    db.add(review)
    db.flush()

    updated = contract.model_copy(
        update={
            "status": "in_review",
            "revision": record.revision + 1,
            "review": ReviewReferenceV1(
                status="requested",
                requested_version=record.version,
                approval_id=review.id,
            ),
            "actor_id": user.id,
            "updated_at": datetime.now(UTC),
        }
    )
    persist_contract(record, CreativeDocumentV1.model_validate(updated))
    if record.post_id:
        post = db.get(Post, record.post_id)
        if post and post.status in {"draft", "changes_requested"}:
            previous = post.status
            post.status = "in_review"
            db.add(
                ApprovalEvent(
                    workspace_id=record.workspace_id,
                    post_id=post.id,
                    actor_id=user.id,
                    actor_name=user.name,
                    event_type="action",
                    action="request_review",
                    detail=f"Studio v{record.version} enviada para revisão ({previous} → in_review)",
                )
            )
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.review.requested",
        aggregate_type="studio_review",
        aggregate_id=review.id,
        correlation_id=contract.correlation_id,
        actor_id=user.id,
        payload={
            "documentId": record.id,
            "documentVersion": record.version,
            "postId": record.post_id,
            "renderJobId": render_job_id,
            "renderAssetId": render_result.artifact.asset_id if render_result else None,
            "renderChecksumSha256": (render_result.artifact.checksum_sha256 if render_result else None),
        },
    )
    db.commit()
    db.refresh(review)
    return review


def decide_review(
    db: Session,
    review: StudioReviewRequest,
    user: User,
    *,
    action: str,
    comment: str | None,
    listening_review: StudioListeningReviewSubmissionV1 | None = None,
) -> StudioReviewRequest:
    record = db.get(CreativeDocument, review.document_id)
    if not record:
        raise ValueError("studio_review_document_missing")
    db.refresh(record, with_for_update=True)
    db.refresh(review, with_for_update=True)
    if review.status != "requested":
        raise ValueError("studio_review_already_decided")
    contract = record_to_contract(record)
    snapshot = CreativeDocumentV1.model_validate(review.snapshot)
    if (
        contract.review.approval_id != review.id
        or contract.review.status != "requested"
        or reviewable_content(contract) != reviewable_content(snapshot)
    ):
        raise ValueError("studio_review_snapshot_stale")
    if action == "request_changes" and not (comment or "").strip():
        raise ValueError("studio_review_comment_required")
    natural_sound_review_required = requires_natural_sound_review(snapshot)
    if listening_review and not natural_sound_review_required:
        raise ValueError("studio_review_listening_not_applicable")
    if action == "approve" and natural_sound_review_required:
        if not listening_review:
            raise ValueError("studio_review_listening_required")
        if not listening_review.all_passed():
            raise ValueError("studio_review_listening_failed")
    if listening_review:
        if (
            listening_review.render_asset_id != review.render_asset_id
            or listening_review.render_checksum_sha256.lower() != (review.render_checksum_sha256 or "").lower()
        ):
            raise ValueError("studio_review_listening_render_mismatch")
        # Refuse an attestation if the server cannot still materialize and hash
        # the exact private file shown by the client.
        with verified_review_video_path(db, review):
            pass
    status_map = {
        "approve": "approved",
        "request_changes": "changes_requested",
        "reject": "rejected",
    }
    next_status = status_map[action]
    decided_at = datetime.now(UTC)
    if listening_review:
        result = "pass" if listening_review.all_passed() else "needs_changes"
        listening_event = emit_event(
            db,
            workspace_id=review.workspace_id,
            event_type="studio.review.listening_recorded",
            aggregate_type="studio_review",
            aggregate_id=review.id,
            correlation_id=contract.correlation_id,
            actor_id=user.id,
            payload={},
        )
        db.flush()
        listening_event.payload = StudioListeningReviewRecordV1(
            assessment_id=listening_event.id,
            review_id=review.id,
            document_id=review.document_id,
            document_version=review.document_version,
            snapshot_checksum_sha256=_snapshot_checksum(review),
            reviewer_id=user.id,
            reviewed_at=decided_at,
            result=result,
            submission=listening_review,
        ).model_dump(by_alias=True, mode="json")
    review.status = next_status
    review.decided_by = user.id
    review.decision_comment = (comment or "").strip() or None
    review.decided_at = decided_at

    document_status = "approved" if action == "approve" else "draft"
    updated = contract.model_copy(
        update={
            "status": document_status,
            "revision": record.revision + 1,
            "review": ReviewReferenceV1(
                status=next_status,
                requested_version=review.document_version,
                approval_id=review.id,
            ),
            "actor_id": user.id,
            "updated_at": decided_at,
        }
    )
    persist_contract(record, CreativeDocumentV1.model_validate(updated))

    post = db.get(Post, review.post_id) if review.post_id else None
    if post:
        previous = post.status
        post.status = next_status
        detail = review.decision_comment or f"Studio v{review.document_version}: {action}"
        db.add(
            ApprovalEvent(
                workspace_id=review.workspace_id,
                post_id=post.id,
                actor_id=user.id,
                actor_name=user.name,
                event_type="action",
                action=action,
                detail=detail,
            )
        )
        db.add(
            FeedbackEvent(
                workspace_id=review.workspace_id,
                campaign_id=record.campaign_id,
                content_id=post.id,
                creative_document_id=record.id,
                user_id=user.id,
                event_type={"approve": "approved", "reject": "discarded"}.get(action, "status_changed"),
                reason=review.decision_comment,
                payload={
                    "action": action,
                    "from": previous,
                    "to": next_status,
                    "studioReviewId": review.id,
                    "documentVersion": review.document_version,
                },
            )
        )
    emit_event(
        db,
        workspace_id=review.workspace_id,
        event_type=f"studio.review.{next_status}",
        aggregate_type="studio_review",
        aggregate_id=review.id,
        correlation_id=contract.correlation_id,
        actor_id=user.id,
        payload={"documentId": review.document_id, "documentVersion": review.document_version},
    )
    db.flush()
    if action == "approve" and natural_sound_review_required:
        try_admit_natural_sound_review(db, review)
    db.commit()
    db.refresh(review)
    return review
