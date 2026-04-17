"""Unit tests for role/permission utilities in app.core.deps."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.users.models import UserRole


def test_user_role_enum_has_all_roles():
    """UserRole enum contains all expected roles."""
    expected = {"admin", "instructor", "learner", "finance", "dataops"}
    actual = {r.value for r in UserRole}
    assert expected == actual


def test_role_enum_is_string_enum():
    """Roles are string values for JWT compatibility."""
    for role in UserRole:
        assert isinstance(role.value, str)
        assert role.value == role.name


def test_admin_has_highest_privilege_convention():
    """Admin role is first in the enum (convention check)."""
    roles = list(UserRole)
    assert roles[0] == UserRole.admin
