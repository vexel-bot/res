"""Real timbre conversion with a generated stock reference; zero human subjects."""

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
import uuid
import wave
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


def run_container(controller, *, image, inputs, outputs, kokoro_repo, converter, timeout_seconds):
    inspected = controller._docker(["image", "inspect", image])
    metadata = json.loads(inspected.stdout)[0] if inspected.returncode == 0 else {}
    labels = (metadata.get("Config") or {}).get("Labels") or {}
    if metadata.get("Id") != image or labels.get("io.clicko.execution-device") != "cpu":
        raise ValueError("openvoice_cpu_image_binding_mismatch")
    name = "clicko-openvoice-cpu-" + uuid.uuid4().hex
    uid = os.getuid() if hasattr(os, "getuid") else 10001
    gid = os.getgid() if hasattr(os, "getgid") else 10001
    if uid == 0:
        uid = gid = 10001
        os.chown(outputs, uid, gid)
    args = [
        "create",
        "--pull",
        "never",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        f"{uid}:{gid}",
        "--cpus",
        "4",
        "--memory",
        "3g",
        "--memory-swap",
        "3g",
        "--pids-limit",
        "128",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m,mode=1777",
        "--tmpfs",
        "/run/clicko-runtime:rw,exec,nosuid,nodev,size=256m,mode=1777",
    ]
    for source, target, readonly in [
        (inputs, "/job/input", True),
        (outputs, "/job/output", False),
        (kokoro_repo, "/models/kokoro-repo", True),
        (converter, "/models/openvoice", True),
    ]:
        if any(char in str(source) for char in (",", "\n", "\r")):
            raise ValueError("openvoice_cpu_bind_path_invalid")
        args.extend(["--mount", f"type=bind,source={source},target={target}" + (",readonly" if readonly else "")])
    args.extend(
        [
            image,
            "--request",
            "/job/input/request.json",
            "--reference",
            "/job/input/reference.wav",
            "--output",
            "/job/output/converted.wav",
            "--result",
            "/job/output/result.json",
        ]
    )
    process, started = None, time.perf_counter()
    try:
        created = controller._docker(args)
        if created.returncode != 0 or len(created.stdout.strip()) != 64:
            raise RuntimeError("openvoice_cpu_container_creation_failed")
        state = controller._docker(["container", "inspect", created.stdout.strip()])
        if state.returncode != 0:
            raise RuntimeError("openvoice_cpu_inspection_failed")
        info = json.loads(state.stdout)[0]
        observation = {
            "containerId": info["Id"],
            "networkMode": info["HostConfig"]["NetworkMode"],
            "readonlyRootfs": info["HostConfig"]["ReadonlyRootfs"],
            "user": info["Config"]["User"],
            "memoryBytes": info["HostConfig"]["Memory"],
            "nanoCpus": info["HostConfig"]["NanoCpus"],
            "mounts": [{"destination": item["Destination"], "writable": item["RW"]} for item in info["Mounts"]],
        }
        with (outputs / "private-runtime.log").open("wb") as log:
            process = subprocess.Popen(
                [controller.docker_executable, "start", "--attach", created.stdout.strip()],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            while process.poll() is None:
                if time.perf_counter() - started > timeout_seconds:
                    raise TimeoutError("openvoice_cpu_execution_timeout")
                time.sleep(0.2)
            if process.returncode != 0:
                raise RuntimeError("openvoice_cpu_execution_failed_see_private_log")
        return observation
    finally:
        try:
            controller._remove(name)
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-image-digest", required=True)
    parser.add_argument("--clone-image-digest", required=True)
    parser.add_argument("--kokoro-repository", type=Path, required=True)
    parser.add_argument("--openvoice-assets", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--docker-executable", type=Path, default=Path(shutil.which("docker") or "docker"))
    parser.add_argument("--timeout-seconds", type=int, default=900)
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
    observation = run_container(
        stock,
        image=args.clone_image_digest,
        inputs=inputs,
        outputs=outputs,
        kokoro_repo=kokoro_repo,
        converter=converter_root,
        timeout_seconds=args.timeout_seconds,
    )
    result = json.loads((outputs / "result.json").read_text(encoding="utf-8"))
    if (
        result.get("watermarkApplied") is not True
        or result.get("executionDevice") != "cpu"
        or result.get("scriptDigestSha256") != speech.script_digest_sha256
        or result.get("kokoroModelManifestDigestSha256") != base_digest
        or result.get("openvoiceModelManifestDigestSha256") != converter_digest
    ):
        raise ValueError("openvoice_cpu_result_binding_mismatch")
    audio = outputs / "converted.wav"
    with wave.open(str(audio), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 24000:
            raise ValueError("openvoice_cpu_audio_format_mismatch")
        duration = math.ceil(wav.getnframes() * 1000 / wav.getframerate())
    report = {
        "schemaVersion": "clicko.openvoice-cpu-smoke.v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "coverage": "one_synthetic_reference_timbre_conversion_not_human_clone_qualification",
        "humanSubjects": 0,
        "referenceReused": args.reuse_synthetic_reference is not None,
        "providerPromoted": False,
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
