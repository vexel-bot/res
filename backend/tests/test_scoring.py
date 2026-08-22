from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.domain.radar.scoring import SCORE_VERSION, rank_signal


@dataclass
class Signal:
    title: str = "Novo hábito de pedidos por delivery em restaurantes locais"
    summary: str = "Donos de restaurantes aumentam vendas com cardápio digital e delivery"
    topics: list[str] = field(default_factory=lambda: ["restaurantes", "delivery"])
    entities: list[str] = field(default_factory=list)
    region: str = "BR"
    published_at: datetime = field(default_factory=lambda: datetime.now(UTC) - timedelta(hours=2))
    metrics: dict = field(default_factory=lambda: {"novelty_score": 70, "momentum_score": 60})


@dataclass
class Brand:
    target_audience: str = "donos de restaurantes locais que querem aumentar pedidos por delivery"
    keywords: list[str] = field(default_factory=lambda: ["restaurante", "delivery", "cardápio digital"])
    products: list[dict] = field(
        default_factory=lambda: [{"name": "Cardápio digital", "description": "mais pedidos por delivery"}]
    )
    watchlist: dict = field(default_factory=lambda: {"nicho": ["restaurantes", "delivery"]})
    pillars: list[str] = field(default_factory=lambda: ["gestão de restaurantes", "vendas por delivery"])
    industry: str = "tecnologia para restaurantes"
    regions: list[str] = field(default_factory=lambda: ["BR"])
    prohibited_topics: list[str] = field(default_factory=list)


def test_score_is_reproducible_and_explainable():
    now = datetime(2026, 8, 3, 12, tzinfo=UTC)
    signal = Signal(published_at=now - timedelta(hours=2))
    first = rank_signal(signal, Brand(), now)
    second = rank_signal(signal, Brand(), now)
    assert first == second
    assert first.eligible
    assert first.score >= 50
    assert first.breakdown["momentum"] == 60
    assert SCORE_VERSION == "radar-v1.1"


def test_expired_or_prohibited_connections_are_rejected():
    now = datetime.now(UTC)
    expired = Signal(published_at=now - timedelta(days=30))
    assert not rank_signal(expired, Brand(), now).eligible
    prohibited_brand = Brand(prohibited_topics=["delivery"])
    result = rank_signal(Signal(), prohibited_brand, now)
    assert not result.eligible
    assert result.breakdown["risk"] == 100
