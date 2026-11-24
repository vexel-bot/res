"""Deterministic intent retrieval; a search miss is not a capability verdict."""
import json
import re
import unicodedata


GROUPS = (
    "camera cameras framing enquadramento angulo perspectiva lens depth profundidade 3d",
    "light lights lighting luz luzes iluminacao shadow sombra",
    "text texto tipografia font fonte typography size tamanho",
    "audio sound som volume music musica levels",
    "motion movimento animation animacao keyframes keys easing",
    "mask mascara matte recorte rotoscopia tracking rastreamento",
    "script scripting jsx codigo layers camada camadas",
    "color cor cores grading contraste exposure exposicao",
)


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value).casefold()) if not unicodedata.combining(c))


def rank(items, query):
    terms = set(re.findall(r"[\w]+", normalized(query))) - {"de", "da", "do", "e", "com", "the", "and", "a"}
    expanded = set(terms)
    for group in GROUPS:
        words = set(group.split())
        if terms & words:
            expanded |= words
    scored = []
    for index, item in enumerate(items):
        text = normalized(json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else item)
        score = sum(4 for term in terms if term in text) + sum(1 for term in expanded - terms if term in text)
        if not terms or score:
            scored.append((-score, index, item))
    return [item for _, _, item in sorted(scored)]


def search_result(items, query, offset=0, limit=70):
    if type(offset) is not int or offset < 0:
        raise ValueError("craft_capability_offset_invalid")
    matches = rank(items, query)
    return {"commands": matches[offset:offset + limit], "total": len(matches), "offset": offset,
            "searchStatus": "matches" if matches else "no_matches",
            "suggestedCategories": [] if matches else ["camera", "light", "text", "audio", "motion", "mask", "script"],
            "interpretation": "Search relevance, not proof of execution or proof of absence."}
