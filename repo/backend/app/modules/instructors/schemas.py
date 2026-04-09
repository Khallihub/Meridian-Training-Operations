import uuid
from datetime import datetime

from pydantic import BaseModel


class InstructorCreate(BaseModel):
    user_id: uuid.UUID
    bio: str | None = None


class InstructorUpdate(BaseModel):
    bio: str | None = None
    is_active: bool | None = None


class InstructorResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    bio: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
