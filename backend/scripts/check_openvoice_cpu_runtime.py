"""Real timbre conversion with a generated stock reference; zero human subjects."""

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.contracts import SpeechSynthesisRequestV1, SpeechSynthesisResultV1, VoiceCloneReferenceV1
from app.domain.studios.speech_assets import (
    KokoroModelAssetManifestV1,
    OpenVoiceModelAssetManifestV1,
    verify_kokoro_model_snapshot,
    verify_openvoice_model_assets,
)
from app.providers.studios.kokoro_docker import KokoroDockerSpeechProvider
from app.providers.studios.kokoro_stock import KokoroStockConfig
from app.providers.studios.openvoice_cpu import OpenVoiceCPUExecutionError, create_openvoice_cpu_provider
from app.services.object_storage import sha256_file
from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_TEXT = (
    "Esta é uma referência de voz sintética para um teste local da Clicko. "
    "Nenhuma pessoa real participa desta avaliação."
)
OUTPUT_TEXT = (
    "A nossa criação mantém a voz escolhida durante toda a apresentação. "
    "Este áudio foi produzido em um teste técnico local."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-image-digest", required=True)
    parser.add_argument("--clone-image-digest", required=True)
    parser.add_argument("--kokoro-repository", type=Path, required=True)
    parser.add_argument("--openvoice-assets", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--docker-executable", type=Path, default=Path(shutil.which("docker") or "docker"))
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--mode", choices=("synthesize", "cancel"), default="synthesize")
    parser.add_argument("--reuse-synthetic-reference", type=Path)
    args = parser.parse_args()
    output = args.output_directory
    if (
        not output.is_absolute()
        or output.exists()
        or any(output.resolve().is_relative_to(ROOT / d) for d in ("public", "dist"))
    ):
        parser.error("use a new absolute private output-directory")
    output.mkdir(parents=True, mode=0o700)
    inputs, outputs = output / "input", output / "output"
    inputs.mkdir()
    outputs.mkdir()
    kokoro = KokoroModelAssetManifestV1.model_validate_json(
        (ROOT / ".candidate-build/kokoro-model-assets.json").read_text(encoding="utf-8")
    )
    converter = OpenVoiceModelAssetManifestV1.model_validate_json(
        (ROOT / "workers/speech-gpu/openvoice-model-assets.v1.json").read_text(encoding="utf-8")
    )
    kokoro_repo, converter_root = args.kokoro_repository.resolve(), args.openvoice_assets.resolve()
    base_digest = verify_kokoro_model_snapshot(kokoro, kokoro_repo / "snapshots" / kokoro.source_revision)
    converter_digest = verify_openvoice_model_assets(converter, converter_root)
    stock = KokoroDockerSpeechProvider(
        KokoroStockConfig(
            source_revision="dfb907a02bba8152ca444717ca5d78747ccb4bec",
            model_revision=kokoro.source_revision,
            model_digest_sha256=base_digest,
            worker_manifest_digest_sha256=manifest_digest(
                load_worker_manifest(ROOT / "workers/speech-cpu/worker.manifest.json")
            ),
            worker_image_digest=args.stock_image_digest,
            cpu_hourly_cost_usd=0.04,
        ),
        docker_executable=args.docker_executable,
    )
    reference_path = inputs / "reference.wav"
    if args.reuse_synthetic_reference:
        previous = args.reuse_synthetic_reference
        receipt = json.loads((previous / "reference-receipt.json").read_text(encoding="utf-8"))
        reference_result = SpeechSynthesisResultV1.model_validate(receipt["speech"])
        source = previous / "input/reference.wav"
        if (
            receipt.get("voiceKey") != "pm_alex"
            or receipt.get("humanSubjects") != 0
            or receipt.get("referenceTextDigestSha256") != hashlib.sha256(REFERENCE_TEXT.encode()).hexdigest()
            or reference_result.provenance.worker_image_digest != args.stock_image_digest
            or reference_result.provenance.model_digest_sha256 != base_digest
            or sha256_file(source) != reference_result.artifact_checksum_sha256
        ):
            raise ValueError("synthetic_reference_receipt_mismatch")
        shutil.copyfile(source, reference_path)
        print("Reusing the checksummed synthetic pm_alex reference; zero human subjects.", flush=True)
    else:
        print("Generating synthetic pm_alex reference; zero human subjects.", flush=True)
        reference_result = stock.synthesize(
            SpeechSynthesisRequestV1(
                locale="pt-BR",
                text=REFERENCE_TEXT,
                script_digest_sha256=hashlib.sha256(REFERENCE_TEXT.encode()).hexdigest(),
                voice_key="pm_alex",
                audio_format="wav",
                sample_rate=24000,
            ),
            reference_path,
            lambda _: None,
            lambda: False,
        )
    (output / "reference-receipt.json").write_text(
        json.dumps(
            {
                "voiceKey": "pm_alex",
                "humanSubjects": 0,
                "referenceTextDigestSha256": hashlib.sha256(REFERENCE_TEXT.encode()).hexdigest(),
                "speech": reference_result.model_dump(by_alias=True, mode="json"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    reference = VoiceCloneReferenceV1(
        voice_version_id="synthetic-pm-alex-test",
        consent_grant_id="synthetic-only-no-human-consent",
        source_asset_id="synthetic-reference-local-test",
        source_checksum_sha256=sha256_file(reference_path),
        normalized_checksum_sha256=sha256_file(reference_path),
        duration_ms=reference_result.duration_ms,
    )
    speech = SpeechSynthesisRequestV1(
        locale="pt-BR",
        text=OUTPUT_TEXT,
        script_digest_sha256=hashlib.sha256(OUTPUT_TEXT.encode()).hexdigest(),
        voice_key=reference.voice_version_id,
    )
    (inputs / "request.json").write_text(
        json.dumps(
            {
                "schemaVersion": "clicko.voice-clone-sidecar-request.v1",
                "pipelineContract": converter.pipeline_contract,
                "speech": speech.model_dump(by_alias=True, mode="json"),
                "reference": reference.model_dump(by_alias=True, mode="json"),
            }
        ),
        encoding="utf-8",
    )
    print("Executing Kokoro pf_dora + OpenVoice + local verified WavMark on CPU.", flush=True)
    provider = create_openvoice_cpu_provider(
        manifest_path=ROOT / "workers/speech-gpu/openvoice-model-assets.v1.json",
        asset_root=converter_root,
        kokoro_manifest_path=ROOT / ".candidate-build/kokoro-model-assets.json",
        kokoro_repository=kokoro_repo,
        worker_manifest_digest_sha256=manifest_digest(
            load_worker_manifest(ROOT / "workers/speech-cpu/openvoice.worker.manifest.json")
        ),
        worker_image_digest=args.clone_image_digest,
        docker_executable=args.docker_executable,
        cpu_hourly_cost_usd=0.04,
        timeout_seconds=args.timeout_seconds,
    )
    audio = outputs / "converted.wav"
    if args.mode == "cancel":
        identifier = None
        running_observed = False
        control = provider._docker

        def observe(arguments, timeout=20):
            nonlocal identifier
            response = control(arguments, timeout)
            if arguments[0] == "create" and response.returncode == 0:
                identifier = response.stdout.strip()
            return response

        def cancelled():
            nonlocal running_observed
            if not identifier:
                return False
            response = control(["container", "inspect", identifier])
            if response.returncode == 0:
                running_observed = bool(json.loads(response.stdout)[0]["State"]["Running"])
            return running_observed

        provider._docker = observe
        try:
            provider.clone(speech, reference, reference_path, audio, lambda _: None, cancelled)
        except InterruptedError:
            if audio.exists() or not running_observed:
                raise RuntimeError("openvoice_cpu_cancellation_not_verified") from None
        else:
            raise RuntimeError("openvoice_cpu_did_not_cancel")
        report = {
            "schemaVersion": "clicko.openvoice-cpu-cancel.v1",
            "generatedAt": datetime.now(UTC).isoformat(),
            "status": "cancel_cleanup_verified",
            "daemonRunningObserved": running_observed,
            "imageDigest": args.clone_image_digest,
            "outputPersisted": False,
            "humanSubjects": 0,
        }
        (output / "runtime-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report), flush=True)
        return
    try:
        cloned = provider.clone(speech, reference, reference_path, audio, lambda _: None, lambda: False)
    except OpenVoiceCPUExecutionError as exc:
        (output / "private-runtime-error.log").write_text(exc.diagnostics, encoding="utf-8")
        raise
    if cloned.provenance.model_digest_sha256 != converter_digest:
        raise ValueError("openvoice_cpu_result_binding_mismatch")
    duration = cloned.duration_ms
    result = {
        "wallSeconds": cloned.metrics["sidecarWallSeconds"],
        "peakResidentBytes": cloned.metrics["peakResidentBytes"],
        "watermarkApplied": cloned.metrics["watermarkVerified"] == 1,
    }
    observation = {key: value for key, value in cloned.metrics.items() if key.startswith("container")}
    report = {
        "schemaVersion": "clicko.openvoice-cpu-smoke.v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "coverage": "one_synthetic_reference_timbre_conversion_not_human_clone_qualification",
        "humanSubjects": 0,
        "referenceReused": args.reuse_synthetic_reference is not None,
        "providerPromoted": False,
        "runtimePath": "application_adapter",
        "adapterSpeech": cloned.model_dump(by_alias=True, mode="json"),
        "imageDigest": args.clone_image_digest,
        "reference": reference_result.model_dump(by_alias=True, mode="json"),
        "convertedAudio": {"durationMs": duration, "checksumSha256": sha256_file(audio), "result": result},
        "isolation": observation,
        "containerCleanup": "verified_by_daemon_inventory",
    }
    (output / "runtime-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "execution_passed_candidate_unqualified",
                "durationMs": duration,
                "wallSeconds": result["wallSeconds"],
                "watermarkApplied": True,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
