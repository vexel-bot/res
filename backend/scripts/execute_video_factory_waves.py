from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.creative_autonomy import (
    CreativeAutonomyCaseV1,
    CreativePilotCasebookV1,
    creative_casebook_digest,
    format_recipe_digest,
)
from app.domain.studios.video_factory import (
    VideoFactoryBudgetV1,
    VideoFactoryJobV1,
    VideoFactoryProgramEvidenceV1,
    VideoFactoryWaveEvidenceV1,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CASEBOOK_PATH = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "studios"
    / "creative"
    / "video-creative-pilot-casebook.v1.json"
)
OUTPUT_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
)
FIXED_STARTED_AT = datetime(2026, 9, 1, 19, 0, tzinfo=UTC)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_path(case: CreativeAutonomyCaseV1) -> Path:
    if not case.animatic.render_asset_path or not case.animatic.render_digest_sha256:
        raise ValueError(f"case_missing_rendered_animatic:{case.case_id}")
    path = (REPOSITORY_ROOT / case.animatic.render_asset_path).resolve()
    if not path.is_relative_to(REPOSITORY_ROOT) or not path.is_file():
        raise ValueError(f"case_animatic_missing:{case.case_id}")
    if sha256(path) != case.animatic.render_digest_sha256:
        raise ValueError(f"case_animatic_digest_mismatch:{case.case_id}")
    return path


def probe(path: Path, ffprobe: str) -> dict[str, object]:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def render_one(
    case: CreativeAutonomyCaseV1,
    *,
    wave: str,
    variant: int,
    ordinal: int,
    ffmpeg: str,
    ffprobe: str,
    max_attempts: int,
) -> VideoFactoryJobV1:
    source = source_path(case)
    output_dir = OUTPUT_ROOT / wave
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "pilot" if wave == "pilot_12" else f"cal-{variant}"
    output = output_dir / f"{ordinal:03d}-{case.case_id}-{suffix}.mp4"
    base_filter = (
        "scale=360:640:force_original_aspect_ratio=decrease,"
        "pad=360:640:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    )
    filters = {
        0: base_filter,
        1: f"{base_filter},eq=saturation=1.05:contrast=1.02",
        2: f"{base_filter},eq=saturation=.95:brightness=.01,unsharp=5:5:.35:5:5:0",
    }
    started = time.perf_counter()
    attempts = 0
    error = ""
    while attempts < max_attempts:
        attempts += 1
        command = [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            filters[variant],
            "-an",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            break
        error = (result.stderr or "ffmpeg_failed")[-1000:]
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    if not output.is_file() or output.stat().st_size == 0:
        return VideoFactoryJobV1(
            job_id=f"{wave}-{ordinal:03d}",
            wave=wave,
            ordinal=ordinal,
            case_id=case.case_id,
            family=case.family,
            recipe_id=case.recipe.recipe_id,
            recipe_digest_sha256=format_recipe_digest(case.recipe),
            idempotency_key=f"factory-{wave}-{ordinal:03d}-{case.case_id}",
            capability="media_cpu",
            provider="builtin.ffmpeg-calibration-v1",
            provider_version="ffmpeg-local",
            status="failed",
            attempts=attempts,
            max_attempts=max_attempts,
            direct_cost_usd=0,
            rollback_recipe_id=case.recipe.recipe_id,
            rollback_provider="builtin.ffmpeg-calibration-v1",
            blockers=[f"render_failed:{error}"],
        )
    metadata = probe(output, ffprobe)
    stream = metadata["streams"][0]
    duration_ms = round(float(metadata["format"]["duration"]) * 1000)
    expected_ms = case.script.target_duration_milliseconds
    qc = (
        stream["width"] == 360
        and stream["height"] == 640
        and abs(duration_ms - expected_ms) <= 100
    )
    return VideoFactoryJobV1(
        job_id=f"{wave}-{ordinal:03d}",
        wave=wave,
        ordinal=ordinal,
        case_id=case.case_id,
        family=case.family,
        recipe_id=case.recipe.recipe_id,
        recipe_digest_sha256=format_recipe_digest(case.recipe),
        idempotency_key=f"factory-{wave}-{ordinal:03d}-{case.case_id}",
        capability="media_cpu",
        provider="builtin.ffmpeg-calibration-v1",
        provider_version="ffmpeg-local",
        status="succeeded" if qc else "failed",
        attempts=attempts,
        max_attempts=max_attempts,
        source_artifact_digest_sha256=sha256(source),
        artifact_path=output.relative_to(REPOSITORY_ROOT).as_posix(),
        artifact_digest_sha256=sha256(output),
        render_duration_milliseconds=elapsed_ms,
        direct_cost_usd=0,
        technical_qc_passed=qc,
        human_review_status="pending",
        rollback_recipe_id=case.recipe.recipe_id,
        rollback_provider="builtin.ffmpeg-calibration-v1",
        blockers=[] if qc else ["technical_qc_failed"],
    )


def execute_wave(
    casebook: CreativePilotCasebookV1,
    *,
    wave: str,
    variants: tuple[int, ...],
    count: int,
    ffmpeg: str,
    ffprobe: str,
) -> VideoFactoryWaveEvidenceV1:
    budget = VideoFactoryBudgetV1(
        max_direct_cost_usd=1,
        max_wall_time_seconds=3600,
        max_concurrent_jobs=4,
        rate_limit_jobs_per_minute=120,
        max_attempts_per_job=2,
    )
    work = []
    ordinal = 0
    for variant in variants:
        for case in casebook.cases:
            ordinal += 1
            work.append((case, variant, ordinal))
    if len(work) != count:
        raise ValueError("factory_wave_work_count_mismatch")
    started = time.perf_counter()
    jobs: list[VideoFactoryJobV1] = []
    with ThreadPoolExecutor(max_workers=budget.max_concurrent_jobs) as pool:
        futures = {
            pool.submit(
                render_one,
                case,
                wave=wave,
                variant=variant,
                ordinal=job_ordinal,
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
                max_attempts=budget.max_attempts_per_job,
            ): job_ordinal
            for case, variant, job_ordinal in work
        }
        for future in as_completed(futures):
            job = future.result()
            jobs.append(job)
            print(json.dumps({"jobId": job.job_id, "status": job.status}))
    jobs.sort(key=lambda item: item.ordinal)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    technical = all(item.status == "succeeded" and item.technical_qc_passed for item in jobs)
    wave_id = "clicko-pilot-12-v1" if wave == "pilot_12" else "clicko-calibration-24-v1"
    blockers = ["human_review_pending", "infrastructure_cost_not_metered"]
    if not technical:
        blockers.append("technical_qc_incomplete")
    return VideoFactoryWaveEvidenceV1(
        wave_id=wave_id,
        wave=wave,
        source_casebook_digest_sha256=creative_casebook_digest(casebook),
        prerequisite_wave_ids=[] if wave == "pilot_12" else ["clicko-pilot-12-v1"],
        budget=budget,
        jobs=jobs,
        direct_cost_usd=round(sum(item.direct_cost_usd for item in jobs), 6),
        wall_time_milliseconds=elapsed_ms,
        technical_eligible=technical,
        promotion_eligible=False,
        blockers=blockers,
        started_at=FIXED_STARTED_AT,
        completed_at=datetime.now(UTC),
    )


def blocked_scale_wave(casebook: CreativePilotCasebookV1) -> VideoFactoryWaveEvidenceV1:
    jobs = []
    for ordinal in range(1, 65):
        case = casebook.cases[(ordinal - 1) % len(casebook.cases)]
        jobs.append(
            VideoFactoryJobV1(
                job_id=f"scale_64-{ordinal:03d}",
                wave="scale_64",
                ordinal=ordinal,
                case_id=case.case_id,
                family=case.family,
                recipe_id=case.recipe.recipe_id,
                recipe_digest_sha256=format_recipe_digest(case.recipe),
                idempotency_key=f"factory-scale_64-{ordinal:03d}-{case.case_id}",
                capability="motion_browser" if case.family == "motion_visual_essay" else "media_cpu",
                provider=(
                    "hyperframes.cli"
                    if case.family == "motion_visual_essay"
                    else "builtin.ffmpeg-calibration-v1"
                ),
                provider_version="not-dispatched-gate-v1",
                status="blocked_by_gate",
                attempts=0,
                max_attempts=3,
                direct_cost_usd=0,
                rollback_recipe_id=case.recipe.recipe_id,
                rollback_provider=(
                    "hyperframes.cli"
                    if case.family == "motion_visual_essay"
                    else "builtin.ffmpeg-calibration-v1"
                ),
                blockers=["pilot_human_approval_required", "calibration_human_approval_required"],
            )
        )
    return VideoFactoryWaveEvidenceV1(
        wave_id="clicko-scale-64-v1",
        wave="scale_64",
        source_casebook_digest_sha256=creative_casebook_digest(casebook),
        prerequisite_wave_ids=["clicko-pilot-12-v1", "clicko-calibration-24-v1"],
        budget=VideoFactoryBudgetV1(
            max_direct_cost_usd=64,
            max_wall_time_seconds=86_400,
            max_concurrent_jobs=4,
            rate_limit_jobs_per_minute=30,
            max_attempts_per_job=3,
        ),
        jobs=jobs,
        direct_cost_usd=0,
        wall_time_milliseconds=0,
        technical_eligible=False,
        promotion_eligible=False,
        blockers=["pilot_human_approval_required", "calibration_human_approval_required"],
        started_at=FIXED_STARTED_AT,
        completed_at=FIXED_STARTED_AT,
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    global OUTPUT_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--casebook", type=Path, default=CASEBOOK_PATH)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    if not shutil.which(args.ffmpeg) or not shutil.which(args.ffprobe):
        raise SystemExit("ffmpeg_and_ffprobe_required")
    casebook = CreativePilotCasebookV1.model_validate_json(
        args.casebook.read_text(encoding="utf-8")
    )
    OUTPUT_ROOT = args.output_root.resolve()
    pilot = execute_wave(
        casebook,
        wave="pilot_12",
        variants=(0,),
        count=12,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
    )
    calibration = execute_wave(
        casebook,
        wave="calibration_24",
        variants=(1, 2),
        count=24,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
    )
    scale = blocked_scale_wave(casebook)
    program = VideoFactoryProgramEvidenceV1(
        program_id="clicko-video-factory-100-v1",
        pilot=pilot,
        calibration=calibration,
        scale=scale,
        produced_artifact_count=36,
        human_approved_count=0,
        completed=False,
        blockers=[
            "36_human_reviews_pending",
            "scale_64_not_dispatched_by_hard_gate",
            "external_publication_not_authorized",
        ],
        evaluated_at=datetime.now(UTC),
    )
    write_json(OUTPUT_ROOT / "pilot-12-manifest.json", pilot.model_dump(mode="json", by_alias=True))
    write_json(
        OUTPUT_ROOT / "calibration-24-manifest.json",
        calibration.model_dump(mode="json", by_alias=True),
    )
    write_json(OUTPUT_ROOT / "scale-64-manifest.json", scale.model_dump(mode="json", by_alias=True))
    write_json(OUTPUT_ROOT / "program-manifest.json", program.model_dump(mode="json", by_alias=True))
    print(
        json.dumps(
            {
                "produced": program.produced_artifact_count,
                "humanApproved": program.human_approved_count,
                "scaleBlocked": len(scale.jobs),
                "programCompleted": program.completed,
            }
        )
    )


if __name__ == "__main__":
    main()
