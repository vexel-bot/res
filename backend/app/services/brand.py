from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..models import BrandProfile


@dataclass(frozen=True)
class ReadinessCriterion:
    field: str
    label: str
    weight: int
    impact: str
    reason: str
    complete: bool


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _filled(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return value is not None


def _brain(brand: BrandProfile) -> dict[str, Any]:
    watchlist = brand.watchlist or {}
    candidate = watchlist.get("brain")
    return candidate if isinstance(candidate, dict) else {}


def _watch_values(watchlist: dict[str, Any], *keys: str) -> list[Any]:
    return [watchlist.get(key) for key in keys if _filled(watchlist.get(key))]


def readiness_criteria(brand: BrandProfile) -> list[ReadinessCriterion]:
    brain = _brain(brand)
    watchlist = brand.watchlist or {}
    products = brand.products or []
    source_files = brain.get("sourceFiles") if isinstance(brain.get("sourceFiles"), list) else []
    visual_sources = [
        item
        for item in source_files
        if isinstance(item, dict) and item.get("type") in {"image", "logo", "product", "face"}
    ]
    monitoring = _watch_values(
        watchlist,
        "topics",
        "competitors",
        "players",
        "references",
        "monitoredTopics",
        "nicho",
    )
    return [
        ReadinessCriterion(
            "brand_identity",
            "Identidade da marca",
            8,
            "high",
            "Nome e contexto da empresa orientam todas as recomendações.",
            _filled(brand.name) and (_filled(brain.get("company")) or _filled(brand.industry)),
        ),
        ReadinessCriterion(
            "segment",
            "Segmento e atuação",
            8,
            "high",
            "O segmento reduz conexões genéricas ou incompatíveis.",
            _filled(brand.industry) or _filled(brain.get("company")),
        ),
        ReadinessCriterion(
            "location",
            "Localização e área de atuação",
            7,
            "medium",
            "A localização permite priorizar acontecimentos locais e regionais.",
            bool(brand.regions) or _filled(watchlist.get("serviceArea")),
        ),
        ReadinessCriterion(
            "products_and_offers",
            "Produtos, serviços e ofertas",
            12,
            "high",
            "Sem uma oferta real não existe ponte confiável para conversão.",
            bool(products) or _filled(brain.get("products")) or _filled(brain.get("services")),
        ),
        ReadinessCriterion(
            "audience",
            "Público e personas",
            10,
            "high",
            "O Radar precisa saber para quem o conteúdo deve ser útil.",
            _filled(brand.target_audience) or _filled(brain.get("audience")) or _filled(brain.get("personas")),
        ),
        ReadinessCriterion(
            "audience_motivations",
            "Dores, desejos e objeções",
            12,
            "high",
            "Dores, desejos e objeções sustentam a conexão entre sinal e conteúdo.",
            all(_filled(brain.get(key)) for key in ("pains", "desires", "objections")),
        ),
        ReadinessCriterion(
            "voice_and_positioning",
            "Tom de voz e posicionamento",
            11,
            "high",
            "Tom e diferenciais mantêm as peças reconhecíveis e coerentes.",
            (_filled(brand.tone) or _filled(brain.get("toneOfVoice")))
            and (_filled(brain.get("differentiators")) or _filled(brain.get("objectives"))),
        ),
        ReadinessCriterion(
            "editorial_policy",
            "Pilares e limites editoriais",
            11,
            "high",
            "Pilares e restrições impedem recomendações forçadas ou arriscadas.",
            bool(brand.pillars)
            and (
                bool(brand.prohibited_topics)
                or _filled(brand.do_and_donts)
                or _filled(brain.get("forbiddenWords"))
            ),
        ),
        ReadinessCriterion(
            "monitoring_context",
            "Concorrentes, referências e assuntos monitorados",
            10,
            "medium",
            "O contexto monitorado melhora a cobertura do nicho e reduz ruído.",
            bool(monitoring) or _filled(brain.get("competitors")) or _filled(brain.get("faq")),
        ),
        ReadinessCriterion(
            "visual_assets",
            "Identidade e ativos visuais",
            11,
            "medium",
            "Cores e ativos reais permitem composições consistentes e editáveis.",
            (_filled(brand.primary_color) or _filled(brain.get("visualIdentity")))
            and (bool(visual_sources) or _filled(brain.get("visualIdentity"))),
        ),
    ]


def brand_readiness(brand: BrandProfile) -> dict[str, Any]:
    criteria = readiness_criteria(brand)
    completed = [criterion.field for criterion in criteria if criterion.complete]
    percentage = sum(criterion.weight for criterion in criteria if criterion.complete)
    watchlist = brand.watchlist or {}
    revision_value = watchlist.get("brainRevision", 1)
    try:
        revision = max(1, int(revision_value))
    except (TypeError, ValueError):
        revision = 1
    return {
        "workspace_id": brand.workspace_id,
        "percentage": percentage,
        "status": "ready" if percentage >= 80 else "usable" if percentage >= 50 else "incomplete",
        "completed_fields": completed,
        "missing_fields": [
            {
                "field": criterion.field,
                "label": criterion.label,
                "impact": criterion.impact,
                "weight": criterion.weight,
                "reason": criterion.reason,
            }
            for criterion in criteria
            if not criterion.complete
        ],
        "revision": revision,
        "version_count": len(brand.versions or []),
        "updated_at": brand.updated_at,
    }


def brand_profile_snapshot(brand: BrandProfile, *, label: str, number: int) -> dict[str, Any]:
    return {
        "number": number,
        "label": label,
        "createdAt": datetime.now(UTC).isoformat(),
        "readinessPercentage": brand_readiness(brand)["percentage"],
        "profile": {
            "name": brand.name,
            "industry": brand.industry,
            "regions": list(brand.regions or []),
            "languages": list(brand.languages or []),
            "tone": brand.tone,
            "target_audience": brand.target_audience,
            "keywords": list(brand.keywords or []),
            "do_and_donts": brand.do_and_donts,
            "primary_color": brand.primary_color,
            "products": list(brand.products or []),
            "pillars": list(brand.pillars or []),
            "watchlist": dict(brand.watchlist or {}),
            "prohibited_topics": list(brand.prohibited_topics or []),
        },
    }
