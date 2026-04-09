from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import NotFoundError
from app.modules.locations.models import Location, Room
from app.modules.locations.repository import LocationRepository
from app.modules.locations.schemas import (
    LocationCreate, LocationResponse, LocationUpdate,
    RoomCreate, RoomResponse, RoomUpdate,
)


class LocationService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = LocationRepository(db)

    async def list(self, is_active: bool | None = None) -> list[LocationResponse]:
        locs = await self._repo.list(is_active)
        return [LocationResponse.model_validate(l) for l in locs]

    async def get(self, location_id: uuid.UUID) -> LocationResponse:
        loc = await self._repo.get(location_id)
        if not loc:
            raise NotFoundError("Location")
        return LocationResponse.model_validate(loc)

    async def create(self, payload: LocationCreate, actor_id: str | None = None) -> LocationResponse:
        loc = Location(**payload.model_dump())
        loc = await self._repo.create(loc)
        await log_audit(self._repo._db, actor_id or "", "location", str(loc.id), "create")
        return LocationResponse.model_validate(loc)

    async def update(self, location_id: uuid.UUID, payload: LocationUpdate, actor_id: str | None = None) -> LocationResponse:
        loc = await self._repo.get(location_id)
        if not loc:
            raise NotFoundError("Location")
        changes = payload.model_dump(exclude_none=True)
        for k, v in changes.items():
            setattr(loc, k, v)
        await self._repo.save(loc)
        await log_audit(self._repo._db, actor_id or "", "location", str(location_id), "update", new_value=changes)
        return LocationResponse.model_validate(loc)

    async def delete(self, location_id: uuid.UUID, actor_id: str | None = None) -> None:
        loc = await self._repo.get(location_id)
        if not loc:
            raise NotFoundError("Location")
        loc.is_active = False
        await self._repo.save(loc)
        await log_audit(self._repo._db, actor_id or "", "location", str(location_id), "delete")

    async def list_rooms(self, location_id: uuid.UUID) -> list[RoomResponse]:
        rooms = await self._repo.list_rooms(location_id)
        return [RoomResponse.model_validate(r) for r in rooms]

    async def create_room(self, location_id: uuid.UUID, payload: RoomCreate, actor_id: str | None = None) -> RoomResponse:
        loc = await self._repo.get(location_id)
        if not loc:
            raise NotFoundError("Location")
        room = Room(location_id=location_id, **payload.model_dump())
        room = await self._repo.create_room(room)
        await log_audit(self._repo._db, actor_id or "", "room", str(room.id), "create")
        return RoomResponse.model_validate(room)

    async def get_room(self, room_id: uuid.UUID) -> RoomResponse:
        room = await self._repo.get_room(room_id)
        if not room:
            raise NotFoundError("Room")
        return RoomResponse.model_validate(room)

    async def update_room(self, room_id: uuid.UUID, payload: RoomUpdate, actor_id: str | None = None) -> RoomResponse:
        room = await self._repo.get_room(room_id)
        if not room:
            raise NotFoundError("Room")
        changes = payload.model_dump(exclude_none=True)
        for k, v in changes.items():
            setattr(room, k, v)
        await self._repo.save(room)
        await log_audit(self._repo._db, actor_id or "", "room", str(room_id), "update", new_value=changes)
        return RoomResponse.model_validate(room)

    async def delete_room(self, room_id: uuid.UUID, actor_id: str | None = None) -> None:
        room = await self._repo.get_room(room_id)
        if not room:
            raise NotFoundError("Room")
        room.is_active = False
        await self._repo.save(room)
        await log_audit(self._repo._db, actor_id or "", "room", str(room_id), "delete")
