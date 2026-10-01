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
    parser.add_argument("--qwen-inventory", type=Path, required=True)
    parser.add_argument("--qwen-inventory-digest", required=True)
    parser.add_argument("--kimi-inventory", type=Path, required=True)
    parser.add_argument("--kimi-inventory-digest", required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--lock-digest", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-digest", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-digest", required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.backend))
    from app.domain.studios.artifacts import (  # noqa: PLC0415
        ArtifactInventoryV1,
        artifact_inventory_digest,
    )
    from app.domain.studios.benchmarking import (  # noqa: PLC0415
        BenchmarkPolicyV1,
        benchmark_policy_digest,
    )
    from app.services.studios.worker_runtime import (  # noqa: PLC0415
        load_worker_manifest,
        manifest_digest,
    )

    policy = BenchmarkPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    _require_digest("planning_policy", benchmark_policy_digest(policy), args.policy_digest)
    if policy.status != "frozen":
        raise SystemExit(f"planning_policy_not_frozen:{policy.status}")
    if any(item.execution_capability != "llm_gpu" for item in policy.candidates):
        raise SystemExit("planning_policy_wrong_execution_capability")

    inventory_inputs = (
        ("qwen_inventory", args.qwen_inventory, args.qwen_inventory_digest),
        ("kimi_inventory", args.kimi_inventory, args.kimi_inventory_digest),
    )
    inventory_statuses: dict[str, str] = {}
    for label, path, expected_digest in inventory_inputs:
        inventory = ArtifactInventoryV1.model_validate_json(path.read_text(encoding="utf-8"))
        _require_digest(label, artifact_inventory_digest(inventory), expected_digest)
        if inventory.status != "incomplete":
            raise SystemExit(f"{label}_must_remain_incomplete:{inventory.status}")
        if inventory.policy_digests_sha256 != [args.policy_digest.lower()]:
            raise SystemExit(f"{label}_policy_binding_mismatch")
        inventory_statuses[label] = inventory.status

    manifest = load_worker_manifest(args.manifest)
    if manifest.capability != "llm_gpu":
        raise SystemExit(f"preflight_capability_mismatch:{manifest.capability}")
    if manifest.providers:
        raise SystemExit("preflight_provider_registry_must_be_empty")
    if manifest.job_types != ["planning_copy"]:
        raise SystemExit("preflight_job_types_mismatch")
    _require_digest("worker_manifest", manifest_digest(manifest), args.manifest_digest)
    _require_digest("requirements_lock", _sha256(args.lock), args.lock_digest)

    print(
        json.dumps(
            {
                "inventories": inventory_statuses,
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
