"""Generate a focused SPDX SBOM and license review from the frozen wheelhouse."""

from __future__ import annotations

import argparse
import email
import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packaging.utils import canonicalize_name, parse_wheel_filename

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK = ROOT / "workers/vision-gpu/supervision/requirements.lock"

LICENSE_FALLBACKS = {
    "annotated-types": "MIT",
    "av": "BSD-3-Clause",
    "certifi": "MPL-2.0",
    "charset-normalizer": "MIT",
    "colorama": "BSD-3-Clause",
    "contourpy": "BSD-3-Clause",
    "cycler": "BSD-3-Clause",
    "defusedxml": "PSF-2.0",
    "fonttools": "MIT",
    "idna": "BSD-3-Clause",
    "kiwisolver": "BSD-3-Clause",
    "matplotlib": "PSF-2.0",
    "numpy": "BSD-3-Clause",
    "packaging": "Apache-2.0 OR BSD-2-Clause",
    "pillow": "HPND",
    "pydeprecate": "MIT",
    "pydantic": "MIT",
    "pydantic-core": "MIT",
    "pyparsing": "MIT",
    "python-dateutil": "Apache-2.0 OR BSD-3-Clause",
    "pyyaml": "MIT",
    "requests": "Apache-2.0",
    "scipy": "BSD-3-Clause",
    "six": "MIT",
    "supervision": "MIT",
    "tqdm": "MPL-2.0 AND MIT",
    "typing-extensions": "PSF-2.0",
    "typing-inspection": "MIT",
    "urllib3": "MIT",
}

NATIVE_REVIEW_REQUIRED = {
    "av",
    "contourpy",
    "fonttools",
    "kiwisolver",
    "matplotlib",
    "numpy",
    "pillow",
    "pydantic-core",
    "pyyaml",
    "scipy",
}


def main() -> int:
    args = _parse_args()
    locked = _parse_lock(args.lock)
    packages = _inspect_wheelhouse(args.wheelhouse, locked)
    lock_digest = _sha256(args.lock.read_bytes())
    sbom = _spdx(packages, lock_digest)
    review = _review(packages, lock_digest)
    args.sbom.parent.mkdir(parents=True, exist_ok=True)
    args.review.parent.mkdir(parents=True, exist_ok=True)
    args.sbom.write_text(
        json.dumps(sbom, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.review.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "lockDigestSha256": lock_digest,
                "packageCount": len(packages),
                "reviewStatus": review["status"],
                "sbom": str(args.sbom),
                "review": str(args.review),
            },
            separators=(",", ":"),
        )
    )
    return 0


def _parse_lock(path: Path) -> dict[str, dict[str, str]]:
    line_pattern = re.compile(
        r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^ ]+) "
        r"--hash=sha256:(?P<digest>[0-9a-f]{64})$"
    )
    result: dict[str, dict[str, str]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = line_pattern.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid lock line: {line}")
        name = canonicalize_name(match.group("name"))
        if name in result:
            raise ValueError(f"duplicate lock package: {name}")
        result[name] = {
            "version": match.group("version"),
            "sha256": match.group("digest"),
        }
    if not result:
        raise ValueError("empty Supervision lock")
    return result


def _inspect_wheelhouse(
    wheelhouse: Path,
    locked: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for path in sorted(wheelhouse.glob("*.whl")):
        parsed_name, parsed_version, _build, _tags = parse_wheel_filename(path.name)
        name = canonicalize_name(parsed_name)
        if name not in locked:
            raise ValueError(f"wheel not present in lock: {path.name}")
        if name in found:
            raise ValueError(f"duplicate wheel for locked package: {name}")
        digest = _sha256(path.read_bytes())
        expected = locked[name]
        if str(parsed_version) != expected["version"] or digest != expected["sha256"]:
            raise ValueError(f"wheel does not match lock: {path.name}")
        with zipfile.ZipFile(path) as archive:
            metadata_path = next(
                item
                for item in archive.namelist()
                if item.endswith(".dist-info/METADATA")
            )
            metadata = email.message_from_bytes(archive.read(metadata_path))
            license_files = sorted(
                item
                for item in archive.namelist()
                if ".dist-info/licenses/" in item.lower()
                or item.lower().endswith(
                    ("/license", "/license.txt", "/copying", "/copying.txt")
                )
            )
        declared = metadata.get("License-Expression") or LICENSE_FALLBACKS.get(name)
        if declared is None:
            raise ValueError(f"license mapping missing: {name}")
        found[name] = {
            "name": str(metadata.get("Name") or parsed_name),
            "canonicalName": name,
            "version": str(metadata.get("Version") or parsed_version),
            "wheel": path.name,
            "sha256": digest,
            "declaredLicense": declared,
            "licenseExpressionFromMetadata": metadata.get("License-Expression"),
            "licenseFiles": license_files,
            "homePage": metadata.get("Home-page"),
            "reviewStatus": (
                "review_required" if name in NATIVE_REVIEW_REQUIRED else "approved"
            ),
        }
    missing = sorted(set(locked) - set(found))
    if missing:
        raise ValueError(f"locked wheels missing: {','.join(missing)}")
    return [found[name] for name in sorted(found)]


def _spdx(packages: list[dict[str, Any]], lock_digest: str) -> dict[str, Any]:
    spdx_packages: list[dict[str, Any]] = []
    relationships: list[dict[str, str]] = []
    for item in packages:
        identifier = "SPDXRef-Package-" + re.sub(
            r"[^A-Za-z0-9.-]",
            "-",
            item["canonicalName"],
        )
        spdx_packages.append(
            {
                "SPDXID": identifier,
                "name": item["name"],
                "versionInfo": item["version"],
                "downloadLocation": (
                    f"https://pypi.org/project/{item['canonicalName']}/{item['version']}/"
                ),
                "filesAnalyzed": False,
                "checksums": [
                    {
                        "algorithm": "SHA256",
                        "checksumValue": item["sha256"],
                    }
                ],
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": item["declaredLicense"],
                "copyrightText": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": (
                            f"pkg:pypi/{item['canonicalName']}@{item['version']}"
                        ),
                    }
                ],
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": identifier,
            }
        )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "clicko-supervision-evaluation-wheelhouse",
        "documentNamespace": (
            "https://clicko.invalid/spdx/supervision-evaluation/" + lock_digest
        ),
        "creationInfo": {
            "created": datetime(2026, 8, 28, tzinfo=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "creators": [
                "Tool: clicko-generate-supervision-supply-chain/1.0.0"
            ],
        },
        "packages": spdx_packages,
        "relationships": relationships,
    }


def _review(packages: list[dict[str, Any]], lock_digest: str) -> dict[str, Any]:
    pending = [
        item["canonicalName"]
        for item in packages
        if item["reviewStatus"] != "approved"
    ]
    return {
        "schemaVersion": "clicko.dependency-license-review.v1",
        "candidate": "supervision-toolkit-0.30.1",
        "lockDigestSha256": lock_digest,
        "status": "review_required" if pending else "approved",
        "policy": "open-source-only",
        "packages": packages,
        "pendingNativeBundleReview": pending,
        "notes": [
            "Declared licenses are metadata evidence, not a legal opinion.",
            "Native wheels remain review_required until bundled notices and linked libraries are inspected.",
            "This review does not approve any detector, tracker, model weights or provider promotion.",
        ],
    }


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
