# Meridian Training Operations System — Backend

Production-grade, fully offline training management platform.

## Start

```bash
docker compose up
```

All services build automatically. No manual setup required.

## Service URLs

| Service | URL |
|---|---|
| API | http://localhost/api |
| API Docs (Swagger) | http://localhost/api/docs |
| API Docs (ReDoc) | http://localhost/api/redoc |
| MinIO Console | http://localhost:9001 (minioadmin / minioadmin123) |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |

## Verification

```bash
# Health check
curl http://localhost/api/monitoring/health
# → {"status": "ok", "timestamp": "..."}

# Login with default admin
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin@Meridian1"}'
```

## Default Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@Meridian1` |

**Change the admin password immediately after first login.**

## Configuration

Copy `backend/.env.example` to `backend/.env` for local override. All secrets are loaded from environment variables. `docker-compose.yml` contains **development-only defaults** — these must be replaced with strong, unique values before any production deployment.

Key secrets to rotate in production:
- `SECRET_KEY` — JWT signing key
- `FIELD_ENCRYPTION_KEY` — Fernet key for PII encryption
- `PAYMENT_SIGNATURE_SECRET` — HMAC key for terminal callbacks
- `MINIO_SECRET_KEY` — MinIO credentials

## Running Tests

```bash
# Inside the backend container or with local Python env:
docker compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing
```

## Architecture

- **Backend**: FastAPI on port 8000, proxied by Nginx on port 80
- **Database**: PostgreSQL 15 — all state persisted here
- **Cache/Queue**: Redis — JWT blocklist, Celery broker, dedup sets
- **Jobs**: Celery worker + Beat for all scheduled tasks
- **Video**: MinIO (S3-compatible) for session recordings
- **Streaming**: Kafka for data ingestion
- **Monitoring**: Prometheus scrapes `/api/monitoring/metrics`; Grafana visualises

## WebSocket Live Room

Connect via `WS /api/ws/sessions/{session_id}/room?token=<access_jwt>`

Receives real-time push events: `room_state`, `session_status_changed`, `attendee_joined`, `attendee_left`, `roster_update`.
