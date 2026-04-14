import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IngestionSourceType(str, enum.Enum):
    kafka = "kafka"
    flume = "flume"
    logstash = "logstash"
    file = "file"
    mysql_cdc = "mysql_cdc"
    postgres_cdc = "postgres_cdc"


class IngestionRunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    partial_failed = "partial_failed"
    failed = "failed"
    canceled = "canceled"
    resolved = "resolved"


class IngestionSource(Base):
    __tablename__ = "ingestion_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    type: Mapped[IngestionSourceType] = mapped_column(Enum(IngestionSourceType), nullable=False)
    config_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-encrypted JSON
    collection_frequency_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    concurrency_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    runs: Mapped[list["IngestionRun"]] = relationship("IngestionRun", back_populates="source")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_sources.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rows_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[IngestionRunStatus] = mapped_column(Enum(IngestionRunStatus), nullable=False, default=IngestionRunStatus.running)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[IngestionSource] = relationship("IngestionSource", back_populates="runs")
