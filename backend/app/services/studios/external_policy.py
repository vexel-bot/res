"""Shared pre-submission policy and durable monthly USD reservations.

Uses existing job rows and the shared transactional budget lock. No second ledger,
no provider POST retry and no inference that an estimate is an invoice.
"""

import math
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select

from ...models import StudioGenerationJob


def billing_scope(user, workspace_id, db=None):
    trusted = getattr(user, "_studio_billing_scope", None)
    if trusted:
        return dict(trusted)
    if getattr(user, "password_hash", None) == "!session-bridge-only":
        # Background continuations reload the ORM user, without HTTP attributes.
        # Recover only from this actor's server-created planning/media audit.
        if db is not None:
            previous = db.scalars(
                select(StudioGenerationJob)
                .where(
                    StudioGenerationJob.workspace_id == workspace_id,
                    StudioGenerationJob.requested_by == user.id,
                    StudioGenerationJob.job_type.in_(["editing_ai", "editing_gemini", "craft_ai"]),
                )
                .order_by(StudioGenerationJob.created_at.desc())
                .limit(1)
            ).first()
            scope = previous.request_payload.get("billingScope") if previous else None
            if (
                isinstance(scope, dict)
                and set(scope) == {"workspaceId", "userId"}
                and all(isinstance(value, str) and value for value in scope.values())
            ):
                return dict(scope)
        raise ValueError("commercial_billing_scope_required")
    return {"workspaceId": workspace_id, "userId": user.id}


def job_scope(job):
    return job.request_payload.get("billingScope") or {"workspaceId": job.workspace_id, "userId": job.requested_by}


def assert_operation(settings, provider, operation, *, model=None, media=False, seconds=None):
    if "video" in operation and seconds is not None:
        from ...providers.studios.editing_ai import ADAPTERS

        spec = next((item for item in ADAPTERS.values() if item.id == provider), None)
        if spec and (
            (spec.min_video_seconds is not None and seconds < spec.min_video_seconds)
            or (spec.max_video_seconds is not None and seconds > spec.max_video_seconds)
        ):
            raise ValueError("editing_video_duration_unsupported")
    if provider == "google.gemini-editing" and "video" in operation:
        if not settings.gemini_outbound_enabled or not settings.gemini_video_generation_enabled:
            raise ValueError("gemini_video_generation_disabled")
        if settings.gemini_max_external_spend_usd <= 0:
            raise ValueError("gemini_video_spend_limit_required")
        if model and model.startswith("veo-") and (operation != "generate_video" or media or seconds not in {4, 6, 8}):
            raise ValueError("veo_text_to_video_duration_required")


def committed(job):
    state = job.result_payload or {}
    # A lost acknowledgement retains its full reservation until reconciled.
    if state.get("preflightFailure") and state.get("submissionOutcome") == "rejected":
        return 0.0
    if not state.get("submissionStarted") and job.status in {"failed", "cancelled"}:
        return 0.0
    actual = state.get("providerReportedCostUsd")
    estimate = state.get("estimatedCostUsd", state.get("measuredCostUsd"))
    reservation = max(
        float(state.get("financialReservationUsd", 0) or 0),
        float(state.get("testReservationUsd", 0) or 0),
        float(state.get("llmReservationUsd", 0) or 0),
    )
    # Tariff estimates never release uncertainty, and invoice data cannot conceal a larger hold.
    return max(reservation, float(actual or 0), float(estimate or 0))


def reserve_monthly(db, job, amount, settings):
    from .contextual_editing import lock_editing_budget

    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("external_reservation_invalid")
    limits = (
        settings.studio_external_monthly_budget_usd,
        settings.studio_external_workspace_monthly_budget_usd,
        settings.studio_external_user_monthly_budget_usd,
    )
    if any(not math.isfinite(limit) or limit <= 0 for limit in limits):
        raise ValueError("external_monthly_budget_required")
    model = job.request_payload.get("model", "")
    from .model_lifecycle import assert_supported

    assert_supported(model)
    model_limit = settings.studio_external_model_monthly_budgets.get(model, 0)
    if not model or not math.isfinite(model_limit) or model_limit <= 0:
        raise ValueError("external_model_budget_required")
    lock_editing_budget(db, job.workspace_id)
    start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period = start.strftime("%Y-%m")
    video = job.provider == "google.gemini-editing" and "video" in job.request_payload.get("input", {}).get(
        "operation", ""
    )
    rows = (
        db.scalars(
            select(StudioGenerationJob).where(
                StudioGenerationJob.id != job.id,
                or_(
                    StudioGenerationJob.created_at >= start,
                    StudioGenerationJob.result_payload["financialPeriod"].as_string() == period,
                    # Unreconciled submissions remain liabilities across month boundaries.
                    StudioGenerationJob.result_payload["submissionOutcome"].as_string() == "unknown",
                    and_(
                        StudioGenerationJob.result_payload["submissionStarted"].as_boolean().is_(True),
                        or_(
                            StudioGenerationJob.result_payload["submissionOutcome"].as_string().is_(None),
                            StudioGenerationJob.result_payload["submissionOutcome"].as_string() == "pending",
                        ),
                    ),
                ),
            )
        ).all()
        if any(limit > 0 for limit in limits) or video
        else []
    )
    current_scope = job_scope(job)
    scopes = (
        rows,
        [row for row in rows if job_scope(row)["workspaceId"] == current_scope["workspaceId"]],
        [row for row in rows if job_scope(row) == current_scope],
    )
    for limit, scope in zip(limits, scopes, strict=True):
        if limit > 0 and sum(committed(row) for row in scope) + amount > limit + 1e-9:
            raise ValueError("external_monthly_budget_exceeded")
    model_used = sum(committed(row) for row in rows if row.request_payload.get("model") == model)
    if model_used + amount > model_limit + 1e-9:
        raise ValueError("external_model_budget_exceeded")
    if video:
        video_used = sum(
            committed(row)
            for row in rows
            if row.provider == job.provider and "video" in row.request_payload.get("input", {}).get("operation", "")
        )
        if video_used + amount > settings.gemini_max_external_spend_usd + 1e-9:
            raise ValueError("gemini_video_spend_limit_exceeded")
    job.result_payload = {
        **(job.result_payload or {}),
        "financialReservationUsd": amount,
        "financialPeriod": period,
        "costCurrency": "USD",
        "providerReportedCostUsd": None,
        "costSource": "conservative-reservation",
    }
