"""Read-only, authenticated rendering of the immutable review snapshot."""

import hashlib
import io
from contextlib import ExitStack

from sqlalchemy import select

from ...domain.studios.contracts import CreativeDocumentV1
from ...models import LibraryAsset, StudioReviewRequest
from ..creatives import render_creative
from ..object_storage import get_object_storage
from .compatibility import composition_page_to_canvas


def render_review_page(db, review: StudioReviewRequest, page_id: str) -> bytes:
    snapshot = CreativeDocumentV1.model_validate(review.snapshot)
    if snapshot.workspace_id != review.workspace_id or snapshot.document_id != review.document_id:
        raise ValueError("studio_review_snapshot_binding_mismatch")
    if snapshot.content_type not in {"visual", "carousel"}:
        raise ValueError("studio_review_requires_rendered_video")
    index = next((i for i, page in enumerate(snapshot.composition.pages) if page.id == page_id), None)
    if index is None:
        raise ValueError("studio_review_page_not_found")
    page = snapshot.composition.pages[index]
    if page.width * page.height > 16_000_000 or any(layer.width * layer.height > 16_000_000 for layer in page.layers):
        raise ValueError("studio_review_preview_pixel_limit")
    canvas = composition_page_to_canvas(snapshot, index)
    required_ids = {
        layer.asset_id for layer in canvas.layers if layer.type == "image" and layer.visible and layer.opacity > 0
    }
    references = {asset.id: asset for asset in snapshot.assets}
    with ExitStack() as stack:
        paths = {}
        for asset_id in required_ids:
            ref = references.get(asset_id)
            asset = db.scalar(
                select(LibraryAsset).where(
                    LibraryAsset.id == asset_id,
                    LibraryAsset.workspace_id == review.workspace_id,
                    LibraryAsset.lifecycle_status == "active",
                )
            )
            if not ref or not ref.checksum or not asset or not asset.storage_key:
                raise ValueError("studio_review_source_unavailable_or_unpinned")
            if ref.checksum.lower() != (asset.checksum_sha256 or "").lower():
                raise ValueError("studio_review_source_changed")
            path = stack.enter_context(
                get_object_storage(asset.storage_backend or "local").materialize(asset.storage_key)
            )
            with path.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            if digest != ref.checksum.lower():
                raise ValueError("studio_review_source_changed")
            paths[asset_id] = path
        image = render_creative(canvas, paths)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
