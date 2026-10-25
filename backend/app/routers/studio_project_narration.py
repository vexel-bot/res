"""Narration is a durable project material, bound to the selected library voice."""

from datetime import UTC, datetime
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..domain.studios.contracts import StudioContract
from ..models import StudioGenerationJob, User
from ..security import get_current_user
from ..services.studios.cast_speech import create_selected_speech_job, selected_speech, selected_speech_asset
from ..services.studios.casting import resolve_cast
from ..services.studios.jobs import TERMINAL_STATES, enqueue_job_task, request_cancel
from .studio_department import change, out, owned
from .studios import studio_identity_error

router = APIRouter(prefix="/studios/v1/projects", tags=["studio-project-narration"])


class NarrationDraftRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class NarrationRequest(NarrationDraftRequest):
    request_key: str = Field(min_length=8, max_length=80)


def reference(db, row):
    refs = resolve_cast(db, row.workspace_id, row.payload.get("identityVersionId"), row.payload.get("voiceVersionId"))
    voice = (row.payload.get("casting") or {}).get("voice")
    if not voice:
        raise ValueError("voice_version_required")
    if voice != refs.get("voice"):
        raise ValueError("cast_version_reference_mismatch")
    return voice


def current_job(db, row):
    narration = row.payload.get("narration") or {}
    job = db.get(StudioGenerationJob, narration.get("jobId")) if narration.get("jobId") else None
    if narration.get("jobId") and (
        not job or job.workspace_id != row.workspace_id or job.correlation_id != f"department-narration:{row.id}"
    ):
        raise ValueError("production_voice_job_conflict")
    return job


def view(db, row, *, validate=True):
    narration = row.payload.get("narration") or {}
    job = current_job(db, row)
    default_script = ""
    direction = next((d for d in row.payload["directions"] if d["id"] == row.payload.get("directionId")), None)
    if direction:
        default_script = "\n\n".join(
            dict.fromkeys(
                text.strip() for text in [direction["opening"], *direction["beats"], direction["cta"]] if text.strip()
            )
        )[:4000]
    available, blocker, asset = False, None, None
    if validate:
        ref = reference(db, row)
        if job:
            asset = selected_speech_asset(db, job, ref, narration["text"])
        try:
            selected_speech(db, row.workspace_id, ref)
            available = direction is not None and row.payload.get("status") != "producing"
            if not direction:
                blocker = "narration_direction_required"
            elif row.payload.get("status") == "producing":
                blocker = "narration_project_producing"
        except ValueError as error:
            blocker = str(error)
    return {
        "schemaVersion": "clicko.project-narration.v1",
        "project": out(row),
        "text": row.payload.get("narrationDraft") or narration.get("text", default_script),
        "generatedText": narration.get("text") if asset else None,
        "requestKey": narration.get("requestKey"),
        "canGenerate": available,
        "blocker": blocker,
        "assetId": asset.id if asset else None,
        "job": {"id": job.id, "status": job.status, "progress": job.progress, "errorCode": job.error_code}
        if job
        else None,
    }


@router.get("/{project_id}/narration")
def get_narration(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return view(db, owned(db, user, project_id))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/{project_id}/narration", status_code=202)
def create_narration(
    project_id: str, data: NarrationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = owned(db, user, project_id)
    try:
        ref = reference(db, row)
        previous = row.payload.get("narration") or {}
        existing = current_job(db, row)
        if previous.get("requestKey") == data.request_key:
            if previous.get("text") != data.text:
                raise HTTPException(409, detail={"code": "idempotency_payload_conflict"})
            return view(db, row)
        if existing and existing.status not in TERMINAL_STATES:
            raise HTTPException(409, detail={"code": "narration_already_running"})
        if not row.payload.get("directionId"):
            raise ValueError("narration_direction_required")
        if row.payload.get("status") == "producing":
            raise HTTPException(409, detail={"code": "narration_project_producing"})
        if row.payload["revision"] != data.expected_revision:
            raise HTTPException(409, detail={"code": "studio_project_conflict"})
        selection = selected_speech(db, row.workspace_id, ref)
        job, created = create_selected_speech_job(
            db,
            selection,
            data.text,
            user,
            workspace_id=row.workspace_id,
            document_id=row.payload.get("documentId"),
            key=f"department-narration:{row.id}:{data.request_key}",
            correlation_id=f"department-narration:{row.id}",
            commit=False,
        )
        if not created:
            raise HTTPException(409, detail={"code": "narration_request_superseded"})
        row = change(
            db,
            row,
            data.expected_revision,
            {
                "narrationDraft": None,
                "narration": {
                    "requestKey": data.request_key,
                    "text": data.text,
                    "scriptDigestSha256": sha256(data.text.encode()).hexdigest(),
                    "voice": ref,
                    "jobId": job.id,
                },
            },
        )
        if created:
            from ..tasks import execute_studio_generation

            try:
                enqueue_job_task(
                    execute_studio_generation,
                    job,
                    isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
                )
            except Exception as error:
                db.refresh(job)
                if job.status == "queued":
                    job.status, job.error_code, job.error_message = "failed", "queue_unavailable", type(error).__name__
                    job.finished_at = datetime.now(UTC)
                    db.commit()
        return view(db, row)
    except ValueError as error:
        db.rollback()
        raise studio_identity_error(error) from error


@router.patch("/{project_id}/narration")
def save_narration_draft(
    project_id: str, data: NarrationDraftRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = owned(db, user, project_id)
    try:
        reference(db, row)
        if row.payload.get("narrationDraft") == data.text:
            return view(db, row)
        job = current_job(db, row)
        if job and job.status not in TERMINAL_STATES:
            raise HTTPException(409, detail={"code": "narration_already_running"})
        if row.payload.get("status") == "producing":
            raise HTTPException(409, detail={"code": "narration_project_producing"})
        row = change(db, row, data.expected_revision, {"narrationDraft": data.text})
        return view(db, row)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/{project_id}/narration/cancel")
def cancel_narration(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = owned(db, user, project_id)
    try:
        job = current_job(db, row)
        if not job:
            raise HTTPException(404, detail={"code": "narration_not_found"})
        request_cancel(db, job, "Cancelado pelo responsável pelo projeto.", user.id)
        # Revocation must never prevent the owner from cancelling a job.
        return view(db, row, validate=False)
    except ValueError as error:
        raise studio_identity_error(error) from error
