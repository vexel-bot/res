from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

CUDA_INDEX = "https://download.pytorch.org/whl/cu124"
TORCH_VERSION = "2.6.0+cu124"
CHATTERBOX_PERTH_REVISION = "ce86c49d029f42272c1902eccb675556b9ed2330"
OPENVOICE_KOKORO_REVISION = "dfb907a02bba8152ca444717ca5d78747ccb4bec"
OPENVOICE_MISAKI_REVISION = "fba1236595f2d2bf21d414ba6e57d25256afada3"
WAVMARK_VERSION = "0.0.3"
WAVMARK_WHEEL_DIGEST = "f77c7234e66b6983273fa7bd7509acaa9195cd936fd1c178b46c8e996d7e8f02"
ESPEAKNG_LOADER_VERSION = "0.2.4"
ESPEAKNG_LOADER_WHEEL_DIGEST = (
    "08721baf27d13d461f6be6eed9a65277e70d68234ff484fd8b9897b222cdcb6d"
)
FORBIDDEN_PACKAGES = {
    "faster-whisper",
    "gradio",
    "melo",
    "openai",
    "silero-vad",
    "whisper-timestamped",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _packages(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packages = lock.get("package")
    if not isinstance(packages, list) or not packages:
        raise ValueError("speech_gpu_candidate_lock_packages_required")
    indexed: dict[str, dict[str, Any]] = {}
    for package in packages:
        name = package.get("name")
        if not isinstance(name, str) or name in indexed:
            raise ValueError("speech_gpu_candidate_lock_package_names_invalid")
        indexed[name] = package
    return indexed


def _require_hashed_registry_artifacts(packages: dict[str, dict[str, Any]]) -> None:
    for name, package in packages.items():
        if "registry" not in package.get("source", {}):
            continue
        artifacts = list(package.get("wheels", []))
        if "sdist" in package:
            artifacts.append(package["sdist"])
        if not artifacts or any(
            not artifact.get("hash", "").startswith("sha256:") for artifact in artifacts
        ):
            raise ValueError(f"speech_gpu_candidate_lock_unhashed_registry_artifact:{name}")


def _require_git_revision(package: dict[str, Any], revision: str, name: str) -> None:
    source = package.get("source", {}).get("git", "")
    if f"?rev={revision}" not in source or not source.endswith(f"#{revision}"):
        raise ValueError(f"speech_gpu_candidate_lock_git_revision_mismatch:{name}")


def _require_wheel_digest(package: dict[str, Any], digest: str, name: str) -> None:
    hashes = {wheel.get("hash") for wheel in package.get("wheels", [])}
    if f"sha256:{digest}" not in hashes:
        raise ValueError(f"speech_gpu_candidate_lock_wheel_digest_mismatch:{name}")


def _require_cuda_pair(packages: dict[str, dict[str, Any]]) -> None:
    for name in ("torch", "torchaudio"):
        package = packages.get(name)
        if package is None:
            raise ValueError(f"speech_gpu_candidate_lock_runtime_missing:{name}")
        if package.get("version") != TORCH_VERSION:
            raise ValueError(f"speech_gpu_candidate_lock_runtime_version_mismatch:{name}")
        if package.get("source", {}).get("registry") != CUDA_INDEX:
            raise ValueError(f"speech_gpu_candidate_lock_cuda_source_mismatch:{name}")


def verify_lock(path: Path, candidate: str) -> dict[str, Any]:
    if candidate not in {"chatterbox", "openvoice"}:
        raise ValueError("speech_gpu_candidate_lock_candidate_unknown")
    lock = tomllib.loads(path.read_text(encoding="utf-8"))
    packages = _packages(lock)
    forbidden = sorted(FORBIDDEN_PACKAGES.intersection(packages))
    if forbidden:
        raise ValueError(f"speech_gpu_candidate_lock_forbidden_package:{forbidden[0]}")
    _require_hashed_registry_artifacts(packages)
    _require_cuda_pair(packages)

    requires_espeak_replacement = candidate == "openvoice"
    if candidate == "chatterbox":
        perth = packages.get("resemble-perth")
        if perth is None:
            raise ValueError("speech_gpu_candidate_lock_runtime_missing:resemble-perth")
        _require_git_revision(perth, CHATTERBOX_PERTH_REVISION, "resemble-perth")
    else:
        kokoro = packages.get("kokoro")
        misaki = packages.get("misaki")
        wavmark = packages.get("wavmark")
        espeak = packages.get("espeakng-loader")
        for name, package in (
            ("kokoro", kokoro),
            ("misaki", misaki),
            ("wavmark", wavmark),
            ("espeakng-loader", espeak),
        ):
            if package is None:
                raise ValueError(f"speech_gpu_candidate_lock_runtime_missing:{name}")
        _require_git_revision(kokoro, OPENVOICE_KOKORO_REVISION, "kokoro")
        _require_git_revision(misaki, OPENVOICE_MISAKI_REVISION, "misaki")
        if wavmark.get("version") != WAVMARK_VERSION:
            raise ValueError("speech_gpu_candidate_lock_runtime_version_mismatch:wavmark")
        _require_wheel_digest(wavmark, WAVMARK_WHEEL_DIGEST, "wavmark")
        if espeak.get("version") != ESPEAKNG_LOADER_VERSION:
            raise ValueError("speech_gpu_candidate_lock_runtime_version_mismatch:espeakng-loader")
        _require_wheel_digest(espeak, ESPEAKNG_LOADER_WHEEL_DIGEST, "espeakng-loader")

    return {
        "candidate": candidate,
        "cudaIndex": CUDA_INDEX,
        "lockDigestSha256": _digest(path),
        "packageCount": len(packages),
        "requiresEspeakRuntimeReplacement": requires_espeak_replacement,
        "status": "speech-gpu-candidate-lock-verified",
        "torchVersion": TORCH_VERSION,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lock", type=Path)
    parser.add_argument("--candidate", choices=("chatterbox", "openvoice"), required=True)
    args = parser.parse_args()
    print(json.dumps(verify_lock(args.lock, args.candidate), sort_keys=True))


if __name__ == "__main__":
    main()
