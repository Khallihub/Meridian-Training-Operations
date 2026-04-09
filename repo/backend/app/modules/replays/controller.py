import uuid

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import decode_token, is_token_blocklisted
from app.core.storage import get_object_chunks, stat_object
from app.modules.replays.models import RecordingUploadStatus, SessionRecording
from app.modules.replays.schemas import (
    ReplayAccessRuleCreate, ReplayAccessRuleResponse, ReplayStats,
    ReplayViewCreate, RecordingResponse,
)
from app.modules.replays.service import ReplayService

router = APIRouter(tags=["Replays"])


async def _resolve_stream_user(token: str, db: AsyncSession):
    """Resolve a user from a ?token= query param (used for video streaming)."""
    from app.core.security import is_inactive, touch_last_seen
    from app.modules.users.repository import UserRepository
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("Invalid token.")
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type.")
    if await is_token_blocklisted(token):
        raise UnauthorizedError("Token has been revoked.")
    user_id: str = payload.get("sub")
    if not user_id:
        raise UnauthorizedError()
    if await is_inactive(user_id):
        raise UnauthorizedError("Session expired due to inactivity.")
    user = await UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    await touch_last_seen(user_id)
    return user


@router.get("/sessions/{session_id}/recordings", response_model=list[RecordingResponse])
async def list_recordings(
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all ready recordings for a session (newest first)."""
    return await ReplayService(db).get_all_recordings(session_id, current_user.id, current_user.role)


@router.get("/sessions/{session_id}/recordings/{recording_id}/stream")
async def stream_recording(
    session_id: uuid.UUID,
    recording_id: uuid.UUID,
    request: Request,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream a recording directly from MinIO through the backend.
    Accepts the JWT as ?token= so it can be used as a plain <video src=>.
    Supports HTTP Range requests for video seeking.
    """
    user = await _resolve_stream_user(token, db)
    await ReplayService(db)._check_access(session_id, user.id, user.role)

    result = await db.execute(
        select(SessionRecording).where(
            and_(
                SessionRecording.id == recording_id,
                SessionRecording.session_id == session_id,
                SessionRecording.upload_status == RecordingUploadStatus.ready,
            )
        )
    )
    recording = result.scalar_one_or_none()
    if not recording:
        raise NotFoundError("Recording")

    stat = stat_object(recording.bucket_name, recording.object_storage_key)
    total_size = stat.size
    content_type = recording.mime_type or stat.content_type or "video/webm"

    range_header = request.headers.get("Range")
    if range_header:
        # Parse "bytes=start-end"
        range_val = range_header.strip().replace("bytes=", "")
        start_str, _, end_str = range_val.partition("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else total_size - 1
        end = min(end, total_size - 1)
        length = end - start + 1
        return StreamingResponse(
            get_object_chunks(recording.bucket_name, recording.object_storage_key, offset=start, length=length),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{total_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            },
        )

    return StreamingResponse(
        get_object_chunks(recording.bucket_name, recording.object_storage_key),
        status_code=200,
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(total_size),
        },
    )


@router.get("/sessions/{session_id}/replay", response_model=RecordingResponse)
async def get_replay(
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReplayService(db).get_replay(session_id, current_user.id, current_user.role)


@router.post("/sessions/{session_id}/replay/upload")
async def initiate_upload(
    session_id: uuid.UUID,
    _=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    """Get a presigned PUT URL to upload a recording to MinIO."""
    return await ReplayService(db).initiate_upload(session_id)


@router.patch("/sessions/{session_id}/replay/recording", response_model=RecordingResponse)
async def confirm_upload(
    session_id: uuid.UUID,
    file_size_bytes: int | None = None,
    duration_seconds: int | None = None,
    _=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await ReplayService(db).confirm_upload(session_id, file_size_bytes, duration_seconds)


@router.post("/sessions/{session_id}/replay/recording/data", response_model=RecordingResponse)
async def upload_recording_direct(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    duration_seconds: int = Form(0),
    _=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    """Direct upload endpoint — browser POSTs multipart to backend, backend writes to MinIO."""
    data = await file.read()
    content_type = file.content_type or "video/webm"
    return await ReplayService(db).store_recording_direct(
        session_id, data, len(data), duration_seconds, content_type
    )


@router.post("/sessions/{session_id}/replay/access-rule", response_model=ReplayAccessRuleResponse)
async def set_access_rule(
    session_id: uuid.UUID,
    body: ReplayAccessRuleCreate,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await ReplayService(db).set_access_rule(session_id, body, actor_id=str(current_user.id))


@router.post("/replays/{session_id}/view", status_code=204)
async def record_view(
    session_id: uuid.UUID,
    body: ReplayViewCreate,
    current_user=Depends(require_roles("learner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    await ReplayService(db).record_view(session_id, current_user.id, body, user_role=current_user.role)


@router.get("/replays/{session_id}/stats", response_model=ReplayStats)
async def get_replay_stats(
    session_id: uuid.UUID,
    _=Depends(require_roles("admin", "instructor")),
    db: AsyncSession = Depends(get_db),
):
    return await ReplayService(db).get_stats(session_id)
