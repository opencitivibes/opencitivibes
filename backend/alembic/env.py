"""Alembic environment

Uses project settings and database engine to run migrations.
This file is intentionally lightweight and imports the application's
SQLAlchemy `Base` metadata so autogenerate works.
"""

from __future__ import with_statement

import sys
from logging.config import fileConfig

from alembic import context

# Allow imports from package root
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import app settings and metadata (noqa: E402 - imports after path manipulation)
from models.config import settings  # noqa: E402
from repositories.database import Base, engine as app_engine  # noqa: E402

config = context.config

# Override sqlalchemy.url from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode using the app engine."""
    connectable = app_engine

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
