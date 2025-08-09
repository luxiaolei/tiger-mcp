"""
Alembic environment configuration for Tiger MCP database migrations.
"""

import asyncio
import logging
from logging.config import fileConfig

from alembic import context
from database.base import Base
from database.config import db_config

# Import models to ensure they're registered
from database.models import *  # noqa: F403, F401
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Set the target metadata
target_metadata = Base.metadata

# Set the database URL from our config
config.set_main_option("sqlalchemy.url", db_config.sync_database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
        # Include schemas in autogenerate
        include_schemas=True,
        # Custom rendering options
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
        # Include schemas in autogenerate
        include_schemas=True,
        # Custom rendering options
        render_item=render_item,
        # Transaction per migration
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    try:
        asyncio.run(run_async_migrations())
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def render_item(type_, obj, autogen_context):
    """
    Custom rendering for migration objects.

    Apply custom rendering rules for specific types.
    """
    # Add custom rendering rules here if needed
    if type_ == "type" and hasattr(obj, "impl"):
        # Handle custom types
        pass

    # Return False to use default rendering
    return False


def include_object(object, name, type_, reflected, compare_to):
    """
    Determine whether to include an object in the migration.

    This function is called for each object (table, column, index, etc.)
    and can be used to exclude objects from autogenerate.
    """
    # Skip objects that shouldn't be in migrations
    if type_ == "table" and name.startswith("_"):
        return False

    # Include all other objects
    return True


# Add custom comparison functions if needed
def compare_type(
    context, inspected_column, metadata_column, inspected_type, metadata_type
):
    """Custom type comparison function."""
    # Add custom type comparison logic if needed
    return None


def compare_server_default(
    context,
    inspected_column,
    metadata_column,
    inspected_default,
    metadata_default,
    rendered_metadata_default,
):
    """Custom server default comparison function."""
    # Add custom default comparison logic if needed
    return None


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
