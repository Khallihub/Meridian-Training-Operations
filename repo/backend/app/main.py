import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import CorrelationIdMiddleware, configure_logging

configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        import asyncio
        os.makedirs(settings.EXPORTS_DIR, exist_ok=True)
        os.makedirs(settings.UPLOADS_DIR, exist_ok=True)

        from app.modules.sessions.websocket import redis_room_subscriber

        async def _supervised_subscriber() -> None:
            """Restart the Redis room subscriber if it crashes."""
            while True:
                try:
                    await redis_room_subscriber()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Room subscriber exited unexpectedly; restarting in 2 s")
                    await asyncio.sleep(2)

        # Store reference on the app to prevent garbage collection.
        # asyncio only keeps a weak reference to tasks — without a strong
        # reference the subscriber can be GC'd, silently killing all Redis
        # pub/sub delivery (peer_joined, webrtc_offer, webrtc_ice, …).
        task = asyncio.create_task(_supervised_subscriber())
        logger.info("Meridian backend started (subscriber task scheduled).")
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app = FastAPI(
        title="Meridian Training Operations API",
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # Correlation ID — must be added before CORS so every request gets an ID
    app.add_middleware(CorrelationIdMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handlers
    register_exception_handlers(app)

    # Register all routers
    _register_routers(app)

    return app


def _register_routers(app: FastAPI) -> None:
    from app.modules.auth.controller import router as auth_router
    from app.modules.users.controller import router as users_router
    from app.modules.locations.controller import router as locations_router, rooms_router
    from app.modules.courses.controller import router as courses_router
    from app.modules.instructors.controller import router as instructors_router
    from app.modules.sessions.controller import router as sessions_router
    from app.modules.sessions.websocket import router as ws_router
    from app.modules.bookings.controller import router as bookings_router
    from app.modules.attendance.controller import router as attendance_router
    from app.modules.replays.controller import router as replays_router
    from app.modules.promotions.controller import router as promotions_router
    from app.modules.checkout.controller import router as checkout_router
    from app.modules.payments.controller import router as payments_router
    from app.modules.search.controller import router as search_router
    from app.modules.ingestion.controller import router as ingestion_router
    from app.modules.jobs.controller import router as jobs_router
    from app.modules.monitoring.controller import router as monitoring_router
    from app.modules.audit.controller import router as audit_router
    from app.modules.policy.controller import router as policy_router

    prefix = "/api/v1"
    app.include_router(auth_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    app.include_router(locations_router, prefix=prefix)
    app.include_router(rooms_router, prefix=prefix)
    app.include_router(courses_router, prefix=prefix)
    app.include_router(instructors_router, prefix=prefix)
    app.include_router(sessions_router, prefix=prefix)
    app.include_router(ws_router)            # WebSocket — no /api/v1 prefix
    app.include_router(bookings_router, prefix=prefix)
    app.include_router(attendance_router, prefix=prefix)
    app.include_router(replays_router, prefix=prefix)
    app.include_router(promotions_router, prefix=prefix)
    app.include_router(checkout_router, prefix=prefix)
    app.include_router(payments_router, prefix=prefix)
    app.include_router(search_router, prefix=prefix)
    app.include_router(ingestion_router, prefix=prefix)
    app.include_router(jobs_router, prefix=prefix)
    app.include_router(monitoring_router, prefix=prefix)
    app.include_router(audit_router, prefix=prefix)
    app.include_router(policy_router, prefix=prefix)


app = create_app()
