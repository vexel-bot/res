from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "materialize_self_hosted_assets.py"
SPEC = importlib.util.spec_from_file_location("materialize_self_hosted_assets", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_frozen_manifest_has_unique_safe_exact_assets() -> None:
    manifest_path = Path(__file__).parents[2] / "workers" / "local-evaluation" / "self-hosted-model-assets.v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schemaVersion"] == "clicko.self-hosted-model-assets.v1"
    destinations: set[str] = set()
    for group in manifest["groups"].values():
        assert group["parameterCount"] > 0
        for entry in group["files"]:
            MODULE._validate_entry(entry)
            assert entry["destination"] not in destinations
            destinations.add(entry["destination"])

    assert manifest["groups"]["qwen3-4b-q4-k-m"]["parameterCount"] == 4_022_468_096
    assert manifest["groups"]["chatterbox-pt-br"]["parameterCount"] == 500_000_000


def test_local_launchers_keep_api_loopback_and_providers_disabled() -> None:
    root = Path(__file__).parents[2]
    launcher = (root / "backend/scripts/start_local_qwen_server.ps1").read_text(
        encoding="utf-8"
    )
    assert '[string]$HostAddress = "127.0.0.1"' in launcher
    assert "-AllowNetworkExposure" in launcher
    assert "LLAMA_API_KEY" in launcher
    assert "apiKeyExposed = $false" in launcher
    for manifest_path in (
        root / "workers/llm-gpu/worker.manifest.json",
        root / "workers/speech-gpu/worker.manifest.json",
    ):
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["providers"] == []


def test_rejects_unsafe_destination_and_host() -> None:
    entry = {
        "destination": "../escape.bin",
        "sourceUrl": "https://example.com/model.bin",
        "sizeBytes": 1,
        "sha256": "0" * 64,
    }
    with pytest.raises(ValueError, match="unsafe_destination"):
        MODULE._validate_entry(entry)


def test_existing_verified_asset_is_not_downloaded(tmp_path: Path) -> None:
    target = tmp_path / "asset.bin"
    target.write_bytes(b"clicko")
    entry = {
        "destination": "asset.bin",
        "sourceUrl": "https://huggingface.co/example/resolve/revision/asset.bin",
        "sizeBytes": 6,
        "sha256": "25f5a14535066b85cb553b9736816a00cfcfca1214f638fc7b13f6fefa4b0327",
    }
    result = MODULE._download(entry, target, retries=1)
    assert result["status"] == "already_verified"


def test_existing_mismatched_asset_fails_closed(tmp_path: Path) -> None:
    target = tmp_path / "asset.bin"
    target.write_bytes(b"wrong")
    entry = {
        "destination": "asset.bin",
        "sourceUrl": "https://huggingface.co/example/resolve/revision/asset.bin",
        "sizeBytes": 6,
        "sha256": "3be7b8b182ccd96e48989b4e57311193b183728e1700382503767f286f25fd1a",
    }
    with pytest.raises(RuntimeError, match="existing_asset_mismatch"):
        MODULE._download(entry, target, retries=1)
