import uuid
from datetime import datetime

from pydantic import BaseModel


class LocationCreate(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "UTC"


class LocationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None
    is_active: bool | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    timezone: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomCreate(BaseModel):
    name: str
    capacity: int = 20


class RoomUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None
    is_active: bool | None = None


class RoomResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    name: str
    capacity: int
    is_active: bool

    model_config = {"from_attributes": True}
