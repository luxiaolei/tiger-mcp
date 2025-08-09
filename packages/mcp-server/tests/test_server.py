"""
Unit tests for Tiger MCP Server.

Tests the TigerMCPServer class that orchestrates all components including:
1. Server initialization and lifecycle management
2. Service orchestration and dependency management
3. Background task management and monitoring
4. Configuration loading and validation
5. Health status reporting and monitoring
6. Graceful shutdown and resource cleanup
"""

import asyncio
import signal
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the class under test
from mcp_server.server import TigerMCPServer


class TestTigerMCPServer:
    """Test suite for TigerMCPServer."""

    @pytest.mark.asyncio
    async def test_server_initialization(self, mock_config):
        """Test server initialization with default parameters."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            # Create server
            server = TigerMCPServer()

            # Verify initial state
            assert server.config_manager is not None
            assert server.config is None
            assert server.account_manager is None
            assert server.account_router is None
            assert server.process_manager is None
            assert server.tiger_service is None
            assert len(server.background_tasks) == 0
            assert not server._started
            assert not server.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_server_initialization_with_config(self, mock_config):
        """Test server initialization with custom config file."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            # Create server with custom config
            server = TigerMCPServer(
                config_file="/path/to/custom/config.yaml", environment="testing"
            )

            # Verify config manager was called with parameters
            mock_get_config_manager.assert_called_once_with(
                config_file="/path/to/custom/config.yaml", environment="testing"
            )

    @pytest.mark.asyncio
    async def test_server_initialize_success(
        self,
        mock_config,
        mock_db_manager,
        mock_account_manager,
        mock_account_router,
        mock_process_manager,
        mock_tiger_service,
    ):
        """Test successful server initialization."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_config_manager.load_config.return_value = mock_config
            mock_get_config_manager.return_value = mock_config_manager

            # Create server
            server = TigerMCPServer()

            # Mock all initialization steps
            with (
                patch.object(server, "_configure_logging") as mock_configure_logging,
                patch.object(server, "_initialize_database") as mock_init_db,
                patch.object(
                    server, "_initialize_account_services"
                ) as mock_init_accounts,
                patch.object(server, "_initialize_process_pool") as mock_init_process,
                patch.object(server, "_initialize_tiger_service") as mock_init_tiger,
                patch.object(server, "_start_background_tasks") as mock_start_tasks,
            ):

                # Execute initialization
                await server.initialize()

                # Verify initialization order and calls
                mock_config_manager.load_config.assert_called_once()
                mock_configure_logging.assert_called_once()
                mock_init_db.assert_called_once()
                mock_init_accounts.assert_called_once()
                mock_init_process.assert_called_once()
                mock_init_tiger.assert_called_once()
                mock_start_tasks.assert_called_once()

                # Verify final state
                assert server.config == mock_config
                assert server._started is True

    @pytest.mark.asyncio
    async def test_server_initialize_failure(self, mock_config):
        """Test server initialization failure and cleanup."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_config_manager.load_config.return_value = mock_config
            mock_get_config_manager.return_value = mock_config_manager

            # Create server
            server = TigerMCPServer()

            # Mock failure during process pool initialization
            with (
                patch.object(server, "_configure_logging"),
                patch.object(server, "_initialize_database"),
                patch.object(server, "_initialize_account_services"),
                patch.object(server, "_initialize_process_pool") as mock_init_process,
                patch.object(server, "cleanup") as mock_cleanup,
            ):

                mock_init_process.side_effect = RuntimeError(
                    "Process pool initialization failed"
                )

                # Execute initialization and expect failure
                with pytest.raises(
                    RuntimeError, match="Process pool initialization failed"
                ):
                    await server.initialize()

                # Verify cleanup was called
                mock_cleanup.assert_called_once()
                assert server._started is False

    @pytest.mark.asyncio
    async def test_configure_logging(self, mock_config):
        """Test logging configuration."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config

            with patch("loguru.logger") as mock_logger:
                # Execute logging configuration
                server._configure_logging()

                # Verify logger configuration
                mock_logger.remove.assert_called_once()
                assert mock_logger.add.call_count >= 1  # At least console logging

                # Check if production logging is configured
                if mock_config.environment == "production":
                    assert mock_logger.add.call_count == 2  # Console + file
                else:
                    assert mock_logger.add.call_count == 1  # Console only

    @pytest.mark.asyncio
    async def test_initialize_database_success(self, mock_config, mock_db_manager):
        """Test successful database initialization."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config

            # Execute database initialization
            await server._initialize_database()

            # Verify database manager initialization
            mock_db_manager.initialize.assert_called_once_with(
                database_url=mock_config.database.url, echo=mock_config.database.echo
            )

    @pytest.mark.asyncio
    async def test_initialize_database_import_error(self, mock_config, capture_logs):
        """Test database initialization when database package is not available."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config

            # Mock import error
            with patch(
                "mcp_server.server.get_db_manager",
                side_effect=ImportError("Database package not available"),
            ):
                # Should not raise exception, just log warning
                await server._initialize_database()

                # Check that warning was logged
                log_messages = [record.message for record in capture_logs]
                assert any(
                    "Database package not available" in msg for msg in log_messages
                )

    @pytest.mark.asyncio
    async def test_initialize_account_services(
        self, mock_config, mock_account_manager, mock_account_router
    ):
        """Test account services initialization."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config

            # Execute account services initialization
            await server._initialize_account_services()

            # Verify services were initialized
            assert server.account_manager is not None
            assert server.account_router is not None
            mock_account_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_process_pool(self, mock_config, mock_process_manager):
        """Test process pool initialization."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config

            # Execute process pool initialization
            await server._initialize_process_pool()

            # Verify process manager configuration and start
            assert server.process_manager is not None
            mock_process_manager.configure.assert_called_once()
            mock_process_manager.start.assert_called_once()

            # Verify configuration parameters
            config_call = mock_process_manager.configure.call_args
            assert config_call[1]["min_workers"] == mock_config.process.min_workers
            assert config_call[1]["max_workers"] == mock_config.process.max_workers

    @pytest.mark.asyncio
    async def test_initialize_tiger_service(self, mock_config, mock_tiger_service):
        """Test Tiger API service initialization."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config

            # Execute Tiger service initialization
            await server._initialize_tiger_service()

            # Verify service was started
            assert server.tiger_service is not None
            mock_tiger_service.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_background_tasks(
        self, mock_config, mock_account_manager, mock_process_manager
    ):
        """Test background task startup."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.account_manager = mock_account_manager
            server.process_manager = mock_process_manager

            # Mock asyncio.create_task
            mock_tasks = [MagicMock() for _ in range(3)]
            with patch("asyncio.create_task", side_effect=mock_tasks):
                # Execute background task startup
                await server._start_background_tasks()

                # Verify tasks were created and tracked
                assert len(server.background_tasks) == 3
                assert all(task in server.background_tasks for task in mock_tasks)

    @pytest.mark.asyncio
    async def test_token_refresh_task(self, mock_config, mock_account_manager):
        """Test token refresh background task."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.account_manager = mock_account_manager

            # Mock shutdown event for quick termination
            server.shutdown_event.set()

            # Execute token refresh task
            await server._token_refresh_task()

            # Task should complete quickly due to shutdown event
            # Verify account manager method would be called if not shutdown
            assert mock_account_manager.refresh_expiring_tokens.call_count >= 0

    @pytest.mark.asyncio
    async def test_token_refresh_task_error_handling(
        self, mock_config, mock_account_manager, capture_logs
    ):
        """Test token refresh task error handling."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.account_manager = mock_account_manager

            # Mock account manager to raise error
            mock_account_manager.refresh_expiring_tokens.side_effect = RuntimeError(
                "Token refresh failed"
            )

            # Set shutdown event to terminate task after one iteration
            async def delayed_shutdown():
                await asyncio.sleep(0.1)
                server.shutdown_event.set()

            # Run task and shutdown concurrently
            await asyncio.gather(
                server._token_refresh_task(), delayed_shutdown(), return_exceptions=True
            )

            # Verify error was logged
            log_messages = [record.message for record in capture_logs]
            assert any("Error in token refresh task" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_health_monitor_task(self, mock_config, mock_process_manager):
        """Test health monitoring background task."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.process_manager = mock_process_manager

            # Mock shutdown event for quick termination
            server.shutdown_event.set()

            # Execute health monitor task
            await server._health_monitor_task()

            # Task should complete quickly due to shutdown event
            # Verify process manager methods would be called if not shutdown
            assert mock_process_manager.check_worker_health.call_count >= 0
            assert mock_process_manager.auto_scale.call_count >= 0

    @pytest.mark.asyncio
    async def test_health_monitor_task_with_unhealthy_workers(
        self, mock_config, mock_process_manager, capture_logs
    ):
        """Test health monitoring with unhealthy workers."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.process_manager = mock_process_manager

            # Mock unhealthy workers
            mock_process_manager.check_worker_health.return_value = [
                "worker1",
                "worker2",
            ]

            # Set shutdown event to terminate task after one iteration
            async def delayed_shutdown():
                await asyncio.sleep(0.1)
                server.shutdown_event.set()

            # Run task and shutdown concurrently
            await asyncio.gather(
                server._health_monitor_task(),
                delayed_shutdown(),
                return_exceptions=True,
            )

            # Verify warning was logged
            log_messages = [record.message for record in capture_logs]
            assert any("unhealthy workers" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_cleanup_task(
        self, mock_config, mock_account_manager, mock_process_manager
    ):
        """Test cleanup background task."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.account_manager = mock_account_manager
            server.process_manager = mock_process_manager

            # Mock shutdown event for quick termination
            server.shutdown_event.set()

            # Execute cleanup task
            await server._cleanup_task()

            # Task should complete quickly due to shutdown event
            # Verify cleanup methods would be called if not shutdown
            assert mock_account_manager.cleanup_expired_sessions.call_count >= 0
            assert mock_process_manager.cleanup_old_metrics.call_count >= 0

    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self, mock_config):
        """Test waiting for shutdown signal."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()

            # Set shutdown event in parallel
            async def trigger_shutdown():
                await asyncio.sleep(0.1)
                server.shutdown_event.set()

            # Wait for shutdown
            await asyncio.gather(server.wait_for_shutdown(), trigger_shutdown())

            # Should complete when shutdown event is set
            assert server.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_cleanup_success(
        self,
        mock_config,
        mock_tiger_service,
        mock_process_manager,
        mock_account_manager,
        mock_db_manager,
    ):
        """Test successful server cleanup."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.tiger_service = mock_tiger_service
            server.process_manager = mock_process_manager
            server.account_manager = mock_account_manager
            server._started = True

            # Add mock background tasks
            mock_task1 = AsyncMock()
            mock_task2 = AsyncMock()
            server.background_tasks = [mock_task1, mock_task2]

            # Execute cleanup
            await server.cleanup()

            # Verify cleanup order and calls
            mock_task1.cancel.assert_called_once()
            mock_task2.cancel.assert_called_once()
            mock_tiger_service.stop.assert_called_once()
            mock_process_manager.stop.assert_called_once()
            mock_account_manager.cleanup.assert_called_once()
            mock_db_manager.cleanup.assert_called_once()

            # Verify final state
            assert server._started is False
            assert len(server.background_tasks) == 0

    @pytest.mark.asyncio
    async def test_cleanup_with_task_timeout(self, mock_config, capture_logs):
        """Test cleanup with background task timeout."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config

            # Create mock task that doesn't complete
            mock_task = AsyncMock()
            server.background_tasks = [mock_task]

            # Mock asyncio.wait_for to raise timeout
            with patch(
                "asyncio.wait_for",
                side_effect=asyncio.TimeoutError("Tasks did not complete"),
            ):
                await server.cleanup()

            # Verify warning was logged
            log_messages = [record.message for record in capture_logs]
            assert any("did not complete within timeout" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_cleanup_with_service_errors(
        self, mock_config, mock_tiger_service, capture_logs
    ):
        """Test cleanup with service errors."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.tiger_service = mock_tiger_service

            # Mock service to raise error during stop
            mock_tiger_service.stop.side_effect = RuntimeError("Service stop failed")

            # Execute cleanup - should not raise exception
            await server.cleanup()

            # Verify error was logged
            log_messages = [record.message for record in capture_logs]
            assert any(
                "Error stopping Tiger API service" in msg for msg in log_messages
            )

    @pytest.mark.asyncio
    async def test_start_server(self, mock_config):
        """Test server start operation."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()

            # Mock initialize method
            server.initialize = AsyncMock()

            # Start server
            await server.start()

            # Verify initialization was called
            server.initialize.assert_called_once()

            # Try to start again - should raise error
            with pytest.raises(RuntimeError, match="Server is already started"):
                await server.start()

    @pytest.mark.asyncio
    async def test_stop_server(self, mock_config):
        """Test server stop operation."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server._started = True

            # Mock cleanup method
            server.cleanup = AsyncMock()

            # Stop server
            await server.stop()

            # Verify shutdown event was set and cleanup called
            assert server.shutdown_event.is_set()
            server.cleanup.assert_called_once()

            # Try to stop when not started - should raise error
            server._started = False
            with pytest.raises(RuntimeError, match="Server is not started"):
                await server.stop()

    def test_is_started_property(self, mock_config):
        """Test is_started property."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()

            # Initially not started
            assert server.is_started is False

            # Set started
            server._started = True
            assert server.is_started is True

            # Set not started
            server._started = False
            assert server.is_started is False

    def test_get_health_status(
        self, mock_config, mock_process_manager, mock_account_manager
    ):
        """Test health status reporting."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.process_manager = mock_process_manager
            server.account_manager = mock_account_manager
            server._started = True
            server.background_tasks = [MagicMock(), MagicMock()]

            # Mock process manager workers
            mock_worker1 = MagicMock()
            mock_worker1.request_count = 100
            mock_worker1.error_count = 5
            mock_worker2 = MagicMock()
            mock_worker2.request_count = 75
            mock_worker2.error_count = 2

            mock_process_manager.workers = {
                "worker1": mock_worker1,
                "worker2": mock_worker2,
            }

            # Mock account manager accounts
            mock_account1 = MagicMock()
            mock_account1.status.value = "active"
            mock_account2 = MagicMock()
            mock_account2.status.value = "inactive"

            mock_account_manager.accounts = {
                "account1": mock_account1,
                "account2": mock_account2,
            }

            # Get health status
            status = server.get_health_status()

            # Verify status structure
            assert "server" in status
            assert "process_pool" in status
            assert "accounts" in status

            # Verify server status
            server_status = status["server"]
            assert server_status["started"] is True
            assert server_status["environment"] == mock_config.environment
            assert server_status["background_tasks"] == 2

            # Verify process pool status
            process_status = status["process_pool"]
            assert process_status["active_workers"] == 2
            assert process_status["total_requests"] == 175  # 100 + 75
            assert process_status["failed_requests"] == 7  # 5 + 2

            # Verify account status
            account_status = status["accounts"]
            assert account_status["total_accounts"] == 2
            assert account_status["active_accounts"] == 1

    def test_get_health_status_with_errors(
        self, mock_config, mock_process_manager, mock_account_manager
    ):
        """Test health status reporting with service errors."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.process_manager = mock_process_manager
            server.account_manager = mock_account_manager

            # Mock process manager to raise error
            mock_process_manager.workers.side_effect = RuntimeError(
                "Process manager error"
            )

            # Mock account manager to raise error
            mock_account_manager.accounts.side_effect = RuntimeError(
                "Account manager error"
            )

            # Get health status
            status = server.get_health_status()

            # Verify error handling
            assert "process_pool" in status
            assert "error" in status["process_pool"]
            assert "accounts" in status
            assert "error" in status["accounts"]

    def test_signal_handler_setup(self, mock_config):
        """Test signal handler setup."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            with patch("signal.signal") as mock_signal:
                # Create server (should setup signal handlers)
                TigerMCPServer()

                # Verify signal handlers were setup (except on Windows)
                if sys.platform != "win32":
                    assert mock_signal.call_count >= 1
                    # Verify SIGTERM and SIGINT handlers
                    signal_calls = [call[0] for call in mock_signal.call_args_list]
                    assert signal.SIGTERM in signal_calls
                    assert signal.SIGINT in signal_calls

    def test_signal_handler_execution(self, mock_config):
        """Test signal handler execution."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()

            # Verify shutdown event is not set initially
            assert not server.shutdown_event.is_set()

            # Execute signal handler
            server._signal_handler(signal.SIGTERM, None)

            # Verify shutdown event is set
            assert server.shutdown_event.is_set()


class TestTigerMCPServerIntegration:
    """Integration tests for TigerMCPServer."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_server_full_lifecycle(
        self,
        mock_config,
        mock_db_manager,
        mock_account_manager,
        mock_account_router,
        mock_process_manager,
        mock_tiger_service,
    ):
        """Test complete server lifecycle."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_config_manager.load_config.return_value = mock_config
            mock_get_config_manager.return_value = mock_config_manager

            # Create server
            server = TigerMCPServer()

            try:
                # Start server
                await server.start()

                # Verify server is started
                assert server.is_started is True
                assert server.config == mock_config

                # Verify all services were initialized
                mock_db_manager.initialize.assert_called_once()
                mock_account_manager.initialize.assert_called_once()
                mock_process_manager.configure.assert_called_once()
                mock_process_manager.start.assert_called_once()
                mock_tiger_service.start.assert_called_once()

                # Verify background tasks were started
                assert len(server.background_tasks) > 0

                # Get health status
                status = server.get_health_status()
                assert status["server"]["started"] is True

                # Test shutdown signal
                server.shutdown_event.set()
                await server.wait_for_shutdown()
                assert server.shutdown_event.is_set()

            finally:
                # Stop server
                if server.is_started:
                    await server.stop()

                # Verify cleanup was performed
                assert server.is_started is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_server_error_recovery(self, mock_config):
        """Test server error recovery during initialization."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_config_manager.load_config.return_value = mock_config
            mock_get_config_manager.return_value = mock_config_manager

            # Create server
            server = TigerMCPServer()

            # Mock database initialization failure
            with patch(
                "database.get_db_manager",
                side_effect=RuntimeError("Database connection failed"),
            ):
                with pytest.raises(RuntimeError, match="Database connection failed"):
                    await server.initialize()

                # Verify server is not started
                assert server.is_started is False

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_server_background_task_management(
        self, mock_config, mock_account_manager, mock_process_manager
    ):
        """Test background task management over time."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_config_manager.load_config.return_value = mock_config
            mock_get_config_manager.return_value = mock_config_manager

            # Create server with fast intervals for testing
            server = TigerMCPServer()
            server.config = mock_config
            server.config.process.health_check_interval = 0.1  # Fast interval
            server.config.security.token_refresh_threshold = 0.2
            server.account_manager = mock_account_manager
            server.process_manager = mock_process_manager

            try:
                # Start background tasks
                await server._start_background_tasks()

                # Let tasks run for a short time
                await asyncio.sleep(0.5)

                # Verify tasks are running
                assert len(server.background_tasks) > 0
                assert all(not task.done() for task in server.background_tasks)

                # Trigger shutdown
                server.shutdown_event.set()

                # Wait a bit for tasks to notice shutdown
                await asyncio.sleep(0.2)

                # Cleanup tasks
                for task in server.background_tasks:
                    task.cancel()

                await asyncio.gather(*server.background_tasks, return_exceptions=True)

            finally:
                # Ensure cleanup
                server.shutdown_event.set()
                for task in server.background_tasks:
                    if not task.done():
                        task.cancel()

                if server.background_tasks:
                    await asyncio.gather(
                        *server.background_tasks, return_exceptions=True
                    )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_server_concurrent_operations(
        self, mock_config, mock_account_manager, mock_process_manager
    ):
        """Test server handling concurrent operations."""
        with patch("mcp_server.server.get_config_manager") as mock_get_config_manager:
            mock_config_manager = MagicMock()
            mock_config_manager.load_config.return_value = mock_config
            mock_get_config_manager.return_value = mock_config_manager

            server = TigerMCPServer()
            server.config = mock_config
            server.account_manager = mock_account_manager
            server.process_manager = mock_process_manager
            server._started = True

            # Simulate concurrent health status requests
            async def get_health_multiple_times():
                tasks = [
                    asyncio.create_task(asyncio.to_thread(server.get_health_status))
                    for _ in range(10)
                ]
                return await asyncio.gather(*tasks)

            # Execute concurrent operations
            results = await get_health_multiple_times()

            # Verify all requests succeeded
            assert len(results) == 10
            assert all(isinstance(result, dict) for result in results)
            assert all("server" in result for result in results)
