from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.speech_assets import (
    OpenVoiceModelAssetManifestV1,
    openvoice_model_asset_manifest_digest,
    verify_openvoice_model_assets,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "workers/speech-gpu/openvoice-model-assets.v1.json"


def _payload() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _tiny_manifest(asset_root: Path) -> OpenVoiceModelAssetManifestV1:
    payload = _payload()
    for index, entry in enumerate(payload["files"]):
        content = f"{entry['runtimePath']}:{index}".encode()
        entry["sizeBytes"] = len(content)
        entry["checksumSha256"] = hashlib.sha256(content).hexdigest()
        target = asset_root / entry["runtimePath"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return OpenVoiceModelAssetManifestV1.model_validate(payload)


def test_openvoice_metadata_lock_is_minimal_offline_pipeline() -> None:
    manifest = OpenVoiceModelAssetManifestV1.model_validate_json(
        MANIFEST.read_text(encoding="utf-8")
    )

    assert manifest.base_voice_strategy == "kokoro-pt-br-extract-source-se"
    assert manifest.reference_strategy == "normalized-consented-wav-extract-target-se"
    assert {item.runtime_path for item in manifest.files} == {
        "converter/checkpoint.pth",
        "converter/config.json",
        "watermark/wavmark.model.pkl",
    }
    assert openvoice_model_asset_manifest_digest(manifest) == (
        "035360cd1f63378a6bd0f8b951b6de859f2fb961a61a2f5d7dcf627a90459d7c"
    )


def test_openvoice_asset_verifier_accepts_only_exact_offline_file_set(
    tmp_path: Path,
) -> None:
    manifest = _tiny_manifest(tmp_path)

    assert verify_openvoice_model_assets(manifest, tmp_path) == (
        openvoice_model_asset_manifest_digest(manifest)
    )


def test_openvoice_asset_verifier_rejects_tampered_converter(tmp_path: Path) -> None:
    manifest = _tiny_manifest(tmp_path)
    (tmp_path / "converter/checkpoint.pth").write_bytes(b"tampered")

    with pytest.raises(ValueError, match="size_mismatch|checksum_mismatch"):
        verify_openvoice_model_assets(manifest, tmp_path)


def test_openvoice_manifest_rejects_dynamic_or_extra_runtime_asset() -> None:
    payload = _payload()
    payload["files"].append(
        {
            "sourceRepositoryId": "M4869/WavMark",
            "sourceRevision": "0ad3c7b74f641bddb61f6b85cdf2de0d93a5bfef",
            "sourcePath": "dynamic.model.pkl",
            "runtimePath": "watermark/dynamic.model.pkl",
            "sizeBytes": 1,
            "checksumSha256": "0" * 64,
        }
    )

    with pytest.raises(ValidationError, match="exactly the approved runtime files"):
        OpenVoiceModelAssetManifestV1.model_validate(payload)
