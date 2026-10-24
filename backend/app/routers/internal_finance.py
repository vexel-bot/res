"""Non-browser, signed Node admission using the SAME transactional Studios USD ledger.

No prompts, credentials or responses are stored here. Unknown submissions retain
their full hold. These records are not queue jobs and cannot be retried as jobs.
"""

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import StudioGenerationJob, User, Workspace
from ..services.studios.external_policy import job_scope, reserve_monthly
from ..studio_bridge_key import bridge_secret

router = APIRouter(prefix="/internal/finance", tags=["internal-finance"])


def actor(credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))):
    try:
        if not credentials:
            raise ValueError("missing")
        claims = jwt.decode(
            credentials.credentials, bridge_secret(), algorithms=["HS256"], audience="clicko-finance",
            issuer="clicko-governance", options={"require": ["exp", "iat", "sub", "workspaceId"]},
        )
        if claims.get("type") != "external_finance" or not all(
            isinstance(claims[key], str) and 0 < len(claims[key]) <= 128 for key in ("sub", "workspaceId")
        ):
            raise ValueError("invalid")
        return {"workspaceId": claims["workspaceId"], "userId": claims["sub"]}
    except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
        raise HTTPException(401, detail={"code": "FINANCE_AUTH_REQUIRED"}) from exc


class Reservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["google.klic", "google.cloud-tts"]
    model: str = Field(min_length=1, max_length=160)
    operation: Literal["generate", "stream", "synthesize"]
    key: str = Field(min_length=8, max_length=128)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    units: int = Field(default=0, ge=0, le=20_000_000)


class Settlement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["completed", "unknown"]
    input_tokens: int | None = Field(default=None, ge=0, le=1_000_000_000)
    output_tokens: int | None = Field(default=None, ge=0, le=1_000_000_000)


def tariff(request):
    settings = get_settings()
    if not settings.studio_node_outbound_enabled:
        raise ValueError("FINANCE_OUTBOUND_DISABLED")
    config = settings.studio_node_tariffs.get(request.provider + ":" + request.model, {})
    required = ("revision", "validUntil", "unit", "inputUsdPerMillion", "outputUsdPerMillion", "maxInput", "maxOutput")
    if not all(key in config for key in required) or not config.get("revision"):
        raise ValueError("FINANCE_TARIFF_REQUIRED")
    if datetime.fromisoformat(config["validUntil"]).date() < datetime.now(UTC).date():
        raise ValueError("FINANCE_TARIFF_EXPIRED")
    expected = "characters" if request.provider == "google.cloud-tts" else "tokens"
    if config["unit"] != expected or (request.provider == "google.cloud-tts") != (request.operation == "synthesize"):
        raise ValueError("FINANCE_OPERATION_INVALID")
    for key in ("inputUsdPerMillion", "outputUsdPerMillion", "maxInput", "maxOutput"):
        if not isinstance(config[key], (float, int)) or not math.isfinite(config[key]) or config[key] < 0:
            raise ValueError("FINANCE_TARIFF_INVALID")
    if not 0 < config["maxInput"] <= 20_000_000 or not 0 < config["maxOutput"] <= 65536:
        raise ValueError("FINANCE_TARIFF_INVALID")
    if request.units > config["maxInput"]:
        raise ValueError("FINANCE_INPUT_LIMIT")
    # Multimodal tokenization is not inferred from bytes. Reserve the configured
    # FULL model input ceiling plus bounded output (including thinking tokens).
    count = request.units if expected == "characters" else config["maxInput"]
    amount = (count * config["inputUsdPerMillion"] + (
        config["maxOutput"] * config["outputUsdPerMillion"] if expected == "tokens" else 0
    )) / 1_000_000
    if amount <= 0:
        raise ValueError("FINANCE_TARIFF_INVALID")
    return dict(config), amount


def receipt(job):
    return {"id": job.id, "status": job.status, "maxOutputTokens": job.request_payload["tariff"]["maxOutput"],
            "reservedUsd": job.result_payload["financialReservationUsd"]}


@router.post("/reserve")
def reserve(request: Reservation, scope=Depends(actor), db: Session = Depends(get_db)):
    try:
        config, amount = tariff(request)
        workspace = str(uuid5(NAMESPACE_URL, "clicko-finance:" + scope["workspaceId"]))
        user = str(uuid5(NAMESPACE_URL, "clicko-finance-user:" + scope["userId"]))
        # Isolated service ledger identities have no password/session/membership.
        # No customer documents or governance rows are changed.
        if not db.get(Workspace, workspace):
            db.add(Workspace(id=workspace, name="Financial admission ledger"))
        if not db.get(User, user):
            db.add(User(id=user, email=user + "@finance.clicko.internal", name="Service ledger",
                        password_hash="!finance-service-only", is_active=False))
        db.flush()
        from ..services.studios.contextual_editing import lock_editing_budget

        lock_editing_budget(db, workspace)
        key = hashlib.sha256((scope["userId"] + ":" + request.key).encode()).hexdigest()
        digest = hashlib.sha256(json.dumps(request.model_dump(exclude={"key"}), sort_keys=True).encode()).hexdigest()
        existing = db.scalar(select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == workspace, StudioGenerationJob.job_type == "external_call",
            StudioGenerationJob.idempotency_key == key,
        ))
        if existing:
            if existing.payload_hash != digest:
                raise ValueError("FINANCE_IDEMPOTENCY_CONFLICT")
            return receipt(existing)
        job = StudioGenerationJob(
            workspace_id=workspace, requested_by=user, job_type="external_call", provider=request.provider,
            idempotency_key=key, payload_hash=digest, correlation_id=request.key, status="reserved",
            max_attempts=1, request_payload={"billingScope": scope, "model": request.model,
                "operation": request.operation, "units": request.units, "tariff": config},
        )
        db.add(job)
        db.flush()
        reserve_monthly(db, job, amount, get_settings())
        db.commit()
        return receipt(job)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, detail={"code": "FINANCE_RESERVATION_CONFLICT"}) from exc
    except (ValueError, TypeError) as exc:
        db.rollback()
        code = str(exc) if str(exc).startswith(("FINANCE_", "external_")) else "FINANCE_TARIFF_INVALID"
        raise HTTPException(403, detail={"code": code}) from exc


def owned(db, job_id, scope):
    job = db.get(StudioGenerationJob, job_id)
    if not job or job.job_type != "external_call" or job_scope(job) != scope:
        raise HTTPException(404, detail={"code": "FINANCE_RECEIPT_NOT_FOUND"})
    return job


@router.post("/{job_id}/start")
def start(job_id: str, scope=Depends(actor), db: Session = Depends(get_db)):
    job = owned(db, job_id, scope)
    if not get_settings().studio_node_outbound_enabled:
        raise HTTPException(403, detail={"code": "FINANCE_OUTBOUND_DISABLED"})
    if job.result_payload.get("financialPeriod") != datetime.now(UTC).strftime("%Y-%m"):
        raise HTTPException(409, detail={"code": "FINANCE_RESERVATION_EXPIRED"})
    created = job.created_at.replace(tzinfo=UTC) if job.created_at.tzinfo is None else job.created_at
    if created + timedelta(seconds=60) < datetime.now(UTC):
        raise HTTPException(409, detail={"code": "FINANCE_RESERVATION_EXPIRED"})
    current = get_settings().studio_node_tariffs.get(job.provider + ":" + job.request_payload["model"])
    if current != job.request_payload["tariff"]:
        raise HTTPException(409, detail={"code": "FINANCE_TARIFF_REVISION_CHANGED"})
    from ..services.studios.model_lifecycle import lifecycle

    if lifecycle(job.request_payload["model"])["status"] == "retired":
        raise HTTPException(403, detail={"code": "FINANCE_MODEL_RETIRED"})
    # Claim is irreversible; a lost ACK must NOT authorize a second provider POST.
    result = db.execute(update(StudioGenerationJob).where(
        StudioGenerationJob.id == job.id, StudioGenerationJob.status == "reserved",
    ).values(status="running", attempts=1, started_at=datetime.now(UTC), result_payload={
        **job.result_payload, "submissionStarted": True, "submissionOutcome": "unknown",
    }))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, detail={"code": "FINANCE_SUBMISSION_ALREADY_CLAIMED"})
    db.commit()
    return {"admitted": True}


@router.post("/{job_id}/settle")
def settle(job_id: str, request: Settlement, scope=Depends(actor), db: Session = Depends(get_db)):
    job = owned(db, job_id, scope)
    if job.status == "reserved":
        raise HTTPException(409, detail={"code": "FINANCE_SUBMISSION_NOT_STARTED"})
    if job.status != "running":
        return receipt(job)
    config = job.request_payload["tariff"]
    usage = request.input_tokens is not None and request.output_tokens is not None
    estimate = (
        (request.input_tokens * config["inputUsdPerMillion"] + request.output_tokens * config["outputUsdPerMillion"])
        / 1_000_000 if usage else None
    )
    state = {**job.result_payload, "submissionOutcome": request.outcome,
        "inputTokens": request.input_tokens, "outputTokensIncludingThinking": request.output_tokens,
        "estimatedCostUsd": estimate, "costSource": "tariff-estimate-not-invoice" if usage else "unreconciled-hold"}
    # Do not release holds based on estimates or an unverified transport failure.
    db.execute(update(StudioGenerationJob).where(
        StudioGenerationJob.id == job.id, StudioGenerationJob.status == "running",
    ).values(status="succeeded" if request.outcome == "completed" else "failed",
             finished_at=datetime.now(UTC), result_payload=state))
    db.commit()
    db.refresh(job)
    return receipt(job)
