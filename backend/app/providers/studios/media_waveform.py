from __future__ import annotations

import hashlib
import json
import math
import queue
import subprocess
import sys
import tempfile
import threading
import time
from array import array
from functools import lru_cache
from pathlib import Path

from ...config import get_settings
from ...domain.studios.contracts import (
    AudioWaveformBucketV1,
    AudioWaveformManifestV1,
    AudioWaveformSpecV1,
)
from ...domain.studios.providers import MediaWaveformProvider


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


def _spec_digest(spec: AudioWaveformSpecV1) -> str:
    payload = json.dumps(
        spec.model_dump(by_alias=True, mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FFmpegMediaWaveformProvider:
    name = "builtin.ffmpeg-waveform"

    def __init__(self, executable: str, timeout_seconds: int) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    @property
    def version(self) -> str:
        return _binary_version(self.executable, self.timeout_seconds)

    def generate(
        self,
        source: Path,
        destination: Path,
        *,
        media_ingest_id: str,
        source_asset_id: str,
        source_checksum_sha256: str,
        audio_stream_index: int,
        start_microseconds: int,
        source_duration_microseconds: int,
        spec: AudioWaveformSpecV1,
        progress,
        is_cancelled,
    ) -> AudioWaveformManifestV1:
        if is_cancelled():
            raise InterruptedError("media_waveform_cancelled")
        command = [
            self.executable,
            "-hide_banner",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(source),
            "-map",
            f"0:{audio_stream_index}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(spec.sample_rate),
            "-t",
            f"{source_duration_microseconds / 1_000_000:.6f}",
            "-acodec",
            "pcm_s16le",
            "-f",
            "s16le",
            "pipe:1",
        ]
        progress(12)
        started = time.monotonic()
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        chunks: queue.Queue[bytes | None] = queue.Queue(maxsize=8)
        reader_errors: list[BaseException] = []
        stop_reader = threading.Event()
        buckets: list[AudioWaveformBucketV1] = []
        samples_per_bucket = spec.sample_rate // spec.points_per_second
        bucket_count = 0
        bucket_min = 32_767
        bucket_max = -32_768
        bucket_sum_squares = 0
        total_samples = 0

        def finish_bucket() -> None:
            nonlocal bucket_count, bucket_min, bucket_max, bucket_sum_squares
            if bucket_count == 0:
                return
            rms = math.isqrt(bucket_sum_squares // bucket_count) if spec.include_rms else None
            buckets.append(
                AudioWaveformBucketV1(
                    minimum=bucket_min,
                    maximum=bucket_max,
                    rms=rms,
                )
            )
            bucket_count = 0
            bucket_min = 32_767
            bucket_max = -32_768
            bucket_sum_squares = 0

        with tempfile.TemporaryFile() as error_log:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=error_log,
                shell=False,
                creationflags=creation_flags,
            )
            if process.stdout is None:  # pragma: no cover - subprocess contract
                _stop_process(process)
                raise RuntimeError("media_waveform_stdout_unavailable")

            def read_stdout() -> None:
                def enqueue(value: bytes | None) -> bool:
                    while not stop_reader.is_set():
                        try:
                            chunks.put(value, timeout=0.1)
                            return True
                        except queue.Full:
                            continue
                    return False

                try:
                    while chunk := process.stdout.read(64 * 1024):
                        if not enqueue(chunk):
                            return
                except BaseException as error:  # pragma: no cover - OS pipe failure
                    reader_errors.append(error)
                finally:
                    enqueue(None)

            reader = threading.Thread(target=read_stdout, name="ffmpeg-waveform-reader", daemon=True)
            reader.start()
            pending = b""
            try:
                while True:
                    if is_cancelled():
                        _stop_process(process)
                        raise InterruptedError("media_waveform_cancelled")
                    if time.monotonic() - started > self.timeout_seconds:
                        _stop_process(process)
                        raise TimeoutError("media_waveform_timeout")
                    try:
                        chunk = chunks.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if chunk is None:
                        break
                    payload = pending + chunk
                    if len(payload) % 2:
                        pending = payload[-1:]
                        payload = payload[:-1]
                    else:
                        pending = b""
                    values = array("h")
                    values.frombytes(payload)
                    if sys.byteorder != "little":  # pragma: no cover - CI is little endian
                        values.byteswap()
                    for sample in values:
                        bucket_min = min(bucket_min, sample)
                        bucket_max = max(bucket_max, sample)
                        bucket_sum_squares += sample * sample
                        bucket_count += 1
                        total_samples += 1
                        if bucket_count == samples_per_bucket:
                            finish_bucket()
                    if source_duration_microseconds > 0:
                        decoded_microseconds = total_samples * 1_000_000 // spec.sample_rate
                        progress(min(82, 12 + decoded_microseconds * 70 // source_duration_microseconds))
                reader.join(timeout=1)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired as error:
                    _stop_process(process)
                    raise TimeoutError("media_waveform_timeout") from error
                if pending:
                    raise ValueError("media_waveform_odd_pcm_payload")
                if reader_errors:
                    raise RuntimeError("media_waveform_pipe_read_failed") from reader_errors[0]
                if process.returncode != 0:
                    error_log.seek(0)
                    message = error_log.read(4000).decode("utf-8", errors="replace").strip()
                    raise ValueError(f"media_waveform_failed:{message[-2000:]}")
            except Exception:
                stop_reader.set()
                _stop_process(process)
                reader.join(timeout=1)
                destination.unlink(missing_ok=True)
                raise
        finish_bucket()
        duration_microseconds = (
            total_samples * 1_000_000 + spec.sample_rate // 2
        ) // spec.sample_rate
        manifest = AudioWaveformManifestV1(
            media_ingest_id=media_ingest_id,
            source_asset_id=source_asset_id,
            source_checksum_sha256=source_checksum_sha256,
            audio_stream_index=audio_stream_index,
            start_microseconds=start_microseconds,
            duration_microseconds=duration_microseconds,
            sample_rate=spec.sample_rate,
            samples_per_bucket=samples_per_bucket,
            total_samples=total_samples,
            bucket_count=len(buckets),
            buckets=buckets,
            provider=self.name,
            provider_version=self.version,
            spec=spec,
            spec_digest=_spec_digest(spec),
        )
        destination.write_text(
            json.dumps(
                manifest.model_dump(by_alias=True, mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        progress(86)
        return manifest


settings = get_settings()
MEDIA_WAVEFORM_PROVIDERS: dict[str, MediaWaveformProvider] = {
    FFmpegMediaWaveformProvider.name: FFmpegMediaWaveformProvider(
        settings.ffmpeg_path,
        settings.ffmpeg_timeout_seconds,
    )
}
