from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class JobExecutionResponse(BaseModel):
    id: uuid.UUID
    job_name: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    error_detail: str | None

    model_config = {"from_attributes": True}


class JobStatRow(BaseModel):
    job_name: str
    total_executions: int
    success_count: int
    failure_count: int
    success_rate_pct: float
    avg_duration_ms: float
    p95_duration_ms: float
    last_run_at: datetime | None
    last_status: str | None


class JobStatsAggregate(BaseModel):
    window_minutes: int
    jobs: list[JobStatRow]


class AlertResponse(BaseModel):
    id: uuid.UUID
    alert_type: str
    message: str
    job_name: str | None
    is_resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}
