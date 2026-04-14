import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.sessions.models import SessionStatus


class RecurrenceRuleCreate(BaseModel):
    rrule_string: str
    start_date: datetime
    end_date: datetime | None = None


class SessionCreate(BaseModel):
    title: str
    course_id: uuid.UUID
    instructor_id: uuid.UUID
    room_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    capacity: int = Field(default=20, ge=1)
    buffer_minutes: int = Field(default=10, ge=0)

    @model_validator(mode="after")
    def _end_after_start(self) -> "SessionCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class RecurringSessionCreate(BaseModel):
    title: str
    course_id: uuid.UUID
    instructor_id: uuid.UUID
    room_id: uuid.UUID
    capacity: int = Field(default=20, ge=1)
    buffer_minutes: int = Field(default=10, ge=0)
    recurrence: RecurrenceRuleCreate


class SessionUpdate(BaseModel):
    title: str | None = None
    course_id: uuid.UUID | None = None
    instructor_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    capacity: int | None = Field(default=None, ge=1)
    buffer_minutes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _end_after_start(self) -> "SessionUpdate":
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    course_id: uuid.UUID
    instructor_id: uuid.UUID
    room_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    capacity: int
    enrolled_count: int
    buffer_minutes: int
    status: SessionStatus
    recurrence_rule_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime

    # Denormalised from relationships (populated when joins are loaded)
    course_title: str | None = None
    instructor_name: str | None = None
    room_name: str | None = None
    location_name: str | None = None
    location_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}
