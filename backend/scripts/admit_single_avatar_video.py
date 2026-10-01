"""Validate one base video for the fixed HeyGem visual-avatar pilot.

This command never calls HeyGem, never trains a voice and never accepts more
than one input file. Human assertions are explicit because ffprobe cannot prove
identity rights, person count, face visibility or capture suitability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.avatar_models import AvatarVisualSourceV1  # noqa: E402

SourceKind = Literal["authorized_performer_video", "synthetic_original_video"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe(path: Path, ffprobe: str) -> dict[str, Any]:
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(f"avatar_base_video_probe_failed:{completed.stderr[:500]}")
    if len(completed.stdout) > 5_000_000:
        raise ValueError("avatar_base_video_probe_output_too_large")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("avatar_base_video_probe_invalid_json") from error


def validate_probe_payload(payload: dict[str, Any]) -> tuple[int, int, int]:
    video_streams = [
        stream
        for stream in payload.get("streams") or []
        if stream.get("codec_type") == "video"
    ]
    if len(video_streams) != 1:
        raise ValueError("avatar_base_video_requires_exactly_one_video_stream")
    stream = video_streams[0]
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    if width < 720 or height < 720:
        raise ValueError("avatar_base_video_requires_at_least_720_pixels_per_dimension")
    duration_value = (payload.get("format") or {}).get("duration") or stream.get(
        "duration"
    )
    try:
        duration_ms = round(float(duration_value) * 1000)
    except (TypeError, ValueError) as error:
        raise ValueError("avatar_base_video_duration_missing") from error
    if duration_ms < 8_000:
        raise ValueError("avatar_base_video_requires_at_least_8_seconds")
    return duration_ms, width, height


def build_visual_source(
    *,
    path: Path,
    asset_id: str,
    source_kind: SourceKind,
    rights_status: Literal["open_license", "rights_verified"],
    consent_grant_id: str | None,
    exactly_one_person_approved: bool,
    face_visible_approved: bool,
    neutral_capture_approved: bool,
    ffprobe: str,
) -> AvatarVisualSourceV1:
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError("avatar_base_video_regular_file_required")
    if resolved.suffix.lower() not in {".mp4", ".mov"}:
        raise ValueError("avatar_base_video_requires_mp4_or_mov")
    if not exactly_one_person_approved:
        raise ValueError("avatar_base_video_person_count_review_required")
    if not face_visible_approved:
        raise ValueError("avatar_base_video_face_review_required")
    if not neutral_capture_approved:
        raise ValueError("avatar_base_video_capture_review_required")
    duration_ms, width, height = validate_probe_payload(_probe(resolved, ffprobe))
    return AvatarVisualSourceV1(
        source_kind=source_kind,
        asset_id=asset_id,
        checksum_sha256=_sha256(resolved),
        duration_milliseconds=duration_ms,
        width=width,
        height=height,
        exactly_one_person=True,
        face_visible_and_unobstructed=True,
        neutral_capture_approved=True,
        rights_status=rights_status,
        consent_grant_id=consent_grant_id,
        voice_training_allowed=False,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Admit exactly one base video for one HeyGem visual avatar."
    )
    parser.add_argument("video", type=Path, help="The only MP4/MOV base video")
    parser.add_argument("--asset-id", required=True)
    parser.add_argument(
        "--source-kind",
        required=True,
        choices=["authorized_performer_video", "synthetic_original_video"],
    )
    parser.add_argument(
        "--rights-status", required=True, choices=["open_license", "rights_verified"]
    )
    parser.add_argument("--consent-grant-id")
    parser.add_argument("--one-person-approved", action="store_true", required=True)
    parser.add_argument("--face-visible-approved", action="store_true", required=True)
    parser.add_argument("--neutral-capture-approved", action="store_true", required=True)
    parser.add_argument("--ffprobe", default=shutil.which("ffprobe") or "ffprobe")
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        source = build_visual_source(
            path=args.video,
            asset_id=args.asset_id,
            source_kind=args.source_kind,
            rights_status=args.rights_status,
            consent_grant_id=args.consent_grant_id,
            exactly_one_person_approved=args.one_person_approved,
            face_visible_approved=args.face_visible_approved,
            neutral_capture_approved=args.neutral_capture_approved,
            ffprobe=args.ffprobe,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2
    rendered = source.model_dump_json(by_alias=True, indent=2)
    if args.output:
        destination = args.output.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f"{destination.suffix}.tmp")
        temporary.write_text(rendered + "\n", encoding="utf-8")
        temporary.replace(destination)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
