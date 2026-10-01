from __future__ import annotations

from .llm_celery_app import llm_celery_app


@llm_celery_app.task(bind=True, name="app.tasks.probe_studio_worker", max_retries=3)
def probe_studio_worker(
    self,
    expected_capability: str,
    expected_queue: str,
    expected_manifest_digest: str,
) -> dict:
    """Expose only attestation; no Qwen/Kimi inference task is registered yet."""
    from .services.studios.worker_runtime import probe_current_worker

    delivery = self.request.delivery_info or {}
    routing_key = delivery.get("routing_key")
    if routing_key and routing_key != expected_queue:
        raise ValueError("worker_probe_delivery_queue_mismatch")
    return probe_current_worker(
        expected_capability=expected_capability,
        expected_queue=expected_queue,
        expected_manifest_digest=expected_manifest_digest,
    )
