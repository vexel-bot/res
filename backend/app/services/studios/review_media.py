"""Materialize and verify the private render pinned by an immutable review."""

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import LibraryAsset, StudioReviewRequest
from ..object_storage import get_object_storage

MAX_PACKAGE_BYTES = 512 * 1024 * 1024


@contextmanager
def verified_library_asset_path(
    db: Session,
    *,
    workspace_id: str,
    asset_id: str,
    checksum_sha256: str,
    max_bytes: int,
    missing_code: str,
    changed_code: str,
    too_large_code: str,
) -> Iterator[tuple[LibraryAsset, Path]]:
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == asset_id,
            LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if (
        not asset
        or not asset.storage_key
        or (asset.checksum_sha256 or "").lower() != checksum_sha256.lower()
    ):
        raise ValueError(missing_code if not asset or not asset.storage_key else changed_code)
    if asset.size_bytes is None or asset.size_bytes > max_bytes:
        raise ValueError(too_large_code)
    with get_object_storage(asset.storage_backend or "local").materialize(asset.storage_key) as path:
        if path.stat().st_size > max_bytes:
            raise ValueError(too_large_code)
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != checksum_sha256.lower():
            raise ValueError(changed_code)
        yield asset, path


@contextmanager
def verified_review_video_path(db: Session, review: StudioReviewRequest) -> Iterator[tuple[Path, str]]:
    if not review.render_asset_id or not review.render_checksum_sha256:
        raise ValueError("studio_publication_render_missing")
    with verified_library_asset_path(
        db,
        workspace_id=review.workspace_id,
        asset_id=review.render_asset_id,
        checksum_sha256=review.render_checksum_sha256,
        max_bytes=MAX_PACKAGE_BYTES,
        missing_code="studio_publication_render_changed",
        changed_code="studio_publication_render_changed",
        too_large_code="studio_publication_package_too_large",
    ) as (asset, path):
        extension = ".webm" if asset.media_type == "video/webm" else ".mp4"
        yield path, extension
