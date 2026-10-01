from __future__ import annotations

import subprocess
import tempfile
import time
from functools import lru_cache
from pathlib import Path

from ...config import get_settings
from ...domain.studios.contracts import MediaProxyEncodeResultV1, MediaProxySpecV1
from ...domain.studios.providers import MediaProxyProvider
from .media_probe import MEDIA_PROBE_PROVIDERS


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
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class FFmpegMediaProxyProvider:
    name = "builtin.ffmpeg-proxy"

    def __init__(self, executable: str, timeout_seconds: int) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    @property
    def version(self) -> str:
        return _binary_version(self.executable, self.timeout_seconds)

    def transcode(
        self,
        source: Path,
        destination: Path,
        spec: MediaProxySpecV1,
        progress,
        is_cancelled,
    ) -> MediaProxyEncodeResultV1:
        crf = "28" if spec.quality == "draft" else "23"
        scale = (
            f"scale=w='min({spec.max_width},iw)':h='min({spec.max_height},ih)':"
            "force_original_aspect_ratio=decrease:force_divisible_by=2"
        )
        command = [
            self.executable,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-copyts",
            "-start_at_zero",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-vf",
            f"{scale},fps={spec.target_fps}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            crf,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-sn",
            "-dn",
            str(destination),
        ]
        progress(15)
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
                    raise InterruptedError("media_proxy_cancelled")
                if time.monotonic() - started > self.timeout_seconds:
                    _stop_process(process)
                    destination.unlink(missing_ok=True)
                    raise TimeoutError("media_proxy_timeout")
                time.sleep(0.2)
            if process.returncode != 0:
                error_log.seek(0)
                message = error_log.read(4000).decode("utf-8", errors="replace").strip()
                destination.unlink(missing_ok=True)
                raise ValueError(f"media_proxy_failed:{message[-2000:]}")
        progress(78)
        probe_provider = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"]
        probe = probe_provider.probe(destination, asset_id="proxy-pending", checksum_sha256=None)
        if not probe.video_streams:
            destination.unlink(missing_ok=True)
            raise ValueError("media_proxy_video_stream_missing")
        stream = probe.video_streams[0]
        return MediaProxyEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=stream.width,
            height=stream.height,
            frame_rate=stream.frame_rate,
            video_start_microseconds=stream.start_microseconds - probe.start_microseconds,
            audio_start_microseconds=(
                probe.audio_streams[0].start_microseconds - probe.start_microseconds
                if probe.audio_streams
                else 0
            ),
            duration_microseconds=probe.duration_microseconds,
            video_codec=stream.codec,
            audio_codec=probe.audio_streams[0].codec if probe.audio_streams else None,
        )


settings = get_settings()
MEDIA_PROXY_PROVIDERS: dict[str, MediaProxyProvider] = {
    FFmpegMediaProxyProvider.name: FFmpegMediaProxyProvider(
        settings.ffmpeg_path,
        settings.ffmpeg_timeout_seconds,
    )
}
