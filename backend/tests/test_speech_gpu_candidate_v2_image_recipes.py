from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHATTERBOX = ROOT / "workers/speech-gpu/Dockerfile.chatterbox-candidate-v2"
OPENVOICE = ROOT / "workers/speech-gpu/Dockerfile.openvoice-candidate-v2"


def test_chatterbox_v2_builds_pinned_source_wheels_without_upstream_deps() -> None:
    recipe = CHATTERBOX.read_text(encoding="utf-8")

    assert "5de7a54aa4e5e2baadb0182dde554908b48b85c2" in recipe
    assert "ce86c49d029f42272c1902eccb675556b9ed2330" in recipe
    assert "--no-deps" in recipe
    assert "verify_speech_gpu_candidate_v2_lock.py" in recipe
    assert "da41ec1f91c666ae37ca663108fe8c3f1e43175e0ea001ed45aba73c83501ad2" in recipe
    assert "'pykakasi','praat-parselmouth'" in recipe
    assert 'io.clicko.providers="none"' in recipe


def test_openvoice_v2_applies_digest_bound_patches_and_omits_frontends() -> None:
    recipe = OPENVOICE.read_text(encoding="utf-8")

    assert "392e8c1dd20511bdc5b466a578daa04343a59931572f6ea27680603f1b3da0e0" in recipe
    assert "bf31edc3e69ccdd6bad00b55d3d94d7566757244085f9b305716ca51fec707a9" in recipe
    assert recipe.count("git -C /src/") >= 10
    assert "git -C /src/openvoice apply --check" in recipe
    assert "git -C /src/kokoro apply --check" in recipe
    assert "--no-deps" in recipe
    assert "verify_speech_gpu_candidate_v2_lock.py" in recipe
    assert "de0dfa2271abc283f1a102d01211b1f623f4daf4de0d42e30e9280164aebe6cf" in recipe
    assert "--expected-manifest-digest" in recipe
    assert "app.domain.studios.speech_assets" not in recipe
    assert 'io.clicko.providers="none"' in recipe


def test_v2_recipes_keep_weights_external_and_runtime_non_root() -> None:
    for path in (CHATTERBOX, OPENVOICE):
        recipe = path.read_text(encoding="utf-8")
        assert 'io.clicko.weights="external-manifested-mount-only"' in recipe
        assert "useradd --create-home --uid 10001 clicko" in recipe
        assert "USER clicko" in recipe
        assert 'HF_HUB_OFFLINE="1"' in recipe
        assert 'TRANSFORMERS_OFFLINE="1"' in recipe
