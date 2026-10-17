"""Pending/stale comparisons never become human aesthetic approval."""

from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from app.domain.studios.visual_study import CreateVisualStudyComparisonV1, VisualStudyComparisonReviewV1
from app.services.studios import visual_study as service


def reference(index):
    return {
        "documentId": f"doc-{index}",
        "documentRevision": 3,
        "assetId": f"asset-{index}",
        "checksum": str(index + 1) * 64,
    }


def test_comparison_requires_three_distinct_renders():
    with pytest.raises(ValidationError, match="three_distinct"):
        CreateVisualStudyComparisonV1(variants=[reference(0)] * 3)


def fixture_session():
    return {
        "id": "session",
        "status": "not_assessed",
        "language": "motion_graphics",
        "variants": {
            label: {
                "reference": reference(i),
                "sourceDigest": "same",
                "briefDigest": "same",
                "recipeDigest": label,
                "provider": "remotion.contextual-v2",
                "studyVariant": variant,
            }
            for i, (label, variant) in enumerate([("A", "a"), ("B", "b"), ("C", "control")])
        },
    }


def test_review_needs_human_visual_evidence_and_stale_checks(monkeypatch):
    session = fixture_session()
    monkeypatch.setattr(service, "sessions", lambda *_: {"session": session})
    monkeypatch.setattr(
        service,
        "_reference",
        lambda _db, _ws, ref: {
            "sourceDigest": "same",
            "briefDigest": "same",
            "recipeDigest": chr(65 + int(ref.asset_id[-1])),
            "provider": "remotion.contextual-v2",
            "review": {},
        },
    )
    monkeypatch.setattr(service, "_visual_approved", lambda *_: False)
    monkeypatch.setattr(service, "_record", lambda *_: None)
    request = VisualStudyComparisonReviewV1(
        preferred_label="A",
        full_video_inspected=True,
        mobile_inspected=True,
        blind_review_completed=True,
        same_materials_confirmed=True,
        control_simplicity_confirmed=True,
        unrecorded_manual_corrections=False,
        notes="Human preference; numeric review still missing",
    )
    assert service.review(None, "ws", "session", request, NS(id="human"))["status"] == "pending"
    monkeypatch.setattr(service, "_visual_approved", lambda *_: True)
    assert service.review(None, "ws", "session", request, NS(id="human"))["status"] == "passed"
    monkeypatch.setattr(service, "_reference", lambda *_: {"sourceDigest": "changed"})
    assert service.project(None, "ws", "session")["status"] == "stale"


def test_control_preference_is_rejected_and_incomplete_viewing_pending(monkeypatch):
    session = fixture_session()
    monkeypatch.setattr(service, "sessions", lambda *_: {"session": session})
    monkeypatch.setattr(service, "fresh", lambda *_: {label: {} for label in "ABC"})
    monkeypatch.setattr(service, "_record", lambda *_: None)
    request = VisualStudyComparisonReviewV1(
        preferred_label="C",
        full_video_inspected=True,
        mobile_inspected=True,
        blind_review_completed=True,
        same_materials_confirmed=True,
        control_simplicity_confirmed=True,
        unrecorded_manual_corrections=False,
        notes="The simple sequence was clearer",
    )
    assert service.review(None, "ws", "session", request, NS(id="human"))["status"] == "rejected"
    request.full_video_inspected = False
    assert service.review(None, "ws", "session", request, NS(id="human"))["status"] == "pending"


def test_experimental_comparison_permission(client, monkeypatch):
    from conftest import register

    from app.config import get_settings

    token, workspace = register(client, "visual-study-owner@example.com")
    path = f"/api/v1/studios/v1/workspaces/{workspace}/visual-study-comparisons/session"
    assert client.get(path, headers={"Authorization": "Bearer " + token}).status_code == 404
    monkeypatch.setattr(get_settings(), "studio_visual_quality_indicator_enabled", True)
    foreign, _ = register(client, "visual-study-foreign@example.com")
    assert client.get(path, headers={"Authorization": "Bearer " + foreign}).status_code in {403, 404}


def test_real_event_store_empty_and_latest_receipt(client):
    from conftest import register
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import Membership

    _, workspace = register(client, "visual-study-events@example.com")
    with SessionLocal() as db:
        assert service.sessions(db, workspace) == {}
        user_id = db.scalar(select(Membership).where(Membership.workspace_id == workspace)).user_id
        value = {**fixture_session(), "workspaceId": workspace}
        service._record(db, workspace, value, NS(id=user_id))
        assert service.sessions(db, workspace)["session"]["status"] == "not_assessed"
        service._record(db, workspace, {**value, "status": "pending"}, NS(id=user_id))
        assert service.sessions(db, workspace)["session"]["status"] == "pending"


def test_woff2_upload_validates_contents_and_scope(client, monkeypatch, tmp_path):
    from pathlib import Path

    from conftest import register

    from app.routers import assets

    monkeypatch.setattr(assets.settings, "storage_path", str(tmp_path))
    token, workspace = register(client, "font-owner@example.com")
    root = Path(__file__).resolve().parents[2]
    font = root / "node_modules/@fontsource-variable/manrope/files/manrope-latin-wght-normal.woff2"
    data = {"workspace_id": workspace, "title": "Manrope licensed study"}
    headers = {"Authorization": "Bearer " + token}
    malformed = client.post(
        "/api/v1/assets/upload",
        data=data,
        headers=headers,
        files={"file": ("fake.woff2", b"wOF2" + bytes(44), "font/woff2")},
    )
    assert malformed.status_code == 422
    uploaded = client.post(
        "/api/v1/assets/upload",
        data=data,
        headers=headers,
        files={"file": (font.name, font.read_bytes(), "font/woff2")},
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["mediaType"] == "font/woff2"
