from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from app.domain.studios.video_factory import VideoFactoryProgramEvidenceV1

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
)


def render_frame(ffmpeg: str, source: Path, timestamp: float, output: Path) -> None:
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            "scale=180:320:force_original_aspect_ratio=decrease,pad=180:320:(ow-iw)/2:(oh-ih)/2:black",
            str(output),
        ],
        check=True,
    )


def xstack(ffmpeg: str, inputs: list[Path], output: Path, columns: int) -> None:
    rows = (len(inputs) + columns - 1) // columns
    padded = [*inputs]
    while len(padded) < rows * columns:
        padded.append(inputs[-1])
    command = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
    for path in padded:
        command.extend(["-i", str(path)])
    layout = "|".join(
        f"{(index % columns) * 180}_{(index // columns) * 320}"
        for index in range(len(padded))
    )
    command.extend(
        [
            "-filter_complex",
            f"xstack=inputs={len(padded)}:layout={layout}:fill=black",
            "-frames:v",
            "1",
            str(output),
        ]
    )
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, default=FACTORY_ROOT / "program-manifest.json")
    parser.add_argument("--output-root", type=Path, default=FACTORY_ROOT / "review-contact-sheets")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    if not shutil.which(args.ffmpeg):
        raise SystemExit("ffmpeg_required")
    program = VideoFactoryProgramEvidenceV1.model_validate_json(
        args.program.read_text(encoding="utf-8")
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    poster_frames: list[Path] = []
    manifest = []
    for job in program.pilot.jobs:
        if not job.artifact_path:
            raise ValueError(f"pilot_artifact_missing:{job.job_id}")
        source = (REPOSITORY_ROOT / job.artifact_path).resolve()
        case_root = args.output_root / job.job_id
        case_root.mkdir(parents=True, exist_ok=True)
        duration_seconds = 15.0
        frames = []
        for index, fraction in enumerate((0.1, 0.3, 0.5, 0.7, 0.9), start=1):
            output = case_root / f"moment-{index}.png"
            render_frame(args.ffmpeg, source, duration_seconds * fraction, output)
            frames.append(output)
        sheet = args.output_root / f"{job.job_id}-sheet.png"
        xstack(args.ffmpeg, frames, sheet, columns=5)
        poster_frames.append(frames[2])
        manifest.append(
            {
                "jobId": job.job_id,
                "caseId": job.case_id,
                "artifactPath": job.artifact_path,
                "sheetPath": sheet.relative_to(REPOSITORY_ROOT).as_posix(),
            }
        )
    overview = args.output_root / "pilot-12-overview.png"
    xstack(args.ffmpeg, poster_frames, overview, columns=4)
    (args.output_root / "manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": "clicko.factory-review-contact-sheets.v1",
                "overviewPath": overview.relative_to(REPOSITORY_ROOT).as_posix(),
                "items": manifest,
                "humanReviewReplaced": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"sheets": len(manifest), "overview": str(overview)}))


if __name__ == "__main__":
    main()
