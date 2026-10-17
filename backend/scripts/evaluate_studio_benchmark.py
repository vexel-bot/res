from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.benchmarking import (  # noqa: E402
    BenchmarkCorpusManifestV1,
    BenchmarkEvidenceBundleV1,
    BenchmarkLicenseManifestV1,
    BenchmarkPolicyV1,
    BenchmarkRunV1,
    evaluate_benchmark_run,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a Clicko Studio benchmark run against a frozen policy.")
    parser.add_argument("policy", type=Path, help="Path to studio.benchmark-policy.v1 JSON")
    parser.add_argument("run", type=Path, help="Path to studio.benchmark-run.v1 JSON")
    parser.add_argument(
        "--corpus-manifest",
        required=True,
        type=Path,
        help="Private studio.benchmark-corpus-manifest.v1 JSON (asset references only)",
    )
    parser.add_argument(
        "--evidence-bundle",
        required=True,
        type=Path,
        help="Private studio.benchmark-evidence-bundle.v1 JSON",
    )
    parser.add_argument(
        "--license-manifest",
        required=True,
        type=Path,
        help="Audited studio.benchmark-license-manifest.v1 JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = BenchmarkPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    run = BenchmarkRunV1.model_validate_json(args.run.read_text(encoding="utf-8"))
    corpus_manifest = BenchmarkCorpusManifestV1.model_validate_json(
        args.corpus_manifest.read_text(encoding="utf-8")
    )
    evidence_bundle = BenchmarkEvidenceBundleV1.model_validate_json(
        args.evidence_bundle.read_text(encoding="utf-8")
    )
    license_manifest = BenchmarkLicenseManifestV1.model_validate_json(
        args.license_manifest.read_text(encoding="utf-8")
    )
    result = evaluate_benchmark_run(
        policy,
        run,
        corpus_manifest=corpus_manifest,
        evidence_bundle=evidence_bundle,
        license_manifest=license_manifest,
    )
    print(result.model_dump_json(by_alias=True, indent=2))
    return {"passed": 0, "failed": 2, "incomplete": 3}[result.decision]


if __name__ == "__main__":
    raise SystemExit(main())
