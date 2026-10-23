"""Video-only canonical timeline boundary, reusing Clicko's session and jobs."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..domain.studios.craft import CraftAICommandRequestV1
from ..domain.studios.timeline_editor import TimelineEditRequest, TimelineRenderRequest
from ..models import User
from ..providers.studios.timeline_ffmpeg import capability, probe
from ..security import get_current_user
from ..services.object_storage import get_object_storage
from ..services.studios import timeline_editor
from ..services.studios.compatibility import record_to_contract
from ..services.studios.craft import scoped_asset
from ..services.studios.jobs import enqueue_job_task, job_out
from .studios import owned_document

router = APIRouter(prefix="/studios/v1/video", tags=["video-timeline"])


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
                "editing_submission_outcome_unknown_manual_reconciliation_required"
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


@router.post("/documents/{document_id}/ai-commands")
def ai_commands(
    document_id: str,
    request: CraftAICommandRequestV1,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.studios.craft_ai import ai_commands as apply_ai

    record = owned_document(db, user.id, document_id)
    if record_to_contract(record).native_editor_state:
        raise HTTPException(422, detail={"code": "timeline_requires_canonical_video_project"})
    try:
        return apply_ai(db, record, request, user, key)
    except ValueError as error:
        db.rollback()
        raise failure(error) from error


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
    if "clicko-video-export" not in (asset.tags or []):
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
    except ValueError as error:
        db.rollback()
        raise failure(error) from error
