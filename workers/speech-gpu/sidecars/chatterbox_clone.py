from __future__ import annotations

import argparse
import json
import os
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

MAX_REQUEST_BYTES = 2 * 1024 * 1024
VARIANTS = {
    "chatterbox.multilingual.from-local.v1": (
        "chatterbox-multilingual-v3",
        "t3_mtl23ls_v3.safetensors",
    ),
    "clicko.chatterbox.pt-br-from-local.v1": (
        "chatterbox-pt-br",
        "t3_pt_br.safetensors",
    ),
}
REQUIRED_FILES = {
    "grapheme_mtl_merged_expanded_v1.json",
    "s3gen.pt",
    "ve.pt",
}
ModelLoader = Callable[[Path, str], Any]
AudioWriter = Callable[[Path, Any, int], None]


def _default_model_loader(asset_root: Path, t3_model: str) -> Any:
    try:
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except ImportError as error:  # pragma: no cover - isolated candidate image only
        raise RuntimeError("chatterbox_runtime_not_installed") from error
    if not torch.cuda.is_available():
        raise RuntimeError("chatterbox_cuda_required")
    return ChatterboxMultilingualTTS.from_local(
        asset_root,
        device="cuda",
        t3_model=t3_model,
    )


def _default_audio_writer(destination: Path, audio: Any, sample_rate: int) -> None:
    try:
        import torchaudio
    except ImportError as error:  # pragma: no cover - isolated candidate image only
        raise RuntimeError("chatterbox_torchaudio_not_installed") from error
    torchaudio.save(
        str(destination),
        audio,
        sample_rate,
        encoding="PCM_S",
        bits_per_sample=16,
    )


def _load_descriptor(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_REQUEST_BYTES:
        raise ValueError("chatterbox_sidecar_request_missing_or_too_large")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("chatterbox_sidecar_request_object_required")
    return payload


def run(
    *,
    request_path: Path,
    reference_path: Path,
    output_path: Path,
    result_path: Path,
    asset_root: Path,
    model_loader: ModelLoader = _default_model_loader,
    audio_writer: AudioWriter = _default_audio_writer,
) -> None:
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise ValueError("chatterbox_offline_runtime_required")
    control_root = request_path.parent.resolve()
    if any(path.parent.resolve() != control_root for path in (output_path, result_path)):
        raise ValueError("chatterbox_sidecar_control_path_scope_mismatch")
    if not reference_path.is_file() or reference_path.is_symlink():
        raise ValueError("chatterbox_sidecar_reference_required")
    payload = _load_descriptor(request_path)
    pipeline = payload.get("pipelineContract")
    if payload.get("schemaVersion") != "clicko.voice-clone-sidecar-request.v1" or pipeline not in VARIANTS:
        raise ValueError("chatterbox_sidecar_contract_invalid")
    speech = payload.get("speech")
    reference = payload.get("reference")
    if not isinstance(speech, dict) or not isinstance(reference, dict):
        raise ValueError("chatterbox_sidecar_payload_invalid")
    if (
        speech.get("schemaVersion") != "studio.speech-synthesis-request.v1"
        or speech.get("locale") != "pt-BR"
        or speech.get("audioFormat") != "wav"
        or speech.get("sampleRate") != 24_000
        or not isinstance(speech.get("text"), str)
        or not speech["text"].strip()
        or speech.get("voiceKey") != reference.get("voiceVersionId")
        or reference.get("retentionMode") != "job-ephemeral"
    ):
        raise ValueError("chatterbox_sidecar_speech_reference_binding_invalid")
    candidate_id, t3_model = VARIANTS[pipeline]
    candidate_root = asset_root / candidate_id
    expected_files = REQUIRED_FILES | {t3_model}
    if (
        not candidate_root.is_dir()
        or candidate_root.is_symlink()
        or {item.name for item in candidate_root.iterdir() if item.is_file()} != expected_files
    ):
        raise ValueError("chatterbox_sidecar_asset_layout_invalid")
    with wave.open(str(reference_path), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != 24_000
            or source.getnframes() < 72_000
        ):
            raise ValueError("chatterbox_sidecar_reference_format_invalid")

    model = model_loader(candidate_root, t3_model)
    audio = model.generate(
        speech["text"],
        language_id="pt",
        audio_prompt_path=str(reference_path),
    )
    if int(model.sr) != 24_000:
        raise ValueError("chatterbox_sidecar_model_sample_rate_mismatch")
    audio_writer(output_path, audio, int(model.sr))
    if not output_path.is_file() or output_path.is_symlink() or output_path.stat().st_size <= 44:
        raise ValueError("chatterbox_sidecar_output_invalid")
    result_path.write_text(
        json.dumps(
            {
                "schemaVersion": "clicko.voice-clone-sidecar-result.v1",
                "pipelineContract": pipeline,
                "watermarkApplied": True,
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Clicko Chatterbox clone sidecar")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--asset-root", required=True, type=Path)
    args = parser.parse_args()
    run(
        request_path=args.request,
        reference_path=args.reference,
        output_path=args.output,
        result_path=args.result,
        asset_root=args.asset_root,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by candidate image
    raise SystemExit(main())
