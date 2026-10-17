from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ...domain.studios.contracts import (
    SpeechProvenanceV1,
    SpeechSynthesisRequestV1,
    SpeechSynthesisResultV1,
    VoiceCloneReferenceV1,
)
from ...domain.studios.speech_assets import (
    ChatterboxModelAssetManifestV1,
    OpenVoiceModelAssetManifestV1,
    chatterbox_model_asset_manifest_digest,
    openvoice_model_asset_manifest_digest,
    verify_chatterbox_model_assets,
    verify_openvoice_model_assets,
)
from ...services.object_storage import sha256_file

SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
MAX_RESULT_BYTES = 64 * 1024
PipelineId = Literal[
    "chatterbox.multilingual.from-local.v1",
    "clicko.chatterbox.pt-br-from-local.v1",
    "clicko.kokoro-openvoice-v2.pt-br.v1",
]
AssetVerifier = Callable[[], str]


@dataclass(frozen=True)
class VoiceCloneSidecarConfig:
    provider_name: str
    provider_version: str
    pipeline_contract: PipelineId
    source_revision: str
    model_digest_sha256: str
    asset_manifest_digest_sha256: str
    worker_manifest_digest_sha256: str
    worker_image_digest: str
    command: tuple[str, ...]
    gpu_hourly_cost_usd: float
    timeout_seconds: float = 3_600
    watermark_required: bool = True

    def __post_init__(self) -> None:
        if not self.provider_name.startswith("candidate."):
            raise ValueError("voice_clone_candidate_provider_name_required")
        if len(self.source_revision) < 7:
            raise ValueError("voice_clone_source_revision_required")
        digests = (
            self.model_digest_sha256,
            self.asset_manifest_digest_sha256,
            self.worker_manifest_digest_sha256,
        )
        if any(not SHA256.fullmatch(value) for value in digests):
            raise ValueError("voice_clone_sidecar_sha256_config_invalid")
        if not IMAGE_DIGEST.fullmatch(self.worker_image_digest):
            raise ValueError("voice_clone_sidecar_image_digest_invalid")
        if not self.command or not Path(self.command[0]).is_absolute():
            raise ValueError("voice_clone_sidecar_absolute_command_required")
        if not math.isfinite(self.timeout_seconds) or not 1 <= self.timeout_seconds <= 7_200:
            raise ValueError("voice_clone_sidecar_timeout_invalid")
        if not math.isfinite(self.gpu_hourly_cost_usd) or self.gpu_hourly_cost_usd <= 0:
            raise ValueError("voice_clone_sidecar_gpu_cost_required")


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class AuditedVoiceCloneSidecarProvider:
    """Offline candidate adapter; construction never registers or promotes it."""

    def __init__(self, config: VoiceCloneSidecarConfig, verify_assets: AssetVerifier) -> None:
        self.config = config
        self.name = config.provider_name
        self.version = config.provider_version
        self._verify_assets = verify_assets

    def _preflight(
        self,
        request: SpeechSynthesisRequestV1,
        reference: VoiceCloneReferenceV1,
        reference_path: Path,
    ) -> None:
        if request.locale != "pt-BR":
            raise ValueError("voice_clone_sidecar_only_supports_pt_br")
        if request.audio_format != "wav" or request.sample_rate != 24_000:
            raise ValueError("voice_clone_sidecar_requires_wav_24khz")
        if request.voice_key != reference.voice_version_id:
            raise ValueError("voice_clone_sidecar_voice_version_mismatch")
        if not reference_path.is_file() or reference_path.is_symlink():
            raise ValueError("voice_clone_sidecar_reference_file_required")
        if sha256_file(reference_path).lower() != reference.normalized_checksum_sha256.lower():
            raise ValueError("voice_clone_sidecar_reference_checksum_mismatch")
        if self._verify_assets().lower() != self.config.asset_manifest_digest_sha256.lower():
            raise ValueError("voice_clone_sidecar_asset_manifest_mismatch")

    def clone(
        self,
        request: SpeechSynthesisRequestV1,
        reference: VoiceCloneReferenceV1,
        reference_path: Path,
        destination: Path,
        progress: Callable[[int], None],
        is_cancelled: Callable[[], bool],
    ) -> SpeechSynthesisResultV1:
        self._preflight(request, reference, reference_path)
        if is_cancelled():
            raise InterruptedError("voice_clone_cancelled_before_inference")
        destination.parent.mkdir(parents=True, exist_ok=True)
        request_path = destination.parent / "voice-clone-sidecar-request.json"
        result_path = destination.parent / "voice-clone-sidecar-result.json"
        descriptor = {
            "schemaVersion": "clicko.voice-clone-sidecar-request.v1",
            "pipelineContract": self.config.pipeline_contract,
            "speech": request.model_dump(by_alias=True, mode="json"),
            "reference": reference.model_dump(by_alias=True, mode="json"),
        }
        request_path.write_text(
            json.dumps(descriptor, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )
        command = [
            *self.config.command,
            "--request",
            str(request_path),
            "--reference",
            str(reference_path),
            "--output",
            str(destination),
            "--result",
            str(result_path),
        ]
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        started = time.perf_counter()
        progress(5)
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
                start_new_session=os.name != "nt",
            )
            while process.poll() is None:
                if is_cancelled():
                    _stop_process(process)
                    raise InterruptedError("voice_clone_cancelled_during_inference")
                if time.perf_counter() - started > self.config.timeout_seconds:
                    _stop_process(process)
                    raise TimeoutError("voice_clone_sidecar_timeout")
                time.sleep(0.05)
            if process.returncode != 0:
                raise RuntimeError("voice_clone_sidecar_failed")
            progress(90)
            if not result_path.is_file() or result_path.stat().st_size > MAX_RESULT_BYTES:
                raise ValueError("voice_clone_sidecar_result_missing_or_too_large")
            sidecar_result = json.loads(result_path.read_text(encoding="utf-8"))
            if (
                sidecar_result.get("schemaVersion")
                != "clicko.voice-clone-sidecar-result.v1"
                or sidecar_result.get("pipelineContract") != self.config.pipeline_contract
                or (
                    self.config.watermark_required
                    and sidecar_result.get("watermarkApplied") is not True
                )
            ):
                raise ValueError("voice_clone_sidecar_result_binding_mismatch")
            if not destination.is_file() or destination.is_symlink():
                raise ValueError("voice_clone_sidecar_output_missing")
            with wave.open(str(destination), "rb") as output:
                if (
                    output.getnchannels() != 1
                    or output.getsampwidth() != 2
                    or output.getframerate() != request.sample_rate
                    or output.getnframes() <= 0
                ):
                    raise ValueError("voice_clone_sidecar_output_format_mismatch")
                duration_ms = max(
                    1,
                    math.ceil(output.getnframes() * 1_000 / output.getframerate()),
                )
            elapsed_seconds = max(time.perf_counter() - started, 1e-9)
            progress(100)
            return SpeechSynthesisResultV1(
                provider=self.name,
                provider_version=self.version,
                audio_format="wav",
                sample_rate=request.sample_rate,
                duration_ms=duration_ms,
                artifact_checksum_sha256=sha256_file(destination),
                provenance=SpeechProvenanceV1(
                    source_revision=self.config.source_revision,
                    model_digest_sha256=self.config.model_digest_sha256,
                    worker_manifest_digest_sha256=self.config.worker_manifest_digest_sha256,
                    worker_image_digest=self.config.worker_image_digest,
                    provenance_mode="clicko-auditable-offline-sidecar-v1",
                    voice_version_id=reference.voice_version_id,
                    consent_grant_id=reference.consent_grant_id,
                    voice_reference_checksum_sha256=reference.normalized_checksum_sha256,
                ),
                metrics={
                    "activeComputeSeconds": elapsed_seconds,
                    "directCostUsd": elapsed_seconds
                    * self.config.gpu_hourly_cost_usd
                    / 3_600,
                },
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            request_path.unlink(missing_ok=True)
            result_path.unlink(missing_ok=True)


def create_chatterbox_sidecar_provider(
    *,
    candidate_id: Literal["chatterbox-multilingual-v3", "chatterbox-pt-br"],
    manifest_path: Path,
    asset_root: Path,
    worker_manifest_digest_sha256: str,
    worker_image_digest: str,
    command: tuple[str, ...],
    gpu_hourly_cost_usd: float,
    timeout_seconds: float = 3_600,
) -> AuditedVoiceCloneSidecarProvider:
    manifest = ChatterboxModelAssetManifestV1.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    variant = next(item for item in manifest.variants if item.candidate_id == candidate_id)
    manifest_digest = chatterbox_model_asset_manifest_digest(manifest)
    return AuditedVoiceCloneSidecarProvider(
        VoiceCloneSidecarConfig(
            provider_name=f"candidate.{candidate_id}",
            provider_version=f"0.1.0+{manifest.chatterbox_code_revision[:12]}",
            pipeline_contract=variant.loader_contract,
            source_revision=manifest.chatterbox_code_revision,
            model_digest_sha256=manifest_digest,
            asset_manifest_digest_sha256=manifest_digest,
            worker_manifest_digest_sha256=worker_manifest_digest_sha256,
            worker_image_digest=worker_image_digest,
            command=command,
            gpu_hourly_cost_usd=gpu_hourly_cost_usd,
            timeout_seconds=timeout_seconds,
        ),
        lambda: verify_chatterbox_model_assets(manifest, asset_root),
    )


def create_openvoice_sidecar_provider(
    *,
    manifest_path: Path,
    asset_root: Path,
    worker_manifest_digest_sha256: str,
    worker_image_digest: str,
    command: tuple[str, ...],
    gpu_hourly_cost_usd: float,
    timeout_seconds: float = 3_600,
) -> AuditedVoiceCloneSidecarProvider:
    manifest = OpenVoiceModelAssetManifestV1.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    manifest_digest = openvoice_model_asset_manifest_digest(manifest)
    return AuditedVoiceCloneSidecarProvider(
        VoiceCloneSidecarConfig(
            provider_name="candidate.kokoro-openvoice-v2",
            provider_version=f"0.1.0+{manifest.openvoice_code_revision[:12]}",
            pipeline_contract=manifest.pipeline_contract,
            source_revision=manifest.openvoice_code_revision,
            model_digest_sha256=manifest_digest,
            asset_manifest_digest_sha256=manifest_digest,
            worker_manifest_digest_sha256=worker_manifest_digest_sha256,
            worker_image_digest=worker_image_digest,
            command=command,
            gpu_hourly_cost_usd=gpu_hourly_cost_usd,
            timeout_seconds=timeout_seconds,
        ),
        lambda: verify_openvoice_model_assets(manifest, asset_root),
    )
