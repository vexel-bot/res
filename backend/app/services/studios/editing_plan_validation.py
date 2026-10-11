"""Bounded validation facts keyed by complete event content, never cached plans."""
import hashlib
import json
from collections import OrderedDict
from threading import RLock

from sqlalchemy import String, cast, select

from ...models import StudioDomainEvent


class _ValidatedRevisions:
    def __init__(self, max_entries=1024):
        self.max_entries = max_entries
        self._entries = OrderedDict()
        self._lock = RLock()

    def get(self, key):
        with self._lock:
            revision = self._entries.get(key)
            if revision is not None:
                self._entries.move_to_end(key)
            return revision

    def remember(self, key, revision):
        with self._lock:
            self._entries[key] = revision
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self):
        with self._lock:
            self._entries.clear()


_validated_revisions = _ValidatedRevisions()


def load_validated_plan(db, workspace_id, plan_id, parser):
    # CAST avoids ORM JSON hydration while still reading every current event.
    # IDs/revisions/timestamps alone never establish unchanged valid content.
    events = db.execute(select(StudioDomainEvent.id, cast(StudioDomainEvent.payload, String)).where(
        StudioDomainEvent.workspace_id == workspace_id,
        StudioDomainEvent.event_type == "studio.editing.plan",
        StudioDomainEvent.aggregate_id == plan_id,
    ).order_by(StudioDomainEvent.occurred_at, StudioDomainEvent.id)).all()
    if not events:
        raise ValueError("editing_plan_not_found")
    selected_text, selected_revision = None, -1
    for event_id, raw in events:
        fingerprint = hashlib.sha256(raw.encode("utf-8")).digest()
        key = (parser, workspace_id, event_id, fingerprint)
        revision = _validated_revisions.get(key)
        if revision is None:
            # Validate before storing a fact; invalid history cannot become a hit.
            revision = parser(json.loads(raw)["plan"]).revision
            _validated_revisions.remember(key, revision)
        if revision >= selected_revision:
            selected_text, selected_revision = raw, revision
    # Always return a freshly parsed model. Caller edits must never poison facts
    # or change the result seen by another request. Full selected evidence stays.
    return parser(json.loads(selected_text)["plan"])
