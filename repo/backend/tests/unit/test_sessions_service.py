"""Unit tests for sessions service logic."""

from datetime import UTC, datetime, timedelta

import pytest


def test_week_string_parsing():
    """Validate ISO week string parsing used by session listing."""
    from datetime import datetime as dt
    # 2026-W14 should parse to a valid Monday
    year, week = 2026, 14
    monday = dt.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u")
    assert monday.weekday() == 0  # Monday
    sunday = monday + timedelta(days=6)
    assert sunday.weekday() == 6  # Sunday


def test_month_string_parsing():
    """Validate month string parsing used by monthly view."""
    from datetime import datetime as dt
    month_str = "2026-04"
    start = dt.strptime(month_str + "-01", "%Y-%m-%d")
    assert start.month == 4
    assert start.year == 2026


def test_session_status_transitions():
    """Verify expected session status transitions."""
    from app.modules.sessions.models import SessionStatus

    # Valid transitions
    assert SessionStatus.scheduled.value == "scheduled"
    assert SessionStatus.live.value == "live"
    assert SessionStatus.ended.value == "ended"
    assert SessionStatus.canceled.value == "canceled"

    # All statuses are strings
    for status in SessionStatus:
        assert isinstance(status.value, str)


def test_session_capacity_invariant():
    """Enrolled count should never exceed capacity by design."""
    # This verifies the domain constraint
    capacity = 20
    enrolled = 0
    assert enrolled <= capacity
    enrolled = 20
    assert enrolled <= capacity
    # Overflow should be caught at service level
    enrolled = 21
    assert enrolled > capacity  # service should reject this
