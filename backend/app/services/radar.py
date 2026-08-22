from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..domain.radar import SCORE_VERSION, rank_signal
from ..models import BrandProfile, ExternalSignal, FeedbackEvent, Opportunity
from .learning import preference_adjustment, workspace_preference_profile


def _brain(brand: BrandProfile) -> dict[str, Any]:
    watchlist = brand.watchlist or {}
    value = watchlist.get("brain")
    return value if isinstance(value, dict) else {}


def _first_relevant(values: list[str], haystack: str) -> str:
    for value in values:
        if value and value.casefold() in haystack:
            return value
    return values[0] if values else ""


def opportunity_contract(
    db: Session,
    opportunity: Opportunity,
    *,
    brand: BrandProfile | None = None,
    signal: ExternalSignal | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    brand = brand or db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == opportunity.workspace_id))
    signal = signal or db.get(ExternalSignal, opportunity.signal_id)
    feedback = db.scalars(
        select(FeedbackEvent)
        .where(
            FeedbackEvent.workspace_id == opportunity.workspace_id,
            FeedbackEvent.opportunity_id == opportunity.id,
            FeedbackEvent.event_type.in_(["saved", "rejected", "chosen"]),
        )
        .order_by(FeedbackEvent.occurred_at.desc())
        .limit(1)
    ).first()
    feedback_type = feedback.event_type if feedback else ""
    brain = _brain(brand) if brand else {}
    products = [
        str(item.get("name") or item.get("title") or "").strip()
        for item in (brand.products or [] if brand else [])
        if isinstance(item, dict)
    ]
    product_text = str(brain.get("products") or brain.get("services") or "").strip()
    if product_text and not products:
        products = [product_text]
    pillars = [str(value).strip() for value in (brand.pillars or [] if brand else []) if str(value).strip()]
    signal_text = " ".join(
        value for value in [signal.title if signal else "", signal.summary if signal else ""] if value
    ).casefold()
    score = opportunity.score
    score_label = (
        "Excelente combinação"
        if score >= 80
        else "Oportunidade relevante"
        if score >= 65
        else "Vale monitorar"
        if score >= 50
        else "Baixa prioridade"
    )
    risk_score = float((opportunity.score_breakdown or {}).get("risk", 0))
    risk_level = (
        "high"
        if not opportunity.eligible or risk_score >= 60
        else "medium"
        if opportunity.risks or risk_score >= 25
        else "low"
    )
    publish_until = opportunity.publish_until
    if publish_until.tzinfo is None:
        publish_until = publish_until.replace(tzinfo=UTC)
    hours_remaining = max(0.0, (publish_until - now).total_seconds() / 3600)
    window_label = (
        "Publique hoje"
        if hours_remaining <= 24
        else "Próximos 3 dias"
        if hours_remaining <= 72
        else "Nesta semana"
    )
    source_contract = {
        "name": signal.source if signal else "",
        "url": signal.url if signal else "",
        "publishedAt": signal.published_at.isoformat() if signal else None,
        "collectedAt": signal.collected_at.isoformat() if signal else None,
    }
    return {
        "id": opportunity.id,
        "workspace_id": opportunity.workspace_id,
        "signal_id": opportunity.signal_id,
        "title": opportunity.title,
        "event_summary": opportunity.event_summary,
        "bridge": opportunity.bridge,
        "recommended_format": opportunity.recommended_format,
        "hook": opportunity.hook,
        "objective": opportunity.objective,
        "publish_until": opportunity.publish_until,
        "score": opportunity.score,
        "score_breakdown": opportunity.score_breakdown or {},
        "score_version": opportunity.score_version,
        "risks": opportunity.risks or [],
        "evidence": opportunity.evidence or [],
        "eligible": opportunity.eligible,
        "rejection_reason": opportunity.rejection_reason,
        "source": source_contract,
        "updated_at": opportunity.updated_at,
        "why_it_fits": opportunity.bridge,
        "related_context": {
            "audience": (brand.target_audience if brand else "") or str(brain.get("audience") or ""),
            "product": _first_relevant(products, signal_text),
            "pillar": _first_relevant(pillars, signal_text),
        },
        "score_label": score_label,
        "risk_level": risk_level,
        "window_label": window_label,
        "saved": feedback_type == "saved",
        "rejected": feedback_type == "rejected",
        "actions": {
            "canCreateCampaign": opportunity.eligible and feedback_type != "rejected",
            "canSave": feedback_type != "saved",
            "canReject": feedback_type != "rejected",
        },
    }


def evergreen_suggestions(brand: BrandProfile) -> list[dict[str, Any]]:
    brain = _brain(brand)
    products = [
        str(item.get("name") or item.get("title") or "").strip()
        for item in (brand.products or [])
        if isinstance(item, dict) and (item.get("name") or item.get("title"))
    ]
    product = products[0] if products else str(brain.get("products") or brain.get("services") or "a oferta da marca")
    audience = brand.target_audience or str(brain.get("audience") or "o público definido pela marca")
    pillar = (brand.pillars or ["tema central da marca"])[0]
    return [
        {
            "title": f"Guia prático sobre {pillar}",
            "rationale": f"Conteúdo educativo fundamentado no pilar cadastrado e nas dúvidas de {audience}.",
            "recommended_format": "Carrossel educativo",
            "objective": "authority",
            "grounded_in": [f"pilar:{pillar}", f"público:{audience}"],
        },
        {
            "title": f"Como avaliar {product} antes de decidir",
            "rationale": "Explica critérios reais da oferta sem depender de uma tendência não confirmada.",
            "recommended_format": "Post estático",
            "objective": "leads",
            "grounded_in": [f"produto:{product}", f"público:{audience}"],
        },
        {
            "title": f"Perguntas frequentes de {audience}",
            "rationale": "Transforma dúvidas persistidas na memória da marca em conteúdo útil e verificável.",
            "recommended_format": "Stories",
            "objective": "reach",
            "grounded_in": [f"público:{audience}", "memória:faq"],
        },
    ]


def cluster_evidence(db: Session, signal: ExternalSignal, now: datetime) -> list[dict[str, str]]:
    members = db.scalars(
        select(ExternalSignal)
        .where(
            ExternalSignal.workspace_id == signal.workspace_id,
            ExternalSignal.cluster_key == signal.cluster_key,
            ExternalSignal.expires_at > now,
        )
        .order_by(ExternalSignal.published_at.desc())
        .limit(8)
    ).all()
    evidence: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for member in members:
        if member.url in seen_urls:
            continue
        seen_urls.add(member.url)
        evidence.append(
            {
                "source": member.source,
                "url": member.url,
                "publishedAt": member.published_at.isoformat(),
            }
        )
    return evidence


def upsert_workspace_opportunities(
    db: Session,
    workspace_id: str,
    *,
    signal_ids: list[str] | None = None,
    now: datetime | None = None,
) -> tuple[list[Opportunity], int, int]:
    now = now or datetime.now(UTC)
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == workspace_id))
    if not brand:
        raise ValueError("Brand profile not found")
    query = select(ExternalSignal).where(
        or_(ExternalSignal.workspace_id == workspace_id, ExternalSignal.workspace_id.is_(None)),
        ExternalSignal.expires_at > now,
    )
    if signal_ids:
        query = query.where(ExternalSignal.id.in_(signal_ids))
    signals = db.scalars(query.order_by(ExternalSignal.published_at.desc()).limit(200)).all()
    preference_profile = workspace_preference_profile(db, workspace_id)
    opportunities: list[Opportunity] = []
    created = 0
    updated = 0
    for signal in signals:
        ranked = rank_signal(signal, brand, now=now)
        opportunity = db.scalars(
            select(Opportunity)
            .where(
                Opportunity.workspace_id == workspace_id,
                Opportunity.signal_id == signal.id,
            )
            .order_by(Opportunity.updated_at.desc())
            .limit(1)
        ).first()
        personalized_adjustment = preference_adjustment(ranked.breakdown, preference_profile)
        score_breakdown = {
            **ranked.breakdown,
            "preference_adjustment": personalized_adjustment,
            "preference_events": float(preference_profile.explicit_events),
            "performance_samples": float(preference_profile.performance_samples),
        }
        fields = {
            "title": signal.title,
            "event_summary": signal.summary or signal.title,
            "bridge": ranked.bridge,
            "recommended_format": "Carrossel educativo",
            "hook": f"O que {signal.title} muda para o seu público?",
            "objective": "authority"
            if ranked.breakdown["authority_potential"] >= ranked.breakdown["conversion_potential"]
            else "conversion",
            "publish_until": signal.expires_at,
            "score": round(max(0.0, min(100.0, ranked.score + personalized_adjustment)), 2),
            "score_breakdown": score_breakdown,
            "score_version": SCORE_VERSION,
            "risks": ranked.risks,
            "evidence": cluster_evidence(db, signal, now),
            "eligible": ranked.eligible,
            "rejection_reason": ranked.rejection_reason,
        }
        if not opportunity:
            opportunity = Opportunity(
                workspace_id=workspace_id,
                signal_id=signal.id,
                **fields,
            )
            db.add(opportunity)
            created += 1
        else:
            for field, value in fields.items():
                setattr(opportunity, field, value)
            updated += 1
        opportunities.append(opportunity)
    db.flush()
    return opportunities, created, updated
