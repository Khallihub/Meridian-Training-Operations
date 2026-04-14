from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DateRange(BaseModel):
    from_: datetime | None = None
    to: datetime | None = None


class SearchFilters(BaseModel):
    invoice_number: str | None = None      # order id substring
    learner_phone: str | None = None       # matched after decryption
    enrollment_status: str | None = None   # booking status
    date_range: DateRange | None = None
    date_from: datetime | None = None      # flat alternative to date_range
    date_to: datetime | None = None        # flat alternative to date_range
    site_id: uuid.UUID | None = None
    instructor_id: uuid.UUID | None = None
    learner_id: uuid.UUID | None = None
    page: int = 1
    page_size: int = 50
    include_facets: bool = False


class FacetCount(BaseModel):
    id: str
    name: str
    count: int


class SearchFacets(BaseModel):
    enrollment_status: dict[str, int] = {}
    site: list[FacetCount] = []
    instructor: list[FacetCount] = []


class SearchResultItem(BaseModel):
    booking_id: uuid.UUID
    session_id: uuid.UUID
    learner_id: uuid.UUID
    learner_username: str
    learner_phone_masked: str | None
    status: str
    session_date: datetime
    session_title: str
    instructor_name: str
    site_name: str
    order_id: uuid.UUID | None
    amount: float | None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    query_time_ms: float
    facets: SearchFacets | None = None


class SavedSearchCreate(BaseModel):
    name: str
    filters: dict


class SavedSearchResponse(BaseModel):
    id: uuid.UUID
    name: str
    filters_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ExportRequest(BaseModel):
    filters: SearchFilters
    format: Literal["csv", "excel"] = "csv"


class SearchExportJobResponse(BaseModel):
    id: uuid.UUID
    status: str
    format: str
    row_count: int | None = None
    error_detail: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
