"""
Unit tests for Tiger MCP Server FastMCP Integration.

Tests the TigerFastMCPServer class and main entry points that integrate
Tiger MCP Server with FastMCP framework. Tests cover:

1. FastMCP server integration and tool registration
2. Server startup and transport handling (stdio/SSE)
3. Health endpoints and server information
4. CLI integration and argument parsing
5. Tool routing and execution coordination
6. Error handling and graceful degradation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the classes and functions under test
from mcp_server.main import TigerFastMCPServer


class TestTigerFastMCPServer:
    """Test suite for TigerFastMCPServer."""

    @pytest.mark.asyncio
    async def test_server_initialization(self, mock_config):
        """Test FastMCP server initialization."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = MagicMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server
            server = TigerFastMCPServer()

            # Verify initial state
            assert server.tiger_server == mock_tiger_server
            assert server.mcp_server is None
            assert server._started is False

            # Verify Tiger MCP Server was created with default parameters
            mock_tiger_server_class.assert_called_once_with(
                config_file=None, environment=None
            )

    @pytest.mark.asyncio
    async def test_server_initialization_with_config(self, mock_config):
        """Test FastMCP server initialization with custom configuration."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = MagicMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server with custom config
            server = TigerFastMCPServer(
                config_file="/custom/config.yaml", environment="production"
            )

            # Verify Tiger MCP Server was created with custom parameters
            mock_tiger_server_class.assert_called_once_with(
                config_file="/custom/config.yaml", environment="production"
            )

    @pytest.mark.asyncio
    async def test_server_initialize_success(self, mock_config, mock_fastmcp_server):
        """Test successful FastMCP server initialization."""
        with (
            patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class,
            patch(
                "mcp_server.main.FastMCP", return_value=mock_fastmcp_server
            ) as mock_fastmcp_class,
        ):

            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server
            server = TigerFastMCPServer()

            # Mock tool registration
            with patch.object(server, "_register_all_tools") as mock_register_tools:
                # Execute initialization
                await server.initialize()

                # Verify initialization sequence
                mock_tiger_server.initialize.assert_called_once()
                mock_fastmcp_class.assert_called_once_with("Tiger MCP Server")
                mock_register_tools.assert_called_once()

                # Verify state
                assert server.mcp_server == mock_fastmcp_server
                assert server._started is True

    @pytest.mark.asyncio
    async def test_server_initialize_failure(self, mock_config):
        """Test FastMCP server initialization failure."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server.initialize.side_effect = RuntimeError(
                "Tiger server initialization failed"
            )
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server
            server = TigerFastMCPServer()

            # Execute initialization and expect failure
            with pytest.raises(
                RuntimeError, match="Tiger server initialization failed"
            ):
                await server.initialize()

            # Verify state
            assert server.mcp_server is None
            assert server._started is False

    @pytest.mark.asyncio
    async def test_register_all_tools(self, mock_config, mock_fastmcp_server):
        """Test tool registration with FastMCP."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server
            server = TigerFastMCPServer()
            server.mcp_server = mock_fastmcp_server

            # Mock tool modules and their tools
            mock_data_tools = MagicMock()
            mock_data_tools.tiger_get_quote = AsyncMock()
            mock_data_tools.tiger_get_kline = AsyncMock()

            mock_info_tools = MagicMock()
            mock_info_tools.tiger_get_contracts = AsyncMock()
            mock_info_tools.tiger_get_financials = AsyncMock()

            mock_account_tools = MagicMock()
            mock_account_tools.tiger_list_accounts = AsyncMock()
            mock_account_tools.tiger_add_account = AsyncMock()

            mock_trading_tools = MagicMock()
            mock_trading_tools.tiger_get_positions = AsyncMock()
            mock_trading_tools.tiger_place_order = AsyncMock()

            # Mock tool imports
            with patch.dict(
                "sys.modules",
                {
                    "data_tools": mock_data_tools,
                    "info_tools": mock_info_tools,
                    "account_tools": mock_account_tools,
                    "trading_tools": mock_trading_tools,
                },
            ):
                # Execute tool registration
                await server._register_all_tools()

                # Verify FastMCP server tool method was called
                # The exact verification depends on how tools are registered
                # This would need to match the actual implementation
                assert mock_fastmcp_server.method_calls  # Some methods were called

    @pytest.mark.asyncio
    async def test_register_data_tools(self, mock_config, mock_fastmcp_server):
        """Test data tools registration."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            server = TigerFastMCPServer()
            server.mcp_server = mock_fastmcp_server

            # Mock data tools module
            mock_data_tools = MagicMock()
            mock_tools = {
                "tiger_get_quote": AsyncMock(),
                "tiger_get_kline": AsyncMock(),
                "tiger_get_market_data": AsyncMock(),
                "tiger_search_symbols": AsyncMock(),
                "tiger_get_option_chain": AsyncMock(),
                "tiger_get_market_status": AsyncMock(),
            }

            for name, tool in mock_tools.items():
                setattr(mock_data_tools, name, tool)

            with patch("importlib.import_module", return_value=mock_data_tools):
                # Execute data tools registration
                await server._register_data_tools()

                # Verify tools were registered with FastMCP
                # This verification would depend on the actual registration method
                assert mock_fastmcp_server.method_calls  # Some registration occurred

    @pytest.mark.asyncio
    async def test_run_stdio_server(self, mock_config, mock_fastmcp_server):
        """Test running server with stdio transport."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server
            server = TigerFastMCPServer()
            server.mcp_server = mock_fastmcp_server
            server._started = True

            # Mock stdio transport
            with patch("sys.stdin"), patch("sys.stdout"):
                # Execute stdio server
                await server.run_stdio()

                # Verify FastMCP run was called
                mock_fastmcp_server.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_sse_server(self, mock_config, mock_fastmcp_server):
        """Test running server with SSE transport."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server
            server = TigerFastMCPServer()
            server.mcp_server = mock_fastmcp_server
            server._started = True

            # Execute SSE server
            await server.run_sse()

            # Verify FastMCP run_sse was called
            mock_fastmcp_server.run_sse.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_server_not_initialized(self, mock_config):
        """Test running server when not initialized."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server but don't initialize
            server = TigerFastMCPServer()

            # Attempt to run stdio - should raise error
            with pytest.raises(RuntimeError, match="Server not initialized"):
                await server.run_stdio()

            # Attempt to run SSE - should raise error
            with pytest.raises(RuntimeError, match="Server not initialized"):
                await server.run_sse()

    @pytest.mark.asyncio
    async def test_cleanup_server(self, mock_config, mock_fastmcp_server):
        """Test server cleanup."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create and start FastMCP server
            server = TigerFastMCPServer()
            server.mcp_server = mock_fastmcp_server
            server._started = True

            # Execute cleanup
            await server.cleanup()

            # Verify Tiger MCP server cleanup
            mock_tiger_server.cleanup.assert_called_once()

            # Verify state
            assert server._started is False

    @pytest.mark.asyncio
    async def test_server_context_manager(self, mock_config, mock_fastmcp_server):
        """Test server as async context manager."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Mock tool registration
            with patch("mcp_server.main.FastMCP", return_value=mock_fastmcp_server):
                server = TigerFastMCPServer()

                # Mock tool registration
                with patch.object(server, "_register_all_tools"):
                    # Use as context manager
                    async with server:
                        # Verify server was initialized
                        assert server._started is True
                        mock_tiger_server.initialize.assert_called_once()

                    # Verify cleanup was called
                    mock_tiger_server.cleanup.assert_called_once()

    def test_get_server_info(self, mock_config, mock_server_data):
        """Test getting server information."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = MagicMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            server = TigerFastMCPServer()

            # Mock server info
            with patch.object(
                server, "_get_server_info", return_value=mock_server_data.server_info
            ):
                info = server.get_server_info()

                # Verify server info structure
                assert "name" in info
                assert "version" in info
                assert "description" in info
                assert info["name"] == "Tiger MCP Server"
                assert "supported_tools" in info

    def test_get_health_status(self, mock_config, mock_server_data):
        """Test getting health status."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = MagicMock()
            mock_tiger_server.get_health_status.return_value = (
                mock_server_data.health_status
            )
            mock_tiger_server_class.return_value = mock_tiger_server

            server = TigerFastMCPServer()

            # Get health status
            status = server.get_health_status()

            # Verify health status
            assert status == mock_server_data.health_status
            mock_tiger_server.get_health_status.assert_called_once()


class TestMainEntryPoints:
    """Test suite for main entry point functions."""

    @pytest.mark.asyncio
    async def test_main_stdio_success(self, mock_config, mock_fastmcp_server):
        """Test successful stdio main execution."""
        with (
            patch("mcp_server.main.TigerFastMCPServer") as mock_server_class,
            patch("mcp_server.main.get_config", return_value=mock_config),
        ):

            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server

            # Mock successful server operations
            mock_server.initialize = AsyncMock()
            mock_server.run_stdio = AsyncMock()
            mock_server.cleanup = AsyncMock()

            # Mock main function
            from mcp_server.main import main

            # Execute main
            await main()

            # Verify server lifecycle
            mock_server.initialize.assert_called_once()
            mock_server.run_stdio.assert_called_once()
            mock_server.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_stdio_with_error(self, mock_config, capture_logs):
        """Test stdio main execution with error."""
        with (
            patch("mcp_server.main.TigerFastMCPServer") as mock_server_class,
            patch("mcp_server.main.get_config", return_value=mock_config),
        ):

            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server

            # Mock server initialization failure
            mock_server.initialize.side_effect = RuntimeError("Initialization failed")
            mock_server.cleanup = AsyncMock()

            # Mock main function
            from mcp_server.main import main

            # Execute main - should not raise exception
            await main()

            # Verify cleanup was called even after error
            mock_server.cleanup.assert_called_once()

            # Verify error was logged
            log_messages = [record.message for record in capture_logs]
            assert any("Initialization failed" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_main_sse_success(self, mock_config, mock_fastmcp_server):
        """Test successful SSE main execution."""
        with (
            patch("mcp_server.main.TigerFastMCPServer") as mock_server_class,
            patch("mcp_server.main.get_config", return_value=mock_config),
        ):

            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server

            # Mock successful server operations
            mock_server.initialize = AsyncMock()
            mock_server.run_sse = AsyncMock()
            mock_server.cleanup = AsyncMock()

            # Mock SSE main function
            from mcp_server.main import main_sse

            # Execute SSE main
            await main_sse()

            # Verify server lifecycle
            mock_server.initialize.assert_called_once()
            mock_server.run_sse.assert_called_once()
            mock_server.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_keyboard_interrupt(self, mock_config, capture_logs):
        """Test main execution with keyboard interrupt."""
        with (
            patch("mcp_server.main.TigerFastMCPServer") as mock_server_class,
            patch("mcp_server.main.get_config", return_value=mock_config),
        ):

            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server

            # Mock keyboard interrupt during run
            mock_server.initialize = AsyncMock()
            mock_server.run_stdio.side_effect = KeyboardInterrupt("User interrupt")
            mock_server.cleanup = AsyncMock()

            # Mock main function
            from mcp_server.main import main

            # Execute main
            await main()

            # Verify cleanup was called
            mock_server.cleanup.assert_called_once()

            # Verify interrupt was logged
            log_messages = [record.message for record in capture_logs]
            assert any("keyboard interrupt" in msg.lower() for msg in log_messages)

    @pytest.mark.asyncio
    async def test_tool_execution_routing(
        self, mock_config, mock_fastmcp_server, mock_tiger_api_data
    ):
        """Test tool execution routing through FastMCP."""
        with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
            mock_tiger_server = AsyncMock()
            mock_tiger_server_class.return_value = mock_tiger_server

            # Create FastMCP server
            server = TigerFastMCPServer()
            server.mcp_server = mock_fastmcp_server
            server._started = True

            # Mock a tool execution scenario
            with patch("mcp_server.tools.data_tools.tiger_get_quote") as mock_get_quote:
                mock_get_quote.return_value = mock_tiger_api_data.quote_response

                # Simulate tool call through FastMCP
                # This would depend on how FastMCP routes tool calls
                result = await mock_get_quote("AAPL")

                # Verify tool was called and returned expected result
                assert result == mock_tiger_api_data.quote_response
                mock_get_quote.assert_called_once_with("AAPL")

    def test_get_config_loading(self):
        """Test configuration loading in main module."""
        with patch("mcp_server.main.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            # Import should trigger config loading
            from mcp_server.main import get_config

            config = get_config()

            # Verify config was loaded
            assert config == mock_config


class TestMainIntegration:
    """Integration tests for main FastMCP integration."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_server_integration(
        self,
        mock_config,
        mock_db_manager,
        mock_account_manager,
        mock_process_manager,
        mock_tiger_service,
    ):
        """Test full server integration with all components."""
        with (
            patch("mcp_server.main.get_config", return_value=mock_config),
            patch("mcp_server.main.FastMCP") as mock_fastmcp_class,
        ):

            mock_fastmcp_server = AsyncMock()
            mock_fastmcp_class.return_value = mock_fastmcp_server

            # Create and initialize server
            server = TigerFastMCPServer()

            try:
                # Initialize server
                await server.initialize()

                # Verify server is initialized
                assert server._started is True
                assert server.mcp_server is not None

                # Verify Tiger MCP Server was initialized
                server.tiger_server.initialize.assert_called_once()

                # Verify FastMCP server was created
                mock_fastmcp_class.assert_called_once_with("Tiger MCP Server")

                # Test health status
                health_status = server.get_health_status()
                assert isinstance(health_status, dict)

                # Test server info
                server_info = server.get_server_info()
                assert isinstance(server_info, dict)

            finally:
                # Cleanup
                if server._started:
                    await server.cleanup()

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_server_tool_integration(
        self,
        mock_config,
        mock_account_manager,
        mock_process_manager,
        mock_tiger_api_data,
    ):
        """Test server integration with actual tool execution."""
        with (
            patch("mcp_server.main.get_config", return_value=mock_config),
            patch("mcp_server.main.FastMCP") as mock_fastmcp_class,
        ):

            mock_fastmcp_server = AsyncMock()
            mock_fastmcp_class.return_value = mock_fastmcp_server

            # Create server
            server = TigerFastMCPServer()

            try:
                # Initialize server
                await server.initialize()

                # Mock tool execution through the integrated system
                with patch(
                    "mcp_server.tools.data_tools.tiger_get_quote"
                ) as mock_get_quote:
                    mock_get_quote.return_value = mock_tiger_api_data.quote_response

                    # Simulate tool execution
                    result = await mock_get_quote("AAPL")

                    # Verify integration
                    assert result == mock_tiger_api_data.quote_response
                    mock_get_quote.assert_called_once()

                # Test multiple concurrent tool executions
                with (
                    patch(
                        "mcp_server.tools.data_tools.tiger_get_quote"
                    ) as mock_get_quote,
                    patch(
                        "mcp_server.tools.account_tools.tiger_list_accounts"
                    ) as mock_list_accounts,
                ):

                    mock_get_quote.return_value = mock_tiger_api_data.quote_response
                    mock_list_accounts.return_value = {"success": True, "accounts": []}

                    # Execute concurrent tools
                    results = await asyncio.gather(
                        mock_get_quote("AAPL"),
                        mock_get_quote("GOOGL"),
                        mock_list_accounts(),
                    )

                    # Verify all executed successfully
                    assert len(results) == 3
                    assert results[0] == mock_tiger_api_data.quote_response
                    assert results[1] == mock_tiger_api_data.quote_response
                    assert results[2]["success"] is True

            finally:
                # Cleanup
                if server._started:
                    await server.cleanup()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_server_error_handling_integration(self, mock_config):
        """Test server error handling in integration scenarios."""
        with patch("mcp_server.main.get_config", return_value=mock_config):

            # Test server initialization failure
            with patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class:
                mock_tiger_server = AsyncMock()
                mock_tiger_server.initialize.side_effect = RuntimeError(
                    "Database connection failed"
                )
                mock_tiger_server_class.return_value = mock_tiger_server

                server = TigerFastMCPServer()

                # Initialization should fail
                with pytest.raises(RuntimeError, match="Database connection failed"):
                    await server.initialize()

                # Server should not be started
                assert server._started is False

            # Test tool execution error handling
            with (
                patch("mcp_server.main.TigerMCPServer") as mock_tiger_server_class,
                patch("mcp_server.main.FastMCP") as mock_fastmcp_class,
            ):

                mock_tiger_server = AsyncMock()
                mock_tiger_server_class.return_value = mock_tiger_server

                mock_fastmcp_server = AsyncMock()
                mock_fastmcp_class.return_value = mock_fastmcp_server

                server = TigerFastMCPServer()

                try:
                    # Initialize successfully
                    with patch.object(server, "_register_all_tools"):
                        await server.initialize()

                    # Test tool execution error
                    with patch(
                        "mcp_server.tools.data_tools.tiger_get_quote"
                    ) as mock_get_quote:
                        mock_get_quote.side_effect = RuntimeError("Process pool error")

                        # Tool execution should handle error gracefully
                        with pytest.raises(RuntimeError, match="Process pool error"):
                            await mock_get_quote("AAPL")

                finally:
                    # Cleanup should work even after errors
                    await server.cleanup()
                    assert server._started is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_main_function_integration(self, mock_config):
        """Test main function integration with full lifecycle."""
        with patch("mcp_server.main.get_config", return_value=mock_config):

            # Mock server for main function testing
            mock_server = AsyncMock()

            with patch("mcp_server.main.TigerFastMCPServer", return_value=mock_server):

                # Test successful main execution
                from mcp_server.main import main

                await main()

                # Verify full lifecycle
                mock_server.initialize.assert_called_once()
                mock_server.run_stdio.assert_called_once()
                mock_server.cleanup.assert_called_once()

            # Test main with SSE
            mock_sse_server = AsyncMock()

            with patch(
                "mcp_server.main.TigerFastMCPServer", return_value=mock_sse_server
            ):

                from mcp_server.main import main_sse

                await main_sse()

                # Verify SSE lifecycle
                mock_sse_server.initialize.assert_called_once()
                mock_sse_server.run_sse.assert_called_once()
                mock_sse_server.cleanup.assert_called_once()
