"""No endpoint is available outside a signed, local DEV experiment session."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.motion_gemini import MotionGeminiCancel, MotionGeminiKey, MotionGeminiSettings
from ..models import User
from ..security import get_current_user
from ..services.studios import motion_gemini as service
from .studio_agents import failure

router = APIRouter(prefix="/studios/v1/agents/motion-gemini", tags=["motion-gemini-dev"])


def invoke(request, db, user, workspace_id, operation, *args):
    service.require_dev(request)
    try:
        return operation(db, workspace_id, user, *args)
    except ValueError as exc:
        raise failure(db, exc) from exc


@router.get("")
def status(request: Request, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return invoke(request, db, user, workspace_id, service.status)


@router.put("/key")
def key(
    request: Request,
    body: MotionGeminiKey,
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return invoke(request, db, user, workspace_id, service.save_key, body.api_key.get_secret_value())


@router.delete("/key")
def remove(request: Request, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return invoke(request, db, user, workspace_id, service.remove_key)


@router.post("/test")
def test(request: Request, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return invoke(request, db, user, workspace_id, service.discover)


@router.put("")
def configure(
    request: Request,
    body: MotionGeminiSettings,
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return invoke(request, db, user, workspace_id, service.configure, body)


@router.post("/cancel/{document_id}")
def cancel(
    request: Request,
    document_id: str,
    body: MotionGeminiCancel,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    from ..models import StudioGenerationJob
    from ..services.studios.jobs import request_cancel
    from .studios import owned_document

    service.require_dev(request)
    document = owned_document(db, user.id, document_id)
    task = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.document_id == document.id,
            StudioGenerationJob.workspace_id == document.workspace_id,
            StudioGenerationJob.requested_by == user.id,
            StudioGenerationJob.job_type == "agent_plan",
            StudioGenerationJob.idempotency_key == body.request_key,
        )
    )
    if not task:
        raise failure(db, ValueError("motion_gemini_task_not_admitted"))
    request_cancel(db, task, "Cancelado pelo usuário; não aplicar o plano.", user.id)
    return {"status": task.status}
