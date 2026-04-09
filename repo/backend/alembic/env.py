import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models so Alembic can autogenerate against them
from app.core.database import Base  # noqa: F401
from app.modules.users.models import User  # noqa: F401
from app.modules.locations.models import Location, Room  # noqa: F401
from app.modules.courses.models import Course  # noqa: F401
from app.modules.instructors.models import Instructor  # noqa: F401
from app.modules.sessions.models import Session, RecurrenceRule  # noqa: F401
from app.modules.bookings.models import Booking  # noqa: F401
from app.modules.attendance.models import AttendanceRecord  # noqa: F401
from app.modules.replays.models import ReplayAccessRule, SessionRecording, ReplayView  # noqa: F401
from app.modules.promotions.models import Promotion  # noqa: F401
from app.modules.checkout.models import Order, OrderItem, OrderPromotion  # noqa: F401
from app.modules.payments.models import Payment, Refund, ReconciliationExport  # noqa: F401
from app.modules.search.models import SavedSearch  # noqa: F401
from app.modules.ingestion.models import IngestionSource, IngestionRun  # noqa: F401
from app.modules.jobs.models import JobExecution, MonitoringAlert  # noqa: F401
from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.policy.models import AdminPolicy  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from environment variable
db_url = os.getenv("DATABASE_URL", "")
if db_url:
    # Alembic needs sync driver for migration; replace asyncpg with psycopg2
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
