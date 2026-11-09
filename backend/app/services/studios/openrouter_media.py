"""Authenticated generated media with durable idempotency, reservations and provenance."""

import hashlib
import json
import math
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ...config import get_settings
from ...domain.studios.contracts import AssetReferenceV1
from ...models import StudioGenerationJob
from ...providers.studios.openrouter_media import OpenRouterMediaProvider
from .compatibility import persist_contract, record_to_contract
from .contextual_editing import lock_editing_budget
from .craft import write_asset
from .external_policy import billing_scope, committed, reserve_monthly
from .llm_connections import decrypt, scoped


def provider(db, workspace_id, connection_id):
    row = scoped(db, workspace_id, connection_id)
    if row.provider != "openrouter" or row.config.get("baseUrl", "").rstrip("/") != "https://openrouter.ai/api/v1":
        raise ValueError("openrouter_media_official_connection_required")
    if not row.config.get("enabled") or row.config.get("billingMode") != "metered":
        raise ValueError("openrouter_media_connection_disabled")
    secret = decrypt(row)
    if not secret:
        raise ValueError("llm_credential_required")
    return row, OpenRouterMediaProvider(secret)


def estimate(request, model):
    rates = model.get("pricing_skus", {})
    if request.kind == "speech":
        rate = float(model.get("pricing", {}).get("prompt", 0))
        amount = rate * len(request.text)
    else:
        if request.duration_seconds not in model.get("supported_durations", []):
            raise ValueError("openrouter_media_duration_unsupported")
        if request.resolution not in model.get("supported_resolutions", []) or request.aspect_ratio not in model.get(
            "supported_aspect_ratios", []
        ):
            raise ValueError("openrouter_media_dimensions_unsupported")
        audio = "with_audio" if request.generate_audio else "without_audio"
        rate = rates.get(f"duration_seconds_{audio}_{request.resolution}")
        if rate is None:
            rate = rates.get(f"duration_seconds_{request.resolution}", rates.get(f"duration_seconds_{audio}"))
        # Token-priced video models require a different calculator; fail closed.
        if rate is None:
            raise ValueError("openrouter_media_pricing_unsupported")
        amount = float(rate) * request.duration_seconds
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("openrouter_media_pricing_required")
    return math.ceil(amount * 1_000_000) / 1_000_000


def out(job):
    state = job.result_payload or {}
    outcome = state.get("submissionOutcome")
    return {
        "id": job.id,
        "status": job.status,
        "kind": job.request_payload.get("kind"),
        "submissionOutcome": outcome,
        "requiresReconciliation": outcome in {"unknown", "pending", "response_received"},
        "canDiscardPending": outcome in {"completed", "rejected", "failed"},
        "assetId": state.get("assetId"),
        "downloadUrl": state.get("downloadUrl"),
        "providerOperationId": state.get("providerOperationId"),
        "estimatedCostUsd": state.get("estimatedCostUsd"),
        "providerReportedCostUsd": state.get("providerReportedCostUsd"),
        "errorCode": job.error_code,
    }


def create(db, record, request, user, key):
    payload = request.model_dump(mode="json", by_alias=True)
    digest = hashlib.sha256(json.dumps({"documentId": record.id, **payload}, sort_keys=True).encode()).hexdigest()
    lock_editing_budget(db, record.workspace_id)
    prior = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == record.workspace_id,
            StudioGenerationJob.job_type == "external_call",
            StudioGenerationJob.idempotency_key == key,
        )
    )
    if prior:
        if prior.payload_hash != digest:
            raise ValueError("idempotency_payload_conflict")
        return out(prior)
    row, adapter = provider(db, record.workspace_id, request.connection_id)
    videos, speech = adapter.models()
    model = next((m for m in (videos if request.kind == "video" else speech) if m["id"] == request.model), None)
    if not model:
        raise ValueError("openrouter_media_model_unavailable")
    if request.kind == "speech" and request.voice not in model.get("supported_voices", []):
        raise ValueError("openrouter_media_voice_unsupported")
    amount = estimate(request, model)
    # Serialize reservations for the production and retain unknown provider outcomes.
    previous = list(
        db.scalars(
            select(StudioGenerationJob).where(
                StudioGenerationJob.workspace_id == record.workspace_id, StudioGenerationJob.job_type == "external_call"
            )
        )
    )
    production = [j for j in previous if j.request_payload.get("productionId") == request.production_id]
    ceiling = min([request.max_cost_usd] + [j.request_payload["maxCostUsd"] for j in production])
    if sum(committed(j) for j in production) + amount > ceiling + 1e-9:
        raise ValueError("openrouter_media_production_budget_exceeded")
    pending = sum(
        committed(j) for j in previous if (j.result_payload or {}).get("submissionOutcome") in {"unknown", "pending"}
    )
    if pending + amount > adapter.balance() + 1e-9:
        raise ValueError("openrouter_media_insufficient_balance")
    job = StudioGenerationJob(
        id=str(uuid4()),
        workspace_id=record.workspace_id,
        requested_by=user.id,
        document_id=record.id,
        job_type="external_call",
        provider="openrouter.media",
        status="running",
        progress=1,
        idempotency_key=key,
        payload_hash=digest,
        correlation_id="openrouter-media:" + request.production_id,
        request_payload={
            **payload,
            "llmConnectionId": row.id,
            "billingScope": billing_scope(user, record.workspace_id, db),
        },
        result_payload={"estimatedCostUsd": amount},
        max_attempts=1,
        started_at=datetime.now(UTC),
    )
    db.add(job)
    try:
        reserve_monthly(db, job, amount, get_settings())
        job.result_payload = {**job.result_payload, "submissionStarted": True, "submissionOutcome": "unknown"}
        db.commit()  # The POST must never precede durable submission intent.
    except IntegrityError:
        db.rollback()
        raise ValueError("openrouter_media_concurrent_request") from None
    try:
        if request.kind == "video":
            response = adapter.request(
                "POST",
                "/videos",
                {
                    "model": request.model,
                    "prompt": request.prompt,
                    "duration": request.duration_seconds,
                    "resolution": request.resolution,
                    "aspect_ratio": request.aspect_ratio,
                    "generate_audio": request.generate_audio,
                },
            )
            operation = response.get("id")
            adapter.job_path(operation)
            job.result_payload = {
                **job.result_payload,
                "providerOperationId": operation,
                "submissionOutcome": "pending",
            }
            db.commit()
        else:
            data, generation = adapter.request(
                "POST",
                "/audio/speech",
                {"model": request.model, "input": request.text, "voice": request.voice, "response_format": "mp3"},
                binary=True,
            )
            job.result_payload = {
                **job.result_payload,
                "generationId": generation,
                "submissionOutcome": "response_received",
            }
            db.commit()
            finish(db, record, job, data, "audio/mpeg", ".mp3")
    except Exception as exc:
        db.rollback()
        db.refresh(job)
        job.status = "failed"
        job.error_code = str(exc)[:120] if isinstance(exc, ValueError) else "openrouter_media_outcome_unknown"
        job.error_message = job.error_code
        # A known HTTP rejection did not create work; unknown submission remains held.
        if job.error_code.startswith("openrouter_media_http_"):
            job.result_payload = {**job.result_payload, "submissionOutcome": "rejected", "preflightFailure": True}
        db.commit()
        raise ValueError(job.error_code) from exc
    return out(job)


def finish(db, record, job, data, mime, suffix):
    if not data:
        raise ValueError("openrouter_media_empty_output")
    with tempfile.TemporaryDirectory(prefix="clicko-openrouter-") as directory:
        path = Path(directory) / ("generated" + suffix)
        path.write_bytes(data)
        from ...providers.studios.timeline_ffmpeg import probe

        info = probe(path)
        kind = "video" if suffix == ".mp4" else "audio"
        if not any(s.get("codec_type") == kind for s in info.get("streams", [])):
            raise ValueError("openrouter_media_stream_missing")
        # Lock before attaching to avoid lost updates when multiple scenes complete.
        lock_editing_budget(db, record.workspace_id)
        db.refresh(record, with_for_update=True)
        asset, storage, storage_key = write_asset(
            db,
            record,
            path,
            suffix=suffix,
            media_type=mime,
            asset_type=kind,
            title=f"{record.title} · IA {kind}",
            metadata={
                "provider": "openrouter",
                "model": job.request_payload["model"],
                "generationJobId": job.id,
                "providerOperationId": (job.result_payload or {}).get("providerOperationId"),
                "generatedByAI": True,
                "durationSeconds": float(info["format"]["duration"]),
            },
        )
        try:
            contract = record_to_contract(record)
            ref = AssetReferenceV1(
                id=asset.id,
                media_type=mime,
                checksum=asset.checksum_sha256,
                origin="workspace",
                rights_status="unknown",
                provenance={"source": "OpenRouter AI generation", "jobId": job.id},
            )
            persist_contract(
                record,
                contract.model_copy(update={"assets": [*contract.assets, ref], "revision": contract.revision + 1}),
            )
            job.result_payload = {
                **job.result_payload,
                "assetId": asset.id,
                "downloadUrl": f"/api/v1/assets/{asset.id}/content",
                "submissionOutcome": "completed",
                "durationSeconds": float(info["format"]["duration"]),
            }
            job.status, job.progress, job.finished_at = "succeeded", 100, datetime.now(UTC)
            db.commit()
        except Exception:
            db.rollback()
            storage.delete(storage_key)
            raise


def poll(db, record, job):
    if job.document_id != record.id or job.provider != "openrouter.media":
        raise ValueError("openrouter_media_job_not_found")
    state = job.result_payload or {}
    if job.status == "succeeded" or not state.get("providerOperationId"):
        return out(job)
    _, adapter = provider(db, record.workspace_id, job.request_payload["connectionId"])
    operation = adapter.job_path(state["providerOperationId"])
    response = adapter.request("GET", operation)
    if response.get("status") == "failed":
        job.status, job.error_code = "failed", "openrouter_media_generation_failed"
        job.result_payload = {
            **state,
            "submissionOutcome": "failed",
            "providerReportedCostUsd": response.get("usage", {}).get("cost"),
        }
        db.commit()
    elif response.get("status") == "completed":
        data, _ = adapter.request("GET", operation + "/content", binary=True)
        # Polling may be retried but must not create duplicate library assets.
        lock_editing_budget(db, record.workspace_id)
        db.refresh(job, with_for_update=True)
        if job.status != "succeeded":
            job.result_payload = {
                **job.result_payload,
                "providerReportedCostUsd": response.get("usage", {}).get("cost"),
            }
            finish(db, record, job, data, "video/mp4", ".mp4")
    return out(job)
