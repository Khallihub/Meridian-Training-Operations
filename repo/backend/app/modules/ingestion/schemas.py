import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.ingestion.models import IngestionRunStatus, IngestionSourceType


class IngestionSourceCreate(BaseModel):
    name: str
    type: IngestionSourceType
    config: dict = {}     # plaintext; encrypted before storage
    collection_frequency_seconds: int = 300
    concurrency_cap: int = 10


class IngestionSourceUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    collection_frequency_seconds: int | None = None
    concurrency_cap: int | None = None
    is_active: bool | None = None


class IngestionSourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: IngestionSourceType
    collection_frequency_seconds: int
    concurrency_cap: int
    is_active: bool
    last_run_at: datetime | None
    last_status: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestionRunResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    rows_ingested: int
    status: IngestionRunStatus
    error_detail: str | None

    model_config = {"from_attributes": True}


class ConnectivityResult(BaseModel):
    success: bool
    latency_ms: float | None
    error: str | None
