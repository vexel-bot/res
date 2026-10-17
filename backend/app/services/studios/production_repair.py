"""Bounded corrections for received invalid responses; never replay uncertain submissions."""

import json
import re

from ...config import get_settings

DETERMINISTIC_CONTRACT_ERRORS = (
    "editing_ai_incomplete_response",
    "editing_v2_quadratic_requires_three_points",
    "editing_v2_camera_target_role_invalid",
    "editing_v2_composition_target_conflict",
    "production_blueprint_media_missing",
    "production_mixed_montage_media_missing",
    "editing_component_evidence_requires_media_and_annotation",
    "editing_v2_motion_cue_property_conflict",
    "editing_v2_child_out_of_parent_interval",
    "editing_v2_deliberate_hold_profile_required",
    "production_semantic_repair_requires_alternative",
    "editing_v2_keyword_source_binding_required",
    "editing_v2_keyword_source_binding_invalid",
    "editing_v2_keyword_out_of_range",
    "production_visual_preflight_failed",
    "production_revision_changed_unselected_scene",
    "production_component_only_for_composable_material",
    "editing_v2_shot_component_missing",
    "editing_v2_effect_stack_conflicts_legacy_filters",
    "repeatCount",
    "motionCues.0.intensity",
    "production_composition_duration_exceeds_target",
    "rejectedstylemoves",
    "production_cinematic_shot_sequence_required",
    "production_direction_beat_object_required",
    "editing_component_viewport_format_binding_invalid",
    "editing_component_interface_event_binding_invalid",
    "editing_v2_alignment_cycle",
    "editing_v2_text_span_timing_out_of_range",
    "editing_v2_text_source_required",
    "editing_v2_content_part_source_required",
    "editing_v2_content_binding_requires_part_or_group",
    "editing_v2_motion_cue_out_of_range",
    "editing_v2_path_reveal_requires_path",
    "Bezier controls are only valid for cubic-bezier easing",
    "editing_v2_animation_out_of_range",
    "editing_v2_alignment_requires_sibling",
    "editing_v2_connector_requires_path_and_two_targets",
    "editing_v2_shot_intervals_must_be_contiguous",
    "production_compiled_shot_target_missing",
    "production_compiled_shot_target_not_visible",
    "production_compiled_art_direction_changed",
    "production_storyboard_scene_binding_conflict",
    "production_indispensable_material_target_missing",
    "production_blueprint_material_request_missing",
    "production_compiled_shot_material_unbound",
    "editing_component_requires_two_targets",
    "production_semantic_repair_requires_alternative",
    # The provider response is already stored. A corrected local binding may
    # safely replay parsing/compilation without another network submission;
    # execute_job_once still verifies the persisted endpoint fingerprint and
    # exact model before reading the response.
    "editing_ai_provider_binding_conflict",
    "editing_ai_local_postprocessing_interrupted",
)


def _repairable_contract_error(message):
    return any(token in (message or "") for token in DETERMINISTIC_CONTRACT_ERRORS)


def recover_stored_response(db, state, failed_correction, actor_id):
    """Retry a paid response locally after deterministic contract repairs change.

    This path is deliberately limited to a correction that never reached a
    provider because its stage budget was exhausted. It reuses the immutable
    stored response and never submits another billable request.
    """
    from ...models import CreativeDocument, StudioGenerationJob
    from .editorial_components import REPAIR_VERSION
    from .jobs import retry_job

    stage = state.get("stage")
    correction = state.get("responseCorrection", {})
    if stage not in {"direction", "composition"} or failed_correction.status not in {
        "failed",
        "retrying",
    }:
        return None
    history = None
    original = failed_correction
    payload = original.result_payload or {}
    replays = list(state.get("deterministicResponseReplays", []))

    def replay_available(candidate, candidate_payload):
        candidate_key = f"{candidate_payload['responseKey']}:{REPAIR_VERSION}"
        # A binding conflict occurs before the immutable response is read. It
        # must not consume the local replay once the process is restored to
        # the provider/model fingerprint stored with that response.
        return (
            candidate_key not in replays
            or candidate.error_message == "editing_ai_provider_binding_conflict"
        )

    def response_likely_complete(candidate, candidate_payload):
        usage = candidate_payload.get("usage") or {}
        completion_tokens = usage.get("completion_tokens")
        output_limit = (getattr(candidate, "request_payload", None) or {}).get(
            "maxOutputTokens"
        )
        return not (
            isinstance(completion_tokens, int)
            and isinstance(output_limit, int)
            and completion_tokens >= output_limit
        )

    if failed_correction.error_message in {
        "editing_gemini_test_budget_exceeded",
        "production_pre_render_budget_exceeded",
    }:
        if correction.get("stage") != stage:
            return None
        candidates = []
        for item in reversed(state.get("correctionHistory", [])):
            if (
                item.get("stage") != stage
                or item.get("category") != "invalid_response"
                or not _repairable_contract_error(item.get("error"))
            ):
                continue
            candidate = db.get(StudioGenerationJob, item.get("jobId"))
            candidate_payload = candidate.result_payload if candidate else None
            if not candidate_payload or not candidate_payload.get("responseKey"):
                continue
            replay_key = f"{candidate_payload['responseKey']}:{REPAIR_VERSION}"
            if replay_available(candidate, candidate_payload):
                candidates.append((item, candidate, candidate_payload, replay_key))
        if not candidates:
            return None
        candidates.sort(
            key=lambda item: not response_likely_complete(item[1], item[2])
        )
        history, original, payload, replay_key = candidates[0]
    elif correction.get("stage") == stage and correction.get("attempt", 0) >= 2:
        candidates = []
        candidate_keys = set()
        if (
            payload.get("responseKey")
            and not payload.get("providerOperationId")
            and _repairable_contract_error(failed_correction.error_message)
        ):
            current_key = f"{payload['responseKey']}:{REPAIR_VERSION}"
            if replay_available(failed_correction, payload):
                candidates.append((None, failed_correction, payload, current_key))
                candidate_keys.add(current_key)
        for item in reversed(state.get("correctionHistory", [])):
            if (
                item.get("stage") != stage
                or item.get("category") != "invalid_response"
                or not _repairable_contract_error(item.get("error"))
            ):
                continue
            candidate = db.get(StudioGenerationJob, item.get("jobId"))
            candidate_payload = candidate.result_payload if candidate else None
            if not candidate_payload or not candidate_payload.get("responseKey"):
                continue
            candidate_key = f"{candidate_payload['responseKey']}:{REPAIR_VERSION}"
            if replay_available(candidate, candidate_payload) and candidate_key not in candidate_keys:
                candidates.append((item, candidate, candidate_payload, candidate_key))
                candidate_keys.add(candidate_key)
        # The response that exhausted the correction allowance is not itself in
        # correctionHistory. Recover it (or another later persisted candidate)
        # from the immutable job ledger before falling back to older responses.
        if hasattr(db, "scalars"):
            from sqlalchemy import select

            from ...models import StudioGenerationJob

            ledger = db.scalars(
                select(StudioGenerationJob)
                .where(
                    StudioGenerationJob.workspace_id == failed_correction.workspace_id,
                    StudioGenerationJob.document_id == failed_correction.document_id,
                    StudioGenerationJob.correlation_id == failed_correction.correlation_id,
                )
                .order_by(StudioGenerationJob.created_at.desc())
            ).all()
            ledger_candidates = []
            for candidate in ledger:
                candidate_payload = candidate.result_payload or {}
                candidate_stage = (candidate.request_payload or {}).get("input", {}).get(
                    "productionStage"
                )
                if (
                    candidate_stage != stage
                    or candidate.status not in {"failed", "retrying"}
                    or not candidate_payload.get("responseKey")
                    or candidate_payload.get("providerOperationId")
                    or not _repairable_contract_error(candidate.error_message)
                ):
                    continue
                candidate_key = f"{candidate_payload['responseKey']}:{REPAIR_VERSION}"
                if not replay_available(candidate, candidate_payload) or candidate_key in candidate_keys:
                    continue
                ledger_candidates.append((None, candidate, candidate_payload, candidate_key))
                candidate_keys.add(candidate_key)
            candidates = ledger_candidates + candidates
        if not candidates:
            return None
        candidates.sort(
            key=lambda item: not response_likely_complete(item[1], item[2])
        )
        history, original, payload, replay_key = candidates[0]
    elif not (
        payload.get("responseKey")
        and not payload.get("providerOperationId")
        and _repairable_contract_error(failed_correction.error_message)
    ):
        return None
    record = db.get(CreativeDocument, failed_correction.document_id) if hasattr(db, "get") else None
    original_request = getattr(original, "request_payload", {}) or {}
    expected_revision = original_request.get("documentRevision")
    if (
        not original
        or original.workspace_id != failed_correction.workspace_id
        or original.document_id != failed_correction.document_id
        or (
            expected_revision is not None
            and (record is None or getattr(record, "revision", None) != expected_revision)
        )
        or original.status not in {"failed", "retrying"}
        or not payload
        or (history and payload.get("responseKey") != history.get("responseKey"))
        or payload.get("providerOperationId")
    ):
        return None
    replay_key = f"{payload['responseKey']}:{REPAIR_VERSION}"
    if not replay_available(original, payload):
        fallback = None
        for item in reversed(state.get("correctionHistory", [])):
            if (
                item.get("stage") != stage
                or item.get("category") != "invalid_response"
                or not _repairable_contract_error(item.get("error"))
            ):
                continue
            candidate = db.get(StudioGenerationJob, item.get("jobId"))
            candidate_payload = candidate.result_payload if candidate else None
            if (
                not candidate_payload
                or candidate.status not in {"failed", "retrying"}
                or not candidate_payload.get("responseKey")
                or candidate_payload.get("providerOperationId")
                or (
                    (getattr(candidate, "request_payload", {}) or {}).get("documentRevision") is not None
                    and (
                        record is None
                        or getattr(record, "revision", None)
                        != (getattr(candidate, "request_payload", {}) or {}).get("documentRevision")
                    )
                )
            ):
                continue
            candidate_key = f"{candidate_payload['responseKey']}:{REPAIR_VERSION}"
            if replay_available(candidate, candidate_payload):
                fallback = (item, candidate, candidate_payload, candidate_key)
                break
        if fallback is None:
            return None
        history, original, payload, replay_key = fallback
    if original.status == "retrying":
        payload = {**payload, "localReplayPending": True}
        original.result_payload = payload
        db.commit()
        db.refresh(original)
    else:
        retry_job(db, original, actor_id)
    state["deterministicResponseReplays"] = [*replays, replay_key]
    state["jobs"] = {**state.get("jobs", {}), stage: original.id}
    state["replayHistory"] = [
        *state.get("replayHistory", []),
        {
            "stage": stage,
            "jobId": original.id,
            "responseKey": payload["responseKey"],
            "repairVersion": REPAIR_VERSION,
            "providerSubmission": False,
        },
    ]
    state.update(status="pending", blockers=[])
    return original


def recover_budget_rejected_correction(db, state, workspace_id, actor_id):
    """Requeue the latest correction rejected before provider submission.

    A budget-policy migration may make a previously rejected correction
    admissible.  Reuse its persisted job identity and prompt, update only the
    local budget envelope, and never touch a request that reached a provider.
    """

    from sqlalchemy import select

    from ...models import StudioGenerationJob
    from .jobs import retry_job

    stage = state.get("stage")
    envelope = state.get("budgetEnvelope") or {}
    if stage not in {"direction", "composition"} or not envelope.get("allocations"):
        return None
    active_job_id = (state.get("jobs") or {}).get(stage)
    if not active_job_id:
        return None
    candidates = db.scalars(
        select(StudioGenerationJob)
        .where(
            StudioGenerationJob.workspace_id == workspace_id,
            StudioGenerationJob.document_id == state.get("documentId"),
            StudioGenerationJob.correlation_id == state.get("id"),
            StudioGenerationJob.status == "failed",
        )
        .order_by(StudioGenerationJob.created_at.desc())
    ).all()
    for candidate in candidates:
        request = candidate.request_payload or {}
        payload = candidate.result_payload or {}
        input_payload = request.get("input") or {}
        candidate_stage = input_payload.get("productionStage") or input_payload.get(
            "production_stage"
        )
        if (
            candidate.id != active_job_id
            or
            candidate_stage != stage
            or candidate.error_message != "production_pre_render_budget_exceeded"
            or payload.get("submissionStarted")
            or payload.get("responseKey")
            or payload.get("providerOperationId")
        ):
            continue
        previous_policy = request.get("budgetPolicy") or "res.motion-pilot.v1"
        candidate.request_payload = {
            **request,
            "budgetAllocations": envelope["allocations"],
            "budgetPolicy": envelope.get("policy"),
        }
        candidate.result_payload = None
        db.commit()
        retry_job(db, candidate, actor_id)
        state["jobs"] = {**state.get("jobs", {}), stage: candidate.id}
        state["budgetRecoveryHistory"] = [
            *state.get("budgetRecoveryHistory", []),
            {
                "stage": stage,
                "jobId": candidate.id,
                "reason": "pre_render_rejected_before_submission",
                "fromPolicy": previous_policy,
                "toPolicy": envelope.get("policy"),
                "providerSubmission": False,
            },
        ]
        state.update(status="running", blockers=[])
        return candidate
    return None


def synchronize_unsubmitted_budget_jobs(db, state, workspace_id):
    """Move queued local requests to the run's current budget partition.

    A policy migration may be committed after a material-inspection job was
    created but before a worker reserved or submitted it.  Updating that
    persisted envelope is safe only while there is no submission, response or
    provider operation.  Provider-bound requests remain immutable.
    """

    from sqlalchemy import select

    from ...models import StudioGenerationJob

    envelope = state.get("budgetEnvelope") or {}
    allocations = envelope.get("allocations")
    policy = envelope.get("policy")
    if not allocations or not policy:
        return []
    candidates = db.scalars(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == workspace_id,
            StudioGenerationJob.document_id == state.get("documentId"),
            StudioGenerationJob.correlation_id == state.get("id"),
            StudioGenerationJob.status == "queued",
        )
    ).all()
    updated = []
    for candidate in candidates:
        request = candidate.request_payload or {}
        result = candidate.result_payload or {}
        if (
            result.get("submissionStarted")
            or result.get("responseKey")
            or result.get("providerOperationId")
        ):
            continue
        previous_policy = request.get("budgetPolicy")
        next_request = {
            **request,
            "budgetAllocations": allocations,
            "budgetPolicy": policy,
        }
        pricing = dict(next_request.get("pricing") or {})
        input_payload = next_request.get("input") or {}
        is_material_inspection = bool(
            input_payload.get("materialInspection") or input_payload.get("material_inspection")
        )
        previous_minimum = pricing.get("minimumReservationUsd")
        if is_material_inspection and (
            previous_minimum is None or float(previous_minimum) > 0.02
        ):
            pricing["minimumReservationUsd"] = 0.02
            next_request["pricing"] = pricing
        policy_changed = previous_policy != policy
        pricing_changed = pricing != (request.get("pricing") or {})
        allocations_changed = request.get("budgetAllocations") != allocations
        if not (policy_changed or pricing_changed or allocations_changed):
            continue
        candidate.request_payload = next_request
        updated.append(
            {
                "jobId": candidate.id,
                "fromPolicy": previous_policy,
                "toPolicy": policy,
                "minimumReservationUsd": pricing.get("minimumReservationUsd"),
                "providerSubmission": False,
            }
        )
    if updated:
        db.commit()
        state["budgetJobMigrations"] = [
            *state.get("budgetJobMigrations", []),
            *updated,
        ]
    return updated


def apply_measured_text_reflow(element, measurement, canvas_width, canvas_height):
    """Grow a text box before shrinking type and return an auditable adjustment."""
    if element.kind not in {"text", "card"}:
        return None
    before_size = element.font_size
    before_height = element.height
    maximum_height = max(element.height, canvas_height - element.y - canvas_height * 0.06)
    requested_height = max(element.height, measurement["contentHeight"] * 1.08)
    element.height = min(maximum_height, requested_height)
    residual_height_ratio = max(
        1.0,
        measurement["contentHeight"] / max(1.0, element.height),
    )
    ratio = max(measurement["widthRatio"], residual_height_ratio)
    minimum_size = canvas_width * 16 / 300
    if ratio > 1.001:
        factor = min(0.98, 1 / (ratio * 1.03))
        element.font_size = max(minimum_size, round(element.font_size * factor, 3))
    for span in element.text_spans:
        span.scale = min(span.scale, 1.0)
    element.fit_text = True
    return {
        "elementId": element.id,
        "measuredWidthRatio": measurement["widthRatio"],
        "measuredHeightRatio": measurement["heightRatio"],
        "beforeFontSize": before_size,
        "afterFontSize": element.font_size,
        "beforeHeight": before_height,
        "afterHeight": element.height,
        "minimumPresentationPx": 16,
        "keywordScaleCap": 1.0,
    }


def recover_text_layout_render(db, record, state, failed_render, user):
    """Recompile an applied V2 plan after measured text overflow."""
    from ...domain.studios.contextual_editing_v2 import ContextualEditPlanV2
    from .contextual_editing import get_plan
    from .contextual_editing_v2 import create_plan

    error = failed_render.error_message or ""
    stage = state.get("stage")
    repair_version = "res.measured-text-layout.v5-word-safe-reflow"
    repair_key = f"{failed_render.id}:{repair_version}"
    if (
        stage not in {"animatic", "render"}
        or failed_render.status != "failed"
        or "hyperframes_command_failed" not in error
        or '"textOverflow":[' not in error
        or '"textOverflow":[]' in error
        or repair_key in state.get("deterministicRenderRepairs", [])
        or sum(
            item.get("stage") == stage
            and item.get("reason") == "measured_text_overflow"
            and item.get("repairVersion") == repair_version
            for item in state.get("renderRepairHistory", [])
        )
        >= 2
    ):
        return None
    previous = get_plan(db, record.workspace_id, state["artifacts"]["plan"]["id"])
    if not isinstance(previous, ContextualEditPlanV2) or previous.status != "applied":
        return None
    direction = previous.direction.model_copy(deep=True)
    direction.expected_document_revision = record.revision
    match = re.search(
        r'"textOverflowMeasurements":(\[.*?\]),"sampledFrames"',
        error,
    )
    measurements = json.loads(match.group(1)) if match else []
    snapshot = (failed_render.request_payload or {}).get("documentSnapshot", {})
    layer_names = {
        layer.get("id"): layer.get("name")
        for page in snapshot.get("composition", {}).get("pages", [])
        for layer in page.get("layers", [])
    }
    by_element = {}
    for measurement in measurements:
        element_id = layer_names.get(measurement.get("layerId"))
        box_width = float(measurement.get("boxWidth") or 0)
        content_width = float(measurement.get("contentWidth") or 0)
        box_height = float(measurement.get("boxHeight") or 0)
        content_height = float(measurement.get("contentHeight") or 0)
        if not element_id or box_width <= 0 or box_height <= 0:
            continue
        current = by_element.setdefault(
            element_id,
            {"widthRatio": 1.0, "heightRatio": 1.0, "contentHeight": 0.0},
        )
        current["widthRatio"] = max(current["widthRatio"], content_width / box_width)
        current["heightRatio"] = max(current["heightRatio"], content_height / box_height)
        current["contentHeight"] = max(current["contentHeight"], content_height)
    applied = []
    for scene in direction.scenes:
        for element in scene.elements:
            measurement = by_element.get(element.id)
            if measurement is None or element.kind not in {"text", "card"}:
                continue
            canvas_height = max(
                (item.height for item in scene.elements if item.visual_role == "background"),
                default=max(item.y + item.height for item in scene.elements),
            )
            canvas_width = max(
                (item.width for item in scene.elements if item.visual_role == "background"),
                default=max(item.x + item.width for item in scene.elements),
            )
            adjustment = apply_measured_text_reflow(
                element,
                measurement,
                canvas_width,
                canvas_height,
            )
            if adjustment:
                applied.append(adjustment)
    if not applied:
        return None
    revised = create_plan(
        db,
        record,
        direction,
        user,
        f"production:{state['id']}:{stage}:{repair_version}:{previous.id}",
    )
    if revised.status != "ready":
        return None
    state["artifacts"] = {**state.get("artifacts", {}), "plan": revised.model_dump(mode="json", by_alias=True)}
    state["jobs"] = {
        key: value for key, value in state.get("jobs", {}).items() if key not in {"animatic", "render", "critique"}
    }
    state["deterministicRenderRepairs"] = [*state.get("deterministicRenderRepairs", []), repair_key]
    state["renderRepairHistory"] = [
        *state.get("renderRepairHistory", []),
        {
            "stage": stage,
            "failedJobId": failed_render.id,
            "sourcePlanId": previous.id,
            "revisedPlanId": revised.id,
            "repairVersion": repair_version,
            "providerSubmission": False,
            "reason": "measured_text_overflow",
            "measuredAdjustments": applied,
        },
    ]
    state.update(status="pending", blockers=[])
    return revised


def recover_stale_component_review(db, record, state, user):
    """Recompile a bounded visual failure after the component runtime changed.

    This is a compiler refresh, not another creative correction: the authored
    direction and resolved assets remain untouched.  It is intentionally
    limited to a correction-limit review whose stored executable plan was
    produced by an older registered component library.
    """
    if (
        state.get("status") != "awaiting_review"
        or state.get("stage") not in {"animatic", "render"}
        or state.get("blockers") != ["production_visual_correction_limit_reached"]
        or not state.get("artifacts", {}).get("plan", {}).get("id")
    ):
        return None

    from .contextual_editing import get_plan
    from .contextual_editing_v2 import create_plan
    from .editorial_components import VERSION as CURRENT_COMPONENT_VERSION
    from .scene_compiler import current_execution_versions

    previous = get_plan(db, record.workspace_id, state["artifacts"]["plan"]["id"])
    previous_version = (previous.manifest or {}).get("componentLibraryVersion") or (
        previous.manifest or {}
    ).get("componentVersion")
    if previous_version == CURRENT_COMPONENT_VERSION:
        return None

    direction = previous.direction.model_copy(deep=True)
    direction.expected_document_revision = record.revision
    direction.execution_versions = current_execution_versions()
    revised = create_plan(
        db,
        record,
        direction,
        user,
        (
            f"production:{state['id']}:{state['stage']}:component-refresh:"
            f"{CURRENT_COMPONENT_VERSION}:{previous.id}"
        ),
    )
    if revised.status != "ready":
        return None

    state["artifacts"] = {
        **state.get("artifacts", {}),
        "plan": revised.model_dump(mode="json", by_alias=True),
    }
    state["jobs"] = {
        key: value
        for key, value in state.get("jobs", {}).items()
        if key not in {"composition", "animatic", "render", "critique"}
    }
    state["compilerRefreshHistory"] = [
        *state.get("compilerRefreshHistory", []),
        {
            "stage": state["stage"],
            "sourcePlanId": previous.id,
            "revisedPlanId": revised.id,
            "fromComponentVersion": previous_version,
            "toComponentVersion": CURRENT_COMPONENT_VERSION,
            "reason": "registered_component_runtime_updated_after_bounded_visual_failure",
            "providerSubmission": False,
            "authoredDirectionPreserved": True,
            "resolvedAssetsPreserved": True,
        },
    ]
    state.update(status="pending", blockers=[])
    return revised


def recover_short_visual_render(db, record, state, completed_render, user):
    """Recompile a too-short visual pilot to its bound requested duration."""
    from ...domain.studios.contextual_editing_v2 import ContextualEditPlanV2
    from ...domain.studios.editorial_production import ProductionRequestV1
    from ...domain.studios.production_timing import normalize_visual_duration
    from .contextual_editing import get_plan
    from .contextual_editing_v2 import create_plan

    stage = state.get("stage")
    result = completed_render.result_payload or {}
    artifact = result.get("artifact", {})
    request = ProductionRequestV1.model_validate(state["request"])
    target_ms = round(request.duration_seconds * 1000)
    repair_version = "res.visual-duration-binding.v2"
    repair_key = f"{completed_render.id}:{repair_version}"
    if (
        stage not in {"animatic", "render"}
        or completed_render.status != "succeeded"
        or artifact.get("durationMs", target_ms) >= target_ms - 80
        or repair_key in state.get("deterministicRenderRepairs", [])
    ):
        return None
    previous = get_plan(db, record.workspace_id, state["artifacts"]["plan"]["id"])
    if not isinstance(previous, ContextualEditPlanV2) or previous.status != "applied":
        return None
    direction = previous.direction.model_copy(deep=True)
    direction.expected_document_revision = record.revision
    direction, timing_repairs = normalize_visual_duration(direction, request.duration_seconds)
    revised = create_plan(
        db,
        record,
        direction,
        user,
        f"production:{state['id']}:{stage}:{repair_version}:{previous.id}",
    )
    if revised.status != "ready":
        return None
    state["artifacts"] = {
        **state.get("artifacts", {}),
        "plan": revised.model_dump(mode="json", by_alias=True),
        "shortRenderCandidate": result,
    }
    state["jobs"] = {
        key: value for key, value in state.get("jobs", {}).items() if key not in {"animatic", "render", "critique"}
    }
    state["deterministicRenderRepairs"] = [*state.get("deterministicRenderRepairs", []), repair_key]
    state["renderRepairHistory"] = [
        *state.get("renderRepairHistory", []),
        {
            "stage": stage,
            "failedJobId": completed_render.id,
            "sourcePlanId": previous.id,
            "revisedPlanId": revised.id,
            "repairVersion": repair_version,
            "providerSubmission": False,
            "reason": "render_shorter_than_requested_duration",
            "timingRepairs": timing_repairs,
        },
    ]
    state.update(status="pending", blockers=[])
    return revised


def prepare_response_correction(state, job, *, additional_diagnostic=None):
    stage = state["stage"]
    payload = job.result_payload or {}
    if stage not in {"direction", "composition"} or job.status not in {"failed", "retrying"}:
        return False
    editorial_motion = (state.get("request") or {}).get("cinematicDirectionPolicy") == "editorial_motion_v2"
    if editorial_motion and state.get("automaticCorrectionRounds", 0) >= 2:
        return False

    def count_correction():
        if editorial_motion:
            state["automaticCorrectionRounds"] = state.get("automaticCorrectionRounds", 0) + 1
    if (
        job.error_message == "editing_ai_incomplete_response"
        and payload.get("responseKey")
        and payload.get("submissionOutcome") == "accepted"
        and not payload.get("providerOperationId")
    ):
        incomplete_retries = dict(state.get("incompleteResponseRetries", {}))
        adapter_retries = dict(state.get("adapterCapacityRetries", {}))
        requested_output = int(
            (getattr(job, "request_payload", {}) or {}).get("maxOutputTokens", 0) or 0
        )
        usage = payload.get("usage") or {}
        produced_output = int(
            usage.get("completion_tokens", usage.get("candidatesTokenCount", 0)) or 0
        )
        configured_output = get_settings().studio_editing_ai_max_output_tokens
        capacity_recovery = (
            incomplete_retries.get(stage, 0) >= 1
            and adapter_retries.get(stage, 0) < 1
            and requested_output > 0
            and produced_output == requested_output
            and configured_output > requested_output
        )
        if incomplete_retries.get(stage, 0) >= 1 and not capacity_recovery:
            return False
        if capacity_recovery:
            adapter_retries[stage] = 1
            state["adapterCapacityRetries"] = adapter_retries
        else:
            incomplete_retries[stage] = 1
            state["incompleteResponseRetries"] = incomplete_retries
        creative_attempt = int(state.get("responseCorrections", {}).get(stage, 0))
        concise_error = (
            "The prior JSON response reached its output-token limit. Return the same requested contract "
            "completely and more concisely; do not omit required fields."
        )
        if additional_diagnostic:
            concise_error += (
                " Preserve the requested meaning while also fixing this latest validation diagnostic: "
                + additional_diagnostic[:1600]
            )
        if capacity_recovery:
            concise_error += (
                " The configured output capacity is now larger than the prior request. "
                "Use that capacity only to complete the same concise contract."
            )
        state["responseCorrection"] = {
            "stage": stage,
            "attempt": max(1, creative_attempt),
            "error": concise_error,
        }
        state["correctionHistory"] = [
            *state.get("correctionHistory", []),
            {
                "stage": stage,
                "jobId": job.id,
                "responseKey": payload["responseKey"],
                "category": "incomplete_response",
                "creativeCorrectionAttempt": creative_attempt,
                "completenessRetry": incomplete_retries.get(stage, 0),
                "adapterCapacityRetry": adapter_retries.get(stage, 0),
                "providerSubmission": True,
                "measuredCostUsd": payload.get("measuredCostUsd"),
            },
        ]
        state["jobs"] = {key: value for key, value in state["jobs"].items() if key != stage}
        state.update(status="pending", blockers=[])
        count_correction()
        return True
    if (
        payload.get("preflightFailure") == "editing_ai_prompt_too_large"
        and payload.get("submissionOutcome") == "rejected"
        and not payload.get("responseKey")
    ):
        attempts = dict(state.get("responseCorrections", {}))
        if attempts.get(stage, 0) >= 1:
            return False
        attempts[stage] = 1
        state["responseCorrections"] = attempts
        state["responseCorrection"] = {
            "stage": stage,
            "attempt": 1,
            "error": "Local prompt preflight exceeded the configured size; compact context is required.",
        }
        state["correctionHistory"] = [
            *state.get("correctionHistory", []),
            {
                "stage": stage,
                "jobId": job.id,
                "category": "local_prompt_preflight",
                "providerSubmission": False,
            },
        ]
        state["jobs"] = {key: value for key, value in state["jobs"].items() if key != stage}
        state.update(status="pending", blockers=[])
        count_correction()
        return True
    if not payload.get("responseKey") or payload.get("providerOperationId"):
        return False
    error = job.error_message or ""
    repairable_prefixes = ("production_", "editing_v2_", "editing_component_")
    if (
        job.error_code not in {"ValidationError", "JSONDecodeError"}
        and not error.startswith(repairable_prefixes)
    ):
        return False
    # Conflicts and missing external prerequisites cannot be fixed by regenerating a response.
    if any(token in error for token in ("revision_conflict", "asset_conflict", "checksum", "not_configured")):
        return False
    route_errors = (
        "editing_component_format_transformation_requires_shared_material",
        "production_semantic_repair_requires_alternative",
    )
    if any(token in error for token in route_errors):
        route_attempts = dict(state.get("routeCorrections", {}))
        if route_attempts.get(stage, 0) >= 1:
            return False
        route_attempts[stage] = route_attempts.get(stage, 0) + 1
        state["routeCorrections"] = route_attempts
        state["correctionHistory"] = [
            *state.get("correctionHistory", []),
            {
                "stage": stage,
                "jobId": job.id,
                "responseKey": payload["responseKey"],
                "category": "route_incompatible",
                "attempt": route_attempts[stage],
                "error": error[:2000],
            },
        ]
        state["responseCorrection"] = {
            "stage": stage,
            "attempt": int(state.get("responseCorrections", {}).get(stage, 0)),
            "routeAttempt": route_attempts[stage],
            "error": (
                error[:1600]
                + " Select an executable alternative route that preserves the approved message. "
                "A format_transformation must reuse one shared content identity across every viewport; "
                "otherwise choose another registered composition and explain the observable action."
            ),
        }
        state["jobs"] = {key: value for key, value in state["jobs"].items() if key != stage}
        state.update(status="pending", blockers=[])
        count_correction()
        return True
    attempts = dict(state.get("responseCorrections", {}))
    if attempts.get(stage, 0) >= 2:
        return False
    attempts[stage] = attempts.get(stage, 0) + 1
    state["responseCorrections"] = attempts
    state["correctionHistory"] = [
        *state.get("correctionHistory", []),
        {
            "stage": stage,
            "jobId": job.id,
            "responseKey": payload["responseKey"],
            "category": "invalid_response",
            "attempt": attempts[stage],
            "error": error[:2000],
        },
    ]
    state["responseCorrection"] = {"stage": stage, "attempt": attempts[stage], "error": error[:2000]}
    state["jobs"] = {key: value for key, value in state["jobs"].items() if key != stage}
    state.update(status="pending", blockers=[])
    count_correction()
    return True


def prepare_provider_recovery(state, job):
    """Release a definitively rejected transient submission for another profile.

    Model selection remains a server configuration concern. This state change
    only records the failed immutable binding and permits orchestration to
    create a new job. It never retries an uncertain or accepted submission.
    """
    stage = state.get("stage")
    payload = job.result_payload or {}
    http_status = payload.get("providerHttpStatus")
    provider_error_kind = str(payload.get("providerErrorKind") or "").lower()
    if (
        stage not in {"direction", "composition"}
        or job.status != "failed"
        or payload.get("submissionOutcome") != "rejected"
        or payload.get("responseKey")
        or provider_error_kind
        in {
            "insufficient_quota",
            "credit_balance_exhausted",
            "billing_hard_limit_reached",
            "billing_not_active",
        }
        or http_status not in {429, 500, 502, 503, 504}
    ):
        return False
    history = list(state.get("providerRecoveryHistory", []))
    recovery_key = f"{stage}:{job.provider}:{payload.get('model')}:{http_status}"
    prior = next((item for item in history if item.get("key") == recovery_key), None)
    if prior:
        # A process running older orchestration code could record the safe
        # recovery and then rediscover the same exhausted idempotency key. Once
        # the key format has been upgraded, release that exact stale binding;
        # never apply this to a later replacement job rejected in the same way.
        if (
            prior.get("jobId") == job.id
            and (state.get("jobs") or {}).get(stage) == job.id
        ):
            state["jobs"] = {
                key: value for key, value in state.get("jobs", {}).items() if key != stage
            }
            state.update(status="pending", blockers=[])
            return True
        configured_model = (
            get_settings().studio_editing_ai_model
            if job.provider == "compatible.editing-planner"
            else None
        )
        failed_model = payload.get("model")
        fallback_key = f"{recovery_key}:fallback:{configured_model}"
        if (
            configured_model
            and failed_model
            and configured_model != failed_model
            and not any(item.get("key") == fallback_key for item in history)
        ):
            history.append(
                {
                    "key": fallback_key,
                    "stage": stage,
                    "jobId": job.id,
                    "provider": job.provider,
                    "model": failed_model,
                    "targetModel": configured_model,
                    "httpStatus": http_status,
                    "submissionOutcome": "rejected",
                }
            )
            state["providerRecoveryHistory"] = history
            state["jobs"] = {
                key: value for key, value in state.get("jobs", {}).items() if key != stage
            }
            state.update(status="pending", blockers=[])
            return True
        return False
    history.append(
        {
            "key": recovery_key,
            "stage": stage,
            "jobId": job.id,
            "provider": job.provider,
            "model": payload.get("model"),
            "httpStatus": http_status,
            "submissionOutcome": "rejected",
        }
    )
    state["providerRecoveryHistory"] = history
    state["jobs"] = {key: value for key, value in state.get("jobs", {}).items() if key != stage}
    state.update(status="pending", blockers=[])
    return True
