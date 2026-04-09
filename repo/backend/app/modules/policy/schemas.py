from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, Field


class AdminPolicyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID | None = None
    reschedule_cutoff_hours: int = Field(2, ge=0, le=168)
    cancellation_fee_hours: int = Field(24, ge=0, le=168)
    updated_at: datetime | None = None
    updated_by: uuid.UUID | None = None


class AdminPolicyUpdate(BaseModel):
    reschedule_cutoff_hours: int | None = Field(None, ge=0, le=168)
    cancellation_fee_hours: int | None = Field(None, ge=0, le=168)
