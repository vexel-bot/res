"""Consent-bound OpenVoice CPU port; neural dependencies stay in its offline image."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path

from ...domain.studios.contracts import SpeechProvenanceV1, SpeechSynthesisResultV1
from ...domain.studios.execution import OPENVOICE_CPU_PROVIDER
from ...domain.studios.speech_assets import (
    KokoroModelAssetManifestV1,
    OpenVoiceModelAssetManifestV1,
    kokoro_model_asset_manifest_digest,
    openvoice_model_asset_manifest_digest,
    verify_kokoro_model_snapshot,
    verify_openvoice_model_assets,
)
from ...services.object_storage import sha256_file
from .offline_docker import OfflineDockerControl

PIPELINE = "clicko.kokoro-openvoice-v2.pt-br.v1"


@dataclass(frozen=True)
class OpenVoiceCPUConfig:
    source_revision: str
    model_digest_sha256: str
    kokoro_model_digest_sha256: str
    worker_manifest_digest_sha256: str
    worker_image_digest: str
    cpu_hourly_cost_usd: float
    timeout_seconds: float = 1800

    def __post_init__(self):
        if not re.fullmatch(r"[a-f0-9]{40}", self.source_revision):
            raise ValueError("openvoice_cpu_source_revision_invalid")
        if any(
            not re.fullmatch(r"[a-f0-9]{64}", digest)
            for digest in (
                self.model_digest_sha256,
                self.kokoro_model_digest_sha256,
                self.worker_manifest_digest_sha256,
            )
        ) or not re.fullmatch(r"sha256:[a-f0-9]{64}", self.worker_image_digest):
            raise ValueError("openvoice_cpu_runtime_digest_invalid")
        if not math.isfinite(self.cpu_hourly_cost_usd) or self.cpu_hourly_cost_usd <= 0:
            raise ValueError("openvoice_cpu_hourly_cost_required")
        if not math.isfinite(self.timeout_seconds) or not 1 <= self.timeout_seconds <= 7200:
            raise ValueError("openvoice_cpu_timeout_invalid")


class OpenVoiceCPUExecutionError(RuntimeError):
    def __init__(self, diagnostics):
        super().__init__("openvoice_cpu_execution_failed")
        self.diagnostics = diagnostics


class OpenVoiceCPUProvider(OfflineDockerControl):
    name = OPENVOICE_CPU_PROVIDER
    execution_environment = "local"

    def __init__(self, config, *, docker_executable, manifest, asset_root, kokoro_manifest, kokoro_repository):
        super().__init__(docker_executable)
        self.config = config
        self.manifest, self.asset_root = manifest, Path(asset_root)
        self.kokoro_manifest, self.kokoro_repository = kokoro_manifest, Path(kokoro_repository)
        self.version = (
            f"0.1.0+ov-{config.source_revision[:12]}.models-{config.model_digest_sha256[:8]}"
            f".base-{config.kokoro_model_digest_sha256[:8]}.cpu"
        )

    def _require_image(self):
        inspected = self._docker(["image", "inspect", self.config.worker_image_digest])
        try:
            image = json.loads(inspected.stdout)[0]
            labels = image["Config"].get("Labels") or {}
            valid = (
                inspected.returncode == 0
                and image["Id"] == self.config.worker_image_digest
                and labels.get("io.clicko.execution-device") == "cpu"
                and labels.get("io.clicko.model-manifest.digest") == self.config.model_digest_sha256
                and labels.get("io.clicko.base-model-manifest.digest") == self.config.kokoro_model_digest_sha256
                and labels.get("io.clicko.worker-manifest.digest") == self.config.worker_manifest_digest_sha256
            )
        except (ValueError, IndexError, KeyError, TypeError):
            valid = False
        if not valid:
            raise ValueError("openvoice_cpu_image_binding_mismatch")

    def _inspect_container(self, identifier, user):
        inspected = self._docker(["container", "inspect", identifier])
        try:
            info = json.loads(inspected.stdout)[0]
            host = info["HostConfig"]
            mounts = {item["Destination"]: (item["Type"], item["RW"]) for item in info["Mounts"]}
            valid = (
                inspected.returncode == 0
                and info["Config"]["Image"] == self.config.worker_image_digest
                and info["Config"]["User"] == user
                and host["NetworkMode"] == "none"
                and host["ReadonlyRootfs"] is True
                and host["Memory"] == 3 * 1024**3
                and host["MemorySwap"] == 3 * 1024**3
                and host["NanoCpus"] == 4_000_000_000
                and host["PidsLimit"] == 128
                and "ALL" in host["CapDrop"]
                and any(item in {"no-new-privileges", "no-new-privileges=true"} for item in host["SecurityOpt"])
                and mounts
                == {
                    "/job/input": ("bind", False),
                    "/job/output": ("bind", True),
                    "/models/kokoro-repo": ("bind", False),
                    "/models/openvoice": ("bind", False),
                }
            )
        except (ValueError, IndexError, KeyError, TypeError):
            valid = False
        if not valid:
            raise ValueError("openvoice_cpu_container_isolation_unverified")
        return {
            "containerNetworkDisabled": 1.0,
            "containerReadonlyRoot": 1.0,
            "containerCpuLimit": host["NanoCpus"] / 1e9,
            "containerMemoryLimitBytes": float(host["Memory"]),
        }

    def clone(self, request, reference, reference_path, destination, progress, is_cancelled):
        if request.locale != "pt-BR" or request.audio_format != "wav" or request.sample_rate != 24000:
            raise ValueError("openvoice_cpu_requires_pt_br_wav_24khz")
        if request.speed != 1:
            raise ValueError("openvoice_cpu_speed_not_supported")
        if request.voice_key != reference.voice_version_id:
            raise ValueError("openvoice_cpu_voice_version_mismatch")
        if is_cancelled():
            raise InterruptedError("voice_clone_cancelled_before_inference")
        reference_path, destination = Path(reference_path), Path(destination)
        if (
            reference_path.is_symlink()
            or not reference_path.is_file()
            or sha256_file(reference_path) != reference.normalized_checksum_sha256.lower()
        ):
            raise ValueError("openvoice_cpu_reference_checksum_mismatch")
        with wave.open(str(reference_path), "rb") as wav:
            measured = math.ceil(wav.getnframes() * 1000 / wav.getframerate())
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000) or abs(
                measured - reference.duration_ms
            ) > 1:
                raise ValueError("openvoice_cpu_reference_format_mismatch")
        if destination.exists():
            raise ValueError("openvoice_cpu_destination_must_be_new")
        snapshot = self.kokoro_repository / "snapshots" / self.kokoro_manifest.source_revision
        if (
            verify_kokoro_model_snapshot(self.kokoro_manifest, snapshot) != self.config.kokoro_model_digest_sha256
            or verify_openvoice_model_assets(self.manifest, self.asset_root) != self.config.model_digest_sha256
            or any(item.is_symlink() for item in snapshot.rglob("*"))
        ):
            raise ValueError("openvoice_cpu_model_assets_mismatch")
        self._require_image()
        started, name = time.perf_counter(), "clicko-voice-clone-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix="clicko-openvoice-job-") as temporary:
            root = Path(temporary).resolve()
            inputs, outputs = root / "input", root / "output"
            inputs.mkdir()
            outputs.mkdir()
            uid = os.getuid() if hasattr(os, "getuid") else 10001
            gid = os.getgid() if hasattr(os, "getgid") else 10001
            if uid == 0:
                uid = gid = 10001
                os.chown(outputs, uid, gid)
            shutil.copyfile(reference_path, inputs / "reference.wav")
            (inputs / "request.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": "clicko.voice-clone-sidecar-request.v1",
                        "pipelineContract": PIPELINE,
                        "speech": request.model_dump(by_alias=True, mode="json"),
                        "reference": reference.model_dump(by_alias=True, mode="json"),
                        "executionBinding": {
                            "workerManifestDigestSha256": self.config.worker_manifest_digest_sha256,
                            "workerImageDigest": self.config.worker_image_digest,
                        },
                    }
                ),
                encoding="utf-8",
            )
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
            for source, target, readonly in (
                (inputs, "/job/input", True),
                (outputs, "/job/output", False),
                (self.kokoro_repository, "/models/kokoro-repo", True),
                (self.asset_root, "/models/openvoice", True),
            ):
                source = source.resolve()
                if any(char in str(source) for char in (",", "\n", "\r")):
                    raise ValueError("openvoice_cpu_bind_path_invalid")
                args += ["--mount", f"type=bind,source={source},target={target}" + (",readonly" if readonly else "")]
            args += [
                self.config.worker_image_digest,
                "--request",
                "/job/input/request.json",
                "--reference",
                "/job/input/reference.wav",
                "--output",
                "/job/output/speech.wav",
                "--result",
                "/job/output/result.json",
            ]
            process = None
            progress(5)
            with (root / "runtime.log").open("wb") as log:
                try:
                    created = self._docker(args)
                    identifier = created.stdout.strip()
                    if created.returncode != 0 or not re.fullmatch(r"[a-f0-9]{64}", identifier):
                        raise RuntimeError("openvoice_cpu_container_creation_failed")
                    isolation_metrics = self._inspect_container(identifier, f"{uid}:{gid}")
                    if is_cancelled():
                        raise InterruptedError("voice_clone_cancelled_during_startup")
                    process = subprocess.Popen(
                        [self.docker_executable, "start", "--attach", identifier],
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=log,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    while process.poll() is None:
                        if is_cancelled():
                            raise InterruptedError("voice_clone_cancelled_during_inference")
                        if time.perf_counter() - started > self.config.timeout_seconds:
                            raise TimeoutError("openvoice_cpu_execution_timeout")
                        time.sleep(0.1)
                    if process.returncode != 0:
                        log.flush()
                        raise OpenVoiceCPUExecutionError(
                            (root / "runtime.log").read_bytes()[:131072].decode("utf-8", "replace")
                        )
                finally:
                    try:
                        self._remove(name)
                    finally:
                        if process is not None and process.poll() is None:
                            process.kill()
                            process.wait(timeout=10)
            audio, receipt = outputs / "speech.wav", outputs / "result.json"
            if (
                not receipt.is_file()
                or receipt.is_symlink()
                or receipt.stat().st_size > 65536
                or not audio.is_file()
                or audio.is_symlink()
                or not 44 < audio.stat().st_size <= 180_000_000
            ):
                raise ValueError("openvoice_cpu_output_invalid")
            result = json.loads(receipt.read_text(encoding="utf-8"))
            expected = {
                "schemaVersion": "clicko.voice-clone-sidecar-result.v1",
                "pipelineContract": PIPELINE,
                "executionDevice": "cpu",
                "watermarkApplied": True,
                "watermarkScheme": "wavmark-0.0.3-local-verified",
                "scriptDigestSha256": request.script_digest_sha256.lower(),
                "voiceVersionId": reference.voice_version_id,
                "consentGrantId": reference.consent_grant_id,
                "voiceReferenceChecksumSha256": reference.normalized_checksum_sha256.lower(),
                "kokoroModelManifestDigestSha256": self.config.kokoro_model_digest_sha256,
                "openvoiceModelManifestDigestSha256": self.config.model_digest_sha256,
                "workerManifestDigestSha256": self.config.worker_manifest_digest_sha256,
                "workerImageDigest": self.config.worker_image_digest,
            }
            if result.get("watermarkApplied") is not True or any(
                result.get(key) != value for key, value in expected.items()
            ):
                raise ValueError("openvoice_cpu_result_binding_mismatch")
            for key in ("wallSeconds", "peakResidentBytes"):
                value = result.get(key)
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value <= 0
                ):
                    raise ValueError("openvoice_cpu_result_metrics_invalid")
            with wave.open(str(audio), "rb") as wav:
                duration = math.ceil(wav.getnframes() * 1000 / wav.getframerate())
                if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000) or duration <= 0:
                    raise ValueError("openvoice_cpu_output_format_invalid")
            if is_cancelled():
                raise InterruptedError("voice_clone_cancelled_after_inference")
            checksum = sha256_file(audio)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as target, audio.open("rb") as source:
                try:
                    shutil.copyfileobj(source, target)
                except Exception:
                    destination.unlink(missing_ok=True)
                    raise
        elapsed = time.perf_counter() - started
        progress(100)
        return SpeechSynthesisResultV1(
            provider=self.name,
            provider_version=self.version,
            audio_format="wav",
            sample_rate=24000,
            duration_ms=duration,
            artifact_checksum_sha256=checksum,
            provenance=SpeechProvenanceV1(
                source_revision=self.config.source_revision,
                model_digest_sha256=self.config.model_digest_sha256,
                worker_manifest_digest_sha256=self.config.worker_manifest_digest_sha256,
                worker_image_digest=self.config.worker_image_digest,
                provenance_mode="clicko-offline-openvoice-cpu-v1",
                voice_version_id=reference.voice_version_id,
                consent_grant_id=reference.consent_grant_id,
                voice_reference_checksum_sha256=reference.normalized_checksum_sha256,
            ),
            metrics={
                "activeComputeSeconds": elapsed,
                "directCostUsd": elapsed * self.config.cpu_hourly_cost_usd / 3600,
                "watermarkVerified": 1.0,
                "sidecarWallSeconds": float(result["wallSeconds"]),
                "peakResidentBytes": float(result["peakResidentBytes"]),
                **isolation_metrics,
            },
        )


def create_openvoice_cpu_provider(
    *,
    manifest_path,
    asset_root,
    kokoro_manifest_path,
    kokoro_repository,
    worker_manifest_digest_sha256,
    worker_image_digest,
    docker_executable,
    cpu_hourly_cost_usd,
    timeout_seconds=1800,
):
    try:
        manifest = OpenVoiceModelAssetManifestV1.model_validate_json(Path(manifest_path).read_text(encoding="utf-8"))
        kokoro = KokoroModelAssetManifestV1.model_validate_json(Path(kokoro_manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("openvoice_cpu_model_manifest_invalid") from error
    return OpenVoiceCPUProvider(
        OpenVoiceCPUConfig(
            source_revision=manifest.openvoice_code_revision,
            model_digest_sha256=openvoice_model_asset_manifest_digest(manifest),
            kokoro_model_digest_sha256=kokoro_model_asset_manifest_digest(kokoro),
            worker_manifest_digest_sha256=worker_manifest_digest_sha256,
            worker_image_digest=worker_image_digest,
            cpu_hourly_cost_usd=cpu_hourly_cost_usd,
            timeout_seconds=timeout_seconds,
        ),
        docker_executable=docker_executable,
        manifest=manifest,
        asset_root=asset_root,
        kokoro_manifest=kokoro,
        kokoro_repository=kokoro_repository,
    )
