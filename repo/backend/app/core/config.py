from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://meridian:meridian@db:5432/meridian"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-at-least-64-chars-random-string-here"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # hard ceiling; inactivity window is the effective limit
    INACTIVITY_TIMEOUT_MINUTES: int = 30   # sliding window — idle longer than this expires session
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FIELD_ENCRYPTION_KEY: str = ""  # Base64 Fernet key; generated in entrypoint if blank
    PAYMENT_SIGNATURE_SECRET: str = "change-me-payment-secret"

    # Password policy
    PASSWORD_MIN_LENGTH: int = 12

    # Account lockout
    LOGIN_MAX_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_PUBLIC_ENDPOINT: str = ""   # Public-facing host:port for presigned download URLs (e.g. "localhost:9000"). Falls back to MINIO_ENDPOINT if blank.
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_RECORDINGS: str = "session-recordings"
    MINIO_USE_SSL: bool = False
    PRESIGNED_URL_EXPIRE_SECONDS: int = 3600

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"

    # Storage
    EXPORTS_DIR: str = "/app/exports"
    UPLOADS_DIR: str = "/app/uploads"

    # App
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200
    EXPORT_ROW_LIMIT: int = 50_000

    # Reconciliation
    RECONCILIATION_HOUR: int = 2    # 2:00 AM UTC

    # Audit log retention
    AUDIT_LOG_RETENTION_DAYS: int = 90

    # Order auto-close
    ORDER_EXPIRY_MINUTES: int = 30

    # Job health thresholds
    JOB_FAILURE_RATE_THRESHOLD_PCT: float = 2.0
    JOB_LATENESS_THRESHOLD_MINUTES: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
