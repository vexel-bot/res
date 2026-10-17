from types import SimpleNamespace

import pytest

from app.services.studios.production_repair import (
    apply_measured_text_reflow,
    prepare_provider_recovery,
    prepare_response_correction,
    recover_budget_rejected_correction,
    recover_stored_response,
    synchronize_unsubmitted_budget_jobs,
)


def test_measured_text_reflow_grows_box_before_reducing_readable_type():
    from test_scene_compiler_v2 import direction

    element = direction().scenes[0].elements[0]
    element.height = 60
    element.font_size = 80

    adjustment = apply_measured_text_reflow(
        element,
        {"widthRatio": 1.0, "heightRatio": 2.4, "contentHeight": 140},
        1080,
        1920,
    )

    assert element.height == pytest.approx(151.2)
    assert element.font_size == 80
    assert element.fit_text
    assert adjustment["beforeHeight"] == 60
    assert adjustment["afterHeight"] == pytest.approx(151.2)


def test_measured_text_reflow_never_drops_below_sixteen_px_at_preview_width():
    from test_scene_compiler_v2 import direction

    element = direction().scenes[0].elements[0]
    element.y = 0
    element.height = 30
    element.font_size = 30

    adjustment = apply_measured_text_reflow(
        element,
        {"widthRatio": 4.0, "heightRatio": 20.0, "contentHeight": 1000},
        300,
        300,
    )

    assert element.height == pytest.approx(282)
    assert element.font_size == 16
    assert adjustment["minimumPresentationPx"] == 16


def state():
    return {"stage": "composition", "jobs": {"direction": "first", "composition": "bad"}}


def job(**changes):
    return SimpleNamespace(
        **{
            "id": "bad",
            "status": "failed",
            "error_code": "ValidationError",
            "error_message": "invalid scene field",
            "result_payload": {"responseKey": "response.json"},
            **changes,
        }
    )


def test_budget_migration_updates_only_unsubmitted_queued_jobs():
    queued = SimpleNamespace(
        id="queued",
        workspace_id="workspace",
        document_id="document",
        correlation_id="run",
        status="queued",
        request_payload={"budgetPolicy": "res.motion-pilot.v2"},
        result_payload=None,
    )
    submitted = SimpleNamespace(
        id="submitted",
        workspace_id="workspace",
        document_id="document",
        correlation_id="run",
        status="queued",
        request_payload={"budgetPolicy": "res.motion-pilot.v2"},
        result_payload={"submissionStarted": True},
    )

    class FakeSession:
        def __init__(self):
            self.commits = 0

        def scalars(self, _statement):
            return SimpleNamespace(all=lambda: [queued, submitted])

        def commit(self):
            self.commits += 1

    db = FakeSession()
    run = {
        "id": "run",
        "documentId": "document",
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v3",
            "allocations": {"preRenderLimitUsd": 0.9},
        },
    }

    updated = synchronize_unsubmitted_budget_jobs(db, run, "workspace")

    assert [item["jobId"] for item in updated] == ["queued"]
    assert queued.request_payload["budgetPolicy"] == "res.motion-pilot.v3"
    assert submitted.request_payload["budgetPolicy"] == "res.motion-pilot.v2"
    assert db.commits == 1
    assert run["budgetJobMigrations"][0]["providerSubmission"] is False


def test_current_policy_material_inspection_receives_bounded_floor_before_submission():
    queued = SimpleNamespace(
        id="inspection",
        workspace_id="workspace",
        document_id="document",
        correlation_id="run",
        status="queued",
        request_payload={
            "budgetPolicy": "res.motion-pilot.v4",
            "budgetAllocations": {"preRenderLimitUsd": 1.0},
            "input": {"materialInspection": {"assetId": "asset"}},
            "pricing": {
                "inputUsdPerMillion": 2,
                "outputUsdPerMillion": 8,
                "minimumReservationUsd": 0.10,
            },
        },
        result_payload=None,
    )

    class FakeSession:
        def __init__(self):
            self.commits = 0

        def scalars(self, _statement):
            return SimpleNamespace(all=lambda: [queued])

        def commit(self):
            self.commits += 1

    db = FakeSession()
    run = {
        "id": "run",
        "documentId": "document",
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v4",
            "allocations": {"preRenderLimitUsd": 1.0},
        },
    }

    updated = synchronize_unsubmitted_budget_jobs(db, run, "workspace")

    assert [item["jobId"] for item in updated] == ["inspection"]
    assert queued.request_payload["pricing"]["minimumReservationUsd"] == pytest.approx(0.02)
    assert run["budgetJobMigrations"][0]["minimumReservationUsd"] == pytest.approx(0.02)
    assert db.commits == 1


def test_submitted_material_inspection_pricing_remains_immutable():
    submitted = SimpleNamespace(
        id="submitted-inspection",
        workspace_id="workspace",
        document_id="document",
        correlation_id="run",
        status="queued",
        request_payload={
            "budgetPolicy": "res.motion-pilot.v4",
            "budgetAllocations": {"preRenderLimitUsd": 1.0},
            "input": {"materialInspection": {"assetId": "asset"}},
            "pricing": {"minimumReservationUsd": 0.10},
        },
        result_payload={"submissionStarted": True},
    )

    class FakeSession:
        def scalars(self, _statement):
            return SimpleNamespace(all=lambda: [submitted])

        def commit(self):
            raise AssertionError("submitted job must not be mutated")

    run = {
        "id": "run",
        "documentId": "document",
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v4",
            "allocations": {"preRenderLimitUsd": 1.0},
        },
    }

    assert synchronize_unsubmitted_budget_jobs(FakeSession(), run, "workspace") == []
    assert submitted.request_payload["pricing"]["minimumReservationUsd"] == pytest.approx(0.10)


def test_budget_recovery_never_reactivates_historical_stage_job(monkeypatch):
    active = SimpleNamespace(
        id="active",
        workspace_id="workspace",
        document_id="document",
        correlation_id="run",
        status="retrying",
        request_payload={"input": {"productionStage": "composition"}},
        result_payload=None,
        error_message="production_pre_render_budget_exceeded",
    )
    historical = SimpleNamespace(
        id="historical",
        workspace_id="workspace",
        document_id="document",
        correlation_id="run",
        status="failed",
        request_payload={
            "budgetPolicy": "res.motion-pilot.v3",
            "input": {"productionStage": "composition"},
        },
        result_payload=None,
        error_message="production_pre_render_budget_exceeded",
    )

    class FakeSession:
        def scalars(self, _statement):
            return SimpleNamespace(all=lambda: [historical])

    monkeypatch.setattr(
        "app.services.studios.jobs.retry_job",
        lambda *_args, **_kwargs: pytest.fail("historical job must not be retried"),
    )
    run = {
        "id": "run",
        "documentId": "document",
        "stage": "composition",
        "jobs": {"composition": active.id},
        "budgetEnvelope": {
            "policy": "res.motion-pilot.v4",
            "allocations": {"preRenderLimitUsd": 1.0},
        },
    }

    assert recover_budget_rejected_correction(
        FakeSession(), run, "workspace", "actor"
    ) is None
    assert run["jobs"]["composition"] == "active"


def test_received_invalid_response_gets_at_most_two_corrections():
    run = state()
    for attempt in (1, 2):
        assert prepare_response_correction(run, job())
        assert run["responseCorrections"]["composition"] == attempt
        assert run["jobs"] == {"direction": "first"}
    assert not prepare_response_correction(run, job())
    assert len(run["correctionHistory"]) == 2


def test_editorial_motion_counts_incomplete_route_and_contract_retries_together():
    run = state()
    run["request"] = {"cinematicDirectionPolicy": "editorial_motion_v2"}
    assert prepare_response_correction(run, job())
    route = job(
        error_code="ValueError",
        error_message="editing_component_format_transformation_requires_shared_material",
    )
    assert prepare_response_correction(run, route)
    assert run["automaticCorrectionRounds"] == 2
    assert not prepare_response_correction(run, job())


def test_incompatible_semantic_route_gets_one_separate_correction():
    run = {
        **state(),
        "responseCorrections": {"composition": 2},
    }
    incompatible = job(
        error_code="ValueError",
        error_message="editing_component_format_transformation_requires_shared_material",
    )

    assert prepare_response_correction(run, incompatible)
    assert run["routeCorrections"]["composition"] == 1
    assert run["responseCorrections"]["composition"] == 2
    assert run["correctionHistory"][-1]["category"] == "route_incompatible"
    assert "shared content identity" in run["responseCorrection"]["error"]
    assert not prepare_response_correction(run, incompatible)


def test_received_malformed_json_gets_a_structured_correction():
    run = state()
    malformed = job(
        status="retrying",
        error_code="JSONDecodeError",
        error_message="Expecting property name enclosed in double quotes",
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "accepted",
            "responseKey": "malformed.json",
        },
    )

    assert prepare_response_correction(run, malformed)
    assert run["responseCorrection"]["attempt"] == 1
    assert run["correctionHistory"][-1]["responseKey"] == "malformed.json"


def test_definitive_transient_rejection_allows_one_new_immutable_job():
    run = state()
    rejected = job(
        error_message="gemini_http_503",
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "rejected",
            "providerHttpStatus": 503,
            "model": "gemini-a",
        },
    )
    rejected.provider = "google.gemini-editing"

    assert prepare_provider_recovery(run, rejected)
    assert run["jobs"] == {"direction": "first"}
    assert run["providerRecoveryHistory"][0]["model"] == "gemini-a"
    assert not prepare_provider_recovery(run, rejected)


def test_exhausted_provider_quota_never_creates_a_recovery_job():
    run = state()
    rejected = job(
        error_message="editing_ai_http_429:insufficient_quota",
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "rejected",
            "providerHttpStatus": 429,
            "providerErrorKind": "insufficient_quota",
            "model": "gpt-4.1-mini-2025-04-14",
        },
    )
    rejected.provider = "compatible.editing-planner"

    assert not prepare_provider_recovery(run, rejected)
    assert run == state()


def test_recorded_recovery_releases_the_same_stale_active_job_once():
    run = state()
    rejected = job(
        error_message="editing_ai_http_429",
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "rejected",
            "providerHttpStatus": 429,
            "model": "gpt-4.1",
        },
    )
    rejected.provider = "compatible.editing-planner"
    run["providerRecoveryHistory"] = [
        {
            "key": "composition:compatible.editing-planner:gpt-4.1:429",
            "stage": "composition",
            "jobId": "bad",
        }
    ]

    assert prepare_provider_recovery(run, rejected)
    assert run["jobs"] == {"direction": "first"}
    assert run["status"] == "pending"


def test_exhausted_transient_recovery_can_switch_to_a_configured_model(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "studio_editing_ai_model", "gpt-4.1-mini-2025-04-14")
    run = state()
    rejected = job(
        id="replacement",
        error_message="editing_ai_http_429",
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "rejected",
            "providerHttpStatus": 429,
            "model": "gpt-4.1-2025-04-14",
        },
    )
    rejected.provider = "compatible.editing-planner"
    run["jobs"]["composition"] = "replacement"
    run["providerRecoveryHistory"] = [
        {
            "key": "composition:compatible.editing-planner:gpt-4.1-2025-04-14:429",
            "stage": "composition",
            "jobId": "original",
        }
    ]

    assert prepare_provider_recovery(run, rejected)
    assert run["jobs"] == {"direction": "first"}
    assert run["providerRecoveryHistory"][-1]["targetModel"] == "gpt-4.1-mini-2025-04-14"


def test_uncertain_submission_and_conflicts_never_get_new_requests():
    for failed in [
        job(result_payload={"submissionStarted": True}),
        job(error_message="production_revision_conflict"),
        job(error_code="TimeoutError"),
        job(status="cancelled"),
    ]:
        run = state()
        assert not prepare_response_correction(run, failed)
        assert run == state()


def test_local_oversize_prompt_can_be_compacted_once_without_provider_submission():
    run = state()
    failed = job(
        error_code="ValueError",
        error_message="editing_ai_prompt_too_large",
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "rejected",
            "preflightFailure": "editing_ai_prompt_too_large",
        },
    )
    assert prepare_response_correction(run, failed)
    assert run["jobs"] == {"direction": "first"}
    assert run["correctionHistory"][-1]["providerSubmission"] is False
    assert not prepare_response_correction(run, failed)


def test_stored_incomplete_response_gets_one_concise_followup_without_replay():
    run = state()
    incomplete = job(
        status="retrying",
        error_code="ValueError",
        error_message="editing_ai_incomplete_response",
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "accepted",
            "responseKey": "response.json",
            "measuredCostUsd": 0.072,
        },
    )

    assert prepare_response_correction(run, incomplete)
    assert run["jobs"] == {"direction": "first"}
    assert run["correctionHistory"][-1]["category"] == "incomplete_response"
    assert run["correctionHistory"][-1]["providerSubmission"] is True
    assert "more concisely" in run["responseCorrection"]["error"]
    assert not prepare_response_correction(run, incomplete)


def test_incomplete_retry_does_not_consume_third_creative_correction():
    run = {
        **state(),
        "responseCorrections": {"composition": 2},
        "responseCorrection": {"stage": "composition", "attempt": 2, "error": "old"},
    }
    incomplete = job(
        status="failed",
        error_code="ValueError",
        error_message="editing_ai_incomplete_response",
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "accepted",
            "responseKey": "truncated.json",
            "measuredCostUsd": 0.12,
        },
    )

    assert prepare_response_correction(
        run,
        incomplete,
        additional_diagnostic="production_semantic_repair_requires_alternative",
    )
    assert run["responseCorrections"]["composition"] == 2
    assert run["incompleteResponseRetries"]["composition"] == 1
    assert run["responseCorrection"]["attempt"] == 2
    assert "production_semantic_repair_requires_alternative" in run["responseCorrection"]["error"]
    assert not prepare_response_correction(run, incomplete)


def test_increased_output_capacity_gets_one_operational_recovery(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "studio_editing_ai_max_output_tokens", 16_000)
    run = {
        **state(),
        "responseCorrections": {"composition": 2},
        "incompleteResponseRetries": {"composition": 1},
    }
    capped = job(
        status="retrying",
        error_code="ValueError",
        error_message="editing_ai_incomplete_response",
        request_payload={"maxOutputTokens": 10_000},
        result_payload={
            "submissionStarted": True,
            "submissionOutcome": "accepted",
            "responseKey": "capped.json",
            "usage": {"completion_tokens": 10_000},
        },
    )

    assert prepare_response_correction(run, capped)
    assert run["responseCorrections"]["composition"] == 2
    assert run["incompleteResponseRetries"]["composition"] == 1
    assert run["adapterCapacityRetries"]["composition"] == 1
    assert "capacity is now larger" in run["responseCorrection"]["error"]
    assert not prepare_response_correction(run, capped)


@pytest.mark.parametrize(
    "budget_error",
    ["editing_gemini_test_budget_exceeded", "production_pre_render_budget_exceeded"],
)
def test_budget_blocked_correction_replays_paid_response_without_provider(monkeypatch, budget_error):
    original = job(
        id="original",
        workspace_id="workspace",
        document_id="document",
        error_message="editing_v2_quadratic_requires_three_points",
        result_payload={"responseKey": "response.json"},
    )
    correction = job(
        id="correction",
        workspace_id="workspace",
        document_id="document",
        error_message=budget_error,
        result_payload=None,
    )
    run = {
        **state(),
        "responseCorrection": {"stage": "composition", "attempt": 1},
        "correctionHistory": [
            {
                "stage": "composition",
                "jobId": "original",
                "responseKey": "response.json",
                "category": "invalid_response",
                "error": "editing_v2_quadratic_requires_three_points",
            }
        ],
    }
    calls = []
    monkeypatch.setattr("app.services.studios.jobs.retry_job", lambda db, target, actor: calls.append((target, actor)))

    recovered = recover_stored_response(
        SimpleNamespace(get=lambda model, identity: original if identity == "original" else None),
        run,
        correction,
        "actor",
    )

    assert recovered is original
    assert calls == [(original, "actor")]
    assert run["jobs"]["composition"] == "original"
    assert run["replayHistory"][0]["providerSubmission"] is False
    assert recover_stored_response(
        SimpleNamespace(get=lambda model, identity: original), run, correction, "actor"
    ) is None


def test_current_invalid_stored_response_replays_after_contract_repair(monkeypatch):
    failed = job(
        id="original",
        workspace_id="workspace",
        document_id="document",
        error_message="editing_v2_quadratic_requires_three_points",
    )
    run = state()
    calls = []
    monkeypatch.setattr("app.services.studios.jobs.retry_job", lambda db, target, actor: calls.append((target, actor)))

    recovered = recover_stored_response(SimpleNamespace(), run, failed, "actor")

    assert recovered is failed
    assert calls == [(failed, "actor")]
    assert run["jobs"]["composition"] == "original"
    assert run["replayHistory"][0]["responseKey"] == "response.json"


def test_recovery_tries_an_older_paid_response_when_latest_replay_still_fails(monkeypatch):
    from app.services.studios.editorial_components import REPAIR_VERSION

    latest = job(
        id="latest",
        workspace_id="workspace",
        document_id="document",
        error_message="production_semantic_repair_requires_alternative",
        result_payload={"responseKey": "latest.json"},
    )
    older = job(
        id="older",
        workspace_id="workspace",
        document_id="document",
        error_message="editing_v2_keyword_source_binding_required",
        result_payload={"responseKey": "older.json"},
    )
    run = {
        **state(),
        "correctionHistory": [
            {
                "stage": "composition",
                "jobId": "older",
                "responseKey": "older.json",
                "category": "invalid_response",
                "error": older.error_message,
            },
            {
                "stage": "composition",
                "jobId": "latest",
                "responseKey": "latest.json",
                "category": "invalid_response",
                "error": latest.error_message,
            },
        ],
        "deterministicResponseReplays": [f"latest.json:{REPAIR_VERSION}"],
    }
    records = {"latest": latest, "older": older}
    calls = []
    monkeypatch.setattr("app.services.studios.jobs.retry_job", lambda db, target, actor: calls.append(target.id))

    recovered = recover_stored_response(
        SimpleNamespace(get=lambda model, identity: records.get(identity)), run, latest, "actor"
    )

    assert recovered is older
    assert calls == ["older"]
    assert run["jobs"]["composition"] == "older"
    assert run["replayHistory"][-1]["responseKey"] == "older.json"


def test_exhausted_correction_reuses_older_repairable_response(monkeypatch):
    older = job(
        id="older",
        workspace_id="workspace",
        document_id="document",
        error_message="production_component_only_for_composable_material",
        result_payload={"responseKey": "older.json"},
    )
    malformed_latest = job(
        id="latest",
        workspace_id="workspace",
        document_id="document",
        error_message="dictionary update sequence element malformed",
        result_payload={"responseKey": "latest.json"},
    )
    run = {
        **state(),
        "responseCorrection": {"stage": "composition", "attempt": 2},
        "correctionHistory": [
            {
                "stage": "composition",
                "jobId": "older",
                "responseKey": "older.json",
                "category": "invalid_response",
                "error": older.error_message,
            }
        ],
    }
    calls = []
    monkeypatch.setattr(
        "app.services.studios.jobs.retry_job",
        lambda db, target, actor: calls.append(target.id),
    )

    recovered = recover_stored_response(
        SimpleNamespace(get=lambda model, identity: older if identity == "older" else None),
        run,
        malformed_latest,
        "actor",
    )

    assert recovered is older
    assert calls == ["older"]
    assert run["replayHistory"][-1]["providerSubmission"] is False


def test_exhausted_correction_replays_current_best_response_after_local_repair(monkeypatch):
    current = job(
        id="current",
        workspace_id="workspace",
        document_id="document",
        error_message="editing_component_viewport_format_binding_invalid",
        result_payload={"responseKey": "current.json"},
    )
    run = {
        **state(),
        "responseCorrection": {"stage": "composition", "attempt": 2},
        "correctionHistory": [],
    }
    calls = []
    monkeypatch.setattr(
        "app.services.studios.jobs.retry_job",
        lambda db, target, actor: calls.append(target.id),
    )

    recovered = recover_stored_response(SimpleNamespace(), run, current, "actor")

    assert recovered is current
    assert calls == ["current"]
    assert run["replayHistory"][-1]["responseKey"] == "current.json"
    assert run["replayHistory"][-1]["providerSubmission"] is False


def test_retrying_paid_response_is_marked_for_local_replay_without_transition(monkeypatch):
    original = job(
        id="original",
        status="retrying",
        workspace_id="workspace",
        document_id="document",
        error_message="production_composition_duration_exceeds_target",
        result_payload={
            "responseKey": "response.json",
            "submissionOutcome": "accepted",
            "submissionStarted": True,
        },
    )
    blocked = job(
        id="blocked",
        workspace_id="workspace",
        document_id="document",
        error_message="production_pre_render_budget_exceeded",
        result_payload=None,
    )
    run = {
        **state(),
        "responseCorrection": {"stage": "composition", "attempt": 2},
        "correctionHistory": [
            {
                "stage": "composition",
                "jobId": "original",
                "responseKey": "response.json",
                "category": "invalid_response",
                "error": original.error_message,
            }
        ],
    }
    db = SimpleNamespace(
        get=lambda model, identity: original if identity == "original" else None,
        commit=lambda: None,
        refresh=lambda target: None,
    )
    monkeypatch.setattr(
        "app.services.studios.jobs.retry_job",
        lambda *args: pytest.fail("retrying stored response must not transition to queued"),
    )

    recovered = recover_stored_response(db, run, blocked, "actor")

    assert recovered is original
    assert original.result_payload["localReplayPending"] is True
