from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"promotion_input_unreadable:{path}") from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a provider promotion evidence bundle without changing the worker registry."
        )
    )
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evaluated-at", type=str)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="return success for an incomplete review; binding failures still fail",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(args.backend))
    from app.domain.studios.artifacts import (  # noqa: PLC0415
        ArtifactInventoryV1,
        ProviderCandidateManifestV1,
        ProviderPromotionEvidenceV1,
        evaluate_provider_promotion_gate,
    )
    from app.services.studios.worker_runtime import load_worker_manifest  # noqa: PLC0415

    candidate = ProviderCandidateManifestV1.model_validate(_load_json(args.candidate))
    inventory = ArtifactInventoryV1.model_validate(_load_json(args.inventory))
    evidence = ProviderPromotionEvidenceV1.model_validate(_load_json(args.evidence))
    worker_manifest = load_worker_manifest(args.manifest)
    evaluated_at = (
        datetime.fromisoformat(args.evaluated_at.replace("Z", "+00:00"))
        if args.evaluated_at
        else datetime.now(UTC)
    )
    if evaluated_at.tzinfo is None:
        raise SystemExit("evaluated_at_requires_timezone")

    result = evaluate_provider_promotion_gate(
        candidate,
        inventory,
        evidence,
        worker_manifest,
        evaluated_at=evaluated_at,
    )
    print(result.model_dump_json(by_alias=True, exclude_none=True, indent=2))

    if result.decision == "blocked":
        return 2
    if result.decision == "incomplete" and not args.allow_incomplete:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
