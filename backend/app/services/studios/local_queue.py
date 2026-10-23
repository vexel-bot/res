"""Bounded, non-durable local execution; the database owns job state and retries.

Production always uses Celery/Redis. No provider resubmission on process restart.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="clicko-studios-local")
_slots = BoundedSemaphore(8)


def submit(callback):
    if not _slots.acquire(blocking=False):
        raise ValueError("studio_local_queue_unavailable")

    def run():
        try:
            callback()
        finally:
            _slots.release()

    try:
        _executor.submit(run)
    except Exception:
        _slots.release()
        raise


def dispatch(task, job_id):
    submit(lambda: task.delay(job_id))
