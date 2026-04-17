"""Unit tests for search models and export job status."""

from app.modules.search.models import SavedSearch, SearchExportJob, SearchExportJobStatus


def test_export_job_status_enum():
    expected = {"queued", "processing", "completed", "failed"}
    actual = {s.value for s in SearchExportJobStatus}
    assert expected == actual


def test_export_job_column_defaults():
    table = SearchExportJob.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["status"].default.arg == SearchExportJobStatus.queued
    assert cols["format"].default.arg == "csv"
    assert cols["file_path"].nullable is True
    assert cols["row_count"].nullable is True


def test_saved_search_table():
    assert SavedSearch.__tablename__ == "saved_searches"
    table = SavedSearch.__table__
    cols = {c.name: c for c in table.columns}
    assert "name" in cols
    assert "filters_json" in cols
    assert "user_id" in cols
