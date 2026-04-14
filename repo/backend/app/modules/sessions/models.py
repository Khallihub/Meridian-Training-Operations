import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    live = "live"
    ended = "ended"
    recording_processing = "recording_processing"
    recording_published = "recording_published"
    closed_no_recording = "closed_no_recording"
    canceled = "canceled"
    archived = "archived"


class RecurrenceRule(Base):
    __tablename__ = "recurrence_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rrule_string: Mapped[str] = mapped_column(String(500), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    instructor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instructors.id"), nullable=False, index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), nullable=False, default=SessionStatus.scheduled, index=True)
    recurrence_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("recurrence_rules.id"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    course: Mapped["app.modules.courses.models.Course"] = relationship("Course")
    instructor: Mapped["app.modules.instructors.models.Instructor"] = relationship("Instructor")
    room: Mapped["app.modules.locations.models.Room"] = relationship("Room")
    recurrence_rule: Mapped[RecurrenceRule | None] = relationship("RecurrenceRule")

    @property
    def course_title(self) -> str | None:
        return self.course.title if self.course else None

    @property
    def instructor_name(self) -> str | None:
        if self.instructor and self.instructor.user:
            return self.instructor.user.username
        return None

    @property
    def room_name(self) -> str | None:
        return self.room.name if self.room else None

    @property
    def location_name(self) -> str | None:
        if self.room and self.room.location:
            return self.room.location.name
        return None

    @property
    def location_id(self) -> uuid.UUID | None:
        return self.room.location_id if self.room else None
