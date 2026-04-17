"""Unit tests for attendance record model defaults and schema."""

import uuid


def test_attendance_record_column_defaults():
    """AttendanceRecord model documents expected column defaults."""
    from app.modules.attendance.models import AttendanceRecord

    table = AttendanceRecord.__table__
    cols = {c.name: c for c in table.columns}

    assert cols["minutes_attended"].default.arg == 0
    assert cols["was_late"].default.arg is False
    assert cols["joined_at"].nullable is True
    assert cols["left_at"].nullable is True


def test_attendance_schema_accepts_valid_data():
    """AttendanceRecordResponse schema accepts valid attendance data."""
    from app.modules.attendance.schemas import AttendanceRecordResponse

    resp = AttendanceRecordResponse(
        id=uuid.uuid4(), session_id=uuid.uuid4(), learner_id=uuid.uuid4(),
        joined_at=None, left_at=None, minutes_attended=0, was_late=False,
    )
    assert resp.minutes_attended == 0
    assert resp.was_late is False


def test_attendance_schema_with_late_flag():
    """Late flag tracks tardy arrivals via schema."""
    from app.modules.attendance.schemas import AttendanceRecordResponse
    from datetime import datetime, UTC

    now = datetime.now(UTC)
    resp = AttendanceRecordResponse(
        id=uuid.uuid4(), session_id=uuid.uuid4(), learner_id=uuid.uuid4(),
        joined_at=now, left_at=now, minutes_attended=45, was_late=True,
    )
    assert resp.was_late is True
    assert resp.minutes_attended == 45
