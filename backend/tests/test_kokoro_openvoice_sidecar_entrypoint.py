from __future__ import annotations

import importlib.util
import json
import wave
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "workers/speech-gpu/sidecars/kokoro_openvoice_clone.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("clicko_kokoro_openvoice_sidecar", SIDECAR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path: Path):
    request_path = tmp_path / "request.json"
    reference_path = tmp_path / "reference.wav"
    output_path = tmp_path / "output.wav"
    result_path = tmp_path / "result.json"
    kokoro_root = tmp_path / "kokoro"
    openvoice_root = tmp_path / "openvoice"
    for relative in (
        "config.json",
        "kokoro-v1_0.pth",
        "voices/pf_dora.pt",
        "voices/pm_alex.pt",
        "voices/pm_santa.pt",
    ):
        target = kokoro_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fixture")
    for relative in (
        "converter/checkpoint.pth",
        "converter/config.json",
        "watermark/wavmark.model.pkl",
    ):
        target = openvoice_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fixture")
    with wave.open(str(reference_path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24_000)
        output.writeframes(b"\x00\x00" * 24_000 * 4)
    text = "A Clicko preserva este roteiro integral, com café, emoção e CTA."
    request_path.write_text(
        json.dumps(
            {
                "schemaVersion": "clicko.voice-clone-sidecar-request.v1",
                "pipelineContract": "clicko.kokoro-openvoice-v2.pt-br.v1",
                "speech": {
                    "schemaVersion": "studio.speech-synthesis-request.v1",
                    "locale": "pt-BR",
                    "text": text,
                    "voiceKey": "voice-version-001",
                    "audioFormat": "wav",
                    "sampleRate": 24_000,
                },
                "reference": {
                    "voiceVersionId": "voice-version-001",
                    "retentionMode": "job-ephemeral",
                },
            }
        ),
        encoding="utf-8",
    )
    return (
        request_path,
        reference_path,
        output_path,
        result_path,
        kokoro_root,
        openvoice_root,
        text,
    )


class FakeRuntime:
    def __init__(self, verified: bool = True) -> None:
        self.verified = verified
        self.call = None

    def synthesize_and_convert(self, *, text, reference_path, destination, temporary_root):
        self.call = (text, reference_path, temporary_root)
        (temporary_root / "base.wav").write_bytes(b"ephemeral")
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24_000)
            output.writeframes(b"\x00\x00" * 24_000 * 4)
        return self.verified


def test_entrypoint_binds_full_script_local_assets_and_verified_watermark(
    tmp_path: Path, monkeypatch
) -> None:
    module = _module()
    fixture = _fixture(tmp_path)
    request_path, reference_path, output_path, result_path, kokoro_root, openvoice_root, text = fixture
    runtime = FakeRuntime()
    received_roots = None

    def factory(kokoro, openvoice):
        nonlocal received_roots
        received_roots = (kokoro, openvoice)
        return runtime

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    module.run(
        request_path=request_path,
        reference_path=reference_path,
        output_path=output_path,
        result_path=result_path,
        kokoro_root=kokoro_root,
        openvoice_root=openvoice_root,
        runtime_factory=factory,
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert received_roots == (kokoro_root, openvoice_root)
    assert runtime.call[0] == text
    assert runtime.call[1] == reference_path
    assert not runtime.call[2].exists()
    assert result["watermarkApplied"] is True
    assert result["watermarkScheme"] == "wavmark-0.0.3-local-verified"
    assert result["baseVoice"] == "pf_dora"


def test_chunking_preserves_the_complete_normalized_long_script() -> None:
    module = _module()
    text = "  ".join(
        [
            "A Clicko preserva cada frase do roteiro, sem resumir nem completar por conta propria.",
            "O produto aparece em contexto, a demonstracao respeita a ordem planejada e a prova continua audivel.",
            "Depois entram a oferta, a objecao principal, o mecanismo e o chamado para acao final.",
        ]
        * 4
    )

    chunks = module._normalized_chunks(text, limit=120)

    assert len(chunks) > 1
    assert all(chunk and len(chunk) <= 120 for chunk in chunks)
    assert " ".join(chunks) == " ".join(text.split())


def test_entrypoint_rejects_unverified_watermark_and_deletes_output(
    tmp_path: Path, monkeypatch
) -> None:
    module = _module()
    fixture = _fixture(tmp_path)
    request_path, reference_path, output_path, result_path, kokoro_root, openvoice_root, _ = fixture
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    with pytest.raises(ValueError, match="watermark_verification_failed"):
        module.run(
            request_path=request_path,
            reference_path=reference_path,
            output_path=output_path,
            result_path=result_path,
            kokoro_root=kokoro_root,
            openvoice_root=openvoice_root,
            runtime_factory=lambda *_: FakeRuntime(verified=False),
        )

    assert not output_path.exists()
    assert not result_path.exists()


def test_entrypoint_fails_before_runtime_for_asset_or_offline_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    module = _module()
    fixture = _fixture(tmp_path)
    request_path, reference_path, output_path, result_path, kokoro_root, openvoice_root, _ = fixture
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    with pytest.raises(ValueError, match="offline_runtime_required"):
        module.run(
            request_path=request_path,
            reference_path=reference_path,
            output_path=output_path,
            result_path=result_path,
            kokoro_root=kokoro_root,
            openvoice_root=openvoice_root,
        )

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    (openvoice_root / "dynamic-download.bin").write_bytes(b"forbidden")
    with pytest.raises(ValueError, match="converter_asset_layout_invalid"):
        module.run(
            request_path=request_path,
            reference_path=reference_path,
            output_path=output_path,
            result_path=result_path,
            kokoro_root=kokoro_root,
            openvoice_root=openvoice_root,
        )
