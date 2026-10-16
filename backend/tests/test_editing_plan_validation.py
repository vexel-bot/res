"""Content evidence must accelerate reads without hiding invalid or changed history."""
# ruff: noqa: F811
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import update
from test_editing_plan_projection import STAMP, add, plan
from test_editing_plan_projection import db as db

from app.database import SessionLocal
from app.models import StudioDomainEvent
from app.services.studios import contextual_editing as plans
from app.services.studios import editing_plan_validation as validation


@pytest.fixture(autouse=True)
def isolated_validation_facts():
    validation._validated_revisions.clear()
    yield
    validation._validated_revisions.clear()


def seed(db):
    for index, revision in enumerate([1, 9, 9]):
        raw = plan("shared", revision=revision)
        raw["costBasis"] = f"event-{index}"
        add(db, f"event-{index}", raw, stamp=STAMP + timedelta(seconds=index))
    db.commit()
    db.expunge_all()


def test_warm_history_only_parses_selected_and_returned_plan_is_independent(db, monkeypatch):
    seed(db)
    original = plans.parse_editing_plan
    calls = []

    def counted(raw):
        calls.append(raw["costBasis"])
        return original(raw)

    monkeypatch.setattr(plans, "parse_editing_plan", counted)
    selected = plans.get_plan(db, "workspace", "shared")
    assert calls == ["event-0", "event-1", "event-2", "event-2"]
    assert selected.cost_basis == "event-2"
    assert not any(isinstance(value, StudioDomainEvent) for value in db.identity_map.values())
    selected.cost_basis = "caller-edit"
    selected.revision = 1000
    selected.draft_document.title = "caller-edit"
    calls.clear()
    again = plans.get_plan(db, "workspace", "shared")
    assert calls == ["event-2"] and again.cost_basis == "event-2" and again.revision == 9
    assert again.draft_document.title != "caller-edit"


def test_corruption_of_old_event_after_warming_is_rejected_every_time(db):
    seed(db)
    plans.get_plan(db, "workspace", "shared")
    bad = plan("shared", revision=1)
    bad["revision"] = 0
    db.execute(update(StudioDomainEvent).where(StudioDomainEvent.id == "event-0")
               .values(payload={"plan": bad}).execution_options(synchronize_session=False))
    db.commit()
    for _ in range(2):
        with pytest.raises(ValidationError):
            plans.get_plan(db, "workspace", "shared")
    # Three valid original facts; failed content was never inserted.
    assert len(validation._validated_revisions._entries) == 3


def test_changed_bytes_at_same_id_update_selection_and_evidence(db):
    seed(db)
    plans.get_plan(db, "workspace", "shared")
    changed = plan("shared", revision=1)
    changed["costBasis"] = "changed same ID"
    db.execute(update(StudioDomainEvent).where(StudioDomainEvent.id == "event-2")
               .values(payload={"plan": changed}).execution_options(synchronize_session=False))
    db.commit()
    assert plans.get_plan(db, "workspace", "shared").cost_basis == "event-1"
    add(db, "new", plan("shared", revision=10), stamp=STAMP + timedelta(seconds=5))
    db.commit()
    assert plans.get_plan(db, "workspace", "shared").revision == 10


def test_cached_validation_never_conceals_unflushed_nested_orm_mutation(db):
    seed(db)
    plans.get_plan(db, "workspace", "shared")
    loaded = db.get(StudioDomainEvent, "event-0")
    loaded.payload["plan"]["revision"] = 0
    assert loaded not in db.dirty  # Plain nested JSON changes aren't tracked by this mapping.
    with pytest.raises(ValidationError):
        plans.get_plan(db, "workspace", "shared")


def test_existing_orm_event_context_preserves_in_memory_payload(db):
    seed(db)
    loaded = db.get(StudioDomainEvent, "event-2")
    loaded.payload["plan"]["costBasis"] = "unflushed selected value"
    assert plans.get_plan(db, "workspace", "shared").cost_basis == "unflushed selected value"
    assert not validation._validated_revisions._entries


def test_eviction_is_bounded_and_does_not_change_selection(db, monkeypatch):
    small = validation._ValidatedRevisions(max_entries=2)
    monkeypatch.setattr(validation, "_validated_revisions", small)
    seed(db)
    for _ in range(2):
        assert plans.get_plan(db, "workspace", "shared").cost_basis == "event-2"
        assert len(small._entries) == 2
        assert all(isinstance(value, int) for value in small._entries.values())
        assert all(isinstance(key[-1], bytes) and len(key[-1]) == 32 for key in small._entries)


def test_scope_empty_and_rolled_back_events_are_requeried(db):
    seed(db)
    plans.get_plan(db, "workspace", "shared")
    with pytest.raises(ValueError, match="editing_plan_not_found"):
        plans.get_plan(db, "outside", "shared")
    with pytest.raises(ValueError, match="editing_plan_not_found"):
        plans.get_plan(db, "workspace", "absent")
    add(db, "transient", plan("shared", revision=20), stamp=STAMP + timedelta(seconds=8))
    db.flush()
    db.expunge_all()
    assert plans.get_plan(db, "workspace", "shared").revision == 20
    db.rollback()
    assert plans.get_plan(db, "workspace", "shared").revision == 9


def test_concurrent_readers_get_fresh_independent_plans(db):
    seed(db)

    def read_and_edit(_):
        with SessionLocal() as session:
            current = plans.get_plan(session, "workspace", "shared")
            observed = (current.revision, current.cost_basis)
            current.revision = 100
            current.cost_basis = "caller change"
            return observed

    with ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(read_and_edit, range(6))) == [(9, "event-2")] * 6
