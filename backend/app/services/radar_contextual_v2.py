from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.radar.contracts_v2 import (
    DimensionScoreV2,
    EligibilityGateV2,
    OpportunityCandidateV2,
    ProviderTraceV2,
    SignalClusterV2,
    SourceEvidenceV2,
)
from ..domain.radar.providers import LexicalSemanticMatcher, SemanticMatcher
from ..domain.radar.scoring import SCORE_VERSION, _bounded, _tokens
from ..models import BrandProfile, ExternalSignal, Opportunity, RadarShadowEvaluation
from .brand import brand_readiness

CANDIDATE_SCORE_VERSION = "radar-v2.0-shadow"
POSITIVE_WEIGHTS = {
    "audience_relevance": 0.28,
    "product_connection": 0.24,
    "brand_fit": 0.20,
    "freshness": 0.16,
    "momentum": 0.07,
    "novelty": 0.05,
}


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _brand_context(brand: BrandProfile) -> tuple[str, str, str]:
    brain = (brand.watchlist or {}).get("brain")
    brain = brain if isinstance(brain, dict) else {}
    products = " ".join(
        f"{item.get('name', '')} {item.get('description', '')}"
        for item in (brand.products or [])
        if isinstance(item, dict)
    ) or str(brain.get("products") or brain.get("services") or "")
    audience = brand.target_audience or str(brain.get("audience") or brain.get("personas") or "")
    positioning = " ".join([brand.industry, brand.tone, " ".join(brand.pillars or []), " ".join(brand.keywords or [])])
    return audience, products, positioning


def _derived(value: float, reason: str, refs: list[str]) -> DimensionScoreV2:
    return DimensionScoreV2(
        status="derived", value=round(max(0.0, min(100.0, value)), 2), reason=reason, evidence_refs=refs
    )


def _observed(value: Any, reason: str, refs: list[str]) -> DimensionScoreV2:
    return DimensionScoreV2(status="observed", value=round(_bounded(value), 2), reason=reason, evidence_refs=refs)


def _unknown(reason: str) -> DimensionScoreV2:
    return DimensionScoreV2(status="unknown", value=None, reason=reason, evidence_refs=[])


def cluster_contract(db: Session, signal: ExternalSignal, now: datetime) -> SignalClusterV2:
    rows = db.scalars(
        select(ExternalSignal)
        .where(
            ExternalSignal.workspace_id == signal.workspace_id,
            ExternalSignal.cluster_key == signal.cluster_key,
            ExternalSignal.expires_at > now,
        )
        .order_by(ExternalSignal.published_at.desc())
        .limit(20)
    ).all()
    evidence: list[SourceEvidenceV2] = []
    seen_urls: set[str] = set()
    for row in rows:
        if not row.url or row.url in seen_urls:
            continue
        seen_urls.add(row.url)
        trace = dict(row.provider_trace or {"provider": f"connector:{row.source_type}"})
        trace.setdefault("provider", f"connector:{row.source_type}")
        if "providerVersion" in trace and "provider_version" not in trace:
            trace["provider_version"] = trace.pop("providerVersion")
        evidence.append(
            SourceEvidenceV2(
                signal_id=row.id,
                source=row.source,
                url=row.url,
                published_at=row.published_at,
                collected_at=row.collected_at,
                expires_at=row.expires_at,
                confidence=row.confidence,
                knowledge_type=row.knowledge_type,
                provider_trace=ProviderTraceV2.model_validate(trace),
            )
        )
    return SignalClusterV2(
        cluster_id=signal.cluster_key or signal.id,
        member_signal_ids=[item.signal_id for item in evidence],
        evidence=evidence,
    )


def evaluate_candidate_v2(
    db: Session,
    signal: ExternalSignal,
    brand: BrandProfile,
    *,
    now: datetime | None = None,
    matcher: SemanticMatcher | None = None,
) -> OpportunityCandidateV2:
    now = now or datetime.now(UTC)
    matcher = matcher or LexicalSemanticMatcher()
    cluster = cluster_contract(db, signal, now)
    refs = [item.signal_id for item in cluster.evidence]
    signal_text = " ".join(
        [signal.title, signal.summary, " ".join(signal.topics or []), " ".join(signal.entities or [])]
    )
    audience, products, positioning = _brand_context(brand)
    age_hours = max(0.0, (now - _aware(signal.published_at)).total_seconds() / 3600)
    freshness = 100.0 * math.exp(-age_hours / 72.0)
    metrics = signal.metrics or {}
    dimensions = {
        "audience_relevance": _derived(
            matcher.similarity(signal_text, audience + " " + " ".join(brand.keywords or [])) * 100,
            f"Matching provider-neutral via {matcher.name}.",
            refs,
        ),
        "product_connection": _derived(
            matcher.similarity(signal_text, products) * 100,
            f"Conexão com oferta via {matcher.name}.",
            refs,
        ),
        "brand_fit": _derived(
            matcher.similarity(signal_text, positioning) * 100,
            f"Aderência editorial via {matcher.name}.",
            refs,
        ),
        "freshness": _derived(freshness, "Derivada apenas do horário publicado e da janela atual.", refs),
        "momentum": _observed(metrics["momentum_score"], "Métrica normalizada fornecida pelo conector.", refs)
        if "momentum_score" in metrics
        else _unknown("O conector não forneceu evidência de momentum."),
        "novelty": _observed(metrics["novelty_score"], "Métrica normalizada fornecida pelo conector.", refs)
        if "novelty_score" in metrics
        else _unknown("Não há evidência suficiente para estimar novidade."),
    }
    penalties = {
        "saturation": _observed(metrics["saturation_score"], "Métrica normalizada fornecida pelo conector.", refs)
        if "saturation_score" in metrics
        else _unknown("Saturação desconhecida; nenhum valor substituto foi inventado."),
        "risk": _observed(metrics["risk_score"], "Risco normalizado fornecido pelo conector.", refs)
        if "risk_score" in metrics
        else _unknown("Sem métrica externa de risco; gates editoriais continuam ativos."),
    }
    known_weight = sum(weight for name, weight in POSITIVE_WEIGHTS.items() if dimensions[name].value is not None)
    positive = sum((dimensions[name].value or 0) * weight for name, weight in POSITIVE_WEIGHTS.items())
    score = positive / known_weight if known_weight else None
    if score is not None and penalties["risk"].value is not None:
        score -= penalties["risk"].value * 0.22
    if score is not None and penalties["saturation"].value is not None:
        score -= penalties["saturation"].value * 0.08
    score = round(max(0.0, min(100.0, score)), 2) if score is not None else None

    prohibited_matches = sorted(_tokens(signal_text) & _tokens(" ".join(brand.prohibited_topics or [])))
    gates = [
        EligibilityGateV2(
            gate="evidence_sufficiency",
            status="pass" if len(cluster.evidence) >= 2 else "block",
            reason="Duas ou mais URLs independentes sustentam o acontecimento."
            if len(cluster.evidence) >= 2
            else "Há menos de duas evidências independentes; sugerir evergreen, não tendência.",
        ),
        EligibilityGateV2(
            gate="publication_window",
            status="pass" if _aware(signal.expires_at) > now else "block",
            reason="A janela factual permanece válida."
            if _aware(signal.expires_at) > now
            else "A janela factual expirou.",
        ),
        EligibilityGateV2(
            gate="prohibited_topic",
            status="block" if prohibited_matches else "pass",
            reason=f"Assuntos proibidos encontrados: {', '.join(prohibited_matches)}"
            if prohibited_matches
            else "Nenhum assunto proibido foi encontrado lexicalmente.",
        ),
        EligibilityGateV2(
            gate="natural_connection",
            status="pass"
            if (dimensions["audience_relevance"].value or 0) >= 8
            and max(dimensions["product_connection"].value or 0, dimensions["brand_fit"].value or 0) >= 8
            else "block",
            reason="Há sobreposição verificável entre acontecimento, público e marca."
            if (dimensions["audience_relevance"].value or 0) >= 8
            and max(dimensions["product_connection"].value or 0, dimensions["brand_fit"].value or 0) >= 8
            else "A conexão seria forçada com os dados atuais.",
        ),
        EligibilityGateV2(
            gate="risk",
            status="block" if (penalties["risk"].value or 0) >= 65 else "pass",
            reason="Risco acima do limite independente do score."
            if (penalties["risk"].value or 0) >= 65
            else "Nenhum risco bloqueante foi observado.",
        ),
    ]
    blocked = [gate.reason for gate in gates if gate.status == "block"]
    confidence = min(1.0, 0.35 + min(len(cluster.evidence), 3) * 0.15 + known_weight * 0.2)
    product_label = next(
        (str(item.get("name")) for item in (brand.products or []) if isinstance(item, dict) and item.get("name")),
        "posicionamento da marca",
    )
    return OpportunityCandidateV2(
        workspace_id=brand.workspace_id,
        signal_id=signal.id,
        cluster_id=cluster.cluster_id,
        brand_revision=brand_readiness(brand)["revision"],
        title=signal.title,
        what_to_post=f"Explique o impacto verificável de {signal.title} para o público da marca.",
        why_it_fits=f"Conexão avaliada entre o acontecimento, o público e {product_label}.",
        recommended_format="Carrossel educativo",
        hook=f"O que {signal.title} muda para você?",
        objective="authority",
        publish_until=signal.expires_at,
        confidence=round(confidence, 3),
        score=score,
        dimensions=dimensions,
        penalties=penalties,
        gates=gates,
        eligible=not blocked,
        rejection_reason=" ".join(blocked) if blocked else None,
        evidence=cluster.evidence,
        effort="medium",
        lineage={
            "baselineScoreVersion": SCORE_VERSION,
            "candidateScoreVersion": CANDIDATE_SCORE_VERSION,
            "matcher": matcher.name,
            "brandRevision": brand_readiness(brand)["revision"],
        },
    )


def record_shadow_evaluation(
    db: Session,
    opportunity: Opportunity,
    signal: ExternalSignal,
    brand: BrandProfile,
    *,
    now: datetime | None = None,
) -> RadarShadowEvaluation | None:
    now = now or datetime.now(UTC)
    representative = db.scalars(
        select(ExternalSignal)
        .where(
            ExternalSignal.workspace_id == signal.workspace_id,
            ExternalSignal.cluster_key == signal.cluster_key,
            ExternalSignal.expires_at > now,
        )
        .order_by(ExternalSignal.published_at.desc(), ExternalSignal.id)
        .limit(1)
    ).first()
    if representative and representative.id != signal.id:
        return None
    candidate = evaluate_candidate_v2(db, signal, brand, now=now)
    evaluation = RadarShadowEvaluation(
        workspace_id=opportunity.workspace_id,
        signal_id=signal.id,
        active_opportunity_id=opportunity.id,
        baseline_version=opportunity.score_version,
        baseline_score=opportunity.score,
        candidate_version=CANDIDATE_SCORE_VERSION,
        candidate_score=candidate.score,
        brand_revision=candidate.brand_revision,
        candidate=candidate.model_dump(mode="json"),
        comparison={
            "scoreDelta": round(candidate.score - opportunity.score, 2) if candidate.score is not None else None,
            "baselineEligible": opportunity.eligible,
            "candidateEligible": candidate.eligible,
            "eligibilityChanged": opportunity.eligible != candidate.eligible,
        },
        provider_trace={"semanticMatcher": candidate.lineage["matcher"], "mode": "shadow"},
    )
    db.add(evaluation)
    return evaluation
