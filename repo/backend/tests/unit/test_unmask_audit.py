"""Unit tests for PII unmask audit-before-raise guarantee.

Verifies that log_audit is called regardless of whether the target user
exists — including the not-found path — and that the audit action differs
between success and failure outcomes.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.modules.users.service import UserService


def _make_service(user_return_value):
    """Return a UserService whose repository is fully mocked."""
    svc = UserService.__new__(UserService)
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=user_return_value)
    repo._db = MagicMock()
    svc._repo = repo
    return svc


def _make_user():
    from app.modules.users.models import User, UserRole
    u = User()
    u.id = uuid.uuid4()
    u.username = "test_user"
    u.role = UserRole.learner
    u.email_encrypted = None
    u.phone_encrypted = None
    u.is_active = True
    u.last_login = None
    u.created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    return u


@pytest.mark.asyncio
class TestUnmaskAuditBeforeRaise:

    async def test_not_found_audits_before_raising(self):
        """When the target user does not exist, an audit entry must be written
        BEFORE NotFoundError is raised."""
        svc = _make_service(user_return_value=None)
        actor_id = str(uuid.uuid4())
        target_id = str(uuid.uuid4())

        audit_calls = []

        async def capture_audit(db, actor, entity_type, entity_id, action, **kwargs):
            audit_calls.append({"actor": actor, "entity_id": entity_id, "action": action, **kwargs})

        with patch("app.modules.users.service.log_audit", side_effect=capture_audit):
            with pytest.raises(NotFoundError):
                await svc.unmask(target_id, actor_id=actor_id, reason="Compliance check")

        assert len(audit_calls) == 1, "Exactly one audit entry expected on not-found"
        assert audit_calls[0]["action"] == "unmask_pii_not_found"
        assert audit_calls[0]["actor"] == actor_id
        assert audit_calls[0]["entity_id"] == target_id

    async def test_not_found_audit_includes_reason(self):
        """The not-found audit entry must record the supplied reason."""
        svc = _make_service(user_return_value=None)
        reason = "GDPR request ref #42"

        audit_calls = []

        async def capture_audit(db, actor, entity_type, entity_id, action, **kwargs):
            audit_calls.append({"action": action, **kwargs})

        with patch("app.modules.users.service.log_audit", side_effect=capture_audit):
            with pytest.raises(NotFoundError):
                await svc.unmask(str(uuid.uuid4()), actor_id=str(uuid.uuid4()), reason=reason)

        assert audit_calls[0]["new_value"]["reason"] == reason

    async def test_success_audits_with_correct_action(self):
        """On success, the audit action must be 'unmask_pii' (not the not-found variant)."""
        user = _make_user()
        svc = _make_service(user_return_value=user)
        actor_id = str(uuid.uuid4())

        audit_calls = []

        async def capture_audit(db, actor, entity_type, entity_id, action, **kwargs):
            audit_calls.append({"action": action, **kwargs})

        with patch("app.modules.users.service.log_audit", side_effect=capture_audit):
            result = await svc.unmask(str(user.id), actor_id=actor_id, reason="Admin review")

        assert len(audit_calls) == 1
        assert audit_calls[0]["action"] == "unmask_pii"

    async def test_success_does_not_raise(self):
        """A valid user lookup must return a UserUnmaskResponse without raising."""
        user = _make_user()
        svc = _make_service(user_return_value=user)

        with patch("app.modules.users.service.log_audit", new_callable=AsyncMock):
            from app.modules.users.schemas import UserUnmaskResponse
            result = await svc.unmask(str(user.id), actor_id=str(uuid.uuid4()), reason="Test reason")
            assert isinstance(result, UserUnmaskResponse)
            assert result.id == user.id

    async def test_not_found_raises_only_after_audit(self):
        """Prove ordering: audit fires, then the exception propagates.

        Uses a flag set inside the mock to confirm the audit ran before the
        caller sees the exception.
        """
        svc = _make_service(user_return_value=None)
        audit_fired = []

        async def recording_audit(db, actor, entity_type, entity_id, action, **kwargs):
            audit_fired.append(action)

        with patch("app.modules.users.service.log_audit", side_effect=recording_audit):
            with pytest.raises(NotFoundError):
                await svc.unmask(str(uuid.uuid4()), actor_id=str(uuid.uuid4()), reason="Testing order")

        # If audit had NOT fired before the raise, audit_fired would be empty.
        assert audit_fired, "Audit must have fired before NotFoundError was raised"
