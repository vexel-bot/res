"""Materialize frozen self-hosted evaluation assets with fail-closed checks.

The output directory is intentionally external to the repository's tracked
files. Downloading weights does not activate any provider or authorize use of
biometric inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CHUNK_SIZE = 8 * 1024 * 1024
ALLOWED_SOURCE_HOSTS = {"github.com", "huggingface.co"}
MIN_FREE_RESERVE_BYTES = 4 * 1024**3


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_entry(entry: dict[str, Any]) -> None:
    from urllib.parse import urlparse

    destination = Path(entry["destination"])
    if destination.is_absolute() or ".." in destination.parts:
        raise ValueError(f"unsafe_destination:{destination}")
    host = (urlparse(entry["sourceUrl"]).hostname or "").lower()
    if host not in ALLOWED_SOURCE_HOSTS:
        raise ValueError(f"source_host_not_allowed:{host}")
    expected_hash = entry["sha256"]
    if len(expected_hash) != 64 or any(char not in "0123456789abcdef" for char in expected_hash):
        raise ValueError(f"invalid_sha256:{destination}")
    if int(entry["sizeBytes"]) <= 0:
        raise ValueError(f"invalid_size:{destination}")


def _download(entry: dict[str, Any], target: Path, retries: int) -> dict[str, Any]:
    expected_size = int(entry["sizeBytes"])
    expected_hash = entry["sha256"]
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{target.name}.part")

    if target.exists():
        actual_size = target.stat().st_size
        actual_hash = _sha256(target)
        if actual_size == expected_size and actual_hash == expected_hash:
            return {"path": str(target), "sizeBytes": actual_size, "sha256": actual_hash, "status": "already_verified"}
        raise RuntimeError(f"existing_asset_mismatch:{target}:{actual_size}:{actual_hash}")

    curl = shutil.which("curl.exe") or shutil.which("curl")
    if curl:
        command = [
            curl,
            "--location",
            "--fail",
            "--retry",
            str(retries),
            "--retry-all-errors",
            "--connect-timeout",
            "30",
            "--continue-at",
            "-",
            "--output",
            str(partial),
            entry["sourceUrl"],
        ]
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"curl_download_failed:{target}:{completed.returncode}")
        actual_size = partial.stat().st_size
        if actual_size != expected_size:
            raise RuntimeError(f"download_size_mismatch:{target}:{actual_size}:{expected_size}")
        actual_hash = _sha256(partial)
        if actual_hash != expected_hash:
            raise RuntimeError(f"download_sha256_mismatch:{target}:{actual_hash}:{expected_hash}")
        os.replace(partial, target)
        return {"path": str(target), "sizeBytes": actual_size, "sha256": actual_hash, "status": "downloaded_verified"}

    for attempt in range(1, retries + 1):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > expected_size:
            raise RuntimeError(f"partial_asset_too_large:{partial}:{offset}")
        headers = {"User-Agent": "Clicko-Artifact-Materializer/1.0"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = Request(entry["sourceUrl"], headers=headers)
        try:
            with urlopen(request, timeout=120) as response:
                status = getattr(response, "status", 200)
                if offset and status != 206:
                    partial.unlink(missing_ok=True)
                    offset = 0
                mode = "ab" if offset and status == 206 else "wb"
                with partial.open(mode) as handle:
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        handle.write(chunk)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if attempt == retries:
                raise RuntimeError(f"download_failed:{target}:{attempt}:{exc}") from exc
            time.sleep(min(2**attempt, 10))
            continue

        actual_size = partial.stat().st_size
        if actual_size != expected_size:
            if attempt == retries:
                raise RuntimeError(f"download_size_mismatch:{target}:{actual_size}:{expected_size}")
            time.sleep(min(2**attempt, 10))
            continue
        actual_hash = _sha256(partial)
        if actual_hash != expected_hash:
            raise RuntimeError(f"download_sha256_mismatch:{target}:{actual_hash}:{expected_hash}")
        os.replace(partial, target)
        return {"path": str(target), "sizeBytes": actual_size, "sha256": actual_hash, "status": "downloaded_verified"}

    raise AssertionError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--group", action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--retries", type=int, default=4)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != "clicko.self-hosted-model-assets.v1":
        raise SystemExit("unsupported_manifest_schema")
    selected: list[dict[str, Any]] = []
    for group_id in args.group:
        try:
            group = manifest["groups"][group_id]
        except KeyError as exc:
            raise SystemExit(f"unknown_group:{group_id}") from exc
        for entry in group["files"]:
            _validate_entry(entry)
            selected.append(entry)

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    missing_bytes = 0
    for entry in selected:
        target = (output_root / entry["destination"]).resolve()
        if output_root not in target.parents:
            raise SystemExit(f"destination_escaped_output_root:{target}")
        if not target.exists():
            partial_path = target.with_name(f"{target.name}.part")
            partial_size = partial_path.stat().st_size if partial_path.exists() else 0
            missing_bytes += max(0, int(entry["sizeBytes"]) - partial_size)

    free_bytes = shutil.disk_usage(output_root).free
    if free_bytes - missing_bytes < MIN_FREE_RESERVE_BYTES:
        raise SystemExit(
            "insufficient_disk_reserve:"
            f"free={free_bytes}:missing={missing_bytes}:reserve={MIN_FREE_RESERVE_BYTES}"
        )

    if args.check_only:
        report = {
            "status": "preflight_passed",
            "groups": args.group,
            "assetCount": len(selected),
            "missingBytes": missing_bytes,
            "freeBytes": free_bytes,
            "reserveBytes": MIN_FREE_RESERVE_BYTES,
        }
        print(json.dumps(report, sort_keys=True))
        return 0

    results = []
    for entry in selected:
        results.append(_download(entry, output_root / entry["destination"], args.retries))
    print(json.dumps({"status": "assets_verified", "groups": args.group, "assets": results}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
