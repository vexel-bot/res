"""Exports use the native Craft project and never the retired canvas renderers."""

from uuid import uuid4

from ...domain.studios.craft import CraftMigrationRequestV1, CraftRenderRequestV1
from ...models import LibraryAsset
from .compatibility import record_to_contract


def export_document(db, record, user, *, export_format):
    from .craft import create_render_job, migrate
    from .jobs import execute_job_once

    contract = record_to_contract(record)
    if not contract.native_editor_state:
        migrate(db, record, CraftMigrationRequestV1(
            engine="photocraft" if contract.content_type in {"visual", "carousel"} else "filmcraft",
            expected_revision=record.revision), user, "export-migrate:" + str(uuid4()))
        contract = record_to_contract(record)
    output_format = "png_set" if export_format == "png_set" else export_format
    job, _created = create_render_job(db, record, CraftRenderRequestV1(
        expected_revision=record.revision, format=output_format), user, "export:" + str(uuid4()))
    execute_job_once(db, job)
    db.refresh(job)
    if job.status != "succeeded" or not job.result_payload:
        raise ValueError(job.error_message or "craft_export_failed")
    asset = db.get(LibraryAsset, job.result_payload["artifact"]["assetId"])
    if not asset or asset.workspace_id != record.workspace_id:
        raise ValueError("craft_export_artifact_missing")
    return asset
