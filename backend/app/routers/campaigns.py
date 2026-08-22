from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BrandProfile, Campaign, ExternalSignal, FeedbackEvent, Membership, Opportunity, Post, User, utcnow
from ..schemas import (
    CampaignDecisionIn,
    CampaignIn,
    CampaignOut,
    CampaignPiecesIn,
    CampaignUpdate,
    CampaignVersionIn,
    PostOut,
)
from ..security import get_current_user
from ..serializers import post_out
from ..services.campaigns import build_campaign_strategy

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def campaign_snapshot(item: Campaign, label: str, number: int | None = None) -> dict:
    versions = item.versions or []
    return {
        "id": str(uuid4()),
        "number": number or max((int(version.get("number", 0)) for version in versions), default=0) + 1,
        "label": label,
        "createdAt": utcnow().isoformat(),
        "title": item.title,
        "brief": item.brief,
        "strategy": item.strategy,
        "promptVersion": item.prompt_version,
        "providerTrace": item.provider_trace,
    }


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Workspace not found")


def campaign_out(item: Campaign) -> CampaignOut:
    brief = item.brief or {}
    strategy = item.strategy or {}
    return CampaignOut(
        id=item.id,
        workspace_id=item.workspace_id,
        opportunity_id=item.opportunity_id,
        origin_context=brief.get("originContext", {}),
        name=item.title,
        objective=brief.get("objective", ""),
        start_date=brief.get("startDate", ""),
        end_date=brief.get("endDate", ""),
        budget=brief.get("budget", ""),
        products=brief.get("products", ""),
        audience=brief.get("audience", ""),
        offer=brief.get("offer", ""),
        promise=brief.get("promise", ""),
        proof=brief.get("proof", ""),
        emotion=brief.get("emotion", ""),
        constraints=brief.get("constraints", ""),
        formats=brief.get("formats", []),
        format_suggestions=strategy.get("formatSuggestions", []),
        cta=brief.get("cta", ""),
        important_dates=brief.get("importantDates", ""),
        kpis=strategy.get("kpis", []),
        channels=strategy.get("channels", []),
        funnel=strategy.get("funnel", ""),
        ctas=strategy.get("ctas", []),
        execution_plan=strategy.get("executionPlan", []),
        big_idea=strategy.get("bigIdea", ""),
        central_message=strategy.get("centralMessage", ""),
        angles=strategy.get("angles", []),
        hooks=strategy.get("hooks", []),
        narrative_sequence=strategy.get("narrativeSequence", []),
        creative_matrix=strategy.get("creativeMatrix", []),
        status=strategy.get("status", "draft"),
        brain_revision=strategy.get("brainRevision", 1),
        versions=item.versions or [],
        decisions=item.decisions or [],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CampaignOut]:
    assert_access(db, user.id, workspace_id)
    items = db.scalars(
        select(Campaign).where(Campaign.workspace_id == workspace_id).order_by(Campaign.created_at.desc())
    ).all()
    return [campaign_out(item) for item in items]


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(
    data: CampaignIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    assert_access(db, user.id, data.workspace_id)
    opportunity = None
    if data.opportunity_id:
        opportunity = db.scalar(
            select(Opportunity).where(
                Opportunity.id == data.opportunity_id,
                Opportunity.workspace_id == data.workspace_id,
            )
        )
        if not opportunity:
            raise HTTPException(status_code=422, detail="Opportunity does not belong to workspace")
    brand_profile = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == data.workspace_id))
    if not brand_profile:
        raise HTTPException(status_code=422, detail="Workspace has no brand profile")
    brand_context = dict((brand_profile.watchlist or {}).get("brain", {}))
    brand_context["primaryColor"] = brand_profile.primary_color
    if opportunity:
        signal = db.get(ExternalSignal, opportunity.signal_id)
        products = [
            str(product.get("name") or product.get("title") or "").strip()
            for product in brand_profile.products or []
            if isinstance(product, dict) and (product.get("name") or product.get("title"))
        ]
        product = data.products.strip() or (products[0] if products else str(brand_context.get("products") or ""))
        audience = data.audience.strip() or brand_profile.target_audience or str(brand_context.get("audience") or "")
        risks = " ".join(opportunity.risks or [])
        origin_context = {
            "type": "opportunity",
            "opportunityId": opportunity.id,
            "signalId": opportunity.signal_id,
            "event": opportunity.event_summary,
            "connection": opportunity.bridge,
            "product": product,
            "audience": audience,
            "objective": opportunity.objective,
            "hook": opportunity.hook,
            "publishUntil": opportunity.publish_until.isoformat(),
            "risks": opportunity.risks or [],
            "evidence": opportunity.evidence or [],
            "source": {
                "name": signal.source if signal else "",
                "url": signal.url if signal else "",
                "publishedAt": signal.published_at.isoformat() if signal else None,
                "collectedAt": signal.collected_at.isoformat() if signal else None,
            },
        }
        data = data.model_copy(
            update={
                "objective": data.objective or opportunity.objective,
                "products": product,
                "audience": audience,
                "constraints": data.constraints or risks,
                "important_dates": data.important_dates or opportunity.publish_until.isoformat(),
                "formats": data.formats or ["post", "carousel", "ad", "ugc-script"],
                "hooks": data.hooks or [opportunity.hook],
                "big_idea": data.big_idea or opportunity.title,
                "central_message": data.central_message or opportunity.bridge,
                "angles": data.angles
                or [
                    f"O que o acontecimento muda para {audience}",
                    f"Como {product or 'a marca'} se conecta ao contexto sem oportunismo",
                    "Cuidados, limites e próxima ação recomendada",
                ],
                "narrative_sequence": data.narrative_sequence
                or [
                    opportunity.event_summary,
                    opportunity.bridge,
                    opportunity.hook,
                    data.cta or "Apresentar a próxima ação com clareza",
                ],
                "origin_context": origin_context,
            }
        )
    item = Campaign(
        workspace_id=data.workspace_id,
        opportunity_id=data.opportunity_id,
        title=data.name.strip(),
        brief={
            "objective": data.objective,
            "startDate": data.start_date,
            "endDate": data.end_date,
            "budget": data.budget,
            "products": data.products,
            "audience": data.audience,
            "offer": data.offer,
            "promise": data.promise,
            "proof": data.proof,
            "emotion": data.emotion,
            "constraints": data.constraints,
            "formats": data.formats,
            "originContext": data.origin_context,
            "cta": data.cta,
            "importantDates": data.important_dates,
        },
        strategy=build_campaign_strategy(data, brand_context),
        prompt_version="campaign-planner-v1",
        provider_trace={"provider": "deterministic", "model": "campaign-planner-v1"},
        versions=[],
        decisions=[],
    )
    db.add(item)
    db.flush()
    item.versions = [campaign_snapshot(item, "Versão inicial", 1)]
    if item.opportunity_id:
        db.add(
            FeedbackEvent(
                workspace_id=item.workspace_id,
                opportunity_id=item.opportunity_id,
                campaign_id=item.id,
                user_id=user.id,
                event_type="chosen",
                payload={"campaignId": item.id},
            )
        )
    db.commit()
    db.refresh(item)
    return campaign_out(item)


@router.post("/{campaign_id}/pieces", response_model=list[PostOut])
def create_campaign_pieces(
    campaign_id: str,
    data: CampaignPiecesIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PostOut]:
    item = db.get(Campaign, campaign_id)
    if not item:
        raise HTTPException(status_code=404, detail="Campaign not found")
    assert_access(db, user.id, item.workspace_id)
    strategy = item.strategy or {}
    matrix = strategy.get("creativeMatrix") or []
    allowed = set(data.formats)
    existing_posts = list(
        db.scalars(select(Post).where(Post.campaign_id == item.id, Post.workspace_id == item.workspace_id)).all()
    )
    existing_formats = {post.format for post in existing_posts}
    existing_piece_keys = {
        str(version.get("pieceKey"))
        for post in existing_posts
        for version in (post.versions or [])[:1]
        if version.get("pieceKey")
    }
    created: list[Post] = []
    created_piece_keys: dict[int, str] = {}
    for index, piece in enumerate(matrix):
        requested_format = str(piece.get("format") or "post")
        piece_key = str(piece.get("pieceKey") or "")
        if allowed and requested_format not in allowed:
            continue
        post_format = "script" if requested_format in {"ugc", "ugc-script"} else requested_format
        if (piece_key and piece_key in existing_piece_keys) or (not piece_key and post_format in existing_formats):
            continue
        variant_suffix = f" {piece.get('variant')}" if piece_key else ""
        narrative = [str(value) for value in piece.get("storytelling") or strategy.get("narrativeSequence") or []]
        hook = str(piece.get("hook") or "")
        promise = str(piece.get("promise") or "")
        proof = str((item.brief or {}).get("proof") or "")
        cta = str(piece.get("cta") or "")
        copy = "\n\n".join(value for value in [hook, promise, proof, cta] if value)
        slides = None
        if post_format == "carousel":
            slides = [
                {"slideNumber": slide_index + 1, "headline": step, "text": ""}
                for slide_index, step in enumerate(narrative)
            ]
        post = Post(
            workspace_id=item.workspace_id,
            title=f"{item.title} — {requested_format}{variant_suffix}",
            platform=(strategy.get("channels") or ["instagram"])[
                index % len(strategy.get("channels") or ["instagram"])
            ],
            format=post_format,
            copy=copy,
            hashtags=[],
            slides=slides,
            status="draft",
            author=user.name,
            campaign_id=item.id,
            strategy_id=item.id,
            brain_revision=strategy.get("brainRevision"),
            objective=(item.brief or {}).get("objective"),
            origin="strategy",
            versions=[{"number": 1, "label": "Rascunho estruturado", "copy": copy, "pieceKey": piece_key}],
        )
        db.add(post)
        created.append(post)
        created_piece_keys[id(post)] = piece_key
        existing_formats.add(post_format)
        if piece_key:
            existing_piece_keys.add(piece_key)
    db.flush()
    for post in created:
        post.versions = [
            {
                "id": str(uuid4()),
                "number": 1,
                "label": "Rascunho estruturado",
                "author": post.author,
                "createdAt": utcnow().isoformat(),
                "title": post.title,
                "copy": post.copy,
                "hashtags": post.hashtags,
                "slides": post.slides,
                "pieceKey": created_piece_keys[id(post)],
            }
        ]
        db.add(
            FeedbackEvent(
                workspace_id=item.workspace_id,
                opportunity_id=item.opportunity_id,
                campaign_id=item.id,
                content_id=post.id,
                user_id=user.id,
                event_type="generated",
                payload={"format": post.format, "origin": "strategy"},
            )
        )
    db.commit()
    for post in created:
        db.refresh(post)
    return [post_out(post) for post in created]


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    item = db.get(Campaign, campaign_id)
    if not item:
        raise HTTPException(status_code=404, detail="Campaign not found")
    assert_access(db, user.id, item.workspace_id)
    changes = data.model_dump(exclude_unset=True)
    has_changes = bool(changes)
    if "name" in changes:
        item.title = changes.pop("name").strip()
    brief = dict(item.brief or {})
    strategy = dict(item.strategy or {})
    brief_keys = {
        "objective": "objective",
        "start_date": "startDate",
        "end_date": "endDate",
        "budget": "budget",
        "products": "products",
        "audience": "audience",
        "offer": "offer",
        "promise": "promise",
        "proof": "proof",
        "emotion": "emotion",
        "constraints": "constraints",
        "formats": "formats",
        "origin_context": "originContext",
        "cta": "cta",
        "important_dates": "importantDates",
    }
    strategy_keys = {
        "kpis": "kpis",
        "channels": "channels",
        "funnel": "funnel",
        "ctas": "ctas",
        "execution_plan": "executionPlan",
        "big_idea": "bigIdea",
        "central_message": "centralMessage",
        "angles": "angles",
        "hooks": "hooks",
        "narrative_sequence": "narrativeSequence",
        "creative_matrix": "creativeMatrix",
        "format_suggestions": "formatSuggestions",
        "status": "status",
    }
    for key, target in brief_keys.items():
        if key in changes:
            brief[target] = changes[key]
    for key, target in strategy_keys.items():
        if key in changes:
            strategy[target] = changes[key]
    item.brief = brief
    item.strategy = strategy
    if has_changes:
        versions = list(item.versions or [])
        versions.append(campaign_snapshot(item, "Alteração salva"))
        item.versions = versions[-50:]
    db.commit()
    db.refresh(item)
    return campaign_out(item)


@router.post("/{campaign_id}/versions", response_model=CampaignOut)
def save_campaign_version(
    campaign_id: str,
    data: CampaignVersionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    item = db.get(Campaign, campaign_id)
    if not item:
        raise HTTPException(status_code=404, detail="Campaign not found")
    assert_access(db, user.id, item.workspace_id)
    versions = list(item.versions or [])
    versions.append(campaign_snapshot(item, data.label))
    item.versions = versions[-50:]
    db.commit()
    db.refresh(item)
    return campaign_out(item)


@router.post("/{campaign_id}/versions/{version_number}/restore", response_model=CampaignOut)
def restore_campaign_version(
    campaign_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    item = db.get(Campaign, campaign_id)
    if not item:
        raise HTTPException(status_code=404, detail="Campaign not found")
    assert_access(db, user.id, item.workspace_id)
    version = next((entry for entry in item.versions or [] if int(entry.get("number", 0)) == version_number), None)
    if not version:
        raise HTTPException(status_code=404, detail="Campaign version not found")
    item.title = version["title"]
    item.brief = version["brief"]
    item.strategy = version["strategy"]
    versions = list(item.versions or [])
    versions.append(campaign_snapshot(item, f"Restaurada da versão {version_number}"))
    item.versions = versions[-50:]
    db.commit()
    db.refresh(item)
    return campaign_out(item)


@router.post("/{campaign_id}/decisions", response_model=CampaignOut)
def record_campaign_decision(
    campaign_id: str,
    data: CampaignDecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    item = db.get(Campaign, campaign_id)
    if not item:
        raise HTTPException(status_code=404, detail="Campaign not found")
    assert_access(db, user.id, item.workspace_id)
    decision = {
        "id": str(uuid4()),
        "type": data.decision_type,
        "summary": data.summary,
        "rationale": data.rationale,
        "decidedBy": user.name,
        "occurredAt": utcnow().isoformat(),
    }
    item.decisions = [*(item.decisions or []), decision][-100:]
    db.add(
        FeedbackEvent(
            workspace_id=item.workspace_id,
            opportunity_id=item.opportunity_id,
            campaign_id=item.id,
            user_id=user.id,
            event_type=data.decision_type,
            reason=data.rationale,
            payload=decision,
        )
    )
    db.commit()
    db.refresh(item)
    return campaign_out(item)
