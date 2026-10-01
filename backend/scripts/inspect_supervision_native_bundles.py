from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from packaging.utils import canonicalize_name, parse_wheel_filename

NATIVE_PACKAGES = {
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
NATIVE_SUFFIXES = (".so", ".so.0", ".so.1", ".so.2", ".so.3", ".so.4", ".so.5")


def inspect(wheelhouse: Path) -> dict[str, object]:
    packages: list[dict[str, object]] = []
    found: set[str] = set()
    for wheel in sorted(wheelhouse.glob("*.whl")):
        parsed_name, version, _build, _tags = parse_wheel_filename(wheel.name)
        name = canonicalize_name(parsed_name)
        if name not in NATIVE_PACKAGES:
            continue
        found.add(name)
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            license_paths = sorted(
                item
                for item in names
                if ".dist-info/license" in item.lower()
                or item.lower().endswith(("/license", "/license.txt", "/copying"))
            )
            native_paths = sorted(
                item for item in names if item.lower().endswith(NATIVE_SUFFIXES)
            )
            vendored_paths = [
                item
                for item in native_paths
                if ".libs/" in item.lower() or "manylinux" in item.lower()
            ]
            license_evidence = [
                {
                    "path": path,
                    "sha256": hashlib.sha256(archive.read(path)).hexdigest(),
                    "sizeBytes": len(archive.read(path)),
                }
                for path in license_paths
                if not path.endswith("/")
            ]
        packages.append(
            {
                "package": name,
                "version": str(version),
                "wheel": wheel.name,
                "wheelSha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "licenseEvidence": license_evidence,
                "nativeObjectCount": len(native_paths),
                "vendoredNativeObjectCount": len(vendored_paths),
                "nativeObjectPaths": native_paths,
                "reviewStatus": "human_review_required",
            }
        )
    missing = sorted(NATIVE_PACKAGES - found)
    if missing:
        raise ValueError("Native review wheels missing: " + ",".join(missing))
    missing_notices = [item["package"] for item in packages if not item["licenseEvidence"]]
    return {
        "schemaVersion": "clicko.native-wheel-bundle-review-evidence.v1",
        "candidate": "supervision-toolkit-0.30.1",
        "generatedAt": datetime(2026, 8, 28, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "packageCount": len(packages),
        "allWheelsContainLicenseEvidence": not missing_notices,
        "packagesMissingLicenseEvidence": missing_notices,
        "status": "human_review_required",
        "packages": packages,
        "notes": [
            "This artifact inventories bundled objects and hashes notices; it is not legal approval.",
            "Vendored shared objects require transitive notice and ABI review before promotion.",
            "No package, model, detector or provider is activated by this evidence.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.wheelhouse)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
