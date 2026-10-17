from celery import Celery, bootsteps

from .config import get_settings

settings = get_settings()
celery_app = Celery("nexus", broker=settings.redis_url, backend=settings.redis_url, include=["app.tasks"])
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=30,
    task_time_limit=300,
    task_always_eager=settings.celery_task_always_eager,
    # Eager execution must still return a failed EagerResult so callers can
    # verify the persisted JobAudit. Production workers are unaffected because
    # task_always_eager is disabled outside local/test environments.
    task_eager_propagates=False,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
    beat_schedule={
        "radar-source-sync-every-15-minutes": {
            "task": "app.tasks.enqueue_scheduled_radar_syncs",
            "schedule": 900.0,
        },
        "expired-signal-cleanup-hourly": {
            "task": "app.tasks.enqueue_scheduled_signal_cleanup",
            "schedule": 3600.0,
        },
    },
)


class ValidateStudioWorkerRuntime(bootsteps.StartStopStep):
    """Mandatory boot gate: an incompatible worker never starts consuming."""

    label = "Validate Studio worker runtime"

    def start(self, worker) -> None:  # noqa: ARG002
        runtime_settings = get_settings()
        runtime_settings.validate_for_startup()
        if runtime_settings.studio_worker_manifest_path:
            from .services.studios.worker_runtime import isolated_worker_attestation

            isolated_worker_attestation(settings=runtime_settings, force=True)


celery_app.steps["worker"].add(ValidateStudioWorkerRuntime)
