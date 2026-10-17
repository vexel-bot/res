from __future__ import annotations

import json
import subprocess
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any

from ...config import get_settings
from ...domain.studios.contracts import (
    AudioStreamV1,
    FrameRateV1,
    MediaProbeResultV1,
    StreamTimeBaseV1,
    VideoStreamV1,
)
from ...domain.studios.providers import MediaProbeProvider


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value not in (None, "", "N/A") else None
    except (TypeError, ValueError):
        return None


def _microseconds(value: object) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return max(0, int(Decimal(str(value)) * 1_000_000))
    except (InvalidOperation, ValueError):
        return None


def _signed_microseconds(value: object) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return int(Decimal(str(value)) * 1_000_000)
    except (InvalidOperation, ValueError):
        return None


def _frame_rate_or_none(value: object) -> FrameRateV1 | None:
    try:
        numerator_text, denominator_text = str(value).split("/", maxsplit=1)
        numerator = int(numerator_text)
        denominator = int(denominator_text)
        if numerator > 0 and denominator > 0:
            return FrameRateV1(numerator=numerator, denominator=denominator)
    except (TypeError, ValueError):
        pass
    return None


def _time_base(value: object) -> StreamTimeBaseV1 | None:
    try:
        numerator_text, denominator_text = str(value).split("/", maxsplit=1)
        numerator = int(numerator_text)
        denominator = int(denominator_text)
        if numerator > 0 and denominator > 0:
            return StreamTimeBaseV1(numerator=numerator, denominator=denominator)
    except (TypeError, ValueError):
        pass
    return None


def _rotation(stream: dict[str, Any]) -> int:
    tagged = _optional_int((stream.get("tags") or {}).get("rotate"))
    if tagged is not None:
        return max(-360, min(360, tagged))
    for item in stream.get("side_data_list") or []:
        rotation = _optional_int(item.get("rotation"))
        if rotation is not None:
            return max(-360, min(360, rotation))
    return 0


@lru_cache(maxsize=8)
def _binary_version(executable: str, timeout_seconds: int) -> str:
    completed = subprocess.run(
        [executable, "-version"],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        return "unknown"
    return (completed.stdout.splitlines() or ["unknown"])[0][:240]


class FFprobeMediaProbeProvider:
    name = "builtin.ffprobe"

    def __init__(self, executable: str, timeout_seconds: int) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    @property
    def version(self) -> str:
        return _binary_version(self.executable, self.timeout_seconds)

    def probe(self, path: Path, *, asset_id: str, checksum_sha256: str | None) -> MediaProbeResultV1:
        completed = subprocess.run(
            [
                self.executable,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            message = (completed.stderr or "ffprobe failed").strip()[:1000]
            raise ValueError(f"media_probe_failed:{message}")
        if len(completed.stdout) > 5_000_000:
            raise ValueError("media_probe_output_too_large")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ValueError("media_probe_invalid_json") from error
        streams = payload.get("streams") or []
        video_streams = [
            VideoStreamV1(
                index=int(stream.get("index", 0)),
                codec=str(stream.get("codec_name") or "unknown"),
                width=int(stream.get("width") or 0),
                height=int(stream.get("height") or 0),
                pixel_format=stream.get("pix_fmt"),
                frame_rate=(
                    _frame_rate_or_none(stream.get("avg_frame_rate"))
                    or _frame_rate_or_none(stream.get("r_frame_rate"))
                    or FrameRateV1()
                ),
                real_frame_rate=_frame_rate_or_none(stream.get("r_frame_rate")),
                time_base=_time_base(stream.get("time_base")),
                start_pts=_optional_int(stream.get("start_pts")),
                start_microseconds=_signed_microseconds(stream.get("start_time")) or 0,
                duration_ticks=_optional_int(stream.get("duration_ts")),
                duration_microseconds=_microseconds(stream.get("duration")),
                bitrate=_optional_int(stream.get("bit_rate")),
                rotation_degrees=_rotation(stream),
            )
            for stream in streams
            if stream.get("codec_type") == "video" and stream.get("width") and stream.get("height")
        ]
        audio_streams = [
            AudioStreamV1(
                index=int(stream.get("index", 0)),
                codec=str(stream.get("codec_name") or "unknown"),
                sample_rate=_optional_int(stream.get("sample_rate")),
                channels=_optional_int(stream.get("channels")),
                channel_layout=stream.get("channel_layout"),
                time_base=_time_base(stream.get("time_base")),
                start_pts=_optional_int(stream.get("start_pts")),
                start_microseconds=_signed_microseconds(stream.get("start_time")) or 0,
                duration_ticks=_optional_int(stream.get("duration_ts")),
                duration_microseconds=_microseconds(stream.get("duration")),
                bitrate=_optional_int(stream.get("bit_rate")),
            )
            for stream in streams
            if stream.get("codec_type") == "audio"
        ]
        format_data = payload.get("format") or {}
        duration = _microseconds(format_data.get("duration"))
        if duration is None:
            durations = [
                value.duration_microseconds
                for value in [*video_streams, *audio_streams]
                if value.duration_microseconds is not None
            ]
            duration = max(durations, default=0)
        return MediaProbeResultV1(
            provider=self.name,
            provider_version=self.version,
            asset_id=asset_id,
            checksum_sha256=checksum_sha256,
            container=str(format_data.get("format_name") or "unknown")[:240],
            start_microseconds=_signed_microseconds(format_data.get("start_time")) or 0,
            duration_microseconds=duration,
            size_bytes=_optional_int(format_data.get("size")) or path.stat().st_size,
            bitrate=_optional_int(format_data.get("bit_rate")),
            video_streams=video_streams,
            audio_streams=audio_streams,
            provider_trace={
                "formatLongName": str(format_data.get("format_long_name") or "")[:240],
                "streamCount": len(streams),
            },
        )


settings = get_settings()
MEDIA_PROBE_PROVIDERS: dict[str, MediaProbeProvider] = {
    FFprobeMediaProbeProvider.name: FFprobeMediaProbeProvider(
        settings.ffprobe_path,
        settings.ffprobe_timeout_seconds,
    )
}
