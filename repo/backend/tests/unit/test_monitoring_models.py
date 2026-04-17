"""Unit tests for monitoring/jobs models."""

from app.modules.jobs.models import JobExecution, MonitoringAlert


def test_job_execution_column_defaults():
    table = JobExecution.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["status"].default.arg == "success"
    assert cols["finished_at"].nullable is True
    assert cols["error_detail"].nullable is True


def test_monitoring_alert_column_defaults():
    table = MonitoringAlert.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["is_resolved"].default.arg is False
    assert cols["resolved_at"].nullable is True
    assert cols["job_name"].nullable is True


def test_job_execution_table_name():
    assert JobExecution.__tablename__ == "job_executions"


def test_monitoring_alert_table_name():
    assert MonitoringAlert.__tablename__ == "monitoring_alerts"
