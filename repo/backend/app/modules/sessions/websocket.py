"""WebSocket live-room manager and endpoint.

Multi-worker safe: local connections are managed in-process, but all broadcast
and targeted sends are routed through a Redis pub/sub channel so that clients
connected to different uvicorn workers receive events consistently.

Channel naming: ws:room:{session_id}
Message envelope: {"msg": {...}, "exclude": user_id | null, "target": user_id | null}
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_ws_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Live Room WebSocket"])

ROOM_CHANNEL_PREFIX = "ws:room:"


class RoomConnectionManager:
    """In-process WebSocket registry. All fanout goes through Redis pub/sub."""

    def __init__(self) -> None:
        # session_id → {user_id: websocket}
        self._rooms: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def connect(self, session_id: str, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms[session_id][user_id] = ws
        logger.debug("WS connected: session=%s user=%s total=%d", session_id, user_id, len(self._rooms[session_id]))

    def disconnect(self, session_id: str, user_id: str) -> None:
        self._rooms[session_id].pop(user_id, None)
        if not self._rooms[session_id]:
            self._rooms.pop(session_id, None)

    # ------------------------------------------------------------------
    # Publishing (routes through Redis → all workers deliver locally)
    # ------------------------------------------------------------------

    async def broadcast(self, session_id: str, message: dict, exclude_user_id: str | None = None) -> None:
        """Broadcast to all room members via Redis pub/sub (multi-worker safe)."""
        from app.core.security import get_redis
        payload = json.dumps({"msg": message, "exclude": exclude_user_id})
        await get_redis().publish(f"{ROOM_CHANNEL_PREFIX}{session_id}", payload)

    async def send_to_user(self, session_id: str, user_id: str, message: dict) -> None:
        """Send to one specific user via Redis pub/sub (multi-worker safe)."""
        from app.core.security import get_redis
        payload = json.dumps({"msg": message, "target": user_id})
        await get_redis().publish(f"{ROOM_CHANNEL_PREFIX}{session_id}", payload)

    # ------------------------------------------------------------------
    # Local delivery (called by the Redis subscriber task)
    # ------------------------------------------------------------------

    async def deliver_local(self, session_id: str, message: dict, exclude_user_id: str | None = None) -> None:
        dead: list[str] = []
        for uid, ws in list(self._rooms.get(session_id, {}).items()):
            if uid == exclude_user_id:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(session_id, uid)

    async def deliver_local_to_user(self, session_id: str, user_id: str, message: dict) -> None:
        ws = self._rooms.get(session_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                self.disconnect(session_id, user_id)

    def peer_ids(self, session_id: str, exclude_user_id: str) -> list[str]:
        return [uid for uid in self._rooms.get(session_id, {}) if uid != exclude_user_id]

    async def send_state_snapshot(self, ws: WebSocket, session_id: str, db: AsyncSession) -> None:
        from sqlalchemy import func, select
        from app.modules.sessions.models import Session
        from app.modules.attendance.models import AttendanceRecord

        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            checked_in_result = await db.execute(
                select(func.count()).select_from(AttendanceRecord).where(
                    AttendanceRecord.session_id == session.id,
                    AttendanceRecord.joined_at.isnot(None),
                    AttendanceRecord.left_at.is_(None),
                )
            )
            snapshot = {
                "type": "room_state",
                "session_status": session.status,
                "enrolled_count": session.enrolled_count,
                "checked_in_count": checked_in_result.scalar_one(),
            }
            await ws.send_text(json.dumps(snapshot))


room_manager = RoomConnectionManager()


async def redis_room_subscriber() -> None:
    """
    Background task: subscribes to all ws:room:* Redis channels and delivers
    messages to locally-connected WebSocket clients in this worker process.
    Must be started once per worker process at app startup.
    """
    from app.core.config import settings

    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.psubscribe(f"{ROOM_CHANNEL_PREFIX}*")
    logger.info("Redis room subscriber started (pattern=%s*)", ROOM_CHANNEL_PREFIX)

    try:
        async for raw in pubsub.listen():
            if raw["type"] != "pmessage":
                continue
            channel: str = raw["channel"]
            session_id = channel[len(ROOM_CHANNEL_PREFIX):]
            try:
                envelope = json.loads(raw["data"])
            except Exception:
                continue

            msg = envelope.get("msg", {})
            target: str | None = envelope.get("target")
            exclude: str | None = envelope.get("exclude")

            if target:
                await room_manager.deliver_local_to_user(session_id, target, msg)
            else:
                await room_manager.deliver_local(session_id, msg, exclude_user_id=exclude)

    except asyncio.CancelledError:
        await pubsub.punsubscribe()
        await redis.aclose()
        raise
    except Exception:
        logger.exception("Redis room subscriber crashed; room events may be lost.")
        await redis.aclose()


@router.websocket("/api/ws/sessions/{session_id}/room")
async def session_room_ws(
    session_id: str,
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for live session room.
    Authenticate via ?token=<access_jwt>.
    """
    # Authenticate
    try:
        user = await get_ws_user(websocket, db)
    except Exception:
        return  # get_ws_user closes the socket

    # Verify user has access (confirmed booking, or admin/instructor)
    if user.role not in ("admin", "instructor"):
        from sqlalchemy import select, and_
        from app.modules.bookings.models import Booking, BookingStatus
        result = await db.execute(
            select(Booking).where(
                and_(
                    Booking.session_id == session_id,
                    Booking.learner_id == user.id,
                    Booking.status == BookingStatus.confirmed,
                )
            )
        )
        if not result.scalar_one_or_none():
            await websocket.close(code=4003)
            return

    user_id = str(user.id)
    await room_manager.connect(session_id, user_id, websocket)
    # Send current room state on join
    await room_manager.send_state_snapshot(websocket, session_id, db)
    # Notify others that a peer joined (via Redis → all workers)
    await room_manager.broadcast(session_id, {
        "type": "peer_joined", "user_id": user_id, "role": user.role,
    }, exclude_user_id=user_id)
    # Tell the joining user which peers are already in the room (local only — best effort)
    await websocket.send_text(json.dumps({
        "type": "room_peers",
        "peers": [{"user_id": uid} for uid in room_manager.peer_ids(session_id, user_id)],
    }))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                msg_type = msg.get("type", "")
                if msg_type in ("webrtc_offer", "webrtc_answer", "webrtc_ice"):
                    msg["from_user_id"] = user_id
                    target = msg.get("target_user_id")
                    if target:
                        await room_manager.send_to_user(session_id, target, msg)
                    else:
                        await room_manager.broadcast(session_id, msg, exclude_user_id=user_id)
            except Exception:
                pass
    except WebSocketDisconnect:
        room_manager.disconnect(session_id, user_id)
        await room_manager.broadcast(session_id, {
            "type": "peer_left", "user_id": user_id, "role": user.role,
        })
