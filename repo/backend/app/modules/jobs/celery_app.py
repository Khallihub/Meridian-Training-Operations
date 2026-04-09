from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "meridian",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.modules.jobs.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "close-expired-orders": {
            "task": "app.modules.jobs.tasks.close_expired_orders",
            "schedule": 60.0,  # every 60 seconds
        },
        "attendance-rollup": {
            "task": "app.modules.jobs.tasks.attendance_rollup",
            "schedule": 300.0,  # every 5 minutes
        },
        "replay-access-expiry": {
            "task": "app.modules.jobs.tasks.replay_access_expiry",
            "schedule": 600.0,  # every 10 minutes
        },
        "check-job-health": {
            "task": "app.modules.jobs.tasks.check_job_health",
            "schedule": 120.0,  # every 2 minutes
        },
        "generate-reconciliation-export": {
            "task": "app.modules.jobs.tasks.generate_reconciliation_export",
            "schedule": crontab(hour=settings.RECONCILIATION_HOUR, minute=0),
        },
        "purge-audit-logs": {
            "task": "app.modules.jobs.tasks.purge_audit_logs",
            "schedule": crontab(hour=3, minute=0),
        },
        "run-ingestion-jobs": {
            "task": "app.modules.jobs.tasks.run_ingestion_jobs",
            "schedule": 300.0,  # every 5 minutes; per-source frequency enforced inside
        },
    },
)
