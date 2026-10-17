from dataclasses import dataclass

import pytest

from app.config import Settings
from app.domain.studios.execution import execution_profile
from app.services.studios.jobs import enqueue_job_task


@dataclass
class FakeJob:
    id: str = "job-123"
    workspace_id: str = "workspace-123"
    correlation_id: str = "correlation-123"
    execution_capability: str = "speech_gpu"
    queue_name: str = "studio.gpu.speech"
    hard_time_limit_seconds: int = 3_600


class FakeTask:
    def __init__(self) -> None:
        self.delayed: list[str] = []
        self.applied: list[dict] = []

    def delay(self, job_id: str) -> None:
        self.delayed.append(job_id)

    def apply_async(self, **kwargs) -> None:
        self.applied.append(kwargs)


def test_execution_profiles_separate_cpu_speech_and_vision() -> None:
    assert execution_profile("video_ingest").queue == "studio.media.cpu"
    assert execution_profile("stock_voice").queue == "studio.speech.cpu"
    assert execution_profile("stock_voice").resource_class == "cpu.speech"
    assert execution_profile("voice_clone").queue == "studio.gpu.speech"
    assert execution_profile("avatar_video").queue == "studio.gpu.vision"


def test_queue_rollout_gate_preserves_default_worker_then_routes_explicitly() -> None:
    task = FakeTask()
    job = FakeJob()

    enqueue_job_task(task, job, isolated_queues_enabled=False)
    assert task.delayed == [job.id]
    assert task.applied == []

    enqueue_job_task(task, job, isolated_queues_enabled=True)
    assert task.applied == [
        {
            "args": [job.id],
            "task_id": job.id,
            "queue": "studio.gpu.speech",
            "soft_time_limit": 3_540,
            "time_limit": 3_600,
            "headers": {
                "workspace_id": job.workspace_id,
                "correlation_id": job.correlation_id,
                "execution_capability": job.execution_capability,
                "queue_name": job.queue_name,
            },
        }
    ]


def test_eager_task_execution_is_rejected_in_production() -> None:
    with pytest.raises(RuntimeError, match="CELERY_TASK_ALWAYS_EAGER"):
        Settings(
            environment="production",
            database_url="postgresql://clicko@example.invalid/clicko",
            secret_key="a-production-secret-key-with-at-least-32-characters",
            celery_task_always_eager=True,
        ).validate_for_startup()


def test_worker_manifest_and_capability_must_be_configured_together() -> None:
    with pytest.raises(RuntimeError, match="configured together"):
        Settings(studio_worker_manifest_path="/runtime/manifest.json").validate_for_startup()


def test_empty_worker_environment_values_preserve_control_plane_defaults() -> None:
    settings = Settings(
        studio_worker_manifest_path="",
        studio_worker_capability="",
        studio_worker_instance_id="",
        studio_worker_image_digest="",
    )
    settings.validate_for_startup()
    assert settings.studio_worker_manifest_path is None
    assert settings.studio_worker_capability is None
    assert settings.studio_worker_instance_id is None
    assert settings.studio_worker_image_digest is None


def test_worker_requires_isolated_non_eager_runtime() -> None:
    with pytest.raises(RuntimeError, match="STUDIO_ISOLATED_QUEUES_ENABLED"):
        Settings(
            studio_worker_manifest_path="/runtime/manifest.json",
            studio_worker_capability="media_cpu",
        ).validate_for_startup()
    with pytest.raises(RuntimeError, match="cannot use CELERY_TASK_ALWAYS_EAGER"):
        Settings(
            studio_isolated_queues_enabled=True,
            studio_worker_manifest_path="/runtime/manifest.json",
            studio_worker_capability="media_cpu",
            celery_task_always_eager=True,
        ).validate_for_startup()
