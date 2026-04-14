"""Celery tasks — all background jobs for Meridian."""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from app.modules.jobs.celery_app import celery_app

logger = logging.getLogger(__name__)


def _set_job_context(job_name: str) -> str:
    """Set a job-scoped correlation ID in the logging context and return it."""
    import uuid as _uuid
    from app.core.logging import request_id_var
    job_id = f"job:{job_name}:{_uuid.uuid4().hex[:8]}"
    request_id_var.set(job_id)
    return job_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _get_db():
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _record_execution(job_name: str, started_at: datetime, status: str, error: str | None = None):
    from app.modules.jobs.models import JobExecution
    async with _get_db() as db:
        exec_row = JobExecution(
            job_name=job_name,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            status=status,
            error_detail=error,
        )
        db.add(exec_row)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.modules.jobs.tasks.close_expired_orders",
    bind=True, max_retries=5, default_retry_delay=30,
)
def close_expired_orders(self):
    started = datetime.now(UTC)
    try:
        _run_async(_close_expired_orders_async())
        _run_async(_record_execution("close_expired_orders", started, "success"))
    except Exception as exc:
        _run_async(_record_execution("close_expired_orders", started, "failure", str(exc)))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


async def _close_expired_orders_async():
    from sqlalchemy import update, and_
    from app.modules.checkout.models import Order, OrderStatus

    async with _get_db() as db:
        now = datetime.now(UTC)
        await db.execute(
            update(Order)
            .where(and_(Order.status == OrderStatus.awaiting_payment, Order.expires_at <= now))
            .values(status=OrderStatus.closed_unpaid, closed_at=now)
        )
    logger.info("Expired orders closed.")


@celery_app.task(
    name="app.modules.jobs.tasks.attendance_rollup",
    bind=True, max_retries=5, default_retry_delay=60,
)
def attendance_rollup(self):
    started = datetime.now(UTC)
    try:
        _run_async(_attendance_rollup_async())
        _run_async(_record_execution("attendance_rollup", started, "success"))
    except Exception as exc:
        _run_async(_record_execution("attendance_rollup", started, "failure", str(exc)))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)


async def _attendance_rollup_async():
    """Update minutes_attended for open attendance records (joined but not left)."""
    from sqlalchemy import select, update, and_
    from app.modules.attendance.models import AttendanceRecord

    async with _get_db() as db:
        now = datetime.now(UTC)
        result = await db.execute(
            select(AttendanceRecord).where(
                and_(AttendanceRecord.joined_at.isnot(None), AttendanceRecord.left_at.is_(None))
            )
        )
        records = result.scalars().all()
        for r in records:
            delta = now - r.joined_at.replace(tzinfo=UTC)
            r.minutes_attended = int(delta.total_seconds() / 60)
    logger.info("Attendance rollup complete for %d open records.", len(records) if 'records' in dir() else 0)


@celery_app.task(
    name="app.modules.jobs.tasks.replay_access_expiry",
    bind=True, max_retries=5, default_retry_delay=60,
)
def replay_access_expiry(self):
    started = datetime.now(UTC)
    try:
        _run_async(_replay_access_expiry_async())
        _run_async(_record_execution("replay_access_expiry", started, "success"))
    except Exception as exc:
        _run_async(_record_execution("replay_access_expiry", started, "failure", str(exc)))
        raise self.retry(exc=exc)


async def _replay_access_expiry_async():
    from sqlalchemy import update, and_
    from app.modules.replays.models import ReplayAccessRule

    async with _get_db() as db:
        now = datetime.now(UTC)
        await db.execute(
            update(ReplayAccessRule)
            .where(and_(ReplayAccessRule.available_until <= now, ReplayAccessRule.is_active == True))
            .values(is_active=False)
        )
    logger.info("Expired replay access rules deactivated.")


@celery_app.task(
    name="app.modules.jobs.tasks.generate_reconciliation_export",
    bind=True, max_retries=5, default_retry_delay=120,
)
def generate_reconciliation_export(self):
    started = datetime.now(UTC)
    try:
        _run_async(_generate_reconciliation_async())
        _run_async(_record_execution("generate_reconciliation_export", started, "success"))
    except Exception as exc:
        _run_async(_record_execution("generate_reconciliation_export", started, "failure", str(exc)))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 120)


async def _generate_reconciliation_async():
    from app.modules.payments.service import PaymentService
    async with _get_db() as db:
        svc = PaymentService(db)
        export = await svc.generate_reconciliation_export()
        logger.info("Reconciliation export generated: %s (%d rows)", export.file_path, export.row_count)


@celery_app.task(
    name="app.modules.jobs.tasks.purge_audit_logs",
    bind=True, max_retries=2, default_retry_delay=300,
)
def purge_audit_logs(self):
    started = datetime.now(UTC)
    try:
        _run_async(_purge_audit_logs_async())
        _run_async(_record_execution("purge_audit_logs", started, "success"))
    except Exception as exc:
        _run_async(_record_execution("purge_audit_logs", started, "failure", str(exc)))
        raise self.retry(exc=exc)


async def _purge_audit_logs_async():
    from sqlalchemy import delete
    from app.core.config import settings
    from app.modules.audit.models import AuditLog

    async with _get_db() as db:
        cutoff = datetime.now(UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
        result = await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        logger.info("Purged %d audit log entries older than %d days.", result.rowcount, settings.AUDIT_LOG_RETENTION_DAYS)


@celery_app.task(
    name="app.modules.jobs.tasks.check_job_health",
    bind=True, max_retries=1,
)
def check_job_health(self):
    started = datetime.now(UTC)
    try:
        _run_async(_check_job_health_async())
        _run_async(_record_execution("check_job_health", started, "success"))
    except Exception as exc:
        _run_async(_record_execution("check_job_health", started, "failure", str(exc)))


async def _check_job_health_async():
    from sqlalchemy import Integer, select, func, and_
    from app.core.config import settings
    from app.modules.jobs.models import JobExecution, MonitoringAlert

    async with _get_db() as db:
        window_start = datetime.now(UTC) - timedelta(hours=1)

        # Get job stats per name in last hour
        result = await db.execute(
            select(
                JobExecution.job_name,
                func.count().label("total"),
                func.sum((JobExecution.status == "failure").cast(Integer)).label("failures"),
                func.max(JobExecution.started_at).label("last_run"),
            )
            .where(JobExecution.started_at >= window_start)
            .group_by(JobExecution.job_name)
        )
        stats = result.all()

        for row in stats:
            failure_rate = (row.failures / row.total * 100) if row.total else 0
            if failure_rate > settings.JOB_FAILURE_RATE_THRESHOLD_PCT:
                alert = MonitoringAlert(
                    alert_type="high_failure_rate",
                    message=f"Job '{row.job_name}' failure rate: {failure_rate:.1f}% in last hour.",
                    job_name=row.job_name,
                )
                db.add(alert)
                logger.warning("ALERT: %s failure rate %.1f%%", row.job_name, failure_rate)

        # Check for late jobs — covers both interval (int/float seconds) and crontab schedules
        from celery.schedules import crontab
        from app.modules.jobs.celery_app import celery_app as _ca

        now = datetime.now(UTC)
        for task_name, schedule_conf in _ca.conf.beat_schedule.items():
            sched = schedule_conf.get("schedule")
            job_key = schedule_conf.get("task", "").split(".")[-1]
            expected_latest: datetime | None = None

            if isinstance(sched, (int, float)):
                interval_minutes = sched / 60
                expected_latest = now - timedelta(minutes=interval_minutes + settings.JOB_LATENESS_THRESHOLD_MINUTES)
            elif isinstance(sched, crontab):
                # For crontab jobs, the expected period is 24 hours (daily).
                # A daily job is considered late if it hasn't run within the last
                # 24 hours + the configured lateness threshold.
                expected_latest = now - timedelta(hours=24, minutes=settings.JOB_LATENESS_THRESHOLD_MINUTES)

            if expected_latest is None:
                continue

            last_run_result = await db.execute(
                select(func.max(JobExecution.started_at)).where(JobExecution.job_name == job_key)
            )
            last_run = last_run_result.scalar_one()
            if last_run and last_run < expected_latest:
                alert = MonitoringAlert(
                    alert_type="job_late",
                    message=f"Job '{job_key}' last ran at {last_run.isoformat()}, expected by {expected_latest.isoformat()}.",
                    job_name=job_key,
                )
                db.add(alert)
                logger.warning("ALERT: Job %s is late.", job_key)


@celery_app.task(
    name="app.modules.jobs.tasks.run_search_export",
    bind=True, max_retries=3, default_retry_delay=30,
)
def run_search_export(self, job_id: str):
    """Execute a queued search export job and persist the result file.

    The job row is updated to ``processing`` when work begins, then to
    ``completed`` (with ``file_path`` and ``row_count``) on success, or
    ``failed`` (with ``error_detail``) on unrecoverable error.
    """
    _set_job_context("run_search_export")
    started = datetime.now(UTC)
    try:
        _run_async(_run_search_export_async(job_id))
        _run_async(_record_execution("run_search_export", started, "success"))
    except Exception as exc:
        _run_async(_record_execution("run_search_export", started, "failure", str(exc)))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


async def _run_search_export_async(job_id: str):
    import os
    from app.core.config import settings
    from app.modules.search.models import SearchExportJob, SearchExportJobStatus
    from app.modules.search.schemas import SearchFilters
    from app.modules.search.service import SearchService
    from sqlalchemy import select as _select

    async with _get_db() as db:
        # Fetch the job row and mark it as processing
        result = await db.execute(_select(SearchExportJob).where(SearchExportJob.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if not job:
            logger.error("run_search_export: job %s not found", job_id)
            return

        job.status = SearchExportJobStatus.processing
        await db.flush()

        try:
            filters = SearchFilters(**job.filters_json)
            svc = SearchService(db)
            data: bytes = await svc.export(
                filters=filters,
                fmt=job.format,
                caller_role=job.caller_role,
                caller_id=job.caller_id,
            )

            os.makedirs(settings.EXPORTS_DIR, exist_ok=True)
            ext = "xlsx" if job.format == "excel" else "csv"
            file_path = os.path.join(settings.EXPORTS_DIR, f"search_export_{job_id}.{ext}")
            with open(file_path, "wb") as fh:
                fh.write(data)

            # Count rows: subtract 1 for the header line (CSV), or count bytes for xlsx
            row_count = max(0, data.count(b"\n") - 1) if job.format == "csv" else None

            job.status = SearchExportJobStatus.completed
            job.file_path = file_path
            job.row_count = row_count
            job.completed_at = datetime.now(UTC)
            logger.info("run_search_export: job %s completed (%s rows)", job_id, row_count)
        except Exception as exc:
            job.status = SearchExportJobStatus.failed
            job.error_detail = str(exc)
            job.completed_at = datetime.now(UTC)
            logger.error("run_search_export: job %s failed: %r", job_id, exc)
            raise


@celery_app.task(
    name="app.modules.jobs.tasks.run_ingestion_jobs",
    bind=True, max_retries=5, default_retry_delay=60,
)
def run_ingestion_jobs(self):
    started = datetime.now(UTC)
    try:
        _run_async(_run_ingestion_jobs_async())
        _run_async(_record_execution("run_ingestion_jobs", started, "success"))
    except Exception as exc:
        _run_async(_record_execution("run_ingestion_jobs", started, "failure", str(exc)))
        raise self.retry(exc=exc)


async def _run_ingestion_jobs_async():
    from sqlalchemy import select
    from app.modules.ingestion.models import IngestionSource
    from app.modules.ingestion.service import IngestionService

    async with _get_db() as db:
        result = await db.execute(select(IngestionSource).where(IngestionSource.is_active == True))
        sources = result.scalars().all()
        svc = IngestionService(db)
        for source in sources:
            # Respect per-source frequency
            if source.last_run_at:
                elapsed = (datetime.now(UTC) - source.last_run_at.replace(tzinfo=UTC)).total_seconds()
                if elapsed < source.collection_frequency_seconds:
                    continue
            await svc.run_source(source)
