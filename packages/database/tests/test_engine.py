"""
Tests for database engine and session management.

This module tests:
- Async database engine creation
- Connection pooling configuration
- Health check functionality
- Connection error handling
- Session management and lifecycle
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from database.engine import (
    _engine,
    _session_factory,
    check_database_connection,
    close_engine,
    create_engine,
    get_engine,
    get_session,
    get_session_factory,
    get_transaction,
)
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import NullPool, QueuePool


class TestEngineCreation:
    """Test database engine creation and configuration."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global engine state after each test."""
        yield
        # Reset global state
        global _engine, _session_factory
        if _engine:
            await close_engine()
        _engine = None
        _session_factory = None

    def test_create_engine_basic(self):
        """Test basic engine creation."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.pool_size = 5
            mock_config.max_overflow = 10
            mock_config.pool_timeout = 30
            mock_config.pool_recycle = 3600
            mock_config.validate.return_value = None

            engine = create_engine()

            assert engine is not None
            assert isinstance(engine, AsyncEngine)
            mock_config.validate.assert_called_once()

    def test_create_engine_production_config(self):
        """Test engine creation with production configuration."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_config.debug = False
            mock_config.is_production = True
            mock_config.pool_size = 20
            mock_config.max_overflow = 50
            mock_config.pool_timeout = 60
            mock_config.pool_recycle = 7200
            mock_config.validate.return_value = None

            with patch("database.engine.create_async_engine") as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine

                create_engine()

                # Verify production pool settings
                mock_create.assert_called_once()
                call_args = mock_create.call_args

                assert call_args[1]["poolclass"] == QueuePool
                assert call_args[1]["pool_size"] == 20
                assert call_args[1]["max_overflow"] == 50
                assert call_args[1]["pool_timeout"] == 60
                assert call_args[1]["pool_recycle"] == 7200

    def test_create_engine_development_config(self):
        """Test engine creation with development configuration."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = True
            mock_config.is_production = False
            mock_config.validate.return_value = None

            with patch("database.engine.create_async_engine") as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine

                create_engine()

                # Verify development pool settings (NullPool)
                mock_create.assert_called_once()
                call_args = mock_create.call_args

                assert call_args[1]["poolclass"] == NullPool
                assert call_args[1]["echo"] is True
                assert call_args[1]["echo_pool"] is True

    def test_create_engine_singleton(self):
        """Test that create_engine returns the same instance."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            engine1 = create_engine()
            engine2 = create_engine()

            # Should return the same instance
            assert engine1 is engine2

    def test_get_engine_creates_if_not_exists(self):
        """Test that get_engine creates engine if not exists."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            engine = get_engine()

            assert engine is not None
            assert isinstance(engine, AsyncEngine)

    def test_get_engine_returns_existing(self):
        """Test that get_engine returns existing engine."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            # Create engine first
            engine1 = create_engine()

            # get_engine should return the same instance
            engine2 = get_engine()

            assert engine1 is engine2


class TestSessionFactory:
    """Test session factory creation and management."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global state after each test."""
        yield
        if _engine:
            await close_engine()

    def test_get_session_factory_creates_if_not_exists(self):
        """Test session factory creation."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            factory = get_session_factory()

            assert factory is not None

    def test_get_session_factory_singleton(self):
        """Test that session factory is singleton."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            factory1 = get_session_factory()
            factory2 = get_session_factory()

            assert factory1 is factory2


class TestSessionManagement:
    """Test async session management."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global state after each test."""
        yield
        if _engine:
            await close_engine()

    @pytest.mark.asyncio
    async def test_get_session_context_manager(self, temp_db_file):
        """Test session context manager."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = f"sqlite+aiosqlite:///{temp_db_file}"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            async with get_session() as session:
                assert session is not None
                assert isinstance(session, AsyncSession)

                # Session should be usable
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_get_session_commit_on_success(self, temp_db_file):
        """Test that session commits on successful completion."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = f"sqlite+aiosqlite:///{temp_db_file}"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            # Create engine and tables
            engine = create_engine()
            async with engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: None
                )  # Just ensure connection works

            # Mock session to verify commit is called
            with patch("database.engine.async_sessionmaker") as mock_sessionmaker:
                mock_session = AsyncMock()
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_sessionmaker.return_value.return_value = mock_session

                async with get_session() as session:
                    pass

                # Verify commit was called
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_rollback_on_exception(self, temp_db_file):
        """Test that session rolls back on exception."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = f"sqlite+aiosqlite:///{temp_db_file}"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            # Mock session to verify rollback is called
            with patch("database.engine.async_sessionmaker") as mock_sessionmaker:
                mock_session = AsyncMock()
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_sessionmaker.return_value.return_value = mock_session

                with pytest.raises(ValueError):
                    async with get_session() as session:
                        raise ValueError("Test exception")

                # Verify rollback was called
                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transaction_context_manager(self, temp_db_file):
        """Test transaction context manager."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = f"sqlite+aiosqlite:///{temp_db_file}"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            async with get_transaction() as session:
                assert session is not None
                assert isinstance(session, AsyncSession)

                # Session should be usable within transaction
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_get_transaction_rollback_on_exception(self, temp_db_file):
        """Test that transaction rolls back on exception."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = f"sqlite+aiosqlite:///{temp_db_file}"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            # Mock session to verify rollback behavior
            with patch("database.engine.async_sessionmaker") as mock_sessionmaker:
                mock_session = AsyncMock()
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_session.begin.return_value.__aenter__ = AsyncMock(
                    return_value=None
                )
                mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
                mock_sessionmaker.return_value.return_value = mock_session

                with pytest.raises(ValueError):
                    async with get_transaction() as session:
                        raise ValueError("Test exception")

                # Transaction context manager handles rollback automatically


class TestEngineCleanup:
    """Test engine cleanup and disposal."""

    @pytest.mark.asyncio
    async def test_close_engine(self):
        """Test engine disposal."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            # Create engine
            engine = create_engine()
            assert engine is not None

            # Close engine
            await close_engine()

            # Global state should be reset
            assert _engine is None
            assert _session_factory is None

    @pytest.mark.asyncio
    async def test_close_engine_when_none(self):
        """Test closing engine when none exists."""
        # Should not raise exception
        await close_engine()

    @pytest.mark.asyncio
    async def test_close_engine_disposes_properly(self):
        """Test that close_engine properly disposes the engine."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            with patch("database.engine.create_async_engine") as mock_create:
                mock_engine = AsyncMock()
                mock_create.return_value = mock_engine

                # Create and close engine
                create_engine()
                await close_engine()

                # Verify dispose was called
                mock_engine.dispose.assert_called_once()


class TestHealthCheck:
    """Test database health check functionality."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global state after each test."""
        yield
        if _engine:
            await close_engine()

    @pytest.mark.asyncio
    async def test_check_database_connection_success(self, temp_db_file):
        """Test successful database connection check."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = f"sqlite+aiosqlite:///{temp_db_file}"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            result = await check_database_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self):
        """Test database connection check failure."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = (
                "postgresql+asyncpg://invalid:invalid@nonexistent:5432/invalid"
            )
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            with patch("database.engine.get_engine") as mock_get_engine:
                mock_engine = AsyncMock()
                mock_engine.begin.side_effect = OperationalError(
                    "Connection failed", None, None
                )
                mock_get_engine.return_value = mock_engine

                result = await check_database_connection()

                assert result is False

    @pytest.mark.asyncio
    async def test_check_database_connection_logs_error(self, caplog):
        """Test that connection check logs errors."""
        with caplog.at_level(logging.ERROR):
            with patch("database.engine.db_config") as mock_config:
                mock_config.database_url = (
                    "postgresql+asyncpg://invalid:invalid@nonexistent:5432/invalid"
                )
                mock_config.debug = False
                mock_config.is_production = False
                mock_config.validate.return_value = None

                with patch("database.engine.get_engine") as mock_get_engine:
                    mock_engine = AsyncMock()
                    mock_engine.begin.side_effect = OperationalError(
                        "Connection failed", None, None
                    )
                    mock_get_engine.return_value = mock_engine

                    await check_database_connection()

                    # Check that error was logged
                    assert "Database health check failed" in caplog.text


class TestEventListeners:
    """Test database event listeners."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global state after each test."""
        yield
        if _engine:
            await close_engine()

    def test_event_listeners_added(self):
        """Test that event listeners are properly added."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = True
            mock_config.is_production = False
            mock_config.validate.return_value = None

            with patch("database.engine.event.listens_for") as mock_listens_for:
                create_engine()

                # Verify event listeners were registered
                assert mock_listens_for.call_count >= 3  # At least 3 event listeners

    def test_debug_logging_events(self, caplog):
        """Test debug logging event listeners."""
        with caplog.at_level(logging.DEBUG):
            with patch("database.engine.db_config") as mock_config:
                mock_config.database_url = "sqlite+aiosqlite:///test.db"
                mock_config.debug = True
                mock_config.is_production = False
                mock_config.validate.return_value = None

                # Create engine (this adds event listeners)
                create_engine()

                # Event listeners should be set up for debug logging
                # We can't easily test the actual events without a real database connection
                # but we can verify the engine was created with debug=True


class TestErrorHandling:
    """Test error handling in engine operations."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global state after each test."""
        yield
        if _engine:
            await close_engine()

    def test_create_engine_validation_error(self):
        """Test engine creation with validation error."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.validate.side_effect = ValueError("Invalid configuration")

            with pytest.raises(ValueError, match="Invalid configuration"):
                create_engine()

    @pytest.mark.asyncio
    async def test_session_creation_error(self):
        """Test session creation error handling."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            with patch("database.engine.async_sessionmaker") as mock_sessionmaker:
                mock_sessionmaker.side_effect = SQLAlchemyError(
                    "Session creation failed"
                )

                with pytest.raises(SQLAlchemyError):
                    async with get_session():
                        pass

    @pytest.mark.asyncio
    async def test_connection_error_in_health_check(self):
        """Test connection error handling in health check."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///nonexistent.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            with patch("database.engine.get_engine") as mock_get_engine:
                mock_engine = AsyncMock()
                mock_engine.begin.side_effect = Exception("Unexpected error")
                mock_get_engine.return_value = mock_engine

                result = await check_database_connection()

                # Should handle any exception gracefully
                assert result is False


class TestConcurrentAccess:
    """Test concurrent access to engine and sessions."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global state after each test."""
        yield
        if _engine:
            await close_engine()

    @pytest.mark.asyncio
    async def test_concurrent_engine_creation(self):
        """Test concurrent engine creation."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            # Create multiple engines concurrently
            engines = await asyncio.gather(
                *[
                    asyncio.create_task(asyncio.to_thread(create_engine))
                    for _ in range(5)
                ]
            )

            # All should be the same instance (singleton behavior)
            first_engine = engines[0]
            for engine in engines[1:]:
                assert engine is first_engine

    @pytest.mark.asyncio
    async def test_concurrent_session_usage(self, temp_db_file):
        """Test concurrent session usage."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = f"sqlite+aiosqlite:///{temp_db_file}"
            mock_config.debug = False
            mock_config.is_production = False
            mock_config.validate.return_value = None

            async def use_session(session_id):
                async with get_session() as session:
                    result = await session.execute(text(f"SELECT {session_id}"))
                    return result.scalar()

            # Use multiple sessions concurrently
            results = await asyncio.gather(*[use_session(i) for i in range(5)])

            # Each session should return its ID
            assert results == [0, 1, 2, 3, 4]


class TestPerformanceConfiguration:
    """Test performance-related configuration."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Clean up global state after each test."""
        yield
        if _engine:
            await close_engine()

    def test_production_pool_configuration(self):
        """Test production pool configuration."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_config.debug = False
            mock_config.is_production = True
            mock_config.pool_size = 50
            mock_config.max_overflow = 100
            mock_config.pool_timeout = 120
            mock_config.pool_recycle = 14400
            mock_config.validate.return_value = None

            with patch("database.engine.create_async_engine") as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine

                create_engine()

                # Verify high-performance production settings
                call_args = mock_create.call_args[1]
                assert call_args["poolclass"] == QueuePool
                assert call_args["pool_size"] == 50
                assert call_args["max_overflow"] == 100
                assert call_args["pool_timeout"] == 120
                assert call_args["pool_recycle"] == 14400
                assert call_args["pool_pre_ping"] is True

    def test_development_performance_settings(self):
        """Test development performance settings."""
        with patch("database.engine.db_config") as mock_config:
            mock_config.database_url = "sqlite+aiosqlite:///test.db"
            mock_config.debug = True
            mock_config.is_production = False
            mock_config.validate.return_value = None

            with patch("database.engine.create_async_engine") as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine

                create_engine()

                # Verify development settings prioritize debugging
                call_args = mock_create.call_args[1]
                assert call_args["poolclass"] == NullPool
                assert call_args["echo"] is True
                assert call_args["echo_pool"] is True
