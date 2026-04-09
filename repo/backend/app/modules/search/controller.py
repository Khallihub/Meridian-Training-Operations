import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.modules.search.schemas import (
    ExportRequest, SavedSearchCreate, SavedSearchResponse,
    SearchFilters, SearchResponse,
)
from app.modules.search.service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def search(
    body: SearchFilters,
    _=Depends(require_roles("admin", "instructor", "finance")),
    db: AsyncSession = Depends(get_db),
):
    return await SearchService(db).search(body)


@router.get("/saved", response_model=list[SavedSearchResponse])
async def list_saved(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await SearchService(db).list_saved_searches(current_user.id)


@router.post("/saved", response_model=SavedSearchResponse, status_code=201)
async def save_search(body: SavedSearchCreate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await SearchService(db).save_search(current_user.id, body)


@router.delete("/saved/{search_id}", status_code=204)
async def delete_saved(search_id: uuid.UUID, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await SearchService(db).delete_saved_search(search_id, current_user.id)


@router.post("/export")
async def export_search(
    body: ExportRequest,
    _=Depends(require_roles("admin", "instructor", "finance")),
    db: AsyncSession = Depends(get_db),
):
    data = await SearchService(db).export(body.filters, body.format)
    if body.format == "excel":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "search_export.xlsx"
    else:
        media_type = "text/csv"
        filename = "search_export.csv"

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
