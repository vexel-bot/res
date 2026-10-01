from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

KOKORO_REVISION = "dfb907a02bba8152ca444717ca5d78747ccb4bec"
MISAKI_REVISION = "fba1236595f2d2bf21d414ba6e57d25256afada3"
ESPEAKNG_LOADER_VERSION = "0.2.4"
ESPEAKNG_LOADER_SOURCE_REVISION = "146599e29be31bf17d99f0bcb7dbb2f92aef3d95"
ESPEAKNG_LOADER_BUNDLED_ESPEAK_REVISION = "4870adfa25b1a32b4361592f1be8a40337c58d6c"
ESPEAKNG_LOADER_LINUX_AMD64_WHEEL_DIGEST = (
    "08721baf27d13d461f6be6eed9a65277e70d68234ff484fd8b9897b222cdcb6d"
)
POLICY_ESPEAK_REVISION = "7d426728fe146f4168fa716e29d8e276c7da33f2"
REQUIRED_REGISTRY_PACKAGES = {
    "espeakng-loader",
    "huggingface-hub",
    "numpy",
    "phonemizer-fork",
    "pydantic",
    "pydantic-settings",
    "torch",
    "transformers",
}
EXPECTED_REGISTRY_VERSIONS = {
    "espeakng-loader": ESPEAKNG_LOADER_VERSION,
    "phonemizer-fork": "3.3.2",
    "pydantic": "2.12.5",
    "pydantic-settings": "2.12.0",
}
PYTORCH_CPU_REGISTRY = "https://download.pytorch.org/whl/cpu"
FORBIDDEN_CPU_RUNTIME_PACKAGES = frozenset({"triton"})
FORBIDDEN_CPU_RUNTIME_PREFIXES = ("nvidia-",)


def _source_text(package: dict[str, Any]) -> str:
    return json.dumps(package.get("source", {}), sort_keys=True, separators=(",", ":"))


def _has_hashed_distribution(package: dict[str, Any]) -> bool:
    sdist = package.get("sdist")
    if isinstance(sdist, dict) and str(sdist.get("hash", "")).startswith("sha256:"):
        return True
    wheels = package.get("wheels")
    return bool(wheels) and all(
        isinstance(wheel, dict) and str(wheel.get("hash", "")).startswith("sha256:")
        for wheel in wheels
    )


def verify_lock(path: Path) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError("kokoro_candidate_lock_unreadable") from error
    packages = payload.get("package")
    if not isinstance(packages, list) or not packages:
        raise ValueError("kokoro_candidate_lock_packages_missing")
    by_name: dict[str, list[dict[str, Any]]] = {}
    for package in packages:
        if not isinstance(package, dict) or not isinstance(package.get("name"), str):
            raise ValueError("kokoro_candidate_lock_package_invalid")
        source = package.get("source", {})
        if isinstance(source, dict) and any(key in source for key in ("editable", "directory")):
            raise ValueError(f"kokoro_candidate_lock_local_source:{package['name']}")
        by_name.setdefault(package["name"].lower(), []).append(package)

    kokoro = by_name.get("kokoro", [])
    misaki = by_name.get("misaki", [])
    if len(kokoro) != 1 or kokoro[0].get("version") != "0.9.4":
        raise ValueError("kokoro_candidate_lock_version_mismatch")
    if KOKORO_REVISION not in _source_text(kokoro[0]):
        raise ValueError("kokoro_candidate_lock_source_revision_mismatch")
    if len(misaki) != 1 or MISAKI_REVISION not in _source_text(misaki[0]):
        raise ValueError("misaki_candidate_lock_source_revision_mismatch")

    missing = sorted(REQUIRED_REGISTRY_PACKAGES - by_name.keys())
    if missing:
        raise ValueError(f"kokoro_candidate_lock_runtime_missing:{','.join(missing)}")
    for name, expected_version in EXPECTED_REGISTRY_VERSIONS.items():
        packages_for_name = by_name[name]
        if len(packages_for_name) != 1 or packages_for_name[0].get("version") != expected_version:
            raise ValueError(f"kokoro_candidate_lock_runtime_version_mismatch:{name}")
    unhashed = sorted(
        name
        for name in REQUIRED_REGISTRY_PACKAGES
        if not all(_has_hashed_distribution(package) for package in by_name[name])
    )
    if unhashed:
        raise ValueError(f"kokoro_candidate_lock_hashes_missing:{','.join(unhashed)}")

    torch_sources = {_source_text(package) for package in by_name["torch"]}
    if len(torch_sources) != 1 or PYTORCH_CPU_REGISTRY not in next(iter(torch_sources)):
        raise ValueError("kokoro_candidate_lock_torch_not_cpu_only")
    forbidden_cpu_packages = sorted(
        name
        for name in by_name
        if name in FORBIDDEN_CPU_RUNTIME_PACKAGES
        or name.startswith(FORBIDDEN_CPU_RUNTIME_PREFIXES)
    )
    if forbidden_cpu_packages:
        raise ValueError(
            "kokoro_candidate_lock_gpu_runtime_forbidden:"
            + ",".join(forbidden_cpu_packages)
        )

    raw = path.read_bytes()
    return {
        "schemaVersion": "clicko.kokoro-candidate-lock-verification.v1",
        "lockDigestSha256": hashlib.sha256(raw).hexdigest(),
        "packageCount": len(packages),
        "kokoroRevision": KOKORO_REVISION,
        "misakiRevision": MISAKI_REVISION,
        "espeakngLoaderSourceRevision": ESPEAKNG_LOADER_SOURCE_REVISION,
        "espeakngLoaderLinuxAmd64WheelDigestSha256": (
            ESPEAKNG_LOADER_LINUX_AMD64_WHEEL_DIGEST
        ),
        "bundledEspeakRevision": ESPEAKNG_LOADER_BUNDLED_ESPEAK_REVISION,
        "policyEspeakRevision": POLICY_ESPEAK_REVISION,
        "bundledEspeakMatchesPolicy": False,
        "requiresEspeakRuntimeReplacement": True,
        "torchDistribution": "cpu-only",
        "status": "candidate-lock-verified-replacement-required",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the external Kokoro Linux lock artifact.")
    parser.add_argument("lock", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_lock(args.lock), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
