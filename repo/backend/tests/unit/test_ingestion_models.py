"""Unit tests for ingestion models and enums."""

from app.modules.ingestion.models import IngestionSource, IngestionSourceType, IngestionRun, IngestionRunStatus


def test_source_type_enum():
    expected = {"kafka", "flume", "logstash", "file", "mysql_cdc", "postgres_cdc"}
    actual = {t.value for t in IngestionSourceType}
    assert expected == actual


def test_run_status_enum():
    expected = {"queued", "running", "succeeded", "partial_failed", "failed", "canceled", "resolved"}
    actual = {s.value for s in IngestionRunStatus}
    assert expected == actual


def test_source_column_defaults():
    table = IngestionSource.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["collection_frequency_seconds"].default.arg == 300
    assert cols["concurrency_cap"].default.arg == 10
    assert cols["is_active"].default.arg is True
    assert cols["last_run_at"].nullable is True


def test_run_column_defaults():
    table = IngestionRun.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["rows_ingested"].default.arg == 0
    assert cols["error_detail"].nullable is True
