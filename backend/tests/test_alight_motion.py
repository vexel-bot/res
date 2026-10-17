"""Software boundary tests only. Fixtures do not demonstrate Alight rendering."""

# ruff: noqa: F811
import json
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest
from conftest import register
from pydantic import ValidationError
from sqlalchemy import select
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_remotion_native import native_direction, native_document

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.contextual_editing import EditingTechniqueV1, digest
from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.engine_qualification import CreateEngineComparisonV1, EngineComparisonReviewV1
from app.domain.studios.motion_recipes import MotionRecipeV1, TechniqueSourceV1
from app.models import CreativeDocument, LibraryAsset, Membership, StudioGenerationJob
from app.providers.studios.alight_motion import refresh_registration
from app.providers.studios.alight_worker import NAME
from app.services.studios.alight_techniques import alight_technique_cards
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.engine_qualification import create_comparison, review_comparison


def test_empty_new_fields_preserve_legacy_serialization_and_private_execution_fields():
    from app.domain.studios.contracts import VideoRenderRequestV1

    direction = native_direction()
    payload = direction.model_dump(mode="json", by_alias=True)
    assert "renderEngine" not in payload and "engineProfile" not in payload
    assert all("motionRecipes" not in scene for scene in payload["scenes"])
    request = VideoRenderRequestV1(
        workspace_id="w",
        document_id="d",
        document_revision=1,
        document_version=1,
        page_ids=["p"],
        output={"width": 320, "height": 320, "fps": 30},
        correlation_id="test",
        execution_job_id="private",
        execution_plan_snapshot={"id": "private-plan"},
    )
    assert "executionJobId" not in request.model_dump(by_alias=True)
    assert "executionPlanSnapshot" not in request.model_dump(by_alias=True)


def test_recipe_sound_event_must_match_the_executable_audio_attack():
    payload = native_direction().model_dump(mode="json", by_alias=True)
    payload["scenes"][0]["audio"] = [
        {"id": "hit", "role": "effect", "purpose": "Contato visível", "startFrame": 2, "durationFrames": 5}
    ]
    payload["scenes"][0]["motionRecipes"] = [
        {
            **recipe(),
            "soundEvents": [{"audioId": "hit", "targetId": "hero", "frame": 1, "observableEvent": "Contato visível"}],
        }
    ]
    with pytest.raises(ValueError, match="sound_attack_mismatch"):
        native_document(ContextualPlanRequestV2.model_validate(payload))


def test_generic_jobs_cannot_bypass_flag_or_use_unclassified_retries(client, project, monkeypatch):
    from app.domain.studios.contracts import CreateGenerationJobRequest
    from app.models import User
    from app.services.studios.jobs import create_job

    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        owner = db.get(User, record.created_by)
        request = CreateGenerationJobRequest(
            workspace_id=record.workspace_id,
            document_id=record.id,
            job_type="video_render",
            provider=NAME,
            request={"softwareBoundaryFixture": True},
        )
        monkeypatch.setattr(get_settings(), "studio_alight_motion_enabled", False)
        with pytest.raises(ValueError, match="access_denied"):
            create_job(db, request, "alight-disabled", owner)
        monkeypatch.setattr(get_settings(), "studio_alight_motion_enabled", True)
        monkeypatch.setattr("app.providers.studios.alight_motion.refresh_registration", lambda *_: {"available": True})
        job, created = create_job(db, request, "alight-atomic-fixture", owner, commit=False)
        assert created and job.max_attempts == 1 and job.hard_time_limit_seconds == 1890
        identifier = job.id
        db.rollback()
        assert db.get(StudioGenerationJob, identifier) is None


def test_internal_planning_path_keeps_alight_owner_and_flag_gate(client, project, monkeypatch):
    from app.models import User
    from app.services.studios.contextual_editing_v2 import create_plan

    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        owner = db.get(User, record.created_by)
        direction = native_direction()
        direction.render_engine = "alight_motion"
        monkeypatch.setattr(get_settings(), "studio_alight_motion_enabled", False)
        with pytest.raises(ValueError, match="access_denied"):
            create_plan(db, record, direction, owner, "internal-alight-denied")


def recipe():
    return {
        "id": "blur",
        "technique": "velocity_blur",
        "targetIds": ["hero"],
        "startFrame": 0,
        "endFrameExclusive": 15,
        "intent": "Passagem legível",
        "continuityAnchor": "hero",
        "verification": ["Parada nítida"],
    }


def test_documented_techniques_are_knowledge_and_old_cards_remain_readable():
    cards = alight_technique_cards()
    assert len(cards) == 9
    for card in cards:
        assert card.qualification == "knowledge_only"
        assert card.source_evidence[0].kind == "documentation"
        assert not card.source_evidence[0].audio_verified
        assert card.engine_qualifications[0].status != "render_verified"
    old = cards[0].model_dump()
    old.pop("source_evidence")
    old.pop("engine_qualifications")
    assert EditingTechniqueV1.model_validate(old).source_evidence == []


@pytest.mark.parametrize(
    "change",
    [
        {"code": "run()"},
        {"endFrameExclusive": 0},
        {"targetIds": ["hero", "hero"]},
        {"parameters": {"shutterDegrees": float("nan")}},
        {
            "parameters": {
                "tracks": [
                    {
                        "targetId": "hero",
                        "property": "opacity",
                        "keyframes": [{"frame": 0, "value": 0}, {"frame": 30, "value": 1}],
                    }
                ]
            }
        },
    ],
)
def test_recipe_rejects_code_invalid_intervals_and_nonfinite_parameters(change):
    with pytest.raises(ValidationError):
        MotionRecipeV1.model_validate({**recipe(), **change})




def test_tutorial_requires_watched_steps_interval_and_result():
    with pytest.raises(ValidationError):
        TechniqueSourceV1(url="https://example.com/tutorial", kind="watched_tutorial")
    with pytest.raises(ValidationError):
        TechniqueSourceV1(url="https://example.com/docs", audio_verified=True)
    assert (
        TechniqueSourceV1(
            url="https://example.com/tutorial",
            kind="watched_tutorial",
            start_seconds=1,
            end_seconds=5,
            steps=["Observe o pivô"],
            observed_result="Objeto se acomoda",
        ).audio_verified
        is False
    )




def test_disabled_provider_never_registers():
    registry = {NAME: object()}
    result = refresh_registration(NS(studio_alight_motion_enabled=False), registry)
    assert not result["available"] and NAME not in registry


def test_alight_refuses_native_components_without_their_exact_capability(tmp_path):
    from app.domain.studios.contracts import VideoRenderRequestV1
    from app.providers.studios.alight_motion import AlightGraphicsProvider, required_capabilities

    document, _ = native_document(native_direction())
    worker = NS(status=lambda: {"available": True, "capabilities": ["composition.text"], "providerVersion": "fixture"})
    request = VideoRenderRequestV1(
        workspace_id="workspace",
        document_id="native-test",
        document_revision=1,
        document_version=1,
        page_ids=["page"],
        correlation_id="test",
        output={"width": 320, "height": 320, "fps": 30, "audioCodec": "none"},
    )
    assert "native.integrated_typography.v1" in required_capabilities(document)
    with pytest.raises(ValueError, match="capability_missing"):
        AlightGraphicsProvider(worker).render(
            document, request, {}, tmp_path / "out", lambda _: None, lambda: False, automatic_draft=True
        )
    assert not (tmp_path / "out").exists()








@pytest.fixture
def experiment(project, monkeypatch):
    monkeypatch.setattr(get_settings(), "studio_alight_motion_enabled", True)
    monkeypatch.setattr(
        "app.services.studios.engine_qualification.engine_capabilities",
        lambda: {
            "engines": [
                {"provider": NAME, "available": False, "capabilities": [], "blockers": ["physical_device_missing"]}
            ]
        },
    )
    return {
        **project,
        "headers": {"Authorization": "Bearer " + project["token"]},
        "base": "/api/v1/studios/v1/workspaces/" + project["workspace"],
    }


def _campaign(client, experiment):
    response = client.post(experiment["base"] + "/engine-campaigns", headers=experiment["headers"], json={})
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    with SessionLocal() as db:
        revision = db.get(CreativeDocument, experiment["document"]).revision
    response = client.post(
        experiment["base"] + f"/engine-campaigns/{identifier}/cases",
        headers=experiment["headers"],
        json={
            "language": "kinetic_type",
            "documentId": experiment["document"],
            "expectedDocumentRevision": revision,
            "expectedCampaignRevision": 1,
        },
    )
    assert response.status_code == 200, response.text
    return identifier


def test_experiment_flag_owner_permission_and_no_false_success(client, project, monkeypatch):
    base = "/api/v1/studios/v1/workspaces/" + project["workspace"]
    headers = {"Authorization": "Bearer " + project["token"]}
    monkeypatch.setattr(get_settings(), "studio_alight_motion_enabled", False)
    assert client.get(base + "/render-engines", headers=headers).status_code == 404
    monkeypatch.setattr(get_settings(), "studio_alight_motion_enabled", True)
    monkeypatch.setattr(get_settings(), "studio_alight_adb_path", "absent-adb")
    status = client.get(base + "/render-engines", headers=headers)
    assert status.status_code == 200, status.text
    assert not status.json()["engines"][-1]["available"]
    created = client.post(base + "/engine-campaigns", headers=headers, json={})
    state = client.get(base + "/engine-campaigns/" + created.json()["id"], headers=headers).json()
    assert state["promotionStatus"] == "pending"
    assert state["visualStatus"] == "not_assessed" and state["autonomyStatus"] == "pending"
    assert state["trials"]["completedAutomatically"] == 0
    with SessionLocal() as db:
        member = db.scalar(select(Membership).where(Membership.workspace_id == project["workspace"]))
        member.role = "editor"
        db.commit()
    assert client.get(base + "/render-engines", headers=headers).status_code == 403


def test_campaign_scope_case_revision_and_no_shared_case_document(client, experiment):
    campaign = _campaign(client, experiment)
    base = experiment["base"] + "/engine-campaigns/" + campaign
    with SessionLocal() as db:
        revision = db.get(CreativeDocument, experiment["document"]).revision
    body = {
        "language": "action_product",
        "documentId": experiment["document"],
        "expectedDocumentRevision": revision,
        "expectedCampaignRevision": 2,
    }
    assert client.post(base + "/cases", headers=experiment["headers"], json=body).status_code == 409
    body["language"] = "kinetic_type"
    body["expectedDocumentRevision"] = revision + 1
    assert client.post(base + "/cases", headers=experiment["headers"], json=body).status_code == 409
    foreign_token, _ = register(client, "foreign-alight@example.com")
    assert client.get(base, headers={"Authorization": "Bearer " + foreign_token}).status_code == 404
    response = client.post(base + "/promote", headers=experiment["headers"])
    assert response.status_code == 409 and "evidence_pending" in response.text


def _render(db, experiment, provider, *, approved=False):
    original = db.get(CreativeDocument, experiment["document"])
    contract = record_to_contract(original)
    record = CreativeDocument(
        workspace_id=original.workspace_id,
        title="Boundary fixture " + provider,
        document={},
        created_by=original.created_by,
    )
    db.add(record)
    db.flush()
    contract.document_id = record.id
    persist_contract(record, contract)
    snapshot = contract.model_dump(mode="json", by_alias=True)
    checksum = digest(str(uuid4()))
    job = StudioGenerationJob(
        workspace_id=record.workspace_id,
        document_id=record.id,
        job_type="video_render",
        provider=provider,
        idempotency_key=str(uuid4()),
        payload_hash=digest(snapshot),
        correlation_id=str(uuid4()),
        status="succeeded",
        request_payload={"documentSnapshot": snapshot},
        attempts=1,
    )
    db.add(job)
    db.flush()
    asset = LibraryAsset(
        workspace_id=record.workspace_id,
        title="Boundary fixture",
        asset_type="video",
        media_type="video/mp4",
        checksum_sha256=checksum,
        object_metadata={
            "derivation": "video_render",
            "generationJobId": job.id,
            "documentId": record.id,
            "documentRevision": record.revision,
            "documentSnapshotSha256": digest(snapshot),
            "sourceAssetBindings": [{"assetId": a.id, "checksumSha256": a.checksum} for a in contract.assets],
            "qualityEvaluation": {"status": "passed"},
        },
    )
    db.add(asset)
    db.flush()
    job.result_payload = {
        "artifact": {
            "assetId": asset.id,
            "checksumSha256": checksum,
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "durationMs": 15000,
            "audioCodec": "aac",
        }
    }
    if approved:
        asset.object_metadata = {
            **asset.object_metadata,
            "visualHumanReview": {
                "assetId": asset.id,
                "renderChecksum": checksum,
                "expectedDocumentRevision": record.revision,
                "status": "meets_human_criteria",
                "fullVideoInspected": True,
                "mobileInspected": True,
                "clarity": 4,
                "rhythm": 4,
                "continuity": 4,
                "finish": 4,
            },
        }
    db.commit()
    return {"documentId": record.id, "documentRevision": record.revision, "assetId": asset.id, "checksum": checksum}


def test_cross_document_comparison_freezes_refs_and_requires_real_human_review(client, experiment):
    campaign = _campaign(client, experiment)
    with SessionLocal() as db:
        alight = _render(db, experiment, NAME)
        remotion = _render(db, experiment, "remotion.contextual-v2")
        control = _render(db, experiment, "builtin.ffmpeg-contextual-v1")
        owner = NS(id=db.get(CreativeDocument, experiment["document"]).created_by)
        session = create_comparison(
            db,
            experiment["workspace"],
            campaign,
            CreateEngineComparisonV1(
                language="kinetic_type", mode="editorial_result", variants=[alight, remotion, control]
            ),
            owner,
        )
        label = next(item["label"] for item in session["labels"] if item["assetId"] == alight["assetId"])
        review = EngineComparisonReviewV1(
            preferred_label=label,
            full_video_inspected=True,
            mobile_inspected=True,
            blind_review_completed=True,
            unrecorded_manual_corrections=False,
            control_simplicity_confirmed=True,
            notes="Avaliação de fronteira, não evidência visual real",
        )
        result = review_comparison(db, experiment["workspace"], campaign, session["id"], review, owner)
        assert result["status"] == "pending"  # Technical QC cannot fill visual scores.
        asset = db.get(LibraryAsset, alight["assetId"])
        asset.checksum_sha256 = "f" * 64
        db.commit()
        with pytest.raises(ValueError, match="checksum"):
            review_comparison(db, experiment["workspace"], campaign, session["id"], review, owner)


def test_comparison_rejects_different_sources_and_same_engine(client, experiment):
    campaign = _campaign(client, experiment)
    with SessionLocal() as db:
        first = _render(db, experiment, NAME)
        second = _render(db, experiment, NAME)
        owner = NS(id=db.get(CreativeDocument, experiment["document"]).created_by)
        with pytest.raises(ValueError, match="two_engines"):
            create_comparison(
                db,
                experiment["workspace"],
                campaign,
                CreateEngineComparisonV1(language="kinetic_type", mode="technical_fidelity", variants=[first, second]),
                owner,
            )


def test_visual_review_revocation_invalidates_a_previously_passed_comparison(client, experiment):
    from app.services.studios.engine_qualification import comparison_projection

    campaign = _campaign(client, experiment)
    with SessionLocal() as db:
        alight = _render(db, experiment, NAME, approved=True)
        remotion = _render(db, experiment, "remotion.contextual-v2")
        control = _render(db, experiment, "builtin.ffmpeg-contextual-v1")
        owner = NS(id=db.get(CreativeDocument, experiment["document"]).created_by)
        session = create_comparison(
            db,
            experiment["workspace"],
            campaign,
            CreateEngineComparisonV1(
                language="kinetic_type", mode="editorial_result", variants=[alight, remotion, control]
            ),
            owner,
        )
        label = next(item["label"] for item in session["labels"] if item["assetId"] == alight["assetId"])
        request = EngineComparisonReviewV1(
            preferred_label=label,
            full_video_inspected=True,
            mobile_inspected=True,
            blind_review_completed=True,
            unrecorded_manual_corrections=False,
            control_simplicity_confirmed=True,
            notes="Software boundary attestation fixture, never a real human review",
        )
        assert (
            review_comparison(db, experiment["workspace"], campaign, session["id"], request, owner)["status"]
            == "passed"
        )
        asset = db.get(LibraryAsset, alight["assetId"])
        asset.object_metadata = {
            **asset.object_metadata,
            "visualHumanReview": {**asset.object_metadata["visualHumanReview"], "finish": 3},
        }
        db.commit()
        state = comparison_projection(db, experiment["workspace"], campaign, session["id"])
        assert state["status"] == "stale" and "engine_comparison_human_review_changed" in state["blockers"]


def test_trials_are_enrolled_before_execution_and_the_cohort_cannot_hide_failures(client, experiment):
    from app.domain.studios.engine_qualification import RegisterEngineTrialV1
    from app.services.studios.engine_qualification import register_trial, validate_trial_intent

    campaign = _campaign(client, experiment)
    with SessionLocal() as db:
        first = _render(db, experiment, NAME)
        asset = db.get(LibraryAsset, first["assetId"])
        job = db.get(StudioGenerationJob, asset.object_metadata["generationJobId"])
        owner = NS(id=db.get(CreativeDocument, experiment["document"]).created_by)
        request = RegisterEngineTrialV1(language="kinetic_type", job_id=job.id)
        with pytest.raises(ValueError, match="before_execution"):
            register_trial(db, experiment["workspace"], campaign, request, owner)
        job.status, job.attempts = "queued", 0
        db.commit()
        state = register_trial(db, experiment["workspace"], campaign, request, owner)
        assert state["trials"]["registered"] == 1 and state["trials"]["completedAutomatically"] == 0
        assert register_trial(db, experiment["workspace"], campaign, request, owner)["trials"]["registered"] == 1
        for _ in range(9):
            ref = _render(db, experiment, NAME)
            asset = db.get(LibraryAsset, ref["assetId"])
            job = db.get(StudioGenerationJob, asset.object_metadata["generationJobId"])
            job.status, job.attempts = "queued", 0
            db.commit()
            register_trial(
                db,
                experiment["workspace"],
                campaign,
                RegisterEngineTrialV1(language="kinetic_type", job_id=job.id),
                owner,
            )
        with pytest.raises(ValueError, match="trial_limit"):
            validate_trial_intent(
                db, experiment["workspace"], campaign, "kinetic_type", job.request_payload["documentSnapshot"]
            )
        revision = db.get(CreativeDocument, experiment["document"]).revision
    response = client.post(
        experiment["base"] + f"/engine-campaigns/{campaign}/cases",
        headers=experiment["headers"],
        json={
            "language": "kinetic_type",
            "documentId": first["documentId"],
            "expectedDocumentRevision": revision,
            "expectedCampaignRevision": 2,
        },
    )
    assert response.status_code == 409 and "locked_after_trials" in response.text
