import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# ---------------------------------------------------------
# Load ENV so DATABASE_URL works
# ---------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------
# Alembic Config Object
# ---------------------------------------------------------
config = context.config

# Override DB URL dynamically from .env
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
else:
    raise RuntimeError("DATABASE_URL not found for Alembic.")

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------
# Import ATLAS Base + Models
# ---------------------------------------------------------
from app.core.database import Base
from app.models import (
    EvaluationLog,
    TrustConfig,
    Tenant,
    TenantAPIKey,
    UsageMeter,
    PricingPlan,
)

# THIS is critical for autogenerate
target_metadata = Base.metadata


# =========================================================
# OFFLINE MODE
# =========================================================

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# =========================================================
# ONLINE MODE
# =========================================================

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# =========================================================
# Entry
# =========================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()