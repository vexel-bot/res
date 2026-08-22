from celery import Celery

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
