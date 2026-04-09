from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.modules.ingestion.schemas import (
    ConnectivityResult, IngestionRunResponse, IngestionSourceCreate,
    IngestionSourceResponse, IngestionSourceUpdate,
)
from app.modules.ingestion.service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.get("/sources", response_model=list[IngestionSourceResponse])
async def list_sources(_=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    return await IngestionService(db).list_sources()


@router.post("/sources", response_model=IngestionSourceResponse, status_code=201)
async def create_source(body: IngestionSourceCreate, _=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    return await IngestionService(db).create_source(body)


@router.get("/sources/{source_id}", response_model=IngestionSourceResponse)
async def get_source(source_id: uuid.UUID, _=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    return await IngestionService(db).get_source(source_id)


@router.patch("/sources/{source_id}", response_model=IngestionSourceResponse)
async def update_source(source_id: uuid.UUID, body: IngestionSourceUpdate, _=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    return await IngestionService(db).update_source(source_id, body)


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(source_id: uuid.UUID, _=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    await IngestionService(db).delete_source(source_id)


@router.post("/sources/{source_id}/test-connection", response_model=ConnectivityResult)
async def test_connection(source_id: uuid.UUID, _=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    return await IngestionService(db).test_connection(source_id)


@router.post("/sources/{source_id}/trigger", response_model=IngestionRunResponse)
async def trigger_run(source_id: uuid.UUID, _=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    return await IngestionService(db).trigger_run(source_id)


@router.get("/sources/{source_id}/runs", response_model=list[IngestionRunResponse])
async def list_runs(source_id: uuid.UUID, limit: int = Query(50, ge=1, le=500), _=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    return await IngestionService(db).list_runs(source_id, limit)


@router.get("/runs/{run_id}", response_model=IngestionRunResponse)
async def get_run(run_id: uuid.UUID, _=Depends(require_roles("admin", "dataops")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.modules.ingestion.models import IngestionRun
    from app.core.exceptions import NotFoundError
    result = await db.execute(select(IngestionRun).where(IngestionRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise NotFoundError("Ingestion run")
    return IngestionRunResponse.model_validate(run)


@router.post("/webhook/{source_id}", response_model=IngestionRunResponse)
async def webhook_ingest(
    source_id: uuid.UUID,
    payload: list[dict],
    x_api_key: str = Header(..., alias="X-Api-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Logstash/Flume HTTP push endpoint. Auth via X-Api-Key header matching source config."""
    return await IngestionService(db).handle_webhook(source_id, payload, x_api_key)
