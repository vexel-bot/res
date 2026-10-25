"""Isolated admission/configuration for the existing Gemini transport and agent jobs.

No key can prove its project's billing tier. Inference therefore requires a
short-lived, server-controlled verification receipt; the UI cannot manufacture it.
"""

import hashlib
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from ...config import get_settings
from ...domain.studios.motion_gemini import MotionFreeTierEvidence
from ...models import StudioGenerationJob, StudioLLMConnection
from ...providers.studios.universal_llm import UniversalLLMPlanner
from . import llm_connections as connections
from .contextual_editing import lock_editing_budget

PROVIDER = "google-motion-experimental"
BASE = "https://generativelanguage.googleapis.com/v1beta"


def enabled():
    s = get_settings()
    return s.environment != "production" and s.clicko_dev_mode and s.clicko_motion_gemini_experimental


def require_dev(request):
    if not enabled() or not getattr(request.state, "motion_gemini_experimental", False):
        raise HTTPException(404, detail={"code": "motion_gemini_dev_only"})


def row_for(db, workspace_id, user_id):
    return db.scalar(
        select(StudioLLMConnection).where(
            StudioLLMConnection.workspace_id == workspace_id,
            StudioLLMConnection.created_by == user_id,
            StudioLLMConnection.provider == PROVIDER,
        )
    )


def now():
    return datetime.now(UTC)


def catalog_current(config):
    try:
        checked = datetime.fromisoformat(config.get("checkedAt", ""))
        return bool(
            checked.tzinfo
            and timedelta(0) <= now() - checked < timedelta(hours=1)
            and config.get("selectedModel") in config.get("models", [])
            and config.get("connectionStatus") == "catalog_verified"
        )
    except (TypeError, ValueError):
        return False


def evidence(row):
    """Operator-reviewed billing/quotas, not a user-supplied price or an API catalog flag."""
    filename = get_settings().clicko_motion_gemini_free_tier_evidence_file
    if not filename:
        raise ValueError("motion_gemini_free_tier_unverified")
    root = Path(os.environ.get("CLICKO_LOCAL_DATA_DIR", ".codex-runtime/clicko-dev")).resolve()
    path = Path(filename).resolve()
    try:
        if not path.is_relative_to(root) or path.is_symlink() or path.stat().st_size > 32000:
            raise ValueError("motion_gemini_evidence_invalid")
        data = MotionFreeTierEvidence.model_validate_json(path.read_text(encoding="utf-8"))
        start, end = datetime.fromisoformat(data.verified_at), datetime.fromisoformat(data.expires_at)
        credential = connections.decrypt(row)
        if (
            not start.tzinfo
            or not end.tzinfo
            or not start <= now() < end
            or end - start > timedelta(hours=24)
            or not data.billing_disabled
            or not data.inference_authorized
            or not data.structured_output_verified
            or data.workspace_id != row.workspace_id
            or data.user_id != row.created_by
            or data.model != row.config.get("selectedModel")
            or data.credential_sha256 != hashlib.sha256(credential.encode()).hexdigest()
        ):
            raise ValueError("motion_gemini_free_tier_unverified")
        return data
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError("motion_gemini_free_tier_unverified") from exc


def status(db, workspace_id, user):
    connections.access(db, user.id, workspace_id, owner=True)
    row = row_for(db, workspace_id, user.id)
    proof, pending = None, "motion_gemini_key_required"
    if row and row.credential_ciphertext:
        try:
            proof = evidence(row)
            pending = None
        except (ValueError, OSError):
            pending = "motion_gemini_free_tier_unverified"
    config = row.config if row else {}
    return {
        "available": enabled(),
        "hasCredential": bool(row and row.credential_ciphertext),
        "enabled": bool(config.get("experimentEnabled")),
        "model": config.get("selectedModel"),
        "models": config.get("discoveredModels", []),
        "connectionStatus": config.get("connectionStatus", "not_tested"),
        "checkedAt": config.get("checkedAt"),
        "freeTierVerified": bool(proof),
        "pendingReason": pending,
        "inferenceReady": bool(proof and catalog_current(config) and config.get("experimentEnabled")),
        "externalBudgetUsd": 0,
        "quota": (
            {
                "requestsPerMinute": proof.requests_per_minute,
                "requestsPerDay": proof.requests_per_day,
                "maxOutputTokens": proof.max_output_tokens,
            }
            if proof
            else None
        ),
    }


def save_key(db, workspace_id, user, key):
    connections.access(db, user.id, workspace_id, owner=True)
    # Credentials are opaque: newer Google auth keys are not the legacy 39-char
    # AIza traffic key. Check safe header syntax/size here; Google validates access.
    if not re.fullmatch(r"[A-Za-z0-9._~+/=-]{20,8192}", key):
        raise ValueError("motion_gemini_key_invalid")
    lock_editing_budget(db, workspace_id)
    row = row_for(db, workspace_id, user.id)
    config = {
        "baseUrl": BASE,
        "protocol": "gemini_generate",
        "models": [],
        "enabled": False,
        "billingMode": "metered",
        "budgetUsd": 0,
        "maxOutputTokens": 6000,
        "authHeader": "x-goog-api-key",
        "authPrefix": "",
        "experimentEnabled": False,
        "connectionStatus": "not_tested",
    }
    if not row:
        row = StudioLLMConnection(
            id=str(uuid4()),
            workspace_id=workspace_id,
            created_by=user.id,
            provider=PROVIDER,
            label="Motion Gemini experimental",
            revision=0,
            config=config,
        )
        db.add(row)
    row.config = config
    row.credential_ciphertext = connections.encrypt(row, key)
    row.revision += 1
    db.commit()
    return status(db, workspace_id, user)


def remove_key(db, workspace_id, user):
    connections.access(db, user.id, workspace_id, owner=True)
    lock_editing_budget(db, workspace_id)
    row = row_for(db, workspace_id, user.id)
    if row:
        row.credential_ciphertext = None
        row.config = {
            **row.config,
            "experimentEnabled": False,
            "models": [],
            "discoveredModels": [],
            "selectedModel": None,
            "connectionStatus": "not_tested",
        }
        row.revision += 1
        db.commit()
    return status(db, workspace_id, user)


def discover(db, workspace_id, user):
    connections.access(db, user.id, workspace_id, owner=True)
    row = row_for(db, workspace_id, user.id)
    if not row or not row.credential_ciphertext:
        raise ValueError("motion_gemini_key_required")
    revision = row.revision
    # No query-string key, environment key, redirects, retries or inference.
    try:
        models = UniversalLLMPlanner(row.config, connections.decrypt(row)).gemini_models()
    except ValueError:
        row.config = {
            **row.config,
            "experimentEnabled": False,
            "connectionStatus": "failed",
            "models": [],
            "discoveredModels": [],
        }
        row.revision += 1
        db.commit()
        raise
    db.refresh(row)
    if row.revision != revision:
        raise ValueError("motion_gemini_configuration_conflict")
    old = row.config.get("selectedModel")
    row.config = {
        **row.config,
        "models": [m["id"] for m in models],
        "discoveredModels": models,
        "selectedModel": old if old in {m["id"] for m in models} else None,
        "connectionStatus": "catalog_verified",
        "checkedAt": now().isoformat(),
    }
    row.revision += 1
    db.commit()
    return status(db, workspace_id, user)


def configure(db, workspace_id, user, request):
    connections.access(db, user.id, workspace_id, owner=True)
    lock_editing_budget(db, workspace_id)
    row = row_for(db, workspace_id, user.id)
    if not row or not row.credential_ciphertext:
        raise ValueError("motion_gemini_key_required")
    if request.model and request.model not in row.config["models"]:
        raise ValueError("motion_gemini_model_unverified")
    row.config = {
        **row.config,
        "experimentEnabled": request.enabled,
        "selectedModel": request.model or row.config.get("selectedModel"),
    }
    row.revision += 1
    db.commit()
    return status(db, workspace_id, user)


def admitted_planner(db, document, user):
    from .compatibility import record_to_contract

    contract = record_to_contract(document)
    production = contract.composition.narrative.get("localProduction", {})
    if (
        not enabled()
        or contract.content_type != "video"
        or contract.native_editor_state
        or not isinstance(production, dict)
        or production.get("kind") != "motion"
    ):
        raise ValueError("motion_gemini_dev_only")
    connections.access(db, user.id, document.workspace_id, owner=True)
    row = row_for(db, document.workspace_id, user.id)
    if not row or not row.config.get("experimentEnabled"):
        raise ValueError("motion_gemini_not_enabled")
    proof = evidence(row)
    model = row.config.get("selectedModel")
    if not catalog_current(row.config):
        raise ValueError("motion_gemini_model_unverified")
    return (
        row,
        UniversalLLMPlanner({**row.config, "maxOutputTokens": proof.max_output_tokens}, connections.decrypt(row)),
        model,
        proof,
    )


def reserve(db, job, row, proof):
    """Shared workspace write lock + durable agent jobs include unknown/cancelled attempts."""
    lock_editing_budget(db, row.workspace_id)
    db.refresh(row)
    current = evidence(row)  # Revocation/expiry is rechecked immediately before admission.
    if current.model != proof.model or current.credential_sha256 != proof.credential_sha256:
        raise ValueError("motion_gemini_configuration_conflict")
    if not row.config.get("experimentEnabled") or not row.credential_ciphertext:
        raise ValueError("motion_gemini_not_enabled")
    recent = list(
        db.scalars(
            select(StudioGenerationJob).where(
                StudioGenerationJob.workspace_id == row.workspace_id,
                StudioGenerationJob.provider == "google.motion-gemini",
                StudioGenerationJob.requested_by == row.created_by,
                StudioGenerationJob.created_at >= now() - timedelta(days=1),
            )
        )
    )
    minute = now().replace(tzinfo=None) - timedelta(minutes=1)
    if (
        len(recent) >= proof.requests_per_day
        or sum(r.created_at.replace(tzinfo=None) >= minute for r in recent) >= proof.requests_per_minute
    ):
        raise ValueError("motion_gemini_local_quota_exhausted")
    recent_tokens = sum(
        r.request_payload.get("inputTokenReservation", 24000)
        for r in recent
        if r.created_at.replace(tzinfo=None) >= minute
    )
    if recent_tokens + 24000 > proof.input_tokens_per_minute:
        raise ValueError("motion_gemini_local_quota_exhausted")
    job.request_payload = {
        **job.request_payload,
        "credentialRevision": row.revision,
        "freeTierProjectId": proof.project_id,
        "freeTierEvidenceExpiresAt": proof.expires_at,
        "inputTokenReservation": 24000,
    }
    job.result_payload = {"llmReservationUsd": 0, "billingAdmission": "verified_free_tier"}
