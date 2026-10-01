from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.speech_assets import KOKORO_REQUIRED_MODEL_FILES
from scripts.generate_kokoro_model_manifest import build_manifest

REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"


def test_generator_hashes_only_the_approved_model_runtime_files(tmp_path):
    cache = tmp_path / "models--hexgrad--Kokoro-82M"
    snapshot = cache / "snapshots" / REVISION
    for relative in KOKORO_REQUIRED_MODEL_FILES:
        path = snapshot / Path(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(relative.encode())
    (snapshot / "README.md").write_bytes(b"model-card")
    (snapshot / "ignored.bin").write_bytes(b"must-not-enter-manifest")
    (cache / "refs").mkdir()
    (cache / "refs" / "main").write_text(REVISION, encoding="utf-8")

    manifest = build_manifest(
        snapshot,
        revision=REVISION,
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert {item.relative_path for item in manifest.files} == KOKORO_REQUIRED_MODEL_FILES
    assert manifest.model_card_digest_sha256 == hashlib.sha256(b"model-card").hexdigest()
