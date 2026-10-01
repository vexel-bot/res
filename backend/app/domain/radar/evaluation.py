from __future__ import annotations

import math
from dataclasses import dataclass

EVALUATION_VERSION = "radar-eval-v1"


@dataclass(frozen=True)
class RankingExample:
    item_id: str
    cluster_id: str
    predicted_score: float
    relevance: int
    eligible: bool
    expected_eligible: bool


def evaluate_ranking(examples: list[RankingExample], *, k: int = 5) -> dict[str, float | int | str]:
    ranked = sorted(examples, key=lambda item: item.predicted_score, reverse=True)
    top = ranked[:k]
    relevant_total = sum(item.relevance > 0 for item in examples)
    relevant_top = sum(item.relevance > 0 for item in top)
    precision = relevant_top / len(top) if top else 0.0
    recall = relevant_top / relevant_total if relevant_total else 0.0
    dcg = sum((2**item.relevance - 1) / math.log2(index + 2) for index, item in enumerate(top))
    ideal = sorted(examples, key=lambda item: item.relevance, reverse=True)[:k]
    idcg = sum((2**item.relevance - 1) / math.log2(index + 2) for index, item in enumerate(ideal))
    unique_clusters = len({item.cluster_id for item in top})
    duplicate_rate = 1 - unique_clusters / len(top) if top else 0.0
    eligibility_disagreements = sum(item.eligible != item.expected_eligible for item in examples)
    return {
        "evaluationVersion": EVALUATION_VERSION,
        "sampleCount": len(examples),
        "k": k,
        "precisionAtK": round(precision, 4),
        "recallAtK": round(recall, 4),
        "ndcgAtK": round(dcg / idcg if idcg else 0.0, 4),
        "duplicateClusterRateAtK": round(duplicate_rate, 4),
        "eligibilityAgreement": round(
            1 - eligibility_disagreements / len(examples) if examples else 0.0,
            4,
        ),
    }
