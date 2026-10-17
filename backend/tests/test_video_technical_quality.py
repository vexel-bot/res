import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from app.domain.studios.contracts import (
    VideoRenderSpecV1,
    VideoTechnicalQualityPolicyV1,
)
from app.providers.studios.video_quality import FFmpegVideoTechnicalQualityProvider


def create_fixture(path: Path, *, color: str, audio: bool = True) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:size=360x640:rate=30:duration=2",
    ]
    if audio:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=2",
            ]
        )
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p"])
    if audio:
        command.extend(["-c:a", "aac", "-shortest"])
    command.append(str(path))
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    assert completed.returncode == 0, completed.stderr


def spec(*, audio: str = "aac") -> VideoRenderSpecV1:
    return VideoRenderSpecV1(
        format="mp4",
        width=360,
        height=640,
        fps=30,
        video_codec="h264",
        audio_codec=audio,
        quality="draft",
    )


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg binaries unavailable",
)
def test_video_technical_quality_passes_valid_ugc_and_records_metrics(tmp_path):
    artifact = tmp_path / "valid.mp4"
    create_fixture(artifact, color="0x201a36")
    provider = FFmpegVideoTechnicalQualityProvider("ffmpeg", 60)

    evaluation = provider.evaluate(
        artifact,
        expected=spec(),
        expected_duration_ms=2000,
        policy=VideoTechnicalQualityPolicyV1(),
        is_cancelled=lambda: False,
    )

    assert evaluation.status == "passed"
    assert evaluation.policy.policy_id == "ugc-review-v1"
    assert evaluation.metrics.black_frame_ratio == 0
    assert evaluation.metrics.silence_ratio == 0
    assert -30 <= evaluation.metrics.integrated_loudness_lufs <= -10
    assert all(
        check.status == "passed" for check in evaluation.checks if check.severity == "blocker"
    )


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg binaries unavailable",
)
def test_video_technical_quality_fails_closed_for_black_video(tmp_path):
    artifact = tmp_path / "black.mp4"
    create_fixture(artifact, color="black")
    provider = FFmpegVideoTechnicalQualityProvider("ffmpeg", 60)

    evaluation = provider.evaluate(
        artifact,
        expected=spec(),
        expected_duration_ms=2000,
        policy=VideoTechnicalQualityPolicyV1(),
        is_cancelled=lambda: False,
    )

    assert evaluation.status == "failed"
    black = next(check for check in evaluation.checks if check.id == "black_frame_ratio")
    assert black.status == "failed" and black.severity == "blocker"
    assert evaluation.metrics.black_frame_ratio > 0.95


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg binaries unavailable",
)
def test_video_technical_quality_fails_closed_without_audio(tmp_path):
    artifact = tmp_path / "silent.mp4"
    create_fixture(artifact, color="0x201a36", audio=False)
    provider = FFmpegVideoTechnicalQualityProvider("ffmpeg", 60)

    evaluation = provider.evaluate(
        artifact,
        expected=spec(),
        expected_duration_ms=2000,
        policy=VideoTechnicalQualityPolicyV1(),
        is_cancelled=lambda: False,
    )

    assert evaluation.status == "failed"
    audio_count = next(check for check in evaluation.checks if check.id == "audio_stream_count")
    assert audio_count.status == "failed"


@pytest.mark.parametrize(
    ("timeout_seconds", "cancel_after", "error_type", "message"),
    [
        (10, 0.2, InterruptedError, "video_quality_cancelled"),
        (0.2, None, TimeoutError, "video_quality_timeout"),
    ],
)
def test_video_technical_quality_process_is_cancelled_or_timed_out(
    timeout_seconds,
    cancel_after,
    error_type,
    message,
):
    provider = FFmpegVideoTechnicalQualityProvider("ffmpeg", timeout_seconds)
    started = time.monotonic()

    def is_cancelled() -> bool:
        return cancel_after is not None and time.monotonic() - started >= cancel_after

    with pytest.raises(error_type, match=message):
        provider._run(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            is_cancelled,
        )
