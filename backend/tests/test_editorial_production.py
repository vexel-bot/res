# ruff: noqa: F811
import json

import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_editing_resources import enable

from app.domain.studios.editorial_production import EditorialDirectionV1, ProductionRequestV1, validate_direction
from app.services.studios.editorial_production import (
    migrate_motion_budget_envelope,
    motion_only_allocations,
    provider_recovery_sequence,
)


def test_provider_recovery_sequence_counts_only_definitive_transient_rejections():
    state = {
        "providerRecoveryHistory": [
            {"stage": "composition", "submissionOutcome": "rejected", "httpStatus": 429},
            {"stage": "composition", "submissionOutcome": "unknown", "httpStatus": 503},
            {"stage": "direction", "submissionOutcome": "rejected", "httpStatus": 429},
            {"stage": "composition", "submissionOutcome": "rejected", "httpStatus": 400},
        ]
    }

    assert provider_recovery_sequence(state, "composition") == 1


def brief():
    return {
        "direction": {
            "expectedDocumentRevision": 1,
            "intent": {
                "objective": "Explicar distribuição",
                "script": "Distribuir não garante atenção.",
                "lockedFacts": ["Distribuir não garante atenção."],
            },
        }
    }


def storyboard():
    concept = dict(
        premise="A ideia busca pessoas",
        visualMechanism="Uma rota conecta lugares",
        clarity="Mostrar a conexão",
        specificity="Destinos concretos",
        continuity="Objeto persiste",
        identityFit="Cores da marca",
        feasibility="Caminhos e imagens disponíveis",
    )
    return {
        "concepts": [
            {"id": "route", **concept},
            {"id": "contrast", **concept, "visualMechanism": "Contraste entre sala vazia e pessoas"},
        ],
        "selectedConceptId": "route",
        "selectionReason": "A rota demonstra a relação causal",
        "beats": [
            {
                "id": "idea",
                "sourceExcerpt": "Distribuir não garante atenção.",
                "narration": "Distribuir não garante atenção.",
                "initialState": "Ideia isolada",
                "action": "Traçar caminhos",
                "consequence": "Destino sem atenção",
                "focus": "Ideia",
                "knowledgeGained": "Alcance difere de atenção",
                "transitionReason": "Concluir com a ressalva",
            }
        ],
    }


def endpoint(project):
    return f"/api/v1/studios/v1/documents/{project['document']}/production-runs"


def headers(project, key="production-test-key"):
    return {"Authorization": f"Bearer {project['token']}", "Idempotency-Key": key}


def test_direction_preserves_negation_and_full_script():
    request = ProductionRequestV1.model_validate(brief())
    direction = EditorialDirectionV1.model_validate(storyboard())
    validate_direction(direction, request)
    direction.beats[0].narration = "garante atenção."
    with pytest.raises(ValueError, match="script_coverage"):
        validate_direction(direction, request)


def test_generated_video_policy_is_provider_neutral_and_backward_compatible():
    disabled = ProductionRequestV1.model_validate(brief()).effective_generated_video_policy()
    assert disabled.mode == "disabled"

    legacy = brief()
    legacy["generatedVideoPolicy"] = "single_short_clip"
    legacy_policy = ProductionRequestV1.model_validate(legacy).effective_generated_video_policy()
    assert legacy_policy.allowed_profile_ids == ["sora-2"]
    assert legacy_policy.maximum_generated_seconds == 4

    local = brief()
    local["generatedVideo"] = {
        "mode": "local_experimental",
        "allowedProfileIds": ["animatediff-lightning-sd15-a-v1"],
        "maxCandidates": 1,
        "allowExperimental": True,
        "maximumGeneratedSeconds": 1,
    }
    local_policy = ProductionRequestV1.model_validate(local).effective_generated_video_policy()
    assert local_policy.mode == "local_experimental"
    assert local_policy.allowed_profile_ids == ["animatediff-lightning-sd15-a-v1"]


def test_legacy_motion_budget_migration_preserves_limit_and_records_receipt():
    state = {
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v1",
            "limitUsd": 1.0,
            "allocations": {
                "planning": 0.4,
                "image": 0.2,
                "critique": 0.2,
                "video": 0.0,
                "reserve": 0.2,
                "preRenderLimitUsd": 0.4,
                "allowReserveSpillover": True,
            },
            "generatedVideoPolicy": {"mode": "disabled"},
        }
    }

    assert migrate_motion_budget_envelope(state)
    envelope = state["budgetEnvelope"]
    assert envelope["limitUsd"] == 1.0
    assert envelope["policy"] == "res.motion-pilot.v7"
    assert envelope["allocations"]["preRenderLimitUsd"] == 1.0
    assert state["budgetPolicyMigrations"][0]["preservedCommittedSpend"] is True
    assert not migrate_motion_budget_envelope(state)


def test_v2_motion_budget_migration_opens_inspection_headroom_without_resetting_limit():
    state = {
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v2",
            "limitUsd": 1.0,
            "allocations": {
                "planning": 0.6,
                "image": 0.1,
                "critique": 0.15,
                "video": 0.0,
                "reserve": 0.15,
                "preRenderLimitUsd": 0.75,
                "allowReserveSpillover": True,
            },
            "generatedVideoPolicy": {"mode": "disabled"},
        }
    }

    assert migrate_motion_budget_envelope(state)
    envelope = state["budgetEnvelope"]
    assert envelope["limitUsd"] == 1.0
    assert envelope["policy"] == "res.motion-pilot.v7"
    assert envelope["allocations"]["preRenderLimitUsd"] == 1.0
    assert state["budgetPolicyMigrations"][-1]["from"] == "res.motion-pilot.v2"
    assert state["budgetPolicyMigrations"][-1]["preservedCommittedSpend"] is True


def test_v3_motion_budget_migration_uses_generation_cap_for_mandatory_replan():
    state = {
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v3",
            "limitUsd": 1.0,
            "allocations": {
                "planning": 0.65,
                "image": 0.05,
                "critique": 0.2,
                "video": 0.0,
                "reserve": 0.1,
                "preRenderLimitUsd": 0.9,
                "allowReserveSpillover": True,
            },
            "generatedVideoPolicy": {"mode": "disabled"},
        }
    }

    assert migrate_motion_budget_envelope(state)
    assert state["budgetEnvelope"]["policy"] == "res.motion-pilot.v7"
    assert state["budgetEnvelope"]["limitUsd"] == 1.0
    assert state["budgetEnvelope"]["allocations"]["preRenderLimitUsd"] == 1.0


def test_two_dollar_motion_budget_preserves_inspection_and_final_critique():
    allocations = motion_only_allocations(2)

    assert allocations == {
        "planning": 0.85,
        "image": 0.20,
        "critique": 0.80,
        "video": 0.0,
        "reserve": 0.15,
        "preRenderLimitUsd": 1.35,
        "allowReserveSpillover": True,
        "allocationUnit": "usd",
        "reserveSpilloverCategories": ["planning", "image", "critique"],
        "inspectionWithinCritiqueUsd": 0.40,
        "finalCritiqueWithinCritiqueUsd": 0.40,
    }
    assert sum(allocations[key] for key in ("planning", "image", "critique", "video", "reserve")) == 2


def test_custom_or_paid_video_budget_is_not_migrated():
    custom = {
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v1",
            "limitUsd": 1.0,
            "allocations": {
                "planning": 0.5,
                "image": 0.1,
                "critique": 0.2,
                "video": 0.0,
                "reserve": 0.2,
                "preRenderLimitUsd": 0.5,
            },
            "generatedVideoPolicy": {"mode": "disabled"},
        }
    }
    paid = {
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v1",
            "limitUsd": 1.0,
            "allocations": {
                "planning": 0.4,
                "image": 0.2,
                "critique": 0.2,
                "video": 0.0,
                "reserve": 0.2,
                "preRenderLimitUsd": 0.4,
            },
            "generatedVideoPolicy": {"mode": "auto"},
        }
    }

    assert not migrate_motion_budget_envelope(custom)
    assert not migrate_motion_budget_envelope(paid)


def test_two_concepts_must_be_distinct():
    value = storyboard()
    value["concepts"][1]["visualMechanism"] = value["concepts"][0]["visualMechanism"]
    with pytest.raises(ValueError, match="concepts_must_differ"):
        EditorialDirectionV1.model_validate(value)


def test_disabled_provider_persists_blocker_and_idempotency(client, project, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "studio_gemini_enabled", False)
    first = client.post(endpoint(project), headers=headers(project), json=brief())
    assert first.status_code == 202, first.text
    run = first.json()
    assert run["status"] == "blocked"
    assert not run["autonomousProductionQualified"]
    assert run["humanReview"] == run["audiovisualEvaluation"] == "pending"
    again = client.post(endpoint(project), headers=headers(project), json=brief())
    assert again.json()["id"] == run["id"]
    changed = brief()
    changed["durationSeconds"] = 20
    assert client.post(endpoint(project), headers=headers(project), json=changed).status_code == 409
    cancelled = client.post(endpoint(project) + f"/{run['id']}/cancel", headers=headers(project))
    assert cancelled.json()["status"] == "cancelled"
    assert (
        client.post(endpoint(project) + f"/{run['id']}/resume", headers=headers(project)).json()["status"]
        == "cancelled"
    )


def test_provider_direction_is_persisted_before_voice_gate(client, project, monkeypatch):
    from app.database import SessionLocal
    from app.models import StudioGenerationJob
    from app.providers.studios.gemini_editing import GeminiEditingProvider
    from app.services.studios.jobs import execute_job_once

    enable(monkeypatch)
    contexts = []

    def plan(self, model, context, media):
        contexts.append(context)
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(storyboard())}]}}]}

    monkeypatch.setattr(GeminiEditingProvider, "plan", plan)
    response = client.post(endpoint(project), headers=headers(project), json=brief())
    assert response.status_code == 202, response.text
    run = response.json()
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, run["jobs"]["direction"])
        assert execute_job_once(db, job) == "succeeded", job.error_message
    url = endpoint(project) + f"/{run['id']}/resume"
    advanced = client.post(url, headers=headers(project)).json()
    assert advanced["stage"] == "composition"
    assert advanced["artifacts"]["directionAuthorship"]["jobId"] == job.id
    blocked = client.post(url, headers=headers(project)).json()
    assert blocked["blockers"] == ["production_qualified_narration_required"]
    assert "composition" not in blocked["jobs"]
    assert len(contexts) == 1
    assert contexts[0]["outputSchema"]["properties"]["concepts"]["minItems"] == 2
    assert blocked["technicalEvaluation"] == "pending"


def test_invalid_structured_direction_is_terminal_and_keeps_response(client, project, monkeypatch):
    from app.database import SessionLocal
    from app.models import StudioGenerationJob
    from app.providers.studios.gemini_editing import GeminiEditingProvider
    from app.services.studios.jobs import execute_job_once

    enable(monkeypatch)
    monkeypatch.setattr(
        GeminiEditingProvider,
        "plan",
        lambda *args: {
            "candidates": [{"content": {"parts": [{"text": '{"concepts": [], "beats": []}'}]}}],
            "usageMetadata": {"totalTokenCount": 19},
        },
    )
    response = client.post(endpoint(project), headers=headers(project), json=brief())
    identifier = response.json()["jobs"]["direction"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, identifier)
        assert execute_job_once(db, job) == "failed"
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, identifier)
        assert job.result_payload["responseKey"]
        assert job.result_payload["usage"]["totalTokenCount"] == 19


def test_direction_identifier_repair_is_ascii_and_preserves_selected_concept():
    from app.domain.studios.editorial_production import normalize_direction_identifiers

    payload, repairs = normalize_direction_identifiers(
        {
            "concepts": [{"id": "conexão visual"}, {"id": "rede"}],
            "selectedConceptId": "conexão visual",
            "beats": [{"id": "b4-negação-final"}, {"id": "b4-negação-final"}],
        }
    )
    assert payload["concepts"][0]["id"] == "conexao-visual"
    assert payload["selectedConceptId"] == "conexao-visual"
    assert [beat["id"] for beat in payload["beats"]] == ["b4-negacao-final", "b4-negacao-final-2"]
    assert len(repairs) == 3


def test_planning_keeps_relevant_technique_requiring_missing_material():
    from app.services.studios.editing_repertoire import rank_repertoire, seed_techniques

    technique = seed_techniques()[0].model_copy(
        update={"id": "requires-footage", "required_material_kinds": ["video"], "required_capabilities": []}
    )
    assert rank_repertoire([technique], technique.title, [], material_kinds=[]) == []
    assert rank_repertoire([technique], technique.title, [], material_kinds=[], allow_missing_materials=True) == [
        technique
    ]


def test_external_motion_workflow_is_knowledge_not_an_unearned_capability():
    from app.services.studios.editing_repertoire import seed_techniques

    indexed = {technique.id: technique for technique in seed_techniques()}

    for technique_id in ("reference-role-lock-v1", "localized-visual-repair-v1"):
        technique = indexed[technique_id]
        assert technique.qualification == "knowledge_only"
        assert technique.sources
        assert technique.required_capabilities == []


def test_uncertain_submission_is_not_replaced(client, project, monkeypatch):
    from sqlalchemy import func, select

    from app.database import SessionLocal
    from app.models import StudioGenerationJob

    enable(monkeypatch)
    run = client.post(endpoint(project), headers=headers(project), json=brief()).json()
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, run["jobs"]["direction"])
        job.status = "failed"
        job.result_payload = {"submissionStarted": True}
        db.commit()
    for _ in range(2):
        result = client.post(endpoint(project) + f"/{run['id']}/resume", headers=headers(project)).json()
        assert result["blockers"] == ["production_submission_requires_reconciliation"]
        assert result["jobs"] == run["jobs"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 1


def test_failed_critique_preserves_render_for_human_review(client, project, monkeypatch):
    from app.config import get_settings
    from app.database import SessionLocal
    from app.models import CreativeDocument, StudioGenerationJob, User
    from app.services.studios.editorial_production import get_run, save

    monkeypatch.setattr(get_settings(), "studio_gemini_enabled", False)
    created = client.post(endpoint(project), headers=headers(project), json=brief()).json()
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        user = db.get(User, record.created_by)
        state = get_run(db, record, created["id"])
        job = StudioGenerationJob(
            workspace_id=record.workspace_id,
            requested_by=user.id,
            document_id=record.id,
            job_type="editing_ai",
            provider="compatible.editing-planner",
            idempotency_key="critique-budget-test",
            payload_hash="0" * 64,
            correlation_id=created["id"],
            status="failed",
            request_payload={},
            error_code="ValueError",
            error_message="editing_gemini_test_budget_exceeded",
        )
        db.add(job)
        db.flush()
        state.update(
            stage="critique",
            status="running",
            jobs={**state["jobs"], "critique": job.id},
        )
        save(db, record, user, state)

    result = client.post(
        endpoint(project) + f"/{created['id']}/resume",
        headers=headers(project),
    ).json()
    assert result["status"] == "awaiting_review"
    assert result["humanReview"] == "pending"
    assert result["blockers"] == ["production_critique_unavailable"]


def test_uncertain_critique_preserves_render_without_resubmission(client, project, monkeypatch):
    from sqlalchemy import func, select

    from app.config import get_settings
    from app.database import SessionLocal
    from app.models import CreativeDocument, StudioGenerationJob, User
    from app.services.studios.editorial_production import get_run, save

    monkeypatch.setattr(get_settings(), "studio_gemini_enabled", False)
    created = client.post(endpoint(project), headers=headers(project), json=brief()).json()
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        user = db.get(User, record.created_by)
        state = get_run(db, record, created["id"])
        job = StudioGenerationJob(
            workspace_id=record.workspace_id,
            requested_by=user.id,
            document_id=record.id,
            job_type="editing_ai",
            provider="compatible.editing-planner",
            idempotency_key="critique-uncertain-test",
            payload_hash="1" * 64,
            correlation_id=created["id"],
            status="failed",
            request_payload={},
            result_payload={"submissionStarted": True},
            error_code="RuntimeError",
            error_message="editing_submission_outcome_unknown_manual_reconciliation_required",
        )
        db.add(job)
        db.flush()
        state.update(
            stage="critique",
            status="running",
            jobs={**state["jobs"], "critique": job.id},
        )
        save(db, record, user, state)
        jobs_before = db.scalar(select(func.count()).select_from(StudioGenerationJob))

    result = client.post(
        endpoint(project) + f"/{created['id']}/resume",
        headers=headers(project),
    ).json()
    assert result["status"] == "awaiting_review"
    assert result["humanReview"] == "pending"
    assert result["blockers"] == ["production_critique_submission_requires_reconciliation"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == jobs_before


def test_changed_document_blocks_run(client, project, monkeypatch):
    from app.database import SessionLocal
    from app.models import CreativeDocument

    enable(monkeypatch)
    run = client.post(endpoint(project), headers=headers(project), json=brief()).json()
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        record.revision += 1
        db.commit()
    result = client.post(endpoint(project) + f"/{run['id']}/resume", headers=headers(project)).json()
    assert result["status"] == "blocked"
    assert result["blockers"] == ["studio_document_conflict"]
