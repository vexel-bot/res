from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..connectors.rss import RSSConnector
from ..database import get_db
from ..models import (
    BrandProfile,
    Campaign,
    CreativeDocument,
    ExternalSignal,
    FeedbackEvent,
    JobAudit,
    Membership,
    Opportunity,
    Post,
    RadarSource,
    User,
)
from ..schemas import (
    FeedbackIn,
    JobOut,
    LearningPreferenceOut,
    OpportunityOut,
    RadarSourceIn,
    RadarSourceOut,
    RadarSourceUpdate,
    RadarStateOut,
    RankRequest,
    SignalIn,
    SignalOut,
)
from ..security import get_current_user
from ..services.brand import brand_readiness
from ..services.learning import workspace_preference_profile
from ..services.radar import evergreen_suggestions, opportunity_contract, upsert_workspace_opportunities
from ..services.signals import normalize_and_store
from ..tasks import rank_workspace, sync_workspace_sources

router = APIRouter(prefix="/radar", tags=["radar"])


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    membership = db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Workspace not found")


def validate_source(source: RadarSourceIn | RadarSourceUpdate, current: RadarSource | None = None) -> None:
    feed_url = source.feed_url if source.feed_url is not None else current.feed_url if current else None
    if not feed_url:
        raise HTTPException(status_code=422, detail="RSS URL is required")
    try:
        RSSConnector(
            source.name or (current.name if current else "RSS"),
            feed_url,
            source.region or (current.region if current else "BR"),
            source.language or (current.language if current else "pt-BR"),
            source.category or (current.category if current else "general"),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/sources", response_model=list[RadarSourceOut])
def list_sources(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RadarSource]:
    assert_access(db, user.id, workspace_id)
    return list(
        db.scalars(
            select(RadarSource).where(RadarSource.workspace_id == workspace_id).order_by(RadarSource.created_at)
        ).all()
    )


@router.post("/sources", response_model=RadarSourceOut, status_code=status.HTTP_201_CREATED)
def create_source(
    data: RadarSourceIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RadarSource:
    assert_access(db, user.id, data.workspace_id)
    validate_source(data)
    source = RadarSource(**data.model_dump())
    db.add(source)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="RSS source already exists in workspace") from error
    db.refresh(source)
    return source


@router.patch("/sources/{source_id}", response_model=RadarSourceOut)
def update_source(
    source_id: str,
    data: RadarSourceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RadarSource:
    source = db.get(RadarSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="RSS source not found")
    assert_access(db, user.id, source.workspace_id)
    validate_source(data, source)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="RSS source already exists in workspace") from error
    db.refresh(source)
    return source


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    source = db.get(RadarSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="RSS source not found")
    assert_access(db, user.id, source.workspace_id)
    db.delete(source)
    db.commit()


@router.post("/sync/jobs", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def enqueue_sync_job(
    data: RankRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=120),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobOut:
    assert_access(db, user.id, data.workspace_id)
    existing = db.scalar(select(JobAudit).where(JobAudit.idempotency_key == idempotency_key))
    if existing:
        if existing.workspace_id != data.workspace_id or existing.job_type != "sync_radar_sources":
            raise HTTPException(status_code=409, detail="Idempotency key already belongs to another operation")
        return JobOut.model_validate(existing)
    audit = JobAudit(
        workspace_id=data.workspace_id,
        job_type="sync_radar_sources",
        idempotency_key=idempotency_key,
        status="queued",
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    try:
        sync_workspace_sources.delay(data.workspace_id, idempotency_key)
    except Exception as error:
        audit.status = "failed"
        audit.error = f"QueueUnavailable: {type(error).__name__}"[:2000]
        audit.finished_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=503, detail="Job queue unavailable") from error
    return JobOut.model_validate(audit)


@router.post("/rank/jobs", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def enqueue_rank_job(
    data: RankRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=120),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobOut:
    assert_access(db, user.id, data.workspace_id)
    if data.signal_ids:
        raise HTTPException(status_code=422, detail="Asynchronous ranking currently processes all valid signals")
    existing = db.scalar(select(JobAudit).where(JobAudit.idempotency_key == idempotency_key))
    if existing:
        if existing.workspace_id != data.workspace_id or existing.job_type != "rank_workspace":
            raise HTTPException(status_code=409, detail="Idempotency key already belongs to another operation")
        return JobOut.model_validate(existing)
    audit = JobAudit(
        workspace_id=data.workspace_id,
        job_type="rank_workspace",
        idempotency_key=idempotency_key,
        status="queued",
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    try:
        rank_workspace.delay(data.workspace_id, idempotency_key)
    except Exception as error:
        audit.status = "failed"
        audit.error = f"QueueUnavailable: {type(error).__name__}"[:2000]
        audit.finished_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=503, detail="Job queue unavailable") from error
    return JobOut.model_validate(audit)


@router.post("/signals", response_model=SignalOut, status_code=status.HTTP_201_CREATED)
def ingest_signal(
    data: SignalIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SignalOut:
    if not data.workspace_id:
        raise HTTPException(status_code=400, detail="Manual signals require workspaceId")
    assert_access(db, user.id, data.workspace_id)
    signal, created = normalize_and_store(db, data)
    if not created:
        raise HTTPException(status_code=409, detail="Signal already collected")
    return SignalOut.model_validate(signal)


@router.post("/rank", response_model=list[OpportunityOut])
def rank_opportunities(
    data: RankRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[OpportunityOut]:
    assert_access(db, user.id, data.workspace_id)
    try:
        opportunities, _, _ = upsert_workspace_opportunities(db, data.workspace_id, signal_ids=data.signal_ids)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Complete the brand profile before ranking") from error
    db.commit()
    for item in opportunities:
        db.refresh(item)
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == data.workspace_id))
    return [
        OpportunityOut.model_validate(opportunity_contract(db, item, brand=brand))
        for item in sorted(opportunities, key=lambda row: row.score, reverse=True)
    ]


@router.get("/opportunities", response_model=list[OpportunityOut])
def top_opportunities(
    workspace_id: str = Query(...),
    limit: int = Query(default=3, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    assert_access(db, user.id, workspace_id)
    now = datetime.now(UTC)
    rows = db.execute(
        select(Opportunity, ExternalSignal.cluster_key)
        .join(ExternalSignal, ExternalSignal.id == Opportunity.signal_id)
        .where(
            Opportunity.workspace_id == workspace_id,
            Opportunity.eligible.is_(True),
            Opportunity.publish_until > now,
        )
        .order_by(Opportunity.score.desc())
        .limit(max(50, limit * 10))
    ).all()
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == workspace_id))
    items: list[dict] = []
    seen_clusters: set[str] = set()
    for opportunity, cluster_key in rows:
        contract = opportunity_contract(db, opportunity, brand=brand, now=now)
        if contract["rejected"]:
            continue
        diversity_key = cluster_key or opportunity.signal_id
        if diversity_key in seen_clusters:
            continue
        seen_clusters.add(diversity_key)
        items.append(contract)
        if len(items) == limit:
            break
    return items


@router.get("/state", response_model=RadarStateOut)
def radar_state(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    assert_access(db, user.id, workspace_id)
    now = datetime.now(UTC)
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == workspace_id))
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    readiness = brand_readiness(brand)
    sources = list(
        db.scalars(
            select(RadarSource)
            .where(RadarSource.workspace_id == workspace_id)
            .order_by(RadarSource.created_at)
        ).all()
    )
    active_sources = [source for source in sources if source.is_active]
    last_collection = max(
        (source.last_synced_at for source in sources if source.last_synced_at),
        default=None,
    )
    next_collection = (
        (last_collection + timedelta(minutes=15))
        if last_collection and active_sources
        else (now + timedelta(minutes=15))
        if active_sources
        else None
    )
    signal_count = db.scalar(
        select(func.count(ExternalSignal.id)).where(
            ExternalSignal.workspace_id == workspace_id,
            ExternalSignal.expires_at > now,
        )
    ) or 0
    latest_job = db.scalars(
        select(JobAudit)
        .where(JobAudit.workspace_id == workspace_id, JobAudit.job_type == "sync_radar_sources")
        .order_by(JobAudit.finished_at.desc(), JobAudit.started_at.desc())
        .limit(1)
    ).first()
    opportunities = top_opportunities(workspace_id=workspace_id, limit=3, db=db, user=user)
    if readiness["status"] == "incomplete":
        state = "brand_incomplete"
        reason = "Complete os campos de maior impacto da memória da marca antes de priorizar sinais."
    elif latest_job and latest_job.status in {"queued", "running", "retrying"}:
        state = "collecting"
        reason = "A coleta automática está em andamento."
    elif opportunities:
        state = "ready"
        reason = "Foram encontradas pontes naturais, atuais e auditáveis para a marca."
    elif not active_sources and signal_count == 0:
        state = "no_sources"
        reason = "Nenhuma fonte ativa ou sinal válido está disponível para coleta."
    elif active_sources and all(source.last_status == "never" for source in active_sources):
        state = "awaiting_first_collection"
        reason = "As fontes estão configuradas e aguardam a primeira coleta automática."
    elif active_sources and all(source.last_status == "error" for source in active_sources):
        state = "collection_error"
        reason = "A última coleta falhou em todas as fontes ativas; nenhuma tendência foi inventada."
    else:
        state = "insufficient_signals"
        reason = "Os sinais atuais não formam uma conexão forte e segura com a marca."
    return {
        "workspace_id": workspace_id,
        "state": state,
        "reason": reason,
        "last_collection_at": last_collection,
        "next_collection_at": next_collection,
        "collection_status": latest_job.status if latest_job else "never",
        "sources_used": [
            {
                "id": source.id,
                "name": source.name,
                "url": source.feed_url,
                "category": source.category,
                "status": source.last_status,
                "lastSyncedAt": source.last_synced_at,
                "lastItemCount": source.last_item_count,
                "error": source.last_error,
            }
            for source in active_sources
        ],
        "signal_count": signal_count,
        "brand_readiness": readiness,
        "evergreen_suggestions": evergreen_suggestions(brand) if not opportunities else [],
        "opportunities": opportunities,
    }


@router.post("/feedback", status_code=status.HTTP_204_NO_CONTENT)
def record_feedback(
    data: FeedbackIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    assert_access(db, user.id, data.workspace_id)
    links = (
        (Opportunity, data.opportunity_id, "Opportunity"),
        (Campaign, data.campaign_id, "Campaign"),
        (Post, data.content_id, "Content"),
        (CreativeDocument, data.creative_document_id, "Creative"),
    )
    for model, resource_id, label in links:
        if resource_id and not db.scalar(
            select(model.id).where(model.id == resource_id, model.workspace_id == data.workspace_id)
        ):
            raise HTTPException(status_code=404, detail=f"{label} not found")
    db.add(FeedbackEvent(**data.model_dump(), user_id=user.id))
    db.commit()


@router.get("/preferences", response_model=LearningPreferenceOut)
def get_preferences(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    assert_access(db, user.id, workspace_id)
    return workspace_preference_profile(db, workspace_id).as_dict()
