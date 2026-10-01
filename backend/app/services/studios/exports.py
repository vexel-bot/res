from __future__ import annotations

import io
import json
import tempfile
import zipfile
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import CreativeDocumentV1, ExportReferenceV1
from ...models import CreativeDocument, FeedbackEvent, LibraryAsset, User
from ..creatives import render_creative
from ..object_storage import get_object_storage, object_key
from .compatibility import composition_page_to_canvas, persist_contract, record_to_contract
from .kernel import emit_event


def export_document(
    db: Session,
    record: CreativeDocument,
    user: User,
    *,
    export_format: str,
) -> LibraryAsset:
    contract = record_to_contract(record)
    page_count = len(contract.composition.pages)
    if export_format == "png" and page_count != 1:
        raise ValueError("studio_export_requires_png_set")

    asset_ids = {asset.id for asset in contract.assets}
    stored_assets = (
        db.scalars(
            select(LibraryAsset).where(
                LibraryAsset.id.in_(asset_ids),
                LibraryAsset.workspace_id == record.workspace_id,
                LibraryAsset.lifecycle_status == "active",
            )
        ).all()
        if asset_ids
        else []
    )
    with ExitStack() as stack:
        source_paths = {
            asset.id: stack.enter_context(
                get_object_storage(asset.storage_backend or "local").materialize(str(asset.storage_key))
            )
            for asset in stored_assets
            if asset.storage_key
        }
        rendered = [
            render_creative(composition_page_to_canvas(contract, index), source_paths) for index in range(page_count)
        ]
    created_at = datetime.now(UTC)
    storage = get_object_storage()
    with tempfile.TemporaryDirectory(prefix="clicko-studio-export-") as temporary_directory:
        if export_format == "png":
            storage_key = object_key(record.workspace_id, "exports", ".png")
            destination = Path(temporary_directory) / "export.png"
            rendered[0].save(destination, format="PNG", optimize=True)
            asset_type = "image"
            media_type = "image/png"
            tags = ["export", "png", f"creative:{record.id}", f"version:{record.version}"]
            public_format = "png"
        else:
            storage_key = object_key(record.workspace_id, "exports", ".zip")
            destination = Path(temporary_directory) / "export.zip"
            manifest = {
                "schemaVersion": "studio.export-manifest.v1",
                "documentId": record.id,
                "documentVersion": record.version,
                "orderedPages": [page.id for page in contract.composition.pages],
            }
            with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                for index, image in enumerate(rendered, start=1):
                    payload = io.BytesIO()
                    image.save(payload, format="PNG", optimize=True)
                    archive.writestr(f"{index:02d}.png", payload.getvalue())
            asset_type = "archive"
            media_type = "application/zip"
            tags = ["export", "png-set", f"creative:{record.id}", f"version:{record.version}"]
            public_format = "png_set"
        stored = storage.put_file(
            destination,
            key=storage_key,
            media_type=media_type,
            metadata={
                "workspace-id": record.workspace_id,
                "document-id": record.id,
                "document-version": str(record.version),
                "source": "studio-export",
            },
        )

    try:
        asset = LibraryAsset(
            workspace_id=record.workspace_id,
            title=f"{record.title} v{record.version} · {page_count} página(s)",
            asset_type=asset_type,
            tags=tags,
            campaign_id=record.campaign_id,
            content_id=record.post_id,
            storage_key=storage_key,
            storage_backend=stored.backend,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            object_metadata=stored.metadata,
        )
        db.add(asset)
        db.flush()
        updated = contract.model_copy(
            update={
                "revision": record.revision + 1,
                "exports": [
                    *contract.exports,
                    ExportReferenceV1(
                        asset_id=asset.id,
                        document_version=record.version,
                        target="library",
                        format=public_format,
                        created_at=created_at,
                    ),
                ],
                "actor_id": user.id,
                "updated_at": created_at,
            }
        )
        persist_contract(record, CreativeDocumentV1.model_validate(updated))
        db.add(
            FeedbackEvent(
                workspace_id=record.workspace_id,
                campaign_id=record.campaign_id,
                content_id=record.post_id,
                creative_document_id=record.id,
                user_id=user.id,
                event_type="generated",
                payload={
                    "exportAssetId": asset.id,
                    "format": public_format,
                    "version": record.version,
                    "pageCount": page_count,
                },
            )
        )
        emit_event(
            db,
            workspace_id=record.workspace_id,
            event_type="studio.document.exported",
            aggregate_type="creative_document",
            aggregate_id=record.id,
            correlation_id=contract.correlation_id,
            actor_id=user.id,
            payload={"assetId": asset.id, "format": public_format, "pageCount": page_count},
        )
        db.commit()
        db.refresh(asset)
        return asset
    except Exception:
        db.rollback()
        storage.delete(storage_key)
        raise
