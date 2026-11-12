"""Durable review media shared by the native editor and its directing session."""

import hashlib
import json

from sqlalchemy import select

from ...models import LibraryAsset
from .craft import write_asset
from ..object_storage import sha256_file


def persist_review(db, record, review, *, job_id=None, draft_batch=None):
    path = review["path"]
    checksum = sha256_file(path)
    origin = {"documentId": record.id, "documentRevision": record.revision,
              "jobId": job_id, "draftBatch": draft_batch, "report": review["report"]}
    evidence_hash = hashlib.sha256(json.dumps(origin, sort_keys=True).encode()).hexdigest()
    origin["evidenceHash"] = evidence_hash
    asset = db.scalar(select(LibraryAsset).where(
        LibraryAsset.workspace_id == record.workspace_id,
        LibraryAsset.lifecycle_status == "active", LibraryAsset.checksum_sha256 == checksum,
        LibraryAsset.object_metadata["craftReview"]["documentId"].as_string() == record.id,
        LibraryAsset.object_metadata["craftReview"]["documentRevision"].as_integer() == record.revision,
        LibraryAsset.object_metadata["craftReview"]["evidenceHash"].as_string() == evidence_hash,
    ))
    if asset is None:
        media_type = review["report"]["artifact"]["mediaType"]
        asset, storage, key = write_asset(
            db, record, path, suffix=".mp4" if media_type.startswith("video/") else ".wav",
            media_type=media_type, asset_type="video" if media_type.startswith("video/") else "audio",
            metadata={"craftReview": origin}, title=record.title + " · prévia de edição",
        )
        try:
            db.flush()
        except Exception:
            storage.delete(key)
            raise
    return {"assetId": asset.id, "checksumSha256": checksum, "mediaType": asset.media_type, "documentRevision": record.revision,
            "draftBatch": draft_batch, "jobId": job_id, "report": review["report"]}
