from __future__ import annotations

import subprocess
import tempfile
import time
import wave
from functools import lru_cache
from pathlib import Path

from ...config import get_settings
from ...domain.studios.contracts import VoiceCloneReferenceV1
from ...domain.studios.providers import VOICE_REFERENCE_NORMALIZERS
from ...services.object_storage import sha256_file

VOICE_REFERENCE_SAMPLE_RATE = 24_000
VOICE_REFERENCE_MIN_DURATION_MS = 3_000
VOICE_REFERENCE_MAX_DURATION_MS = 30_000


@lru_cache(maxsize=8)
def _binary_version(executable: str, timeout_seconds: int) -> str:
    completed = subprocess.run(
        [executable, "-version"],
        capture_output=True,
        text=True,
        timeout=min(timeout_seconds, 30),
        check=False,
    )
    if completed.returncode != 0:
        return "unknown"
    return (completed.stdout.splitlines() or ["unknown"])[0][:240]


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class FFmpegVoiceReferenceNormalizer:
    name = "builtin.ffmpeg-voice-reference-v1"

    def __init__(self, executable: str, timeout_seconds: int) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    @property
    def version(self) -> str:
        return _binary_version(self.executable, self.timeout_seconds)

    def normalize(
        self,
        source: Path,
        destination: Path,
        *,
        voice_version_id: str,
        consent_grant_id: str,
        source_asset_id: str,
        source_checksum_sha256: str,
        progress,
        is_cancelled,
    ) -> VoiceCloneReferenceV1:
        if is_cancelled():
            raise InterruptedError("voice_reference_normalization_cancelled")
        command = [
            self.executable,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(VOICE_REFERENCE_SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            "-t",
            str(VOICE_REFERENCE_MAX_DURATION_MS / 1000),
            str(destination),
        ]
        destination.parent.mkdir(parents=True, exist_ok=True)
        progress(8)
        started = time.monotonic()
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with tempfile.TemporaryFile() as error_log:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=error_log,
                shell=False,
                creationflags=creation_flags,
            )
            while process.poll() is None:
                if is_cancelled():
                    _stop_process(process)
                    destination.unlink(missing_ok=True)
                    raise InterruptedError("voice_reference_normalization_cancelled")
                if time.monotonic() - started > self.timeout_seconds:
                    _stop_process(process)
                    destination.unlink(missing_ok=True)
                    raise TimeoutError("voice_reference_normalization_timeout")
                time.sleep(0.1)
            if process.returncode != 0:
                error_log.seek(0)
                message = error_log.read(4000).decode("utf-8", errors="replace").strip()
                destination.unlink(missing_ok=True)
                raise ValueError(f"voice_reference_normalization_failed:{message[-2000:]}")
        try:
            with wave.open(str(destination), "rb") as normalized:
                channels = normalized.getnchannels()
                sample_width = normalized.getsampwidth()
                sample_rate = normalized.getframerate()
                frames = normalized.getnframes()
        except (OSError, EOFError, wave.Error) as error:
            destination.unlink(missing_ok=True)
            raise ValueError("voice_reference_normalized_wav_invalid") from error
        duration_ms = round(frames * 1000 / sample_rate)
        if channels != 1 or sample_width != 2 or sample_rate != VOICE_REFERENCE_SAMPLE_RATE:
            destination.unlink(missing_ok=True)
            raise ValueError("voice_reference_normalized_format_mismatch")
        if not VOICE_REFERENCE_MIN_DURATION_MS <= duration_ms <= VOICE_REFERENCE_MAX_DURATION_MS:
            destination.unlink(missing_ok=True)
            raise ValueError("voice_reference_duration_out_of_range")
        progress(15)
        return VoiceCloneReferenceV1(
            voice_version_id=voice_version_id,
            consent_grant_id=consent_grant_id,
            source_asset_id=source_asset_id,
            source_checksum_sha256=source_checksum_sha256,
            normalized_checksum_sha256=sha256_file(destination),
            duration_ms=duration_ms,
        )


settings = get_settings()
VOICE_REFERENCE_NORMALIZERS[FFmpegVoiceReferenceNormalizer.name] = (
    FFmpegVoiceReferenceNormalizer(
        settings.ffmpeg_path,
        settings.ffmpeg_timeout_seconds,
    )
)
