from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.ugc_acceptance import (  # noqa: E402
    UgcAdAcceptanceCaseResultV1,
    UgcAdAcceptanceRunV1,
    UgcCriterionResultV1,
)
from app.providers.studios.openai_compatible_planning import (  # noqa: E402
    OpenAICompatiblePlanningCopyProvider,
)
from app.services.studios.ugc_acceptance import (  # noqa: E402
    automated_preflight_status,
    build_ugc_revision_request,
    canonical_json_digest,
    evaluate_planning_copy,
    load_ugc_acceptance_casebook,
    render_ad_kit,
    sha256_file,
    standard_capability_gates,
    verify_ad_kit,
    weighted_score,
)


def _env_value(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, raw = stripped.split("=", 1)
        if name.strip() == key:
            return raw.strip().strip('"').strip("'")
    return None


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute the frozen ten-ad UGC creative acceptance suite.")
    parser.add_argument(
        "--casebook",
        type=Path,
        default=REPOSITORY_ROOT / "benchmarks/studios/ugc/ugc-ad-creative-acceptance-casebook.v1.json",
    )
    parser.add_argument("--base-url", default=os.getenv("CLICKO_QWEN_BASE_URL", "http://127.0.0.1:18080"))
    parser.add_argument("--model", default="clicko-qwen3-4b-q4-k-m")
    parser.add_argument("--model-revision", default="bc640142c66e1fdd12af0bd68f40445458f3869b")
    parser.add_argument("--api-key", default=None, help="Prefer .env:AI_API_KEY; never commit this value.")
    parser.add_argument("--max-output-tokens", type=int, default=1800)
    parser.add_argument("--timeout-seconds", type=float, default=240)
    parser.add_argument("--output-root", type=Path, default=REPOSITORY_ROOT / "artifacts/validation/ugc-ad-acceptance")
    parser.add_argument("--case", action="append", dest="case_ids", default=[])
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--retry-report",
        type=Path,
        default=None,
        help="Replace exactly one failed case in a previous canonical run, retaining a retry receipt.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    casebook = load_ugc_acceptance_casebook(args.casebook)
    selected = [case for case in casebook.cases if not args.case_ids or case.case_id in args.case_ids]
    if len(selected) != (len(args.case_ids) if args.case_ids else 10):
        raise SystemExit("Requested case id is absent or duplicated.")
    retry_run: UgcAdAcceptanceRunV1 | None = None
    if args.retry_report:
        if len(selected) != 1 or len(args.case_ids) != 1:
            raise SystemExit("A retry report requires exactly one --case.")
        retry_run = UgcAdAcceptanceRunV1.model_validate_json(args.retry_report.read_text(encoding="utf-8"))
        if retry_run.suite_id != casebook.suite_id or retry_run.casebook_digest_sha256 != canonical_json_digest(
            casebook
        ):
            raise SystemExit("Retry report does not bind to this frozen casebook.")
        if {item.case_id for item in retry_run.results} != {case.case_id for case in casebook.cases}:
            raise SystemExit("Retry report must contain exactly the ten frozen cases.")
        previous = next((item for item in retry_run.results if item.case_id == selected[0].case_id), None)
        if previous is None or previous.automated_status != "fail":
            raise SystemExit("Only an existing failed case can be retried.")
    if args.case_ids and len(selected) != 10 and not retry_run:
        print("Partial diagnostic run: no canonical ten-case run manifest will be emitted.")

    env_path = REPOSITORY_ROOT / ".env"
    api_key = args.api_key or os.getenv("AI_API_KEY") or _env_value(env_path, "AI_API_KEY")
    if not api_key:
        raise SystemExit("AI_API_KEY is required via process environment or repository .env.")

    started_at = datetime.now(UTC)
    run_id = (
        f"{retry_run.run_id}-retry-{started_at.strftime('%Y%m%dT%H%M%SZ')}"
        if retry_run
        else (args.run_id or started_at.strftime("ugc-acceptance-%Y%m%dT%H%M%SZ"))
    )
    if Path(run_id).name != run_id or run_id in {".", ".."}:
        raise SystemExit("run-id must be a single directory name.")
    output_root = args.output_root / run_id
    output_root.mkdir(parents=True, exist_ok=False)
    attempt_root = output_root
    results: list[UgcAdAcceptanceCaseResultV1] = []

    with OpenAICompatiblePlanningCopyProvider(
        base_url=args.base_url,
        model=args.model,
        model_revision=args.model_revision,
        api_key=api_key,
        max_output_tokens=args.max_output_tokens,
        timeout_seconds=args.timeout_seconds,
    ) as provider:
        for index, case in enumerate(selected, start=1):
            print(f"[{index}/{len(selected)}] {case.case_id}: planning", flush=True)
            result = None
            criteria: list[UgcCriterionResultV1] = []
            artifacts = []
            generated = False
            rendered = False
            failure: str | None = None
            try:
                request = (
                    build_ugc_revision_request(case, previous.planning_result)
                    if retry_run and previous.planning_result
                    else case.request
                )
                (output_root / f"{case.case_id}.request.json").write_text(
                    request.model_dump_json(by_alias=True, indent=2), encoding="utf-8"
                )
                result = provider.plan(request, lambda _progress: None, lambda: False)
                generated = True
                criteria = evaluate_planning_copy(case, result)
                print(f"[{index}/{len(selected)}] {case.case_id}: render kit", flush=True)
                artifacts = render_ad_kit(case, result, attempt_root / case.case_id)
                criteria.append(verify_ad_kit(case, artifacts, allowed_root=output_root))
                rendered = True
            except Exception as error:  # the manifest must retain a fail-closed receipt
                failure = f"{type(error).__name__}: {error}"
                criteria.append(
                    UgcCriterionResultV1(
                        criterion_id="pipeline_execution",
                        status="fail",
                        score=0,
                        weight=10,
                        evidence=[failure[:1000]],
                        notes=["Nenhum fallback autoral foi usado; o caso permanece falho e rastreável."],
                    )
                )
            score = weighted_score(criteria)
            automated_status = automated_preflight_status(criteria) if generated and rendered else "fail"
            results.append(
                UgcAdAcceptanceCaseResultV1(
                    case_id=case.case_id,
                    planning_result=result,
                    criteria=criteria,
                    artifacts=artifacts,
                    capability_gates=standard_capability_gates(generated=generated, rendered=rendered),
                    weighted_score=score,
                    automated_status=automated_status,
                )
            )
            print(
                f"[{index}/{len(selected)}] {case.case_id}: {automated_status} score={score:.3f}"
                + (f" error={failure}" if failure else ""),
                flush=True,
            )
            # Each completed case survives an interrupted batch, including diagnostic and failed runs.
            (output_root / f"{case.case_id}.result.json").write_text(
                results[-1].model_dump_json(by_alias=True, indent=2), encoding="utf-8"
            )

    if retry_run:
        replacements = {item.case_id: item for item in results}
        cases = {case.case_id: case for case in casebook.cases}
        results = []
        for item in retry_run.results:
            if item.case_id in replacements:
                results.append(replacements[item.case_id])
                continue
            case = cases[item.case_id]
            checks = evaluate_planning_copy(case, item.planning_result) if item.planning_result else []
            integrity = verify_ad_kit(case, item.artifacts, allowed_root=args.retry_report.parent)
            inherited_artifacts = []
            # A derived run is self-contained. Copy only verified bytes, never inherit old pass labels.
            if integrity.status == "pass":
                inherited_root = output_root / item.case_id
                inherited_root.mkdir(exist_ok=False)
                for artifact in item.artifacts:
                    source = Path(artifact.path).resolve()
                    target = inherited_root / source.name
                    if target.exists():
                        raise ValueError("Inherited artifacts must have distinct filenames.")
                    shutil.copyfile(source, target)
                    inherited_artifacts.append(artifact.model_copy(update={"path": str(target.resolve())}))
                integrity = verify_ad_kit(case, inherited_artifacts, allowed_root=output_root)
            checks.append(integrity)
            results.append(
                item.model_copy(
                    update={
                        "criteria": checks,
                        "artifacts": inherited_artifacts,
                        "weighted_score": weighted_score(checks),
                        "automated_status": automated_preflight_status(checks),
                    }
                )
            )
        retry_receipt = output_root / "retries" / f"retry-{started_at.strftime('%Y%m%dT%H%M%SZ')}.json"
        retry_receipt.parent.mkdir(parents=True, exist_ok=True)
        retry_receipt.write_text(
            json.dumps(
                {
                    "schemaVersion": "studio.ugc-ad-acceptance-retry-receipt.v1",
                    "runId": retry_run.run_id,
                    "caseId": selected[0].case_id,
                    "previousStatus": "fail",
                    "previousRunReportSha256": sha256_file(args.retry_report),
                    "previousResult": previous.model_dump(by_alias=True, mode="json"),
                    "replacementStatus": results[
                        [item.case_id for item in results].index(selected[0].case_id)
                    ].automated_status,
                    "attemptStartedAt": started_at.isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if len(results) == 10:
        completed_at = datetime.now(UTC)
        run = UgcAdAcceptanceRunV1(
            suite_id=casebook.suite_id,
            run_id=run_id,
            casebook_digest_sha256=canonical_json_digest(casebook),
            started_at=retry_run.started_at if retry_run else started_at,
            completed_at=completed_at,
            results=results,
        )
        report_path = output_root / "run-report.json"
        report_path.write_text(run.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
        summary = {
            "schemaVersion": "studio.ugc-ad-acceptance-summary.v1",
            "runId": run_id,
            "passed": sum(item.automated_status == "pass" for item in results),
            "failed": sum(item.automated_status == "fail" for item in results),
            "averageScore": round(sum(item.weighted_score for item in results) / len(results), 3),
            "productionAvatarClaimAllowed": False,
            "humanReviewRequired": True,
            "assessmentScope": "mechanical_preflight_only",
            "imageSynthesisExecuted": False,
            "ugcAdCompletionStatus": "blocked_missing_avatar_voice_and_editorial_review",
            "report": str(report_path.resolve()),
        }
        summary_path = output_root / "summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return 0 if summary["failed"] == 0 else 2
    return 0 if all(item.automated_status == "pass" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
