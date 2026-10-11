"""Owner/admin-only experimental engine qualification endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..dependencies import get_current_user
from ..domain.studios.engine_qualification import (
    BindEngineCaseV1,
    CreateEngineCampaignV1,
    CreateEngineComparisonV1,
    EngineComparisonReviewV1,
    Language,
    RegisterEngineTrialV1,
)
from ..models import User
from ..services.studios import engine_qualification as service

router = APIRouter()


def guard(db, user, workspace_id):
    from .studios import assert_governance_access

    if not get_settings().studio_alight_motion_enabled:
        raise HTTPException(status_code=404, detail={"code": "engine_experiment_disabled"})
    assert_governance_access(db, user.id, workspace_id)


def _call(function, *args):
    try:
        return function(*args)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not_found" in str(exc) else 409, detail={"code": str(exc)}) from exc


@router.get("/workspaces/{workspace_id}/render-engines")
def capabilities(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    guard(db, user, workspace_id)
    return service.engine_capabilities()


@router.get("/workspaces/{workspace_id}/engine-campaigns")
def campaigns(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    guard(db, user, workspace_id)
    return service.list_campaigns(db, workspace_id)


@router.post("/workspaces/{workspace_id}/engine-campaigns", status_code=201)
def create(
    workspace_id: str,
    request: CreateEngineCampaignV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    guard(db, user, workspace_id)
    return service.create_campaign(db, workspace_id, request, user)


@router.get("/workspaces/{workspace_id}/engine-campaigns/{campaign_id}")
def campaign(
    workspace_id: str, campaign_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    guard(db, user, workspace_id)
    return _call(service.campaign_projection, db, workspace_id, campaign_id)


@router.post("/workspaces/{workspace_id}/engine-campaigns/{campaign_id}/promote")
def promote(workspace_id: str, campaign_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    guard(db, user, workspace_id)
    return _call(service.promote_campaign, db, workspace_id, campaign_id, user)


@router.post("/workspaces/{workspace_id}/engine-campaigns/{campaign_id}/cases")
def bind(
    workspace_id: str,
    campaign_id: str,
    request: BindEngineCaseV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    guard(db, user, workspace_id)
    return _call(service.bind_case, db, workspace_id, campaign_id, request, user)


@router.post("/workspaces/{workspace_id}/engine-campaigns/{campaign_id}/trials")
def trial(
    workspace_id: str,
    campaign_id: str,
    request: RegisterEngineTrialV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    guard(db, user, workspace_id)
    return _call(service.register_trial, db, workspace_id, campaign_id, request, user)


@router.get("/workspaces/{workspace_id}/engine-campaigns/{campaign_id}/candidates")
def candidates(
    workspace_id: str,
    campaign_id: str,
    language: Language,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    guard(db, user, workspace_id)
    return _call(service.comparison_candidates, db, workspace_id, campaign_id, language)


@router.post("/workspaces/{workspace_id}/engine-campaigns/{campaign_id}/comparisons", status_code=201)
def compare(
    workspace_id: str,
    campaign_id: str,
    request: CreateEngineComparisonV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    guard(db, user, workspace_id)
    return _call(service.create_comparison, db, workspace_id, campaign_id, request, user)


@router.get("/workspaces/{workspace_id}/engine-campaigns/{campaign_id}/comparisons/{session_id}")
def comparison(
    workspace_id: str,
    campaign_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    guard(db, user, workspace_id)
    return _call(service.comparison_projection, db, workspace_id, campaign_id, session_id)


@router.post("/workspaces/{workspace_id}/engine-campaigns/{campaign_id}/comparisons/{session_id}/review")
def review(
    workspace_id: str,
    campaign_id: str,
    session_id: str,
    request: EngineComparisonReviewV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    guard(db, user, workspace_id)
    return _call(service.review_comparison, db, workspace_id, campaign_id, session_id, request, user)
