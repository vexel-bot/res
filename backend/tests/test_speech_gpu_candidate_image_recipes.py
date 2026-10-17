from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHATTERBOX = ROOT / "workers/speech-gpu/Dockerfile.chatterbox-candidate"
OPENVOICE = ROOT / "workers/speech-gpu/Dockerfile.openvoice-candidate"
BASE = (
    "python:3.11-slim@sha256:"
    "272efc3f94bec901e2bc7a5c9984b3d113c317839edca2714c6a388b9476f8fc"
)


def test_chatterbox_recipe_binds_source_lock_and_non_provider_runtime() -> None:
    recipe = CHATTERBOX.read_text(encoding="utf-8")

    assert recipe.count(BASE) == 3
    assert "5de7a54aa4e5e2baadb0182dde554908b48b85c2" in recipe
    assert "4248e910a928849fe5815a0f9236e17fa07768d95b9193212752c464b93d6caa" in recipe
    assert "93ff351872971b6cb06071e402852f55b5ad97fe33a829baf8a7f2b2b0600ee5" in recipe
    assert "verify_lock.py uv.lock --candidate chatterbox" in recipe
    assert "pip wheel" in recipe and "--no-deps" in recipe
    assert 'io.clicko.providers="none"' in recipe
    assert 'io.clicko.candidate.status="evaluation"' in recipe
    assert 'io.clicko.weights="external-manifested-mount-only"' in recipe
    assert "HF_HUB_OFFLINE=\"1\"" in recipe
    assert "TRANSFORMERS_OFFLINE=\"1\"" in recipe
    assert 'NUMBA_CACHE_DIR="/tmp/clicko-speech"' in recipe
    assert 'HF_HOME="/tmp/clicko-speech/huggingface"' in recipe
    assert 'XDG_CACHE_HOME="/tmp/clicko-speech/cache"' in recipe
    assert 'TORCH_HOME="/tmp/clicko-speech/torch"' in recipe
    assert "USER clicko" in recipe
    assert "celery" not in recipe.lower()
    assert "DATABASE_URL" not in recipe
    assert "REDIS_URL" not in recipe


def test_openvoice_recipe_binds_minimal_chain_and_espeak_replacement() -> None:
    recipe = OPENVOICE.read_text(encoding="utf-8")

    assert recipe.count(BASE) == 3
    assert "74a1d147b17a8c3092dd5430504bd83ef6c7eb23" in recipe
    assert "bb3541f421e6273d3a3e3dd5bdba2bd3b79a3c2eadca65cde9c62c2467903ac0" in recipe
    assert "d56c6da1f8ca807460085f7eb982313aeedc5be33b730d0cd2aab601018e28dd" in recipe
    assert "verify_lock.py uv.lock --candidate openvoice" in recipe
    assert "install_espeak_runtime_replacement.py" in recipe
    assert "COPY backend /opt/clicko/backend" not in recipe
    assert "backend/app/domain/studios/speech_assets.py" in recipe
    assert "espeak-runtime-evidence" in recipe
    assert 'io.clicko.providers="none"' in recipe
    assert 'io.clicko.candidate.status="evaluation"' in recipe
    assert 'io.clicko.weights="external-manifested-mount-only"' in recipe
    assert 'io.clicko.legal-review="wavmark-wheel-and-espeak-distribution-required"' in recipe
    assert "HF_HUB_OFFLINE=\"1\"" in recipe
    assert "TRANSFORMERS_OFFLINE=\"1\"" in recipe
    assert 'NUMBA_CACHE_DIR="/tmp/clicko-speech"' in recipe
    assert 'HF_HOME="/tmp/clicko-speech/huggingface"' in recipe
    assert 'XDG_CACHE_HOME="/tmp/clicko-speech/cache"' in recipe
    assert 'TORCH_HOME="/tmp/clicko-speech/torch"' in recipe
    assert "USER clicko" in recipe
    assert "celery" not in recipe.lower()
    assert "DATABASE_URL" not in recipe
    assert "REDIS_URL" not in recipe


def test_candidate_recipes_do_not_bake_model_or_biometric_bytes() -> None:
    combined = CHATTERBOX.read_text(encoding="utf-8") + OPENVOICE.read_text(encoding="utf-8")

    assert "snapshot_download" not in combined
    assert "huggingface-cli" not in combined
    assert "hf_hub_download" not in combined
    assert "checkpoint.pth" not in combined
    assert "safetensors" not in combined
    assert "reference.wav" not in combined
    assert "voice-version" not in combined
