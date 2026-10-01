from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from .contracts import StudioContract


class StudioDomainEventV1(StudioContract):
    schema_version: str = "studio.domain-event.v1"
    event_id: str
    event_type: str
    workspace_id: str
    aggregate_type: str
    aggregate_id: str
    correlation_id: str
    actor_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
