from __future__ import annotations

from celery import Celery, bootsteps

from .config import get_settings

settings = get_settings()
vision_celery_app = Celery(
    "clicko-vision",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.vision_tasks"],
)
vision_celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=30,
    task_time_limit=7_200,
    task_always_eager=False,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
)


class ValidateVisionWorkerRuntime(bootsteps.StartStopStep):
    """Refuse queue consumption until the GPU runtime attestation passes."""

    label = "Validate Clicko vision worker runtime"

    def start(self, worker) -> None:  # noqa: ARG002
        runtime_settings = get_settings()
        runtime_settings.validate_for_startup()
        if not runtime_settings.studio_worker_manifest_path:
            raise ValueError("vision_worker_manifest_required")

        from .services.studios.worker_runtime import isolated_worker_attestation

        isolated_worker_attestation(settings=runtime_settings, force=True)


vision_celery_app.steps["worker"].add(ValidateVisionWorkerRuntime)
