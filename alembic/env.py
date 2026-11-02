from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import create_engine, pool

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.database.base import Base

# Import all models to register their metadata.
import app.models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

MODEL_TABLES = {
    "users",
    "conversations",
    "messages",
    "user_preferences",
    "documents",
    "learning_activities",
     "study_resources",
     "resource_categories",
    "study_resource_categories",
    "user_resource_interactions",
    "recommendations",
    "recommendation_feedback",
}


def include_name(name, type_, parent_names):
    """
    Restrict reflected database tables to registered ScholarAI models.
    """

    if type_ == "table":
        return name in MODEL_TABLES

    return True


def include_object(object, name, type_, reflected, compare_to):
    """
    Include only registered ScholarAI model tables.
    """

    if type_ == "table":
        return name in MODEL_TABLES

    return True


def run_migrations_offline():
    database_url = settings.DATABASE_URL

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from .env")

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_name=include_name,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    database_url = settings.DATABASE_URL

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from .env")

    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                include_name=include_name,
                include_object=include_object,
            )

            with context.begin_transaction():
                context.run_migrations()

    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()