"""Unit tests for replay models and enums."""

from app.modules.replays.models import ReplayAccessRule, ReplayRuleType, ReplayView, RecordingUploadStatus, SessionRecording


def test_replay_rule_type_enum():
    expected = {"enrolled_only", "public", "custom"}
    actual = {t.value for t in ReplayRuleType}
    assert expected == actual


def test_recording_upload_status_enum():
    expected = {"pending", "processing", "ready", "failed"}
    actual = {s.value for s in RecordingUploadStatus}
    assert expected == actual


def test_session_recording_column_defaults():
    table = SessionRecording.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["upload_status"].default.arg == RecordingUploadStatus.pending
    assert cols["mime_type"].default.arg == "video/mp4"
    assert cols["file_size_bytes"].nullable is True
    assert cols["duration_seconds"].nullable is True


def test_replay_access_rule_column_defaults():
    table = ReplayAccessRule.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["rule_type"].default.arg == ReplayRuleType.enrolled_only
    assert cols["is_active"].default.arg is True
    assert cols["available_from"].nullable is True


def test_replay_view_column_defaults():
    table = ReplayView.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["watched_seconds"].default.arg == 0
    assert cols["completed"].default.arg is False


def test_replay_schema_defaults():
    from app.modules.replays.schemas import ReplayViewCreate
    view = ReplayViewCreate()
    assert view.watched_seconds == 0
    assert view.completed is False


def test_replay_access_rule_create_schema_default():
    from app.modules.replays.schemas import ReplayAccessRuleCreate
    rule = ReplayAccessRuleCreate()
    assert rule.rule_type == ReplayRuleType.enrolled_only
    assert rule.available_from is None
