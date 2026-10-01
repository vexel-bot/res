from __future__ import annotations

import json
import math
import re
import subprocess
import time
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from ...config import get_settings
from ...domain.studios.contracts import (
    VideoRenderSpecV1,
    VideoTechnicalQualityCheckV1,
    VideoTechnicalQualityEvaluationV1,
    VideoTechnicalQualityMetricsV1,
    VideoTechnicalQualityPolicyV1,
)
from .media_probe import MEDIA_PROBE_PROVIDERS

_BLACK_DURATION = re.compile(r"black_duration:(?P<value>[0-9]+(?:\.[0-9]+)?)")
_SILENCE_DURATION = re.compile(r"silence_duration:\s*(?P<value>[0-9]+(?:\.[0-9]+)?)")
_LOUDNORM_JSON = re.compile(r'\{\s*"input_i".*?\}', re.DOTALL)


@lru_cache(maxsize=8)
def _ffmpeg_binary_version(executable: str, timeout_seconds: int) -> str:
    try:
        completed = subprocess.run(
            [executable, "-version"],
            capture_output=True,
            text=True,
            timeout=min(timeout_seconds, 30),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return (completed.stdout.splitlines() or ["unknown"])[0][:110]


def _finite_metric(value: object, fallback: float = -120.0) -> float:
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return fallback
    return parsed if math.isfinite(parsed) else fallback


class FFmpegVideoTechnicalQualityProvider:
    name = "builtin.ffmpeg-qc-v1"

    def __init__(self, ffmpeg: str, timeout_seconds: int) -> None:
        self.ffmpeg = ffmpeg
        self.timeout_seconds = timeout_seconds

    @property
    def version(self) -> str:
        probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"]
        return (
            f"ffprobe={probe.version[:110]}; "
            f"ffmpeg={_ffmpeg_binary_version(self.ffmpeg, self.timeout_seconds)}"
        )[:240]

    def _run(self, arguments: list[str], is_cancelled) -> str:
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                arguments,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            raise ValueError("video_quality_binary_unavailable") from error
        while process.poll() is None:
            if is_cancelled():
                process.kill()
                process.communicate()
                raise InterruptedError("video_quality_cancelled")
            if time.monotonic() - started > self.timeout_seconds:
                process.kill()
                process.communicate()
                raise TimeoutError("video_quality_timeout")
            time.sleep(0.1)
        stdout, stderr = process.communicate()
        output = f"{stdout}\n{stderr}"
        if len(output) > 5_000_000:
            raise ValueError("video_quality_output_too_large")
        if process.returncode != 0:
            raise ValueError(f"video_quality_analysis_failed:{stderr.strip()[:1000]}")
        return output

    def _analyze_video(self, artifact: Path, policy, is_cancelled) -> float:
        output = self._run(
            [
                self.ffmpeg,
                "-hide_banner",
                "-nostats",
                "-loglevel",
                "info",
                "-i",
                str(artifact),
                "-map",
                "0:v:0",
                "-vf",
                (
                    "blackdetect="
                    f"d={policy.black_min_duration_ms / 1000:.3f}:"
                    # Detect actual signal loss while allowing intentionally dark
                    # motion palettes such as #10181c.
                    "pic_th=0.98:pix_th=0.02"
                ),
                "-an",
                "-f",
                "null",
                "-",
            ],
            is_cancelled,
        )
        return sum(float(match.group("value")) for match in _BLACK_DURATION.finditer(output))

    def _analyze_audio(self, artifact: Path, policy, is_cancelled) -> tuple[float, float, float]:
        output = self._run(
            [
                self.ffmpeg,
                "-hide_banner",
                "-nostats",
                "-loglevel",
                "info",
                "-i",
                str(artifact),
                "-map",
                "0:a:0",
                "-af",
                (
                    "silencedetect=noise=-45dB:"
                    f"d={policy.silence_min_duration_ms / 1000:.3f},"
                    "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json"
                ),
                "-vn",
                "-f",
                "null",
                "-",
            ],
            is_cancelled,
        )
        silence_seconds = sum(
            float(match.group("value")) for match in _SILENCE_DURATION.finditer(output)
        )
        payloads = _LOUDNORM_JSON.findall(output)
        if not payloads:
            raise ValueError("video_quality_loudness_summary_missing")
        try:
            loudness = json.loads(payloads[-1])
        except json.JSONDecodeError as error:
            raise ValueError("video_quality_loudness_summary_invalid") from error
        return (
            _finite_metric(loudness.get("input_i")),
            _finite_metric(loudness.get("input_tp")),
            silence_seconds,
        )

    @staticmethod
    def _exact_check(identifier, actual, expected, message) -> VideoTechnicalQualityCheckV1:
        passed = actual == expected
        return VideoTechnicalQualityCheckV1(
            id=identifier,
            severity="blocker",
            status="passed" if passed else "failed",
            actual=actual,
            expected=str(expected),
            message=message,
        )

    @staticmethod
    def _maximum_check(
        identifier,
        actual: float,
        maximum: float,
        *,
        severity: str,
        unit: str,
        message: str,
    ) -> VideoTechnicalQualityCheckV1:
        passed = actual <= maximum
        return VideoTechnicalQualityCheckV1(
            id=identifier,
            severity=severity,
            status="passed" if passed else ("failed" if severity == "blocker" else "warning"),
            actual=round(actual, 6),
            maximum=maximum,
            unit=unit,
            message=message,
        )

    def evaluate(
        self,
        artifact: Path,
        *,
        expected: VideoRenderSpecV1,
        expected_duration_ms: int,
        policy: VideoTechnicalQualityPolicyV1,
        is_cancelled,
    ) -> VideoTechnicalQualityEvaluationV1:
        if is_cancelled():
            raise InterruptedError("video_quality_cancelled")
        probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
            artifact,
            asset_id="quality-pending",
            checksum_sha256=None,
        )
        video = probe.video_streams[0] if len(probe.video_streams) == 1 else None
        audio = probe.audio_streams[0] if len(probe.audio_streams) == 1 else None
        container_duration_ms = probe.duration_microseconds / 1000
        video_duration_ms = (
            (video.duration_microseconds / 1000)
            if video and video.duration_microseconds is not None
            else container_duration_ms
        )
        audio_duration_ms = (
            (audio.duration_microseconds / 1000)
            if audio and audio.duration_microseconds is not None
            else container_duration_ms
        )
        duration_delta_ms = abs(container_duration_ms - expected_duration_ms)
        av_start_delta_ms = (
            abs(video.start_microseconds - audio.start_microseconds) / 1000
            if video and audio
            else container_duration_ms
        )
        av_duration_delta_ms = (
            abs(video_duration_ms - audio_duration_ms)
            if video and audio
            else container_duration_ms
        )
        black_seconds = self._analyze_video(artifact, policy, is_cancelled) if video else 0.0
        loudness_lufs, true_peak_dbfs, silence_seconds = (
            self._analyze_audio(artifact, policy, is_cancelled)
            if audio
            else (-120.0, -120.0, container_duration_ms / 1000)
        )
        black_duration_ms = min(video_duration_ms, black_seconds * 1000)
        silence_duration_ms = min(audio_duration_ms, silence_seconds * 1000)
        black_ratio = black_duration_ms / video_duration_ms if video_duration_ms else 1.0
        silence_ratio = silence_duration_ms / audio_duration_ms if audio_duration_ms else 1.0
        fps = (
            video.frame_rate.numerator / video.frame_rate.denominator if video else 0.0
        )
        checks = [
            self._exact_check(
                "video_stream_count",
                len(probe.video_streams),
                1,
                "O artefato deve conter exatamente um stream de vídeo.",
            ),
            self._exact_check(
                "audio_stream_count",
                len(probe.audio_streams),
                1,
                "O artefato deve conter exatamente um stream de áudio.",
            ),
            self._exact_check(
                "video_codec",
                video.codec if video else "missing",
                "h264" if expected.video_codec == "h264" else expected.video_codec,
                "O codec de vídeo deve corresponder ao contrato de saída.",
            ),
            self._exact_check(
                "audio_codec",
                audio.codec if audio else "missing",
                "aac" if expected.audio_codec == "aac" else expected.audio_codec,
                "O codec de áudio deve corresponder ao contrato de saída.",
            ),
            self._exact_check(
                "dimensions",
                f"{video.width}x{video.height}" if video else "missing",
                f"{expected.width}x{expected.height}",
                "O canvas codificado deve corresponder ao render solicitado.",
            ),
            self._maximum_check(
                "frame_rate",
                abs(fps - expected.fps),
                0.001,
                severity="blocker",
                unit="fps-delta",
                message="O frame rate deve corresponder ao timebase solicitado.",
            ),
            self._maximum_check(
                "duration_delta",
                duration_delta_ms,
                policy.max_duration_delta_ms,
                severity="blocker",
                unit="ms",
                message="A duração final deve permanecer dentro da tolerância frame-exact.",
            ),
            self._maximum_check(
                "av_start_delta",
                av_start_delta_ms,
                policy.max_av_start_delta_ms,
                severity="blocker",
                unit="ms",
                message="Áudio e vídeo devem iniciar sincronizados.",
            ),
            self._maximum_check(
                "av_duration_delta",
                av_duration_delta_ms,
                policy.max_av_duration_delta_ms,
                severity="blocker",
                unit="ms",
                message="Áudio e vídeo devem terminar dentro da tolerância de sync.",
            ),
            self._maximum_check(
                "black_frame_ratio",
                black_ratio,
                policy.max_black_frame_ratio,
                severity="blocker",
                unit="ratio",
                message="Frames pretos acima do limite bloqueiam revisão.",
            ),
            VideoTechnicalQualityCheckV1(
                id="integrated_loudness",
                severity="warning",
                status=(
                    "passed"
                    if policy.min_integrated_loudness_lufs
                    <= loudness_lufs
                    <= policy.max_integrated_loudness_lufs
                    else "warning"
                ),
                actual=round(loudness_lufs, 3),
                minimum=policy.min_integrated_loudness_lufs,
                maximum=policy.max_integrated_loudness_lufs,
                unit="LUFS",
                message="Loudness fora da janela exige decisão humana antes da publicação.",
            ),
            self._maximum_check(
                "true_peak",
                true_peak_dbfs,
                policy.max_true_peak_dbfs,
                severity="warning",
                unit="dBFS",
                message="True peak acima do limite pode introduzir clipping na distribuição.",
            ),
            self._maximum_check(
                "silence_ratio",
                silence_ratio,
                policy.max_silence_ratio,
                severity="warning",
                unit="ratio",
                message="Silêncio excessivo exige revisão editorial.",
            ),
        ]
        metrics = VideoTechnicalQualityMetricsV1(
            video_duration_ms=video_duration_ms,
            audio_duration_ms=audio_duration_ms,
            duration_delta_ms=duration_delta_ms,
            av_start_delta_ms=av_start_delta_ms,
            av_duration_delta_ms=av_duration_delta_ms,
            black_duration_ms=black_duration_ms,
            black_frame_ratio=black_ratio,
            integrated_loudness_lufs=loudness_lufs,
            true_peak_dbfs=true_peak_dbfs,
            silence_duration_ms=silence_duration_ms,
            silence_ratio=silence_ratio,
        )
        status = (
            "failed"
            if any(check.severity == "blocker" and check.status == "failed" for check in checks)
            else "passed"
        )
        return VideoTechnicalQualityEvaluationV1(
            provider=self.name,
            provider_version=self.version,
            policy=policy,
            status=status,
            metrics=metrics,
            checks=checks,
            evaluated_at=datetime.now(UTC),
        )


settings = get_settings()
VIDEO_TECHNICAL_QUALITY_PROVIDERS = {
    FFmpegVideoTechnicalQualityProvider.name: FFmpegVideoTechnicalQualityProvider(
        settings.ffmpeg_path,
        settings.ffmpeg_timeout_seconds,
    )
}
