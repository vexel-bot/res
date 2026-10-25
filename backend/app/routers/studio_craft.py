"""Authenticated native Craft editor API. Clients never send storage or executable paths."""

import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from ..config import get_settings
from ..database import get_db
from ..domain.studios.craft import (
    CraftAICommandRequestV1,
    CraftCommandRequestV1,
    CraftLinkRequestV1,
    CraftMigrationRequestV1,
    CraftPreviewRequestV1,
    CraftRecoverEffectsRequestV1,
    CraftRenderRequestV1,
    CraftUpgradeRequestV1,
)
from ..domain.studios.llm import LLMConnectionRequest
from ..models import User
from ..providers.studios.craft import ENGINES, EXTENSIONS, CraftRuntimeError, engine_capability
from ..schemas import AssetOut
from ..security import get_current_user
from ..services.object_storage import get_object_storage, sha256_file
from ..services.studios import craft
from ..services.studios.compatibility import record_to_contract
from ..services.studios.jobs import enqueue_job_task, job_out
from .assets import assert_access, asset_out, validate_uploaded_content
from .studios import owned_document

router = APIRouter(prefix="/studios/v1", tags=["craft-studios-v1"])


def error(exc: ValueError) -> HTTPException:
    code = str(exc)
    unavailable = isinstance(exc, CraftRuntimeError) and any(
        word in code for word in ("runtime", "not_built", "unavailable", "timeout")
    )
    return HTTPException(status_code=503 if unavailable else 409 if "conflict" in code else 422, detail={"code": code})


def invoke(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except ValueError as exc:
        raise error(exc) from exc


@router.get("/craft/engines")
def engines(user: User = Depends(get_current_user)):
    return {"schemaVersion": "studio.craft-engines.v1", "engines": [engine_capability(engine) for engine in ENGINES]}


@router.get("/craft/llm-catalog")
def llm_catalog(user: User = Depends(get_current_user)):
    from ..config import get_settings
    from ..providers.studios.llm_catalog import PROVIDERS

    settings = get_settings()
    selected = settings.studio_editing_ai_planning_provider or settings.studio_editing_ai_provider
    legacy_ready = (
        selected == "compatible" and bool(settings.studio_editing_ai_base_url and settings.studio_editing_ai_model)
    ) or (selected == "gemini" and settings.studio_gemini_enabled)
    return {
        "providers": PROVIDERS,
        "credentialStorageReady": bool(settings.studio_llm_credential_key),
        "legacyPlanningAvailable": legacy_ready,
    }


@router.get("/craft/llm-connections")
def llm_connections(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    from ..models import Membership, StudioLLMConnection
    from ..services.studios import llm_connections as service

    service.access(db, user.id, workspace_id)
    role = db.scalar(
        select(Membership.role).where(
            Membership.user_id == user.id,
            Membership.workspace_id == workspace_id,
        )
    )
    rows = db.scalars(select(StudioLLMConnection).where(StudioLLMConnection.workspace_id == workspace_id))
    return {
        "connections": [service.public(row) for row in rows if row.provider != "google-motion-experimental"],
        "canManage": role.lower() in {"owner", "admin"},
    }


@router.post("/craft/llm-connections", status_code=201)
def create_llm_connection(
    workspace_id: str,
    request: LLMConnectionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.studios.llm_connections import save

    return invoke(save, db, workspace_id, request, user)


@router.put("/craft/llm-connections/{connection_id}")
def update_llm_connection(
    connection_id: str,
    workspace_id: str,
    request: LLMConnectionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.studios.llm_connections import save

    return invoke(save, db, workspace_id, request, user, connection_id)


@router.delete("/craft/llm-connections/{connection_id}")
def disable_llm_connection(
    connection_id: str,
    workspace_id: str,
    expected_revision: int = Query(ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import update

    from ..models import StudioLLMConnection
    from ..services.studios import llm_connections as service

    service.access(db, user.id, workspace_id, owner=True)
    row = invoke(service.scoped, db, workspace_id, connection_id)
    changed = db.execute(
        update(StudioLLMConnection)
        .where(
            StudioLLMConnection.id == row.id,
            StudioLLMConnection.revision == expected_revision,
        )
        .values(config={**row.config, "enabled": False}, credential_ciphertext=None, revision=expected_revision + 1)
    )
    if changed.rowcount != 1:
        db.rollback()
        raise error(ValueError("llm_connection_revision_conflict"))
    db.commit()
    db.refresh(row)
    return service.public(row)


@router.get("/documents/{document_id}/craft/inspection")
def inspect_document(
    document_id: str,
    frame: int = Query(default=0, ge=0),
    page_id: str | None = Query(default=None, alias="pageId"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return invoke(craft.inspection, db, owned_document(db, user.id, document_id), frame=frame, page_id=page_id)


@router.post("/documents/{document_id}/craft/migrate")
def migrate_document(
    document_id: str,
    request: CraftMigrationRequestV1,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return invoke(craft.migrate, db, owned_document(db, user.id, document_id), request, user, key)


@router.post("/documents/{document_id}/craft/commands")
def execute_commands(
    document_id: str,
    request: CraftCommandRequestV1,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    result = invoke(craft.commands, db, record, request, user, key)
    result["linkedCompositionRefresh"] = schedule_composition_refresh(db, record, user)
    return result


@router.post("/documents/{document_id}/craft/upgrade-build")
def upgrade_build(
    document_id: str,
    request: CraftUpgradeRequestV1,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    result = invoke(craft.upgrade_build, db, record, request, user, key)
    result["linkedCompositionRefresh"] = schedule_composition_refresh(db, record, user)
    return result


@router.post("/documents/{document_id}/craft/recover-effects")
def recover_effects(
    document_id: str,
    request: CraftRecoverEffectsRequestV1,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return invoke(craft.recover_effects, db, owned_document(db, user.id, document_id), request, user, key)


@router.post("/documents/{document_id}/craft/ai-commands")
def execute_ai_commands(
    document_id: str,
    request: CraftAICommandRequestV1,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.studios.craft_ai import ai_commands

    record = owned_document(db, user.id, document_id)
    result = invoke(ai_commands, db, record, request, user, key)
    result["linkedCompositionRefresh"] = schedule_composition_refresh(db, record, user)
    return result


@router.get("/documents/{document_id}/craft/ai-requests/{key}")
def reconcile_ai_request(
    document_id: str,
    key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    from ..models import StudioGenerationJob

    record = owned_document(db, user.id, document_id)
    job = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == record.workspace_id,
            StudioGenerationJob.document_id == record.id,
            StudioGenerationJob.job_type == "craft_ai",
            StudioGenerationJob.idempotency_key == key,
        )
    )
    if job is None:
        return {"status": "not_found"}
    committed = invoke(craft.receipt, db, record, key, job.payload_hash)
    return {
        "status": "committed" if committed else job.status,
        "receipt": committed,
        "responseReady": bool((job.result_payload or {}).get("commands")),
        "errorCode": job.error_code,
        "safeToStartNew": job.status == "failed" and not (job.result_payload or {}).get("submissionStarted"),
    }


def schedule_composition_refresh(db, record, user):
    state = record_to_contract(record).native_editor_state
    if state and state.engine == "effectcraft":
        from ..tasks import refresh_craft_compositions

        try:
            refresh_craft_compositions.apply_async(args=[record.id, user.id], queue="studio.media.cpu", retry=False)
            return {"queued": True}
        except Exception:
            craft.emit_event(
                db,
                workspace_id=record.workspace_id,
                event_type="studio.craft.link_refresh_queue_failed",
                aggregate_type="creative_document",
                aggregate_id=record.id,
                correlation_id=record.correlation_id,
                actor_id=user.id,
                payload={"code": "craft_link_refresh_queue_unavailable"},
            )
            db.commit()
            return {"queued": False, "reason": "craft_link_refresh_queue_unavailable"}
    return None


@router.post("/documents/{document_id}/craft/link-composition")
def link_composition(
    document_id: str,
    request: CraftLinkRequestV1,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    source = owned_document(db, user.id, request.composition_document_id)
    target = owned_document(db, user.id, document_id)
    return invoke(craft.link_composition, db, target, source, request, user, key)


@router.post("/documents/{document_id}/craft/preview")
def preview(
    document_id: str,
    request: CraftPreviewRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    result = invoke(craft.render_frame, db, record, frame=request.frame, page_id=request.page_id)
    return Response(result, media_type="image/png", headers={"Cache-Control": "private, no-store"})


@router.post("/documents/{document_id}/craft/render-jobs", status_code=201)
def render_job(
    document_id: str,
    request: CraftRenderRequestV1,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job, created = invoke(craft.create_render_job, db, owned_document(db, user.id, document_id), request, user, key)
    if created:
        from ..tasks import execute_studio_generation

        try:
            enqueue_job_task(
                execute_studio_generation, job, isolated_queues_enabled=get_settings().studio_isolated_queues_enabled
            )
        except Exception as exc:
            # Make broker failures visible and eligible for the existing retry endpoint.
            job.status = "failed"
            job.error_code = "queue_unavailable"
            job.error_message = type(exc).__name__
            db.commit()
            raise HTTPException(
                status_code=503, detail={"code": "craft_job_queue_unavailable", "jobId": job.id}
            ) from exc
    return job_out(job)


@router.get("/documents/{document_id}/native-project")
def load_native_project(
    document_id: str,
    all_pages: bool = Query(default=False, alias="allPages"),
    page_id: str | None = Query(default=None, alias="pageId"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    state = record_to_contract(record).native_editor_state
    if not state:
        raise HTTPException(status_code=422, detail={"code": "craft_native_project_required"})
    if all_pages:
        manager = craft.native_bundle(db, record, state)
        payload = invoke(manager.__enter__)
        return FileResponse(
            str(payload),
            media_type="application/zip",
            background=BackgroundTask(manager.__exit__, None, None, None),
            headers={
                "Cache-Control": "private, no-store",
                "Content-Disposition": f'attachment; filename="{record.id}-projects.zip"',
            },
        )
    state = invoke(craft.select_page_state, state, page_id)
    asset = invoke(craft.scoped_asset, db, record.workspace_id, state.project_asset_id, state.checksum_sha256)

    def content():
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            if sha256_file(path) != state.checksum_sha256:
                raise ValueError("craft_native_checksum_mismatch")
            with path.open("rb") as stream:
                while chunk := stream.read(1024**2):
                    yield chunk

    return StreamingResponse(
        content(),
        media_type=asset.media_type,
        headers={
            "ETag": f'"{state.checksum_sha256}"',
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'attachment; filename="{record.id}{EXTENSIONS[state.engine]}"',
        },
    )


async def receive_stream(request: Request, path: Path) -> None:
    limit = get_settings().studio_craft_max_upload_bytes
    declared = request.headers.get("Content-Length")
    if declared and (not declared.isdigit() or int(declared) > limit):
        raise HTTPException(status_code=413, detail={"code": "craft_upload_too_large"})
    size = 0
    with path.open("xb") as destination:
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                raise HTTPException(status_code=413, detail={"code": "craft_upload_too_large"})
            destination.write(chunk)
    if not size:
        raise HTTPException(status_code=422, detail={"code": "craft_upload_empty"})


@router.put("/documents/{document_id}/native-project")
async def save_native_project(
    document_id: str,
    request: Request,
    engine: Literal["photocraft", "filmcraft", "effectcraft"] = Query(),
    expected_revision: int = Query(alias="expectedRevision", ge=1),
    page_id: str | None = Query(default=None, alias="pageId"),
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    with tempfile.TemporaryDirectory(prefix="craft-upload-") as temporary:
        path = Path(temporary) / ("upload" + EXTENSIONS[engine])
        await receive_stream(request, path)
        result = await run_in_threadpool(
            invoke,
            craft.save_native,
            db,
            record,
            user,
            path,
            engine=engine,
            expected_revision=expected_revision,
            key=key,
            page_id=page_id,
        )
        result["linkedCompositionRefresh"] = schedule_composition_refresh(db, record, user)
        return result


@router.post("/craft/assets", response_model=AssetOut, status_code=201)
async def upload_asset(
    request: Request,
    workspace_id: str = Query(),
    title: str = Query(min_length=1, max_length=240),
    filename: str = Query(min_length=1, max_length=240),
    media_type: str = Query(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assert_access(db, user.id, workspace_id)
    types = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "audio/wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/flac": ".flac",
        "font/woff2": ".woff2",
    }
    if media_type not in types:
        raise HTTPException(status_code=422, detail={"code": "craft_asset_media_type_unsupported"})
    with tempfile.TemporaryDirectory(prefix="craft-asset-upload-") as temporary:
        path = Path(temporary) / ("upload" + types[media_type])
        await receive_stream(request, path)
        if media_type == "video/webm":
            with path.open("rb") as source:
                if source.read(4) != b"\x1aE\xdf\xa3":
                    raise HTTPException(status_code=422, detail={"code": "craft_asset_content_invalid"})
        else:
            await run_in_threadpool(validate_uploaded_content, path, media_type)
        record = SimpleNamespace(id="upload", workspace_id=workspace_id, campaign_id=None, post_id=None, title=title)
        asset, storage, key = await run_in_threadpool(
            craft.write_asset,
            db,
            record,
            path,
            suffix=types[media_type],
            media_type=media_type,
            asset_type="video"
            if media_type.startswith("video/")
            else "audio"
            if media_type.startswith("audio/")
            else "image"
            if media_type.startswith("image/")
            else "document",
            metadata={"sourceFilename": filename, "uploadedBy": user.id},
        )
        try:
            db.commit()
            db.refresh(asset)
            return asset_out(asset)
        except Exception:
            db.rollback()
            storage.delete(key)
            raise
