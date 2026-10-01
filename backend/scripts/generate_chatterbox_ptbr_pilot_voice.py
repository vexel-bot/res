from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from types import MethodType
from typing import Any

CHATTERBOX_SOURCE_REVISION = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"
PTBR_MODEL_REVISION = "b3952f18bc2eaa72b9bd7c17d2c4653bcad4770d"
BASE_MODEL_REVISION = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
PERTH_SOURCE_REVISION = "ff1c8ac55a976971245cdd53c18d6131ca00d993"
SAMPLE_RATE = 24_000
SEED = 240_904
EXAGGERATION = 0.60009765625  # exact fp16 representation near 0.60
CFG_WEIGHT = 0.35
TEMPERATURE = 0.78
SCRIPT = (
    "Se sua agência começa um vídeo escolhendo cenas, ela já começou pela etapa errada. "
    "Gerar clipes é só o começo. Sem uma lógica comum, oferta, audiência e referências viram decisões soltas "
    "na produção. O Clicko Studios organiza estratégia, copy, roteiro, personagem e produção em um fluxo "
    "revisável. Cada decisão fica ligada ao objetivo da campanha. Assim, sua equipe pode avaliar o que funciona, "
    "corrigir a etapa certa e preservar a identidade de cada projeto. Quer testar esse processo na sua agência? "
    "Solicite acesso ao piloto do Clicko Studios."
)
REQUIRED_ASSETS = {
    "pt-br/t3_pt_br.safetensors": "074aaf65255eb9cb960288f7cc72e09d3b5008f6e0b14868c0d4e5b0bd7cbb6c",
    "pt-br/s3gen_v3.safetensors": "4a46190f3dccc2230fbb3488a930bccc925862ee68f2662433dfcfe93ce6c2cb",
    "pt-br/grapheme_mtl_merged_expanded_v1.json": "69632f47220a788a52ce2661d096453c5655e9bf25289d89a8d832c46ee07dbf",
    "base/conds.pt": "6552d70568833628ba019c6b03459e77fe71ca197d5c560cef9411bee9d87f4e",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_assets(asset_root: Path) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for relative, expected in REQUIRED_ASSETS.items():
        path = asset_root / Path(relative)
        if not path.is_file():
            raise FileNotFoundError(f"chatterbox_asset_missing:{relative}")
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"chatterbox_asset_checksum_mismatch:{relative}")
        verified.append(
            {
                "relativePath": relative,
                "checksumSha256": actual,
                "byteCount": path.stat().st_size,
            }
        )
    return verified


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_fp16_model(asset_root: Path):
    import torch
    from chatterbox.models.s3gen import S3Gen
    from chatterbox.models.t3 import T3
    from chatterbox.models.t3.modules.t3_config import T3Config
    from chatterbox.models.tokenizers import MTLTokenizer
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS, Conditionals
    from safetensors import safe_open

    if not torch.cuda.is_available():
        raise RuntimeError("chatterbox_cuda_required_for_this_host")
    total_memory = torch.cuda.get_device_properties(0).total_memory
    if total_memory < 3_800_000_000:
        raise RuntimeError("chatterbox_insufficient_cuda_memory")

    device = torch.device("cuda:0")
    dtype = torch.float16
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)

    def construct_fp16_on_cuda(factory):
        previous = torch.get_default_dtype()
        torch.set_default_dtype(dtype)
        try:
            with torch.device(device):
                return factory()
        finally:
            torch.set_default_dtype(previous)

    def load_incrementally(module, checkpoint: Path, *, allowed_missing=frozenset()):
        targets = dict(module.named_parameters()) | dict(module.named_buffers())
        with safe_open(checkpoint, framework="pt", device="cpu") as source:
            source_keys = set(source.keys())
            missing = set(targets) - source_keys - set(allowed_missing)
            unexpected = source_keys - set(targets)
            if missing or unexpected:
                raise ValueError(f"chatterbox_checkpoint_incompatible:{checkpoint.name}")
            with torch.no_grad():
                for key in source.keys():
                    target = targets[key]
                    tensor = source.get_tensor(key).to(
                        device=target.device,
                        dtype=target.dtype,
                    )
                    target.copy_(tensor)
                    del tensor
        gc.collect()
        torch.cuda.empty_cache()

    # Construct directly on the GPU in fp16 and stream each safetensor into its
    # destination. This avoids materializing multi-gigabyte fp32 state dicts.
    t3 = construct_fp16_on_cuda(lambda: T3(T3Config.multilingual()))
    load_incrementally(
        t3,
        asset_root / "pt-br" / "t3_pt_br.safetensors",
        allowed_missing={
            "tfmr.rotary_emb.inv_freq",
            "tfmr.rotary_emb.original_inv_freq",
        },
    )
    t3.eval()

    s3gen = construct_fp16_on_cuda(S3Gen)
    load_incrementally(
        s3gen,
        asset_root / "pt-br" / "s3gen_v3.safetensors",
        allowed_missing={"tokenizer._mel_filters", "tokenizer.window", "trim_fade"},
    )
    s3gen.eval()

    # The harmonic vocoder uses CUDA operations that intentionally emit fp32
    # sine waves and complex spectra. Keep only this small submodule in fp32;
    # the T3 and flow models remain fp16.
    s3gen.mel2wav.float()

    def hift_inference_fp32(self, speech_feat, cache_source=None):
        if cache_source is None:
            cache_source = torch.zeros(
                1, 1, 0, device=self.device, dtype=torch.float32
            )
        else:
            cache_source = cache_source.to(dtype=torch.float32)
        return self.mel2wav.inference(
            speech_feat=speech_feat.to(dtype=torch.float32),
            cache_source=cache_source,
        )

    s3gen.hift_inference = MethodType(hift_inference_fp32, s3gen)

    tokenizer = MTLTokenizer(str(asset_root / "pt-br" / "grapheme_mtl_merged_expanded_v1.json"))
    conditionals = Conditionals.load(asset_root / "base" / "conds.pt", map_location="cpu")
    conditionals.t3.to(device=device, dtype=dtype)
    for key, value in conditionals.gen.items():
        if torch.is_tensor(value):
            conditionals.gen[key] = value.to(
                device=device,
                dtype=dtype if value.dtype.is_floating_point else None,
            )
    conditionals.t3.emotion_adv = torch.full((1, 1, 1), EXAGGERATION, device=device, dtype=dtype)

    # The voice encoder is intentionally absent: this runner cannot ingest a
    # reference clip and therefore cannot perform voice cloning.
    model = ChatterboxMultilingualTTS(
        t3=t3,
        s3gen=s3gen,
        ve=None,
        tokenizer=tokenizer,
        device=str(device),
        conds=conditionals,
    )
    return model, torch


def _normalize(raw: Path, destination: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(raw),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ],
        check=True,
        timeout=600,
    )


def _probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the Caio Vale PT-BR stock voice locally with no voice cloning."
    )
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../artifacts/studios/avatar-pilots/caio-vale"),
    )
    args = parser.parse_args()
    if os.getenv("HF_HUB_OFFLINE") != "1":
        raise RuntimeError("chatterbox_offline_execution_required")
    if os.getenv("CLICKO_CHATTERBOX_SOURCE_REVISION") != CHATTERBOX_SOURCE_REVISION:
        raise RuntimeError("chatterbox_source_revision_attestation_mismatch")

    asset_root = args.asset_root.resolve()
    assets = _verify_assets(asset_root)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "clicko-studios-caio-vale-chatterbox-ptbr-v1.wav"
    result_path = output_dir / "clicko-studios-caio-vale-chatterbox-ptbr-v1.result.json"
    raw = output_dir / "clicko-studios-caio-vale-chatterbox-ptbr-v1.raw.wav"
    if destination.exists() or result_path.exists() or raw.exists():
        raise FileExistsError("chatterbox_pilot_voice_output_already_exists")

    started = time.perf_counter()
    model, torch = _load_fp16_model(asset_root)
    waveform = model.generate(
        SCRIPT,
        language_id="pt",
        audio_prompt_path=None,
        exaggeration=EXAGGERATION,
        cfg_weight=CFG_WEIGHT,
        temperature=TEMPERATURE,
    )
    import soundfile as sf

    samples = waveform.detach().float().cpu().numpy().reshape(-1)
    if samples.size == 0:
        raise RuntimeError("chatterbox_synthesis_returned_no_audio")
    sf.write(raw, samples, SAMPLE_RATE, subtype="PCM_16")
    _normalize(raw, destination)
    raw.unlink(missing_ok=True)

    probe = _probe(destination)
    streams = probe.get("streams", [])
    audio_streams = [item for item in streams if item.get("codec_type") == "audio"]
    video_streams = [item for item in streams if item.get("codec_type") == "video"]
    if len(audio_streams) != 1 or video_streams:
        raise ValueError("chatterbox_canonical_stream_layout_invalid")
    duration = float(probe["format"]["duration"])
    duration_accepted = 24 <= duration <= 45
    result = {
        "schemaVersion": "studio.local-stock-voice-pilot-result.v1",
        "provider": "chatterbox-multilingual-pt-br-stock",
        "voiceKey": "builtin-stock-voice",
        "locale": "pt-BR",
        "voiceClone": False,
        "referenceAudioProvided": False,
        "voiceEncoderLoaded": False,
        "watermark": "PerTh",
        "sampleRate": SAMPLE_RATE,
        "channels": 1,
        "durationSeconds": round(duration, 6),
        "durationPolicy": "content_fit-24-45-seconds",
        "durationAccepted": duration_accepted,
        "artifactChecksumSha256": _sha256(destination),
        "byteCount": destination.stat().st_size,
        "scriptDigestSha256": hashlib.sha256(SCRIPT.encode("utf-8")).hexdigest(),
        "sourceRevision": CHATTERBOX_SOURCE_REVISION,
        "ptbrModelRevision": PTBR_MODEL_REVISION,
        "baseModelRevision": BASE_MODEL_REVISION,
        "perthSourceRevision": PERTH_SOURCE_REVISION,
        "assets": assets,
        "generation": {
            "seed": SEED,
            "precision": "fp16",
            "exaggeration": EXAGGERATION,
            "cfgWeight": CFG_WEIGHT,
            "temperature": TEMPERATURE,
            "normalization": "EBU-R128-I-16-TP-1.5-LRA-7",
        },
        "runtime": {
            "mode": "isolated-windows-cuda-evaluation",
            "promoted": False,
            "cudaDevice": torch.cuda.get_device_name(0),
            "packages": {
                name: importlib.metadata.version(name)
                for name in (
                    "chatterbox-tts",
                    "torch",
                    "torchaudio",
                    "transformers",
                    "resemble-perth",
                )
            },
        },
        "activeComputeSeconds": round(time.perf_counter() - started, 6),
        "generatedAt": datetime.now(UTC).isoformat(),
        "publicationState": "private_review",
    }
    _write_json(result_path, result)
    print(json.dumps(result, ensure_ascii=False))
    if not duration_accepted:
        raise RuntimeError("chatterbox_wav_outside_content_fit_duration")


if __name__ == "__main__":
    main()
