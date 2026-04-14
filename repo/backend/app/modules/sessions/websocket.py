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
ROOM_MEMBERS_PREFIX = "ws:room:members:"


class RoomConnectionManager:
    """In-process WebSocket registry. All fanout goes through Redis pub/sub."""

    def __init__(self) -> None:
        # session_id → {user_id: websocket}
        self._rooms: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def connect(self, session_id: str, user_id: str, ws: WebSocket) -> None:
        # accept() is called by the endpoint before connect() — do not call it here.
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

    # ------------------------------------------------------------------
    # Cross-worker membership via Redis sets
    # ------------------------------------------------------------------

    async def add_member(self, session_id: str, user_id: str) -> None:
        """Register user in the Redis membership set (visible to all workers)."""
        from app.core.security import get_redis
        await get_redis().sadd(f"{ROOM_MEMBERS_PREFIX}{session_id}", user_id)

    async def remove_member(self, session_id: str, user_id: str) -> None:
        """Remove user from the Redis membership set."""
        from app.core.security import get_redis
        r = get_redis()
        await r.srem(f"{ROOM_MEMBERS_PREFIX}{session_id}", user_id)
        if await r.scard(f"{ROOM_MEMBERS_PREFIX}{session_id}") == 0:
            await r.delete(f"{ROOM_MEMBERS_PREFIX}{session_id}")

    async def get_peer_ids(self, session_id: str, exclude_user_id: str) -> list[str]:
        """Return all room members across all workers, excluding one user."""
        from app.core.security import get_redis
        members = await get_redis().smembers(f"{ROOM_MEMBERS_PREFIX}{session_id}")
        return [uid for uid in members if uid != exclude_user_id]

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
        logger.exception("Redis room subscriber crashed — will be restarted by the supervisor.")
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
    # Accept the HTTP→WebSocket upgrade immediately.  Close codes such as 4001
    # and 4003 are part of the WebSocket protocol and can only be sent after
    # the HTTP 101 handshake completes.  Calling close() before accept() causes
    # uvicorn to drop the TCP connection, which the browser reports as a generic
    # "WebSocket connection failed" error rather than a clean rejection.
    await websocket.accept()

    # Authenticate
    try:
        user = await get_ws_user(websocket, db)
    except Exception:
        return  # get_ws_user sends close(4001) on expected auth failures

    # Verify user has access to this specific session room
    from sqlalchemy import select, and_
    if user.role == "instructor":
        # Instructor must be assigned to the session
        from app.modules.instructors.models import Instructor
        from app.modules.sessions.models import Session as _Session
        instr_result = await db.execute(
            select(Instructor).where(Instructor.user_id == user.id)
        )
        instructor = instr_result.scalar_one_or_none()
        if instructor:
            sess_result = await db.execute(
                select(_Session).where(_Session.id == session_id)
            )
            sess = sess_result.scalar_one_or_none()
            if not sess or sess.instructor_id != instructor.id:
                await websocket.close(code=4003)
                return
        else:
            await websocket.close(code=4003)
            return
    elif user.role != "admin":
        # Learner (and any other role): require confirmed booking
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
    await room_manager.add_member(session_id, user_id)
    # Send current room state on join
    await room_manager.send_state_snapshot(websocket, session_id, db)
    # Notify others that a peer joined (via Redis → all workers)
    await room_manager.broadcast(session_id, {
        "type": "peer_joined", "user_id": user_id, "role": user.role,
    }, exclude_user_id=user_id)
    # Tell the joining user which peers are already in the room (cross-worker via Redis)
    peer_ids = await room_manager.get_peer_ids(session_id, user_id)
    await websocket.send_text(json.dumps({
        "type": "room_peers",
        "peers": [{"user_id": uid} for uid in peer_ids],
    }))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                msg_type = msg.get("type", "")
                if msg_type in ("webrtc_offer", "webrtc_answer", "webrtc_ice", "webrtc_request"):
                    msg["from_user_id"] = user_id
                    target = msg.get("target_user_id")
                    if target:
                        await room_manager.send_to_user(session_id, target, msg)
                    else:
                        await room_manager.broadcast(session_id, msg, exclude_user_id=user_id)
            except Exception:
                logger.exception("Error routing WS message session=%s user=%s", session_id, user_id)
    except WebSocketDisconnect:
        pass
    finally:
        room_manager.disconnect(session_id, user_id)
        await room_manager.remove_member(session_id, user_id)
        await room_manager.broadcast(session_id, {
            "type": "peer_left", "user_id": user_id, "role": user.role,
        })
