from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.speech_assets import (
    ChatterboxModelAssetManifestV1,
    chatterbox_model_asset_manifest_digest,
    verify_chatterbox_model_assets,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "workers/speech-gpu/chatterbox-model-assets.v1.json"


def _payload() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _tiny_manifest(asset_root: Path) -> ChatterboxModelAssetManifestV1:
    payload = _payload()
    for variant in payload["variants"]:
        candidate_id = variant["candidateId"]
        for index, entry in enumerate(variant["files"]):
            content = f"{candidate_id}:{entry['runtimePath']}:{index}".encode()
            entry["sizeBytes"] = len(content)
            entry["checksumSha256"] = hashlib.sha256(content).hexdigest()
            target = asset_root / candidate_id / entry["runtimePath"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    return ChatterboxModelAssetManifestV1.model_validate(payload)


def test_chatterbox_model_metadata_lock_is_frozen_and_complete() -> None:
    manifest = ChatterboxModelAssetManifestV1.model_validate_json(
        MANIFEST.read_text(encoding="utf-8")
    )

    assert [item.candidate_id for item in manifest.variants] == [
        "chatterbox-multilingual-v3",
        "chatterbox-pt-br",
    ]
    assert sum(len(item.files) for item in manifest.variants) == 8
    assert chatterbox_model_asset_manifest_digest(manifest) == (
        "0b3757e10317b5ace3a594ca58bbb6dc184af4a81bfbae0d473398aa543e5b7f"
    )
    pt_br = manifest.variants[1]
    decoder = next(item for item in pt_br.files if item.runtime_path == "s3gen.pt")
    assert decoder.source_path == "s3gen_v3.pt"
    assert decoder.source_revision == "b3952f18bc2eaa72b9bd7c17d2c4653bcad4770d"


def test_chatterbox_asset_verifier_accepts_exact_offline_file_set(tmp_path: Path) -> None:
    manifest = _tiny_manifest(tmp_path)

    assert verify_chatterbox_model_assets(manifest, tmp_path) == (
        chatterbox_model_asset_manifest_digest(manifest)
    )


def test_chatterbox_asset_verifier_rejects_missing_or_tampered_bytes(tmp_path: Path) -> None:
    manifest = _tiny_manifest(tmp_path)
    target = tmp_path / "chatterbox-pt-br" / "s3gen.pt"
    target.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="size_mismatch|checksum_mismatch"):
        verify_chatterbox_model_assets(manifest, tmp_path)


def test_chatterbox_manifest_rejects_pt_br_loader_contract_swap() -> None:
    payload = _payload()
    payload["variants"][1]["loaderContract"] = "chatterbox.multilingual.from-local.v1"

    with pytest.raises(ValidationError, match="wrong loader contract"):
        ChatterboxModelAssetManifestV1.model_validate(payload)
