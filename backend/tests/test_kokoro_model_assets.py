from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.studios.speech_assets import (
    KOKORO_REQUIRED_MODEL_FILES,
    KokoroModelAssetFileV1,
    KokoroModelAssetManifestV1,
    kokoro_model_asset_manifest_digest,
    verify_kokoro_model_snapshot,
)

REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"


def _fixture(tmp_path: Path):
    cache = tmp_path / "models--hexgrad--Kokoro-82M"
    snapshot = cache / "snapshots" / REVISION
    entries = []
    for index, relative in enumerate(sorted(KOKORO_REQUIRED_MODEL_FILES), start=1):
        payload = f"fixture-{index}-{relative}".encode()
        path = snapshot / Path(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        entries.append(
            KokoroModelAssetFileV1(
                relative_path=relative,
                size_bytes=len(payload),
                checksum_sha256=hashlib.sha256(payload).hexdigest(),
            )
        )
    (cache / "refs").mkdir()
    (cache / "refs" / "main").write_text(REVISION, encoding="utf-8")
    manifest = KokoroModelAssetManifestV1(
        source_revision=REVISION,
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
        model_card_digest_sha256="a" * 64,
        files=entries,
    )
    return snapshot, manifest


def test_model_snapshot_verifier_binds_revision_reference_size_and_checksum(tmp_path):
    snapshot, manifest = _fixture(tmp_path)

    assert verify_kokoro_model_snapshot(manifest, snapshot) == kokoro_model_asset_manifest_digest(
        manifest
    )


def test_model_snapshot_verifier_rejects_tampered_voice_bytes(tmp_path):
    snapshot, manifest = _fixture(tmp_path)
    (snapshot / "voices" / "pf_dora.pt").write_bytes(b"tampered")

    with pytest.raises(ValueError, match="kokoro_model_asset_(size|checksum)_mismatch"):
        verify_kokoro_model_snapshot(manifest, snapshot)


def test_model_manifest_rejects_unapproved_extra_file(tmp_path):
    _snapshot, manifest = _fixture(tmp_path)
    extra = KokoroModelAssetFileV1(
        relative_path="voices/af_heart.pt",
        size_bytes=1,
        checksum_sha256="b" * 64,
    )

    with pytest.raises(ValueError, match="exactly the approved runtime files"):
        KokoroModelAssetManifestV1.model_validate(
            {
                **manifest.model_dump(mode="json", by_alias=True),
                "files": [
                    *manifest.model_dump(mode="json", by_alias=True)["files"],
                    extra.model_dump(mode="json", by_alias=True),
                ],
            }
        )
