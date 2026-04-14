#!/bin/bash
set -e

echo "==> Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-meridian}"; do
  sleep 1
done
echo "==> PostgreSQL is ready."

echo "==> Ensuring test database exists..."
psql "postgresql://${DB_USER:-meridian}:${DB_PASSWORD:-meridian}@${DB_HOST:-db}:${DB_PORT:-5432}/postgres" \
  -tc "SELECT 1 FROM pg_database WHERE datname='meridian_test'" \
  | grep -q 1 \
  || psql "postgresql://${DB_USER:-meridian}:${DB_PASSWORD:-meridian}@${DB_HOST:-db}:${DB_PORT:-5432}/postgres" \
     -c "CREATE DATABASE meridian_test OWNER ${DB_USER:-meridian}"

echo "==> Running Alembic migrations..."
cd /app
alembic -c alembic/alembic.ini upgrade head

if [ "${APP_ENV:-production}" != "production" ]; then
  echo "==> Seeding default admin user (non-production only)..."
  python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.modules.users.models import User, UserRole
from sqlalchemy import select

async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == 'admin'))
        if not result.scalar_one_or_none():
            admin = User(
                username='admin',
                password_hash=hash_password('Admin@Meridian1'),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            print('Default admin user created.')
        else:
            print('Admin user already exists.')

asyncio.run(seed())
"
else
  echo "==> Production mode: skipping default admin seed. Create an admin user via the API or database directly."
fi

echo "==> Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info
