import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.replays.models import RecordingUploadStatus, ReplayRuleType


class ReplayAccessRuleCreate(BaseModel):
    rule_type: ReplayRuleType = ReplayRuleType.enrolled_only
    available_from: datetime | None = None
    available_until: datetime | None = None


class ReplayAccessRuleResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    rule_type: ReplayRuleType
    available_from: datetime | None
    available_until: datetime | None
    is_active: bool

    model_config = {"from_attributes": True}


class RecordingResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    file_size_bytes: int | None
    duration_seconds: int | None
    mime_type: str
    upload_status: RecordingUploadStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ReplayViewCreate(BaseModel):
    watched_seconds: int = 0
    completed: bool = False


class ReplayStats(BaseModel):
    session_id: uuid.UUID
    total_views: int
    unique_viewers: int
    completion_rate_pct: float
