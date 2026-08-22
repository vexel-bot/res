from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class NormalizedSignal:
    source: str
    url: str
    title: str
    summary: str
    raw_text: str
    published_at: datetime
    expires_at: datetime
    language: str = "pt-BR"
    region: str = "BR"
    category: str = "general"
    topics: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class SourceConnector(ABC):
    @abstractmethod
    def collect(self) -> list[NormalizedSignal]:
        """Collect legal source data and return bounded, normalized records."""
