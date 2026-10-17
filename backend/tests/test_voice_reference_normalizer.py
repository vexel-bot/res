from __future__ import annotations

import wave
from pathlib import Path

import pytest

from app.config import get_settings
from app.providers.studios.voice_reference import FFmpegVoiceReferenceNormalizer
from app.services.object_storage import sha256_file


def _write_source(path: Path, *, seconds: int = 4) -> None:
    sample_rate = 48_000
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"\x00\x00\x00\x00" * sample_rate * seconds)


def test_ffmpeg_voice_reference_is_mono_24khz_and_checksum_bound(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.wav"
    destination = tmp_path / "normalized.wav"
    _write_source(source)
    settings = get_settings()
    normalizer = FFmpegVoiceReferenceNormalizer(
        settings.ffmpeg_path,
        settings.ffmpeg_timeout_seconds,
    )
    progress: list[int] = []

    reference = normalizer.normalize(
        source,
        destination,
        voice_version_id="voice-version-001",
        consent_grant_id="consent-001",
        source_asset_id="asset-001",
        source_checksum_sha256=sha256_file(source),
        progress=progress.append,
        is_cancelled=lambda: False,
    )

    with wave.open(str(destination), "rb") as normalized:
        assert normalized.getnchannels() == 1
        assert normalized.getsampwidth() == 2
        assert normalized.getframerate() == 24_000
    assert reference.duration_ms == 4_000
    assert reference.normalized_checksum_sha256 == sha256_file(destination)
    assert reference.retention_mode == "job-ephemeral"
    assert progress == [8, 15]


def test_voice_reference_normalizer_cancels_before_reading_source(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    normalizer = FFmpegVoiceReferenceNormalizer(
        settings.ffmpeg_path,
        settings.ffmpeg_timeout_seconds,
    )

    with pytest.raises(InterruptedError, match="normalization_cancelled"):
        normalizer.normalize(
            tmp_path / "missing.wav",
            tmp_path / "normalized.wav",
            voice_version_id="voice-version-001",
            consent_grant_id="consent-001",
            source_asset_id="asset-001",
            source_checksum_sha256="a" * 64,
            progress=lambda _value: None,
            is_cancelled=lambda: True,
        )
