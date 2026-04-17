"""Unit tests for policy service defaults and schema."""

from app.modules.policy.schemas import AdminPolicyResponse, AdminPolicyUpdate
from app.modules.policy.models import AdminPolicy


def test_policy_defaults():
    defaults = AdminPolicyResponse(reschedule_cutoff_hours=2, cancellation_fee_hours=24)
    assert defaults.reschedule_cutoff_hours == 2
    assert defaults.cancellation_fee_hours == 24


def test_policy_update_partial():
    update = AdminPolicyUpdate(reschedule_cutoff_hours=6)
    dumped = update.model_dump(exclude_none=True)
    assert dumped == {"reschedule_cutoff_hours": 6}


def test_policy_update_full():
    update = AdminPolicyUpdate(reschedule_cutoff_hours=4, cancellation_fee_hours=48)
    dumped = update.model_dump(exclude_none=True)
    assert dumped["reschedule_cutoff_hours"] == 4
    assert dumped["cancellation_fee_hours"] == 48


def test_admin_policy_column_defaults():
    table = AdminPolicy.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["reschedule_cutoff_hours"].default.arg == 2
    assert cols["cancellation_fee_hours"].default.arg == 24
    assert cols["updated_by"].nullable is True
