"""
SQLAlchemy async engine configuration and session management.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from .config import db_config

logger = logging.getLogger(__name__)

# Global engine instance
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def create_engine() -> AsyncEngine:
    """Create and configure SQLAlchemy async engine."""
    global _engine, _session_factory

    if _engine is not None:
        return _engine

    # Validate configuration
    db_config.validate()

    # Engine configuration
    engine_kwargs = {
        "echo": db_config.debug,
        "echo_pool": db_config.debug,
        "future": True,
        "pool_pre_ping": True,
        "pool_recycle": db_config.pool_recycle,
    }

    # Configure connection pooling
    if db_config.is_production:
        # Use QueuePool for production
        engine_kwargs.update(
            {
                "poolclass": QueuePool,
                "pool_size": db_config.pool_size,
                "max_overflow": db_config.max_overflow,
                "pool_timeout": db_config.pool_timeout,
            }
        )
    else:
        # Use NullPool for development to avoid connection issues
        engine_kwargs["poolclass"] = NullPool

    # Create engine
    _engine = create_async_engine(db_config.database_url, **engine_kwargs)

    # Create session factory
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )

    # Add event listeners
    _add_event_listeners(_engine)

    logger.info(
        f"Created database engine for {db_config.host}:{db_config.port}/{db_config.name}"
    )

    return _engine


def get_engine() -> AsyncEngine:
    """Get the global engine instance."""
    if _engine is None:
        return create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the global session factory."""
    if _session_factory is None:
        create_engine()
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session with explicit transaction control."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                # Transaction will be rolled back automatically
                raise


async def close_engine() -> None:
    """Close the database engine and all connections."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine closed")
        _engine = None
        _session_factory = None


def _add_event_listeners(engine: AsyncEngine) -> None:
    """Add event listeners for logging and monitoring."""

    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        """Log new database connections."""
        logger.debug("New database connection established")

    @event.listens_for(engine.sync_engine, "close")
    def on_close(dbapi_connection, connection_record):
        """Log database connection closures."""
        logger.debug("Database connection closed")

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        """Log SQL queries in debug mode."""
        if db_config.debug:
            logger.debug(f"Executing SQL: {statement}")
            if parameters:
                logger.debug(f"Parameters: {parameters}")

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log SQL execution time in debug mode."""
        if db_config.debug:
            total_time = context.get_current_parameters().get("duration", 0)
            logger.debug(f"SQL execution completed in {total_time:.3f}s")


# Health check function
async def check_database_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
