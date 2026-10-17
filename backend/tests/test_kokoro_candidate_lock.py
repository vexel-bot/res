from __future__ import annotations

from pathlib import Path

import pytest

from scripts.verify_kokoro_candidate_lock import (
    ESPEAKNG_LOADER_BUNDLED_ESPEAK_REVISION,
    ESPEAKNG_LOADER_VERSION,
    KOKORO_REVISION,
    MISAKI_REVISION,
    POLICY_ESPEAK_REVISION,
    verify_lock,
)


def _write_lock(
    path: Path,
    *,
    kokoro_revision: str = KOKORO_REVISION,
    loader_version: str = ESPEAKNG_LOADER_VERSION,
    torch_registry: str = "https://download.pytorch.org/whl/cpu",
    include_cuda_runtime: bool = False,
) -> Path:
    cuda_package = ""
    if include_cuda_runtime:
        cuda_package = f'''\n[[package]]
name = "nvidia-cublas-cu12"
version = "12.0.0"
source = {{ registry = "https://pypi.org/simple" }}
wheels = [{{ url = "https://example.invalid/cublas.whl", hash = "sha256:{'9' * 64}" }}]
'''
    path.write_text(
        f'''version = 1

[[package]]
name = "kokoro"
version = "0.9.4"
source = {{ git = "https://github.com/hexgrad/kokoro.git?rev={kokoro_revision}#{kokoro_revision}" }}

[[package]]
name = "misaki"
version = "0.9.4"
source = {{ git = "https://github.com/hexgrad/misaki.git?rev={MISAKI_REVISION}#{MISAKI_REVISION}" }}

[[package]]
name = "espeakng-loader"
version = "{loader_version}"
source = {{ registry = "https://pypi.org/simple" }}
wheels = [{{ url = "https://example.invalid/espeakng-loader.whl", hash = "sha256:{'5' * 64}" }}]

[[package]]
name = "huggingface-hub"
version = "1.0.0"
source = {{ registry = "https://pypi.org/simple" }}
wheels = [{{ url = "https://example.invalid/huggingface.whl", hash = "sha256:{'1' * 64}" }}]

[[package]]
name = "phonemizer-fork"
version = "3.3.2"
source = {{ registry = "https://pypi.org/simple" }}
wheels = [{{ url = "https://example.invalid/phonemizer.whl", hash = "sha256:{'6' * 64}" }}]

[[package]]
name = "pydantic"
version = "2.12.5"
source = {{ registry = "https://pypi.org/simple" }}
wheels = [{{ url = "https://example.invalid/pydantic.whl", hash = "sha256:{'7' * 64}" }}]

[[package]]
name = "pydantic-settings"
version = "2.12.0"
source = {{ registry = "https://pypi.org/simple" }}
wheels = [{{ url = "https://example.invalid/pydantic-settings.whl", hash = "sha256:{'8' * 64}" }}]

[[package]]
name = "numpy"
version = "2.0.0"
source = {{ registry = "https://pypi.org/simple" }}
sdist = {{ url = "https://example.invalid/numpy.tar.gz", hash = "sha256:{'2' * 64}" }}

[[package]]
name = "torch"
version = "2.0.0"
source = {{ registry = "{torch_registry}" }}
wheels = [{{ url = "https://example.invalid/torch.whl", hash = "sha256:{'3' * 64}" }}]

[[package]]
name = "transformers"
version = "5.0.0"
source = {{ registry = "https://pypi.org/simple" }}
wheels = [{{ url = "https://example.invalid/transformers.whl", hash = "sha256:{'4' * 64}" }}]
{cuda_package}
''',
        encoding="utf-8",
    )
    return path


def test_candidate_lock_verifier_binds_git_sources_and_hashed_runtime(tmp_path):
    result = verify_lock(_write_lock(tmp_path / "uv.lock"))

    assert result["status"] == "candidate-lock-verified-replacement-required"
    assert result["packageCount"] == 10
    assert len(result["lockDigestSha256"]) == 64
    assert result["bundledEspeakRevision"] == ESPEAKNG_LOADER_BUNDLED_ESPEAK_REVISION
    assert result["policyEspeakRevision"] == POLICY_ESPEAK_REVISION
    assert result["bundledEspeakMatchesPolicy"] is False
    assert result["requiresEspeakRuntimeReplacement"] is True
    assert result["torchDistribution"] == "cpu-only"


def test_candidate_lock_verifier_rejects_moving_or_tampered_kokoro_source(tmp_path):
    with pytest.raises(ValueError, match="kokoro_candidate_lock_source_revision_mismatch"):
        verify_lock(_write_lock(tmp_path / "uv.lock", kokoro_revision="a" * 40))


def test_candidate_lock_verifier_rejects_unpinned_espeak_loader(tmp_path):
    with pytest.raises(
        ValueError,
        match="kokoro_candidate_lock_runtime_version_mismatch:espeakng-loader",
    ):
        verify_lock(_write_lock(tmp_path / "uv.lock", loader_version="0.2.3"))


def test_candidate_lock_verifier_rejects_default_pypi_torch(tmp_path):
    with pytest.raises(ValueError, match="kokoro_candidate_lock_torch_not_cpu_only"):
        verify_lock(
            _write_lock(tmp_path / "uv.lock", torch_registry="https://pypi.org/simple")
        )


def test_candidate_lock_verifier_rejects_cuda_runtime_packages(tmp_path):
    with pytest.raises(
        ValueError,
        match="kokoro_candidate_lock_gpu_runtime_forbidden:nvidia-cublas-cu12",
    ):
        verify_lock(_write_lock(tmp_path / "uv.lock", include_cuda_runtime=True))
