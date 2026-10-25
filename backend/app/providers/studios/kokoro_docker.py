"""Lightweight API adapter; Torch and the model stay in an offline container."""

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
from dataclasses import asdict
from pathlib import Path

from ...domain.studios.contracts import SpeechSynthesisResultV1
from ...services.object_storage import sha256_file
from .kokoro_stock import KOKORO_SAMPLE_RATE, KokoroStockConfig, KokoroStockVoiceProvider

CONTRACT = "clicko.kokoro-stock-sidecar.v1"


class SpeechDockerExecutionError(RuntimeError):
    """Public error code plus private diagnostics for the operator's smoke CLI."""

    def __init__(self, diagnostics):
        super().__init__("speech_docker_synthesis_failed")
        self.diagnostics = diagnostics


class KokoroDockerSpeechProvider:
    name = KokoroStockVoiceProvider.name
    execution_environment = "local"

    def __init__(self, config: KokoroStockConfig, *, docker_executable: Path, timeout_seconds: float = 1800):
        if not docker_executable.is_absolute() or not docker_executable.is_file():
            raise ValueError("speech_docker_absolute_executable_required")
        if not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 7200:
            raise ValueError("speech_docker_timeout_invalid")
        self.config = config
        self.version = KokoroStockVoiceProvider(config).version
        self.docker_executable = str(docker_executable)
        self.timeout_seconds = timeout_seconds

    def _docker(self, arguments, timeout=20):
        try:
            return subprocess.run(
                [self.docker_executable, *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("speech_docker_control_unavailable") from exc

    def _require_image(self):
        inspected = self._docker(["image", "inspect", self.config.worker_image_digest])
        try:
            image = json.loads(inspected.stdout)[0]
            labels = image["Config"].get("Labels") or {}
            valid = (
                inspected.returncode == 0
                and image["Id"] == self.config.worker_image_digest
                and labels.get("io.clicko.sidecar.contract") == CONTRACT
                and labels.get("io.clicko.model-manifest.digest") == self.config.model_digest_sha256
            )
        except (ValueError, IndexError, KeyError, TypeError):
            valid = False
        if not valid:
            raise ValueError("speech_docker_image_binding_mismatch")

    def _remove(self, name):
        # Killing the Docker client alone does not stop inference in the daemon.
        self._docker(["container", "rm", "--force", name])
        inventory = self._docker(["container", "ls", "--all", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"])
        if inventory.returncode != 0 or inventory.stdout.strip():
            raise RuntimeError("speech_docker_cleanup_unverified")

    def synthesize(self, request, destination, progress, is_cancelled):
        if request.locale != "pt-BR" or request.voice_key not in self.config.allowed_voices:
            raise ValueError("kokoro_stock_voice_not_allowlisted")
        if request.audio_format != "wav" or request.sample_rate != KOKORO_SAMPLE_RATE:
            raise ValueError("kokoro_stock_requires_wav_24khz")
        if is_cancelled():
            raise InterruptedError("kokoro_synthesis_cancelled")
        destination = Path(destination)
        if destination.exists():
            raise ValueError("speech_docker_destination_must_be_new")
        self._require_image()
        name = "clicko-speech-" + uuid.uuid4().hex
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="clicko-speech-sidecar-") as temporary:
            root = Path(temporary).resolve()
            if any(char in str(root) for char in (",", "\n", "\r")):
                raise ValueError("speech_docker_bind_path_invalid")
            inputs, outputs = root / "input", root / "output"
            inputs.mkdir()
            outputs.mkdir()
            # Linux runs as the host's non-root uid so a 0700 job directory is writable.
            uid = os.getuid() if hasattr(os, "getuid") else 10001
            gid = os.getgid() if hasattr(os, "getgid") else 10001
            if uid == 0:
                uid = gid = 10001
                os.chown(outputs, uid, gid)
            config = asdict(self.config)
            config["allowed_voices"] = sorted(self.config.allowed_voices)
            (inputs / "config.json").write_text(json.dumps(config), encoding="utf-8")
            (inputs / "request.json").write_text(request.model_dump_json(by_alias=True), encoding="utf-8")
            arguments = [
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
                "/tmp:rw,noexec,nosuid,size=256m,mode=1777",
                "--tmpfs",
                "/run/clicko-phonemizer:rw,exec,nosuid,nodev,size=64m,mode=1777",
                "--env",
                "TMPDIR=/run/clicko-phonemizer",
                "--mount",
                f"type=bind,source={inputs},target=/job/input,readonly",
                "--mount",
                f"type=bind,source={outputs},target=/job/output",
                self.config.worker_image_digest,
                "python",
                "scripts/run_kokoro_stock_sidecar.py",
                "--request",
                "/job/input/request.json",
                "--config",
                "/job/input/config.json",
                "--output",
                "/job/output/speech.wav",
                "--result",
                "/job/output/result.json",
            ]
            progress(5)
            process = None
            diagnostics_path = root / "runtime.log"
            diagnostics = diagnostics_path.open("wb")
            try:
                # Establish a daemon-owned handle before cancellation can race startup.
                created = self._docker(arguments)
                container_id = created.stdout.strip()
                if created.returncode != 0 or not re.fullmatch(r"[a-f0-9]{64}", container_id):
                    raise RuntimeError("speech_docker_container_creation_failed")
                if is_cancelled():
                    raise InterruptedError("kokoro_synthesis_cancelled")
                process = subprocess.Popen(
                    [self.docker_executable, "start", "--attach", container_id],
                    stdin=subprocess.DEVNULL,
                    stdout=diagnostics,
                    stderr=diagnostics,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    start_new_session=os.name != "nt",
                )
                while process.poll() is None:
                    if is_cancelled():
                        raise InterruptedError("kokoro_synthesis_cancelled")
                    if time.perf_counter() - started > self.timeout_seconds:
                        raise TimeoutError("speech_docker_synthesis_timeout")
                    time.sleep(0.1)
                if process.returncode != 0:
                    diagnostics.flush()
                    raise SpeechDockerExecutionError(diagnostics_path.read_bytes()[:131072].decode("utf-8", "replace"))
            finally:
                try:
                    self._remove(name)
                finally:
                    try:
                        if process is not None and process.poll() is None:
                            process.kill()
                            process.wait(timeout=10)
                    finally:
                        diagnostics.close()
            result_path, audio = outputs / "result.json", outputs / "speech.wav"
            if (
                not result_path.is_file()
                or result_path.is_symlink()
                or result_path.stat().st_size > 65536
                or not audio.is_file()
                or audio.is_symlink()
                or not 44 < audio.stat().st_size <= 180_000_000
            ):
                raise ValueError("speech_docker_output_invalid")
            result = SpeechSynthesisResultV1.model_validate_json(result_path.read_text(encoding="utf-8"))
            provenance = result.provenance
            with wave.open(str(audio), "rb") as wav:
                duration = math.ceil(wav.getnframes() * 1000 / wav.getframerate())
                audio_valid = wav.getnchannels() == 1 and wav.getsampwidth() == 2 and wav.getframerate() == 24000
            if (
                not audio_valid
                or result.duration_ms != duration
                or result.provider != self.name
                or result.provider_version != self.version
                or result.audio_format != request.audio_format
                or result.sample_rate != request.sample_rate
                or result.artifact_checksum_sha256 != sha256_file(audio)
                or provenance.source_revision != self.config.source_revision
                or provenance.model_digest_sha256 != self.config.model_digest_sha256
                or provenance.worker_manifest_digest_sha256 != self.config.worker_manifest_digest_sha256
                or provenance.worker_image_digest != self.config.worker_image_digest
            ):
                raise ValueError("speech_docker_result_binding_mismatch")
            if is_cancelled():
                raise InterruptedError("kokoro_synthesis_cancelled")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as target, audio.open("rb") as source:
                try:
                    shutil.copyfileobj(source, target)
                except Exception:
                    destination.unlink(missing_ok=True)
                    raise
            result.metrics["sidecarWallSeconds"] = time.perf_counter() - started
            progress(100)
            return result
