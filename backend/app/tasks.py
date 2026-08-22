from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError

from .celery_app import celery_app
from .connectors.rss import RSSConnector
from .database import SessionLocal
from .models import ExternalSignal, JobAudit, RadarSource
from .schemas import SignalIn
from .services.radar import upsert_workspace_opportunities
from .services.signals import normalize_and_store


def start_audit(db, *, job_type: str, idempotency_key: str, workspace_id: str | None = None) -> tuple[JobAudit, bool]:
    audit = db.scalar(select(JobAudit).where(JobAudit.idempotency_key == idempotency_key))
    if audit and audit.status == "completed":
        return audit, True
    if not audit:
        audit = JobAudit(workspace_id=workspace_id, job_type=job_type, idempotency_key=idempotency_key)
        db.add(audit)
    audit.status = "running"
    audit.error = None
    audit.started_at = datetime.now(UTC)
    audit.finished_at = None
    db.commit()
    return audit, False


def record_failure(idempotency_key: str, error: Exception, *, retrying: bool) -> None:
    try:
        with SessionLocal() as db:
            audit = db.scalar(select(JobAudit).where(JobAudit.idempotency_key == idempotency_key))
            if not audit:
                return
            audit.status = "retrying" if retrying else "failed"
            audit.error = f"{type(error).__name__}: {error}"[:2000]
            if not retrying:
                audit.finished_at = datetime.now(UTC)
            db.commit()
    except Exception:
        # Preserve the original task error if the audit database itself is unavailable.
        return


def retry_or_raise(task, idempotency_key: str, error: Exception):
    retrying = task.request.retries < task.max_retries
    record_failure(idempotency_key, error, retrying=retrying)
    if retrying:
        raise task.retry(exc=error, countdown=min(30 * (2**task.request.retries), 240))
    raise error


@celery_app.task
def enqueue_scheduled_radar_syncs() -> dict:
    now = datetime.now(UTC)
    window = int(now.timestamp()) // 900
    queued = 0
    with SessionLocal() as db:
        workspace_ids = db.scalars(
            select(RadarSource.workspace_id).where(RadarSource.is_active.is_(True)).distinct()
        ).all()
        for workspace_id in workspace_ids:
            idempotency_key = f"scheduled-radar-sync:{workspace_id}:{window}"
            if db.scalar(select(JobAudit.id).where(JobAudit.idempotency_key == idempotency_key)):
                continue
            audit = JobAudit(
                workspace_id=workspace_id,
                job_type="sync_radar_sources",
                idempotency_key=idempotency_key,
                status="queued",
            )
            db.add(audit)
            db.commit()
            try:
                sync_workspace_sources.delay(workspace_id, idempotency_key)
                queued += 1
            except Exception as error:
                audit.status = "failed"
                audit.error = f"QueueUnavailable: {type(error).__name__}"[:2000]
                audit.finished_at = now
                db.commit()
    return {"queued": queued}


@celery_app.task
def enqueue_scheduled_signal_cleanup() -> dict:
    now = datetime.now(UTC)
    idempotency_key = f"scheduled-signal-cleanup:{int(now.timestamp()) // 3600}"
    with SessionLocal() as db:
        if db.scalar(select(JobAudit.id).where(JobAudit.idempotency_key == idempotency_key)):
            return {"queued": 0}
        db.add(
            JobAudit(
                job_type="cleanup_expired_signals",
                idempotency_key=idempotency_key,
                status="queued",
            )
        )
        db.commit()
    try:
        cleanup_expired_signals.delay(idempotency_key)
    except Exception as error:
        record_failure(idempotency_key, error, retrying=False)
        return {"queued": 0}
    return {"queued": 1}


@celery_app.task(bind=True, max_retries=3)
def sync_workspace_sources(self, workspace_id: str, idempotency_key: str) -> dict:
    try:
        with SessionLocal() as db:
            audit, completed = start_audit(
                db,
                workspace_id=workspace_id,
                job_type="sync_radar_sources",
                idempotency_key=idempotency_key,
            )
            if completed:
                return {"status": "already-completed"}
            audit.attempts = self.request.retries + 1
            sources = db.scalars(
                select(RadarSource).where(
                    RadarSource.workspace_id == workspace_id,
                    RadarSource.is_active.is_(True),
                )
            ).all()
            collected = 0
            created = 0
            source_errors = 0
            for source in sources:
                try:
                    connector = RSSConnector(
                        source.name,
                        source.feed_url,
                        source.region,
                        source.language,
                        source.category,
                    )
                    signals = connector.collect()
                    source_created = 0
                    for signal in signals:
                        _, was_created = normalize_and_store(
                            db,
                            SignalIn(
                                workspace_id=workspace_id,
                                source=signal.source,
                                url=signal.url,
                                title=signal.title,
                                summary=signal.summary,
                                raw_text=signal.raw_text,
                                published_at=signal.published_at,
                                expires_at=signal.expires_at,
                                language=signal.language,
                                region=signal.region,
                                category=signal.category,
                                topics=signal.topics,
                                entities=signal.entities,
                                metrics=signal.metrics,
                            ),
                        )
                        source_created += int(was_created)
                    collected += len(signals)
                    created += source_created
                    source.last_status = "ok"
                    source.last_error = None
                    source.last_item_count = len(signals)
                except Exception as error:
                    source_errors += 1
                    source.last_status = "error"
                    source.last_error = f"{type(error).__name__}: {error}"[:2000]
                    source.last_item_count = 0
                source.last_synced_at = datetime.now(UTC)
                db.commit()
            _, opportunities_created, opportunities_updated = upsert_workspace_opportunities(db, workspace_id)
            audit.status = "completed"
            audit.finished_at = datetime.now(UTC)
            db.commit()
            return {
                "sources": len(sources),
                "source_errors": source_errors,
                "collected": collected,
                "created": created,
                "opportunities_created": opportunities_created,
                "opportunities_updated": opportunities_updated,
            }
    except (OSError, OperationalError) as error:
        return retry_or_raise(self, idempotency_key, error)
    except Exception as error:
        record_failure(idempotency_key, error, retrying=False)
        raise


@celery_app.task(bind=True, max_retries=3)
def cleanup_expired_signals(self, idempotency_key: str) -> dict:
    try:
        with SessionLocal() as db:
            audit, completed = start_audit(
                db,
                job_type="cleanup_expired_signals",
                idempotency_key=idempotency_key,
            )
            if completed:
                return {"status": "already-completed"}
            audit.attempts = self.request.retries + 1
            result = db.execute(delete(ExternalSignal).where(ExternalSignal.expires_at < datetime.now(UTC)))
            audit.status = "completed"
            audit.finished_at = datetime.now(UTC)
            db.commit()
            return {"deleted": result.rowcount}
    except (OSError, OperationalError) as error:
        return retry_or_raise(self, idempotency_key, error)
    except Exception as error:
        record_failure(idempotency_key, error, retrying=False)
        raise


@celery_app.task(bind=True, max_retries=3)
def rank_workspace(self, workspace_id: str, idempotency_key: str) -> dict:
    try:
        with SessionLocal() as db:
            audit, completed = start_audit(
                db,
                workspace_id=workspace_id,
                job_type="rank_workspace",
                idempotency_key=idempotency_key,
            )
            if completed:
                return {"status": "already-completed"}
            audit.attempts = self.request.retries + 1
            _, created, updated = upsert_workspace_opportunities(db, workspace_id)
            audit.status = "completed"
            audit.finished_at = datetime.now(UTC)
            db.commit()
            return {"created": created, "updated": updated}
    except (OSError, OperationalError) as error:
        return retry_or_raise(self, idempotency_key, error)
    except Exception as error:
        record_failure(idempotency_key, error, retrying=False)
        raise
