"""Latest-document projection must preserve event ordering without hydrating history."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import event
from test_contextual_editing import document

from app.database import SessionLocal
from app.domain.studios.contextual_editing import ContextualEditPlanV1
from app.models import StudioDomainEvent, Workspace
from app.services.studios.contextual_editing import PLAN_EVENT, get_plan, latest_plan

STAMP = datetime(2026, 10, 5, tzinfo=UTC)


def plan(plan_id, document_id="document", revision=1, created_at=STAMP):
    doc = document()
    doc.document_id = document_id
    return ContextualEditPlanV1(
        id=plan_id, revision=revision, workspace_id="workspace", document_id=document_id,
        document_revision=doc.revision, source_digest="a" * 64, source_assets={},
        intent={"objective": "Preserve the authored message"}, operations=[], blockers=[],
        status="ready", estimated_cost_cents=0, cost_basis="test", draft_document=doc,
        created_at=created_at,
    ).model_dump(mode="json", by_alias=True)


def add(db, event_id, raw, *, stamp=STAMP, workspace="workspace", kind=PLAN_EVENT):
    db.add(StudioDomainEvent(
        id=event_id, workspace_id=workspace, event_type=kind, aggregate_type="editing_plan",
        aggregate_id=raw.get("id", "invalid"), correlation_id="projection-test",
        payload={"plan": raw}, occurred_at=stamp,
    ))


@pytest.fixture
def db():
    with SessionLocal() as session:
        session.add_all([Workspace(id="workspace", name="Projection"),
                         Workspace(id="outside", name="Other workspace")])
        session.commit()
        yield session


def test_latest_scopes_document_workspace_and_event_type_and_hydrates_one(db):
    add(db, "old", plan("old", revision=20))
    add(db, "current", plan("current"), stamp=STAMP + timedelta(seconds=1))
    add(db, "wrong-document", plan("wrong-doc", "another"), stamp=STAMP + timedelta(seconds=2))
    add(db, "wrong-workspace", plan("outside"), workspace="outside", stamp=STAMP + timedelta(seconds=3))
    add(db, "wrong-type", plan("type"), kind="studio.other", stamp=STAMP + timedelta(seconds=4))
    # Unrelated malformed historical data must not be deserialized/validated.
    add(db, "irrelevant-invalid", {"documentId": "another", "largeHistory": "x" * 100_000})
    db.commit()
    db.expunge_all()
    loaded = []

    def on_load(instance, context):
        loaded.append(instance.id)

    event.listen(StudioDomainEvent, "load", on_load)
    try:
        selected = latest_plan(db, SimpleNamespace(id="document", workspace_id="workspace"))
    finally:
        event.remove(StudioDomainEvent, "load", on_load)
    assert selected.id == "current" and selected.revision == 1
    assert loaded == ["current"]


def test_equal_persisted_timestamps_use_id_not_revision_or_client_clock(db):
    # Insert the winning ID first to ensure insertion order isn't the decision.
    add(db, "z-event", plan("new-sibling", revision=1, created_at=STAMP - timedelta(days=1)))
    add(db, "a-event", plan("old-sibling", revision=99, created_at=STAMP + timedelta(days=1)))
    db.commit()
    assert latest_plan(db, SimpleNamespace(id="document", workspace_id="workspace")).id == "new-sibling"


def test_no_matching_document_returns_none(db):
    add(db, "event", plan("different", "another"))
    db.commit()
    assert latest_plan(db, SimpleNamespace(id="document", workspace_id="workspace")) is None


def test_malformed_newest_plan_fails_without_fallback(db):
    add(db, "old", plan("valid"))
    add(db, "new", {"id": "bad", "documentId": "document"}, stamp=STAMP + timedelta(seconds=1))
    db.commit()
    with pytest.raises(ValidationError):
        latest_plan(db, SimpleNamespace(id="document", workspace_id="workspace"))


def test_get_plan_still_chooses_highest_revision_and_latest_tie(db):
    high = plan("shared", revision=9)
    high["costBasis"] = "first-high"
    add(db, "a", high)
    tie = {**high, "costBasis": "last-high"}
    add(db, "b", tie, stamp=STAMP + timedelta(seconds=1))
    add(db, "c", plan("shared", revision=1), stamp=STAMP + timedelta(seconds=2))
    db.commit()
    assert get_plan(db, "workspace", "shared").cost_basis == "last-high"


def test_get_plan_still_rejects_invalid_historical_revision(db):
    add(db, "a", {"id": "shared", "documentId": "document"})
    add(db, "b", plan("shared", revision=2), stamp=STAMP + timedelta(seconds=1))
    db.commit()
    with pytest.raises(ValidationError):
        get_plan(db, "workspace", "shared")
