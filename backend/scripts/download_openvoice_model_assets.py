"""Fetch only the frozen public OpenVoice/WavMark bytes, with streaming checksums."""

import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from app.domain.studios.speech_assets import (
    KokoroModelAssetManifestV1,
    OpenVoiceModelAssetManifestV1,
    verify_kokoro_model_snapshot,
    verify_openvoice_model_assets,
)


def materialize_kokoro(manifest, source_repository, target_repository):
    """Flatten only verified public model bytes; never change the original HF cache."""
    if target_repository.is_symlink():
        raise ValueError("kokoro_materialization_symlink_forbidden")
    source = source_repository / "snapshots" / manifest.source_revision
    digest = verify_kokoro_model_snapshot(manifest, source)
    target = target_repository / "snapshots" / manifest.source_revision
    for entry in manifest.files:
        destination = target / entry.relative_path
        if any(parent.is_symlink() for parent in (destination, *destination.parents)):
            raise ValueError("kokoro_materialization_symlink_forbidden")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            with tempfile.TemporaryDirectory(prefix="clicko-materialize-", dir=destination.parent) as temporary:
                partial = Path(temporary) / "asset.partial"
                shutil.copyfile(source / entry.relative_path, partial, follow_symlinks=True)
                partial.replace(destination)
    reference = target_repository / "refs/main"
    reference.parent.mkdir(parents=True, exist_ok=True)
    if any(parent.is_symlink() for parent in (reference, *reference.parents)) or (
        reference.exists() and reference.read_text().strip() != manifest.source_revision
    ):
        raise ValueError("kokoro_materialization_revision_mismatch")
    if not reference.exists():
        reference.write_text(manifest.source_revision + "\n", encoding="utf-8")
    if any(item.is_symlink() for item in target.rglob("*")):
        raise ValueError("kokoro_materialization_symlink_forbidden")
    if verify_kokoro_model_snapshot(manifest, target) != digest:
        raise ValueError("kokoro_materialization_digest_mismatch")
    return digest


def download(manifest, root):
    if root.is_symlink():
        raise ValueError("openvoice_download_symlink_forbidden")
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    for entry in manifest.files:
        destination = root / entry.runtime_path
        if any(parent.is_symlink() for parent in (destination, *destination.parents)):
            raise ValueError("openvoice_download_symlink_forbidden")
        if destination.exists():
            if destination.stat().st_size != entry.size_bytes:
                raise ValueError("existing_openvoice_asset_size_mismatch")
            with destination.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            if digest != entry.checksum_sha256:
                raise ValueError("existing_openvoice_asset_checksum_mismatch")
            print(f"verified existing: {entry.runtime_path}", flush=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        url = (
            f"https://huggingface.co/{entry.source_repository_id}/resolve/"
            f"{entry.source_revision}/{quote(entry.source_path, safe='/')}"
        )
        with tempfile.TemporaryDirectory(prefix="clicko-download-", dir=destination.parent) as temporary:
            partial = Path(temporary) / "asset.partial"
            digest, size = hashlib.sha256(), 0
            with urlopen(url, timeout=60) as response, partial.open("xb") as target:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > entry.size_bytes:
                        raise ValueError("downloaded_openvoice_asset_too_large")
                    digest.update(chunk)
                    target.write(chunk)
            if size != entry.size_bytes or digest.hexdigest() != entry.checksum_sha256:
                raise ValueError("downloaded_openvoice_asset_integrity_mismatch")
            partial.replace(destination)
        print(f"downloaded and verified: {entry.runtime_path} ({size} bytes)", flush=True)
    return verify_openvoice_model_assets(manifest, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--kokoro-manifest", type=Path)
    parser.add_argument("--kokoro-source-repository", type=Path)
    parser.add_argument("--kokoro-target-repository", type=Path)
    args = parser.parse_args()
    if not args.asset_root.is_absolute():
        parser.error("asset-root must be an absolute private path")
    manifest = OpenVoiceModelAssetManifestV1.model_validate_json(args.manifest.read_text(encoding="utf-8"))
    print("manifest verified: " + download(manifest, args.asset_root))
    kokoro_args = (args.kokoro_manifest, args.kokoro_source_repository, args.kokoro_target_repository)
    if any(kokoro_args):
        if not all(kokoro_args) or not all(path.is_absolute() for path in kokoro_args[1:]):
            parser.error("provide all three Kokoro arguments with absolute source and target paths")
        kokoro = KokoroModelAssetManifestV1.model_validate_json(args.kokoro_manifest.read_text(encoding="utf-8"))
        print(
            "regular Kokoro files verified: "
            + materialize_kokoro(kokoro, args.kokoro_source_repository, args.kokoro_target_repository)
        )


if __name__ == "__main__":
    main()
