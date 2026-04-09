# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start everything (one command)
docker compose up

# Run tests (requires PostgreSQL + Redis running)
docker compose exec backend pytest tests/ -v
docker compose exec backend pytest tests/unit/ -v           # unit only (no DB needed)
docker compose exec backend pytest tests/api/ -v            # API tests (need test DB)

# Run a single test file
docker compose exec backend pytest tests/unit/test_best_offer.py -v

# Migrations
docker compose exec backend alembic upgrade head
docker compose exec backend alembic revision --autogenerate -m "description"

# Celery tasks (manual trigger)
docker compose exec celery_worker celery -A app.modules.jobs.celery_app.celery_app call app.modules.jobs.tasks.close_expired_orders
```

## Architecture

### Module Layout

Every feature lives in `backend/app/modules/<name>/` with consistent files:
- `models.py` — SQLAlchemy ORM model(s)
- `schemas.py` — Pydantic request/response models
- `repository.py` — async DB queries (no business logic)
- `service.py` — business logic (calls repository)
- `controller.py` — FastAPI router (calls service)

### Key Design Decisions

**Promotion stacking** (`modules/checkout/best_offer.py`): Mutual exclusion by default. `null stack_group` = singleton pool (only best one applies). Same named `stack_group` = mutually exclusive within group. Different named groups = stackable across groups. `is_exclusive=True` = never combined.

**WebSocket live room** (`modules/sessions/websocket.py`): In-process `RoomConnectionManager`. Broadcasts triggered from service layer after DB writes (go-live, attendance checkin/out, roster changes). Token auth via `?token=` query param.

**Video storage** (`core/storage.py`): MinIO (S3-compatible). Recordings stored at `sessions/{session_id}/recording.mp4`. Access via presigned URLs generated on demand. Recording metadata in `session_recordings` table.

**Field encryption** (`core/encryption.py`): Fernet symmetric encryption for `users.email`, `users.phone`, `ingestion_sources.config`. Key from env `FIELD_ENCRYPTION_KEY`.

**Audit logging** (`core/audit.py`): `log_audit()` is fire-and-forget (never raises). Called from service layer for schedule changes, promotion changes, refund actions, access control changes.

**Job monitoring** (`modules/jobs/controller.py`): `GET /api/jobs/stats/aggregate` queries `job_executions` table directly — serves the admin console Vue UI. Grafana/Prometheus is for DevOps only.

**Search facets** (`modules/search/service.py`): `POST /api/search?include_facets=true` returns `facets` block with enrollment status counts, site counts, instructor counts — computed via `COUNT(*) GROUP BY` sub-queries.

### RBAC

`core/deps.py::require_roles(*roles)` — FastAPI dependency. Five roles: `admin`, `instructor`, `learner`, `finance`, `dataops`.

### Background Jobs

All Celery tasks in `modules/jobs/tasks.py`. Beat schedule in `modules/jobs/celery_app.py`. Each task wraps execution in try/finally and writes to `job_executions`. Retry policy: `max_retries=3`, exponential backoff.

### Ingestion Pipeline

Source types: `kafka`, `logstash` (webhook), `batch_file`, `cdc_mysql`, `cdc_pg`. Adapters in `modules/ingestion/adapters/`. Dedup via Redis sets with 7-day TTL. Config stored Fernet-encrypted in `ingestion_sources.config_encrypted`.

## Database

PostgreSQL 15 with `uuid-ossp` and `pg_trgm` extensions. All UUIDs as primary keys. Timestamps in UTC with timezone. Migrations via Alembic in `backend/alembic/versions/`.

Sensitive columns: `users.email_encrypted`, `users.phone_encrypted`, `ingestion_sources.config_encrypted` — always encrypted at rest, never store plaintext.

## Environment Variables

See `backend/.env.example` for all required variables. Critical secrets: `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `PAYMENT_SIGNATURE_SECRET`.
