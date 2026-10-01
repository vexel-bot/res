"""Discovery metadata ranks inspection order, never proves visual suitability."""

import re
import unicodedata


def tokens(value):
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return set(re.findall(r"[a-z0-9]{3,}", text))


def rank_candidates(requirement, need, project_assets=()):
    core = tokens(" ".join([need.query, getattr(need, "entity", ""), getattr(need, "action", "")]))
    descriptive = tokens(
        " ".join(
            [
                need.purpose,
                getattr(need, "visual_description", ""),
                getattr(need, "appearance", ""),
                *need.acceptance_criteria,
            ]
        )
    )
    preferred = tokens(" ".join(getattr(need, "preferred_criteria", []) or []))
    pool = [
        ({"catalogAssetId": item["id"]}, item, 0 if item["id"] in project_assets else 1)
        for item in requirement.get("candidates", [])
    ]
    pool.extend((item, item, 2) for item in (requirement.get("discovery") or {}).get("candidates", []))
    def score(metadata):
        observed = tokens(metadata)
        # Discovery metadata is only a screening signal. Entity/action terms
        # outweigh art-direction preferences, which can never make a candidate
        # semantically acceptable on their own.
        return 5 * len(core & observed) + 2 * len(descriptive & observed) + len(preferred & observed)

    ranked = sorted(
        enumerate(pool),
        key=lambda pair: (-score(pair[1][1]), pair[1][2], pair[0]),
    )
    result, seen = [], set()
    for _, (candidate, _metadata, _) in ranked:
        key = str(candidate.get("catalogAssetId") or candidate.get("id") or candidate.get("url") or candidate)
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return result
