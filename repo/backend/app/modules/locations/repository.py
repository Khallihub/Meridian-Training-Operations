from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.models import Location, Room


class LocationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, is_active: bool | None = None) -> list[Location]:
        q = select(Location)
        if is_active is not None:
            q = q.where(Location.is_active == is_active)
        result = await self._db.execute(q.order_by(Location.name))
        return result.scalars().all()

    async def get(self, location_id: uuid.UUID) -> Location | None:
        result = await self._db.execute(select(Location).where(Location.id == location_id))
        return result.scalar_one_or_none()

    async def create(self, location: Location) -> Location:
        self._db.add(location)
        await self._db.flush()
        await self._db.refresh(location)
        return location

    async def save(self, obj) -> None:
        await self._db.flush()

    async def list_rooms(self, location_id: uuid.UUID) -> list[Room]:
        result = await self._db.execute(select(Room).where(Room.location_id == location_id).order_by(Room.name))
        return result.scalars().all()

    async def get_room(self, room_id: uuid.UUID) -> Room | None:
        result = await self._db.execute(select(Room).where(Room.id == room_id))
        return result.scalar_one_or_none()

    async def create_room(self, room: Room) -> Room:
        self._db.add(room)
        await self._db.flush()
        await self._db.refresh(room)
        return room
