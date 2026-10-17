from __future__ import annotations

import hashlib
import wave
from dataclasses import dataclass

import numpy as np
import pytest

from app.domain.studios.contracts import SpeechSynthesisRequestV1
from app.providers.studios.kokoro_stock import KokoroStockConfig, KokoroStockVoiceProvider


@dataclass
class FakeResult:
    audio: np.ndarray | None


class FakePipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, float, object]] = []

    def __call__(self, text, *, voice, speed, split_pattern):
        self.calls.append((text, voice, speed, split_pattern))
        yield FakeResult(np.zeros(2_400, dtype=np.float32))


def _config() -> KokoroStockConfig:
    return KokoroStockConfig(
        source_revision="dfb907a02bba8152ca444717ca5d78747ccb4bec",
        model_revision="f3ff3571791e39611d31c381e3a41a3af07b4987",
        model_digest_sha256="1" * 64,
        worker_manifest_digest_sha256="2" * 64,
        worker_image_digest=f"sha256:{'3' * 64}",
        cpu_hourly_cost_usd=0.08,
    )


def _request(text: str, *, voice: str = "pf_dora") -> SpeechSynthesisRequestV1:
    return SpeechSynthesisRequestV1(
        locale="pt-BR",
        text=text,
        script_digest_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        voice_key=voice,
    )


def _attest_offline(monkeypatch, config: KokoroStockConfig) -> None:
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("CLICKO_KOKORO_MODEL_REVISION", config.model_revision)
    monkeypatch.setenv("CLICKO_KOKORO_MODEL_DIGEST_SHA256", config.model_digest_sha256)


def test_kokoro_adapter_writes_bound_wav_and_chunks_without_losing_script(
    tmp_path, monkeypatch
):
    config = _config()
    _attest_offline(monkeypatch, config)
    pipeline = FakePipeline()
    provider = KokoroStockVoiceProvider(config, pipeline_factory=lambda _config: pipeline)
    text = ("Café Aurora prepara uma experiência real para a campanha. " * 20).strip()
    progress: list[int] = []
    destination = tmp_path / "speech.wav"

    result = provider.synthesize(_request(text), destination, progress.append, lambda: False)

    assert len(pipeline.calls) > 1
    assert " ".join(call[0] for call in pipeline.calls) == text
    assert all(len(call[0]) <= config.max_chunk_characters for call in pipeline.calls)
    assert all(call[1:] == ("pf_dora", 1.0, None) for call in pipeline.calls)
    assert progress[-1] == 100
    with wave.open(str(destination), "rb") as source:
        assert source.getframerate() == 24_000
        assert source.getnchannels() == 1
        assert source.getsampwidth() == 2
        assert source.getnframes() == len(pipeline.calls) * 2_400
    assert result.duration_ms == len(pipeline.calls) * 100
    assert result.artifact_checksum_sha256 == hashlib.sha256(destination.read_bytes()).hexdigest()
    assert result.provenance.model_digest_sha256 == config.model_digest_sha256
    assert result.metrics["directCostUsd"] > 0


def test_kokoro_adapter_fails_closed_for_unpinned_runtime_and_unknown_voice(
    tmp_path, monkeypatch
):
    config = _config()
    pipeline = FakePipeline()
    provider = KokoroStockVoiceProvider(config, pipeline_factory=lambda _config: pipeline)

    with pytest.raises(ValueError, match="kokoro_huggingface_offline_required"):
        provider.synthesize(_request("Teste curto."), tmp_path / "offline.wav", lambda _: None, lambda: False)

    _attest_offline(monkeypatch, config)
    with pytest.raises(ValueError, match="kokoro_stock_voice_not_allowlisted"):
        provider.synthesize(
            _request("Teste curto.", voice="af_heart"),
            tmp_path / "voice.wav",
            lambda _: None,
            lambda: False,
        )
    assert pipeline.calls == []


def test_kokoro_adapter_removes_partial_audio_when_cancelled(tmp_path, monkeypatch):
    config = _config()
    _attest_offline(monkeypatch, config)
    pipeline = FakePipeline()
    provider = KokoroStockVoiceProvider(config, pipeline_factory=lambda _config: pipeline)
    checks = iter([False, False, True])
    destination = tmp_path / "cancelled.wav"

    with pytest.raises(InterruptedError, match="kokoro_synthesis_cancelled"):
        provider.synthesize(
            _request("Primeiro trecho. " * 40),
            destination,
            lambda _: None,
            lambda: next(checks, True),
        )

    assert not destination.exists()
