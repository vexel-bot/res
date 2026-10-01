from __future__ import annotations

from celery import Celery, bootsteps

from .config import get_settings

settings = get_settings()
llm_celery_app = Celery(
    "clicko-llm",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.llm_tasks"],
)
llm_celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=30,
    task_time_limit=3_600,
    task_always_eager=False,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
)


class ValidateLlmWorkerRuntime(bootsteps.StartStopStep):
    """Refuse queue consumption until the dedicated LLM runtime is attested."""

    label = "Validate Clicko LLM worker runtime"

    def start(self, worker) -> None:  # noqa: ARG002
        runtime_settings = get_settings()
        runtime_settings.validate_for_startup()
        if not runtime_settings.studio_worker_manifest_path:
            raise ValueError("llm_worker_manifest_required")

        from .services.studios.worker_runtime import isolated_worker_attestation

        isolated_worker_attestation(settings=runtime_settings, force=True)


llm_celery_app.steps["worker"].add(ValidateLlmWorkerRuntime)
