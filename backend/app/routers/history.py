from copy import deepcopy
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Campaign, CreativeDocument, FeedbackEvent, LibraryAsset, Membership, Post, User, utcnow
from ..schemas import (
    CampaignOut,
    CreativeDocumentOut,
    HistoryItemOut,
    HistoryReuseIn,
    PostOut,
)
from ..security import get_current_user
from ..serializers import post_out
from .campaigns import campaign_out, campaign_snapshot
from .creatives import creative_out

router = APIRouter(prefix="/history", tags=["history"])


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Workspace not found")


def item_matches(item_type: str | None, *accepted: str) -> bool:
    return item_type is None or item_type in accepted


@router.get("", response_model=list[HistoryItemOut])
def search_history(
    workspace_id: str = Query(...),
    query: str = Query(default="", max_length=160),
    item_type: str | None = Query(default=None, pattern="^(post|campaign|creative|template|asset)$"),
    limit: int = Query(default=60, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[HistoryItemOut]:
    assert_access(db, user.id, workspace_id)
    pattern = f"%{query.strip()}%"
    items: list[HistoryItemOut] = []
    per_type_limit = min(200, limit * 3)

    if item_matches(item_type, "post"):
        statement = select(Post).where(Post.workspace_id == workspace_id)
        if query.strip():
            statement = statement.where(or_(Post.title.ilike(pattern), Post.copy.ilike(pattern)))
        for post in db.scalars(statement.order_by(Post.updated_at.desc()).limit(per_type_limit)).all():
            items.append(
                HistoryItemOut(
                    id=f"post:{post.id}",
                    resource_id=post.id,
                    workspace_id=workspace_id,
                    item_type="post",
                    title=post.title,
                    snippet=(post.copy or "Sem texto")[:320],
                    tags=[post.platform, post.format, post.status],
                    campaign_id=post.campaign_id,
                    reusable=True,
                    version_count=len(post.versions or []),
                    created_at=post.created_at,
                    updated_at=post.updated_at,
                )
            )

    if item_matches(item_type, "campaign"):
        statement = select(Campaign).where(Campaign.workspace_id == workspace_id)
        if query.strip():
            statement = statement.where(Campaign.title.ilike(pattern))
        for campaign in db.scalars(statement.order_by(Campaign.updated_at.desc()).limit(per_type_limit)).all():
            strategy = campaign.strategy or {}
            brief = campaign.brief or {}
            items.append(
                HistoryItemOut(
                    id=f"campaign:{campaign.id}",
                    resource_id=campaign.id,
                    workspace_id=workspace_id,
                    item_type="campaign",
                    title=campaign.title,
                    snippet=str(strategy.get("centralMessage") or brief.get("objective") or "Sem resumo")[:320],
                    tags=[
                        str(strategy.get("status") or "draft"),
                        *[str(value) for value in strategy.get("channels") or []],
                    ],
                    campaign_id=campaign.id,
                    reusable=True,
                    version_count=len(campaign.versions or []),
                    decision_count=len(campaign.decisions or []),
                    created_at=campaign.created_at,
                    updated_at=campaign.updated_at,
                )
            )

    if item_matches(item_type, "creative", "template"):
        statement = select(CreativeDocument).where(CreativeDocument.workspace_id == workspace_id)
        if item_type == "creative":
            statement = statement.where(CreativeDocument.kind == "document")
        elif item_type == "template":
            statement = statement.where(CreativeDocument.kind == "template")
        if query.strip():
            statement = statement.where(CreativeDocument.title.ilike(pattern))
        for creative in db.scalars(statement.order_by(CreativeDocument.updated_at.desc()).limit(per_type_limit)).all():
            canvas = creative.document or {}
            creative_type = "template" if creative.kind == "template" else "creative"
            items.append(
                HistoryItemOut(
                    id=f"{creative_type}:{creative.id}",
                    resource_id=creative.id,
                    workspace_id=workspace_id,
                    item_type=creative_type,
                    title=creative.title,
                    snippet=(
                        f"{canvas.get('width', '?')} × {canvas.get('height', '?')} px · "
                        f"{len(canvas.get('layers') or [])} camadas"
                    ),
                    tags=[creative.kind, f"v{creative.version}", "creative-v1"],
                    campaign_id=creative.campaign_id,
                    reusable=True,
                    version_count=1 + len(creative.versions or []),
                    created_at=creative.created_at,
                    updated_at=creative.updated_at,
                )
            )

    if item_matches(item_type, "asset"):
        statement = select(LibraryAsset).where(LibraryAsset.workspace_id == workspace_id)
        if query.strip():
            statement = statement.where(LibraryAsset.title.ilike(pattern))
        for asset in db.scalars(statement.order_by(LibraryAsset.updated_at.desc()).limit(per_type_limit)).all():
            items.append(
                HistoryItemOut(
                    id=f"asset:{asset.id}",
                    resource_id=asset.id,
                    workspace_id=workspace_id,
                    item_type="asset",
                    title=asset.title,
                    snippet="Ativo privado" if asset.storage_key else "Referência da biblioteca",
                    tags=[asset.asset_type, *(asset.tags or [])],
                    campaign_id=asset.campaign_id,
                    reusable=False,
                    created_at=asset.created_at,
                    updated_at=asset.updated_at,
                )
            )

    items.sort(key=lambda item: item.updated_at, reverse=True)
    return items[:limit]


@router.post("/posts/{post_id}/reuse", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def reuse_post(
    post_id: str,
    data: HistoryReuseIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PostOut:
    source = db.get(Post, post_id)
    if not source:
        raise HTTPException(status_code=404, detail="Post not found")
    assert_access(db, user.id, source.workspace_id)
    post = Post(
        workspace_id=source.workspace_id,
        title=(data.title or f"{source.title} — cópia").strip(),
        platform=source.platform,
        format=source.format,
        copy=source.copy,
        hashtags=deepcopy(source.hashtags or []),
        image_url=source.image_url,
        video_url=source.video_url,
        slides=deepcopy(source.slides),
        status="draft",
        author=user.name,
        campaign_id=source.campaign_id,
        strategy_id=source.strategy_id,
        brain_revision=source.brain_revision,
        objective=source.objective,
        origin="manual",
        versions=[],
        metrics={},
    )
    db.add(post)
    db.flush()
    post.versions = [
        {
            "id": str(uuid4()),
            "number": 1,
            "label": "Reutilizada do histórico",
            "author": user.name,
            "createdAt": utcnow().isoformat(),
            "title": post.title,
            "copy": post.copy,
        }
    ]
    db.add(
        FeedbackEvent(
            workspace_id=post.workspace_id,
            campaign_id=post.campaign_id,
            content_id=post.id,
            user_id=user.id,
            event_type="reused",
            payload={"sourcePostId": source.id},
        )
    )
    db.commit()
    db.refresh(post)
    return post_out(post)


@router.post("/campaigns/{campaign_id}/reuse", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def reuse_campaign(
    campaign_id: str,
    data: HistoryReuseIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    source = db.get(Campaign, campaign_id)
    if not source:
        raise HTTPException(status_code=404, detail="Campaign not found")
    assert_access(db, user.id, source.workspace_id)
    strategy = deepcopy(source.strategy or {})
    strategy["status"] = "draft"
    campaign = Campaign(
        workspace_id=source.workspace_id,
        opportunity_id=source.opportunity_id,
        title=(data.title or f"{source.title} — cópia").strip(),
        brief=deepcopy(source.brief),
        strategy=strategy,
        prompt_version=source.prompt_version,
        provider_trace=deepcopy(source.provider_trace),
        versions=[],
        decisions=[],
    )
    db.add(campaign)
    db.flush()
    campaign.versions = [campaign_snapshot(campaign, "Reutilizada do histórico", 1)]
    db.add(
        FeedbackEvent(
            workspace_id=campaign.workspace_id,
            opportunity_id=campaign.opportunity_id,
            campaign_id=campaign.id,
            user_id=user.id,
            event_type="reused",
            payload={"sourceCampaignId": source.id},
        )
    )
    db.commit()
    db.refresh(campaign)
    return campaign_out(campaign)


@router.post("/creatives/{creative_id}/reuse", response_model=CreativeDocumentOut, status_code=status.HTTP_201_CREATED)
def reuse_creative(
    creative_id: str,
    data: HistoryReuseIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreativeDocumentOut:
    source = db.get(CreativeDocument, creative_id)
    if not source:
        raise HTTPException(status_code=404, detail="Creative not found")
    assert_access(db, user.id, source.workspace_id)
    creative = CreativeDocument(
        workspace_id=source.workspace_id,
        campaign_id=source.campaign_id,
        kind="document",
        title=(data.title or f"{source.title} — cópia").strip(),
        document=deepcopy(source.document),
        version=1,
        versions=[],
    )
    db.add(creative)
    db.flush()
    db.add(
        FeedbackEvent(
            workspace_id=creative.workspace_id,
            campaign_id=creative.campaign_id,
            creative_document_id=creative.id,
            user_id=user.id,
            event_type="reused",
            payload={"sourceCreativeId": source.id},
        )
    )
    db.commit()
    db.refresh(creative)
    return creative_out(creative)
