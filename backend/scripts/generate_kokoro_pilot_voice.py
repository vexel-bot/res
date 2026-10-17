from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
from huggingface_hub import hf_hub_download
from kokoro import KPipeline
from kokoro import model as kokoro_model
from kokoro import pipeline as kokoro_pipeline

KOKORO_SOURCE_REVISION = "dfb907a02bba8152ca444717ca5d78747ccb4bec"
MISAKI_SOURCE_REVISION = "fba1236595f2d2bf21d414ba6e57d25256afada3"
MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_MANIFEST_DIGEST = "fec04722c639685b8a138ae036a6aeda743f8b848acaf05f59279c599ec41aa3"
SAMPLE_RATE = 24_000
SCRIPT = (
    "Se sua agência começa um vídeo escolhendo cenas, ela já começou pela etapa errada. "
    "Gerar clipes é só o começo. Sem uma lógica comum, oferta, audiência e referências viram decisões soltas "
    "na produção. O Clicko Studios organiza estratégia, copy, roteiro, personagem e produção em um fluxo "
    "revisável. Cada decisão fica ligada ao objetivo da campanha. Assim, sua equipe pode avaliar o que funciona, "
    "corrigir a etapa certa e preservar a identidade de cada projeto. Quer testar esse processo na sua agência? "
    "Solicite acesso ao piloto do Clicko Studios."
)


def _pcm16(audio: Any) -> bytes:
    if hasattr(audio, "detach"):
        audio = audio.detach()
    if hasattr(audio, "cpu"):
        audio = audio.cpu()
    if hasattr(audio, "numpy"):
        audio = audio.numpy()
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size == 0 or not np.isfinite(samples).all():
        raise ValueError("kokoro_audio_samples_invalid")
    return (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Caio Vale pilot stock voice locally.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../artifacts/studios/avatar-pilots/caio-vale"),
    )
    parser.add_argument("--script-file", type=Path)
    parser.add_argument("--output-stem", default="clicko-studios-caio-vale-pm-alex-v1")
    parser.add_argument("--min-duration", type=float, default=24)
    parser.add_argument("--max-duration", type=float, default=45)
    args = parser.parse_args()
    if Path(args.output_stem).name != args.output_stem or not args.output_stem.strip():
        parser.error("output-stem must be a filename without directories")
    if not 0 < args.min_duration <= args.max_duration <= 120:
        parser.error("duration range must be within 0–120 seconds")
    script = args.script_file.read_text(encoding="utf-8-sig").strip() if args.script_file else SCRIPT
    if not script or len(script) > 5000:
        parser.error("script must contain 1–5000 characters")
    if os.getenv("HF_HUB_OFFLINE") != "1":
        raise RuntimeError("kokoro_offline_execution_required")
    if os.getenv("CLICKO_KOKORO_MODEL_REVISION") != MODEL_REVISION:
        raise RuntimeError("kokoro_model_revision_attestation_mismatch")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{args.output_stem}.wav"
    result_path = output_dir / f"{args.output_stem}.result.json"
    if destination.exists() or result_path.exists():
        raise FileExistsError("pilot_voice_output_already_exists")

    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))

    def pinned_download(*, repo_id: str, filename: str, **_: Any) -> str:
        return hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            revision=MODEL_REVISION,
            local_files_only=True,
        )

    # Upstream omits `revision`; bind both import sites to the audited snapshot.
    kokoro_model.hf_hub_download = pinned_download
    kokoro_pipeline.hf_hub_download = pinned_download
    started = time.perf_counter()
    pipeline = KPipeline(
        lang_code="p",
        repo_id="hexgrad/Kokoro-82M",
        device="cpu",
    )
    parts: list[bytes] = []
    for result in pipeline(script, voice="pm_alex", speed=1.0, split_pattern=r"\n+"):
        if result.audio is not None:
            parts.append(_pcm16(result.audio))
    if not parts:
        raise RuntimeError("kokoro_synthesis_returned_no_audio")

    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for part in parts:
            output.writeframes(part)

    byte_count = destination.stat().st_size
    frame_count = sum(len(part) // 2 for part in parts)
    duration_seconds = frame_count / SAMPLE_RATE
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    duration_accepted = args.min_duration <= duration_seconds <= args.max_duration
    result = {
        "schemaVersion": "studio.local-stock-voice-pilot-result.v1",
        "provider": "kokoro-82m-stock",
        "voiceKey": "pm_alex",
        "locale": "pt-BR",
        "voiceClone": False,
        "sampleRate": SAMPLE_RATE,
        "channels": 1,
        "speed": 1.0,
        "durationSeconds": round(duration_seconds, 6),
        "durationPolicy": f"content_fit-{args.min_duration:g}-{args.max_duration:g}-seconds",
        "durationAccepted": duration_accepted,
        "artifactChecksumSha256": checksum,
        "byteCount": byte_count,
        "scriptDigestSha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "sourceRevision": KOKORO_SOURCE_REVISION,
        "misakiRevision": MISAKI_SOURCE_REVISION,
        "modelRevision": MODEL_REVISION,
        "modelManifestDigestSha256": MODEL_MANIFEST_DIGEST,
        "runtime": {
            "mode": "isolated-windows-cpu-evaluation",
            "promoted": False,
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("kokoro", "misaki", "torch", "transformers", "espeakng-loader")
            },
        },
        "activeComputeSeconds": round(time.perf_counter() - started, 6),
        "generatedAt": datetime.now(UTC).isoformat(),
        "publicationState": "private_review",
    }
    _write_json(result_path, result)
    print(json.dumps(result, ensure_ascii=False))
    if not duration_accepted:
        raise RuntimeError("kokoro_wav_outside_content_fit_duration")


if __name__ == "__main__":
    main()
