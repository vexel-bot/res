from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "workers" / "speech-cpu" / "Dockerfile.candidate"


def test_candidate_recipe_installs_only_manifested_offline_runtime():
    recipe = DOCKERFILE.read_text(encoding="utf-8")

    assert recipe.count(
        "python:3.11-slim@sha256:272efc3f94bec901e2bc7a5c9984b3d113c317839edca2714c6a388b9476f8fc"
    ) == 2
    assert "uv sync --frozen --no-dev" in recipe
    assert "verify_kokoro_candidate_lock.py" in recipe
    assert "verify_kokoro_model_snapshot" in recipe
    assert "verify_espeak_runtime" in recipe
    assert "install_espeak_runtime_replacement.py" in recipe
    assert "HF_HUB_OFFLINE=\"1\"" in recipe
    assert "TRANSFORMERS_OFFLINE=\"1\"" in recipe
    assert 'io.clicko.cpu.threading="omp=4,mkl=4,openblas=4,numexpr=4"' in recipe
    assert 'OMP_NUM_THREADS="4"' in recipe
    assert 'MKL_NUM_THREADS="4"' in recipe
    assert 'OPENBLAS_NUM_THREADS="4"' in recipe
    assert 'NUMEXPR_NUM_THREADS="4"' in recipe
    assert "KPipeline(lang_code='p', model=False)" in recipe


def test_candidate_recipe_remains_non_deployable_and_unadvertised():
    recipe = DOCKERFILE.read_text(encoding="utf-8")

    assert 'io.clicko.providers="none"' in recipe
    assert 'io.clicko.candidate.status="evaluation"' in recipe
    assert 'USER clicko' in recipe
    assert 'CMD ["python", "scripts/run_kokoro_stock_benchmark.py", "--help"]' in recipe
    assert "celery" not in recipe
    assert "DATABASE_URL" not in recipe
    assert "REDIS_URL" not in recipe
    assert "SPEECH_PROVIDERS" not in recipe
