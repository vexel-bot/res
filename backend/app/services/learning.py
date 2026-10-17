from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.radar.scoring import SCORE_VERSION, WEIGHTS
from ..models import Campaign, FeedbackEvent, Opportunity, Post, PostMetricSnapshot

MAX_FEATURE_BIAS = 0.12
MIN_PERFORMANCE_SAMPLES = 3


@dataclass(frozen=True)
class PreferenceProfile:
    workspace_id: str
    feature_bias: dict[str, float]
    explicit_events: int
    performance_samples: int
    performance_active: bool

    @property
    def status(self) -> str:
        if self.performance_active:
            return "feedback_and_performance"
        if self.explicit_events:
            return "explicit_feedback"
        return "no_feedback"

    def as_dict(self) -> dict:
        return {
            "workspaceId": self.workspace_id,
            "scoreVersion": SCORE_VERSION,
            "featureBias": self.feature_bias,
            "explicitEvents": self.explicit_events,
            "performanceSamples": self.performance_samples,
            "performanceActive": self.performance_active,
            "status": self.status,
        }


def _event_valence(event: FeedbackEvent) -> float:
    if event.event_type == "chosen":
        return 1.0
    if event.event_type == "rejected":
        return -1.0
    if event.event_type == "rated":
        try:
            return max(-1.0, min(1.0, (float((event.payload or {}).get("rating")) - 3.0) / 2.0))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _latest_performance_rows(db: Session, workspace_id: str) -> list[tuple[PostMetricSnapshot, Opportunity]]:
    rows = db.execute(
        select(PostMetricSnapshot, Opportunity)
        .join(Post, Post.id == PostMetricSnapshot.post_id)
        .join(Campaign, Campaign.id == Post.campaign_id)
        .join(Opportunity, Opportunity.id == Campaign.opportunity_id)
        .where(PostMetricSnapshot.workspace_id == workspace_id)
        .order_by(PostMetricSnapshot.observed_at.desc(), PostMetricSnapshot.created_at.desc())
    ).all()
    latest: dict[str, tuple[PostMetricSnapshot, Opportunity]] = {}
    for snapshot, opportunity in rows:
        latest.setdefault(snapshot.post_id, (snapshot, opportunity))
    return list(latest.values())


def workspace_preference_profile(db: Session, workspace_id: str) -> PreferenceProfile:
    numerators = {feature: 0.0 for feature in WEIGHTS}
    denominators = {feature: 0.0 for feature in WEIGHTS}
    explicit_events = 0
    rows = db.execute(
        select(FeedbackEvent, Opportunity)
        .join(Opportunity, Opportunity.id == FeedbackEvent.opportunity_id)
        .where(
            FeedbackEvent.workspace_id == workspace_id,
            FeedbackEvent.event_type.in_(("chosen", "rejected", "rated")),
        )
        .order_by(FeedbackEvent.occurred_at.desc())
    ).all()
    latest_explicit: dict[str, tuple[FeedbackEvent, Opportunity]] = {}
    for event, opportunity in rows:
        latest_explicit.setdefault(opportunity.id, (event, opportunity))
    for event, opportunity in latest_explicit.values():
        valence = _event_valence(event)
        if not valence:
            continue
        explicit_events += 1
        breakdown = opportunity.score_breakdown or {}
        for feature in WEIGHTS:
            strength = max(0.0, min(1.0, float(breakdown.get(feature, 0.0)) / 100.0))
            numerators[feature] += valence * strength
            denominators[feature] += abs(valence)

    performance_rows = _latest_performance_rows(db, workspace_id)
    performance_rates: list[tuple[float, Opportunity]] = []
    for snapshot, opportunity in performance_rows:
        metrics = snapshot.metrics or {}
        reach = float(metrics.get("reach") or 0)
        if reach <= 0:
            continue
        interactions = sum(float(metrics.get(name) or 0) for name in ("likes", "comments", "shares", "saves"))
        performance_rates.append((interactions / reach, opportunity))
    performance_active = len(performance_rates) >= MIN_PERFORMANCE_SAMPLES
    if performance_active:
        ordered = sorted(performance_rates, key=lambda row: row[0])
        divisor = max(1, len(ordered) - 1)
        tied_rank = {}
        for rate in {row[0] for row in ordered}:
            indexes = [index for index, row in enumerate(ordered) if row[0] == rate]
            tied_rank[rate] = sum(indexes) / len(indexes)
        for rate, opportunity in ordered:
            valence = (tied_rank[rate] / divisor) * 2.0 - 1.0
            breakdown = opportunity.score_breakdown or {}
            for feature in WEIGHTS:
                strength = max(0.0, min(1.0, float(breakdown.get(feature, 0.0)) / 100.0))
                numerators[feature] += valence * strength * 0.5
                denominators[feature] += abs(valence) * 0.5

    bias = {
        feature: round(max(-MAX_FEATURE_BIAS, min(MAX_FEATURE_BIAS, numerators[feature] / denominators[feature])), 4)
        if denominators[feature]
        else 0.0
        for feature in WEIGHTS
    }
    return PreferenceProfile(
        workspace_id=workspace_id,
        feature_bias=bias,
        explicit_events=explicit_events,
        performance_samples=len(performance_rates),
        performance_active=performance_active,
    )


def preference_adjustment(breakdown: dict[str, float], profile: PreferenceProfile) -> float:
    adjustment = sum(
        float(breakdown.get(feature, 0.0)) * WEIGHTS[feature] * profile.feature_bias[feature] for feature in WEIGHTS
    )
    return round(max(-8.0, min(8.0, adjustment)), 2)
