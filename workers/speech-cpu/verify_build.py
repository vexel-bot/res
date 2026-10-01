from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_digest(label: str, actual: str, expected: str) -> None:
    if actual.lower() != expected.lower():
        raise SystemExit(f"{label}_digest_mismatch:{actual}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--requirements-digest", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-digest", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-digest", required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.backend))
    from app.domain.studios.benchmarking import (  # noqa: PLC0415
        BenchmarkPolicyV1,
        benchmark_policy_digest,
    )
    from app.services.studios.worker_runtime import (  # noqa: PLC0415
        load_worker_manifest,
        manifest_digest,
    )

    manifest = load_worker_manifest(args.manifest)
    if manifest.capability != "speech_cpu":
        raise SystemExit("speech_cpu_manifest_capability_required")
    if manifest.providers:
        raise SystemExit("preflight_provider_registry_must_be_empty")
    if manifest.job_types != ["stock_voice"]:
        raise SystemExit("speech_cpu_preflight_must_only_reserve_stock_voice")
    _require_digest("worker_manifest", manifest_digest(manifest), args.manifest_digest)

    policy = BenchmarkPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    if policy.capability != "stock_voice" or policy.locale != "pt-BR":
        raise SystemExit("speech_cpu_preflight_policy_mismatch")
    if policy.corpus.minimum_subjects != 0 or policy.corpus.raw_biometric_data_allowed_in_repository:
        raise SystemExit("speech_cpu_preflight_requires_synthetic_only_policy")
    _require_digest("benchmark_policy", benchmark_policy_digest(policy), args.policy_digest)
    _require_digest("backend_requirements", _sha256(args.requirements), args.requirements_digest)

    print(
        json.dumps(
            {
                "capability": manifest.capability,
                "policy": policy.suite_id,
                "providers": manifest.providers,
                "runtime": manifest.runtime_name,
                "status": "preflight-verified",
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
