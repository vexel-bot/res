from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    CreateStudioDocumentRequest,
    CreativeDocumentV1,
    ReplaceStudioDocumentRequest,
    RestoreStudioDocumentVersionRequest,
    ReviewReferenceV1,
    StudioDocumentVersionV1,
)
from ...models import BrandProfile, CreativeDocument, ExternalSignal, Opportunity, StudioDomainEvent, User
from ...services.brand import brand_readiness
from .asset_rights import project_natural_sound_rights
from .compatibility import composition_to_canvas, persist_contract, record_to_contract
from .review_binding import invalidate_linked_post_review, reviewable_content


def emit_event(
    db: Session,
    *,
    workspace_id: str,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    correlation_id: str,
    actor_id: str | None,
    payload: dict | None = None,
) -> StudioDomainEvent:
    event = StudioDomainEvent(
        workspace_id=workspace_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        payload=payload or {},
    )
    db.add(event)
    return event


def create_document(db: Session, request: CreateStudioDocumentRequest, user: User) -> CreativeDocument:
    creation_key = (
        f"studio:{request.workspace_id}:post:{request.post_id}:{request.content_type}" if request.post_id else None
    )
    if creation_key:
        existing = db.scalar(select(CreativeDocument).where(CreativeDocument.studio_creation_key == creation_key))
        if existing:
            return existing
    document_id = str(uuid4())
    now = datetime.now(UTC)
    correlation_id = request.correlation_id or str(uuid4())
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == request.workspace_id))
    if not brand or brand_readiness(brand)["revision"] != request.brand_revision:
        raise ValueError("studio_brand_revision_mismatch")
    opportunity_ref = None
    if request.opportunity_id:
        opportunity = db.get(Opportunity, request.opportunity_id)
        signal = db.get(ExternalSignal, opportunity.signal_id) if opportunity else None
        evidence = opportunity.evidence or [] if opportunity else []
        first_evidence = evidence[0] if evidence else {}
        opportunity_ref = {
            "id": request.opportunity_id,
            "version": opportunity.score_version if opportunity else None,
            "sourceUrl": first_evidence.get("url") or (signal.url if signal else None),
            "observedAt": signal.collected_at if signal else None,
            "confidence": None,
        }
    contract = CreativeDocumentV1(
        document_id=document_id,
        workspace_id=request.workspace_id,
        title=request.title.strip(),
        content_type=request.content_type,
        actor_id=user.id,
        correlation_id=correlation_id,
        campaign_ref={"id": request.campaign_id} if request.campaign_id else None,
        post_ref={"id": request.post_id} if request.post_id else None,
        opportunity_ref=opportunity_ref,
        brand_memory_ref={"id": brand.id, "revision": request.brand_revision},
        brief=request.brief,
        composition=request.composition,
        assets=request.assets,
        created_at=now,
        updated_at=now,
    )
    contract = project_natural_sound_rights(db, contract)
    record = CreativeDocument(
        id=document_id,
        workspace_id=request.workspace_id,
        campaign_id=request.campaign_id,
        post_id=request.post_id,
        kind="document",
        title=contract.title,
        document=composition_to_canvas(contract).model_dump(by_alias=True),
        schema_version=contract.schema_version,
        canonical_document=contract.model_dump(by_alias=True, mode="json"),
        revision=1,
        correlation_id=correlation_id,
        created_by=user.id,
        studio_creation_key=creation_key,
        version=1,
        versions=[],
    )
    db.add(record)
    emit_event(
        db,
        workspace_id=request.workspace_id,
        event_type="studio.document.created",
        aggregate_type="creative_document",
        aggregate_id=document_id,
        correlation_id=correlation_id,
        actor_id=user.id,
        payload={"schemaVersion": contract.schema_version, "contentType": contract.content_type},
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if not creation_key:
            raise
        existing = db.scalar(select(CreativeDocument).where(CreativeDocument.studio_creation_key == creation_key))
        if not existing:
            raise
        return existing
    db.refresh(record)
    return record


def replace_document(
    db: Session, record: CreativeDocument, request: ReplaceStudioDocumentRequest, user: User
) -> CreativeDocument:
    db.refresh(record, with_for_update=True)
    if request.expected_revision != record.revision:
        raise ValueError("studio_document_conflict")
    incoming = project_natural_sound_rights(db, request.document)
    if incoming.document_id != record.id or incoming.workspace_id != record.workspace_id:
        raise ValueError("studio_document_identity_mismatch")
    next_contract = incoming.model_copy(
        update={
            "revision": record.revision + 1,
            "version": record.version,
            "actor_id": user.id,
            "created_at": record.created_at,
            "updated_at": datetime.now(UTC),
        }
    )
    current = record_to_contract(record)
    changed = reviewable_content(next_contract) != reviewable_content(current)
    # Review state is server-owned; editing cannot mint or carry approval onto changed content.
    next_contract = next_contract.model_copy(
        update={
            "status": "draft" if changed else current.status,
            "review": ReviewReferenceV1() if changed else current.review,
        }
    )
    if changed:
        invalidate_linked_post_review(db, record)
    record.title = next_contract.title
    record.campaign_id = next_contract.campaign_ref.id if next_contract.campaign_ref else None
    record.post_id = next_contract.post_ref.id if next_contract.post_ref else None
    persist_contract(record, next_contract)
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.document.updated",
        aggregate_type="creative_document",
        aggregate_id=record.id,
        correlation_id=next_contract.correlation_id,
        actor_id=user.id,
        payload={"revision": next_contract.revision},
    )
    db.commit()
    db.refresh(record)
    return record


def save_version(db: Session, record: CreativeDocument, label: str, user: User) -> CreativeDocument:
    db.refresh(record, with_for_update=True)
    contract = record_to_contract(record)
    next_version = record.version + 1
    now = datetime.now(UTC)
    updated = contract.model_copy(
        update={"version": next_version, "updated_at": now, "status": "draft", "review": ReviewReferenceV1()}
    )
    invalidate_linked_post_review(db, record)
    snapshots = list(record.versions or [])
    snapshots.append(
        {
            "number": next_version,
            "label": label,
            "createdAt": now.isoformat(),
            "actorId": user.id,
            "document": record.document,
            "canonicalDocument": updated.model_dump(by_alias=True, mode="json"),
        }
    )
    record.version = next_version
    record.versions = snapshots[-20:]
    persist_contract(record, updated)
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.document.versioned",
        aggregate_type="creative_document",
        aggregate_id=record.id,
        correlation_id=updated.correlation_id,
        actor_id=user.id,
        payload={"version": next_version, "label": label},
    )
    db.commit()
    db.refresh(record)
    return record


def version_history(record: CreativeDocument) -> list[StudioDocumentVersionV1]:
    history: list[StudioDocumentVersionV1] = []
    for raw in record.versions or []:
        canonical = raw.get("canonicalDocument")
        if not canonical:
            continue
        number = int(raw["number"])
        snapshot = CreativeDocumentV1.model_validate(canonical).model_copy(
            update={
                "document_id": record.id,
                "workspace_id": record.workspace_id,
                "version": number,
            }
        )
        history.append(
            StudioDocumentVersionV1(
                document_id=record.id,
                workspace_id=record.workspace_id,
                number=number,
                label=raw.get("label") or f"Versão {number}",
                created_at=raw["createdAt"],
                actor_id=raw.get("actorId"),
                snapshot=snapshot,
            )
        )
    return sorted(history, key=lambda item: item.number, reverse=True)


def restore_document_version(
    db: Session,
    record: CreativeDocument,
    version_number: int,
    request: RestoreStudioDocumentVersionRequest,
    user: User,
) -> CreativeDocument:
    db.refresh(record, with_for_update=True)
    if request.expected_revision != record.revision:
        raise ValueError("studio_document_conflict")
    target = next((item for item in version_history(record) if item.number == version_number), None)
    if not target:
        raise ValueError("studio_document_version_not_found")

    now = datetime.now(UTC)
    current = record_to_contract(record)
    backup_number = record.version + 1
    restored_number = backup_number + 1
    backup = current.model_copy(update={"version": backup_number, "updated_at": now})
    restored = target.snapshot.model_copy(
        update={
            "document_id": record.id,
            "workspace_id": record.workspace_id,
            "revision": record.revision + 1,
            "version": restored_number,
            "actor_id": user.id,
            "correlation_id": current.correlation_id,
            "created_at": current.created_at,
            "updated_at": now,
            "status": "draft",
            "review": ReviewReferenceV1(),
        }
    )
    restored = project_natural_sound_rights(db, restored)
    invalidate_linked_post_review(db, record)
    snapshots = list(record.versions or [])
    snapshots.extend(
        [
            {
                "number": backup_number,
                "label": f"Backup antes de restaurar v{version_number}",
                "createdAt": now.isoformat(),
                "actorId": user.id,
                "document": record.document,
                "canonicalDocument": backup.model_dump(by_alias=True, mode="json"),
            },
            {
                "number": restored_number,
                "label": (request.label or f"Restaurada da v{version_number}").strip(),
                "createdAt": now.isoformat(),
                "actorId": user.id,
                "document": record.document,
                "canonicalDocument": restored.model_dump(by_alias=True, mode="json"),
            },
        ]
    )
    record.title = restored.title
    record.campaign_id = restored.campaign_ref.id if restored.campaign_ref else None
    record.post_id = restored.post_ref.id if restored.post_ref else None
    record.version = restored_number
    record.versions = snapshots[-20:]
    persist_contract(record, restored)
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.document.restored",
        aggregate_type="creative_document",
        aggregate_id=record.id,
        correlation_id=restored.correlation_id,
        actor_id=user.id,
        payload={
            "sourceVersion": version_number,
            "backupVersion": backup_number,
            "restoredVersion": restored_number,
            "revision": restored.revision,
        },
    )
    db.commit()
    db.refresh(record)
    return record
