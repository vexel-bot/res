from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from scripts.verify_speech_gpu_candidate_lock import verify_lock

ROOT = Path(__file__).resolve().parents[2]
CHATTERBOX_LOCK = ROOT / "workers/speech-gpu/candidate/chatterbox/uv.lock"
OPENVOICE_LOCK = ROOT / "workers/speech-gpu/candidate/openvoice/uv.lock"


@pytest.mark.parametrize(
    ("candidate", "lock_path", "digest", "package_count", "espeak_replacement"),
    [
        (
            "chatterbox",
            CHATTERBOX_LOCK,
            "93ff351872971b6cb06071e402852f55b5ad97fe33a829baf8a7f2b2b0600ee5",
            125,
            False,
        ),
        (
            "openvoice",
            OPENVOICE_LOCK,
            "d56c6da1f8ca807460085f7eb982313aeedc5be33b730d0cd2aab601018e28dd",
            130,
            True,
        ),
    ],
)
def test_real_candidate_lock_is_frozen_and_verified(
    candidate: str,
    lock_path: Path,
    digest: str,
    package_count: int,
    espeak_replacement: bool,
) -> None:
    result = verify_lock(lock_path, candidate)

    assert result["status"] == "speech-gpu-candidate-lock-verified"
    assert result["lockDigestSha256"] == digest
    assert result["packageCount"] == package_count
    assert result["requiresEspeakRuntimeReplacement"] is espeak_replacement
    assert result["torchVersion"] == "2.6.0+cu124"


def _mutated_lock(tmp_path: Path, source: Path, old: str, new: str) -> Path:
    payload = source.read_text(encoding="utf-8")
    assert old in payload
    target = tmp_path / "uv.lock"
    target.write_text(payload.replace(old, new, 1), encoding="utf-8")
    tomllib.loads(target.read_text(encoding="utf-8"))
    return target


def test_lock_rejects_cross_index_torchaudio(tmp_path: Path) -> None:
    lock = _mutated_lock(
        tmp_path,
        OPENVOICE_LOCK,
        'source = { registry = "https://download.pytorch.org/whl/cu124" }',
        'source = { registry = "https://pypi.org/simple" }',
    )
    with pytest.raises(ValueError, match="cuda_source_mismatch"):
        verify_lock(lock, "openvoice")


def test_lock_rejects_moving_perth_revision(tmp_path: Path) -> None:
    lock = _mutated_lock(
        tmp_path,
        CHATTERBOX_LOCK,
        "?rev=ce86c49d029f42272c1902eccb675556b9ed2330"
        "#ce86c49d029f42272c1902eccb675556b9ed2330",
        "?rev=master#master",
    )
    with pytest.raises(ValueError, match="git_revision_mismatch:resemble-perth"):
        verify_lock(lock, "chatterbox")


def test_lock_rejects_forbidden_demo_dependency(tmp_path: Path) -> None:
    payload = OPENVOICE_LOCK.read_text(encoding="utf-8")
    target = tmp_path / "uv.lock"
    digest = "a" * 64
    target.write_text(
        payload
        + f'''
[[package]]
name = "gradio"
version = "6.8.0"
source = {{ registry = "https://pypi.org/simple" }}
wheels = [{{ url = "https://example.invalid/gradio.whl", hash = "sha256:{digest}" }}]
''',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="forbidden_package:gradio"):
        verify_lock(target, "openvoice")


def test_lock_rejects_unhashed_registry_artifact(tmp_path: Path) -> None:
    lock = _mutated_lock(tmp_path, OPENVOICE_LOCK, "hash = \"sha256:", "hash = \"sha257:")
    with pytest.raises(ValueError, match="unhashed_registry_artifact"):
        verify_lock(lock, "openvoice")
