"""Authenticated preview of the immutable, verified native render approved by review."""

import json
import zipfile

from ...domain.studios.contracts import CreativeDocumentV1
from ..object_storage import get_object_storage, sha256_file
from .craft import scoped_asset


def render_review_page(db, review, page_id):
    snapshot = CreativeDocumentV1.model_validate(review.snapshot)
    if snapshot.workspace_id != review.workspace_id or snapshot.document_id != review.document_id:
        raise ValueError("studio_review_snapshot_binding_mismatch")
    if not snapshot.native_editor_state:
        raise ValueError("studio_review_native_migration_required")
    if snapshot.native_editor_state.engine != "photocraft":
        raise ValueError("studio_review_requires_rendered_video")
    if not review.render_asset_id or not review.render_checksum_sha256:
        raise ValueError("studio_review_craft_render_required")
    artifact = scoped_asset(db, review.workspace_id, review.render_asset_id, review.render_checksum_sha256)
    with get_object_storage(artifact.storage_backend).materialize(artifact.storage_key) as path:
        if sha256_file(path) != review.render_checksum_sha256:
            raise ValueError("studio_review_render_artifact_mismatch")
        if artifact.media_type == "application/zip":
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                filename = manifest["pages"].get(page_id)
                if not filename or filename not in archive.namelist():
                    raise ValueError("studio_review_page_not_found")
                return archive.read(filename)
        if len(snapshot.composition.pages) != 1 or snapshot.composition.pages[0].id != page_id:
            raise ValueError("studio_review_page_not_found")
        return path.read_bytes()
