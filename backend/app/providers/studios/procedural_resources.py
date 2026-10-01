"""Trusted, assetless visual candidates backed by the bundled Lucide library."""

import hashlib
import re
import unicodedata

ICON_RULES = (
    (("envolvido", "atento", "absorve", "engajado"), "UserRoundCheck"),
    (("pessoas", "publico", "audiencia", "destinatario", "grupo"), "Users"),
    (("story", "stories", "celular", "smartphone"), "Smartphone"),
    (("tablet",), "Tablet"),
    (("monitor", "tela", "screen", "display", "device", "dispositivo"), "Monitor"),
    (("mensagem", "message", "chat", "direta"), "MessageCircle"),
    (("audio", "podcast", "waveform", "onda"), "AudioWaveform"),
    (("video", "player", "reel"), "CirclePlay"),
    (("ideia", "idea", "insight", "lampada", "lightbulb", "conceito", "concept"), "Lightbulb"),
    (("post", "feed", "artigo", "texto"), "PanelsTopLeft"),
    (("conexao", "distribuicao", "caminho", "rede"), "Network"),
    (("node", "ponto", "circulo", "periferico", "inerte"), "CircleDot"),
)


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return set(re.findall(r"[a-z0-9]+", normalized))


def discover(query: str, purpose: str, kind: str):
    if kind != "image":
        return {"status": "unsupported", "candidates": []}
    words = _tokens(query)
    if "mockup" in words or "mockups" in words:
        return {"status": "no_semantic_match", "candidates": []}
    if not words.intersection({"icone", "icon", "simbolo", "symbol"}):
        return {"status": "no_semantic_match", "candidates": []}
    match = next(
        (
            (name, sorted(words.intersection(keywords)))
            for keywords, name in ICON_RULES
            if words.intersection(keywords)
        ),
        None,
    )
    if not match:
        return {
            "status": "no_semantic_match",
            "candidates": [],
            "observation": "registered_component_requires_explicit_semantic_match",
        }
    icon, matched_terms = match
    identity = hashlib.sha256(f"{icon}:{query}:{purpose}".encode()).hexdigest()[:20]
    return {
        "status": "candidates",
        "candidates": [
            {
                "id": f"procedural-{identity}",
                "provider": "procedural-icon",
                "providerId": icon,
                "kind": "image",
                "description": f"Ícone vetorial {icon}: {purpose}",
                "query": query,
                "purpose": purpose,
                "licenseUrl": "https://lucide.dev/license",
                "observation": "deterministic_registered_component",
                "semanticMatch": {"terms": matched_terms, "confidence": "rule_exact"},
                "renderReady": False,
            }
        ],
    }
