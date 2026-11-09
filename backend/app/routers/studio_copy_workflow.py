"""Authenticated product and copy preparation. No model invocation routes."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.contracts import StudioContract
from ..models import User
from ..security import get_current_user
from ..services.studios import ad_copy_workflow as workflow
from .studio_department import owned
from .studios import owned_document

router = APIRouter(prefix="/studios/v1/copy", tags=["ad-copy-workflow"])


class CopyRequest(StudioContract):
    expected_revision: int = Field(ge=0)
    request_key: str = Field(min_length=8, max_length=80)
    status: Literal["draft", "in_review", "changes_requested", "approved"] = "draft"
    data: dict[str, str] = Field(default_factory=dict)
    checks: dict[str, bool] = Field(default_factory=dict)

    @field_validator("data")
    @classmethod
    def bounded_data(cls, data):
        if (
            not set(data) <= set(workflow.FIELDS)
            or any(len(value) > 6000 for value in data.values())
            or sum(map(len, data.values())) > 40000
        ):
            raise ValueError("copy_fields_invalid")
        return data

    @field_validator("checks")
    @classmethod
    def known_checks(cls, checks):
        if not set(checks) <= set(workflow.CHECKS):
            raise ValueError("copy_checks_invalid")
        return checks


def target(db, user, kind, identifier):
    return owned_document(db, user.id, identifier) if kind == "document" else owned(db, user, identifier)


@router.get("/{kind}/{identifier}")
def get_copy(
    kind: Literal["project", "document"],
    identifier: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = target(db, user, kind, identifier)
    return workflow.view(db, record.workspace_id, kind, identifier)


@router.put("/{kind}/{identifier}")
def save_copy(
    kind: Literal["project", "document"],
    identifier: str,
    request: CopyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = target(db, user, kind, identifier)
    try:
        return workflow.save(db, record.workspace_id, kind, identifier, request, user)
    except ValueError as error:
        db.rollback()
        raise HTTPException(409 if "conflict" in str(error) else 422, detail={"code": str(error)}) from error
