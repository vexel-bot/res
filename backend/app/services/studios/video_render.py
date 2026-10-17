"""Compatibility entry point routes existing production callers to Craft render jobs."""

from ...domain.studios.craft import CraftMigrationRequestV1, CraftRenderRequestV1
from .compatibility import record_to_contract


def create_video_render_job(db, document, request, idempotency_key, user):
    from .craft import create_render_job, migrate

    if document.workspace_id != request.workspace_id or document.id != request.document_id:
        raise ValueError("studio_render_document_mismatch")
    if document.revision != request.expected_document_revision or document.version != request.expected_document_version:
        raise ValueError("studio_document_conflict")
    contract = record_to_contract(document)
    if not contract.native_editor_state:
        engine = "effectcraft" if any(page.layers for page in contract.composition.pages) else "filmcraft"
        converted = migrate(
            db,
            document,
            CraftMigrationRequestV1(engine=engine, expected_revision=document.revision),
            user,
            "render-migrate:" + idempotency_key,
        )
        if converted.get("migrationWarnings"):
            raise ValueError("craft_conversion_requires_review_open_native_studio")
    return create_render_job(
        db,
        document,
        CraftRenderRequestV1(
            expected_revision=document.revision, format=request.output.format, quality=request.output.quality
        ),
        user,
        idempotency_key,
    )


def execute_video_render(db, job, progress, is_cancelled):
    if job.job_type != "craft_render":
        raise ValueError("legacy_video_renderer_replaced_by_craft")
    from .craft import execute_render_job

    return execute_render_job(db, job, progress, is_cancelled)
