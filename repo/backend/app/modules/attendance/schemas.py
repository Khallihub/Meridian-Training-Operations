import uuid
from datetime import datetime

from pydantic import BaseModel


class CheckInRequest(BaseModel):
    learner_id: uuid.UUID


class CheckOutRequest(BaseModel):
    learner_id: uuid.UUID


class AttendanceRecordResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    learner_id: uuid.UUID
    joined_at: datetime | None
    left_at: datetime | None
    minutes_attended: int
    was_late: bool

    model_config = {"from_attributes": True}


class AttendanceStats(BaseModel):
    session_id: uuid.UUID
    total_enrolled: int
    checked_in: int
    late_joins: int
    avg_minutes_attended: float
    replay_completion_rate: float
