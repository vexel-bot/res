"""Video-only canonical timeline boundary, reusing Clicko's session and jobs."""

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..domain.studios.timeline_editor import TimelineEditRequest, TimelineRenderRequest
from ..domain.studios.video_assembly import AssemblyRenderRequest
from ..models import LibraryAsset, StudioGenerationJob, User
from ..providers.studios import moneyprinterturbo
from ..providers.studios.timeline_ffmpeg import capability, probe
from ..security import get_current_user
from ..services.object_storage import get_object_storage
from ..services.studios import timeline_editor
from ..services.studios.compatibility import record_to_contract
from ..services.studios.craft import scoped_asset
from ..services.studios.jobs import enqueue_job_task, job_out
from .assets import store_upload
from .studios import owned_document

router = APIRouter(prefix="/studios/v1/video", tags=["video-timeline"])
archive_router = APIRouter(prefix="/studios/v1/documents", tags=["studio-archive"])


def recover_interrupted_local_jobs():
    """After a local restart, surface interrupted CPU work as explicitly retryable.

    Never steal from a live worker and never automatically repeat provider work.
    """
    if not get_settings().celery_task_always_eager:
        return
    from sqlalchemy import select

    from ..database import SessionLocal
    from ..models import StudioGenerationJob
    from ..providers.studios.heavy_media_lease import _identity

    with SessionLocal() as db:
        rows = db.scalars(
            select(StudioGenerationJob).where(
                StudioGenerationJob.job_type != "external_call",
                StudioGenerationJob.status.in_(["queued", "running", "retrying", "cancel_requested"])
            )
        ).all()
        for job in rows:
            context = job.worker_execution_context or {}
            pid = context.get("processId")
            identity = _identity(int(pid)) if pid else None
            instance = context.get("workerInstanceId", "") or ""
            if identity is not None and (
                not instance.startswith(("local-timeline:", "local-studios:")) or instance.endswith(":" + identity)
            ):
                continue
            job.status = "cancelled" if job.status == "cancel_requested" else "failed"
            unknown = (
                (job.result_payload or {}).get("submissionStarted")
                and not (job.result_payload or {}).get("responseKey")
                and not (job.result_payload or {}).get("providerOperationId")
            )
            job.error_code = (
                "craft_agent_interrupted"
                if job.job_type == "craft_ai" and job.request_payload.get("input", {}).get("operation") == "native_tool_session"
                else "editing_submission_outcome_unknown_manual_reconciliation_required"
                if unknown
                else "timeline_interrupted_restart"
                if job.job_type == "timeline_render"
                else "studio_interrupted_restart"
            )
            job.error_message = (
                "O serviço foi reiniciado. Seu projeto está salvo. "
                "Confira o resultado antes de repetir qualquer chamada externa."
            )
            from datetime import UTC, datetime

            job.finished_at = datetime.now(UTC)
        db.commit()


def failure(error):
    code = str(error)
    return HTTPException(409 if "conflict" in code else 503 if "unavailable" in code else 422, detail={"code": code})


@router.get("/capabilities")
def capabilities(user: User = Depends(get_current_user)):
    return capability()


@router.get("/library")
def video_library(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import select

    from ..models import LibraryAsset, Membership
    from .assets import asset_out

    membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
    rows = db.scalars(
        select(LibraryAsset)
        .where(
            LibraryAsset.workspace_id == membership.workspace_id,
            LibraryAsset.asset_type == "video",
            LibraryAsset.lifecycle_status == "active",
        )
        .order_by(LibraryAsset.created_at.desc())
        .limit(500)
    ).all()
    return [asset_out(row) for row in rows if "clicko-video-export" in (row.tags or [])]


@router.get("/library/{asset_id}/content")
def video_content(
    asset_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from sqlalchemy import select

    from ..models import Membership
    from .assets import download_asset

    membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
    try:
        asset = scoped_asset(db, membership.workspace_id, asset_id)
    except ValueError as error:
        raise HTTPException(404, "Vídeo não encontrado.") from error
    if "clicko-video-export" not in (asset.tags or []) and (asset.object_metadata or {}).get("editorialPreview") is not True:
        raise HTTPException(404, "Vídeo não encontrado.")
    response = download_asset(asset_id, db, user)
    if not request.query_params.get("download") and response.status_code != 307:
        response.headers["content-disposition"] = 'inline; filename="clicko-video.mp4"'
    return response


@router.get("/assets/{asset_id}/probe")
def media_probe(
    asset_id: str, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from .assets import assert_access

    assert_access(db, user.id, workspace_id)
    try:
        asset = scoped_asset(db, workspace_id, asset_id)
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            info = probe(path)
        return {
            "assetId": asset.id,
            "durationSeconds": float(info["format"]["duration"]),
            "streams": [
                {k: stream[k] for k in ("codec_type", "codec_name", "width", "height", "sample_rate") if k in stream}
                for stream in info["streams"]
            ],
        }
    except ValueError as error:
        raise failure(error) from error


@router.put("/documents/{document_id}/timeline")
def save_timeline(
    document_id: str,
    request: TimelineEditRequest,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return timeline_editor.save(db, owned_document(db, user.id, document_id), request, user, key)
    except ValueError as error:
        db.rollback()
        raise failure(error) from error


def dispatch(job):
    from ..tasks import execute_studio_generation

    settings = get_settings()
    enqueue_job_task(execute_studio_generation, job, isolated_queues_enabled=settings.studio_isolated_queues_enabled)


@router.post("/documents/{document_id}/render-jobs", status_code=202)
def render_job(
    document_id: str,
    request: TimelineRenderRequest,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return submit_render(db, user, document_id, request, key)


@router.post("/documents/{document_id}/assemblies", status_code=202)
def assemble_video(
    document_id: str,
    request: AssemblyRenderRequest,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return submit_render(db, user, document_id, request, key)


@router.get("/assembly-capability")
def assembly_capability(_user: User = Depends(get_current_user)):
    try:
        moneyprinterturbo.require_available()
    except ValueError:
        return {"available": False, "frameRate": moneyprinterturbo.FPS}
    return {"available": True, "frameRate": moneyprinterturbo.FPS}


@router.post("/documents/{document_id}/assembly-materials", status_code=201)
async def upload_assembly_material(
    document_id: str,
    title: str = Form(min_length=1, max_length=240),
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    document = record_to_contract(record)
    if document.content_type != "video" or document.native_editor_state:
        raise HTTPException(422, detail={"code": "moneyprinterturbo_requires_new_video_project"})
    if not (file.content_type or "").startswith(("audio/", "video/")):
        raise HTTPException(415, detail={"code": "moneyprinterturbo_material_type_mismatch"})
    return await store_upload(db, record.workspace_id, title, "studio,source", file, 1024**3)


@archive_router.get("/{document_id}/files")
def project_files(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import select

    record = owned_document(db, user.id, document_id)
    contract = record_to_contract(record)
    outputs = {entry.asset_id for entry in contract.exports}
    materials = {entry.id for entry in contract.assets}
    if contract.native_editor_state:
        materials.update(entry.asset_id for entry in contract.native_editor_state.asset_manifest)
        materials.update(entry.asset_id for entry in contract.native_editor_state.font_manifest)
    jobs = db.scalars(select(StudioGenerationJob).where(
        StudioGenerationJob.workspace_id == record.workspace_id,
        StudioGenerationJob.document_id == record.id,
        StudioGenerationJob.provider == moneyprinterturbo.PROVIDER,
    ))
    for job in jobs:
        materials.update(job.request_payload.get("assemblyChecksums", {}))
    identifiers = sorted(outputs | materials)
    rows = {row.id: row for row in db.scalars(select(LibraryAsset).where(
        LibraryAsset.workspace_id == record.workspace_id, LibraryAsset.id.in_(identifiers),
    ))}
    files = []
    for identifier in identifiers:
        row = rows.get(identifier)
        available = False
        if row and row.storage_key and row.lifecycle_status == "active":
            storage = get_object_storage(row.storage_backend or "local")
            available = row.storage_backend not in {"local", None} or storage.exists(row.storage_key)
        files.append({
            "assetId": identifier,
            "title": row.title if row else "Arquivo sem registro",
            "role": "export" if identifier in outputs else "material",
            "available": available,
        })
    return files


def submit_render(db, user, document_id, request, key):
    try:
        job, created = timeline_editor.create_render(db, owned_document(db, user.id, document_id), request, user, key)
        if created:
            try:
                dispatch(job)
            except Exception:
                job.status, job.error_code, job.error_message = (
                    "failed",
                    "queue_unavailable",
                    "O processamento não está disponível. Tente novamente.",
                )
                db.commit()
        return job_out(job)
    except ValidationError as error:
        db.rollback()
        raise HTTPException(422, detail={"code": "invalid_video_assembly"}) from error
    except ValueError as error:
        db.rollback()
        raise failure(error) from error
