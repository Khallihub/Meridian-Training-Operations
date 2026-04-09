#!/bin/bash
set -e

echo "==> Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-meridian}"; do
  sleep 1
done

echo "==> Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping | grep -q PONG; do
  sleep 1
done

cd /app

if [ "$CELERY_ROLE" = "beat" ]; then
  echo "==> Starting Celery Beat..."
  exec celery -A app.modules.jobs.celery_app.celery_app beat --loglevel=info
else
  echo "==> Starting Celery Worker..."
  exec celery -A app.modules.jobs.celery_app.celery_app worker --loglevel=info --concurrency=4
fi
