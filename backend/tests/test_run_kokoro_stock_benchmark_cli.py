from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.run_kokoro_stock_benchmark import (
    _parse_component_digests,
    _require_outside_repository,
    _verify_espeak_runtime_binding,
)
from scripts.verify_kokoro_candidate_lock import (
    ESPEAKNG_LOADER_BUNDLED_ESPEAK_REVISION,
    ESPEAKNG_LOADER_LINUX_AMD64_WHEEL_DIGEST,
    POLICY_ESPEAK_REVISION,
)

ROOT = Path(__file__).resolve().parents[2]


def test_component_digest_parser_requires_unique_sha256_bindings():
    assert _parse_component_digests([f"kokoro-code={'a' * 64}"]) == {
        "kokoro-code": "a" * 64
    }
    with pytest.raises(ValueError, match="unique_id_equals_sha256"):
        _parse_component_digests([f"kokoro-code={'a' * 64}", f"kokoro-code={'b' * 64}"])
    with pytest.raises(ValueError, match="unique_id_equals_sha256"):
        _parse_component_digests(["kokoro-code=not-a-digest"])


def test_cli_rejects_private_inputs_inside_repository():
    with pytest.raises(ValueError, match="private_benchmark_path_inside_repository"):
        _require_outside_repository(Path(__file__))


def _espeak_manifest(**overrides):
    values = {
        "source_revision": POLICY_ESPEAK_REVISION,
        "bundled_espeak_revision": ESPEAKNG_LOADER_BUNDLED_ESPEAK_REVISION,
        "loader_wheel_digest_sha256": ESPEAKNG_LOADER_LINUX_AMD64_WHEEL_DIGEST,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_benchmark_cli_accepts_only_the_manifested_espeak_replacement():
    _verify_espeak_runtime_binding(
        _espeak_manifest(),
        manifest_digest_sha256="a" * 64,
        component_digests_sha256={"espeak-ng-runtime": "a" * 64},
        expected_source_revision=POLICY_ESPEAK_REVISION,
    )


@pytest.mark.parametrize(
    ("manifest", "component_digest", "message"),
    [
        (
            _espeak_manifest(source_revision="f" * 40),
            "a" * 64,
            "kokoro_benchmark_espeak_policy_revision_mismatch",
        ),
        (
            _espeak_manifest(bundled_espeak_revision="f" * 40),
            "a" * 64,
            "kokoro_benchmark_espeak_loader_binding_mismatch",
        ),
        (
            _espeak_manifest(),
            "b" * 64,
            "kokoro_benchmark_espeak_component_digest_mismatch",
        ),
    ],
)
def test_benchmark_cli_rejects_divergent_espeak_bindings(
    manifest, component_digest, message
):
    with pytest.raises(SystemExit, match=message):
        _verify_espeak_runtime_binding(
            manifest,
            manifest_digest_sha256="a" * 64,
            component_digests_sha256={"espeak-ng-runtime": component_digest},
            expected_source_revision=POLICY_ESPEAK_REVISION,
        )


@pytest.mark.parametrize(
    "script",
    [
        "run_kokoro_stock_benchmark.py",
        "prepare_speech_review.py",
        "ingest_speech_review.py",
        "finalize_speech_benchmark_cleanup.py",
        "generate_kokoro_model_manifest.py",
        "generate_espeak_runtime_manifest.py",
        "install_espeak_runtime_replacement.py",
    ],
)
def test_operational_speech_cli_bootstraps_from_repository_root(script):
    result = subprocess.run(
        [sys.executable, str(ROOT / "backend" / "scripts" / script), "--help"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout
