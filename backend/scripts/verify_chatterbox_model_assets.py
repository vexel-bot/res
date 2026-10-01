from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.domain.studios.speech_assets import (
    ChatterboxModelAssetManifestV1,
    chatterbox_model_asset_manifest_digest,
    verify_chatterbox_model_assets,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the frozen Chatterbox V3 and pt-BR model asset manifest."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--asset-root",
        type=Path,
        help="Optional assembled offline asset root; network access is never used.",
    )
    args = parser.parse_args()
    manifest = ChatterboxModelAssetManifestV1.model_validate_json(
        args.manifest.read_text(encoding="utf-8")
    )
    digest = (
        verify_chatterbox_model_assets(manifest, args.asset_root)
        if args.asset_root is not None
        else chatterbox_model_asset_manifest_digest(manifest)
    )
    print(
        json.dumps(
            {
                "schemaVersion": "clicko.chatterbox-model-assets-verification.v1",
                "manifestDigestSha256": digest,
                "assetBytesVerified": args.asset_root is not None,
                "candidateIds": sorted(item.candidate_id for item in manifest.variants),
                "status": (
                    "asset-bytes-verified"
                    if args.asset_root is not None
                    else "metadata-lock-verified"
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
