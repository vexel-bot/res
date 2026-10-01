from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.domain.studios.generative_video import (
    GenerativeVideoOperationV1,
    GenerativeVideoRequestV1,
    GenerativeVideoResultV1,
)
from app.providers.studios.openai_video import OpenAISoraVideoProvider

PROMPT = " ".join(
    (
        "Create exactly one original fictional adult male presenter named Caio Vale.",
        "He is not a real person and must not resemble any public figure or creator.",
        "Brazilian contemporary appearance, early thirties, medium tan skin, short dark brown textured hair,",
        "dark brown eyes, subtle trimmed stubble, calm intelligent expression.",
        "He wears a matte deep-teal overshirt over a plain charcoal crew-neck shirt with no logos.",
        "Vertical 9:16, 720 by 1280, exactly 12 seconds, one uninterrupted medium close-up from mid-chest",
        "upward, locked camera at eye level, natural 50mm portrait perspective.",
        "Stable neutral warm-gray studio background with soft key light, gentle fill and realistic skin texture.",
        "He looks into the lens and remains silent. Natural breathing, two subtle blinks, tiny head and eyebrow",
        "micro-movements, relaxed closed mouth, hands always below frame.",
        "Preserve exactly the same identity, face geometry, hair, clothing, lighting, framing and background",
        "for the full shot. No speech, no lip articulation, no camera motion, no cuts, no zoom, no text,",
        "no logos, no extra people, no visible hands, no objects crossing the face, no morphing,",
        "no beauty-filter skin, no flicker, no warped teeth, no exaggerated expression.",
    )
)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _ffprobe(path: Path, executable: str) -> dict[str, Any]:
    completed = subprocess.run(
        [
            executable,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("ffprobe_invalid_payload")
    return payload


def _strip_audio(raw: Path, canonical: Path, executable: str) -> None:
    if canonical.exists():
        raise FileExistsError("canonical_destination_already_exists")
    canonical.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(raw),
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "copy",
            "-movflags",
            "+faststart",
            str(canonical),
        ],
        check=True,
        timeout=600,
    )


def _validate_canonical_probe(payload: dict[str, Any]) -> None:
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise ValueError("ffprobe_streams_missing")
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(videos) != 1:
        raise ValueError("canonical_requires_exactly_one_video_stream")
    if audios:
        raise ValueError("canonical_requires_zero_audio_streams")
    if (videos[0].get("width"), videos[0].get("height")) != (720, 1280):
        raise ValueError("canonical_resolution_mismatch")


def build_request() -> GenerativeVideoRequestV1:
    return GenerativeVideoRequestV1(
        request_id="clicko-caio-vale-base-video-v1",
        prompt=PROMPT,
        maximum_cost_usd=1.50,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot, resumable Sora source-video runner for Caio Vale."
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../artifacts/studios/avatar-pilots/caio-vale"),
    )
    args = parser.parse_args()

    settings = Settings()
    request = build_request()
    provider = OpenAISoraVideoProvider(settings)
    provider.preflight(request)
    if not args.execute:
        print(json.dumps({"preflight": "passed", "estimatedCostUsd": request.estimated_cost_usd}))
        return

    output_dir = args.output_dir.resolve()
    operation_path = output_dir / "openai-operation-v1.json"
    raw_path = output_dir / "openai-provider-download-v1.mp4"
    canonical_path = output_dir / "base-video-v1.mp4"
    result_path = output_dir / "base-video-v1.result.json"

    if result_path.exists() or canonical_path.exists():
        raise FileExistsError("pilot_output_already_exists")

    if operation_path.exists():
        operation = GenerativeVideoOperationV1.model_validate_json(
            operation_path.read_text(encoding="utf-8")
        )
        if operation.request_id != request.request_id:
            raise ValueError("saved_operation_request_mismatch")
        if operation.status in {"failed", "cancelled"}:
            raise RuntimeError("saved_operation_is_terminal_without_output")
    else:
        operation = provider.start(request)
        _write_json(operation_path, operation.model_dump(mode="json", by_alias=True))

    if operation.status != "completed":
        operation = provider.wait(operation, is_cancelled=lambda: False)
        _write_json(operation_path, operation.model_dump(mode="json", by_alias=True))
    if operation.status != "completed":
        raise RuntimeError(f"provider_operation_{operation.status}")

    if not raw_path.exists():
        provider.download(request, operation, raw_path)
    _strip_audio(raw_path, canonical_path, settings.ffmpeg_path)
    probe = _ffprobe(canonical_path, settings.ffprobe_path)
    _validate_canonical_probe(probe)
    checksum = hashlib.sha256(canonical_path.read_bytes()).hexdigest()
    result = GenerativeVideoResultV1(
        request_id=request.request_id,
        provider_operation_id=operation.provider_operation_id,
        prompt_digest_sha256=hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
        artifact_checksum_sha256=checksum,
        estimated_cost_usd=request.estimated_cost_usd,
        completed_at=datetime.now(UTC),
    )
    _write_json(result_path, result.model_dump(mode="json", by_alias=True))
    raw_path.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "status": "completed",
                "operationId": operation.provider_operation_id,
                "canonicalPath": str(canonical_path),
                "checksumSha256": checksum,
                "estimatedCostUsd": request.estimated_cost_usd,
            }
        )
    )


if __name__ == "__main__":
    main()
