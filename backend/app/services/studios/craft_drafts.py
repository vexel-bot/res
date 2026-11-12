"""Private native checkpoints for interrupted Craft editing sessions."""
import json
import shutil
from contextlib import contextmanager
from zipfile import ZIP_DEFLATED, ZipFile
from pathlib import Path

from sqlalchemy import select

from ...config import get_settings
from ...models import StudioGenerationJob
from ...providers.studios.craft import EXTENSIONS
from ..object_storage import get_object_storage, object_key, sha256_file


def session_job(db, record, key):
    return db.scalar(select(StudioGenerationJob).where(
        StudioGenerationJob.workspace_id == record.workspace_id,
        StudioGenerationJob.job_type == "craft_ai",
        StudioGenerationJob.idempotency_key == key,
    ))


def save(db, job, draft):
    source = Path(draft.params["nativePath"])
    if source.stat().st_size > get_settings().studio_craft_max_upload_bytes:
        raise ValueError("craft_native_project_too_large")
    current = job.result_payload or {}
    previous = current.get("draft")
    storage = get_object_storage()
    key = object_key(job.workspace_id, "temporary", EXTENSIONS[draft.engine])
    stored = storage.put_file(source, key=key, media_type="application/octet-stream")
    try:
        job.result_payload = {**current, "draft": {
            "storageKey": key, "storageBackend": stored.backend, "checksumSha256": stored.checksum_sha256,
            "batches": draft.batches, "warnings": list(dict.fromkeys(draft.warnings)),
        }}
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    if previous:
        # Once the new pointer is durable, an old-object cleanup error must not
        # turn an accepted edit into a failed tool call.
        try:
            get_object_storage(previous["storageBackend"]).delete(previous["storageKey"])
        except Exception:
            pass


def restore(job, engine, directory, params):
    checkpoint = (job.result_payload or {}).get("draft")
    if not checkpoint or not checkpoint["storageKey"].startswith(job.workspace_id + "/temporary/"):
        raise ValueError("craft_draft_unavailable")
    output = directory / ("resumed" + EXTENSIONS[engine])
    with get_object_storage(checkpoint["storageBackend"]).materialize(checkpoint["storageKey"]) as source:
        if sha256_file(source) != checkpoint["checksumSha256"]:
            raise ValueError("craft_draft_checksum_mismatch")
        shutil.copyfile(source, output)
    return {**params, "nativePath": str(output)}, checkpoint


def decorate_receipt(db, record, key, answer):
    job = session_job(db, record, key)
    result = (job.result_payload or {}) if job else {}
    export_id = result.get("exportJobId")
    render = db.get(StudioGenerationJob, export_id) if export_id else None
    if render is not None:
        return {**answer, "exportJobId": export_id, "exportStatus": render.status}
    return {**answer, "exportStatus": result["exportStatus"]} if "exportStatus" in result else answer


@contextmanager
def bundle(db, record, job):
    from ...domain.studios.contracts import NativeEditorStateV1
    from .craft import workspace_files
    from .craft_direction import media_ids

    raw = job.request_payload.get("nativeEditorState")
    if not raw:
        raise ValueError("craft_draft_unavailable")
    state = NativeEditorStateV1.model_validate(raw)
    with workspace_files(db, record, state, extra_asset_ids=media_ids(job)) as (
        directory, params, manifests,
    ):
        restored, checkpoint = restore(job, state.engine, directory, params)
        archive = directory / "draft.zip"
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as output:
            output.write(restored["nativePath"], "rascunho" + EXTENSIONS[state.engine])
            for media in manifests:
                output.write(directory / media.path, media.path)
            output.writestr("manifest.json", json.dumps({
                "documentId": record.id, "sourceRevision": job.request_payload["documentRevision"],
                "engine": state.engine, "batches": checkpoint["batches"],
                "media": [item.model_dump(mode="json", by_alias=True) for item in manifests],
            }))
        yield archive
