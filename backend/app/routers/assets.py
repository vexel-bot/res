import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Campaign, LibraryAsset, Membership, Post, User
from ..schemas import AssetIn, AssetOut
from ..security import get_current_user

router = APIRouter(prefix="/assets", tags=["assets"])
settings = get_settings()
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_UPLOAD_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "text/plain": ".txt",
    "video/mp4": ".mp4",
}
IMAGE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
MAX_IMAGE_PIXELS = 50_000_000


def validate_uploaded_content(path: Path, content_type: str) -> None:
    try:
        if content_type in IMAGE_FORMATS:
            with Image.open(path) as image:
                if image.format != IMAGE_FORMATS[content_type]:
                    raise ValueError("Image format does not match declared type")
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Image dimensions are too large")
                image.verify()
            return
        if content_type == "application/pdf":
            if not path.read_bytes()[:5] == b"%PDF-":
                raise ValueError("Invalid PDF signature")
            return
        if content_type == "video/mp4":
            header = path.read_bytes()[:32]
            if len(header) < 12 or header[4:8] != b"ftyp":
                raise ValueError("Invalid MP4 signature")
            return
        if content_type == "text/plain":
            path.read_text(encoding="utf-8-sig")
            return
        raise ValueError("Unsupported file type")
    except (OSError, UnicodeDecodeError, UnidentifiedImageError, ValueError) as error:
        raise HTTPException(status_code=422, detail="File content does not match its declared type") from error


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Workspace not found")


def asset_out(item: LibraryAsset) -> AssetOut:
    url = f"/api/v1/assets/{item.id}/content" if item.storage_key else item.url
    return AssetOut(
        id=item.id,
        workspace_id=item.workspace_id,
        title=item.title,
        type=item.asset_type,
        tags=item.tags or [],
        campaign_id=item.campaign_id,
        content_id=item.content_id,
        url=url,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=list[AssetOut])
def list_assets(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AssetOut]:
    assert_access(db, user.id, workspace_id)
    items = db.scalars(
        select(LibraryAsset).where(LibraryAsset.workspace_id == workspace_id).order_by(LibraryAsset.created_at.desc())
    ).all()
    return [asset_out(item) for item in items]


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    data: AssetIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetOut:
    assert_access(db, user.id, data.workspace_id)
    if data.campaign_id and not db.scalar(
        select(Campaign.id).where(Campaign.id == data.campaign_id, Campaign.workspace_id == data.workspace_id)
    ):
        raise HTTPException(status_code=422, detail="Campaign does not belong to workspace")
    if data.content_id and not db.scalar(
        select(Post.id).where(Post.id == data.content_id, Post.workspace_id == data.workspace_id)
    ):
        raise HTTPException(status_code=422, detail="Content does not belong to workspace")
    item = LibraryAsset(
        workspace_id=data.workspace_id,
        title=data.title.strip(),
        asset_type=data.type,
        tags=data.tags,
        campaign_id=data.campaign_id,
        content_id=data.content_id,
        url=data.url,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return asset_out(item)


@router.post("/upload", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    workspace_id: str = Form(...),
    title: str = Form(..., min_length=1, max_length=240),
    tags: str = Form(default=""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetOut:
    assert_access(db, user.id, workspace_id)
    extension = ALLOWED_UPLOAD_TYPES.get(file.content_type or "")
    if not extension:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    storage_root = Path(settings.storage_path).resolve()
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid4().hex}{extension}"
    destination = storage_root / storage_key
    size = 0
    try:
        with destination.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    try:
        validate_uploaded_content(destination, file.content_type or "")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    item = LibraryAsset(
        workspace_id=workspace_id,
        title=title.strip(),
        asset_type="image" if (file.content_type or "").startswith("image/") else "upload",
        tags=[value.strip() for value in tags.split(",") if value.strip()],
        storage_key=storage_key,
    )
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return asset_out(item)


@router.get("/{asset_id}/content", response_class=FileResponse)
def download_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    item = db.get(LibraryAsset, asset_id)
    if not item or not item.storage_key:
        raise HTTPException(status_code=404, detail="Asset not found")
    assert_access(db, user.id, item.workspace_id)
    path = Path(settings.storage_path).resolve() / item.storage_key
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=f"{item.title}{path.suffix}")


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    item = db.get(LibraryAsset, asset_id)
    if not item:
        raise HTTPException(status_code=404, detail="Asset not found")
    assert_access(db, user.id, item.workspace_id)
    if item.storage_key:
        (Path(settings.storage_path).resolve() / item.storage_key).unlink(missing_ok=True)
    db.delete(item)
    db.commit()
