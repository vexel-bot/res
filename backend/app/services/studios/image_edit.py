from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from ...domain.studios.image_edit import (
    ImageDerivationRequestV1,
    ImageEditExecutionV1,
    ImageEditProvider,
    image_derivation_digest,
)
from ...models import LibraryAsset, User
from ...services.object_storage import get_object_storage, object_key, sha256_file
from .kernel import emit_event


def derive_image_asset(
    db: Session,
    *,
    source: LibraryAsset,
    request: ImageDerivationRequestV1,
    user: User,
    provider: ImageEditProvider,
) -> LibraryAsset:
    if source.workspace_id != request.workspace_id:
        raise ValueError("image_derivation_workspace_mismatch")
    if source.lifecycle_status != "active" or not source.storage_key:
        raise ValueError("image_derivation_source_unavailable")
    if not (source.media_type or "").startswith("image/"):
        raise ValueError("image_derivation_source_not_image")
    if not source.checksum_sha256:
        raise ValueError("image_derivation_source_checksum_missing")
    if source.checksum_sha256.lower() != request.expected_source_checksum_sha256.lower():
        raise ValueError("image_derivation_source_checksum_conflict")

    digest = image_derivation_digest(source.checksum_sha256, request)
    derived_id = str(
        uuid5(NAMESPACE_URL, f"clicko:image:{request.workspace_id}:{request.idempotency_key}")
    )
    existing = db.get(LibraryAsset, derived_id)
    if existing:
        metadata = existing.object_metadata or {}
        if (
            metadata.get("sourceAssetId") == source.id
            and metadata.get("operationDigestSha256") == digest
        ):
            return existing
        raise ValueError("image_derivation_idempotency_conflict")

    source_storage = get_object_storage(source.storage_backend)
    destination_storage = get_object_storage()
    destination_key = object_key(request.workspace_id, "derived", ".png")
    execution = ImageEditExecutionV1(
        brightness=request.brightness,
        contrast=request.contrast,
        edit_mask=request.edit_mask,
        protected_regions=request.protected_regions,
    )
    with source_storage.materialize(source.storage_key) as source_path:
        if sha256_file(source_path).lower() != source.checksum_sha256.lower():
            raise ValueError("image_derivation_materialized_checksum_mismatch")
        with tempfile.TemporaryDirectory(prefix="clicko-image-edit-") as directory:
            output_path = Path(directory) / "derived.png"
            result = provider.derive(str(source_path), str(output_path), execution)
            metadata = {
                "sourceAssetId": source.id,
                "sourceChecksumSha256": source.checksum_sha256.lower(),
                "operationDigestSha256": digest,
                "provider": result.provider,
                "providerVersion": result.provider_version,
                "reviewRequired": "true",
                "editMask": json.dumps(
                    request.edit_mask.model_dump(mode="json", by_alias=True)
                    if request.edit_mask
                    else None,
                    separators=(",", ":"),
                ),
                "protectedRegions": json.dumps(
                    [item.model_dump(mode="json", by_alias=True) for item in request.protected_regions],
                    separators=(",", ":"),
                ),
            }
            stored = destination_storage.put_file(
                output_path,
                key=destination_key,
                media_type=result.media_type,
                metadata=metadata,
            )
    derived = LibraryAsset(
        id=derived_id,
        workspace_id=request.workspace_id,
        title=request.title.strip(),
        asset_type="image",
        tags=["studio", "image-derived", "needs-review"],
        campaign_id=source.campaign_id,
        content_id=source.content_id,
        storage_key=destination_key,
        storage_backend=stored.backend,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        object_metadata={**stored.metadata, **metadata},
    )
    try:
        db.add(derived)
        emit_event(
            db,
            workspace_id=request.workspace_id,
            event_type="studio.image-derivation.created",
            aggregate_type="library_asset",
            aggregate_id=derived.id,
            correlation_id=request.idempotency_key,
            actor_id=user.id,
            payload={
                "sourceAssetId": source.id,
                "sourceChecksumSha256": source.checksum_sha256,
                "operationDigestSha256": digest,
                "provider": provider.name,
                "providerVersion": provider.version,
                "reviewRequired": True,
            },
        )
        db.commit()
        db.refresh(derived)
    except Exception:
        db.rollback()
        destination_storage.delete(destination_key)
        raise
    return derived
