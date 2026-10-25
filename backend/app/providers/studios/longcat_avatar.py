from __future__ import annotations

import hashlib
import json
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from ...config import get_settings
from ...domain.studios.avatar_generation import longcat_segment_timing
from ...domain.studios.contracts import (
    AvatarVideoEncodeResultV1,
    AvatarVideoRequest,
    AvatarVideoRequestV2,
    CreativeDocumentV1,
)
from ...services.object_storage import sha256_file

logger = logging.getLogger(__name__)


class LongCatAvatarProvider:
    """Authenticated transport for a separately qualified Linux/CUDA worker."""

    name = "local.longcat-avatar-1.5"
    version = "6b3f4b8582a8bc3f20f795735f5383716c4ba794"

    def __init__(self, base_url: str, token: str):
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("longcat_avatar_loopback_required")
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}

    @contextmanager
    def _cleanup_execution(self, client: httpx.Client, execution_id: str):
        # Do not upload private media to an older worker without this lifecycle.
        response = client.get(f"{self.base_url}/api/v1/lifecycle", headers=self.headers)
        response.raise_for_status()
        policy = response.json()
        if not isinstance(policy, dict) or (
            policy.get("schemaVersion") != "studio.longcat-lifecycle.v1"
            or policy.get("authenticatedDeletion") is not True
            or policy.get("removeInputsAfterExecution") is not True
        ):
            raise ValueError("longcat_worker_lifecycle_required")
        retention = policy.get("retention")
        limits = {
            "artifactTtlSeconds": 86400,
            "executionTtlSeconds": 86400,
            "tombstoneTtlSeconds": 604800,
            "sweepIntervalSeconds": 60,
        }
        if not isinstance(retention, dict) or any(
            type(retention.get(key)) is not int or not 1 <= retention[key] <= maximum for key, maximum in limits.items()
        ):
            raise ValueError("longcat_worker_retention_invalid")
        cleanup = {"acknowledged": False, "completed": False}
        try:
            yield cleanup
        finally:
            try:
                response = client.delete(f"{self.base_url}/api/v1/executions/{execution_id}", headers=self.headers)
                receipt = response.json()
                if not isinstance(receipt, dict):
                    raise ValueError("longcat_cleanup_receipt_invalid")
                detail = receipt.get("detail")
                if (
                    response.status_code == 404
                    and isinstance(detail, dict)
                    and detail.get("code") == "execution_not_found"
                ):
                    cleanup.update(acknowledged=True, completed=True)
                else:
                    response.raise_for_status()
                    if receipt.get("executionId") == execution_id:
                        cleanup["completed"] = receipt.get("status") == "deleted"
                        cleanup["acknowledged"] = cleanup["completed"] or receipt.get("deletionRequested") is True
                if not cleanup["acknowledged"]:
                    logger.warning("LONGCAT_WORKER_CLEANUP_UNCONFIRMED")
            except (httpx.HTTPError, ValueError):
                # The worker's bounded retention remains the fallback if the
                # connection fails after it accepted private inputs. A cleanup
                # outage must not trigger another expensive inference attempt.
                logger.warning("LONGCAT_WORKER_CLEANUP_UNCONFIRMED")

    def render(
        self,
        document: CreativeDocumentV1,
        request: AvatarVideoRequest,
        identity_samples: list[Path],
        driving_audio: Path,
        destination: Path,
        progress,
        is_cancelled,
    ) -> AvatarVideoEncodeResultV1:
        if not isinstance(request, AvatarVideoRequestV2):
            raise ValueError("longcat_avatar_request_v2_required")
        if len(identity_samples) != 1:
            raise ValueError("longcat_avatar_single_reference_required")
        if is_cancelled():
            raise InterruptedError("cancelled")
        avatar_request = request.model_dump(by_alias=True, mode="json")
        request_digest = hashlib.sha256(
            json.dumps(avatar_request, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        # Backend job idempotency is checked before render(). Each actual render
        # attempt needs a fresh worker lease because consumed media is deleted.
        execution_id = hashlib.sha256(f"{document.id}:{request_digest}".encode()).hexdigest()[:40] + "-" + uuid4().hex
        timing = longcat_segment_timing(request.driving_audio_duration_ms)
        payload = {
            "execution_id": execution_id,
            "profile_id": request.profile_id,
            "request_digest_sha256": request_digest,
            "avatar_request": avatar_request,
            "reference_image_checksum_sha256": request.reference_image_checksum_sha256.lower(),
            "driving_audio_checksum_sha256": request.driving_audio_checksum_sha256.lower(),
            "segment_count": timing.segment_count,
            "produced_frames": timing.produced_frames,
            "trim_tail_ms": timing.trim_tail_ms,
        }

        def verified_receipt(receipt):
            if (
                receipt.get("executionId") != execution_id
                or receipt.get("requestDigestSha256") != request_digest
                or receipt.get("profileId") != request.profile_id
            ):
                raise ValueError("longcat_avatar_receipt_binding_mismatch")
            return receipt

        with (
            httpx.Client(timeout=httpx.Timeout(30, read=120)) as client,
            self._cleanup_execution(client, execution_id) as cleanup,
        ):
            if is_cancelled():
                raise InterruptedError("cancelled")
            with identity_samples[0].open("rb") as image_stream, driving_audio.open("rb") as audio_stream:
                response = client.post(
                    self.base_url + "/api/v1/executions",
                    headers=self.headers,
                    data={"metadata": json.dumps(payload, sort_keys=True)},
                    files={
                        "reference_image": ("reference-image", image_stream, "application/octet-stream"),
                        "driving_audio": ("driving-audio", audio_stream, "application/octet-stream"),
                    },
                )
            if response.status_code == 409:
                detail = response.json().get("detail", {})
                raise ValueError(str(detail.get("status") or detail.get("code") or "longcat_unavailable"))
            response.raise_for_status()
            receipt = verified_receipt(response.json())
            progress(20)
            for _ in range(720):
                if is_cancelled():
                    client.post(
                        f"{self.base_url}/api/v1/executions/{execution_id}/cancel",
                        headers=self.headers,
                    )
                    raise InterruptedError("cancelled")
                if receipt.get("status") not in {"queued", "running"}:
                    break
                time.sleep(10)
                receipt_response = client.get(f"{self.base_url}/api/v1/executions/{execution_id}", headers=self.headers)
                receipt_response.raise_for_status()
                receipt = verified_receipt(receipt_response.json())
                progress(min(89, max(20, int(receipt.get("progress", 20)))))
            if receipt.get("status") in {"queued", "running", "cancel_requested"}:
                client.post(f"{self.base_url}/api/v1/executions/{execution_id}/cancel", headers=self.headers)
                raise ValueError("longcat_avatar_timeout")
            if receipt.get("status") != "succeeded":
                raise ValueError(f"longcat_avatar_{receipt.get('status', 'timeout')}")
            if abs(int(receipt["durationMs"]) - request.driving_audio_duration_ms) > 80:
                raise ValueError("longcat_avatar_duration_mismatch")
            try:
                with client.stream(
                    "GET", f"{self.base_url}/api/v1/executions/{execution_id}/artifact", headers=self.headers
                ) as artifact:
                    artifact.raise_for_status()
                    with destination.open("wb") as stream:
                        for chunk in artifact.iter_bytes():
                            if is_cancelled():
                                raise InterruptedError("cancelled")
                            stream.write(chunk)
            except Exception:
                destination.unlink(missing_ok=True)
                raise
        checksum = sha256_file(destination)
        if checksum != receipt.get("artifactChecksumSha256"):
            destination.unlink(missing_ok=True)
            raise ValueError("longcat_avatar_artifact_checksum_mismatch")
        progress(90)
        return AvatarVideoEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=request.width,
            height=request.height,
            fps=request.fps,
            duration_ms=int(receipt["durationMs"]),
            artifact_checksum_sha256=checksum,
            synthetic_content_disclosed=True,
            metrics={
                "segments": float(receipt.get("segments", timing.segment_count)),
                "segmentFrames": 93.0,
                "overlapFrames": 13.0,
                "producedFrames": float(timing.produced_frames),
                "trimTailMs": float(timing.trim_tail_ms),
                "workerCleanupAcknowledged": float(cleanup["acknowledged"]),
                "workerCleanupCompleted": float(cleanup["completed"]),
            },
        )


def configured_longcat_avatar_provider() -> LongCatAvatarProvider | None:
    settings = get_settings()
    if not settings.studio_longcat_avatar_enabled or not settings.studio_longcat_avatar_token:
        return None
    return LongCatAvatarProvider(
        settings.studio_longcat_avatar_url,
        settings.studio_longcat_avatar_token.get_secret_value(),
    )
