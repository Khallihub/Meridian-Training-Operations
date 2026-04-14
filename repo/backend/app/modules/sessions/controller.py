import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.modules.sessions.schemas import (
    RecurringSessionCreate, SessionCreate, SessionResponse, SessionUpdate,
)
from app.modules.sessions.service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=list[SessionResponse])
async def list_weekly(
    week: str = Query(..., example="2026-W14"),
    tz: str = Query("UTC"),
    location_id: Optional[uuid.UUID] = None,
    instructor_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await SessionService(db).list_weekly(week, tz, location_id, instructor_id)


@router.get("/monthly", response_model=list[SessionResponse])
async def list_monthly(
    month: str = Query(..., example="2026-04"),
    tz: str = Query("UTC"),
    location_id: Optional[uuid.UUID] = None,
    instructor_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await SessionService(db).list_monthly(month, tz, location_id, instructor_id)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await SessionService(db).create(body, current_user.id)


@router.post("/recurring", response_model=list[SessionResponse], status_code=201)
async def create_recurring(
    body: RecurringSessionCreate,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await SessionService(db).create_recurring(body, current_user.id)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await SessionService(db).get(session_id)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await SessionService(db).update(session_id, body, str(current_user.id), current_user.role)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    await SessionService(db).delete(session_id, str(current_user.id))


@router.patch("/{session_id}/cancel", response_model=SessionResponse)
async def cancel_session(
    session_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await SessionService(db).cancel(session_id, str(current_user.id), current_user.role)


@router.post("/{session_id}/go-live", response_model=SessionResponse)
async def go_live(
    session_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await SessionService(db).go_live(session_id, str(current_user.id), current_user.role)


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await SessionService(db).end(session_id, str(current_user.id), current_user.role)


@router.post("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    """Alias for /end — kept for backwards compatibility."""
    return await SessionService(db).end(session_id, str(current_user.id), current_user.role)


@router.get("/{session_id}/roster")
async def get_roster(
    session_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    learners = await SessionService(db).get_roster(session_id, str(current_user.id), current_user.role)
    return learners  # already a list of dicts from get_enrolled_learners()
