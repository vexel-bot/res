from __future__ import annotations

import importlib.util
import json
import wave
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "workers/speech-gpu/sidecars/chatterbox_clone.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("clicko_chatterbox_sidecar", SIDECAR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path: Path, pipeline: str):
    request_path = tmp_path / "request.json"
    reference_path = tmp_path / "reference.wav"
    output_path = tmp_path / "output.wav"
    result_path = tmp_path / "result.json"
    candidate_id, t3_model = {
        "chatterbox.multilingual.from-local.v1": (
            "chatterbox-multilingual-v3",
            "t3_mtl23ls_v3.safetensors",
        ),
        "clicko.chatterbox.pt-br-from-local.v1": (
            "chatterbox-pt-br",
            "t3_pt_br.safetensors",
        ),
    }[pipeline]
    candidate_root = tmp_path / "assets" / candidate_id
    candidate_root.mkdir(parents=True)
    for name in (
        "grapheme_mtl_merged_expanded_v1.json",
        "s3gen.pt",
        "ve.pt",
        t3_model,
    ):
        (candidate_root / name).write_bytes(b"fixture")
    with wave.open(str(reference_path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24_000)
        output.writeframes(b"\x00\x00" * 24_000 * 4)
    request_path.write_text(
        json.dumps(
            {
                "schemaVersion": "clicko.voice-clone-sidecar-request.v1",
                "pipelineContract": pipeline,
                "speech": {
                    "schemaVersion": "studio.speech-synthesis-request.v1",
                    "locale": "pt-BR",
                    "text": "Roteiro integral, sem truncamento.",
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
    return request_path, reference_path, output_path, result_path, candidate_root.parent, t3_model


class FakeModel:
    sr = 24_000

    def __init__(self) -> None:
        self.call = None

    def generate(self, text, *, language_id, audio_prompt_path):
        self.call = (text, language_id, audio_prompt_path)
        return object()


@pytest.mark.parametrize(
    "pipeline",
    [
        "chatterbox.multilingual.from-local.v1",
        "clicko.chatterbox.pt-br-from-local.v1",
    ],
)
def test_chatterbox_entrypoint_preserves_variant_and_full_script(
    tmp_path: Path, monkeypatch, pipeline: str
) -> None:
    module = _module()
    fixture = _fixture(tmp_path, pipeline)
    request_path, reference_path, output_path, result_path, asset_root, expected_t3 = fixture
    model = FakeModel()
    loaded = None

    def loader(candidate_root, t3_model):
        nonlocal loaded
        loaded = (candidate_root.name, t3_model)
        return model

    def writer(destination, _audio, sample_rate):
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(b"\x00\x00" * sample_rate)

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    module.run(
        request_path=request_path,
        reference_path=reference_path,
        output_path=output_path,
        result_path=result_path,
        asset_root=asset_root,
        model_loader=loader,
        audio_writer=writer,
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert loaded[1] == expected_t3
    assert model.call[0] == "Roteiro integral, sem truncamento."
    assert model.call[1] == "pt"
    assert result["pipelineContract"] == pipeline
    assert result["watermarkApplied"] is True


def test_chatterbox_entrypoint_fails_closed_without_offline_runtime(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    fixture = _fixture(tmp_path, "chatterbox.multilingual.from-local.v1")
    request_path, reference_path, output_path, result_path, asset_root, _ = fixture
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)

    with pytest.raises(ValueError, match="offline_runtime_required"):
        module.run(
            request_path=request_path,
            reference_path=reference_path,
            output_path=output_path,
            result_path=result_path,
            asset_root=asset_root,
        )

    assert not output_path.exists()
    assert not result_path.exists()
