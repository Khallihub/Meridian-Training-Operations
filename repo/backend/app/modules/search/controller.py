import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.modules.search.schemas import (
    ExportRequest, SavedSearchCreate, SavedSearchResponse,
    SearchExportJobResponse, SearchFilters, SearchResponse,
)
from app.modules.search.service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def search(
    body: SearchFilters,
    current_user=Depends(require_roles("admin", "instructor", "finance")),
    db: AsyncSession = Depends(get_db),
):
    return await SearchService(db).search(
        body,
        caller_role=current_user.role,
        caller_id=current_user.id,
    )


@router.get("/saved", response_model=list[SavedSearchResponse])
async def list_saved(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await SearchService(db).list_saved_searches(current_user.id)


@router.post("/saved", response_model=SavedSearchResponse, status_code=201)
async def save_search(body: SavedSearchCreate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await SearchService(db).save_search(current_user.id, body)


@router.delete("/saved/{search_id}", status_code=204)
async def delete_saved(search_id: uuid.UUID, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await SearchService(db).delete_saved_search(search_id, current_user.id)


@router.post("/export/jobs", response_model=SearchExportJobResponse, status_code=202)
async def create_export_job(
    body: ExportRequest,
    current_user=Depends(require_roles("admin", "instructor", "finance")),
    db: AsyncSession = Depends(get_db),
):
    """Queue an async search export job.

    Returns a ``SearchExportJobResponse`` with ``status="queued"``.
    Poll ``GET /search/export/jobs/{id}`` until ``status="completed"``, then
    download via ``GET /search/export/jobs/{id}/download``.
    """
    svc = SearchService(db)
    job = await svc.create_export_job(
        filters=body.filters,
        fmt=body.format,
        caller_role=current_user.role,
        caller_id=current_user.id,
        created_by=current_user.id,
    )
    # Enqueue after flush so job.id is stable
    from app.modules.jobs.tasks import run_search_export
    run_search_export.delay(str(job.id))
    return job


@router.get("/export/jobs/{job_id}", response_model=SearchExportJobResponse)
async def get_export_job(
    job_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "instructor", "finance")),
    db: AsyncSession = Depends(get_db),
):
    """Poll the status of a previously queued export job."""
    return await SearchService(db).get_export_job(
        job_id, caller_id=current_user.id, caller_role=current_user.role
    )


@router.get("/export/jobs/{job_id}/download")
async def download_export(
    job_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "instructor", "finance")),
    db: AsyncSession = Depends(get_db),
):
    """Download the completed export file.  Returns 409 if the job is not yet complete."""
    from app.modules.search.models import SearchExportJobStatus
    job_resp = await SearchService(db).get_export_job(
        job_id, caller_id=current_user.id, caller_role=current_user.role
    )
    if job_resp.status != SearchExportJobStatus.completed:
        raise HTTPException(status_code=409, detail=f"Export job is not complete (status: {job_resp.status}).")
    if not job_resp.file_path:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Export file path missing.")

    # Re-fetch the raw model to get file_path (not exposed in response schema)
    from sqlalchemy import select as _select
    from app.modules.search.models import SearchExportJob
    result = await db.execute(_select(SearchExportJob).where(SearchExportJob.id == job_id))
    job = result.scalar_one()

    fmt = job.format
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if fmt == "excel" else "text/csv"
    )
    filename = f"search_export_{job_id}.{'xlsx' if fmt == 'excel' else 'csv'}"
    return FileResponse(job.file_path, media_type=media_type, filename=filename)
