from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.speech_assets import (  # noqa: E402
    ESPEAK_ALLOWED_RUNTIME_PREFIXES,
    EspeakRuntimeAssetFileV1,
    EspeakRuntimeManifestV1,
    espeak_runtime_manifest_digest,
    verify_espeak_runtime,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _attestation(runtime_root: Path, relative: str) -> str:
    try:
        value = (runtime_root / relative).read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ValueError(f"espeak_runtime_build_attestation_unreadable:{relative}") from error
    if not value:
        raise ValueError(f"espeak_runtime_build_attestation_empty:{relative}")
    return value


def build_manifest(
    runtime_root: Path,
    *,
    build_recipe: Path,
    loader_wheel_digest_sha256: str,
    bundled_espeak_revision: str,
    generated_at: datetime,
) -> EspeakRuntimeManifestV1:
    files = []
    for source in sorted(runtime_root.rglob("*")):
        if source.is_symlink():
            raise ValueError("espeak_runtime_symlinks_forbidden")
        if not source.is_file():
            continue
        relative = source.relative_to(runtime_root).as_posix()
        if not relative.startswith(ESPEAK_ALLOWED_RUNTIME_PREFIXES):
            raise ValueError(f"espeak_runtime_unapproved_path:{relative}")
        files.append(
            EspeakRuntimeAssetFileV1(
                relative_path=relative,
                size_bytes=source.stat().st_size,
                checksum_sha256=_sha256(source),
            )
        )
    manifest = EspeakRuntimeManifestV1(
        source_revision=_attestation(runtime_root, "build/source-revision.txt"),
        generated_at=generated_at,
        builder_image_digest=_attestation(runtime_root, "build/base-image-digest.txt"),
        compiler=_attestation(runtime_root, "build/compiler.txt"),
        cmake_version=_attestation(runtime_root, "build/cmake.txt"),
        build_flags=[
            item
            for item in _attestation(runtime_root, "build/flags.txt").splitlines()
            if item
        ],
        build_recipe_digest_sha256=_sha256(build_recipe),
        loader_wheel_digest_sha256=loader_wheel_digest_sha256,
        bundled_espeak_revision=bundled_espeak_revision,
        files=files,
    )
    verify_espeak_runtime(manifest, runtime_root)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hash an exact Linux/AMD64 eSpeak replacement runtime."
    )
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--build-recipe", type=Path, required=True)
    parser.add_argument("--loader-wheel-digest", required=True)
    parser.add_argument("--bundled-espeak-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        raise SystemExit("espeak_runtime_manifest_requires_linux_amd64")
    manifest = build_manifest(
        args.runtime_root,
        build_recipe=args.build_recipe,
        loader_wheel_digest_sha256=args.loader_wheel_digest,
        bundled_espeak_revision=args.bundled_espeak_revision,
        generated_at=datetime.now(UTC),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        output.write(manifest.model_dump_json(by_alias=True, indent=2))
        output.write("\n")
    print(
        json.dumps(
            {
                "fileCount": len(manifest.files),
                "manifestDigestSha256": espeak_runtime_manifest_digest(manifest),
                "sourceRevision": manifest.source_revision,
                "status": "espeak-runtime-manifest-verified",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
