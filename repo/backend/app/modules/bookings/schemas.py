import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator

from app.modules.bookings.models import BookingStatus


class BookingCreate(BaseModel):
    session_id: uuid.UUID


class RescheduleRequest(BaseModel):
    new_session_id: uuid.UUID


class CancelRequest(BaseModel):
    reason: str | None = None


class BookingResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    learner_id: uuid.UUID
    status: BookingStatus
    rescheduled_from_id: uuid.UUID | None
    policy_fee_flagged: bool
    cancellation_reason: str | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    # Denormalised from relationships
    session_title: str | None = None
    session_start_time: datetime | None = None
    learner_username: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_relations(cls, v):
        if not hasattr(v, "__dict__"):
            return v
        session = getattr(v, "session", None)
        if session:
            v.__dict__.setdefault("session_title", getattr(session, "title", None))
            v.__dict__.setdefault("session_start_time", getattr(session, "start_time", None))
        learner = getattr(v, "learner", None)
        if learner:
            v.__dict__.setdefault("learner_username", getattr(learner, "username", None))
        return v
