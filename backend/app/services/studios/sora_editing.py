"""Durable Sora material generation for one short, budgeted pilot clip."""

from __future__ import annotations

import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from ...config import get_settings
from ...domain.studios.editing_resources import EditingAIRequestV1, ResourceMetadataV1
from ...domain.studios.generative_video import GenerativeVideoOperationV1, GenerativeVideoRequestV1
from ...models import User
from ...providers.studios.contextual_render import ContextualFFmpegProvider
from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ...providers.studios.openai_video import OpenAISoraVideoProvider
from .editing_resources import store_resource
from .gemini_editing import reserve_test_request, validate_binding


def execute_sora_editing(db, job, progress, is_cancelled):
    settings = get_settings()
    if job.request_payload.get("environment") != settings.environment:
        raise ValueError("editing_environment_mismatch")
    request = EditingAIRequestV1.model_validate(job.request_payload["input"])
    if request.operation != "generate_video" or request.duration_seconds != 4:
        raise ValueError("sora_request_limits_exceeded")
    validate_binding(db, job)
    provider = OpenAISoraVideoProvider(settings)
    started = time.monotonic()
    state = dict(job.result_payload or {})
    generated = GenerativeVideoRequestV1(
        request_id=job.id,
        model="sora-2",
        prompt=request.prompt,
        duration_seconds=4,
        resolution=job.request_payload["outputRatio"],
        maximum_cost_usd=0.40,
    )
    try:
        operation_payload = state.get("providerOperation")
        if operation_payload:
            operation = GenerativeVideoOperationV1.model_validate(operation_payload)
        else:
            if state.get("submissionStarted"):
                raise ValueError("editing_submission_requires_reconciliation")
            provider.preflight(generated)
            reserve_test_request(db, job, generated.duration_seconds)
            state = {
                **(job.result_payload or {}),
                "submissionStarted": True,
                "submittedAt": datetime.now(UTC).isoformat(),
                "model": generated.model,
                "priceVersion": job.request_payload["priceVersion"],
            }
            job.result_payload = state
            db.commit()
            operation = provider.start(generated)
            state["providerOperation"] = operation.model_dump(mode="json", by_alias=True)
            state["providerOperationId"] = operation.provider_operation_id
            job.result_payload = state
            db.commit()
        progress(20)
        operation = provider.wait(operation, is_cancelled=is_cancelled)
        state["providerOperation"] = operation.model_dump(mode="json", by_alias=True)
        job.result_payload = state
        db.commit()
        if operation.status == "cancelled":
            return {**state, "cancelled": True}
        if operation.status != "completed":
            raise ValueError(operation.failure_code or "sora_generation_failed")
        with tempfile.TemporaryDirectory(prefix="res-sora-") as name:
            directory = Path(name)
            raw = directory / "raw.mp4"
            provider.download(generated, operation, raw)
            silent = directory / "silent.mp4"
            ContextualFFmpegProvider(settings.ffmpeg_path, settings.ffmpeg_timeout_seconds)._run(
                ["-y", "-i", str(raw), "-map", "0:v:0", "-an", "-c:v", "copy", str(silent)],
                directory,
                is_cancelled,
            )
            probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                silent, asset_id="generated", checksum_sha256=None
            )
            duration = (probe.duration_microseconds or 0) / 1e6
            if abs(duration - 4) > 0.20:
                raise ValueError("editing_generated_duration_mismatch")
            validate_binding(db, job)
            user = db.get(User, job.requested_by)
            asset = store_resource(
                db,
                job.workspace_id,
                "Material gerado — " + request.prompt[:100],
                silent,
                ResourceMetadataV1(
                    kind="video",
                    description=request.prompt,
                    usage_evidence="Original generated candidate; requires material inspection",
                    official=False,
                ),
                user.id,
                provenance={
                    "derivation": {"provider": job.provider, "model": generated.model},
                    "generationJobId": job.id,
                    "sourceAssetBindings": job.request_payload["sourceAssets"],
                    "visualReview": "pending",
                    "syntheticMedia": True,
                    "canonicalAudioRemoved": True,
                },
            )
        result = {
            **state,
            "assetId": asset.id,
            "checksumSha256": asset.checksum_sha256,
            "status": "candidate_pending_review",
            "testReservationUsd": state.get("testReservationUsd", 0.40),
            "measuredCostUsd": operation.estimated_cost_usd,
            "outputVideoSeconds": 4,
            "originalAudioPreserved": False,
            "processingSeconds": round(time.monotonic() - started, 3),
            "verification": {
                "technical": "passed",
                "visualContinuity": "pending",
                "humanApproved": False,
                "issues": ["Generated clip requires pixel inspection before timeline use"],
            },
        }
        job.result_payload = result
        db.commit()
        return result
    finally:
        provider.close()
