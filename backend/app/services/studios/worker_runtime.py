from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ...config import Settings, get_settings
from ...domain.studios.contracts import (
    StudioWorkerRuntimeManifestV1,
    WorkerExecutionContextV1,
)
from ...domain.studios.execution import execution_profile

ToolRunner = Callable[[list[str]], str]

_cached_pid: int | None = None
_cached_manifest: StudioWorkerRuntimeManifestV1 | None = None
_cached_manifest_digest: str | None = None
_cached_tool_versions: dict[str, str] | None = None


def canonical_manifest_bytes(manifest: StudioWorkerRuntimeManifestV1) -> bytes:
    return json.dumps(
        manifest.model_dump(by_alias=True, mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def manifest_digest(manifest: StudioWorkerRuntimeManifestV1) -> str:
    return hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()


def load_worker_manifest(path: str | Path) -> StudioWorkerRuntimeManifestV1:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"worker_manifest_unreadable:{source}") from error
    return StudioWorkerRuntimeManifestV1.model_validate(payload)


def _default_tool_runner(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"worker_tool_unavailable:{command[0]}") from error
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode != 0 or not output:
        raise ValueError(f"worker_tool_unavailable:{command[0]}")
    return output[:4000]


def validate_worker_manifest(
    manifest: StudioWorkerRuntimeManifestV1,
    settings: Settings,
    *,
    tool_runner: ToolRunner = _default_tool_runner,
) -> dict[str, str]:
    if not settings.studio_isolated_queues_enabled:
        raise ValueError("worker_requires_isolated_queues")
    if settings.celery_task_always_eager:
        raise ValueError("isolated_worker_cannot_run_eager")
    if settings.studio_worker_capability != manifest.capability:
        raise ValueError("worker_capability_mismatch")
    if settings.environment == "production" and settings.object_storage_backend != "s3":
        raise ValueError("production_worker_requires_object_storage")
    if settings.environment == "production" and not settings.studio_worker_image_digest:
        raise ValueError("production_worker_image_digest_required")

    for job_type in manifest.job_types:
        profile = execution_profile(job_type)
        if profile.capability != manifest.capability:
            raise ValueError(f"worker_job_capability_mismatch:{job_type}")
        if profile.queue not in manifest.queues:
            raise ValueError(f"worker_job_queue_mismatch:{job_type}")
        if profile.resource_class not in manifest.resource_classes:
            raise ValueError(f"worker_job_resource_mismatch:{job_type}")

    missing_environment = [name for name in manifest.required_environment if not os.getenv(name)]
    if missing_environment:
        raise ValueError(f"worker_environment_missing:{','.join(missing_environment)}")
    missing_paths = [path for path in manifest.required_paths if not Path(path).is_file()]
    if missing_paths:
        raise ValueError(f"worker_path_missing:{','.join(missing_paths)}")

    versions: dict[str, str] = {}
    for tool in manifest.tools:
        try:
            pattern = re.compile(tool.version_pattern)
        except re.error as error:
            raise ValueError(f"worker_tool_pattern_invalid:{tool.id}") from error
        output = tool_runner(tool.command)
        match = pattern.search(output)
        if not match:
            raise ValueError(f"worker_tool_version_mismatch:{tool.id}")
        versions[tool.id] = match.group(0)[:240]
    if manifest.accelerator:
        accelerator = manifest.accelerator
        try:
            driver_pattern = re.compile(accelerator.driver_version_pattern)
        except re.error as error:
            raise ValueError("worker_accelerator_driver_pattern_invalid") from error
        inventory = tool_runner(accelerator.inventory_command)
        eligible: list[tuple[str, str, int, float]] = []
        for line in inventory.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 4:
                continue
            name, driver, memory, compute = parts
            try:
                memory_mib = int(memory)
                compute_capability = float(compute)
            except ValueError:
                continue
            if (
                driver_pattern.search(driver)
                and memory_mib >= accelerator.minimum_memory_mib
                and compute_capability >= accelerator.minimum_compute_capability
            ):
                eligible.append((name, driver, memory_mib, compute_capability))
        if len(eligible) < accelerator.minimum_devices:
            raise ValueError("worker_accelerator_requirements_unmet")
        name, driver, memory_mib, compute_capability = eligible[0]
        versions["accelerator"] = (
            f"{accelerator.vendor}:{len(eligible)}x:{name}:driver-{driver}:"
            f"{memory_mib}MiB:cc-{compute_capability:g}"
        )[:240]
    return versions


def isolated_worker_attestation(
    *,
    settings: Settings | None = None,
    force: bool = False,
    tool_runner: ToolRunner = _default_tool_runner,
) -> tuple[StudioWorkerRuntimeManifestV1, str, dict[str, str]]:
    global _cached_manifest, _cached_manifest_digest, _cached_pid, _cached_tool_versions

    runtime_settings = settings or get_settings()
    if not runtime_settings.studio_worker_manifest_path:
        raise ValueError("worker_manifest_required")
    current_pid = os.getpid()
    if (
        not force
        and _cached_pid == current_pid
        and _cached_manifest is not None
        and _cached_manifest_digest is not None
        and _cached_tool_versions is not None
    ):
        return _cached_manifest, _cached_manifest_digest, dict(_cached_tool_versions)

    manifest = load_worker_manifest(runtime_settings.studio_worker_manifest_path)
    versions = validate_worker_manifest(manifest, runtime_settings, tool_runner=tool_runner)
    digest = manifest_digest(manifest)
    _cached_pid = current_pid
    _cached_manifest = manifest
    _cached_manifest_digest = digest
    _cached_tool_versions = versions
    return manifest, digest, dict(versions)


def worker_execution_context(
    *,
    job_type: str,
    capability: str,
    queue_name: str,
    settings: Settings | None = None,
) -> WorkerExecutionContextV1:
    runtime_settings = settings or get_settings()
    now = datetime.now(UTC)
    if not runtime_settings.studio_isolated_queues_enabled or capability == "control":
        return WorkerExecutionContextV1(
            mode="embedded",
            attested=False,
            job_type=job_type,
            capability=capability,
            queue_name=queue_name,
            verified_at=now,
        )

    manifest, digest, versions = isolated_worker_attestation(settings=runtime_settings)
    if manifest.capability != capability:
        raise ValueError("job_worker_capability_mismatch")
    if queue_name not in manifest.queues:
        raise ValueError("job_worker_queue_mismatch")
    if job_type not in manifest.job_types:
        raise ValueError("job_worker_type_unsupported")
    instance_id = runtime_settings.studio_worker_instance_id or f"{socket.gethostname()}:{os.getpid()}"
    return WorkerExecutionContextV1(
        mode="isolated",
        attested=True,
        job_type=job_type,
        capability=capability,
        queue_name=queue_name,
        runtime_name=manifest.runtime_name,
        runtime_version=manifest.runtime_version,
        manifest_digest_sha256=digest,
        image_digest=runtime_settings.studio_worker_image_digest,
        worker_instance_id=instance_id,
        hostname=socket.gethostname(),
        process_id=os.getpid(),
        tool_versions=versions,
        verified_at=now,
    )


def probe_current_worker(
    *,
    expected_capability: str,
    expected_queue: str,
    expected_manifest_digest: str,
) -> dict:
    manifest, digest, _ = isolated_worker_attestation()
    if manifest.capability != expected_capability:
        raise ValueError("worker_probe_capability_mismatch")
    if expected_queue not in manifest.queues:
        raise ValueError("worker_probe_queue_mismatch")
    if digest != expected_manifest_digest:
        raise ValueError("worker_probe_manifest_mismatch")
    context = worker_execution_context(
        job_type=manifest.job_types[0],
        capability=manifest.capability,
        queue_name=expected_queue,
    )
    return {
        "schemaVersion": "studio.worker-runtime-probe.v1",
        "status": "ready",
        "runtime": context.model_dump(by_alias=True, mode="json"),
        "supportedJobTypes": manifest.job_types,
        "providers": manifest.providers,
        "isolationPolicy": manifest.isolation.model_dump(by_alias=True, mode="json"),
    }
