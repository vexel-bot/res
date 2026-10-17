from __future__ import annotations

import hashlib
import math
import os
import re
import textwrap
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...domain.studios.contracts import (
    SpeechProvenanceV1,
    SpeechSynthesisRequestV1,
    SpeechSynthesisResultV1,
)

KOKORO_PT_BR_VOICES = frozenset({"pf_dora", "pm_alex", "pm_santa"})
KOKORO_SAMPLE_RATE = 24_000
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class KokoroStockConfig:
    source_revision: str
    model_revision: str
    model_digest_sha256: str
    worker_manifest_digest_sha256: str
    worker_image_digest: str
    cpu_hourly_cost_usd: float
    model_repo_id: str = "hexgrad/Kokoro-82M"
    allowed_voices: frozenset[str] = KOKORO_PT_BR_VOICES
    max_chunk_characters: int = 320

    def __post_init__(self) -> None:
        if len(self.source_revision) < 7 or len(self.model_revision) < 7:
            raise ValueError("kokoro_source_revisions_required")
        digests = (self.model_digest_sha256, self.worker_manifest_digest_sha256)
        if any(not _SHA256.fullmatch(value) for value in digests):
            raise ValueError("kokoro_sha256_config_invalid")
        if not _IMAGE_DIGEST.fullmatch(self.worker_image_digest):
            raise ValueError("kokoro_worker_image_digest_invalid")
        if not math.isfinite(self.cpu_hourly_cost_usd) or self.cpu_hourly_cost_usd <= 0:
            raise ValueError("kokoro_cpu_hourly_cost_required")
        if not self.allowed_voices or not self.allowed_voices.issubset(KOKORO_PT_BR_VOICES):
            raise ValueError("kokoro_pt_br_voice_allowlist_invalid")
        if not 80 <= self.max_chunk_characters <= 400:
            raise ValueError("kokoro_chunk_limit_invalid")


PipelineFactory = Callable[[KokoroStockConfig], Any]


def _default_pipeline_factory(config: KokoroStockConfig) -> Any:
    try:
        from kokoro import KPipeline
    except ImportError as error:  # pragma: no cover - exercised in the isolated worker image
        raise RuntimeError("kokoro_runtime_not_installed") from error
    return KPipeline(
        lang_code="p",
        repo_id=config.model_repo_id,
        device="cpu",
    )


def _normalized_chunks(text: str, limit: int) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        raise ValueError("kokoro_text_empty_after_normalization")
    sentences = re.split(r"(?<=[.!?…])\s+", normalized)
    units: list[str] = []
    for sentence in sentences:
        units.extend(
            textwrap.wrap(
                sentence,
                width=limit,
                break_long_words=True,
                break_on_hyphens=False,
                replace_whitespace=False,
                drop_whitespace=True,
            )
        )
    chunks: list[str] = []
    for unit in units:
        if chunks and len(chunks[-1]) + 1 + len(unit) <= limit:
            chunks[-1] = f"{chunks[-1]} {unit}"
        else:
            chunks.append(unit)
    if " ".join(chunks) != normalized:
        raise ValueError("kokoro_chunking_changed_script")
    return chunks


def _pcm16_bytes(audio: Any) -> tuple[bytes, int]:
    try:
        import numpy as np
    except ImportError as error:  # pragma: no cover - Kokoro itself requires numpy
        raise RuntimeError("kokoro_numpy_not_installed") from error
    if hasattr(audio, "detach"):
        audio = audio.detach()
    if hasattr(audio, "cpu"):
        audio = audio.cpu()
    if hasattr(audio, "numpy"):
        audio = audio.numpy()
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size == 0 or not np.isfinite(samples).all():
        raise ValueError("kokoro_audio_samples_invalid")
    encoded = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    return encoded, int(samples.size)


class KokoroStockVoiceProvider:
    """CPU-only, offline and allowlisted Kokoro adapter for stock pt-BR voices."""

    name = "kokoro-82m-stock"

    def __init__(
        self,
        config: KokoroStockConfig,
        *,
        pipeline_factory: PipelineFactory = _default_pipeline_factory,
    ) -> None:
        self.config = config
        self.version = (
            f"kokoro-{config.source_revision[:12]}+model-{config.model_revision[:12]}"
        )
        self._pipeline_factory = pipeline_factory
        self._pipeline: Any | None = None

    def _require_pinned_offline_runtime(self) -> None:
        if os.getenv("HF_HUB_OFFLINE") != "1":
            raise ValueError("kokoro_huggingface_offline_required")
        if os.getenv("CLICKO_KOKORO_MODEL_REVISION") != self.config.model_revision:
            raise ValueError("kokoro_model_revision_attestation_mismatch")
        expected_digest = os.getenv("CLICKO_KOKORO_MODEL_DIGEST_SHA256", "").lower()
        if expected_digest != self.config.model_digest_sha256.lower():
            raise ValueError("kokoro_model_digest_attestation_mismatch")

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            self._pipeline = self._pipeline_factory(self.config)
        return self._pipeline

    def synthesize(
        self,
        request: SpeechSynthesisRequestV1,
        destination: Path,
        progress: Callable[[int], None],
        is_cancelled: Callable[[], bool],
    ) -> SpeechSynthesisResultV1:
        self._require_pinned_offline_runtime()
        if request.locale != "pt-BR":
            raise ValueError("kokoro_stock_only_supports_pt_br")
        if request.voice_key not in self.config.allowed_voices:
            raise ValueError("kokoro_stock_voice_not_allowlisted")
        if request.audio_format != "wav" or request.sample_rate != KOKORO_SAMPLE_RATE:
            raise ValueError("kokoro_stock_requires_wav_24khz")
        if is_cancelled():
            raise InterruptedError("kokoro_synthesis_cancelled")

        chunks = _normalized_chunks(request.text, self.config.max_chunk_characters)
        pipeline = self._get_pipeline()
        destination.parent.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        total_samples = 0
        generated_parts = 0
        progress(5)
        try:
            with wave.open(str(destination), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(KOKORO_SAMPLE_RATE)
                for index, chunk in enumerate(chunks):
                    if is_cancelled():
                        raise InterruptedError("kokoro_synthesis_cancelled")
                    results = pipeline(
                        chunk,
                        voice=request.voice_key,
                        speed=request.speed,
                        split_pattern=None,
                    )
                    for result in results:
                        if is_cancelled():
                            raise InterruptedError("kokoro_synthesis_cancelled")
                        audio = getattr(result, "audio", None)
                        if audio is None:
                            continue
                        encoded, sample_count = _pcm16_bytes(audio)
                        output.writeframes(encoded)
                        total_samples += sample_count
                        generated_parts += 1
                    progress(5 + math.floor(90 * (index + 1) / len(chunks)))
            if total_samples <= 0 or generated_parts <= 0:
                raise ValueError("kokoro_synthesis_returned_no_audio")
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        elapsed_seconds = max(time.perf_counter() - started, 1e-9)
        duration_ms = max(1, math.ceil(total_samples * 1000 / KOKORO_SAMPLE_RATE))
        checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
        progress(100)
        return SpeechSynthesisResultV1(
            provider=self.name,
            provider_version=self.version,
            audio_format="wav",
            sample_rate=KOKORO_SAMPLE_RATE,
            duration_ms=duration_ms,
            artifact_checksum_sha256=checksum,
            provenance=SpeechProvenanceV1(
                source_revision=self.config.source_revision,
                model_digest_sha256=self.config.model_digest_sha256,
                worker_manifest_digest_sha256=self.config.worker_manifest_digest_sha256,
                worker_image_digest=self.config.worker_image_digest,
                provenance_mode="clicko-auditable-sidecar-v1",
            ),
            metrics={
                "activeComputeSeconds": elapsed_seconds,
                "chunkCount": float(len(chunks)),
                "directCostUsd": elapsed_seconds * self.config.cpu_hourly_cost_usd / 3600,
                "generatedPartCount": float(generated_parts),
            },
        )
