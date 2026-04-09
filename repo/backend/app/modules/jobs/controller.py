from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.core.deps import require_roles
from app.modules.jobs.models import JobExecution, MonitoringAlert
from app.modules.jobs.schemas import (
    AlertResponse, JobExecutionResponse, JobStatRow, JobStatsAggregate,
)

router = APIRouter(prefix="/jobs", tags=["Jobs & Monitoring"])


@router.get("", response_model=list[str])
async def list_jobs(_=Depends(require_roles("admin", "dataops"))):
    from app.modules.jobs.celery_app import celery_app
    return list(celery_app.conf.beat_schedule.keys())


@router.get("/stats/aggregate", response_model=JobStatsAggregate)
async def get_job_stats(
    window_minutes: int = Query(60, ge=1, le=1440),
    _=Depends(require_roles("admin", "dataops")),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin console endpoint: job throughput, latency, success rate.
    Queries job_executions table directly — not Grafana.
    """
    since = datetime.now(UTC) - timedelta(minutes=window_minutes)

    je_inner = aliased(JobExecution)
    result = await db.execute(
        select(
            JobExecution.job_name,
            func.count().label("total"),
            func.sum((JobExecution.status == "success").cast(Integer)).label("success_count"),
            func.sum((JobExecution.status == "failure").cast(Integer)).label("failure_count"),
            func.avg(
                func.extract(
                    "epoch",
                    JobExecution.finished_at - JobExecution.started_at
                ) * 1000
            ).label("avg_duration_ms"),
            func.percentile_cont(0.95).within_group(
                func.extract("epoch", JobExecution.finished_at - JobExecution.started_at) * 1000
            ).label("p95_duration_ms"),
            func.max(JobExecution.started_at).label("last_run_at"),
            (select(je_inner.status)
             .where(je_inner.job_name == JobExecution.job_name)
             .order_by(je_inner.started_at.desc())
             .limit(1)
             .correlate(JobExecution)
             .scalar_subquery()
            ).label("last_status"),
        )
        .where(JobExecution.started_at >= since)
        .group_by(JobExecution.job_name)
    )
    rows = result.all()

    stats: list[JobStatRow] = []
    for row in rows:
        total = row.total or 0
        success = row.success_count or 0
        failure = row.failure_count or 0
        stats.append(JobStatRow(
            job_name=row.job_name,
            total_executions=total,
            success_count=success,
            failure_count=failure,
            success_rate_pct=round(success / total * 100, 1) if total else 0.0,
            avg_duration_ms=round(float(row.avg_duration_ms or 0), 1),
            p95_duration_ms=round(float(row.p95_duration_ms or 0), 1),
            last_run_at=row.last_run_at,
            last_status=row.last_status,
        ))

    return JobStatsAggregate(window_minutes=window_minutes, jobs=stats)


@router.post("/{job_name}/trigger", status_code=202)
async def trigger_job(
    job_name: str,
    _=Depends(require_roles("admin", "dataops")),
):
    """Manually trigger a scheduled job by its beat-schedule key or full task name."""
    from app.modules.jobs.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule

    # Accept: friendly key ("close-expired-orders"), full task name, or short name ("close_expired_orders")
    if job_name in schedule:
        task_name = schedule[job_name]["task"]
    else:
        full_task_names = {v["task"] for v in schedule.values()}
        short_name_map = {v["task"].rsplit(".", 1)[-1]: v["task"] for v in schedule.values()}
        if job_name in full_task_names:
            task_name = job_name
        elif job_name in short_name_map:
            task_name = short_name_map[job_name]
        else:
            from fastapi import HTTPException
            raise HTTPException(404, detail=f"Job '{job_name}' not found in beat schedule")

    celery_app.send_task(task_name)
    return {"queued": task_name}


@router.get("/{job_name}/executions", response_model=list[JobExecutionResponse])
async def get_executions(
    job_name: str,
    limit: int = Query(50, ge=1, le=500),
    _=Depends(require_roles("admin", "dataops")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobExecution)
        .where(JobExecution.job_name == job_name)
        .order_by(JobExecution.started_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
