from datetime import UTC, datetime
import secrets

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.exceptions import UnauthorizedError
from app.modules.jobs.models import MonitoringAlert
from app.modules.jobs.schemas import AlertResponse

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/metrics")
async def metrics(_=Depends(require_roles("admin", "dataops"))):
    """Prometheus metrics endpoint — JWT-authenticated for Swagger/manual access."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/metrics/scrape")
async def metrics_scrape(authorization: str | None = Header(default=None)):
    """
    Dedicated Prometheus scrape endpoint authenticated by a static bearer token.
    Prometheus config: authorization: { credentials: "<PROMETHEUS_SCRAPE_TOKEN>" }
    This sends: Authorization: Bearer <token>
    """
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if not token or not secrets.compare_digest(token, settings.PROMETHEUS_SCRAPE_TOKEN):
        raise UnauthorizedError("Invalid or missing scrape token.")
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    resolved: bool = False,
    _=Depends(require_roles("admin", "dataops")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitoringAlert)
        .where(MonitoringAlert.is_resolved == resolved)
        .order_by(MonitoringAlert.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()


@router.patch("/alerts/{alert_id}/resolve", status_code=204)
async def resolve_alert(
    alert_id: str,
    _=Depends(require_roles("admin", "dataops")),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    result = await db.execute(select(MonitoringAlert).where(MonitoringAlert.id == uuid.UUID(alert_id)))
    alert = result.scalar_one_or_none()
    if alert:
        alert.is_resolved = True
        alert.resolved_at = datetime.now(UTC)
        await db.flush()
