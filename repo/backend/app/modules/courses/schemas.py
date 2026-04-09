import uuid
from datetime import datetime

from pydantic import BaseModel


class CourseCreate(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int = 60
    category: str | None = None
    price: float = 0.0


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    category: str | None = None
    price: float | None = None
    is_active: bool | None = None


class CourseResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    duration_minutes: int
    category: str | None
    price: float
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
