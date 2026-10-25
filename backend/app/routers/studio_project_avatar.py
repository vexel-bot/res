"""Project avatar admission uses final narration and the signed commercial video hold."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import Field, field_validator
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..domain.studios.contracts import CreateGenerationJobRequest, StudioContract
from ..models import User
from ..security import get_current_user
from ..services.studios import project_avatar
from ..services.studios.jobs import TERMINAL_STATES, create_job, enqueue_job_task, job_out, request_cancel
from ..services.studios.kernel import create_document
from .studio_department import change, out, owned
from .studios import studio_identity_error

router = APIRouter(prefix="/studios/v1/projects", tags=["studio-project-avatar"])


class AvatarPlanRequest(StudioContract):
    performance_direction: str = Field(
        default="Plano médio, postura natural e fala clara.", min_length=3, max_length=2000
    )

    @field_validator("performance_direction", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProjectAvatarRequest(AvatarPlanRequest):
    operation: Literal["generate_avatar"]
    expected_revision: int = Field(ge=1)
    plan_digest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    document_id: str = Field(min_length=1, max_length=120)
    duration_seconds: float = Field(gt=0, le=3600)


def view(db, row, *, validate=True):
    job = project_avatar.current_job(db, row)
    asset, blocker, available = None, None, False
    if validate:
        try:
            asset = project_avatar.completed_asset(db, row)
            if (not job or job.status in TERMINAL_STATES) and row.payload.get("status") != "producing":
                project_avatar.plan(
                    db,
                    row,
                    (row.payload.get("avatar") or {}).get(
                        "performanceDirection", AvatarPlanRequest().performance_direction
                    ),
                )
                available = True
        except ValueError as error:
            blocker = str(error)
    return {
        "schemaVersion": "clicko.project-avatar.v1",
        "project": out(row),
        "canGenerate": available,
        "blocker": blocker,
        "requestKey": (row.payload.get("avatar") or {}).get("requestKey"),
        "performanceDirection": (row.payload.get("avatar") or {}).get("performanceDirection"),
        "assetId": asset.id if asset else None,
        "job": {"id": job.id, "status": job.status, "progress": job.progress, "errorCode": job.error_code}
        if job
        else None,
    }


@router.get("/{project_id}/avatar")
def get_avatar(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return view(db, owned(db, user, project_id))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/{project_id}/avatar/plan")
def plan_avatar(
    project_id: str, data: AvatarPlanRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = owned(db, user, project_id)
    try:
        if row.payload.get("status") == "producing":
            raise HTTPException(409, detail={"code": "avatar_project_producing"})
        planned = project_avatar.plan(db, row, data.performance_direction)
        return {k: v for k, v in planned.items() if k != "binding"} | {
            "performanceDirection": data.performance_direction
        }
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/{project_id}/avatar", status_code=202)
def generate_avatar(
    project_id: str,
    data: ProjectAvatarRequest,
    request: Request,
    idempotency_key: str = Header(min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = owned(db, user, project_id)
    try:
        admission = getattr(request.state, "studio_media_admission", None)
        if user.password_hash == "!session-bridge-only" and (
            not isinstance(admission, dict)
            or admission.get("key") != idempotency_key
            or admission.get("documentId") != data.document_id
            or admission.get("seconds") != data.duration_seconds
            or admission.get("operation") != "generate_avatar"
        ):
            raise ValueError("commercial_media_admission_required")
        fingerprint = project_avatar.digest(data.model_dump(by_alias=True, mode="json", exclude={"expected_revision"}))
        saved = row.payload.get("avatar") or {}
        existing = project_avatar.current_job(db, row)
        if saved.get("requestKey") == idempotency_key:
            if saved.get("requestFingerprint") != fingerprint:
                raise HTTPException(409, detail={"code": "idempotency_payload_conflict"})
            project_avatar.materials(db, row)
            return job_out(existing)
        if existing and existing.status not in TERMINAL_STATES:
            raise HTTPException(409, detail={"code": "avatar_already_running"})
        if row.payload["revision"] != data.expected_revision:
            raise HTTPException(409, detail={"code": "studio_project_conflict"})
        if row.payload.get("status") == "producing":
            raise HTTPException(409, detail={"code": "avatar_project_producing"})
        planned = project_avatar.plan(db, row, data.performance_direction)
        if (
            planned["planDigestSha256"] != data.plan_digest_sha256
            or planned["documentId"] != data.document_id
            or planned["durationSeconds"] != data.duration_seconds
        ):
            raise HTTPException(409, detail={"code": "avatar_plan_changed"})
        context = create_document(
            db,
            project_avatar.context_request(db, row, planned),
            user,
            creation_key=f"project-avatar:{data.document_id}",
            document_id=data.document_id,
            commit=False,
        )
        binding = planned["binding"]
        refs = binding["casting"]
        job, created = create_job(
            db,
            CreateGenerationJobRequest(
                workspace_id=row.workspace_id,
                document_id=context.id,
                job_type="avatar_video",
                identity_version_id=refs["identity"]["id"],
                voice_version_id=refs["voice"]["id"],
                consent_grant_id=refs["identity"]["consentGrantId"] or refs["voice"]["consentGrantId"],
                provider=binding["provider"]["provider"],
                request=binding["request"],
                correlation_id=f"department-avatar:{row.id}",
            ),
            idempotency_key,
            user,
            commit=False,
            commercial_admission=admission,
        )
        if not created:
            raise HTTPException(409, detail={"code": "avatar_request_superseded"})
        change(
            db,
            row,
            data.expected_revision,
            {
                "avatar": {
                    "requestKey": idempotency_key,
                    "requestFingerprint": fingerprint,
                    "jobId": job.id,
                    "documentId": context.id,
                    "planDigestSha256": data.plan_digest_sha256,
                    "narrationJobId": binding["narrationJobId"],
                    "directionId": row.payload["directionId"],
                    "performanceDirection": data.performance_direction,
                }
            },
        )
        from ..tasks import execute_studio_generation

        try:
            enqueue_job_task(
                execute_studio_generation, job, isolated_queues_enabled=get_settings().studio_isolated_queues_enabled
            )
        except Exception as error:
            db.refresh(job)
            if job.status == "queued":
                job.status, job.error_code, job.error_message = "failed", "queue_unavailable", type(error).__name__
                job.finished_at = datetime.now(UTC)
                db.commit()
        return job_out(job)
    except (ValueError, HTTPException) as error:
        db.rollback()
        if isinstance(error, HTTPException):
            raise
        raise studio_identity_error(error) from error


@router.post("/{project_id}/avatar/cancel")
def cancel_avatar(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = owned(db, user, project_id)
    try:
        job = project_avatar.current_job(db, row)
        if not job:
            raise HTTPException(404, detail={"code": "avatar_not_found"})
        request_cancel(db, job, "Cancelado pelo responsável pelo projeto.", user.id)
        return job_out(job)
    except ValueError as error:
        raise studio_identity_error(error) from error
