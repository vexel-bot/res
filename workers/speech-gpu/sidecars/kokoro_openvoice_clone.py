from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

MAX_REQUEST_BYTES = 2 * 1024 * 1024
PIPELINE_CONTRACT = "clicko.kokoro-openvoice-v2.pt-br.v1"
BASE_VOICE = "pf_dora"
KOKORO_FILES = {
    "config.json",
    "kokoro-v1_0.pth",
    "voices/pf_dora.pt",
    "voices/pm_alex.pt",
    "voices/pm_santa.pt",
}
OPENVOICE_FILES = {
    "converter/checkpoint.pth",
    "converter/config.json",
    "watermark/wavmark.model.pkl",
}
WATERMARK_PAYLOAD = b"C1"


class CloneRuntime(Protocol):
    def synthesize_and_convert(
        self,
        *,
        text: str,
        reference_path: Path,
        destination: Path,
        temporary_root: Path,
    ) -> bool: ...


RuntimeFactory = Callable[[Path, Path], CloneRuntime]


def _normalized_chunks(text: str, limit: int = 320) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        raise ValueError("openvoice_sidecar_text_empty_after_normalization")
    chunks: list[str] = []
    remainder = normalized
    while remainder:
        if len(remainder) <= limit:
            chunks.append(remainder)
            break
        boundary = max(
            remainder.rfind(marker, 0, limit + 1)
            for marker in (". ", "! ", "? ", "; ", ", ", " ")
        )
        cut = boundary + 1 if boundary > 0 else limit
        chunks.append(remainder[:cut].strip())
        remainder = remainder[cut:].strip()
    if " ".join(chunks) != normalized:
        raise ValueError("openvoice_sidecar_chunking_changed_script")
    return chunks


class LocalKokoroOpenVoiceRuntime:
    def __init__(self, kokoro_root: Path, openvoice_root: Path) -> None:
        try:
            import librosa
            import numpy as np
            import soundfile
            import torch
            import wavmark
            from kokoro import KModel, KPipeline
            from openvoice.api import ToneColorConverter
        except ImportError as error:  # pragma: no cover - candidate image only
            raise RuntimeError("kokoro_openvoice_runtime_not_installed") from error
        if not torch.cuda.is_available():
            raise RuntimeError("kokoro_openvoice_cuda_required")
        self.librosa = librosa
        self.np = np
        self.soundfile = soundfile
        self.torch = torch
        self.wavmark = wavmark
        self.device = "cuda:0"
        model = KModel(
            repo_id="hexgrad/Kokoro-82M",
            config=str(kokoro_root / "config.json"),
            model=str(kokoro_root / "kokoro-v1_0.pth"),
        ).to(self.device).eval()
        self.pipeline = KPipeline(
            lang_code="p",
            repo_id="hexgrad/Kokoro-82M",
            model=model,
            device=self.device,
        )
        self.voice_path = kokoro_root / "voices" / f"{BASE_VOICE}.pt"
        self.converter = ToneColorConverter(
            str(openvoice_root / "converter" / "config.json"),
            device=self.device,
            enable_watermark=False,
        )
        self.converter.load_ckpt(str(openvoice_root / "converter" / "checkpoint.pth"))
        self.watermark_model = wavmark.load_model(
            str(openvoice_root / "watermark" / "wavmark.model.pkl")
        ).to(self.device)

    def _synthesize_base(self, text: str, destination: Path) -> None:
        parts: list[Any] = []
        for chunk in _normalized_chunks(text):
            for result in self.pipeline(
                chunk,
                voice=str(self.voice_path),
                speed=1.0,
                split_pattern=None,
            ):
                audio = getattr(result, "audio", None)
                if audio is None:
                    continue
                if hasattr(audio, "detach"):
                    audio = audio.detach()
                if hasattr(audio, "cpu"):
                    audio = audio.cpu()
                if hasattr(audio, "numpy"):
                    audio = audio.numpy()
                part = self.np.asarray(audio, dtype=self.np.float32).reshape(-1)
                if part.size:
                    parts.append(part)
        if not parts:
            raise ValueError("kokoro_openvoice_base_audio_missing")
        audio = self.np.concatenate(parts)
        if not self.np.isfinite(audio).all():
            raise ValueError("kokoro_openvoice_base_audio_invalid")
        self.soundfile.write(str(destination), audio, 24_000, subtype="PCM_16")

    def _apply_and_verify_watermark(self, source: Path, destination: Path) -> bool:
        signal, _ = self.librosa.load(str(source), sr=16_000, mono=True)
        payload = self.np.unpackbits(self.np.frombuffer(WATERMARK_PAYLOAD, dtype=self.np.uint8))
        encoded, _ = self.wavmark.encode_watermark(
            self.watermark_model,
            signal,
            payload,
            show_progress=False,
        )
        final = self.librosa.resample(encoded, orig_sr=16_000, target_sr=24_000)
        self.soundfile.write(str(destination), final, 24_000, subtype="PCM_16")
        persisted, _ = self.librosa.load(str(destination), sr=16_000, mono=True)
        decoded, _ = self.wavmark.decode_watermark(
            self.watermark_model,
            persisted,
            show_progress=False,
        )
        return decoded is not None and self.np.array_equal(decoded.astype(self.np.uint8), payload)

    def synthesize_and_convert(
        self,
        *,
        text: str,
        reference_path: Path,
        destination: Path,
        temporary_root: Path,
    ) -> bool:
        base_path = temporary_root / "kokoro-base.wav"
        converted_path = temporary_root / "openvoice-converted.wav"
        self._synthesize_base(text, base_path)
        source_se = self.converter.extract_se(str(base_path))
        target_se = self.converter.extract_se(str(reference_path))
        self.converter.convert(
            str(base_path),
            src_se=source_se,
            tgt_se=target_se,
            output_path=str(converted_path),
            message="disabled-clicko-applies-pinned-wavmark-after-conversion",
        )
        return self._apply_and_verify_watermark(converted_path, destination)


def _default_runtime_factory(kokoro_root: Path, openvoice_root: Path) -> CloneRuntime:
    return LocalKokoroOpenVoiceRuntime(kokoro_root, openvoice_root)


def _load_descriptor(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_REQUEST_BYTES:
        raise ValueError("openvoice_sidecar_request_missing_or_too_large")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("openvoice_sidecar_request_object_required")
    return payload


def _regular_file_set(root: Path) -> set[str]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("openvoice_sidecar_asset_root_invalid")
    files: set[str] = set()
    resolved_root = root.resolve()
    for item in root.rglob("*"):
        if item.is_symlink():
            raise ValueError("openvoice_sidecar_asset_symlinks_forbidden")
        if not item.is_file():
            continue
        if not item.resolve().is_relative_to(resolved_root):
            raise ValueError("openvoice_sidecar_asset_escaped_root")
        files.add(item.relative_to(root).as_posix())
    return files


def run(
    *,
    request_path: Path,
    reference_path: Path,
    output_path: Path,
    result_path: Path,
    kokoro_root: Path,
    openvoice_root: Path,
    runtime_factory: RuntimeFactory = _default_runtime_factory,
) -> None:
    output_path.unlink(missing_ok=True)
    result_path.unlink(missing_ok=True)
    try:
        if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
            raise ValueError("kokoro_openvoice_offline_runtime_required")
        control_root = request_path.parent.resolve()
        if any(path.parent.resolve() != control_root for path in (output_path, result_path)):
            raise ValueError("kokoro_openvoice_control_path_scope_mismatch")
        if not reference_path.is_file() or reference_path.is_symlink():
            raise ValueError("kokoro_openvoice_reference_required")
        if _regular_file_set(kokoro_root) != KOKORO_FILES:
            raise ValueError("kokoro_openvoice_kokoro_asset_layout_invalid")
        if _regular_file_set(openvoice_root) != OPENVOICE_FILES:
            raise ValueError("kokoro_openvoice_converter_asset_layout_invalid")
        payload = _load_descriptor(request_path)
        speech = payload.get("speech")
        reference = payload.get("reference")
        if (
            payload.get("schemaVersion") != "clicko.voice-clone-sidecar-request.v1"
            or payload.get("pipelineContract") != PIPELINE_CONTRACT
            or not isinstance(speech, dict)
            or not isinstance(reference, dict)
            or speech.get("schemaVersion") != "studio.speech-synthesis-request.v1"
            or speech.get("locale") != "pt-BR"
            or speech.get("audioFormat") != "wav"
            or speech.get("sampleRate") != 24_000
            or not isinstance(speech.get("text"), str)
            or not speech["text"].strip()
            or speech.get("voiceKey") != reference.get("voiceVersionId")
            or reference.get("retentionMode") != "job-ephemeral"
        ):
            raise ValueError("kokoro_openvoice_speech_reference_binding_invalid")
        with wave.open(str(reference_path), "rb") as source:
            if (
                source.getnchannels() != 1
                or source.getsampwidth() != 2
                or source.getframerate() != 24_000
                or source.getnframes() < 72_000
            ):
                raise ValueError("kokoro_openvoice_reference_format_invalid")
        runtime = runtime_factory(kokoro_root, openvoice_root)
        with tempfile.TemporaryDirectory(prefix="clicko-openvoice-", dir=control_root) as temporary:
            verified = runtime.synthesize_and_convert(
                text=speech["text"],
                reference_path=reference_path,
                destination=output_path,
                temporary_root=Path(temporary),
            )
        if not verified:
            raise ValueError("kokoro_openvoice_watermark_verification_failed")
        if not output_path.is_file() or output_path.is_symlink():
            raise ValueError("kokoro_openvoice_output_missing")
        with wave.open(str(output_path), "rb") as output:
            if (
                output.getnchannels() != 1
                or output.getsampwidth() != 2
                or output.getframerate() != 24_000
                or output.getnframes() < 24_000
            ):
                raise ValueError("kokoro_openvoice_output_format_invalid")
        result_path.write_text(
            json.dumps(
                {
                    "schemaVersion": "clicko.voice-clone-sidecar-result.v1",
                    "pipelineContract": PIPELINE_CONTRACT,
                    "watermarkApplied": True,
                    "watermarkScheme": "wavmark-0.0.3-local-verified",
                    "baseVoice": BASE_VOICE,
                    "scriptDigestSha256": hashlib.sha256(speech["text"].encode()).hexdigest(),
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Clicko Kokoro + OpenVoice clone sidecar")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--kokoro-root", required=True, type=Path)
    parser.add_argument("--openvoice-root", required=True, type=Path)
    args = parser.parse_args()
    run(
        request_path=args.request,
        reference_path=args.reference,
        output_path=args.output,
        result_path=args.result,
        kokoro_root=args.kokoro_root,
        openvoice_root=args.openvoice_root,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - candidate image only
    raise SystemExit(main())
