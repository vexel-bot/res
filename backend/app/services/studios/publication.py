"""Approved-snapshot publication preflight and manual handoff.

This module deliberately does not publish to an external network. It binds an
internal schedule and a downloadable package to the exact Studio review that
was approved.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    CreativeDocumentV1,
    StudioInternalScheduleReceiptV1,
    StudioPreflightCheckV1,
    StudioPublicationPreflightV1,
)
from ...models import CreativeDocument, Post, StudioDomainEvent, StudioReviewRequest, User
from .acoustic_analysis import require_current_natural_sound_admission
from .compatibility import record_to_contract
from .editorial_review import editorial_readiness
from .kernel import emit_event
from .review_binding import publication_content, publication_digest, requires_natural_sound_review, reviewable_content
from .review_media import MAX_PACKAGE_BYTES, verified_review_video_path
from .review_preview import render_review_page


def _handoff(snapshot: CreativeDocumentV1) -> dict:
    handoff = snapshot.composition.narrative.get("publicationHandoff")
    if not isinstance(handoff, dict) or handoff.get("schemaVersion") != "studio.publication-handoff.v1":
        raise ValueError("studio_publication_handoff_missing")
    content = {key: handoff.get(key) for key in ("postId", "title", "platform", "format", "caption", "hashtags")}
    if not all(isinstance(content[key], str) for key in ("postId", "title", "platform", "format", "caption")):
        raise ValueError("studio_publication_handoff_invalid")
    if not isinstance(content["hashtags"], list) or not all(isinstance(tag, str) for tag in content["hashtags"]):
        raise ValueError("studio_publication_handoff_invalid")
    if handoff.get("checksumSha256") != publication_digest(content):
        raise ValueError("studio_publication_handoff_invalid")
    return handoff


def _require_audio_admission(
    snapshot: CreativeDocumentV1,
    *,
    db: Session | None = None,
    review: StudioReviewRequest | None = None,
) -> None:
    if requires_natural_sound_review(snapshot):
        if db is None or review is None:
            raise ValueError("studio_publication_natural_sound_evidence_pending")
        require_current_natural_sound_admission(db, review)
        # Admission is immutable, but delivery still re-materializes the private
        # file so deleting or replacing the object cannot reuse an old decision.
        with verified_review_video_path(db, review):
            pass


def _validated_binding(
    db: Session,
    review: StudioReviewRequest,
    *,
    lock: bool = False,
) -> tuple[CreativeDocumentV1, CreativeDocument, Post, dict]:
    if lock:
        db.refresh(review, with_for_update=True)
    if review.status != "approved":
        raise ValueError("studio_publication_review_not_approved")
    record = db.get(CreativeDocument, review.document_id)
    if not record:
        raise ValueError("studio_publication_document_missing")
    if lock:
        db.refresh(record, with_for_update=True)
    current = record_to_contract(record)
    # This rollout admits private rough cuts only. Preproduction reviews must
    # never be mistaken for approval of the final edited artifact.
    if editorial_readiness(db, record).managed:
        raise ValueError("studio_publication_editorial_final_review_pending")
    snapshot = CreativeDocumentV1.model_validate(review.snapshot)
    if (
        current.workspace_id != review.workspace_id
        or current.document_id != review.document_id
        or current.version != review.document_version
        or current.status != "approved"
        or current.review.status != "approved"
        or current.review.approval_id != review.id
        or reviewable_content(current) != reviewable_content(snapshot)
    ):
        raise ValueError("studio_publication_snapshot_stale")
    if not review.post_id:
        raise ValueError("studio_publication_post_missing")
    post = db.get(Post, review.post_id)
    if not post or post.workspace_id != review.workspace_id:
        raise ValueError("studio_publication_post_missing")
    if lock:
        db.refresh(post, with_for_update=True)
    handoff = _handoff(snapshot)
    if handoff["postId"] != post.id or handoff["checksumSha256"] != publication_digest(publication_content(post)):
        raise ValueError("studio_publication_copy_changed")
    if post.status not in {"approved", "scheduled"}:
        raise ValueError("studio_publication_post_not_approved")
    if any(asset.rights_status == "restricted" for asset in snapshot.assets):
        raise ValueError("studio_publication_rights_restricted")
    _require_audio_admission(snapshot, db=db, review=review)
    return snapshot, record, post, handoff


def publication_preflight(db: Session, review: StudioReviewRequest) -> StudioPublicationPreflightV1:
    snapshot, _, post, handoff = _validated_binding(db, review)
    if snapshot.content_type in {"video", "presenter"}:
        with verified_review_video_path(db, review):
            pass
    else:
        for page in snapshot.composition.pages:
            render_review_page(db, review, page.id)
    unknown_rights = sum(asset.rights_status == "unknown" for asset in snapshot.assets)
    checks = [
        StudioPreflightCheckV1(
            key="approval", label="Conteúdo aprovado", status="passed", detail=f"Revisão {review.id} aprovada."
        ),
        StudioPreflightCheckV1(
            key="version",
            label=f"Versão v{review.document_version} selecionada",
            status="passed",
            detail="Documento e revisão continuam vinculados.",
        ),
        StudioPreflightCheckV1(
            key="media", label="Arquivos disponíveis", status="passed", detail="Mídia fixada foi lida e verificada."
        ),
        StudioPreflightCheckV1(
            key="rights",
            label="Direitos dos assets",
            status="warning" if unknown_rights else "passed",
            detail=(
                f"{unknown_rights} asset(s) ainda exigem conferência manual de direitos."
                if unknown_rights
                else "Nenhuma restrição registrada nos assets."
            ),
        ),
        StudioPreflightCheckV1(
            key="schedule",
            label="Data e horário futuros",
            status="passed" if post.scheduled_at else "warning",
            detail=("Agendamento interno salvo." if post.scheduled_at else "Escolha uma data futura antes de agendar."),
        ),
        StudioPreflightCheckV1(
            key="channel",
            label="Conta/canal confirmado",
            status="warning",
            detail="Conector externo indisponível; a saída é um handoff manual.",
        ),
    ]
    return StudioPublicationPreflightV1(
        review_id=review.id,
        document_id=review.document_id,
        document_version=review.document_version,
        post_id=post.id,
        title=handoff["title"],
        platform=handoff["platform"],
        format=handoff["format"],
        caption=handoff["caption"],
        hashtags=handoff["hashtags"],
        content_type=snapshot.content_type,
        page_ids=[page.id for page in snapshot.composition.pages],
        status="scheduled" if post.status == "scheduled" else "ready",
        scheduled_at=post.scheduled_at,
        checks=checks,
    )


def schedule_publication(
    db: Session,
    review: StudioReviewRequest,
    user: User,
    scheduled_at: datetime,
) -> StudioInternalScheduleReceiptV1:
    snapshot, _, post, handoff = _validated_binding(db, review, lock=True)
    normalized = scheduled_at.astimezone(UTC) if scheduled_at.tzinfo else scheduled_at.replace(tzinfo=UTC)
    if normalized <= datetime.now(UTC):
        raise ValueError("studio_publication_schedule_must_be_future")
    iso_schedule = normalized.isoformat()
    existing = db.scalars(
        select(StudioDomainEvent)
        .where(
            StudioDomainEvent.workspace_id == review.workspace_id,
            StudioDomainEvent.aggregate_type == "studio_review",
            StudioDomainEvent.aggregate_id == review.id,
            StudioDomainEvent.event_type == "studio.publication.scheduled_internal",
        )
        .order_by(StudioDomainEvent.occurred_at.desc())
    ).first()
    if existing and existing.payload.get("scheduledAt") == iso_schedule and post.status == "scheduled":
        return StudioInternalScheduleReceiptV1(
            receipt_id=existing.id,
            review_id=review.id,
            document_id=review.document_id,
            document_version=review.document_version,
            post_id=post.id,
            scheduled_at=normalized,
            external_publication_confirmed=False,
        )
    post.status = "scheduled"
    post.scheduled_at = normalized
    event = emit_event(
        db,
        workspace_id=review.workspace_id,
        event_type="studio.publication.scheduled_internal",
        aggregate_type="studio_review",
        aggregate_id=review.id,
        correlation_id=snapshot.correlation_id,
        actor_id=user.id,
        payload={
            "documentId": review.document_id,
            "documentVersion": review.document_version,
            "postId": post.id,
            "scheduledAt": iso_schedule,
            "publicationChecksumSha256": handoff["checksumSha256"],
            "externalPublicationConfirmed": False,
        },
    )
    db.flush()
    receipt = StudioInternalScheduleReceiptV1(
        receipt_id=event.id,
        review_id=review.id,
        document_id=review.document_id,
        document_version=review.document_version,
        post_id=post.id,
        scheduled_at=normalized,
        external_publication_confirmed=False,
    )
    db.commit()
    return receipt


def publication_package(db: Session, review: StudioReviewRequest) -> tuple[bytes, str]:
    snapshot, _, post, handoff = _validated_binding(db, review)
    output = io.BytesIO()
    manifest = {
        "schemaVersion": "studio.publication-package.v1",
        "reviewId": review.id,
        "documentId": review.document_id,
        "documentVersion": review.document_version,
        "postId": post.id,
        "contentType": snapshot.content_type,
        "publicationChecksumSha256": handoff["checksumSha256"],
        "externalPublicationConfirmed": False,
        "files": [],
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        if snapshot.content_type in {"video", "presenter"}:
            with verified_review_video_path(db, review) as (path, extension):
                filename = f"video-aprovado{extension}"
                package.write(path, filename)
                manifest["files"].append(filename)
        else:
            rendered_bytes = 0
            for index, page in enumerate(snapshot.composition.pages, start=1):
                filename = f"slide-{index:02d}.png"
                rendered = render_review_page(db, review, page.id)
                rendered_bytes += len(rendered)
                if rendered_bytes > MAX_PACKAGE_BYTES:
                    raise ValueError("studio_publication_package_too_large")
                package.writestr(filename, rendered)
                manifest["files"].append(filename)
        caption = handoff["caption"]
        if handoff["hashtags"]:
            caption = f"{caption.rstrip()}\n\n{' '.join(handoff['hashtags'])}"
        package.writestr("legenda.txt", caption)
        manifest["files"].append("legenda.txt")
        package.writestr("manifesto.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return output.getvalue(), f"clicko-{post.id}-v{review.document_version}.zip"
