from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.editor_commands import EditorCommandReceiptV1, EditorCommandV1
from ..models import User
from ..security import get_current_user
from ..services.studios.editor_commands import apply_command, inspect_editor
from .studios import owned_document

router = APIRouter(prefix="/studios/v1/documents", tags=["studio-editor-v1"])


def _error(exc):
    code = str(exc)
    return HTTPException(status_code=409 if "conflict" in code else 422, detail={"code": code})


@router.post("/{document_id}/editor/commands", response_model=EditorCommandReceiptV1)
def editor_command(document_id: str, request: EditorCommandV1,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_document(db, user.id, document_id)
    try:
        return apply_command(db, record, request, user)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/{document_id}/editor/inspection")
def editor_inspection(document_id: str, frame: int = Query(default=0, ge=0),
                      evaluation_detail: Literal["full", "summary"] = Query(default="full", alias="evaluationDetail"),
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_document(db, user.id, document_id)
    try:
        return inspect_editor(db, record, frame, evaluation_detail=evaluation_detail)
    except ValueError as exc:
        raise _error(exc) from exc
