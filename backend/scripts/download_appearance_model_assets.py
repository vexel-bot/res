"""Verify frozen public appearance assets; downloading requires --download."""

import argparse
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from app.domain.studios.appearance_image import AppearanceModelManifestV1, file_digest, verify_model_assets


def _safe(root, path):
    if (
        root.resolve() != root.absolute()
        or not path.resolve().is_relative_to(root.resolve())
        or any(item.is_symlink() for item in (path, *path.parents))
    ):
        raise ValueError("appearance_download_symlink_forbidden")


def download(manifest, root):
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("appearance_download_absolute_root_required")
    _safe(root, root)
    expected, missing = {entry.path for entry in manifest.files}, []
    if root.exists():
        for path in root.rglob("*"):
            _safe(root, path)
            if path.is_file() and path.relative_to(root).as_posix() not in expected:
                raise ValueError("appearance_model_unmanifested_file")
    for entry in manifest.files:
        path = root / entry.path
        _safe(root, path)
        if path.exists():
            if (
                not path.is_file()
                or path.stat().st_size != entry.size_bytes
                or file_digest(path) != entry.checksum_sha256
            ):
                raise ValueError("appearance_existing_asset_mismatch")
        else:
            missing.append(entry)
    existing_parent = root
    while not existing_parent.exists():
        existing_parent = existing_parent.parent
    if shutil.disk_usage(existing_parent).free < sum(entry.size_bytes for entry in missing) + 512 * 1024**2:
        raise ValueError("appearance_download_disk_space_insufficient")
    root.mkdir(parents=True, exist_ok=True)
    for entry in missing:
        target = root / entry.path
        _safe(root, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        url = (f"https://huggingface.co/{manifest.repository}/resolve/"
               f"{manifest.model_revision}/{quote(entry.path, safe='/')}")
        with tempfile.TemporaryDirectory(prefix="clicko-appearance-download-", dir=target.parent) as temporary:
            partial, digest, size = Path(temporary) / "asset.partial", hashlib.sha256(), 0
            with urlopen(url, timeout=60) as response, partial.open("xb") as output:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > entry.size_bytes:
                        raise ValueError("appearance_download_size_exceeded")
                    digest.update(chunk)
                    output.write(chunk)
            if size != entry.size_bytes or digest.hexdigest() != entry.checksum_sha256:
                raise ValueError("appearance_download_checksum_mismatch")
            # Publish complete bytes atomically, without overwriting another downloader.
            try:
                os.link(partial, target)
            except FileExistsError:
                if not target.is_file() or file_digest(target) != entry.checksum_sha256:
                    raise ValueError("appearance_download_destination_conflict") from None
        print(f"verified: {entry.path} ({entry.size_bytes} bytes)", flush=True)
    return verify_model_assets(manifest, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if not args.model_root.is_absolute():
        parser.error("model-root must be an absolute private directory")
    manifest = AppearanceModelManifestV1.model_validate_json(args.manifest.read_text(encoding="utf-8"))
    digest = download(manifest, args.model_root) if args.download else verify_model_assets(manifest, args.model_root)
    print("manifest verified: " + digest)


if __name__ == "__main__":
    main()
