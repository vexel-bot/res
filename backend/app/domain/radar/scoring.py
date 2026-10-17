from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

SCORE_VERSION = "radar-v1.1"

WEIGHTS = {
    "audience_relevance": 0.17,
    "product_connection": 0.16,
    "brand_fit": 0.13,
    "freshness": 0.13,
    "momentum": 0.07,
    "novelty": 0.07,
    "shareability": 0.07,
    "local_fit": 0.07,
    "authority_potential": 0.07,
    "conversion_potential": 0.06,
}


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", normalized)
        if token not in {"para", "como", "uma", "com", "dos", "das", "que", "por"}
    }


def _overlap_score(signal_tokens: set[str], context: str) -> float:
    context_tokens = _tokens(context)
    if not context_tokens:
        return 0.0
    overlap = len(signal_tokens & context_tokens)
    return min(100.0, 100.0 * overlap / max(2.0, math.sqrt(len(context_tokens) * 2)))


def _freshness(published_at: datetime, now: datetime) -> float:
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    age_hours = max(0.0, (now - published_at).total_seconds() / 3600)
    return round(max(0.0, 100.0 * math.exp(-age_hours / 72.0)), 2)


def _bounded(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class RankedOpportunity:
    score: float
    breakdown: dict[str, float]
    eligible: bool
    rejection_reason: str | None
    bridge: str
    risks: list[str]


def rank_signal(signal: Any, brand: Any, now: datetime | None = None) -> RankedOpportunity:
    """Rank a signal using explainable, reproducible lexical and objective features.

    External text is data only. It is never interpreted as instructions here.
    Momentum is zero unless the connector supplied a normalized evidence metric.
    """
    now = now or datetime.now(UTC)
    signal_text = " ".join(
        [signal.title, signal.summary, " ".join(signal.topics or []), " ".join(signal.entities or [])]
    )
    signal_tokens = _tokens(signal_text)
    products = " ".join(
        str(item.get("name", "")) + " " + str(item.get("description", "")) for item in (brand.products or [])
    )
    watchlist = " ".join(str(value) for value in (brand.watchlist or {}).values())
    audience_relevance = max(
        _overlap_score(signal_tokens, brand.target_audience),
        _overlap_score(signal_tokens, " ".join(brand.keywords or []) + " " + watchlist),
    )
    product_connection = _overlap_score(signal_tokens, products)
    brand_fit = _overlap_score(
        signal_tokens, " ".join(brand.pillars or []) + " " + brand.industry + " " + " ".join(brand.keywords or [])
    )
    local_fit = 100.0 if signal.region in (brand.regions or ["BR"]) else 35.0
    freshness = _freshness(signal.published_at, now)
    metrics = signal.metrics or {}
    momentum = _bounded(metrics.get("momentum_score"), 0.0)
    novelty = _bounded(metrics.get("novelty_score"), 50.0)
    shareability = min(100.0, 25.0 + audience_relevance * 0.45 + novelty * 0.25)
    authority = min(100.0, 20.0 + brand_fit * 0.55 + audience_relevance * 0.25)
    conversion = min(100.0, product_connection * 0.65 + audience_relevance * 0.25)
    saturation = _bounded(metrics.get("saturation_score"), 20.0)

    prohibited = _tokens(" ".join(brand.prohibited_topics or []))
    prohibited_matches = sorted(signal_tokens & prohibited)
    risk = _bounded(metrics.get("risk_score"), 0.0)
    risks: list[str] = []
    if prohibited_matches:
        risk = 100.0
        risks.append("O sinal contém assunto proibido pela política da marca.")
    if metrics.get("copyright_sensitive"):
        risk = max(risk, 75.0)
        risks.append("Evite personagens, logos ou imagens protegidas relacionados ao acontecimento.")
    if saturation >= 75:
        risks.append("O assunto apresenta saturação elevada.")

    breakdown = {
        "audience_relevance": round(audience_relevance, 2),
        "product_connection": round(product_connection, 2),
        "brand_fit": round(brand_fit, 2),
        "freshness": freshness,
        "momentum": round(momentum, 2),
        "novelty": round(novelty, 2),
        "shareability": round(shareability, 2),
        "local_fit": round(local_fit, 2),
        "authority_potential": round(authority, 2),
        "conversion_potential": round(conversion, 2),
        "saturation": round(saturation, 2),
        "risk": round(risk, 2),
    }
    positive = sum(breakdown[name] * weight for name, weight in WEIGHTS.items())
    score = max(0.0, min(100.0, positive - risk * 0.22 - saturation * 0.08))

    rejection_reason = None
    if risk >= 65:
        rejection_reason = "Risco de marca, jurídico ou reputacional acima do limite."
    elif freshness < 10:
        rejection_reason = "A janela factual deste sinal expirou."
    elif audience_relevance < 20 or brand_fit < 15:
        rejection_reason = "Não existe ponte natural suficiente com o público e os pilares da marca."
    elif product_connection < 12 and authority < 35:
        rejection_reason = "A conexão com produto ou posicionamento seria forçada."

    eligible = rejection_reason is None
    product_label = (brand.products or [{}])[0].get("name") or "posicionamento da marca"
    bridge = (
        f"{signal.title} → interesse do público em {brand.target_audience or brand.industry} "
        f"→ {product_label} → conteúdo de autoridade contextual."
    )
    return RankedOpportunity(
        score=round(score, 2),
        breakdown=breakdown,
        eligible=eligible,
        rejection_reason=rejection_reason,
        bridge=bridge,
        risks=risks,
    )
