from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ESPEAK_REQUIRED_RUNTIME_FILES = frozenset(
    {
        "build/base-image-digest.txt",
        "build/cmake.txt",
        "build/compiler.txt",
        "build/flags.txt",
        "build/source-revision.txt",
        "lib/libespeak-ng.so",
        "licenses/espeak-ng-COPYING",
        "share/espeak-ng-data/phondata",
        "share/espeak-ng-data/phonindex",
        "share/espeak-ng-data/phontab",
        "share/espeak-ng-data/pt_dict",
        "source/espeak-ng.tar.gz",
    }
)
ESPEAK_ALLOWED_RUNTIME_PREFIXES = (
    "build/",
    "lib/",
    "licenses/",
    "share/espeak-ng-data/",
    "source/",
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
REVISION_RE = re.compile(r"^[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class RuntimeAssetFile:
    relative_path: str
    size_bytes: int
    checksum_sha256: str


@dataclass(frozen=True)
class RuntimeManifest:
    source_revision: str
    files: tuple[RuntimeAssetFile, ...]
    canonical_payload: dict[str, Any]


def _require_string(
    payload: dict[str, Any], key: str, *, pattern: re.Pattern[str] | None = None
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"espeak_manifest_invalid_field:{key}")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ValueError(f"espeak_manifest_invalid_field:{key}")
    return value


def _parse_manifest(payload: dict[str, Any]) -> RuntimeManifest:
    if payload.get("schemaVersion") != "studio.espeak-runtime-assets.v1":
        raise ValueError("espeak_manifest_schema_version_invalid")
    if payload.get("repositoryId") != "espeak-ng/espeak-ng":
        raise ValueError("espeak_manifest_repository_invalid")
    if payload.get("platform") != "linux-amd64":
        raise ValueError("espeak_manifest_platform_invalid")
    if payload.get("replacementPerformed") is not True:
        raise ValueError("espeak_manifest_replacement_flag_invalid")

    source_revision = _require_string(payload, "sourceRevision", pattern=REVISION_RE)
    _require_string(payload, "generatedAt")
    builder_digest = _require_string(payload, "builderImageDigest")
    if not builder_digest.startswith("sha256:") or SHA256_RE.fullmatch(
        builder_digest.removeprefix("sha256:")
    ) is None:
        raise ValueError("espeak_manifest_invalid_field:builderImageDigest")
    for key in (
        "compiler",
        "cmakeVersion",
        "buildRecipeDigestSha256",
        "loaderWheelDigestSha256",
        "bundledEspeakRevision",
    ):
        value = _require_string(payload, key)
        if key.endswith("DigestSha256") and SHA256_RE.fullmatch(value) is None:
            raise ValueError(f"espeak_manifest_invalid_field:{key}")
        if key == "bundledEspeakRevision" and REVISION_RE.fullmatch(value) is None:
            raise ValueError(f"espeak_manifest_invalid_field:{key}")

    build_flags = payload.get("buildFlags")
    if (
        not isinstance(build_flags, list)
        or not 1 <= len(build_flags) <= 100
        or any(not isinstance(value, str) or not value for value in build_flags)
        or len(build_flags) != len(set(build_flags))
    ):
        raise ValueError("espeak_manifest_build_flags_invalid")

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or not 7 <= len(raw_files) <= 10_000:
        raise ValueError("espeak_manifest_files_invalid")
    files: list[RuntimeAssetFile] = []
    for raw in raw_files:
        if not isinstance(raw, dict):
            raise ValueError("espeak_manifest_file_invalid")
        relative_path = _require_string(raw, "relativePath")
        path = PurePosixPath(relative_path)
        if path.is_absolute() or ".." in path.parts or str(path) != relative_path:
            raise ValueError("espeak_manifest_file_path_invalid")
        if not relative_path.startswith(ESPEAK_ALLOWED_RUNTIME_PREFIXES):
            raise ValueError("espeak_manifest_file_path_unapproved")
        size_bytes = raw.get("sizeBytes")
        if (
            isinstance(size_bytes, bool)
            or not isinstance(size_bytes, int)
            or not 0 < size_bytes <= 2 * 1024**3
        ):
            raise ValueError("espeak_manifest_file_size_invalid")
        checksum = _require_string(raw, "checksumSha256", pattern=SHA256_RE).lower()
        files.append(RuntimeAssetFile(relative_path, size_bytes, checksum))
    paths = [entry.relative_path for entry in files]
    if len(paths) != len(set(paths)):
        raise ValueError("espeak_manifest_file_paths_not_unique")
    missing = sorted(ESPEAK_REQUIRED_RUNTIME_FILES - set(paths))
    if missing:
        raise ValueError(f"espeak_manifest_required_files_missing:{','.join(missing)}")
    return RuntimeManifest(source_revision, tuple(files), payload)


def _coerce_manifest(manifest: Any) -> RuntimeManifest:
    if isinstance(manifest, RuntimeManifest):
        return manifest
    if isinstance(manifest, dict):
        return _parse_manifest(manifest)
    model_dump = getattr(manifest, "model_dump", None)
    if callable(model_dump):
        return _parse_manifest(model_dump(mode="json", by_alias=True))
    raise TypeError("espeak_manifest_unsupported_type")


def manifest_digest(manifest: RuntimeManifest) -> str:
    canonical = json.dumps(
        manifest.canonical_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _target_mapping(manifest: RuntimeManifest) -> dict[str, tuple[int, str]]:
    mapping: dict[str, tuple[int, str]] = {}
    for entry in manifest.files:
        if entry.relative_path == "lib/libespeak-ng.so":
            target = "libespeak-ng.so"
        elif entry.relative_path.startswith("share/espeak-ng-data/"):
            target = entry.relative_path.removeprefix("share/")
        else:
            continue
        mapping[target] = (entry.size_bytes, entry.checksum_sha256.lower())
    return mapping


def verify_runtime(manifest: RuntimeManifest, runtime_root: Path) -> str:
    root = runtime_root.resolve()
    if not runtime_root.is_dir() or runtime_root.is_symlink():
        raise ValueError("espeak_runtime_root_missing_or_symlinked")
    disk_files: dict[str, Path] = {}
    for source in runtime_root.rglob("*"):
        if source.is_symlink():
            raise ValueError("espeak_runtime_symlinks_forbidden")
        if not source.is_file():
            continue
        if not source.resolve().is_relative_to(root):
            raise ValueError("espeak_runtime_file_escaped_root")
        relative = source.relative_to(runtime_root).as_posix()
        if not relative.startswith(ESPEAK_ALLOWED_RUNTIME_PREFIXES):
            raise ValueError(f"espeak_runtime_unapproved_path:{relative}")
        disk_files[relative] = source
    expected = {entry.relative_path: entry for entry in manifest.files}
    if set(disk_files) != set(expected):
        raise ValueError("espeak_runtime_file_set_mismatch")
    for relative, entry in expected.items():
        source = disk_files[relative]
        if source.stat().st_size != entry.size_bytes:
            raise ValueError(f"espeak_runtime_asset_size_mismatch:{relative}")
        if _sha256(source) != entry.checksum_sha256:
            raise ValueError(f"espeak_runtime_asset_checksum_mismatch:{relative}")
    return manifest_digest(manifest)


def install_replacement(
    manifest: Any,
    *,
    runtime_root: Path,
    loader_root: Path,
) -> str:
    parsed_manifest = _coerce_manifest(manifest)
    verified_digest = verify_runtime(parsed_manifest, runtime_root)
    resolved_loader = loader_root.resolve()
    if not loader_root.is_dir() or loader_root.is_symlink():
        raise ValueError("espeak_loader_root_missing_or_symlinked")
    old_libraries = sorted(loader_root.glob("libespeak-ng.so*"))
    old_data = loader_root / "espeak-ng-data"
    for path in old_libraries:
        if path.is_dir() or (path.is_symlink() and path.resolve().is_dir()):
            raise ValueError("espeak_loader_library_path_invalid")
        path.unlink(missing_ok=True)
    if old_data.exists():
        if old_data.is_symlink() or not old_data.is_dir():
            raise ValueError("espeak_loader_data_path_invalid")
        shutil.rmtree(old_data)

    source_library = runtime_root / "lib" / "libespeak-ng.so"
    destination_library = loader_root / "libespeak-ng.so"
    shutil.copy2(source_library, destination_library)
    shutil.copytree(runtime_root / "share" / "espeak-ng-data", old_data)

    expected = _target_mapping(parsed_manifest)
    observed: dict[str, Path] = {}
    for path in (destination_library, *sorted(old_data.rglob("*"))):
        if path.is_symlink():
            raise ValueError("espeak_loader_replacement_symlinks_forbidden")
        if not path.is_file():
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(resolved_loader):
            raise ValueError("espeak_loader_replacement_escaped_root")
        observed[path.relative_to(loader_root).as_posix()] = path
    if set(observed) != set(expected):
        raise ValueError("espeak_loader_replacement_file_set_mismatch")
    for relative, (size_bytes, checksum) in expected.items():
        destination = observed[relative]
        if destination.stat().st_size != size_bytes or _sha256(destination) != checksum:
            raise ValueError(f"espeak_loader_replacement_checksum_mismatch:{relative}")
    return verified_digest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replace espeakng-loader bundled bytes with a manifested runtime."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--loader-root", type=Path, required=True)
    parser.add_argument("--expected-manifest-digest")
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("espeak_manifest_root_invalid")
    manifest = _parse_manifest(payload)
    observed_digest = verify_runtime(manifest, args.runtime_root)
    if (
        args.expected_manifest_digest is not None
        and observed_digest.lower() != args.expected_manifest_digest.lower()
    ):
        raise ValueError("espeak_manifest_digest_mismatch")
    digest = install_replacement(
        manifest,
        runtime_root=args.runtime_root,
        loader_root=args.loader_root,
    )
    print(
        json.dumps(
            {
                "manifestDigestSha256": digest,
                "sourceRevision": manifest.source_revision,
                "status": "espeak-loader-runtime-replaced",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
