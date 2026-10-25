"""Run one synthetic stock-voice smoke test; never register or qualify a model."""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.contracts import SpeechSynthesisRequestV1
from app.domain.studios.speech_assets import KokoroModelAssetManifestV1, kokoro_model_asset_manifest_digest
from app.providers.studios.kokoro_docker import KokoroDockerSpeechProvider, SpeechDockerExecutionError
from app.providers.studios.kokoro_stock import KokoroStockConfig
from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest

TEXT = "Café Aurora: uma pausa boa começa aqui."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--worker-manifest", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--mode", choices=("synthesize", "cancel"), default="synthesize")
    parser.add_argument("--docker-executable", type=Path, default=Path(shutil.which("docker") or "docker"))
    args = parser.parse_args()
    if not args.output_directory.is_absolute():
        parser.error("output-directory must be an absolute private path")
    root = Path(__file__).resolve().parents[2]
    output = args.output_directory.resolve()
    if any(output.is_relative_to(root / folder) for folder in ("public", "dist")):
        parser.error("output-directory must be outside publicly served directories")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    audio, report = output / "stock-voice-smoke.wav", output / "runtime-report.json"
    if audio.exists() or report.exists():
        parser.error("use a new output-directory; previous evidence must be preserved")
    manifest = KokoroModelAssetManifestV1.model_validate_json(args.model_manifest.read_text(encoding="utf-8"))
    provider = KokoroDockerSpeechProvider(
        KokoroStockConfig(
            source_revision=args.source_revision,
            model_revision=manifest.source_revision,
            model_digest_sha256=kokoro_model_asset_manifest_digest(manifest),
            worker_manifest_digest_sha256=manifest_digest(load_worker_manifest(args.worker_manifest)),
            worker_image_digest=args.image_digest,
            cpu_hourly_cost_usd=0.04,
        ),
        docker_executable=args.docker_executable,
    )
    request = SpeechSynthesisRequestV1(
        locale="pt-BR",
        text=TEXT,
        script_digest_sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
        voice_key="pf_dora",
        audio_format="wav",
        sample_rate=24000,
    )
    if args.mode == "cancel":
        checks = 0

        def cancelled():
            nonlocal checks
            checks += 1
            return checks >= 3  # Initial check, daemon creation, then attached execution.

        try:
            provider.synthesize(request, audio, lambda _: None, cancelled)
        except InterruptedError:
            if audio.exists():
                raise RuntimeError("cancelled_runtime_persisted_audio") from None
        else:
            raise RuntimeError("runtime_did_not_cancel")
        payload = {
            "schemaVersion": "clicko.speech-runtime-smoke.v1",
            "generatedAt": datetime.now(UTC).isoformat(),
            "coverage": "real_container_start_and_cancel_not_model_qualification",
            "status": "cancel_cleanup_verified",
            "imageDigest": args.image_digest,
            "outputPersisted": False,
        }
        report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload))
        return
    try:
        result = provider.synthesize(
            request,
            audio,
            lambda _: None,
            lambda: False,
        )
    except SpeechDockerExecutionError as exc:
        (output / "private-runtime-error.log").write_text(exc.diagnostics, encoding="utf-8")
        raise
    payload = {
        "schemaVersion": "clicko.speech-runtime-smoke.v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "coverage": "one_synthetic_stock_voice_case_not_model_qualification",
        "torchImportedInHostProcess": "torch" in sys.modules,
        "speech": result.model_dump(by_alias=True, mode="json"),
    }
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "smoke_passed_candidate_unqualified",
                "durationMs": result.duration_ms,
                "sidecarWallSeconds": result.metrics["sidecarWallSeconds"],
                "torchImportedInHostProcess": payload["torchImportedInHostProcess"],
            }
        )
    )


if __name__ == "__main__":
    main()
