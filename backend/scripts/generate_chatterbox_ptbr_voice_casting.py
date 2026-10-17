from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent.resolve()
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.generate_chatterbox_ptbr_pilot_voice import (  # noqa: E402
    BASE_MODEL_REVISION,
    CHATTERBOX_SOURCE_REVISION,
    PERTH_SOURCE_REVISION,
    PTBR_MODEL_REVISION,
    SAMPLE_RATE,
    _load_fp16_model,
    _probe,
    _sha256,
    _verify_assets,
    _write_json,
)

REFERENCE_ENCODER_SHA256 = "4b16d836bc598509860f6fa068165a8bb5e9ac84f05582dfcf278a5a372879f1"
CASTING_TEXT = (
    "Sua agência tem boas ideias. Mas, na hora de produzir, elas se perdem "
    "entre o roteiro, as cenas e a revisão? Conheça o Clicko Studios."
)
VARIANTS = (
    {
        "id": "a-close-conversation",
        "direction": "conversa próxima, energia contida e final firme",
        "seed": 240_911,
        "exaggeration": 0.419921875,
        "cfgWeight": 0.48,
        "temperature": 0.72,
    },
    {
        "id": "b-agile-warmth",
        "direction": "agilidade e sorriso vocal discreto",
        "seed": 240_912,
        "exaggeration": 0.580078125,
        "cfgWeight": 0.42,
        "temperature": 0.78,
    },
    {
        "id": "c-clear-invitation",
        "direction": "explicação segura, pausas claras e convite natural",
        "seed": 240_913,
        "exaggeration": 0.50,
        "cfgWeight": 0.55,
        "temperature": 0.68,
    },
)


def _outside_repository(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved == REPOSITORY_ROOT or resolved.is_relative_to(REPOSITORY_ROOT):
        raise ValueError(f"{label}_must_stay_outside_repository")
    return resolved


def _validate_reference(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError("voice_reference_missing")
    payload = _probe(path)
    streams = payload.get("streams", [])
    audios = [item for item in streams if item.get("codec_type") == "audio"]
    videos = [item for item in streams if item.get("codec_type") == "video"]
    if len(audios) != 1 or videos:
        raise ValueError("voice_reference_requires_one_audio_and_zero_video_streams")
    duration = float(payload["format"]["duration"])
    if not 8 <= duration <= 30:
        raise ValueError("voice_reference_duration_must_be_between_8_and_30_seconds")
    return {
        "durationSeconds": round(duration, 6),
        "checksumSha256": _sha256(path),
        "sampleRate": int(audios[0]["sample_rate"]),
        "channels": int(audios[0]["channels"]),
    }


def _load_voice_encoder(model: Any, asset_root: Path, torch: Any) -> None:
    from chatterbox.models.voice_encoder import VoiceEncoder

    encoder_path = asset_root / "base" / "ve.pt"
    if not encoder_path.is_file():
        raise FileNotFoundError("chatterbox_voice_encoder_missing")
    if _sha256(encoder_path) != REFERENCE_ENCODER_SHA256:
        raise ValueError("chatterbox_voice_encoder_checksum_mismatch")
    voice_encoder = VoiceEncoder()
    voice_encoder.load_state_dict(torch.load(encoder_path, map_location="cpu", weights_only=True))
    model.ve = voice_encoder.to(model.device).eval()

    # Reference conditioning mixes feature extractors that deliberately emit
    # fp32 tensors with the fp16 weights required to fit this 4 GB GPU. CUDA
    # autocast reconciles those operators, then the resulting floating
    # conditionals are pinned back to fp16 for the main generation pass.
    original_prepare = model.prepare_conditionals
    original_flow = model.s3gen.flow.inference
    reference_codes: dict[str, Any] = {}

    def flow_preserving_integer_codes(*args: Any, **kwargs: Any) -> Any:
        # Upstream S3Token2Mel.forward casts ALL ref_dict tensors to fp16,
        # rounding token ids above 2048. Restore the original integer tensors
        # captured before that cast; converting the rounded values back is lossy.
        kwargs.update(reference_codes)
        return original_flow(*args, **kwargs)

    model.s3gen.flow.inference = flow_preserving_integer_codes

    def prepare_conditionals_autocast(wav_fpath: str, exaggeration: float = 0.5) -> None:
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            original_prepare(wav_fpath, exaggeration=exaggeration)
        reference_codes.clear()
        for key in ("prompt_token", "prompt_token_len"):
            reference_codes[key] = model.conds.gen[key].to(dtype=torch.long).clone()
        model.conds.t3.to(device=model.device, dtype=torch.float16)
        for key, value in model.conds.gen.items():
            if torch.is_tensor(value):
                model.conds.gen[key] = value.to(
                    device=model.device,
                    dtype=torch.float16 if value.dtype.is_floating_point else None,
                )

    model.prepare_conditionals = prepare_conditionals_autocast


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
            "-y",
            str(destination),
        ],
        check=True,
        timeout=300,
    )


def _write_audio(path: Path, waveform: Any) -> None:
    import soundfile as sf

    samples = waveform.detach().float().cpu().numpy().reshape(-1)
    if samples.size == 0:
        raise RuntimeError("chatterbox_synthesis_returned_no_audio")
    sf.write(path, samples, SAMPLE_RATE, subtype="PCM_16")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate three private PT-BR voice-casting samples from an authorized reference."
    )
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--consent-grant-id", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(r"C:\Users\edugu\Downloads\clicko-private-evaluation\voice-casting\caio-vale"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if os.getenv("HF_HUB_OFFLINE") != "1":
        raise RuntimeError("chatterbox_offline_execution_required")
    if os.getenv("CLICKO_CHATTERBOX_SOURCE_REVISION") != CHATTERBOX_SOURCE_REVISION:
        raise RuntimeError("chatterbox_source_revision_attestation_mismatch")
    if os.getenv("CLICKO_VOICE_CLONE_AUTHORIZED") != "1":
        raise RuntimeError("voice_clone_authorization_attestation_required")
    if not args.consent_grant_id.strip():
        raise ValueError("consent_grant_id_required")

    reference = _outside_repository(args.reference, "voice_reference")
    output_dir = _outside_repository(args.output_dir, "voice_casting_output")
    reference_probe = _validate_reference(reference)
    asset_root = args.asset_root.resolve()
    verified_assets = _verify_assets(asset_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "casting-result.json"
    if manifest_path.exists() or any(output_dir.glob("caio-casting-*.wav")):
        raise FileExistsError("voice_casting_output_already_exists")

    model, torch = _load_fp16_model(asset_root)
    _load_voice_encoder(model, asset_root, torch)
    started = time.perf_counter()
    outputs: list[dict[str, Any]] = []
    for variant in VARIANTS:
        torch.manual_seed(variant["seed"])
        torch.cuda.manual_seed_all(variant["seed"])
        raw = output_dir / f"caio-casting-{variant['id']}.raw.wav"
        destination = output_dir / f"caio-casting-{variant['id']}.wav"
        waveform = model.generate(
            CASTING_TEXT,
            language_id="pt",
            audio_prompt_path=str(reference),
            exaggeration=variant["exaggeration"],
            cfg_weight=variant["cfgWeight"],
            temperature=variant["temperature"],
        )
        _write_audio(raw, waveform)
        _normalize(raw, destination)
        raw.unlink(missing_ok=True)
        probe = _probe(destination)
        outputs.append(
            {
                **variant,
                "filename": destination.name,
                "checksumSha256": _sha256(destination),
                "durationSeconds": round(float(probe["format"]["duration"]), 6),
            }
        )

    manifest = {
        "schemaVersion": "studio.private-voice-casting-result.v1",
        "createdAt": datetime.now(UTC).isoformat(),
        "publicationState": "private_review",
        "promoted": False,
        "consentGrantId": args.consent_grant_id,
        "reference": reference_probe,
        "referencePathPersisted": False,
        "text": CASTING_TEXT,
        "provider": "chatterbox-multilingual-pt-br-reference-conditioned",
        "sourceRevision": CHATTERBOX_SOURCE_REVISION,
        "ptbrModelRevision": PTBR_MODEL_REVISION,
        "baseModelRevision": BASE_MODEL_REVISION,
        "perthSourceRevision": PERTH_SOURCE_REVISION,
        "voiceEncoderChecksumSha256": REFERENCE_ENCODER_SHA256,
        "verifiedAssets": verified_assets,
        "outputs": outputs,
        "activeComputeSeconds": round(time.perf_counter() - started, 6),
        "humanSelection": None,
    }
    _write_json(manifest_path, manifest)
    print(json.dumps({"status": "private_review", "outputs": outputs}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
