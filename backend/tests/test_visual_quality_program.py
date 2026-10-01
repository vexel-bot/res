from types import SimpleNamespace as NS

import pytest
from conftest import register

from app.domain.studios.editorial_production import ProductionRequestV1
from app.domain.studios.visual_audit import VisualComparisonReviewV1
from app.services.studios.visual_quality_program import material_readiness, render_quality


def _render(receipt=None, *, checksum="a" * 64, revision=2, technical="passed", manual=False):
    asset = NS(
        id="render",
        lifecycle_status="active",
        workspace_id="workspace",
        checksum_sha256="a" * 64,
        object_metadata={
            "documentId": "document",
            "documentRevision": 2,
            **({"visualHumanReview": receipt} if receipt else {}),
        },
    )
    document = NS(id="document", workspace_id="workspace", revision=2)
    state = {
        "id": "run",
        "documentRevision": revision,
        "request": {"qualityPhaseId": "visual-quality-2026-10-01"},
        "technicalEvaluation": {"status": technical},
        "autonomousProductionQualified": True,
        "history": [{"revision": 1}] if manual else [],
        "artifacts": {"video": {"artifact": {"assetId": "render", "checksumSha256": checksum}}},
    }
    return render_quality(state, asset, document)


def test_quality_review_requires_current_checksum_revision_and_complete_playback():
    receipt = {
        "assetId": "render",
        "renderChecksum": "a" * 64,
        "expectedDocumentRevision": 2,
        "status": "meets_human_criteria",
        "clarity": 4,
        "rhythm": 4,
        "continuity": 4,
        "finish": 4,
    }
    assert _render(receipt)["visualStatus"] == "not_assessed"
    receipt.update(fullVideoInspected=True, mobileInspected=True)
    assert _render(receipt)["visualStatus"] == "approved"
    assert _render(receipt)["autonomyStatus"] == "demonstrated"
    assert _render(receipt, manual=True)["autonomyStatus"] == "assisted"
    assert _render(receipt, checksum="b" * 64)["visualStatus"] == "not_assessed"
    assert "render_checksum_mismatch" in _render(receipt, checksum="b" * 64)["blockers"]
    assert "document_revision_stale" in _render(receipt, revision=1)["blockers"]
    assert _render(receipt, technical="failed")["technicalStatus"] == "failed"
    assert "technical_qc_not_passed" in _render(receipt, technical="failed")["blockers"]


def test_phase_contract_rejects_visual_only_or_wrong_duration():
    base = {
        "direction": {
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Produto", "script": "Mostrar o produto.", "lockedFacts": ["Mostrar o produto."]},
        },
        "qualityPhaseId": "visual-quality-2026-10-01",
    }
    assert ProductionRequestV1.model_validate(base).quality_phase_id
    for override in ({"durationSeconds": 11}, {"evaluationScope": "visual_only"}, {"mode": "motion"}):
        with pytest.raises(ValueError, match="visual_quality_phase_requires_15s_audiovisual_montage"):
            ProductionRequestV1.model_validate({**base, **override})


def test_material_readiness_needs_observable_action_and_real_brand_asset():
    payload = {
        "brief": {"objective": "Mostrar preparo"},
        "brandMemoryRef": {"id": "brand"},
        "assets": [
            {"mediaType": "video/mp4", "checksum": "a" * 64, "rightsStatus": "verified"},
            {"mediaType": "video/mp4", "checksum": "b" * 64, "rightsStatus": "verified"},
            {
                "mediaType": "image/png",
                "checksum": "c" * 64,
                "rightsStatus": "verified",
                "provenance": {"editingResource": {"assetRole": "product", "kind": "image"}},
            },
        ],
    }
    assert material_readiness(payload)["blockers"] == ["observable_action_evidence_missing"]
    payload["assets"][0]["provenance"] = {"editingResource": {"motionDescription": "Mão abre a embalagem"}}
    payload["assets"][1]["provenance"] = {"editingResource": {"motionDescription": "Café cai na xícara"}}
    assert material_readiness(payload)["status"] == "ready"


def test_indicator_is_flagged_and_owner_only(client, monkeypatch):
    from sqlalchemy import select

    from app.config import get_settings
    from app.database import SessionLocal
    from app.models import Membership, User

    owner_token, workspace = register(client, "quality-owner@example.com")
    viewer_token, _ = register(client, "quality-viewer@example.com")
    url = f"/api/v1/studios/v1/workspaces/{workspace}/visual-quality"
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_visual_quality_indicator_enabled", False)
    assert client.get(url, headers={"Authorization": f"Bearer {owner_token}"}).status_code == 404
    monkeypatch.setattr(settings, "studio_visual_quality_indicator_enabled", True)
    response = client.get(url, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200, response.text
    assert response.json()["phaseStatus"] == "pending"
    with SessionLocal() as db:
        viewer = db.scalar(select(User).where(User.email == "quality-viewer@example.com"))
        db.add(Membership(user_id=viewer.id, workspace_id=workspace, role="Viewer"))
        db.commit()
    assert client.get(url, headers={"Authorization": f"Bearer {viewer_token}"}).status_code == 403


def test_shared_phase_reservation_counts_other_runs_and_unknown_attempts(monkeypatch):
    from app.config import get_settings
    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_gemini_test_budget_usd", 10)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 10)
    monkeypatch.setattr("app.services.studios.contextual_editing.lock_editing_budget", lambda *_: None)
    group = "visual-quality-2026-10-01"
    spent = NS(
        correlation_id="run-one",
        status="retrying",
        request_payload={"environment": "test", "budgetGroupId": group, "input": {"operation": "plan"}},
        result_payload={
            "testReservationUsd": 9.95,
            "budgetCategory": "planning",
            "submissionStarted": True,
            "submissionOutcome": "unknown",
        },
    )
    current = NS(
        workspace_id="workspace",
        correlation_id="run-two",
        status="queued",
        provider="google.gemini-editing",
        job_type="editing_gemini",
        request_payload={
            "environment": "test",
            "budgetGroupId": group,
            "input": {"operation": "plan"},
            "budgetAllocations": {"planning": 1, "image": 0, "critique": 0, "video": 0},
            "maxPromptChars": 1000,
            "maxOutputTokens": 256,
            "pricing": {"inputUsdPerMillion": 2, "outputUsdPerMillion": 8},
        },
        result_payload={},
    )

    class Rows:
        def __init__(self, values):
            self.values = values

        def all(self):
            return self.values

    class DB:
        def __init__(self):
            self.calls = 0

        def scalars(self, _query):
            self.calls += 1
            return Rows([current] if self.calls == 1 else [spent, current])

    with pytest.raises(ValueError, match="visual_quality_phase_budget_exceeded"):
        reserve_test_request(DB(), current, 1)


def test_phase_run_stops_before_provider_when_materials_are_missing(monkeypatch):
    from app.config import get_settings
    from app.services.studios.editorial_production import create_run

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_visual_quality_indicator_enabled", True)
    request = ProductionRequestV1.model_validate(
        {
            "direction": {
                "expectedDocumentRevision": 1,
                "intent": {
                    "objective": "Produto",
                    "script": "Mostrar o produto.",
                    "lockedFacts": ["Mostrar o produto."],
                },
            },
            "qualityPhaseId": "visual-quality-2026-10-01",
            "nativeSceneEditing": True,
        }
    )
    record = NS(
        canonical_document={"brief": {"objective": "Produto"}, "brandMemoryRef": {"id": "brand"}, "assets": []},
        document=None,
    )
    with pytest.raises(ValueError, match="visual_quality_materials_pending"):
        create_run(None, record, request, NS(id="user"), "missing-materials")


def test_shared_phase_budget_is_global_in_real_database(client, monkeypatch):
    from app.config import get_settings
    from app.database import SessionLocal
    from app.models import StudioGenerationJob
    from app.services.studios.gemini_editing import reserve_test_request

    _, first_workspace = register(client, "budget-first@example.com")
    _, second_workspace = register(client, "budget-second@example.com")
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_gemini_test_budget_usd", 10)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 10)
    group = "visual-quality-2026-10-01"
    with SessionLocal() as db:
        previous = StudioGenerationJob(
            workspace_id=first_workspace,
            job_type="editing_gemini",
            provider="google.gemini-editing",
            idempotency_key="previous",
            payload_hash="a" * 64,
            correlation_id="first-run",
            status="retrying",
            request_payload={"environment": "test", "budgetGroupId": group, "input": {"operation": "plan"}},
            result_payload={"testReservationUsd": 9.95, "budgetCategory": "planning",
                            "submissionStarted": True, "submissionOutcome": "unknown"},
        )
        current = StudioGenerationJob(
            workspace_id=second_workspace,
            job_type="editing_gemini",
            provider="google.gemini-editing",
            idempotency_key="current",
            payload_hash="b" * 64,
            correlation_id="second-run",
            status="queued",
            request_payload={
                "environment": "test", "budgetGroupId": group, "input": {"operation": "plan"},
                "budgetAllocations": {"planning": 1, "image": 0, "critique": 0, "video": 0},
                "maxPromptChars": 1000, "maxOutputTokens": 256,
                "pricing": {"inputUsdPerMillion": 2, "outputUsdPerMillion": 8},
            },
            result_payload={},
        )
        db.add_all([previous, current])
        db.commit()
        with pytest.raises(ValueError, match="visual_quality_phase_budget_exceeded"):
            reserve_test_request(db, current, 1)
        assert not current.result_payload
        # Measured cost replaces the conservative reservation, freeing only the proven difference.
        previous.result_payload = {**previous.result_payload, "measuredCostUsd": 9.90}
        db.commit()
        reserve_test_request(db, current, 1)
        assert current.result_payload["testReservationUsd"] == 0.1
        db.commit()


def test_blind_comparison_binds_two_current_edits_and_fifteen_second_control(monkeypatch):
    from app.services.studios import visual_quality_comparison as service

    document = NS(id="document", workspace_id="workspace", revision=2)
    sources = {"source-1": "1" * 64, "source-2": "2" * 64}

    def make_run(run_id, checksum):
        return {
            "id": run_id,
            "documentRevision": 2,
            "sourceChecksums": sources,
            "request": {"qualityPhaseId": "visual-quality-2026-10-01"},
            "requestDigest": run_id,
            "technicalEvaluation": {"status": "passed"},
            "artifacts": {"video": {"artifact": {"assetId": run_id + "-asset", "checksumSha256": checksum}}},
        }

    states = {"edit-a": make_run("edit-a", "a" * 64), "edit-b": make_run("edit-b", "b" * 64)}

    def render_asset(run_id, checksum):
        return NS(
            id=run_id + "-asset",
            workspace_id="workspace",
            lifecycle_status="active",
            checksum_sha256=checksum,
            object_metadata={
                "documentId": "document",
                "documentRevision": 2,
                "visualHumanReview": {
                    "assetId": run_id + "-asset",
                    "renderChecksum": checksum,
                    "expectedDocumentRevision": 2,
                    "status": "meets_human_criteria",
                    "fullVideoInspected": True,
                    "mobileInspected": True,
                    "clarity": 4,
                    "rhythm": 4,
                    "continuity": 4,
                    "finish": 4,
                },
            },
        )

    assets = {
        "edit-a-asset": render_asset("edit-a", "a" * 64),
        "edit-b-asset": render_asset("edit-b", "b" * 64),
        "control": NS(
            id="control",
            workspace_id="workspace",
            lifecycle_status="active",
            media_type="video/mp4",
            checksum_sha256="c" * 64,
            object_metadata={
                "editingResource": {
                    "technical": {
                        "probe": {
                            "durationMicroseconds": 15_000_000,
                            "videoStreams": [{"width": 1080, "height": 1920}],
                            "audioStreams": [{}],
                        }
                    }
                }
            },
        ),
        **{
            source_id: NS(workspace_id="workspace", lifecycle_status="active", checksum_sha256=checksum,
                          object_metadata={"editingResource": {"technical": {"durationMicroseconds": 10_000_000}}})
            for source_id, checksum in sources.items()
        },
    }
    monkeypatch.setattr(service, "get_run", lambda _db, _doc, run_id: states[run_id])
    monkeypatch.setattr(
        service,
        "record_to_contract",
        lambda _doc: NS(
            assets=[
                NS(id=source_id, checksum=checksum, rights_status="verified", media_type="video/mp4")
                for source_id, checksum in sources.items()
            ]
        ),
    )
    events = []
    monkeypatch.setattr(service, "emit_event", lambda *args, **kwargs: events.append(kwargs))
    db = NS(get=lambda _model, asset_id: assets.get(asset_id), commit=lambda: None)
    request = VisualComparisonReviewV1.model_validate(
        {
            "expectedDocumentRevision": 2,
            "editARunId": "edit-a",
            "editBRunId": "edit-b",
            "editAChecksum": "a" * 64,
            "editBChecksum": "b" * 64,
            "controlAssetId": "control",
            "controlChecksum": "c" * 64,
            "controlEdl": [
                {"assetId": "source-1", "startSeconds": 0, "durationSeconds": 7.5},
                {"assetId": "source-2", "startSeconds": 0, "durationSeconds": 7.5},
            ],
            "preferred": "edit_a",
            "blindReviewCompleted": True,
            "normalSpeedInspected": True,
            "mobileInspected": True,
            "straightConcatenationConfirmed": True,
            "sameMaterialsConfirmed": True,
            "unrecordedManualCorrections": False,
            "notes": "A montagem dirigida sustenta melhor a ação.",
        }
    )
    receipt = service.record_visual_comparison(db, document, request, NS(id="reviewer"))
    assert receipt["status"] == "passed"
    assert receipt["editAChecksum"] == "a" * 64
    assert events[0]["aggregate_type"] == "visual-quality-comparison"
    with pytest.raises(ValueError, match="visual_comparison_viewed_render_changed"):
        service.record_visual_comparison(
            db, document, request.model_copy(update={"edit_b_checksum": "d" * 64}), NS(id="reviewer")
        )
    assets["control"].checksum_sha256 = "a" * 64
    with pytest.raises(ValueError, match="visual_comparison_distinct_control_required"):
        service.record_visual_comparison(
            db, document, request.model_copy(update={"control_checksum": "a" * 64}), NS(id="reviewer")
        )
    assets["control"].checksum_sha256 = "c" * 64
    source_technical = assets["source-1"].object_metadata["editingResource"]["technical"]
    source_technical["durationMicroseconds"] = 1_000_000
    with pytest.raises(ValueError, match="visual_comparison_control_source_interval_invalid"):
        service.record_visual_comparison(db, document, request, NS(id="reviewer"))
    source_technical["durationMicroseconds"] = None
    with pytest.raises(ValueError, match="visual_comparison_source_probe_required"):
        service.record_visual_comparison(db, document, request, NS(id="reviewer"))
    source_technical["durationMicroseconds"] = 10_000_000
    assets["source-1"].checksum_sha256 = "x" * 64
    with pytest.raises(ValueError, match="visual_comparison_control_source_conflict"):
        service.record_visual_comparison(db, document, request, NS(id="reviewer"))
    assets["source-1"].checksum_sha256 = "1" * 64
    assets["control"].object_metadata["editingResource"]["technical"]["probe"]["audioStreams"] = []
    with pytest.raises(ValueError, match="visual_comparison_control_format_required"):
        service.record_visual_comparison(db, document, request, NS(id="reviewer"))
    assets["control"].object_metadata["editingResource"]["technical"]["probe"]["audioStreams"] = [{}]
    states["edit-b"]["sourceChecksums"] = {"source-1": "1" * 64}
    with pytest.raises(ValueError, match="visual_comparison_same_sources_required"):
        service.record_visual_comparison(db, document, request, NS(id="reviewer"))


def test_comparison_projection_invalidates_after_new_render(monkeypatch):
    from datetime import UTC, datetime

    from app.services.studios import visual_quality_program as service

    document = NS(
        id="document",
        workspace_id="workspace",
        revision=2,
        title="Produto",
        canonical_document={
            "brief": {"objective": "Mostrar preparo"},
            "brandMemoryRef": {"id": "brand"},
            "assets": [
                {
                    "mediaType": "video/mp4",
                    "checksum": c * 64,
                    "rightsStatus": "verified",
                    "provenance": {"editingResource": {"motionDescription": "Ação visível"}},
                }
                for c in ("1", "2")
            ]
            + [
                {
                    "mediaType": "image/png",
                    "checksum": "3" * 64,
                    "rightsStatus": "verified",
                    "provenance": {"editingResource": {"assetRole": "product"}},
                }
            ],
        },
        document=None,
    )
    sources = {"source-1": "1" * 64, "source-2": "2" * 64}
    states = [
        {
            "id": run_id,
            "revision": 1,
            "documentId": "document",
            "documentRevision": 2,
            "request": {"qualityPhaseId": "visual-quality-2026-10-01"},
            "sourceChecksums": sources,
            "artifacts": {"video": {"artifact": {"assetId": run_id + "-asset", "checksumSha256": checksum}}},
        }
        for run_id, checksum in (("edit-a", "a" * 64), ("edit-b", "b" * 64))
    ]
    receipt = {
        "expectedDocumentRevision": 2,
        "editARunId": "edit-a",
        "editBRunId": "edit-b",
        "editAChecksum": "a" * 64,
        "editBChecksum": "b" * 64,
        "controlAssetId": "control",
        "controlChecksum": "c" * 64,
        "preferred": "edit_a",
        "status": "passed",
        "sourceChecksums": sources,
    }
    events = [NS(aggregate_id=state["id"], payload=state) for state in states]
    comparisons = [NS(aggregate_id="document", payload=receipt, created_at=datetime.now(UTC))]
    control = NS(id="control", lifecycle_status="active", checksum_sha256="c" * 64)
    source_assets = [NS(id=key, lifecycle_status="active", checksum_sha256=value) for key, value in sources.items()]

    class Rows:
        def __init__(self, values):
            self.values = values

        def all(self):
            return self.values

    class DB:
        def __init__(self):
            self.calls = 0

        def scalars(self, _query):
            values = [[document], events, comparisons, [control, *source_assets], []][self.calls]
            self.calls += 1
            return Rows(values)

    def quality(state, _asset, _document):
        return {
            "runId": state["id"],
            "documentId": "document",
            "qualityPhaseId": "visual-quality-2026-10-01",
            "renderChecksum": state["artifacts"]["video"]["artifact"]["checksumSha256"],
            "visualStatus": "approved",
            "technicalStatus": "passed",
            "blockers": [],
        }

    monkeypatch.setattr(service, "render_quality", quality)
    assert service.project_quality_program(DB(), "workspace")["progress"]["comparisonPassed"] == 1
    states[1]["artifacts"]["video"]["artifact"]["checksumSha256"] = "d" * 64
    assert service.project_quality_program(DB(), "workspace")["progress"]["comparisonPassed"] == 0
