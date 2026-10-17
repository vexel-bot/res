"""Tenant-owned model connections; public metadata never contains credentials."""

import base64
import hashlib
import json
import math
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import select, update

from ...config import get_settings
from ...domain.studios.llm import LLMConnectionRequest
from ...models import Membership, StudioGenerationJob, StudioLLMConnection
from ...providers.studios.universal_llm import UniversalLLMPlanner, validate_endpoint
from .contextual_editing import lock_editing_budget


def access(db, user_id, workspace_id, *, owner=False):
    role = db.scalar(select(Membership.role).where(
        Membership.user_id == user_id, Membership.workspace_id == workspace_id,
    ))
    if not role:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if owner and role.lower() not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Workspace administrator required")


def scoped(db, workspace_id, connection_id):
    row = db.scalar(select(StudioLLMConnection).where(
        StudioLLMConnection.id == connection_id, StudioLLMConnection.workspace_id == workspace_id,
    ))
    if not row:
        raise ValueError("llm_connection_not_found")
    return row


def cipher():
    key = get_settings().studio_llm_credential_key
    if not key:
        raise ValueError("llm_server_credential_key_not_configured")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.get_secret_value().encode()).digest()))


def binding(row):
    return {"workspaceId": row.workspace_id, "connectionId": row.id,
            "baseUrl": row.config["baseUrl"], "protocol": row.config["protocol"]}


def encrypt(row, secret):
    return cipher().encrypt(json.dumps({**binding(row), "secret": secret}).encode()).decode()


def decrypt(row):
    if not row.credential_ciphertext:
        return None
    try:
        payload = json.loads(cipher().decrypt(row.credential_ciphertext.encode()))
        if any(payload.get(key) != value for key, value in binding(row).items()):
            raise ValueError("llm_credential_scope_mismatch")
        return payload["secret"]
    except (InvalidToken, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("llm_credential_unavailable") from exc


def public(row):
    return {"id": row.id, "workspaceId": row.workspace_id, "label": row.label, "provider": row.provider,
            "revision": row.revision, "hasCredential": bool(row.credential_ciphertext), "config": row.config,
            "qualification": "configured_live_qualification_pending"}


def save(db, workspace_id, request: LLMConnectionRequest, user, connection_id=None):
    access(db, user.id, workspace_id, owner=True)
    config = request.model_dump(
        by_alias=True, mode="json", exclude={"api_key", "expected_revision", "label", "provider"},
    )
    local = validate_endpoint(config)
    secret = request.api_key.get_secret_value() if request.api_key else None
    if secret and (len(secret) > 16000 or "\r" in secret or "\n" in secret):
        raise ValueError("llm_credential_invalid")
    if connection_id:
        row = scoped(db, workspace_id, connection_id)
        if request.expected_revision != row.revision:
            raise ValueError("llm_connection_revision_conflict")
        if (
            row.credential_ciphertext
            and any(row.config[k] != config[k] for k in ("baseUrl", "protocol")) and not secret
        ):
            raise ValueError("llm_endpoint_change_requires_credential")
        old_revision = row.revision
        ciphertext = row.credential_ciphertext
        # Bind encryption to the candidate destination without mutating the ORM
        # row before the optimistic update has succeeded.
        candidate = StudioLLMConnection(id=row.id, workspace_id=workspace_id, config=config)
        if secret:
            ciphertext = encrypt(candidate, secret)
        if request.enabled and not local and not ciphertext:
            raise ValueError("llm_credential_required")
        changed = db.execute(update(StudioLLMConnection).where(
            StudioLLMConnection.id == row.id, StudioLLMConnection.revision == old_revision,
        ).values(label=request.label, provider=request.provider, config=config,
                 credential_ciphertext=ciphertext, revision=old_revision + 1))
        if changed.rowcount != 1:
            db.rollback()
            raise ValueError("llm_connection_revision_conflict")
    else:
        row = StudioLLMConnection(id=str(uuid4()), workspace_id=workspace_id, label=request.label,
                                  provider=request.provider, config=config, revision=1, created_by=user.id)
        if secret:
            row.credential_ciphertext = encrypt(row, secret)
        if request.enabled and not local and not row.credential_ciphertext:
            raise ValueError("llm_credential_required")
        db.add(row)
    db.commit()
    db.refresh(row)
    return public(row)


def planner(db, workspace_id, connection_id, model):
    row = scoped(db, workspace_id, connection_id)
    if not row.config["enabled"]:
        raise ValueError("llm_connection_disabled")
    model = model or row.config["models"][0]
    if model not in row.config["models"]:
        raise ValueError("llm_model_not_registered")
    config_hash = hashlib.sha256(json.dumps(row.config, sort_keys=True).encode()).hexdigest()
    fingerprint = hashlib.sha256((row.id + ":" + str(row.revision) + ":" + config_hash).encode()).hexdigest()
    return row, UniversalLLMPlanner(row.config, decrypt(row)), model, fingerprint


def reserve_request(db, job, connection, prompt_chars, tokens):
    """The configured lifetime ceiling includes requests with unknown outcomes."""
    lock_editing_budget(db, connection.workspace_id)
    db.refresh(connection)
    config = connection.config
    if job.request_payload.get("llmConnectionRevision") != connection.revision:
        raise ValueError("llm_connection_revision_conflict")
    if not config["enabled"]:
        raise ValueError("llm_connection_disabled")
    if config["billingMode"] == "local_free":
        validate_endpoint(config)
        amount = 0.0
    else:
        in_rate, out_rate = config["inputUsdPerMillion"], config["outputUsdPerMillion"]
        if in_rate <= 0 or out_rate <= 0 or config["budgetUsd"] <= 0:
            raise ValueError("llm_pricing_and_budget_required")
        amount = math.ceil(((prompt_chars / 3 * in_rate + tokens * out_rate) / 1000000) * 1000000) / 1000000
        # Reserve the full UTF-8 byte count as tokens: dense JSON and non-Latin
        # strings cannot bypass the configured ceiling via a chars/3 estimate.
        amount = max(amount, (prompt_chars * in_rate + tokens * out_rate) / 1000000)
        used = 0.0
        for previous in db.scalars(select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == connection.workspace_id,
            StudioGenerationJob.job_type == "craft_ai",
        )):
            if previous.id != job.id and previous.request_payload.get("llmConnectionId") == connection.id:
                used += float((previous.result_payload or {}).get("llmReservationUsd", 0))
        if used + amount > config["budgetUsd"]:
            raise ValueError("llm_connection_budget_exceeded")
    job.result_payload = {**(job.result_payload or {}), "llmReservationUsd": amount}
