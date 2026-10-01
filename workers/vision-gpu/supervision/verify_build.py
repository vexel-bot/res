from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def main() -> int:
    args = _parse_args()
    _require_digest(args.lock, args.lock_digest, "lock")
    _require_digest(args.sbom, args.sbom_digest, "sbom")
    _require_digest(args.review, args.review_digest, "review")
    _require_digest(args.benchmark, args.benchmark_digest, "benchmark")
    _require_digest(args.manifest, args.manifest_digest, "manifest")
    lock_packages = _verify_lock(args.lock)
    sbom = json.loads(args.sbom.read_text(encoding="utf-8"))
    review = json.loads(args.review.read_text(encoding="utf-8"))
    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    adapter_source = args.adapter.read_text(encoding="utf-8")
    domain_source = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in args.domain.glob("*.py")
    )

    sbom_packages = {
        _canonical(item["name"]): item for item in sbom.get("packages", [])
    }
    review_packages = {
        item["canonicalName"]: item for item in review.get("packages", [])
    }
    if set(lock_packages) != set(sbom_packages) or set(lock_packages) != set(
        review_packages
    ):
        raise SystemExit("supervision_supply_chain_package_set_mismatch")
    for name, locked in lock_packages.items():
        checksums = {
            item["algorithm"]: item["checksumValue"]
            for item in sbom_packages[name].get("checksums", [])
        }
        if checksums.get("SHA256") != locked["sha256"]:
            raise SystemExit(f"supervision_sbom_hash_mismatch:{name}")
        if review_packages[name]["sha256"] != locked["sha256"]:
            raise SystemExit(f"supervision_review_hash_mismatch:{name}")
    if sbom.get("spdxVersion") != "SPDX-2.3":
        raise SystemExit("supervision_sbom_schema_mismatch")
    if review.get("status") != "review_required":
        raise SystemExit("supervision_license_review_must_remain_pending")
    if review.get("lockDigestSha256") != args.lock_digest:
        raise SystemExit("supervision_review_lock_binding_mismatch")
    if benchmark.get("technicalDecision") != "passed":
        raise SystemExit("supervision_benchmark_not_passed")
    if benchmark.get("activationDecision") != "incomplete":
        raise SystemExit("supervision_benchmark_activation_must_remain_incomplete")
    if not all(benchmark.get("checks", {}).values()):
        raise SystemExit("supervision_benchmark_check_failed")
    if manifest.get("providers") != []:
        raise SystemExit("supervision_worker_provider_must_remain_empty")
    if "ByteTrack" in adapter_source:
        raise SystemExit("supervision_bytetrack_is_prohibited")
    if any(item in adapter_source for item in ("requests.", "urllib", "http://", "https://")):
        raise SystemExit("supervision_adapter_egress_surface_detected")
    if "supervision" in domain_source or "personaplex" in domain_source:
        raise SystemExit("supervision_upstream_type_leaked_into_domain")
    if "supervision" not in lock_packages or lock_packages["supervision"]["version"] != "0.30.1":
        raise SystemExit("supervision_lock_pin_missing")
    print(
        json.dumps(
            {
                "benchmark": "passed",
                "licenseReview": "review_required",
                "packageCount": len(lock_packages),
                "providers": [],
                "status": "supervision-evaluation-preflight-verified",
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


def _verify_lock(path: Path) -> dict[str, dict[str, str]]:
    pattern = re.compile(
        r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^ ]+) "
        r"--hash=sha256:(?P<sha256>[0-9a-f]{64})$"
    )
    packages: dict[str, dict[str, str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.fullmatch(line)
        if match is None:
            raise SystemExit(f"supervision_invalid_lock_line:{line}")
        name = _canonical(match.group("name"))
        if name in packages:
            raise SystemExit(f"supervision_duplicate_lock_package:{name}")
        packages[name] = {
            "version": match.group("version"),
            "sha256": match.group("sha256"),
        }
    return packages


def _require_digest(path: Path, expected: str, label: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"supervision_{label}_digest_mismatch:{actual}")


def _canonical(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--domain", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--lock-digest", required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--sbom-digest", required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--review-digest", required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--benchmark-digest", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-digest", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
