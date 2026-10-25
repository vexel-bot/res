"""One private, offline stock-voice job inside the pinned Linux image."""

import argparse
import json
from pathlib import Path

from app.domain.studios.contracts import SpeechSynthesisRequestV1
from app.domain.studios.speech_assets import KokoroModelAssetManifestV1, verify_kokoro_model_snapshot
from app.providers.studios.kokoro_stock import KokoroStockConfig, KokoroStockVoiceProvider
from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads(args.config.read_text(encoding="utf-8"))
    settings["allowed_voices"] = frozenset(settings["allowed_voices"])
    config = KokoroStockConfig(**settings)
    worker = load_worker_manifest("/opt/clicko/worker-manifest.json")
    if manifest_digest(worker) != config.worker_manifest_digest_sha256:
        raise ValueError("kokoro_sidecar_worker_manifest_mismatch")
    manifest = KokoroModelAssetManifestV1.model_validate_json(
        Path("/opt/clicko/kokoro-model-assets.json").read_text(encoding="utf-8")
    )
    snapshot = Path("/opt/clicko/hf/hub/models--hexgrad--Kokoro-82M/snapshots") / config.model_revision
    if verify_kokoro_model_snapshot(manifest, snapshot) != config.model_digest_sha256:
        raise ValueError("kokoro_sidecar_model_manifest_mismatch")
    request = SpeechSynthesisRequestV1.model_validate_json(args.request.read_text(encoding="utf-8"))
    result = KokoroStockVoiceProvider(config).synthesize(request, args.output, lambda _: None, lambda: False)
    args.result.write_text(result.model_dump_json(by_alias=True), encoding="utf-8")


if __name__ == "__main__":
    main()
