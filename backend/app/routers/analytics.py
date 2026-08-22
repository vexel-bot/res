from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BrandProfile, Campaign, FeedbackEvent, Membership, Opportunity, Post, User, Workspace
from ..schemas import AnalyticsSummaryOut
from ..security import get_current_user
from ..services.brand import brand_readiness

router = APIRouter(prefix="/analytics", tags=["analytics"])


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Workspace not found")


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def elapsed_minutes(start: datetime, end: datetime | None) -> float | None:
    if not end:
        return None
    return round(max(0.0, (aware(end) - aware(start)).total_seconds() / 60), 2)


def metric(
    key: str,
    label: str,
    value: float | int | None,
    unit: str,
    source: str,
    sample_size: int,
    definition: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "unit": unit,
        "status": "available" if value is not None else "insufficient_data",
        "source": source,
        "sample_size": sample_size,
        "definition": definition,
    }


@router.get("/summary", response_model=AnalyticsSummaryOut)
def analytics_summary(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    assert_access(db, user.id, workspace_id)
    workspace = db.get(Workspace, workspace_id)
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == workspace_id))
    if not workspace or not brand:
        raise HTTPException(status_code=404, detail="Workspace not found")
    events = list(
        db.scalars(
            select(FeedbackEvent)
            .where(FeedbackEvent.workspace_id == workspace_id)
            .order_by(FeedbackEvent.occurred_at)
        ).all()
    )
    opportunities = list(db.scalars(select(Opportunity).where(Opportunity.workspace_id == workspace_id)).all())
    campaigns = list(db.scalars(select(Campaign).where(Campaign.workspace_id == workspace_id)).all())
    posts = list(db.scalars(select(Post).where(Post.workspace_id == workspace_id)).all())
    eligible_opportunities = [item for item in opportunities if item.eligible]
    first_opportunity = min((item.created_at for item in eligible_opportunities), default=None)
    first_export = next(
        (
            event.occurred_at
            for event in events
            if event.creative_document_id and (event.payload or {}).get("exportAssetId")
        ),
        None,
    )
    shown = {event.opportunity_id for event in events if event.event_type == "shown" and event.opportunity_id}
    chosen = {event.opportunity_id for event in events if event.event_type == "chosen" and event.opportunity_id}
    rejected_events = [event for event in events if event.event_type == "rejected" and event.opportunity_id]
    rejected = {event.opportunity_id for event in rejected_events}
    opportunity_campaigns = [campaign for campaign in campaigns if campaign.opportunity_id]
    campaign_opportunity_ids = {campaign.opportunity_id for campaign in opportunity_campaigns}
    campaign_posts = {post.campaign_id for post in posts if post.campaign_id}
    useful_campaigns = [campaign for campaign in opportunity_campaigns if campaign.id in campaign_posts]
    reused_events = [event for event in events if event.event_type == "reused"]
    edited_events = [event for event in events if event.event_type == "edited"]
    readiness = brand_readiness(brand)
    completion_times = [
        datetime.fromisoformat(str(version["createdAt"]))
        for version in (brand.versions or [])
        if int(version.get("readinessPercentage", 0)) >= 80 and version.get("createdAt")
    ]
    first_brand_completion = min(completion_times, default=None)

    weekly: dict[str, dict[str, int]] = defaultdict(
        lambda: {"campaigns": 0, "opportunityCampaigns": 0, "usefulCampaigns": 0}
    )
    useful_ids = {campaign.id for campaign in useful_campaigns}
    for campaign in campaigns:
        created = aware(campaign.created_at)
        year, week, _ = created.isocalendar()
        key = f"{year}-W{week:02d}"
        weekly[key]["campaigns"] += 1
        weekly[key]["opportunityCampaigns"] += int(bool(campaign.opportunity_id))
        weekly[key]["usefulCampaigns"] += int(campaign.id in useful_ids)
    weekly_activity = [{"week": week, **counts} for week, counts in sorted(weekly.items())]
    active_weeks = len(weekly_activity)
    retained_weeks = sum(1 for item in weekly_activity[1:] if item["campaigns"] > 0)
    retention_rate = round(retained_weeks / max(1, active_weeks - 1) * 100, 2) if active_weeks > 1 else None

    metrics = [
        metric(
            "time_to_complete_brand",
            "Tempo até completar a marca",
            elapsed_minutes(workspace.created_at, first_brand_completion) if readiness["status"] == "ready" else None,
            "minutes",
            "observed",
            1 if readiness["status"] == "ready" else 0,
            "Minutos entre a criação do workspace e a atualização que deixou a prontidão em 80% ou mais.",
        ),
        metric(
            "time_to_first_opportunity",
            "Tempo até a primeira oportunidade útil",
            elapsed_minutes(workspace.created_at, first_opportunity),
            "minutes",
            "observed",
            1 if first_opportunity else 0,
            "Minutos entre a criação do workspace e a primeira oportunidade elegível persistida.",
        ),
        metric(
            "opportunity_selection_rate",
            "Percentual que escolhe uma oportunidade",
            round(len(chosen) / len(shown) * 100, 2) if shown else None,
            "percent",
            "derived",
            len(shown),
            "Oportunidades escolhidas divididas pelas oportunidades exibidas no workspace.",
        ),
        metric(
            "opportunity_to_campaign_rate",
            "Percentual que transforma oportunidade em campanha",
            round(len(campaign_opportunity_ids) / len(eligible_opportunities) * 100, 2)
            if eligible_opportunities
            else None,
            "percent",
            "derived",
            len(eligible_opportunities),
            "Oportunidades elegíveis distintas com campanha divididas pelas oportunidades elegíveis persistidas.",
        ),
        metric(
            "time_to_first_export",
            "Tempo até a primeira peça exportada",
            elapsed_minutes(workspace.created_at, first_export),
            "minutes",
            "observed",
            1 if first_export else 0,
            "Minutos entre a criação do workspace e o primeiro ativo exportado por um documento criativo.",
        ),
        metric(
            "opportunities_rejected",
            "Oportunidades rejeitadas",
            len(rejected),
            "count",
            "observed",
            len(rejected_events),
            "Quantidade de oportunidades distintas rejeitadas explicitamente.",
        ),
        metric(
            "edit_intensity",
            "Intensidade de edição das peças",
            round(
                sum(float((event.payload or {}).get("editIntensity", 0)) for event in edited_events)
                / len(edited_events),
                3,
            )
            if edited_events
            else None,
            "ratio",
            "derived",
            len(edited_events),
            "Média da intensidade registrada em eventos reais de edição.",
        ),
        metric(
            "campaigns_reused",
            "Campanhas e conteúdos reutilizados",
            len(reused_events),
            "count",
            "observed",
            len(reused_events),
            "Eventos persistidos de reutilização de campanha, conteúdo ou criativo.",
        ),
        metric(
            "weekly_campaign_retention",
            "Retenção semanal por campanhas criadas",
            retention_rate,
            "percent",
            "derived",
            active_weeks,
            "Semanas posteriores com campanha divididas pelas semanas observáveis após a primeira semana ativa.",
        ),
        metric(
            "useful_opportunity_campaigns_per_week",
            "Campanhas úteis a partir de oportunidades por semana",
            round(len(useful_campaigns) / max(1, active_weeks), 2) if active_weeks else None,
            "campaigns_per_week",
            "derived",
            len(useful_campaigns),
            "Campanhas com oportunidade de origem e ao menos uma peça persistida, por semana ativa observada.",
        ),
    ]

    rejection_counts = Counter((event.reason or "Sem motivo informado").strip() for event in rejected_events)
    rejection_reasons = [
        {"reason": reason, "count": count}
        for reason, count in rejection_counts.most_common()
    ]
    insights: list[dict[str, Any]] = []
    if rejection_reasons:
        top_reason = rejection_reasons[0]
        insights.append(
            {
                "key": "rejection_pattern",
                "title": "Motivo recorrente de rejeição",
                "statement": f"{top_reason['count']} rejeição(ões) registraram: {top_reason['reason']}.",
                "recommendation": "Ajuste assuntos monitorados e pilares antes da próxima coleta.",
                "evidence_type": "observed",
                "sample_size": len(rejected_events),
            }
        )
    measured_posts = [post for post in posts if (post.metrics or {}).get("reach")]
    if measured_posts:
        by_format: dict[str, list[float]] = defaultdict(list)
        for post in measured_posts:
            values = post.metrics or {}
            interactions = sum(int(values.get(key) or 0) for key in ("likes", "comments", "shares", "saves"))
            by_format[post.format].append(interactions / max(1, int(values["reach"])))
        best_format, samples = max(by_format.items(), key=lambda item: sum(item[1]) / len(item[1]))
        insights.append(
            {
                "key": "best_measured_format",
                "title": "Formato com melhor desempenho relativo",
                "statement": f"{best_format} teve a maior taxa média de interações por alcance informado.",
                "recommendation": f"Teste mais peças em {best_format}, mantendo comparação dentro deste workspace.",
                "evidence_type": "user_reported",
                "sample_size": len(samples),
            }
        )
    if useful_campaigns:
        insights.append(
            {
                "key": "connected_campaign_usage",
                "title": "Campanhas conectadas em uso",
                "statement": f"{len(useful_campaigns)} campanha(s) originada(s) no Radar já possuem peças persistidas.",
                "recommendation": "Registre resultados das peças para refinar as próximas recomendações.",
                "evidence_type": "observed",
                "sample_size": len(useful_campaigns),
            }
        )
    if not insights:
        insights.append(
            {
                "key": "insufficient_evidence",
                "title": "Dados insuficientes para recomendar",
                "statement": "Ainda não há escolhas, rejeições, peças usadas ou métricas suficientes.",
                "recommendation": "Use uma oportunidade, edite uma peça e registre somente os resultados disponíveis.",
                "evidence_type": "insufficient_data",
                "sample_size": 0,
            }
        )
    return {
        "workspace_id": workspace_id,
        "generated_at": datetime.now(UTC),
        "metrics": metrics,
        "insights": insights,
        "weekly_campaign_activity": weekly_activity,
        "rejection_reasons": rejection_reasons,
    }
