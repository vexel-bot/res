from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

if __package__:
    from .verify_speech_gpu_candidate_lock import (
        ESPEAKNG_LOADER_VERSION,
        ESPEAKNG_LOADER_WHEEL_DIGEST,
        OPENVOICE_MISAKI_REVISION,
        WAVMARK_VERSION,
        WAVMARK_WHEEL_DIGEST,
        _packages,
        _require_cuda_pair,
        _require_git_revision,
        _require_hashed_registry_artifacts,
        _require_wheel_digest,
    )
else:
    from verify_speech_gpu_candidate_lock import (
        ESPEAKNG_LOADER_VERSION,
        ESPEAKNG_LOADER_WHEEL_DIGEST,
        OPENVOICE_MISAKI_REVISION,
        WAVMARK_VERSION,
        WAVMARK_WHEEL_DIGEST,
        _packages,
        _require_cuda_pair,
        _require_git_revision,
        _require_hashed_registry_artifacts,
        _require_wheel_digest,
    )

EXPECTED = {
    "chatterbox": {
        "digest": "da41ec1f91c666ae37ca663108fe8c3f1e43175e0ea001ed45aba73c83501ad2",
        "package_count": 95,
        "project": "clicko-chatterbox-clone-candidate-v2",
        "required": {"librosa", "pyyaml", "torch", "torchaudio"},
        "forbidden": {"pykakasi", "praat-parselmouth", "resemble-perth"},
    },
    "openvoice": {
        "digest": "de0dfa2271abc283f1a102d01211b1f623f4daf4de0d42e30e9280164aebe6cf",
        "package_count": 96,
        "project": "clicko-kokoro-openvoice-clone-candidate-v2",
        "required": {
            "espeakng-loader",
            "librosa",
            "misaki",
            "phonemizer-fork",
            "soundfile",
            "torch",
            "torchaudio",
            "transformers",
            "wavmark",
        },
        "forbidden": {
            "cn2an",
            "eng-to-ipa",
            "inflect",
            "jieba",
            "kokoro",
            "num2words",
            "pypinyin",
            "spacy",
            "spacy-curated-transformers",
            "unidecode",
        },
    },
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_platform(lock: dict[str, Any]) -> None:
    marker = "platform_machine == 'x86_64' and sys_platform == 'linux'"
    if lock.get("requires-python") != "==3.11.*":
        raise ValueError("speech_gpu_candidate_v2_python_mismatch")
    if lock.get("resolution-markers") != [marker]:
        raise ValueError("speech_gpu_candidate_v2_resolution_marker_mismatch")
    if lock.get("supported-markers") != [marker]:
        raise ValueError("speech_gpu_candidate_v2_supported_marker_mismatch")
    if lock.get("options", {}).get("exclude-newer") != "2026-08-26T23:59:59Z":
        raise ValueError("speech_gpu_candidate_v2_resolution_cutoff_mismatch")


def verify_v2_lock(path: Path, candidate: str) -> dict[str, Any]:
    expected = EXPECTED.get(candidate)
    if expected is None:
        raise ValueError("speech_gpu_candidate_v2_unknown")
    digest = _digest(path)
    if digest != expected["digest"]:
        raise ValueError("speech_gpu_candidate_v2_digest_mismatch")

    lock = tomllib.loads(path.read_text(encoding="utf-8"))
    _require_platform(lock)
    packages = _packages(lock)
    if len(packages) != expected["package_count"]:
        raise ValueError("speech_gpu_candidate_v2_package_count_mismatch")
    if expected["project"] not in packages:
        raise ValueError("speech_gpu_candidate_v2_project_missing")

    present_forbidden = sorted(expected["forbidden"].intersection(packages))
    if present_forbidden:
        raise ValueError(f"speech_gpu_candidate_v2_forbidden:{present_forbidden[0]}")
    missing_required = sorted(expected["required"].difference(packages))
    if missing_required:
        raise ValueError(f"speech_gpu_candidate_v2_required_missing:{missing_required[0]}")

    virtual_packages = [
        name for name, package in packages.items() if "virtual" in package.get("source", {})
    ]
    if virtual_packages != [expected["project"]]:
        raise ValueError("speech_gpu_candidate_v2_virtual_source_invalid")

    _require_hashed_registry_artifacts(packages)
    _require_cuda_pair(packages)
    if candidate == "openvoice":
        misaki = packages["misaki"]
        wavmark = packages["wavmark"]
        espeak = packages["espeakng-loader"]
        _require_git_revision(misaki, OPENVOICE_MISAKI_REVISION, "misaki")
        if wavmark.get("version") != WAVMARK_VERSION:
            raise ValueError("speech_gpu_candidate_v2_wavmark_version_mismatch")
        _require_wheel_digest(wavmark, WAVMARK_WHEEL_DIGEST, "wavmark")
        if espeak.get("version") != ESPEAKNG_LOADER_VERSION:
            raise ValueError("speech_gpu_candidate_v2_espeak_version_mismatch")
        _require_wheel_digest(
            espeak, ESPEAKNG_LOADER_WHEEL_DIGEST, "espeakng-loader"
        )

    return {
        "candidate": candidate,
        "lockDigestSha256": digest,
        "packageCount": len(packages),
        "removedPackageCount": 125 - len(packages)
        if candidate == "chatterbox"
        else 130 - len(packages),
        "status": "speech-gpu-candidate-v2-lock-verified",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lock", type=Path)
    parser.add_argument("--candidate", choices=tuple(EXPECTED), required=True)
    args = parser.parse_args()
    print(json.dumps(verify_v2_lock(args.lock, args.candidate), sort_keys=True))


if __name__ == "__main__":
    main()
