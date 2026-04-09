import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.modules.locations.schemas import (
    LocationCreate, LocationResponse, LocationUpdate,
    RoomCreate, RoomResponse, RoomUpdate,
)
from app.modules.locations.service import LocationService

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("", response_model=list[LocationResponse])
async def list_locations(is_active: bool | None = None, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await LocationService(db).list(is_active)


@router.post("", response_model=LocationResponse, status_code=201)
async def create_location(body: LocationCreate, current_user=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return await LocationService(db).create(body, actor_id=str(current_user.id))


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(location_id: uuid.UUID, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await LocationService(db).get(location_id)


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(location_id: uuid.UUID, body: LocationUpdate, current_user=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return await LocationService(db).update(location_id, body, actor_id=str(current_user.id))


@router.delete("/{location_id}", status_code=204)
async def delete_location(location_id: uuid.UUID, current_user=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    await LocationService(db).delete(location_id, actor_id=str(current_user.id))


@router.get("/{location_id}/rooms", response_model=list[RoomResponse])
async def list_rooms(location_id: uuid.UUID, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await LocationService(db).list_rooms(location_id)


@router.post("/{location_id}/rooms", response_model=RoomResponse, status_code=201)
async def create_room(location_id: uuid.UUID, body: RoomCreate, current_user=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return await LocationService(db).create_room(location_id, body, actor_id=str(current_user.id))


# Room-level endpoints (separate prefix)
rooms_router = APIRouter(prefix="/rooms", tags=["Rooms"])


@rooms_router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: uuid.UUID, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await LocationService(db).get_room(room_id)


@rooms_router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(room_id: uuid.UUID, body: RoomUpdate, current_user=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return await LocationService(db).update_room(room_id, body, actor_id=str(current_user.id))


@rooms_router.delete("/{room_id}", status_code=204)
async def delete_room(room_id: uuid.UUID, current_user=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    await LocationService(db).delete_room(room_id, actor_id=str(current_user.id))
