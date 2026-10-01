from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.speech_assets import (  # noqa: E402
    KOKORO_REQUIRED_MODEL_FILES,
    KokoroModelAssetFileV1,
    KokoroModelAssetManifestV1,
    kokoro_model_asset_manifest_digest,
    verify_kokoro_model_snapshot,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    snapshot: Path,
    *,
    revision: str,
    generated_at: datetime,
) -> KokoroModelAssetManifestV1:
    files = []
    for relative in sorted(KOKORO_REQUIRED_MODEL_FILES):
        source = snapshot / Path(*PurePosixPath(relative).parts)
        if not source.is_file():
            raise ValueError(f"kokoro_model_asset_missing:{relative}")
        files.append(
            KokoroModelAssetFileV1(
                relative_path=relative,
                size_bytes=source.stat().st_size,
                checksum_sha256=_sha256(source),
            )
        )
    model_card = snapshot / "README.md"
    if not model_card.is_file():
        raise ValueError("kokoro_model_card_missing")
    manifest = KokoroModelAssetManifestV1(
        source_revision=revision,
        generated_at=generated_at,
        model_card_digest_sha256=_sha256(model_card),
        files=files,
    )
    verify_kokoro_model_snapshot(manifest, snapshot)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash the frozen Kokoro runtime assets.")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(
        args.snapshot,
        revision=args.revision,
        generated_at=datetime.now(UTC),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        manifest.model_dump_json(by_alias=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "fileCount": len(manifest.files),
                "manifestDigestSha256": kokoro_model_asset_manifest_digest(manifest),
                "revision": manifest.source_revision,
                "status": "kokoro-model-assets-verified",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
