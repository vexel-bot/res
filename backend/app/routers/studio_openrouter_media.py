"""Document-scoped OpenRouter video and narration API."""

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.contracts import StudioContract
from ..models import StudioGenerationJob, User
from ..security import get_current_user
from ..services.studios import openrouter_media as media
from ..services.studios.llm_connections import access
from .studios import owned_document

router = APIRouter(prefix="/studios/v1/video", tags=["openrouter-media"])


class MediaRequest(StudioContract):
    connection_id: str = Field(min_length=1, max_length=120)
    kind: Literal["video", "speech"]
    model: str = Field(min_length=1, max_length=160)
    prompt: str | None = Field(default=None, min_length=1, max_length=12000)
    text: str | None = Field(default=None, min_length=1, max_length=4000)
    voice: str | None = Field(default=None, max_length=160)
    duration_seconds: int | None = Field(default=None, ge=2, le=30)
    resolution: str = Field(default="720p", max_length=16)
    aspect_ratio: str = Field(default="16:9", max_length=16)
    generate_audio: bool = False
    production_id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    max_cost_usd: float = Field(gt=0, le=100, allow_inf_nan=False)

    @model_validator(mode="after")
    def complete(self):
        if self.kind == "video" and (not self.prompt or not self.duration_seconds):
            raise ValueError("video_prompt_and_duration_required")
        if self.kind == "speech" and (not self.text or not self.voice):
            raise ValueError("speech_text_and_voice_required")
        return self


def failure(error):
    return HTTPException(
        409 if "conflict" in str(error) or "budget" in str(error) else 422, detail={"code": str(error)}
    )


@router.get("/openrouter-models")
def models(
    workspace_id: str, connection_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    access(db, user.id, workspace_id)
    try:
        _, provider = media.provider(db, workspace_id, connection_id)
        videos, speech = provider.models()
        return {"videoModels": videos, "speechModels": speech, "balanceUsd": provider.balance()}
    except ValueError as error:
        raise failure(error) from error


@router.post("/documents/{document_id}/openrouter-media", status_code=202)
def create(
    document_id: str,
    request: MediaRequest,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    try:
        return media.create(db, record, request, user, key)
    except ValueError as error:
        workspace_id, record_id = record.workspace_id, record.id
        db.rollback()
        job = db.scalar(
            select(StudioGenerationJob).where(
                StudioGenerationJob.workspace_id == workspace_id,
                StudioGenerationJob.document_id == record_id,
                StudioGenerationJob.job_type == "external_call",
                StudioGenerationJob.idempotency_key == key,
            )
        )
        detail = {
            "code": str(error),
            "jobId": job.id if job else None,
            "requiresReconciliation": bool(job and media.out(job)["requiresReconciliation"]),
            "canDiscardPending": not job or media.out(job)["canDiscardPending"],
        }
        raise HTTPException(
            409 if "conflict" in str(error) or "budget" in str(error) else 422, detail=detail
        ) from error


@router.get("/documents/{document_id}/openrouter-media/{job_id}")
def poll(document_id: str, job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_document(db, user.id, document_id)
    job = db.get(StudioGenerationJob, job_id)
    if not job or job.workspace_id != record.workspace_id or job.document_id != record.id:
        raise HTTPException(404, "Generation not found")
    try:
        return media.poll(db, record, job)
    except ValueError as error:
        raise failure(error) from error
