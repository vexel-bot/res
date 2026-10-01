import mimetypes
import tempfile
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..domain.studios.image_edit import ImageDerivationRequestV1
from ..models import Campaign, LibraryAsset, Membership, Post, User
from ..providers.studios.pillow_image_edit import PillowImageEditProvider
from ..schemas import AssetIn, AssetOut
from ..security import get_current_user
from ..services.object_storage import get_object_storage, object_key
from ..services.studios.image_edit import derive_image_asset

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
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/flac": ".flac",
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
        if content_type in {"audio/wav", "audio/x-wav"}:
            header = path.read_bytes()[:12]
            if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                raise ValueError("Invalid WAV signature")
            return
        if content_type == "audio/mpeg":
            header = path.read_bytes()[:3]
            if not (header == b"ID3" or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0)):
                raise ValueError("Invalid MP3 signature")
            return
        if content_type == "audio/flac":
            if path.read_bytes()[:4] != b"fLaC":
                raise ValueError("Invalid FLAC signature")
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
    url = (
        f"/api/v1/assets/{item.id}/content"
        if item.lifecycle_status == "active" and item.storage_key
        else item.url if item.lifecycle_status == "active" else None
    )
    return AssetOut(
        id=item.id,
        workspace_id=item.workspace_id,
        title=item.title,
        type=item.asset_type,
        tags=item.tags or [],
        campaign_id=item.campaign_id,
        content_id=item.content_id,
        url=url,
        storage_backend=item.storage_backend if item.storage_key else None,
        media_type=item.media_type,
        size_bytes=item.size_bytes,
        checksum_sha256=item.checksum_sha256,
        metadata=item.object_metadata or {},
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
        select(LibraryAsset)
        .where(
            LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
        .order_by(LibraryAsset.created_at.desc())
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
    media_type = file.content_type or "application/octet-stream"
    storage = get_object_storage(settings=settings)
    storage_key = object_key(workspace_id, "raw", extension)
    with tempfile.TemporaryDirectory(prefix="clicko-upload-") as temporary_directory:
        staged = Path(temporary_directory) / f"upload{extension}"
        size = 0
        try:
            with staged.open("xb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")
                    output.write(chunk)
        finally:
            await file.close()
        validate_uploaded_content(staged, media_type)
        stored = storage.put_file(
            staged,
            key=storage_key,
            media_type=media_type,
            metadata={"workspace-id": workspace_id, "source": "user-upload"},
        )
    item = LibraryAsset(
        workspace_id=workspace_id,
        title=title.strip(),
        asset_type=(
            "image"
            if (file.content_type or "").startswith("image/")
            else "audio"
            if (file.content_type or "").startswith("audio/")
            else "upload"
        ),
        tags=[value.strip() for value in tags.split(",") if value.strip()],
        storage_key=storage_key,
        storage_backend=stored.backend,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        object_metadata=stored.metadata,
    )
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        storage.delete(storage_key)
        raise
    return asset_out(item)


@router.get("/{asset_id}/content", response_model=None)
def download_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    item = db.get(LibraryAsset, asset_id)
    if not item or item.lifecycle_status != "active" or not item.storage_key:
        raise HTTPException(status_code=404, detail="Asset not found")
    assert_access(db, user.id, item.workspace_id)
    storage = get_object_storage(item.storage_backend or "local", settings)
    path = storage.local_path(item.storage_key)
    media_type = item.media_type or mimetypes.guess_type(item.storage_key)[0] or "application/octet-stream"
    suffix = PurePosixPath(item.storage_key).suffix
    filename = f"{item.title}{suffix}"
    if path is not None:
        return FileResponse(path, media_type=media_type, filename=filename)
    signed_url = storage.signed_download_url(item.storage_key, filename=filename)
    if not signed_url:
        raise HTTPException(status_code=404, detail="Stored file not found")
    return RedirectResponse(signed_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.post("/{asset_id}/derive", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def derive_image(
    asset_id: str,
    request: ImageDerivationRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetOut:
    assert_access(db, user.id, request.workspace_id)
    source = db.get(LibraryAsset, asset_id)
    if source is None or source.lifecycle_status != "active":
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        derived = derive_image_asset(
            db,
            source=source,
            request=request,
            user=user,
            provider=PillowImageEditProvider(),
        )
    except ValueError as error:
        code = str(error)
        status_code = 409 if code.endswith("conflict") else 422
        raise HTTPException(status_code=status_code, detail={"code": code}) from error
    return asset_out(derived)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    item = db.get(LibraryAsset, asset_id)
    if not item or item.lifecycle_status != "active":
        raise HTTPException(status_code=404, detail="Asset not found")
    assert_access(db, user.id, item.workspace_id)
    if item.storage_key:
        get_object_storage(item.storage_backend or "local", settings).delete(item.storage_key)
    db.delete(item)
    db.commit()
