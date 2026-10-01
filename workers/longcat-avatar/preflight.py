from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "model-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate(model_root: Path | None = None) -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    reasons = list(manifest["blockers"])
    evidence: dict[str, object] = {
        "platform": platform.system().lower(),
        "modelRootConfigured": model_root is not None,
        "workerImageDigest": os.getenv("LONGCAT_WORKER_IMAGE_DIGEST"),
    }
    if platform.system().lower() != "linux":
        reasons.append("linux_worker_required")
    if model_root is not None:
        missing: list[str] = []
        mismatches: list[str] = []
        for model in manifest["models"]:
            repository_root = model_root / model["repository"].split("/")[-1]
            for item in model["files"]:
                candidate = repository_root / item["path"]
                if not candidate.is_file():
                    missing.append(f"{model['repository']}:{item['path']}")
                elif candidate.stat().st_size != item["sizeBytes"] or sha256_file(candidate) != item["sha256"]:
                    mismatches.append(f"{model['repository']}:{item['path']}")
        evidence["missingArtifacts"] = missing
        evidence["checksumMismatches"] = mismatches
        if not missing:
            reasons = [reason for reason in reasons if reason != "weights_not_installed"]
        if mismatches:
            reasons.append("weight_checksum_mismatch")
    reasons = sorted(set(reasons))
    return {
        "schemaVersion": "studio.longcat-preflight.v1",
        "profileId": manifest["profileId"],
        "state": "unavailable" if reasons else "experimental",
        "usableNow": not reasons,
        "reasons": reasons,
        "evidence": evidence,
        "effectiveParameters": manifest["effectiveParameters"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.model_root), ensure_ascii=False, sort_keys=True))
