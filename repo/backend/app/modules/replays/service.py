from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.config import settings
from app.core.exceptions import ForbiddenError, GoneError, NotFoundError
from app.core.storage import get_presigned_download_url, get_presigned_upload_url
from app.modules.bookings.models import Booking, BookingStatus
from app.modules.replays.models import (
    RecordingUploadStatus, ReplayAccessRule, ReplayRuleType,
    ReplayView, SessionRecording,
)
from app.modules.replays.schemas import (
    ReplayAccessRuleCreate, ReplayAccessRuleResponse, ReplayStats,
    ReplayViewCreate, RecordingResponse,
)
from app.modules.sessions.repository import SessionRepository


class ReplayService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._session_repo = SessionRepository(db)

    async def _check_access(self, session_id: uuid.UUID, user_id: uuid.UUID, user_role: str) -> None:
        """Raise ForbiddenError if user cannot access the replay."""
        if user_role in ("admin", "instructor"):
            return

        result = await self._db.execute(
            select(ReplayAccessRule).where(
                and_(ReplayAccessRule.session_id == session_id, ReplayAccessRule.is_active == True)
            )
        )
        rule = result.scalar_one_or_none()

        now = datetime.now(UTC)
        if rule:
            if rule.available_from and now < rule.available_from:
                raise ForbiddenError("Replay is not yet available.")
            if rule.available_until and now > rule.available_until:
                raise GoneError("Replay access has expired.")
            if rule.rule_type == ReplayRuleType.public:
                return

        # Default (no rule) and enrolled_only rule: require a confirmed booking
        booking_result = await self._db.execute(
            select(Booking).where(
                and_(
                    Booking.session_id == session_id,
                    Booking.learner_id == user_id,
                    Booking.status == BookingStatus.confirmed,
                )
            )
        )
        if not booking_result.scalar_one_or_none():
            raise ForbiddenError("Only enrolled learners can access this replay.")

    async def get_replay(self, session_id: uuid.UUID, user_id: uuid.UUID, user_role: str) -> RecordingResponse:
        await self._check_access(session_id, user_id, user_role)
        result = await self._db.execute(
            select(SessionRecording)
            .where(
                and_(
                    SessionRecording.session_id == session_id,
                    SessionRecording.upload_status == RecordingUploadStatus.ready,
                )
            )
            .order_by(desc(SessionRecording.created_at))
            .limit(1)
        )
        recording = result.scalar_one_or_none()
        if not recording:
            raise NotFoundError("Recording")

        resp = RecordingResponse.model_validate(recording)
        return resp

    async def get_all_recordings(self, session_id: uuid.UUID, user_id: uuid.UUID, user_role: str) -> list[RecordingResponse]:
        await self._check_access(session_id, user_id, user_role)
        result = await self._db.execute(
            select(SessionRecording)
            .where(
                and_(
                    SessionRecording.session_id == session_id,
                    SessionRecording.upload_status == RecordingUploadStatus.ready,
                )
            )
            .order_by(desc(SessionRecording.created_at))
        )
        recordings = result.scalars().all()
        return [RecordingResponse.model_validate(r) for r in recordings]

    async def initiate_upload(self, session_id: uuid.UUID) -> dict:
        """Returns a presigned PUT URL for direct upload to MinIO."""
        session = await self._session_repo.get(session_id)
        if not session:
            raise NotFoundError("Session")

        object_key = f"sessions/{session_id}/recording.mp4"
        bucket = settings.MINIO_BUCKET_RECORDINGS

        # Create or update recording metadata row
        result = await self._db.execute(
            select(SessionRecording).where(SessionRecording.session_id == session_id)
        )
        recording = result.scalar_one_or_none()
        if not recording:
            recording = SessionRecording(
                session_id=session_id,
                object_storage_key=object_key,
                bucket_name=bucket,
                upload_status=RecordingUploadStatus.pending,
            )
            self._db.add(recording)
        else:
            recording.object_storage_key = object_key
            recording.upload_status = RecordingUploadStatus.pending
        await self._db.flush()

        presigned_url = get_presigned_upload_url(bucket, object_key)
        return {"presigned_url": presigned_url, "object_key": object_key, "bucket": bucket}

    async def confirm_upload(self, session_id: uuid.UUID, file_size_bytes: int | None, duration_seconds: int | None) -> RecordingResponse:
        result = await self._db.execute(
            select(SessionRecording).where(SessionRecording.session_id == session_id)
        )
        recording = result.scalar_one_or_none()
        if not recording:
            raise NotFoundError("Recording")
        recording.upload_status = RecordingUploadStatus.ready
        if file_size_bytes:
            recording.file_size_bytes = file_size_bytes
        if duration_seconds:
            recording.duration_seconds = duration_seconds
        await self._db.flush()
        return RecordingResponse.model_validate(recording)

    async def store_recording_direct(
        self, session_id: uuid.UUID, data: bytes, file_size_bytes: int, duration_seconds: int, content_type: str
    ) -> RecordingResponse:
        """Upload recording bytes directly to MinIO (used when presigned URLs are unreachable from browser)."""
        from app.core.storage import upload_object

        session = await self._session_repo.get(session_id)
        if not session:
            raise NotFoundError("Session")

        recording_id = uuid.uuid4()
        # Derive extension from content_type (webm or mp4)
        ext = "webm" if "webm" in content_type else "mp4"
        object_key = f"sessions/{session_id}/{recording_id}.{ext}"
        bucket = settings.MINIO_BUCKET_RECORDINGS

        upload_object(bucket, object_key, data, content_type)

        recording = SessionRecording(
            id=recording_id,
            session_id=session_id,
            object_storage_key=object_key,
            bucket_name=bucket,
            mime_type=content_type,
            upload_status=RecordingUploadStatus.ready,
            file_size_bytes=file_size_bytes,
            duration_seconds=duration_seconds,
        )
        self._db.add(recording)
        await self._db.flush()
        return RecordingResponse.model_validate(recording)

    async def set_access_rule(self, session_id: uuid.UUID, payload: ReplayAccessRuleCreate, actor_id: str | None = None) -> ReplayAccessRuleResponse:
        result = await self._db.execute(
            select(ReplayAccessRule).where(ReplayAccessRule.session_id == session_id)
        )
        rule = result.scalar_one_or_none()
        action = "update" if rule else "create"
        if rule:
            rule.rule_type = payload.rule_type
            rule.available_from = payload.available_from
            rule.available_until = payload.available_until
            rule.is_active = True
        else:
            rule = ReplayAccessRule(session_id=session_id, **payload.model_dump())
            self._db.add(rule)
        await self._db.flush()
        await log_audit(self._db, actor_id or "system", "replay_access_rule", str(session_id), action,
                        new_value=payload.model_dump(mode="json"))
        return ReplayAccessRuleResponse.model_validate(rule)

    async def record_view(self, session_id: uuid.UUID, learner_id: uuid.UUID, payload: ReplayViewCreate, user_role: str = "learner") -> None:
        await self._check_access(session_id, learner_id, user_role)
        view = ReplayView(
            session_id=session_id,
            learner_id=learner_id,
            watched_seconds=payload.watched_seconds,
            completed=payload.completed,
        )
        self._db.add(view)
        await self._db.flush()

    async def get_stats(self, session_id: uuid.UUID) -> ReplayStats:
        total_result = await self._db.execute(
            select(func.count()).where(ReplayView.session_id == session_id)
        )
        total = total_result.scalar_one()

        unique_result = await self._db.execute(
            select(func.count(ReplayView.learner_id.distinct())).where(ReplayView.session_id == session_id)
        )
        unique = unique_result.scalar_one()

        completed_result = await self._db.execute(
            select(func.count()).where(
                and_(ReplayView.session_id == session_id, ReplayView.completed == True)
            )
        )
        completed = completed_result.scalar_one()
        rate = (completed / total * 100) if total else 0.0

        return ReplayStats(
            session_id=session_id,
            total_views=total,
            unique_viewers=unique,
            completion_rate_pct=round(rate, 1),
        )
