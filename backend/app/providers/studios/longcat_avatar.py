from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlparse

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
        execution_id = hashlib.sha256(
            f"{document.id}:{request.scene_id}:{request.requirement_id}:"
            f"{request.reference_image_checksum_sha256}:{request.driving_audio_checksum_sha256}:"
            f"{request.profile_id}:{request.seed}".encode()
        ).hexdigest()[:40]
        timing = longcat_segment_timing(request.driving_audio_duration_ms)
        payload = {
            "execution_id": execution_id,
            "profile_id": request.profile_id,
            "request_digest_sha256": hashlib.sha256(
                json.dumps(
                    request.model_dump(by_alias=True, mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "reference_image_checksum_sha256": request.reference_image_checksum_sha256.lower(),
            "driving_audio_checksum_sha256": request.driving_audio_checksum_sha256.lower(),
            "segment_count": timing.segment_count,
            "produced_frames": timing.produced_frames,
            "trim_tail_ms": timing.trim_tail_ms,
        }
        with httpx.Client(timeout=httpx.Timeout(30, read=120)) as client:
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
            receipt = response.json()
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
                receipt_response = client.get(
                    f"{self.base_url}/api/v1/executions/{execution_id}", headers=self.headers
                )
                receipt_response.raise_for_status()
                receipt = receipt_response.json()
            if receipt.get("status") != "succeeded":
                raise ValueError(f"longcat_avatar_{receipt.get('status', 'timeout')}")
            artifact = client.get(
                f"{self.base_url}/api/v1/executions/{execution_id}/artifact",
                headers=self.headers,
            )
            artifact.raise_for_status()
            destination.write_bytes(artifact.content)
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
