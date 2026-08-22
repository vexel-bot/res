from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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
            select(LibraryAsset).where(LibraryAsset.id.in_(image_ids), LibraryAsset.workspace_id == item.workspace_id)
        ).all()
        if image_ids
        else []
    )
    if len(assets) != len(image_ids) or any(not asset.storage_key for asset in assets):
        raise HTTPException(status_code=422, detail="One or more image layers are unavailable")
    storage_root = Path(settings.storage_path).resolve()
    paths = {asset.id: storage_root / str(asset.storage_key) for asset in assets}
    try:
        rendered = render_creative(data_canvas(item), paths)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    extension = ".png" if data.format == "png" else ".jpg"
    storage_key = f"{uuid4().hex}{extension}"
    storage_root.mkdir(parents=True, exist_ok=True)
    destination = storage_root / storage_key
    try:
        if data.format == "png":
            rendered.save(destination, format="PNG", optimize=True)
        else:
            rendered.convert("RGB").save(destination, format="JPEG", quality=data.quality, optimize=True)
        asset = LibraryAsset(
            workspace_id=item.workspace_id,
            title=f"{item.title} v{item.version}",
            asset_type="image",
            tags=["export", data.format, f"creative:{item.id}", f"version:{item.version}"],
            campaign_id=item.campaign_id,
            content_id=item.post_id,
            storage_key=storage_key,
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
        destination.unlink(missing_ok=True)
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
