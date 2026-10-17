from typing import Any

from ..schemas import CampaignIn


def _clean(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


def build_campaign_strategy(data: CampaignIn, brand: dict[str, Any]) -> dict[str, Any]:
    """Create an editable plan from facts supplied in the brief; it never invents external facts."""
    product = data.products.strip() or data.offer.strip() or "a oferta"
    audience = data.audience.strip() or "o público definido pela marca"
    promise = data.promise.strip() or data.objective.strip()
    cta = data.cta.strip() or (data.ctas[0].strip() if data.ctas else "Saiba mais")
    emotion = data.emotion.strip() or "confiança"
    proof = data.proof.strip()
    big_idea = data.big_idea.strip() or f"{product}: {promise}".strip(": ")
    central_message = (
        data.central_message.strip()
        or f"Uma mensagem para {audience} que conecta {product} ao resultado desejado: {promise}."
    )
    angles = _clean(data.angles) or [
        f"Problema e solução: por que {audience} precisa de uma abordagem melhor",
        f"Demonstração prática do valor de {product}",
        f"Transformação desejada com foco em {emotion}",
    ]
    if proof:
        angles.insert(1, f"Prova e credibilidade: {proof}")
    angles = angles[:5]
    hooks = _clean(data.hooks) or [
        f"O que muda quando {audience} encontra uma solução alinhada ao objetivo?",
        f"Antes de escolher {product}, observe estes pontos.",
        f"Um caminho mais claro para {promise}.",
    ]
    narrative = _clean(data.narrative_sequence) or [
        "Nomear o contexto ou problema sem exageros",
        f"Apresentar a ponte com {product}",
        f"Sustentar a promessa com {proof}" if proof else "Explicar o mecanismo ou benefício com clareza",
        f"Concluir com a ação: {cta}",
    ]
    formats = _clean(data.formats) or ["post", "carousel", "ad", "script", "ugc-script"]
    visual_identity = str(brand.get("visualIdentity") or brand.get("primaryColor") or "paleta e ativos reais da marca")
    matrix = data.creative_matrix or []
    if not matrix and data.opportunity_id:
        kit = [
            ("static-1", "post", "contexto"),
            ("static-2", "post", "educação"),
            ("static-3", "post", "conversão"),
            ("carousel-1", "carousel", "aprofundamento"),
            ("ad-1", "ad", "problema"),
            ("ad-2", "ad", "prova"),
            ("ugc-1", "ugc-script", "experiência"),
            ("ugc-2", "ugc-script", "objeção"),
        ]
        for index, (piece_key, format_name, function_name) in enumerate(kit):
            matrix.append(
                {
                    "pieceKey": piece_key,
                    "variant": index + 1,
                    "format": format_name,
                    "function": function_name,
                    "hook": hooks[index % len(hooks)],
                    "angle": angles[index % len(angles)],
                    "promise": promise,
                    "problem": data.objective,
                    "solution": product,
                    "storytelling": narrative,
                    "cta": cta,
                    "visualStyle": visual_identity,
                    "emotion": emotion,
                    "funnel": data.funnel or "consideração",
                }
            )
    elif not matrix:
        for index, format_name in enumerate(formats):
            matrix.append(
                {
                    "format": format_name,
                    "function": ["apresentar", "educar", "converter", "aprofundar", "humanizar"][index % 5],
                    "hook": hooks[index % len(hooks)],
                    "angle": angles[index % len(angles)],
                    "promise": promise,
                    "problem": data.objective,
                    "solution": product,
                    "storytelling": narrative,
                    "cta": cta,
                    "visualStyle": visual_identity,
                    "emotion": emotion,
                    "funnel": data.funnel or "consideração",
                }
            )
    execution = _clean(data.execution_plan) or [
        "Validar conceito, promessa, prova e restrições",
        "Produzir e revisar as peças conectadas da matriz criativa",
        "Aplicar identidade visual e ativos reais no editor",
        "Agendar a sequência e acompanhar os dados disponíveis",
    ]
    return {
        "kpis": data.kpis,
        "channels": data.channels,
        "funnel": data.funnel,
        "ctas": _clean(data.ctas) or [cta],
        "executionPlan": execution,
        "bigIdea": big_idea,
        "centralMessage": central_message,
        "angles": angles,
        "hooks": hooks,
        "narrativeSequence": narrative,
        "creativeMatrix": matrix,
        "formatSuggestions": ["stories", "reels"] if data.opportunity_id else [],
        "originContext": data.origin_context,
        "status": data.status,
        "brainRevision": data.brain_revision,
    }
