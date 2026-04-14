"""Unit tests for search role-scope ABAC filtering.

Tests _apply_scope() directly to verify each role produces the correct SQL
predicate without needing a live database.
"""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql

from app.modules.bookings.models import Booking
from app.modules.checkout.models import Order, OrderItem
from app.modules.instructors.models import Instructor
from app.modules.search.service import _apply_scope, _build_base_query
from app.modules.search.schemas import SearchFilters


def _compile(q) -> str:
    """Compile a SQLAlchemy query to a PostgreSQL SQL string for assertion.
    literal_binds=True inlines bound parameters so tests can assert on values
    like 'paid' rather than placeholder names like %(status_2)s.
    """
    return str(q.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


class TestApplyScopeAdmin:
    def test_admin_no_predicate_added(self):
        """Admin role must not add any additional WHERE clause."""
        filters = SearchFilters()
        q_no_scope = _build_base_query(filters)
        q_admin = _build_base_query(filters, caller_role="admin", caller_id=uuid.uuid4())

        sql_no_scope = _compile(q_no_scope)
        sql_admin = _compile(q_admin)
        # Admin query must be identical to the unscoped query
        assert sql_no_scope == sql_admin

    def test_none_role_no_predicate_added(self):
        filters = SearchFilters()
        q = _build_base_query(filters, caller_role=None, caller_id=None)
        q_ref = _build_base_query(filters)
        assert _compile(q) == _compile(q_ref)


class TestApplyScopeInstructor:
    def test_instructor_scope_filters_by_user_id(self):
        """Instructor scope must add a predicate linking Instructor.user_id to the caller."""
        caller_id = uuid.uuid4()
        filters = SearchFilters()
        q = _build_base_query(filters, caller_role="instructor", caller_id=caller_id)
        sql = _compile(q)
        # The query must reference instructor.user_id in a WHERE clause
        assert "instructors.user_id" in sql.lower()

    def test_instructor_scope_absent_without_caller_id(self):
        """When caller_id is None, no instructor scope predicate is added."""
        filters = SearchFilters()
        q_scoped = _build_base_query(filters, caller_role="instructor", caller_id=None)
        q_ref = _build_base_query(filters)
        assert _compile(q_scoped) == _compile(q_ref)

    def test_instructor_scope_differs_from_unscoped(self):
        """Instructor-scoped query must differ from unscoped query."""
        filters = SearchFilters()
        q_ref = _build_base_query(filters)
        q_scoped = _build_base_query(filters, caller_role="instructor", caller_id=uuid.uuid4())
        assert _compile(q_ref) != _compile(q_scoped)


class TestApplyScopeFinance:
    def test_finance_scope_restricts_to_paid_orders(self):
        """Finance scope must add a predicate requiring an associated paid order."""
        filters = SearchFilters()
        q = _build_base_query(filters, caller_role="finance", caller_id=uuid.uuid4())
        sql = _compile(q)
        # The query must reference orders and the 'paid' status
        assert "orders" in sql.lower()
        assert "paid" in sql.lower()

    def test_finance_scope_uses_exists(self):
        """Finance scope must use an EXISTS subquery (not a join) to avoid row duplication."""
        filters = SearchFilters()
        q = _build_base_query(filters, caller_role="finance", caller_id=None)
        sql = _compile(q)
        assert "exists" in sql.lower()

    def test_finance_scope_differs_from_unscoped(self):
        """Finance-scoped query must differ from unscoped query."""
        filters = SearchFilters()
        q_ref = _build_base_query(filters)
        q_scoped = _build_base_query(filters, caller_role="finance")
        assert _compile(q_ref) != _compile(q_scoped)

    def test_finance_scope_independent_of_caller_id(self):
        """Finance scope is domain-based, not user-specific; caller_id should not matter."""
        filters = SearchFilters()
        q_with_id = _build_base_query(filters, caller_role="finance", caller_id=uuid.uuid4())
        q_without_id = _build_base_query(filters, caller_role="finance", caller_id=None)
        # Both queries must be identical (finance scope is role-level, not user-level)
        assert _compile(q_with_id) == _compile(q_without_id)


class TestApplyScopeIsolation:
    def test_instructor_and_finance_scopes_are_distinct(self):
        """Instructor and finance scopes must produce different SQL."""
        filters = SearchFilters()
        instructor_id = uuid.uuid4()
        q_instr = _build_base_query(filters, caller_role="instructor", caller_id=instructor_id)
        q_finance = _build_base_query(filters, caller_role="finance", caller_id=instructor_id)
        assert _compile(q_instr) != _compile(q_finance)
