"""
Unit tests for Tiger MCP Data Tools.

Tests all 6 data fetching tools:
1. tiger_get_quote - Real-time stock quotes
2. tiger_get_kline - Historical K-line data
3. tiger_get_market_data - Comprehensive market data
4. tiger_search_symbols - Symbol search functionality
5. tiger_get_option_chain - Options chain data
6. tiger_get_market_status - Market status information
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

# Import the tools under test
from mcp_server.tools.data_tools import (
    tiger_get_kline,
    tiger_get_market_data,
    tiger_get_market_status,
    tiger_get_option_chain,
    tiger_get_quote,
    tiger_search_symbols,
)


class TestDataTools:
    """Test suite for Tiger MCP data tools."""

    @pytest.mark.asyncio
    async def test_tiger_get_quote_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful quote retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.quote_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_quote("AAPL")

        # Verify results
        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.data is not None
        assert result.data["latest_price"] == 150.25
        assert result.data["symbol"] == "AAPL"
        assert result.error is None

        # Verify calls
        mock_account_router.route_data_request.assert_called_once()
        mock_process_manager.execute_task.assert_called_once()

        # Verify task parameters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][0] == "test_account_123"  # account_id
        assert call_args[0][1] == "get_quote"  # method
        assert call_args[0][2] == ["AAPL"]  # args

    @pytest.mark.asyncio
    async def test_tiger_get_quote_invalid_symbol(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test quote retrieval with invalid symbol."""
        # Setup mocks for error response
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.quote_error_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_quote("INVALID")

        # Verify error response
        assert result.success is False
        assert result.symbol == "INVALID"
        assert result.data is None
        assert result.error == "Symbol not found: INVALID"

    @pytest.mark.asyncio
    async def test_tiger_get_quote_process_error(
        self, mock_process_manager, mock_account_router
    ):
        """Test quote retrieval with process execution error."""
        # Setup mocks for process error
        mock_process_manager.execute_task.side_effect = RuntimeError(
            "Process execution failed"
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_quote("AAPL")

        # Verify error handling
        assert result.success is False
        assert result.symbol == "AAPL"
        assert result.data is None
        assert "Process execution failed" in result.error

    @pytest.mark.asyncio
    async def test_tiger_get_quote_no_account(
        self, mock_process_manager, mock_account_router
    ):
        """Test quote retrieval with no available account."""
        # Setup mocks for no account
        mock_account_router.route_data_request.side_effect = RuntimeError(
            "No account available for data requests"
        )

        # Execute tool
        result = await tiger_get_quote("AAPL")

        # Verify error handling
        assert result.success is False
        assert result.symbol == "AAPL"
        assert result.data is None
        assert "No account available" in result.error

    @pytest.mark.asyncio
    async def test_tiger_get_kline_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful K-line data retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.kline_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_kline("AAPL", "1h", 10)

        # Verify results
        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.period == "1h"
        assert result.count == 10
        assert result.data is not None
        assert len(result.data) == 10
        assert all("time" in item and "open" in item for item in result.data)

        # Verify call parameters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "get_kline"
        assert call_args[0][2] == ["AAPL", "1h", 10]

    @pytest.mark.asyncio
    async def test_tiger_get_kline_with_defaults(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test K-line data retrieval with default parameters."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.kline_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with minimal parameters
        result = await tiger_get_kline("AAPL")

        # Verify results
        assert result.success is True
        assert result.symbol == "AAPL"

        # Verify default parameters were used
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][2][1] == "1d"  # default period
        assert call_args[0][2][2] == 100  # default count

    @pytest.mark.asyncio
    async def test_tiger_get_market_data_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful market data retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.market_data_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_market_data(["AAPL", "GOOGL"])

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "quotes" in result.data
        assert len(result.data["quotes"]) == 2
        assert result.data["market_status"] == "TRADING"

        # Verify call parameters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "get_market_data"
        assert call_args[0][2] == [["AAPL", "GOOGL"]]

    @pytest.mark.asyncio
    async def test_tiger_search_symbols_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful symbol search."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.symbol_search_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_search_symbols("AAPL")

        # Verify results
        assert result.success is True
        assert result.query == "AAPL"
        assert result.data is not None
        assert "symbols" in result.data
        assert len(result.data["symbols"]) >= 1
        assert any(symbol["symbol"] == "AAPL" for symbol in result.data["symbols"])

        # Verify call parameters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "search_symbols"
        assert call_args[0][2] == ["AAPL"]

    @pytest.mark.asyncio
    async def test_tiger_search_symbols_with_market_filter(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test symbol search with market filter."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.symbol_search_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with market filter
        result = await tiger_search_symbols("AAPL", "US", "STOCK")

        # Verify results
        assert result.success is True

        # Verify call parameters include filters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][2] == ["AAPL", "US", "STOCK"]

    @pytest.mark.asyncio
    async def test_tiger_get_option_chain_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful option chain retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.option_chain_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_option_chain("AAPL")

        # Verify results
        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.data is not None
        assert "options" in result.data
        assert "strikes" in result.data
        assert "expiry_dates" in result.data
        assert len(result.data["options"]) > 0

        # Verify option data structure
        option = result.data["options"][0]
        assert all(key in option for key in ["strike", "expiry", "type", "bid", "ask"])

    @pytest.mark.asyncio
    async def test_tiger_get_option_chain_with_filters(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test option chain retrieval with expiry and strike filters."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.option_chain_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with filters
        expiry_date = "2024-02-15"
        result = await tiger_get_option_chain("AAPL", expiry_date, 150.0)

        # Verify results
        assert result.success is True

        # Verify call parameters include filters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][2] == ["AAPL", expiry_date, 150.0]

    @pytest.mark.asyncio
    async def test_tiger_get_market_status_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful market status retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.market_status_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_market_status()

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "status" in result.data
        assert "market" in result.data
        assert result.data["status"] in [
            "TRADING",
            "CLOSED",
            "PRE_MARKET",
            "AFTER_HOURS",
        ]
        assert "open_time" in result.data
        assert "close_time" in result.data

        # Verify call parameters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "get_market_status"

    @pytest.mark.asyncio
    async def test_tiger_get_market_status_with_market(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test market status retrieval for specific market."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.market_status_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with market parameter
        result = await tiger_get_market_status("HK")

        # Verify results
        assert result.success is True

        # Verify call parameters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][2] == ["HK"]

    @pytest.mark.asyncio
    async def test_data_tool_timeout_handling(
        self, mock_process_manager, mock_account_router
    ):
        """Test timeout handling in data tools."""
        # Setup mocks for timeout
        mock_process_manager.execute_task.side_effect = asyncio.TimeoutError(
            "Task timed out"
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_quote("AAPL")

        # Verify timeout handling
        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_data_tool_network_error_handling(
        self, mock_process_manager, mock_account_router
    ):
        """Test network error handling in data tools."""
        # Setup mocks for network error
        mock_process_manager.execute_task.side_effect = ConnectionError(
            "Network unreachable"
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_market_data(["AAPL"])

        # Verify network error handling
        assert result.success is False
        assert "network" in result.error.lower() or "connection" in result.error.lower()

    @pytest.mark.asyncio
    async def test_data_tool_rate_limit_handling(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test rate limit error handling."""
        # Setup mocks for rate limit error
        rate_limit_response = mock_tiger_api_data.get_error_response("rate_limit")
        mock_process_manager.execute_task.return_value = rate_limit_response
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_search_symbols("AAPL")

        # Verify rate limit handling
        assert result.success is False
        assert "rate limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_concurrent_data_requests(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test concurrent data tool requests."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.quote_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute multiple concurrent requests
        tasks = [
            tiger_get_quote("AAPL"),
            tiger_get_quote("GOOGL"),
            tiger_get_quote("MSFT"),
        ]
        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert all(result.success for result in results)
        assert len(results) == 3

        # Verify process manager was called for each request
        assert mock_process_manager.execute_task.call_count == 3

    @pytest.mark.parametrize(
        "symbol,expected_valid",
        [
            ("AAPL", True),
            ("GOOGL", True),
            ("MSFT", True),
            ("", False),
            ("INVALID_VERY_LONG_SYMBOL_NAME", False),
            ("123", False),
        ],
    )
    @pytest.mark.asyncio
    async def test_symbol_validation(
        self,
        symbol,
        expected_valid,
        mock_process_manager,
        mock_account_router,
        mock_tiger_api_data,
    ):
        """Test symbol validation in data tools."""
        if expected_valid:
            # Setup for valid symbol
            mock_process_manager.execute_task.return_value = (
                mock_tiger_api_data.quote_response
            )
            mock_account_router.route_data_request.return_value = "test_account_123"

            result = await tiger_get_quote(symbol)
            assert result.success is True
        else:
            # Invalid symbols should be handled gracefully
            result = await tiger_get_quote(symbol)
            # Either handled by validation or by API error response
            if not result.success:
                assert result.error is not None


class TestDataToolsIntegration:
    """Integration tests for data tools with process pool."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_tools_with_real_process_pool_mock(
        self, mock_account_manager, mock_tiger_api_data
    ):
        """Test data tools with realistic process pool interaction."""
        with patch(
            "mcp_server.tools.data_tools.get_process_manager"
        ) as mock_get_process_manager:
            # Create a more realistic process manager mock
            mock_process_manager = AsyncMock()
            mock_get_process_manager.return_value = mock_process_manager

            # Setup realistic process pool behavior
            mock_process_manager.execute_task.return_value = (
                mock_tiger_api_data.quote_response
            )

            with patch(
                "mcp_server.tools.data_tools.get_account_router"
            ) as mock_get_router:
                mock_router = AsyncMock()
                mock_router.route_data_request.return_value = "test_account_123"
                mock_get_router.return_value = mock_router

                # Execute tool
                result = await tiger_get_quote("AAPL")

                # Verify integration
                assert result.success is True
                assert mock_process_manager.execute_task.called
                assert mock_router.route_data_request.called

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_data_tools_stress_test(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Stress test with multiple concurrent data tool requests."""
        # Setup mocks for stress test
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.quote_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Create many concurrent requests
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"] * 10
        tasks = [tiger_get_quote(symbol) for symbol in symbols]

        # Execute all requests
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()

        # Verify results
        successful_results = [
            r for r in results if not isinstance(r, Exception) and r.success
        ]
        assert len(successful_results) == len(symbols)

        # Verify performance (should complete within reasonable time)
        execution_time = end_time - start_time
        assert execution_time < 10.0  # Should complete within 10 seconds

        logger.info(
            f"Stress test completed {len(symbols)} requests in {execution_time:.2f} seconds"
        )
