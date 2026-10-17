from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"acoustic_qualification_input_unreadable:{path}") from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Recompute an acoustic detector qualification and optionally issue a signed promotion "
            "receipt. This command never changes the provider registry."
        )
    )
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--evaluated-at", type=str)
    parser.add_argument("--receipt-output", type=Path)
    parser.add_argument("--signer-key-id", type=str)
    parser.add_argument(
        "--secret-env",
        default="STUDIO_ACOUSTIC_PROMOTION_HMAC_SECRET",
        help="environment variable containing the signing secret; the secret is never printed",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(args.backend.resolve()))
    from app.domain.studios.acoustic_qualification import (  # noqa: PLC0415
        AcousticCorpusManifestV1,
        AcousticQualificationPolicyV1,
        AcousticQualificationRunV1,
        evaluate_acoustic_qualification,
        sign_acoustic_promotion_receipt,
    )

    policy = AcousticQualificationPolicyV1.model_validate(_json(args.policy))
    corpus = AcousticCorpusManifestV1.model_validate(_json(args.corpus))
    run = AcousticQualificationRunV1.model_validate(_json(args.run))
    evaluated_at = (
        datetime.fromisoformat(args.evaluated_at.replace("Z", "+00:00")) if args.evaluated_at else datetime.now(UTC)
    )
    if evaluated_at.tzinfo is None:
        raise SystemExit("evaluated_at_requires_timezone")
    assessment = evaluate_acoustic_qualification(
        policy,
        corpus,
        run,
        asset_root=args.asset_root,
        evaluated_at=evaluated_at,
    )
    print(assessment.model_dump_json(by_alias=True, exclude_none=True, indent=2))
    if assessment.decision == "failed":
        return 2
    if assessment.decision == "incomplete":
        return 3
    if args.receipt_output:
        if not args.signer_key_id:
            raise SystemExit("signer_key_id_required_for_receipt")
        secret = os.getenv(args.secret_env, "")
        if not secret:
            raise SystemExit(f"acoustic_promotion_secret_missing:{args.secret_env}")
        receipt = sign_acoustic_promotion_receipt(
            assessment,
            secret=secret,
            signer_key_id=args.signer_key_id,
        )
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_output.write_text(
            receipt.model_dump_json(by_alias=True, exclude_none=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
