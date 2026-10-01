import tempfile
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Campaign, CreativeDocument, FeedbackEvent, LibraryAsset, Membership, Post, User, utcnow
from ..schemas import (
    AssetOut,
    CreativeDocumentIn,
    CreativeDocumentOut,
    CreativeDocumentUpdate,
    CreativeExportIn,
    CreativeVersionIn,
)
from ..security import get_current_user
from ..services.creatives import render_creative
from ..services.object_storage import get_object_storage, object_key
from .assets import asset_out

router = APIRouter(prefix="/creatives", tags=["creatives"])
settings = get_settings()


def normalized_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Workspace not found")


def assert_links(db: Session, workspace_id: str, campaign_id: str | None, post_id: str | None) -> None:
    if campaign_id and not db.scalar(
        select(Campaign.id).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=422, detail="Campaign does not belong to workspace")
    if post_id and not db.scalar(select(Post.id).where(Post.id == post_id, Post.workspace_id == workspace_id)):
        raise HTTPException(status_code=422, detail="Post does not belong to workspace")


def creative_out(item: CreativeDocument) -> CreativeDocumentOut:
    return CreativeDocumentOut(
        id=item.id,
        workspace_id=item.workspace_id,
        campaign_id=item.campaign_id,
        post_id=item.post_id,
        kind=item.kind,
        title=item.title,
        document=item.document,
        version=item.version,
        versions=item.versions or [],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def owned_document(db: Session, user_id: str, document_id: str) -> CreativeDocument:
    item = db.get(CreativeDocument, document_id)
    if not item:
        raise HTTPException(status_code=404, detail="Creative not found")
    assert_access(db, user_id, item.workspace_id)
    return item


@router.get("", response_model=list[CreativeDocumentOut])
def list_creatives(
    workspace_id: str = Query(...),
    kind: str | None = Query(default=None, pattern="^(document|template)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assert_access(db, user.id, workspace_id)
    query = select(CreativeDocument).where(CreativeDocument.workspace_id == workspace_id)
    if kind:
        query = query.where(CreativeDocument.kind == kind)
    items = db.scalars(query.order_by(CreativeDocument.updated_at.desc())).all()
    return [creative_out(item) for item in items]


@router.get("/{document_id}", response_model=CreativeDocumentOut)
def get_creative(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return creative_out(owned_document(db, user.id, document_id))


@router.post("", response_model=CreativeDocumentOut, status_code=status.HTTP_201_CREATED)
def create_creative(data: CreativeDocumentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assert_access(db, user.id, data.workspace_id)
    assert_links(db, data.workspace_id, data.campaign_id, data.post_id)
    item = CreativeDocument(
        workspace_id=data.workspace_id,
        campaign_id=data.campaign_id,
        post_id=data.post_id,
        kind=data.kind,
        title=data.title.strip(),
        document=data.document.model_dump(by_alias=True),
        version=1,
        versions=[],
    )
    db.add(item)
    db.flush()
    db.add(
        FeedbackEvent(
            workspace_id=item.workspace_id,
            campaign_id=item.campaign_id,
            content_id=item.post_id,
            creative_document_id=item.id,
            user_id=user.id,
            event_type="generated",
            payload={"kind": item.kind},
        )
    )
    db.commit()
    db.refresh(item)
    return creative_out(item)


@router.patch("/{document_id}", response_model=CreativeDocumentOut)
def update_creative(
    document_id: str,
    data: CreativeDocumentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = owned_document(db, user.id, document_id)
    changes = data.model_dump(exclude_unset=True)
    if data.document is not None and (
        (item.canonical_document or {}).get("composition", {}).get("narrative", {}).get("editorialV2")
    ):
        raise HTTPException(status_code=409, detail={"code": "editorial_v2_requires_video_studio"})
    expected_updated_at = changes.pop("expected_updated_at", None)
    if expected_updated_at is not None and normalized_timestamp(
        item.updated_at
    ) != normalized_timestamp(expected_updated_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "creative_version_conflict",
                "message": "Este documento foi alterado em outra sessão. Recarregue antes de salvar novamente.",
                "currentUpdatedAt": normalized_timestamp(item.updated_at).isoformat(),
            },
        )
    assert_links(
        db, item.workspace_id, changes.get("campaign_id", item.campaign_id), changes.get("post_id", item.post_id)
    )
    if "title" in changes:
        item.title = changes["title"].strip()
    if "campaign_id" in changes:
        item.campaign_id = changes["campaign_id"]
    if "post_id" in changes:
        item.post_id = changes["post_id"]
    if "kind" in changes:
        item.kind = changes["kind"]
    if data.document is not None:
        item.document = data.document.model_dump(by_alias=True)
    if changes:
        db.add(
            FeedbackEvent(
                workspace_id=item.workspace_id,
                campaign_id=item.campaign_id,
                content_id=item.post_id,
                creative_document_id=item.id,
                user_id=user.id,
                event_type="edited",
                payload={"changedFields": sorted(changes), "editIntensity": 1.0},
            )
        )
    db.commit()
    db.refresh(item)
    return creative_out(item)


@router.post("/{document_id}/versions", response_model=CreativeDocumentOut)
def save_version(
    document_id: str, data: CreativeVersionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    item = owned_document(db, user.id, document_id)
    next_version = item.version + 1
    snapshots = list(item.versions or [])
    snapshots.append(
        {"number": next_version, "label": data.label, "createdAt": utcnow().isoformat(), "document": item.document}
    )
    item.version = next_version
    item.versions = snapshots[-20:]
    db.commit()
    db.refresh(item)
    return creative_out(item)


@router.post("/{document_id}/versions/{version_number}/restore", response_model=CreativeDocumentOut)
def restore_version(
    document_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = owned_document(db, user.id, document_id)
    snapshot = next((value for value in item.versions or [] if value.get("number") == version_number), None)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Creative version not found")
    snapshots = list(item.versions or [])
    next_version = item.version + 1
    item.document = snapshot["document"]
    snapshots.append(
        {
            "number": next_version,
            "label": f"Restaurada da versão {version_number}",
            "createdAt": utcnow().isoformat(),
            "document": item.document,
        }
    )
    item.version = next_version
    item.versions = snapshots[-20:]
    db.commit()
    db.refresh(item)
    return creative_out(item)


@router.post("/{document_id}/export", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def export_creative(
    document_id: str, data: CreativeExportIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    item = owned_document(db, user.id, document_id)
    image_ids = {layer.asset_id for layer in data_canvas(item).layers if layer.type == "image"}
    assets = (
        db.scalars(
            select(LibraryAsset).where(
                LibraryAsset.id.in_(image_ids),
                LibraryAsset.workspace_id == item.workspace_id,
                LibraryAsset.lifecycle_status == "active",
            )
        ).all()
        if image_ids
        else []
    )
    if len(assets) != len(image_ids) or any(not asset.storage_key for asset in assets):
        raise HTTPException(status_code=422, detail="One or more image layers are unavailable")
    try:
        with ExitStack() as stack:
            paths = {
                asset.id: stack.enter_context(
                    get_object_storage(asset.storage_backend or "local").materialize(str(asset.storage_key))
                )
                for asset in assets
            }
            rendered = render_creative(data_canvas(item), paths)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    extension = ".png" if data.format == "png" else ".jpg"
    media_type = "image/png" if data.format == "png" else "image/jpeg"
    storage_key = object_key(item.workspace_id, "exports", extension)
    storage = get_object_storage()
    with tempfile.TemporaryDirectory(prefix="clicko-creative-export-") as temporary_directory:
        destination = Path(temporary_directory) / f"export{extension}"
        if data.format == "png":
            rendered.save(destination, format="PNG", optimize=True)
        else:
            rendered.convert("RGB").save(destination, format="JPEG", quality=data.quality, optimize=True)
        stored = storage.put_file(
            destination,
            key=storage_key,
            media_type=media_type,
            metadata={
                "workspace-id": item.workspace_id,
                "document-id": item.id,
                "document-version": str(item.version),
                "source": "legacy-creative-export",
            },
        )
    try:
        asset = LibraryAsset(
            workspace_id=item.workspace_id,
            title=f"{item.title} v{item.version}",
            asset_type="image",
            tags=["export", data.format, f"creative:{item.id}", f"version:{item.version}"],
            campaign_id=item.campaign_id,
            content_id=item.post_id,
            storage_key=storage_key,
            storage_backend=stored.backend,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            object_metadata=stored.metadata,
        )
        db.add(asset)
        db.flush()
        db.add(
            FeedbackEvent(
                workspace_id=item.workspace_id,
                campaign_id=item.campaign_id,
                content_id=item.post_id,
                creative_document_id=item.id,
                user_id=user.id,
                event_type="generated",
                payload={"exportAssetId": asset.id, "format": data.format, "version": item.version},
            )
        )
        db.commit()
        db.refresh(asset)
    except Exception:
        db.rollback()
        storage.delete(storage_key)
        raise
    return asset_out(asset)


def data_canvas(item: CreativeDocument):
    from ..schemas import CreativeCanvas

    return CreativeCanvas.model_validate(item.document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_creative(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    item = owned_document(db, user.id, document_id)
    db.add(
        FeedbackEvent(
            workspace_id=item.workspace_id,
            campaign_id=item.campaign_id,
            content_id=item.post_id,
            user_id=user.id,
            event_type="discarded",
            payload={"creativeDocumentId": item.id, "title": item.title},
        )
    )
    db.delete(item)
    db.commit()
