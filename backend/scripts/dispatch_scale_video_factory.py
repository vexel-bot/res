from __future__ import annotations

import argparse
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.creative_autonomy import (
    CreativeAutonomyCaseV1,
    CreativePilotCasebookV1,
    creative_casebook_digest,
)
from app.domain.studios.video_factory import (
    FactoryInfrastructureCostPolicyV1,
    VideoFactoryProgramEvidenceV1,
    VideoFactoryWaveEvidenceV1,
    assert_factory_wave_dispatchable,
)
from scripts import execute_video_factory_waves as factory_executor

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
)
CASEBOOK_PATH = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "studios"
    / "creative"
    / "video-creative-pilot-casebook.v1.json"
)


class DispatchRateLimiter:
    def __init__(self, jobs_per_minute: int) -> None:
        self.minimum_interval_seconds = 60 / jobs_per_minute
        self.last_dispatch: float | None = None

    def acquire(self) -> None:
        now = time.monotonic()
        if self.last_dispatch is not None:
            remaining = self.minimum_interval_seconds - (now - self.last_dispatch)
            if remaining > 0:
                time.sleep(remaining)
        self.last_dispatch = time.monotonic()


def build_scale_work(
    casebook: CreativePilotCasebookV1,
) -> list[tuple[CreativeAutonomyCaseV1, int, int]]:
    return [
        (
            casebook.cases[(ordinal - 1) % len(casebook.cases)],
            (ordinal - 1) % 3,
            ordinal,
        )
        for ordinal in range(1, 65)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--program",
        type=Path,
        default=FACTORY_ROOT / "reviewed-program-manifest.json",
    )
    parser.add_argument("--casebook", type=Path, default=CASEBOOK_PATH)
    parser.add_argument(
        "--cost-policy",
        type=Path,
        default=FACTORY_ROOT / "infrastructure-cost-policy.json",
    )
    parser.add_argument("--output-root", type=Path, default=FACTORY_ROOT)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    if not shutil.which(args.ffmpeg) or not shutil.which(args.ffprobe):
        raise SystemExit("ffmpeg_and_ffprobe_required")
    program = VideoFactoryProgramEvidenceV1.model_validate_json(
        args.program.read_text(encoding="utf-8")
    )
    assert_factory_wave_dispatchable(program.scale, [program.pilot, program.calibration])
    cost_policy = FactoryInfrastructureCostPolicyV1.model_validate_json(
        args.cost_policy.read_text(encoding="utf-8")
    )
    casebook = CreativePilotCasebookV1.model_validate_json(
        args.casebook.read_text(encoding="utf-8")
    )
    if creative_casebook_digest(casebook) != program.scale.source_casebook_digest_sha256:
        raise ValueError("scale_casebook_digest_mismatch")
    factory_executor.OUTPUT_ROOT = args.output_root.resolve()
    budget = program.scale.budget
    started = time.perf_counter()
    jobs = []
    limiter = DispatchRateLimiter(budget.rate_limit_jobs_per_minute)
    with ThreadPoolExecutor(max_workers=budget.max_concurrent_jobs) as pool:
        futures = {}
        for case, variant, ordinal in build_scale_work(casebook):
            limiter.acquire()
            future = pool.submit(
                factory_executor.render_one,
                case,
                wave="scale_64",
                variant=variant,
                ordinal=ordinal,
                ffmpeg=args.ffmpeg,
                ffprobe=args.ffprobe,
                max_attempts=budget.max_attempts_per_job,
            )
            futures[future] = ordinal
        for future in as_completed(futures):
            job = future.result()
            jobs.append(job)
            print(json.dumps({"jobId": job.job_id, "status": job.status}))
    jobs.sort(key=lambda item: item.ordinal)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    technical = all(job.status == "succeeded" and job.technical_qc_passed for job in jobs)
    infrastructure_cost = round(
        sum((job.render_duration_milliseconds or 0) for job in jobs)
        / 3_600_000
        * cost_policy.cpu_hourly_cost_usd,
        6,
    )
    scale = VideoFactoryWaveEvidenceV1(
        wave_id=program.scale.wave_id,
        wave="scale_64",
        source_casebook_digest_sha256=program.scale.source_casebook_digest_sha256,
        prerequisite_wave_ids=program.scale.prerequisite_wave_ids,
        budget=budget,
        jobs=jobs,
        direct_cost_usd=round(sum(job.direct_cost_usd for job in jobs), 6),
        infrastructure_cost_usd=infrastructure_cost,
        cost_policy_id=cost_policy.policy_id,
        wall_time_milliseconds=elapsed_ms,
        technical_eligible=technical,
        promotion_eligible=False,
        blockers=["human_reviews_pending:64"] if technical else ["technical_qc_incomplete"],
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    payload = program.model_dump(mode="json", by_alias=True)
    payload.update(
        {
            "scale": scale.model_dump(mode="json", by_alias=True),
            "producedArtifactCount": 100 if technical else 36,
            "humanApprovedCount": program.human_approved_count,
            "completed": False,
            "blockers": scale.blockers,
            "evaluatedAt": datetime.now(UTC),
        }
    )
    updated = VideoFactoryProgramEvidenceV1.model_validate(payload)
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "scale-64-rendered-manifest.json").write_text(
        json.dumps(scale.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (args.output_root / "scale-rendered-program-manifest.json").write_text(
        json.dumps(updated.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "produced": updated.produced_artifact_count,
                "humanApproved": updated.human_approved_count,
                "scaleTechnicalEligible": scale.technical_eligible,
                "programCompleted": updated.completed,
            }
        )
    )


if __name__ == "__main__":
    main()
