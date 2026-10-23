"""Move new semantic production continuation off HTTP requests."""

from uuid import uuid4

from .contextual_editing import lock_editing_budget
from .editorial_production import get_run, save


def enqueue_continuation(db, record, run_id, user):
    from ...tasks import advance_editorial_production

    lock_editing_budget(db, record.workspace_id)
    state = get_run(db, record, run_id)
    if state["status"] in {"awaiting_review", "cancelled"} or state.get("continuationTaskId"):
        return state
    task_id = str(uuid4())
    state.update(continuationTaskId=task_id, status="running")
    state = save(db, record, user, state)
    try:
        from ...config import get_settings

        def dispatch():
            advance_editorial_production.apply_async(args=[record.id, run_id, user.id, task_id], task_id=task_id)

        if get_settings().environment == "development" and get_settings().celery_task_always_eager:
            from .local_queue import submit

            submit(dispatch)
        else:
            dispatch()
    except Exception:
        state.pop("continuationTaskId", None)
        state.update(status="blocked", blockers=["production_queue_unavailable"])
        state = save(db, record, user, state)
    return state


def continue_from_api(db, record, run_id, user):
    from .editorial_production import advance_run

    state = get_run(db, record, run_id)
    from ...config import get_settings

    if state["request"].get("useSemanticCompositions") or get_settings().environment != "test":
        return enqueue_continuation(db, record, run_id, user)
    return advance_run(db, record, run_id, user)
