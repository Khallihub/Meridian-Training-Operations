import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.modules.attendance.schemas import (
    AttendanceRecordResponse, AttendanceStats, CheckInRequest, CheckOutRequest,
)
from app.modules.attendance.service import AttendanceService

router = APIRouter(prefix="/sessions", tags=["Attendance"])


@router.post("/{session_id}/attendance/checkin", response_model=AttendanceRecordResponse)
async def checkin(
    session_id: uuid.UUID,
    body: CheckInRequest,
    _=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await AttendanceService(db).checkin(session_id, body)


@router.post("/{session_id}/attendance/checkout", response_model=AttendanceRecordResponse)
async def checkout(
    session_id: uuid.UUID,
    body: CheckOutRequest,
    _=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await AttendanceService(db).checkout(session_id, body)


@router.get("/{session_id}/attendance/stats", response_model=AttendanceStats)
async def get_stats(
    session_id: uuid.UUID,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await AttendanceService(db).get_stats(session_id)
