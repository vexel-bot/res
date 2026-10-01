"""Explicit model provisioning; inference never downloads model files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from preflight import CACHE, inspect
from profile_registry import get_profile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile_directory(profile_id: str) -> Path:
    return CACHE / "profiles" / profile_id


def repository_directory(profile_id: str, repository_id: str) -> Path:
    return profile_directory(profile_id) / repository_id.replace("/", "--")


def _inventory(profile_id: str, profile: dict) -> list[dict]:
    inventory = []
    for repository in profile.get("repositories", []):
        root = repository_directory(profile_id, repository["id"])
        for path in sorted(root.rglob("*")):
            if path.is_file() and ".cache" not in path.parts and path.name != "provision-receipt.json":
                inventory.append(
                    {
                        "repository": repository["id"],
                        "path": path.relative_to(root).as_posix(),
                        "sizeBytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                )
    return inventory


def _verify_artifacts(profile_id: str, profile: dict) -> tuple[list[str], list[str]]:
    missing, mismatched = [], []
    for repository in profile.get("repositories", []):
        root = repository_directory(profile_id, repository["id"])
        for artifact in repository.get("artifacts", []):
            path = root / artifact["path"]
            if not path.is_file():
                missing.append(f"{repository['id']}:{artifact['path']}")
            elif sha256(path) != artifact["sha256"]:
                mismatched.append(f"{repository['id']}:{artifact['path']}")
    return missing, mismatched


def status(profile_id: str) -> dict:
    profile = get_profile(profile_id)
    repositories = profile.get("repositories")
    if not repositories:
        return {"profileId": profile_id, "status": "legacy_unprovisioned", "missing": [], "mismatched": []}
    missing, mismatched = _verify_artifacts(profile_id, profile)
    receipt_path = profile_directory(profile_id) / "provision-receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else None
    except json.JSONDecodeError:
        receipt = None
    if receipt:
        expected_inventory = receipt.get("inventory", [])
        actual = _inventory(profile_id, profile)
        if actual != expected_inventory:
            mismatched.append("provisioned_file_inventory")
    else:
        missing.append("provision-receipt.json")
    return {
        "profileId": profile_id,
        "status": "ready" if not missing and not mismatched else "missing",
        "missing": missing,
        "mismatched": mismatched,
    }


def quick_status(profile_id: str) -> dict:
    """Cheap readiness probe; full checksums remain mandatory before inference."""
    profile = get_profile(profile_id)
    if not profile.get("repositories"):
        return {"profileId": profile_id, "status": "legacy_unprovisioned"}
    receipt_path = profile_directory(profile_id) / "provision-receipt.json"
    if not receipt_path.is_file():
        return {"profileId": profile_id, "status": "missing", "reason": "provision_receipt_missing"}
    for repository in profile["repositories"]:
        root = repository_directory(profile_id, repository["id"])
        for artifact in repository.get("artifacts", []):
            path = root / artifact["path"]
            if not path.is_file() or path.stat().st_size != int(artifact["sizeBytes"]):
                return {"profileId": profile_id, "status": "missing", "reason": "pinned_artifact_missing"}
        for pattern in repository.get("allowPatterns", []):
            if "*" not in pattern and not (root / pattern).is_file():
                return {"profileId": profile_id, "status": "missing", "reason": "required_config_missing"}
    return {"profileId": profile_id, "status": "ready", "verification": "quick_manifest_presence"}


def provision(profile_id: str) -> dict:
    admission = inspect(profile_id=profile_id, phase="install", check_environment=True)
    if admission["status"] != "admitted":
        return {"status": "blocked_resources", "preflight": admission, "modelDownloadStarted": False}
    profile = get_profile(profile_id)
    if not profile.get("repositories"):
        raise ValueError("legacy_profile_requires_migration_before_provision")
    controlled_hub = CACHE / "huggingface"
    controlled_hub.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(controlled_hub)
    os.environ["HF_HUB_CACHE"] = str(controlled_hub / "hub")
    os.environ["HF_XET_CACHE"] = str(controlled_hub / "xet")
    from huggingface_hub import snapshot_download

    roots = {}
    for repository in profile["repositories"]:
        target = repository_directory(profile_id, repository["id"])
        target.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=repository["id"],
            revision=repository["revision"],
            allow_patterns=repository["allowPatterns"],
            local_dir=target,
        )
        roots[repository["id"]] = str(target)
    missing, mismatched = _verify_artifacts(profile_id, profile)
    if missing or mismatched:
        raise ValueError("local_diffusion_model_checksum_mismatch")
    receipt = {
        "schemaVersion": "res.local-video-provision-receipt.v1",
        "status": "ready",
        "profileId": profile_id,
        "repositories": roots,
        "inventory": _inventory(profile_id, profile),
    }
    path = profile_directory(profile_id) / "provision-receipt.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    verified = status(profile_id)
    if verified["status"] != "ready":
        raise ValueError("local_diffusion_provision_receipt_mismatch")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("status", "provision"))
    parser.add_argument("--profile-id", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            status(args.profile_id) if args.action == "status" else provision(args.profile_id), separators=(",", ":")
        )
    )
