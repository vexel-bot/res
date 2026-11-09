"""Candidate appearance port; configured commands belong to the local operator."""

from __future__ import annotations

import math
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from ...domain.studios.appearance_image import (
    PROVIDER,
    PROVIDER_VERSION,
    AppearanceImageRequestV1,
    AppearanceImageResultV1,
    AppearanceModelManifestV1,
    canonical_digest,
    file_digest,
)


def _stop(process):
    """Terminate this owned process tree, rather than only its waiting caller."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/taskkill.exe"
        subprocess.run(
            [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=15,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.wait(timeout=5)


class QwenAppearanceProvider:
    name = PROVIDER
    version = PROVIDER_VERSION
    execution_environment = "local"

    def __init__(
        self, *, python_executable, runner_path, runner_digest_sha256, manifest_path, model_root, timeout_seconds=3600
    ):
        self.python_executable, self.runner_path = Path(python_executable), Path(runner_path)
        self.manifest_path, self.model_root = Path(manifest_path), Path(model_root)
        if any(
            not p.is_absolute() for p in (self.python_executable, self.runner_path, self.manifest_path, self.model_root)
        ):
            raise ValueError("appearance_absolute_runtime_paths_required")
        if not self.python_executable.is_file() or self.runner_path.is_symlink():
            raise ValueError("appearance_runtime_unavailable")
        if file_digest(self.runner_path) != runner_digest_sha256:
            raise ValueError("appearance_runner_binding_mismatch")
        if not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 7200:
            raise ValueError("appearance_timeout_invalid")
        self.runner_digest = runner_digest_sha256
        self.timeout_seconds = timeout_seconds
        self.manifest = AppearanceModelManifestV1.model_validate_json(self.manifest_path.read_text(encoding="utf-8"))

    def _command(self):
        if file_digest(self.runner_path) != self.runner_digest:
            raise ValueError("appearance_runner_binding_mismatch")
        current = AppearanceModelManifestV1.model_validate_json(self.manifest_path.read_text(encoding="utf-8"))
        if current != self.manifest:
            raise ValueError("appearance_model_manifest_changed")
        return [
            str(self.python_executable),
            str(self.runner_path),
            "--model-root",
            str(self.model_root),
            "--model-manifest",
            str(self.manifest_path),
        ]

    def generate(
        self, request: AppearanceImageRequestV1, reference_path, source_path, destination, progress, is_cancelled
    ):
        from PIL import Image

        if bool(source_path) != bool(request.source_asset_id):
            raise ValueError("appearance_source_binding_incomplete")
        if is_cancelled():
            raise InterruptedError("appearance_cancelled_before_inference")
        destination = Path(destination)
        if destination.exists():
            raise ValueError("appearance_destination_must_be_new")
        command = self._command()
        with tempfile.TemporaryDirectory(prefix="clicko-appearance-") as temporary:
            root = Path(temporary)
            for path, checksum, name in (
                (Path(reference_path), request.reference_checksum_sha256, "reference-image"),
                (Path(source_path) if source_path else None, request.source_checksum_sha256, "source-image"),
            ):
                if path is None:
                    continue
                if path.is_symlink() or not path.is_file() or path.stat().st_size > 50 * 1024**2:
                    raise ValueError("appearance_input_unavailable")
                if file_digest(path) != checksum:
                    raise ValueError("appearance_input_checksum_mismatch")
                shutil.copyfile(path, root / name)
            (root / "request.json").write_text(request.model_dump_json(by_alias=True), encoding="utf-8")
            command += [
                "--request",
                str(root / "request.json"),
                "--reference",
                str(root / "reference-image"),
                "--output",
                str(root / "output.png"),
                "--result",
                str(root / "result.json"),
                "--progress",
                str(root / "progress"),
                "--cancel-file",
                str(root / "cancel"),
            ]
            if source_path:
                command += ["--source", str(root / "source-image")]
            started, process = time.perf_counter(), None
            with (root / "private-runtime.log").open("wb") as log:
                try:
                    environment = {
                        key: value
                        for key, value in os.environ.items()
                        if key.upper()
                        in {
                            "PATH",
                            "SYSTEMROOT",
                            "WINDIR",
                            "TEMP",
                            "TMP",
                            "HOME",
                            "USERPROFILE",
                            "CUDA_VISIBLE_DEVICES",
                            "LD_LIBRARY_PATH",
                        }
                    }
                    environment.update(
                        PYTHONPATH=str(Path(__file__).resolve().parents[3]),
                        HF_HUB_OFFLINE="1",
                        TRANSFORMERS_OFFLINE="1",
                        HF_DATASETS_OFFLINE="1",
                    )
                    process = subprocess.Popen(
                        command,
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=log,
                        start_new_session=os.name != "nt",
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        env=environment,
                    )
                    while process.poll() is None:
                        if is_cancelled():
                            (root / "cancel").touch()
                            raise InterruptedError("appearance_cancelled_during_inference")
                        if time.perf_counter() - started > self.timeout_seconds:
                            (root / "cancel").touch()
                            raise TimeoutError("appearance_execution_timeout")
                        try:
                            value = int((root / "progress").read_text())
                            if 0 <= value < 100:
                                progress(value)
                        except (OSError, ValueError):
                            pass
                        time.sleep(0.1)
                    if process.returncode != 0:
                        raise RuntimeError("appearance_sidecar_execution_failed")
                finally:
                    if process is not None:
                        _stop(process)
            receipt, output = root / "result.json", root / "output.png"
            if (
                not receipt.is_file()
                or receipt.is_symlink()
                or receipt.stat().st_size > 65536
                or not output.is_file()
                or output.is_symlink()
                or output.stat().st_size > 50 * 1024**2
            ):
                raise ValueError("appearance_result_missing_or_invalid")
            result = AppearanceImageResultV1.model_validate_json(receipt.read_text(encoding="utf-8"))
            if (
                result.provider_version != self.version
                or result.request_digest_sha256 != canonical_digest(request)
                or result.model_manifest_digest_sha256 != canonical_digest(self.manifest)
                or result.identity_ref != request.identity_ref
                or result.reference_checksum_sha256 != request.reference_checksum_sha256
                or result.source_checksum_sha256 != request.source_checksum_sha256
                or (result.width, result.height) != (request.width, request.height)
                or result.artifact_checksum_sha256 != file_digest(output)
            ):
                raise ValueError("appearance_result_binding_mismatch")
            with Image.open(output) as image:
                if image.format != "PNG" or image.size != (request.width, request.height):
                    raise ValueError("appearance_result_image_invalid")
                image.verify()
            if is_cancelled():
                raise InterruptedError("appearance_cancelled_before_persistence")
            destination.parent.mkdir(parents=True, exist_ok=True)
            created = False
            try:
                with destination.open("xb") as target:
                    created = True
                    with output.open("rb") as source:
                        shutil.copyfileobj(source, target)
            except Exception:
                # Do not remove a file owned by a concurrent caller that won xb.
                if created:
                    destination.unlink(missing_ok=True)
                raise
        progress(100)
        return result
