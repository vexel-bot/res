from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import textwrap
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.domain.studios.creative_autonomy import (
    AnimaticBatchEvidenceV1,
    AnimaticPlanV1,
    AnimaticRenderEvidenceV1,
    CreativeAutonomyCaseV1,
    CreativePilotCasebookV1,
    animatic_plan_digest,
    creative_casebook_digest,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path(
            "/usr/share/fonts/truetype/dejavu2/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu2/DejaVuSans.ttf"
        ),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def draw_card(case: CreativeAutonomyCaseV1, shot_index: int, destination: Path) -> None:
    shot = case.storyboard.shots[shot_index]
    beat = next(item for item in case.script.beats if item.beat_id == shot.beat_id)
    width = case.animatic.width
    height = case.animatic.height
    image = Image.new("RGB", (width, height), shot.primary_color)
    draw = ImageDraw.Draw(image)
    margin = 42
    accent = shot.accent_color
    draw.rounded_rectangle(
        (margin, 48, width - margin, 118),
        radius=18,
        fill=accent,
    )
    draw.text(
        (margin + 22, 68),
        f"SHOT {shot_index + 1:02d} / {len(case.storyboard.shots):02d}",
        font=font(25, bold=True),
        fill="#FFFFFF",
    )
    draw.text(
        (margin, 154),
        case.title,
        font=font(30, bold=True),
        fill="#F5F7FA",
    )
    draw.text(
        (margin, 208),
        f"{beat.narrative_role.upper()} · {shot.visual_function.upper()}",
        font=font(20, bold=True),
        fill=accent,
    )
    body = "\n".join(textwrap.wrap(shot.frame_description, width=42))
    draw.multiline_text(
        (margin, 270),
        body,
        font=font(25),
        fill="#F5F7FA",
        spacing=10,
    )
    if shot.on_screen_text:
        text = "\n".join(textwrap.wrap(shot.on_screen_text, width=28))
        box_top = 650
        draw.rounded_rectangle(
            (margin, box_top, width - margin, 820),
            radius=22,
            outline=accent,
            width=4,
        )
        draw.multiline_text(
            (margin + 24, box_top + 24),
            text,
            font=font(29, bold=True),
            fill="#FFFFFF",
            spacing=8,
        )
    duration = shot.duration_milliseconds / 1000
    draw.text(
        (margin, height - 92),
        f"{duration:.2f}s · {shot.placeholder_kind} · PLACEHOLDER",
        font=font(19),
        fill="#AAB2C0",
    )
    draw.text(
        (margin, height - 54),
        "SEM PUBLICAÇÃO · SEM VOZ/IDENTIDADE SINTÉTICA",
        font=font(16, bold=True),
        fill="#FFB4A8",
    )
    image.save(destination, format="PNG", optimize=True)


def render_case(
    case: CreativeAutonomyCaseV1,
    destination: Path,
    *,
    ffmpeg: str,
    ffprobe: str,
) -> tuple[Path, dict[str, object]]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"clicko-animatic-{case.case_id}-") as directory:
        workdir = Path(directory)
        images: list[Path] = []
        command = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
        for index, shot in enumerate(case.storyboard.shots):
            image_path = workdir / f"shot-{index:03d}.png"
            draw_card(case, index, image_path)
            images.append(image_path)
            command.extend(
                [
                    "-loop",
                    "1",
                    "-framerate",
                    str(case.animatic.frame_rate),
                    "-t",
                    f"{shot.duration_milliseconds / 1000:.6f}",
                    "-i",
                    str(image_path),
                ]
            )
        total_ms = case.storyboard.target_duration_milliseconds
        command.extend(
            [
                "-f",
                "lavfi",
                "-t",
                f"{total_ms / 1000:.6f}",
                "-i",
                "anullsrc=r=48000:cl=stereo",
            ]
        )
        filters = []
        concat_inputs = []
        for index in range(len(images)):
            filters.append(
                f"[{index}:v]scale={case.animatic.width}:{case.animatic.height},"
                f"fps={case.animatic.frame_rate},format=yuv420p[v{index}]"
            )
            concat_inputs.append(f"[v{index}]")
        filters.append(
            f"{''.join(concat_inputs)}concat=n={len(images)}:v=1:a=0[vout]"
        )
        frames = round(total_ms * case.animatic.frame_rate / 1000)
        command.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[vout]",
                "-map",
                f"{len(images)}:a:0",
                "-frames:v",
                str(frames),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "25",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-t",
                f"{total_ms / 1000:.6f}",
                "-movflags",
                "+faststart",
                str(destination),
            ]
        )
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"animatic_render_failed:{case.case_id}:{completed.stderr[-2000:]}")

    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height,r_frame_rate:format=duration",
            "-of",
            "json",
            str(destination),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return destination, json.loads(probe.stdout)


def probe_values(probe: dict[str, object]) -> tuple[int, int, float, int]:
    streams = probe["streams"]
    assert isinstance(streams, list)
    video = next(item for item in streams if item["codec_type"] == "video")
    numerator, denominator = str(video["r_frame_rate"]).split("/", maxsplit=1)
    frame_rate = int(numerator) / int(denominator)
    format_info = probe["format"]
    assert isinstance(format_info, dict)
    duration_ms = round(float(format_info["duration"]) * 1000)
    return int(video["width"]), int(video["height"]), frame_rate, duration_ms


def main() -> int:
    parser = argparse.ArgumentParser(description="Render all governed Clicko placeholder animatics.")
    parser.add_argument(
        "--casebook",
        type=Path,
        default=Path("benchmarks/studios/creative/video-creative-pilot-casebook.v1.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/validation/video-creative-pilot/animatics-20260901-v1"),
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    if not shutil.which(args.ffmpeg) or not shutil.which(args.ffprobe):
        raise SystemExit("ffmpeg_and_ffprobe_required")

    casebook = CreativePilotCasebookV1.model_validate_json(
        args.casebook.read_text(encoding="utf-8")
    )
    output_dir = args.output_dir.resolve()
    updated_cases: list[CreativeAutonomyCaseV1] = []
    pending_evidence: list[tuple[CreativeAutonomyCaseV1, dict[str, object]]] = []
    blockers: list[str] = []
    for case in casebook.cases:
        destination = output_dir / f"{case.case_id}.mp4"
        _, probe = render_case(
            case,
            destination,
            ffmpeg=args.ffmpeg,
            ffprobe=args.ffprobe,
        )
        width, height, frame_rate, duration_ms = probe_values(probe)
        expected_ms = case.storyboard.target_duration_milliseconds
        tolerance_ms = round(2000 / case.animatic.frame_rate)
        notes: list[str] = []
        if (width, height) != (case.animatic.width, case.animatic.height):
            notes.append("dimensions_mismatch")
        if abs(frame_rate - case.animatic.frame_rate) > 0.001:
            notes.append("frame_rate_mismatch")
        if abs(duration_ms - expected_ms) > tolerance_ms:
            notes.append("duration_mismatch")
        artifact_digest = sha256_file(destination)
        relative_path = destination.relative_to(args.casebook.resolve().parents[3]).as_posix()
        animatic_payload = case.animatic.model_dump(mode="json", by_alias=True)
        animatic_payload.update(
            {
                "status": "rendered",
                "renderAssetPath": relative_path,
                "renderDigestSha256": artifact_digest,
            }
        )
        updated_animatic = AnimaticPlanV1.model_validate(animatic_payload)
        case_payload = case.model_dump(mode="json", by_alias=True)
        case_payload["animatic"] = updated_animatic.model_dump(mode="json", by_alias=True)
        updated_case = CreativeAutonomyCaseV1.model_validate(case_payload)
        updated_cases.append(updated_case)
        if notes:
            blockers.extend(f"{case.case_id}:{note}" for note in notes)
        pending_evidence.append(
            (
                updated_case,
                {
                    "artifact_path": relative_path,
                    "artifact_digest": artifact_digest,
                    "width": width,
                    "height": height,
                    "frame_rate": frame_rate,
                    "duration_ms": duration_ms,
                    "expected_ms": expected_ms,
                    "notes": notes,
                },
            )
        )

    updated_casebook = CreativePilotCasebookV1(
        suite_id=casebook.suite_id,
        cases=updated_cases,
    )
    args.casebook.write_text(
        json.dumps(
            updated_casebook.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    renders = [
        AnimaticRenderEvidenceV1(
            case_id=case.case_id,
            animatic_id=case.animatic.animatic_id,
            animatic_digest_sha256=animatic_plan_digest(case.animatic),
            artifact_path=str(values["artifact_path"]),
            artifact_digest_sha256=str(values["artifact_digest"]),
            width=int(values["width"]),
            height=int(values["height"]),
            frame_rate=float(values["frame_rate"]),
            duration_milliseconds=int(values["duration_ms"]),
            expected_duration_milliseconds=int(values["expected_ms"]),
            qc_passed=not values["notes"],
            qc_notes=list(values["notes"]),
        )
        for case, values in pending_evidence
    ]
    manifest = AnimaticBatchEvidenceV1(
        suite_id=updated_casebook.suite_id,
        casebook_digest_sha256=creative_casebook_digest(updated_casebook),
        renders=renders,
        eligible=not blockers,
        blockers=blockers,
        rendered_at=datetime.now(UTC),
    )
    manifest_path = args.manifest or output_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "renders": len(renders),
                "eligible": manifest.eligible,
                "blockers": manifest.blockers,
                "casebookDigestSha256": manifest.casebook_digest_sha256,
            },
            ensure_ascii=False,
        )
    )
    return 0 if manifest.eligible else 1


if __name__ == "__main__":
    raise SystemExit(main())
