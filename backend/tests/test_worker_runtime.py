from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.domain.studios.contracts import WorkerExecutionContextV1
from app.services.studios import worker_runtime

MANIFEST = Path(__file__).parents[2] / "workers" / "media-cpu" / "worker.manifest.json"
VISION_MANIFEST = Path(__file__).parents[2] / "workers" / "vision-gpu" / "worker.manifest.json"
SPEECH_CPU_MANIFEST = Path(__file__).parents[2] / "workers" / "speech-cpu" / "worker.manifest.json"
SPEECH_GPU_MANIFEST = Path(__file__).parents[2] / "workers" / "speech-gpu" / "worker.manifest.json"


def test_media_worker_manifest_is_versioned_and_matches_execution_profiles() -> None:
    manifest = worker_runtime.load_worker_manifest(MANIFEST)
    assert manifest.schema_version == "studio.worker-runtime-manifest.v1"
    assert manifest.capability == "media_cpu"
    assert manifest.queues == ["studio.media.cpu"]
    assert set(manifest.job_types) == {
        "media_probe",
        "video_proxy",
        "media_waveform",
        "video_render",
        "editing_gemini",
        "editing_ai",
    }
    assert {"google.gemini-editing", "builtin.ffmpeg-contextual-v1"} <= set(manifest.providers)
    digest = worker_runtime.manifest_digest(manifest)
    assert len(digest) == 64
    assert digest == worker_runtime.manifest_digest(
        type(manifest).model_validate(
            manifest.model_dump(by_alias=True, mode="json")
        )
    )


def test_manifest_validation_proves_tools_and_rejects_version_drift() -> None:
    manifest = worker_runtime.load_worker_manifest(MANIFEST).model_copy(
        update={"required_environment": [], "required_paths": []}
    )
    outputs = {
        "node": "v22.15.0",
        "python": "Python 3.11.2",
        "celery": "5.6.2 (recovery)",
        "ffmpeg": "ffmpeg version 5.1.9-0+deb12u1",
        "ffprobe": "ffprobe version 5.1.9-0+deb12u1",
        "chromium": "Chromium 151.0.7922.173",
    }

    def runner(command: list[str]) -> str:
        if command[:2] == ["node", "-p"]:
            return "0.8.12"
        return outputs[command[0]]

    settings = Settings(
        celery_task_always_eager=False,
        studio_isolated_queues_enabled=True,
        studio_worker_manifest_path=str(MANIFEST),
        studio_worker_capability="media_cpu",
    )
    versions = worker_runtime.validate_worker_manifest(
        manifest, settings, tool_runner=runner
    )
    assert versions["ffmpeg"].startswith("ffmpeg version 5.1.9")
    assert versions["hyperframes"] == "0.8.12"

    outputs["ffmpeg"] = "ffmpeg version 7.0-unapproved"
    with pytest.raises(ValueError, match="worker_tool_version_mismatch:ffmpeg"):
        worker_runtime.validate_worker_manifest(manifest, settings, tool_runner=runner)


def test_manifest_rejects_wrong_capability_and_missing_environment() -> None:
    manifest = worker_runtime.load_worker_manifest(MANIFEST).model_copy(
        update={"required_paths": []}
    )
    wrong = Settings(
        celery_task_always_eager=False,
        studio_isolated_queues_enabled=True,
        studio_worker_manifest_path=str(MANIFEST),
        studio_worker_capability="speech_gpu",
    )
    with pytest.raises(ValueError, match="worker_capability_mismatch"):
        worker_runtime.validate_worker_manifest(manifest, wrong)

    correct = Settings(
        celery_task_always_eager=False,
        studio_isolated_queues_enabled=True,
        studio_worker_manifest_path=str(MANIFEST),
        studio_worker_capability="media_cpu",
    )
    with pytest.raises(ValueError, match="worker_environment_missing"):
        worker_runtime.validate_worker_manifest(manifest, correct)


def test_execution_context_is_honest_for_embedded_and_attested_workers(
    monkeypatch,
) -> None:
    embedded = worker_runtime.worker_execution_context(
        job_type="media_probe",
        capability="media_cpu",
        queue_name="studio.media.cpu",
        settings=Settings(studio_isolated_queues_enabled=False),
    )
    assert embedded.mode == "embedded"
    assert embedded.attested is False
    assert embedded.manifest_digest_sha256 is None

    manifest = worker_runtime.load_worker_manifest(MANIFEST)
    monkeypatch.setattr(
        worker_runtime,
        "isolated_worker_attestation",
        lambda **_: (manifest, "a" * 64, {"ffmpeg": "ffmpeg version 5.1.9"}),
    )
    isolated = worker_runtime.worker_execution_context(
        job_type="media_probe",
        capability="media_cpu",
        queue_name="studio.media.cpu",
        settings=Settings(
            celery_task_always_eager=False,
            studio_isolated_queues_enabled=True,
            studio_worker_manifest_path=str(MANIFEST),
            studio_worker_capability="media_cpu",
            studio_worker_instance_id="worker-test-1",
        ),
    )
    assert isolated.mode == "isolated"
    assert isolated.attested is True
    assert isolated.worker_instance_id == "worker-test-1"
    assert isolated.manifest_digest_sha256 == "a" * 64


def test_isolated_context_cannot_claim_partial_attestation() -> None:
    with pytest.raises(ValueError, match="fully attested"):
        WorkerExecutionContextV1(
            mode="isolated",
            attested=True,
            job_type="media_probe",
            capability="media_cpu",
            queue_name="studio.media.cpu",
            runtime_name="clicko-media-cpu",
            runtime_version="0.1.0",
            manifest_digest_sha256="a" * 64,
            verified_at=datetime.now(UTC),
        )


def test_vision_worker_manifest_requires_and_attests_gpu_inventory() -> None:
    source_manifest = worker_runtime.load_worker_manifest(VISION_MANIFEST)
    assert (
        worker_runtime.manifest_digest(source_manifest)
        == "fbe3c7a55ba2d98a7a12a4ae37e8b97b46d2282bcb89cfe5a657d6b60ac0efb1"
    )
    assert source_manifest.providers == []
    manifest = source_manifest.model_copy(
        update={"required_environment": [], "required_paths": []}
    )
    settings = Settings(
        celery_task_always_eager=False,
        studio_isolated_queues_enabled=True,
        studio_worker_manifest_path=str(VISION_MANIFEST),
        studio_worker_capability="vision_gpu",
    )

    def runner(command: list[str]) -> str:
        if "name,driver_version" in " ".join(command):
            return "NVIDIA A10, 535.129.03, 23028, 8.6"
        if command[0] == "nvidia-smi":
            return "535.129.03"
        if command[0] == "celery":
            return "5.6.2 (recovery)"
        return "Python 3.11.2"

    versions = worker_runtime.validate_worker_manifest(manifest, settings, tool_runner=runner)
    assert versions["accelerator"].startswith("nvidia:1x:NVIDIA A10")
    assert set(manifest.job_types) == {"reality_analysis", "video_physical_qc"}

    def insufficient_gpu(command: list[str]) -> str:
        if "name,driver_version" in " ".join(command):
            return "NVIDIA T4, 535.129.03, 15360, 7.5"
        return runner(command)

    with pytest.raises(ValueError, match="worker_accelerator_requirements_unmet"):
        worker_runtime.validate_worker_manifest(
            manifest, settings, tool_runner=insufficient_gpu
        )


def test_speech_preflight_manifests_reserve_separate_queues_without_providers() -> None:
    cpu = worker_runtime.load_worker_manifest(SPEECH_CPU_MANIFEST)
    assert cpu.capability == "speech_cpu"
    assert cpu.queues == ["studio.speech.cpu"]
    assert cpu.resource_classes == ["cpu.speech"]
    assert cpu.job_types == ["stock_voice"]
    assert cpu.providers == []
    assert cpu.accelerator is None

    gpu = worker_runtime.load_worker_manifest(SPEECH_GPU_MANIFEST)
    assert gpu.capability == "speech_gpu"
    assert gpu.queues == ["studio.gpu.speech"]
    assert gpu.resource_classes == ["gpu.speech"]
    assert set(gpu.job_types) == {"transcription", "voice_clone"}
    assert gpu.providers == []
    assert gpu.accelerator is not None
    assert gpu.accelerator.minimum_memory_mib == 16_384

    assert len(worker_runtime.manifest_digest(cpu)) == 64
    assert len(worker_runtime.manifest_digest(gpu)) == 64


def test_speech_gpu_preflight_validates_attested_hardware_floor() -> None:
    source_manifest = worker_runtime.load_worker_manifest(SPEECH_GPU_MANIFEST)
    manifest = source_manifest.model_copy(
        update={"required_environment": [], "required_paths": []}
    )
    settings = Settings(
        celery_task_always_eager=False,
        studio_isolated_queues_enabled=True,
        studio_worker_manifest_path=str(SPEECH_GPU_MANIFEST),
        studio_worker_capability="speech_gpu",
    )

    def runner(command: list[str]) -> str:
        if "name,driver_version" in " ".join(command):
            return "NVIDIA L4, 535.129.03, 23034, 8.9"
        if command[0] == "nvidia-smi":
            return "535.129.03"
        if command[0] == "celery":
            return "5.6.2 (recovery)"
        if command[0] == "ffmpeg":
            return "ffmpeg version 5.1.9-0+deb12u1"
        return "Python 3.11.9"

    versions = worker_runtime.validate_worker_manifest(manifest, settings, tool_runner=runner)
    assert versions["accelerator"].startswith("nvidia:1x:NVIDIA L4")
    assert versions["ffmpeg"].startswith("ffmpeg version 5.1.9")

    def insufficient_gpu(command: list[str]) -> str:
        if "name,driver_version" in " ".join(command):
            return "NVIDIA T4, 535.129.03, 15360, 7.5"
        return runner(command)

    with pytest.raises(ValueError, match="worker_accelerator_requirements_unmet"):
        worker_runtime.validate_worker_manifest(
            manifest, settings, tool_runner=insufficient_gpu
        )
