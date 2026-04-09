from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_field, encrypt_field
from app.core.exceptions import NotFoundError
from app.modules.ingestion.models import (
    IngestionRun, IngestionRunStatus, IngestionSource, IngestionSourceType,
)
from app.modules.ingestion.schemas import (
    ConnectivityResult, IngestionRunResponse, IngestionSourceCreate,
    IngestionSourceResponse, IngestionSourceUpdate,
)


class IngestionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_sources(self) -> list[IngestionSourceResponse]:
        result = await self._db.execute(select(IngestionSource).order_by(IngestionSource.name))
        return [IngestionSourceResponse.model_validate(s) for s in result.scalars().all()]

    async def get_source(self, source_id: uuid.UUID) -> IngestionSourceResponse:
        result = await self._db.execute(select(IngestionSource).where(IngestionSource.id == source_id))
        s = result.scalar_one_or_none()
        if not s:
            raise NotFoundError("Ingestion source")
        return IngestionSourceResponse.model_validate(s)

    async def create_source(self, payload: IngestionSourceCreate) -> IngestionSourceResponse:
        encrypted_config = encrypt_field(json.dumps(payload.config))
        source = IngestionSource(
            name=payload.name,
            type=payload.type,
            config_encrypted=encrypted_config,
            collection_frequency_seconds=payload.collection_frequency_seconds,
            concurrency_cap=payload.concurrency_cap,
        )
        self._db.add(source)
        await self._db.flush()
        await self._db.refresh(source)
        return IngestionSourceResponse.model_validate(source)

    async def update_source(self, source_id: uuid.UUID, payload: IngestionSourceUpdate) -> IngestionSourceResponse:
        result = await self._db.execute(select(IngestionSource).where(IngestionSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("Ingestion source")
        if payload.config is not None:
            source.config_encrypted = encrypt_field(json.dumps(payload.config))
        for k, v in payload.model_dump(exclude_none=True, exclude={"config"}).items():
            setattr(source, k, v)
        await self._db.flush()
        return IngestionSourceResponse.model_validate(source)

    async def delete_source(self, source_id: uuid.UUID) -> None:
        result = await self._db.execute(select(IngestionSource).where(IngestionSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("Ingestion source")
        source.is_active = False
        await self._db.flush()

    async def test_connection(self, source_id: uuid.UUID) -> ConnectivityResult:
        result = await self._db.execute(select(IngestionSource).where(IngestionSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("Ingestion source")

        config = json.loads(decrypt_field(source.config_encrypted))

        if source.type == IngestionSourceType.kafka:
            from app.modules.ingestion.adapters.kafka_adapter import test_connectivity
            ok, lat, err = test_connectivity(config)
        elif source.type == IngestionSourceType.cdc_mysql:
            from app.modules.ingestion.adapters.cdc_adapter import test_mysql_connectivity
            ok, lat, err = test_mysql_connectivity(config)
        elif source.type == IngestionSourceType.cdc_pg:
            from app.modules.ingestion.adapters.cdc_adapter import test_pg_connectivity
            ok, lat, err = test_pg_connectivity(config)
        elif source.type == IngestionSourceType.batch_file:
            from app.modules.ingestion.adapters.batch_adapter import test_connectivity
            ok, lat, err = test_connectivity(config)
        elif source.type in (IngestionSourceType.logstash, IngestionSourceType.flume):
            # Push-based agents (Logstash/Flume): verify that the source config contains
            # an api_key and that the source is active — connectivity is confirmed when
            # the agent successfully pushes its first payload.
            api_key = config.get("api_key")
            if not api_key:
                ok, lat, err = False, None, "api_key missing in source config; Flume/Logstash sources require an api_key for webhook authentication."
            else:
                ok, lat, err = True, 0.0, None
        else:
            ok, lat, err = False, None, f"Unsupported source type: {source.type}"

        return ConnectivityResult(success=ok, latency_ms=lat, error=err)

    async def trigger_run(self, source_id: uuid.UUID) -> IngestionRunResponse:
        result = await self._db.execute(select(IngestionSource).where(IngestionSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("Ingestion source")
        run = await self.run_source(source)
        return run

    async def run_source(self, source: IngestionSource) -> IngestionRunResponse:
        run = IngestionRun(source_id=source.id, started_at=datetime.now(UTC))
        self._db.add(run)
        await self._db.flush()

        config = json.loads(decrypt_field(source.config_encrypted))
        rows_ingested = 0
        error = None

        try:
            if source.type == IngestionSourceType.kafka:
                from app.modules.ingestion.adapters.kafka_adapter import consume_batch
                import redis as redis_lib
                from app.core.config import settings as _settings
                r = redis_lib.from_url(_settings.REDIS_URL)
                _, rows_ingested = consume_batch(config, source.concurrency_cap, source_id=str(source.id), redis_client=r)
            elif source.type == IngestionSourceType.cdc_mysql:
                from app.modules.ingestion.adapters.cdc_adapter import pull_mysql_cdc
                from app.modules.ingestion.adapters.batch_adapter import filter_duplicates as _fd
                import redis as redis_lib
                from app.core.config import settings as _settings
                r = redis_lib.from_url(_settings.REDIS_URL)
                rows, _ = pull_mysql_cdc(config, source.concurrency_cap * 10)
                rows_ingested = len(_fd(rows, str(source.id), r))
            elif source.type == IngestionSourceType.cdc_pg:
                from app.modules.ingestion.adapters.cdc_adapter import pull_pg_cdc
                from app.modules.ingestion.adapters.batch_adapter import filter_duplicates as _fd
                import redis as redis_lib
                from app.core.config import settings as _settings
                r = redis_lib.from_url(_settings.REDIS_URL)
                rows, _ = pull_pg_cdc(config, source.concurrency_cap * 10)
                rows_ingested = len(_fd(rows, str(source.id), r))
            elif source.type in (IngestionSourceType.logstash, IngestionSourceType.flume):
                # logstash/flume deliver via HTTP webhook push; scheduled pull is a no-op
                rows_ingested = 0
            elif source.type == IngestionSourceType.batch_file:
                from app.modules.ingestion.adapters.batch_adapter import parse_file, filter_duplicates
                import redis as redis_lib
                from app.core.config import settings as _settings
                r = redis_lib.from_url(_settings.REDIS_URL)
                file_path = config.get("file_path", "")
                filename = file_path.split("/")[-1] or "data.csv"
                from app.core.storage import get_object_chunks
                bucket = config.get("bucket", _settings.MINIO_BUCKET_RECORDINGS)
                content = b"".join(get_object_chunks(bucket, file_path))
                rows = parse_file(content, filename)
                fresh = filter_duplicates(rows, str(source.id), r)
                rows_ingested = len(fresh)
            run.status = IngestionRunStatus.success
        except Exception as e:
            run.status = IngestionRunStatus.failed
            run.error_detail = str(e)
            error = str(e)

        run.finished_at = datetime.now(UTC)
        run.rows_ingested = rows_ingested
        source.last_run_at = run.finished_at
        source.last_status = run.status.value
        await self._db.flush()
        return IngestionRunResponse.model_validate(run)

    async def list_runs(self, source_id: uuid.UUID, limit: int = 50) -> list[IngestionRunResponse]:
        result = await self._db.execute(
            select(IngestionRun)
            .where(IngestionRun.source_id == source_id)
            .order_by(IngestionRun.started_at.desc())
            .limit(limit)
        )
        return [IngestionRunResponse.model_validate(r) for r in result.scalars().all()]

    async def handle_webhook(self, source_id: uuid.UUID, payload: list[dict], api_key: str) -> IngestionRunResponse:
        """Handle Logstash/Flume HTTP push. Validates X-Api-Key against source config."""
        result = await self._db.execute(select(IngestionSource).where(IngestionSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("Ingestion source")
        config = json.loads(decrypt_field(source.config_encrypted))
        if config.get("api_key") != api_key:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Invalid API key")

        from app.modules.ingestion.adapters.batch_adapter import filter_duplicates
        import redis as redis_lib
        from app.core.config import settings as _settings
        r = redis_lib.from_url(_settings.REDIS_URL)
        fresh_payload = filter_duplicates(payload, str(source.id), r)

        run = IngestionRun(
            source_id=source.id,
            started_at=datetime.now(UTC),
            rows_ingested=len(fresh_payload),
            status=IngestionRunStatus.success,
            finished_at=datetime.now(UTC),
        )
        self._db.add(run)
        source.last_run_at = run.finished_at
        source.last_status = "success"
        await self._db.flush()
        return IngestionRunResponse.model_validate(run)
