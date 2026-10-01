from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.generate_chatterbox_ptbr_pilot_voice import (  # noqa: E402
    CHATTERBOX_SOURCE_REVISION,
    SCRIPT,
    _load_fp16_model,
    _probe,
    _sha256,
    _verify_assets,
    _write_json,
)
from scripts.generate_chatterbox_ptbr_voice_casting import (  # noqa: E402
    _load_voice_encoder,
    _normalize,
    _outside_repository,
    _validate_reference,
    _write_audio,
)

SEED = 240_921
EXAGGERATION = 0.419921875
CFG_WEIGHT = 0.48
TEMPERATURE = 0.72
AD_SCRIPT = SCRIPT.replace("Gerar clipes é só o começo. ", "").replace("Quer testar esse processo na sua agência? ", "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the full private Caio Vale ad voice from an authorized reference."
    )
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--consent-grant-id", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(r"C:\Users\edugu\Downloads\clicko-private-evaluation\voice-casting\caio-vale"),
    )
    args = parser.parse_args()
    if os.getenv("HF_HUB_OFFLINE") != "1":
        raise RuntimeError("chatterbox_offline_execution_required")
    if os.getenv("CLICKO_CHATTERBOX_SOURCE_REVISION") != CHATTERBOX_SOURCE_REVISION:
        raise RuntimeError("chatterbox_source_revision_attestation_mismatch")
    if os.getenv("CLICKO_VOICE_CLONE_AUTHORIZED") != "1":
        raise RuntimeError("voice_clone_authorization_attestation_required")

    reference = _outside_repository(args.reference, "voice_reference")
    output_dir = _outside_repository(args.output_dir, "voice_output")
    reference_probe = _validate_reference(reference)
    asset_root = args.asset_root.resolve()
    verified_assets = _verify_assets(asset_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = output_dir / "caio-full-ad-v3.raw.wav"
    destination = output_dir / "caio-full-ad-v3.wav"
    manifest_path = output_dir / "caio-full-ad-v3.result.json"
    if raw.exists() or destination.exists() or manifest_path.exists():
        raise FileExistsError("full_ad_voice_output_already_exists")

    started = time.perf_counter()
    model, torch = _load_fp16_model(asset_root)
    _load_voice_encoder(model, asset_root, torch)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    from functools import partial

    import chatterbox.models.t3.t3 as t3_module
    import tqdm

    # Quiet the per-token progress; print sentence-level progress instead.
    t3_module.tqdm = partial(tqdm.tqdm, disable=True)
    sentences = re.split(r"(?<=[.!?])\s+", AD_SCRIPT)
    parts = []
    segments = []
    position = 0.0
    for index, sentence in enumerate(sentences):
        print(json.dumps({"sentence": index + 1, "of": len(sentences)}), flush=True)
        part = model.generate(
            sentence,
            language_id="pt",
            audio_prompt_path=str(reference),
            exaggeration=EXAGGERATION,
            cfg_weight=CFG_WEIGHT,
            temperature=TEMPERATURE,
        )
        seconds = part.shape[-1] / model.sr
        if seconds >= 39.9:
            raise RuntimeError("sentence_reached_token_limit")
        segments.append({"text": sentence, "startSeconds": position, "endSeconds": position + seconds})
        parts.append(part)
        position += seconds
        if index < len(sentences) - 1:
            parts.append(torch.zeros((1, int(model.sr * 0.12))))
            position += 0.12
    waveform = torch.cat(parts, dim=-1)
    _write_audio(raw, waveform)
    _normalize(raw, destination)
    raw.unlink(missing_ok=True)
    duration = round(float(_probe(destination)["format"]["duration"]), 6)

    result = {
        "schemaVersion": "studio.private-cloned-ad-voice-result.v1",
        "createdAt": datetime.now(UTC).isoformat(),
        "publicationState": "private_review",
        "promoted": False,
        "provider": "chatterbox-multilingual-pt-br-reference-conditioned",
        "selectedCastingVariant": "a-close-conversation",
        "selectionBasis": "delegated_voice_choice_and_technical_qc",
        "consentGrantId": args.consent_grant_id,
        "reference": reference_probe,
        "referencePathPersisted": False,
        "script": AD_SCRIPT,
        "contentFitPassed": 24 <= duration <= 45,
        "segments": segments,
        "referenceIntegerCodesPreserved": True,
        "durationSeconds": duration,
        "artifactFilename": destination.name,
        "artifactChecksumSha256": _sha256(destination),
        "generation": {
            "seed": SEED,
            "exaggeration": EXAGGERATION,
            "cfgWeight": CFG_WEIGHT,
            "temperature": TEMPERATURE,
        },
        "verifiedAssets": verified_assets,
        "activeComputeSeconds": round(time.perf_counter() - started, 6),
        "humanNaturalnessStatus": "pending_review",
    }
    _write_json(manifest_path, result)
    if not result["contentFitPassed"]:
        raise RuntimeError("full_ad_voice_outside_content_fit_duration")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
