"""Server-owned rights decisions for governed audio assets.

Declarations in CreativeDocument remain user input. Only an immutable event
created here can project `rightsStatus=verified` or `restricted` back into a
audio reference used as natural sound or licensed music.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    AssetReferenceV1,
    CreativeDocumentV1,
    ReviewReferenceV1,
    StudioAssetRightsReviewRecordV1,
    StudioAssetRightsReviewRequestV1,
)
from ...models import CreativeDocument, StudioDomainEvent, User
from .compatibility import persist_contract, record_to_contract
from .review_binding import invalidate_linked_post_review
from .review_media import verified_library_asset_path

NATURAL_SOUND_PURPOSE = "natural-sound-candidate"
LICENSED_MUSIC_PURPOSE = "licensed-music-candidate"
GOVERNED_AUDIO_PURPOSES = frozenset({NATURAL_SOUND_PURPOSE, LICENSED_MUSIC_PURPOSE})
MAX_RIGHTS_ASSET_BYTES = 20 * 1024 * 1024
RIGHTS_PROVENANCE_KEYS = {
    "rightsReviewId",
    "rightsReviewedAt",
    "rightsReviewerId",
    "rightsExpiresAt",
    "rightsPublicationScope",
    "rightsStatusReason",
}


def _payload_hash(document_id: str, asset_id: str, request: StudioAssetRightsReviewRequestV1) -> str:
    payload = {
        "documentId": document_id,
        "assetId": asset_id,
        "request": request.model_dump(by_alias=True, mode="json"),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _rights_events(db: Session, workspace_id: str, asset_id: str) -> list[StudioDomainEvent]:
    return list(
        db.scalars(
            select(StudioDomainEvent)
            .where(
                StudioDomainEvent.workspace_id == workspace_id,
                StudioDomainEvent.aggregate_type == "studio_asset",
                StudioDomainEvent.aggregate_id == asset_id,
                StudioDomainEvent.event_type == "studio.asset.rights_reviewed",
            )
            .order_by(StudioDomainEvent.occurred_at.desc(), StudioDomainEvent.id.desc())
        ).all()
    )


def _record_from_event(event: StudioDomainEvent) -> StudioAssetRightsReviewRecordV1 | None:
    raw = (event.payload or {}).get("record")
    try:
        return StudioAssetRightsReviewRecordV1.model_validate(raw) if raw else None
    except ValueError:
        return None


def _project_reference(
    reference: AssetReferenceV1,
    rights_record: StudioAssetRightsReviewRecordV1 | None,
    *,
    now: datetime,
) -> AssetReferenceV1:
    provenance = dict(reference.provenance)
    for key in RIGHTS_PROVENANCE_KEYS:
        provenance.pop(key, None)
    status = "unknown"
    reason = "rights_review_missing"
    if rights_record and reference.checksum and (
        rights_record.asset_checksum_sha256.lower() == reference.checksum.lower()
    ):
        source = str(provenance.get("sourceDeclaration") or "")
        license_declaration = str(provenance.get("licenseDeclaration") or "")
        expires_at = rights_record.expires_at
        expired = bool(expires_at and expires_at <= now)
        declarations_match = (
            source == rights_record.source_declaration
            and license_declaration == rights_record.license_declaration
        )
        if rights_record.decision == "restricted":
            status = "restricted"
            reason = "rights_review_restricted"
        elif expired:
            reason = "rights_review_expired"
        elif declarations_match:
            status = "verified"
            reason = "rights_review_verified"
        else:
            reason = "rights_declarations_changed"
        provenance.update({
            "rightsReviewId": rights_record.review_id,
            "rightsReviewedAt": rights_record.reviewed_at.isoformat(),
            "rightsReviewerId": rights_record.reviewer_id,
            "rightsExpiresAt": rights_record.expires_at.isoformat() if rights_record.expires_at else None,
            "rightsPublicationScope": rights_record.publication_scope,
        })
    provenance["rightsStatusReason"] = reason
    return reference.model_copy(update={"rights_status": status, "provenance": provenance})


def project_governed_audio_rights(db: Session, document: CreativeDocumentV1) -> CreativeDocumentV1:
    now = datetime.now(UTC)
    projected: list[AssetReferenceV1] = []
    for reference in document.assets:
        if reference.provenance.get("purpose") not in GOVERNED_AUDIO_PURPOSES:
            projected.append(reference)
            continue
        latest = next(
            (
                record
                for event in _rights_events(db, document.workspace_id, reference.id)
                if (record := _record_from_event(event)) is not None
            ),
            None,
        )
        projected.append(_project_reference(reference, latest, now=now))
    return document.model_copy(update={"assets": projected})


def project_natural_sound_rights(db: Session, document: CreativeDocumentV1) -> CreativeDocumentV1:
    """Compatibility alias while callers migrate to the governed-audio name."""

    return project_governed_audio_rights(db, document)


def review_natural_sound_rights(
    db: Session,
    document: CreativeDocument,
    asset_id: str,
    request: StudioAssetRightsReviewRequestV1,
    user: User,
    *,
    idempotency_key: str,
) -> tuple[StudioAssetRightsReviewRecordV1, CreativeDocument]:
    db.refresh(document, with_for_update=True)
    current = record_to_contract(document)
    target = next(
        (
            reference
            for reference in current.assets
            if reference.id == asset_id
            and reference.provenance.get("purpose") in GOVERNED_AUDIO_PURPOSES
        ),
        None,
    )
    if target is None:
        raise ValueError("studio_asset_rights_natural_sound_required")
    payload_hash = _payload_hash(document.id, asset_id, request)
    for event in _rights_events(db, document.workspace_id, asset_id):
        if (event.payload or {}).get("idempotencyKey") != idempotency_key:
            continue
        if (event.payload or {}).get("payloadHash") != payload_hash:
            raise ValueError("studio_asset_rights_idempotency_conflict")
        existing = _record_from_event(event)
        if existing is None:
            raise ValueError("studio_asset_rights_record_invalid")
        return existing, document
    if request.expected_document_revision != document.revision:
        raise ValueError("studio_asset_rights_document_conflict")
    if not target.checksum or target.checksum.lower() != request.asset_checksum_sha256.lower():
        raise ValueError("studio_asset_rights_checksum_mismatch")
    if request.expires_at:
        if request.expires_at.tzinfo is None or request.expires_at <= datetime.now(UTC):
            raise ValueError("studio_asset_rights_expiration_invalid")
    source_declaration = str(target.provenance.get("sourceDeclaration") or "").strip()
    license_declaration = str(target.provenance.get("licenseDeclaration") or "").strip()
    if not source_declaration or not license_declaration:
        raise ValueError("studio_asset_rights_declarations_required")
    with verified_library_asset_path(
        db,
        workspace_id=document.workspace_id,
        asset_id=asset_id,
        checksum_sha256=request.asset_checksum_sha256,
        max_bytes=MAX_RIGHTS_ASSET_BYTES,
        missing_code="studio_asset_rights_asset_not_found",
        changed_code="studio_asset_rights_checksum_mismatch",
        too_large_code="studio_asset_rights_asset_too_large",
    ):
        pass

    reviewed_at = datetime.now(UTC)
    event = StudioDomainEvent(
        workspace_id=document.workspace_id,
        event_type="studio.asset.rights_reviewed",
        aggregate_type="studio_asset",
        aggregate_id=asset_id,
        correlation_id=current.correlation_id,
        actor_id=user.id,
        payload={},
    )
    db.add(event)
    db.flush()
    rights_record = StudioAssetRightsReviewRecordV1(
        review_id=event.id,
        workspace_id=document.workspace_id,
        document_id=document.id,
        document_revision=document.revision + 1,
        asset_id=asset_id,
        asset_checksum_sha256=request.asset_checksum_sha256.lower(),
        decision=request.decision,
        basis=request.basis,
        source_declaration=source_declaration,
        license_declaration=license_declaration,
        source_reference=request.source_reference.strip(),
        rights_reference=request.rights_reference.strip(),
        expires_at=request.expires_at,
        no_expiration_confirmed=request.no_expiration_confirmed,
        notes=(request.notes or "").strip() or None,
        reviewer_id=user.id,
        reviewed_at=reviewed_at,
    )
    event.payload = {
        "idempotencyKey": idempotency_key,
        "payloadHash": payload_hash,
        "record": rights_record.model_dump(by_alias=True, mode="json"),
    }
    updated_assets = [
        _project_reference(reference, rights_record, now=reviewed_at)
        if reference.id == asset_id
        and reference.provenance.get("purpose") in GOVERNED_AUDIO_PURPOSES
        else reference
        for reference in current.assets
    ]
    updated = current.model_copy(update={
        "assets": updated_assets,
        "revision": document.revision + 1,
        "status": "draft",
        "review": ReviewReferenceV1(),
        "actor_id": user.id,
        "updated_at": reviewed_at,
    })
    invalidate_linked_post_review(db, document)
    persist_contract(document, CreativeDocumentV1.model_validate(updated))
    db.add(StudioDomainEvent(
        workspace_id=document.workspace_id,
        event_type="studio.document.rights_changed",
        aggregate_type="creative_document",
        aggregate_id=document.id,
        correlation_id=current.correlation_id,
        actor_id=user.id,
        payload={
            "revision": updated.revision,
            "assetId": asset_id,
            "assetRightsReviewId": rights_record.review_id,
            "decision": rights_record.decision,
        },
    ))
    db.commit()
    db.refresh(document)
    return rights_record, document
