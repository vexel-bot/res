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
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--inventory-digest", required=True)
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
    from app.domain.studios.reality import (  # noqa: PLC0415
        PhysicalPlausibilityPolicyV1,
        physical_plausibility_policy_digest,
    )
    from app.services.studios.worker_runtime import (  # noqa: PLC0415
        load_worker_manifest,
        manifest_digest,
    )

    inventory = ArtifactInventoryV1.model_validate_json(args.inventory.read_text(encoding="utf-8"))
    if inventory.status not in {"review_required", "approved"}:
        raise SystemExit(f"artifact_inventory_not_buildable:{inventory.status}")
    _require_digest(
        "artifact_inventory",
        artifact_inventory_digest(inventory),
        args.inventory_digest,
    )

    manifest = load_worker_manifest(args.manifest)
    if manifest.providers:
        raise SystemExit("preflight_provider_registry_must_be_empty")
    _require_digest("worker_manifest", manifest_digest(manifest), args.manifest_digest)

    policy = PhysicalPlausibilityPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    _require_digest(
        "physical_policy",
        physical_plausibility_policy_digest(policy),
        args.policy_digest,
    )
    _require_digest("requirements_lock", _sha256(args.lock), args.lock_digest)

    print(
        json.dumps(
            {
                "inventoryStatus": inventory.status,
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
