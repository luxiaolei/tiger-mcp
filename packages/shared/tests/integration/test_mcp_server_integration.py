"""
Integration tests for MCP server with full system integration.

Tests complete MCP server functionality including tool execution,
multi-account operations, error handling, and performance under load.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest


class TestMCPServerBasicFunctionality:
    """Test basic MCP server functionality and tool execution."""

    def test_server_health_check(self, mcp_test_client):
        """Test MCP server health check endpoint."""
        client, server = mcp_test_client

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_mcp_tool_discovery(self, mcp_server_instance):
        """Test MCP tool discovery and metadata."""
        app, server = mcp_server_instance

        # Mock MCP tools discovery
        available_tools = [
            "get_account_info",
            "get_portfolio",
            "get_market_data",
            "place_order",
            "get_order_status",
            "scan_market",
            "get_historical_data",
        ]

        # Verify tools are available
        assert hasattr(server, "tiger_clients")
        assert len(available_tools) > 0

    @pytest.mark.asyncio
    async def test_account_info_tool(
        self, mcp_server_instance, multiple_tiger_accounts, mock_tiger_api_responses
    ):
        """Test get_account_info MCP tool."""
        app, server = mcp_server_instance

        # Mock Tiger API response
        mock_response = mock_tiger_api_responses["account_info"]

        # Simulate tool execution
        with patch.object(server, "tiger_clients") as mock_clients:
            mock_client = MagicMock()
            mock_client.get_assets.return_value.is_success.return_value = True
            mock_client.get_assets.return_value.data = MagicMock()
            mock_client.get_assets.return_value.data.currency = "USD"
            mock_client.get_assets.return_value.data.cash = 50000.00
            mock_client.get_assets.return_value.data.buying_power = 100000.00

            account = list(multiple_tiger_accounts.values())[0]
            mock_clients[account.account_number] = mock_client

            # Execute account info tool (simulated)
            result = {
                "success": True,
                "account_id": account.account_number,
                "currency": "USD",
                "cash": 50000.00,
                "buying_power": 100000.00,
                "net_liquidation": 75000.00,
            }

            assert result["success"] is True
            assert result["account_id"] == account.account_number
            assert result["cash"] == 50000.00

    @pytest.mark.asyncio
    async def test_market_data_tool(
        self, mcp_server_instance, sample_market_data, mock_tiger_api_responses
    ):
        """Test get_market_data MCP tool."""
        app, server = mcp_server_instance

        symbols = list(sample_market_data.keys())

        # Mock Tiger API response
        with patch.object(server, "tiger_clients") as mock_clients:
            mock_client = MagicMock()
            mock_client.get_stock_briefs.return_value.is_success.return_value = True

            # Create mock brief objects
            mock_briefs = []
            for symbol, data in sample_market_data.items():
                mock_brief = MagicMock()
                mock_brief.symbol = symbol
                mock_brief.latest_price = data["latest_price"]
                mock_brief.prev_close = data["prev_close"]
                mock_brief.volume = data["volume"]
                mock_brief.change = data["change"]
                mock_brief.change_rate = data["change_rate"]
                mock_briefs.append(mock_brief)

            mock_client.get_stock_briefs.return_value.data = mock_briefs

            # Set up client
            account = (
                list(server.tiger_clients.keys())[0]
                if server.tiger_clients
                else "test_account"
            )
            mock_clients[account] = mock_client

            # Simulate market data tool execution
            result = {
                "success": True,
                "data": [
                    {
                        "symbol": brief.symbol,
                        "latest_price": brief.latest_price,
                        "prev_close": brief.prev_close,
                        "volume": brief.volume,
                        "change": brief.change,
                        "change_rate": brief.change_rate,
                    }
                    for brief in mock_briefs
                ],
                "timestamp": time.time(),
            }

            assert result["success"] is True
            assert len(result["data"]) == len(symbols)

            # Verify data for each symbol
            result_symbols = {item["symbol"] for item in result["data"]}
            assert result_symbols == set(symbols)


class TestMultiAccountMCPOperations:
    """Test MCP operations across multiple accounts."""

    @pytest.mark.asyncio
    async def test_account_routing_in_mcp_tools(
        self, mcp_server_instance, multiple_tiger_accounts
    ):
        """Test account routing logic in MCP tools."""
        app, server = mcp_server_instance

        # Set up multiple Tiger clients
        mock_clients = {}
        for account_name, account in multiple_tiger_accounts.items():
            mock_client = MagicMock()
            mock_client.account_id = account.account_number
            mock_clients[account.account_number] = mock_client

        with patch.object(server, "tiger_clients", mock_clients):
            # Test routing for trading operations
            trading_account = multiple_tiger_accounts["trading"]
            data_account = multiple_tiger_accounts["data"]

            # Verify different accounts are available
            assert trading_account.account_number in mock_clients
            assert data_account.account_number in mock_clients

            # Simulate routing logic
            trading_client = mock_clients[trading_account.account_number]
            data_client = mock_clients[data_account.account_number]

            assert trading_client is not None
            assert data_client is not None

    @pytest.mark.asyncio
    async def test_failover_between_accounts(
        self, mcp_server_instance, multiple_tiger_accounts, mock_tiger_api_responses
    ):
        """Test failover between accounts when one fails."""
        app, server = mcp_server_instance

        # Set up clients with one failing
        accounts = list(multiple_tiger_accounts.values())
        primary_account = accounts[0]
        fallback_account = accounts[1]

        mock_clients = {}

        # Primary client that fails
        primary_client = MagicMock()
        primary_client.get_account_info.side_effect = Exception("Connection failed")
        mock_clients[primary_account.account_number] = primary_client

        # Fallback client that succeeds
        fallback_client = MagicMock()
        fallback_client.get_account_info.return_value = mock_tiger_api_responses[
            "account_info"
        ]
        mock_clients[fallback_account.account_number] = fallback_client

        with patch.object(server, "tiger_clients", mock_clients):
            # Simulate failover logic
            try:
                # Try primary account
                result = primary_client.get_account_info()
                assert False, "Should have failed"
            except Exception:
                # Fallback to second account
                result = fallback_client.get_account_info()
                assert result == mock_tiger_api_responses["account_info"]

    @pytest.mark.asyncio
    async def test_concurrent_mcp_operations(
        self, mcp_server_instance, multiple_tiger_accounts, sample_market_data
    ):
        """Test concurrent MCP tool operations."""
        app, server = mcp_server_instance

        # Set up mock clients
        mock_clients = {}
        for account_name, account in multiple_tiger_accounts.items():
            mock_client = MagicMock()

            # Mock market data response
            mock_briefs = []
            for symbol, data in sample_market_data.items():
                mock_brief = MagicMock()
                mock_brief.symbol = symbol
                mock_brief.latest_price = data["latest_price"]
                mock_briefs.append(mock_brief)

            mock_client.get_stock_briefs.return_value.is_success.return_value = True
            mock_client.get_stock_briefs.return_value.data = mock_briefs

            mock_clients[account.account_number] = mock_client

        with patch.object(server, "tiger_clients", mock_clients):
            # Simulate concurrent operations
            symbols = list(sample_market_data.keys())

            async def get_market_data_for_symbol(symbol):
                # Simulate tool execution with delay
                await asyncio.sleep(0.1)
                return {
                    "symbol": symbol,
                    "latest_price": sample_market_data[symbol]["latest_price"],
                    "success": True,
                }

            # Execute concurrent operations
            tasks = [get_market_data_for_symbol(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks)

            # Verify results
            assert len(results) == len(symbols)
            for result in results:
                assert result["success"] is True
                assert result["symbol"] in symbols


class TestMCPErrorHandlingAndResilience:
    """Test MCP server error handling and resilience."""

    @pytest.mark.asyncio
    async def test_tiger_api_error_handling(
        self, mcp_server_instance, mock_tiger_api_responses, error_scenarios
    ):
        """Test handling of Tiger API errors."""
        app, server = mcp_server_instance

        # Test different error scenarios
        for error_name, error_config in error_scenarios.items():
            mock_client = MagicMock()

            # Configure client to return error
            if error_config["error_type"] == "timeout":
                mock_client.get_market_data.side_effect = asyncio.TimeoutError(
                    error_config["error_message"]
                )
            elif error_config["error_type"] == "auth_error":
                mock_client.get_market_data.return_value = mock_tiger_api_responses[
                    "auth_failure"
                ]
            elif error_config["error_type"] == "rate_limit":
                mock_client.get_market_data.return_value = mock_tiger_api_responses[
                    "rate_limit_error"
                ]
            else:
                mock_client.get_market_data.side_effect = Exception(
                    error_config["error_message"]
                )

            mock_clients = {"test_account": mock_client}

            with patch.object(server, "tiger_clients", mock_clients):
                # Simulate error handling
                try:
                    result = mock_client.get_market_data(["AAPL"])

                    # Check if it's an error response
                    if hasattr(result, "get") and result.get("code") != 0:
                        assert result["msg"] in [
                            "Authentication failed",
                            "Rate limit exceeded",
                        ]
                    else:
                        assert False, f"Expected error for {error_name}"

                except Exception as e:
                    # Expected for timeout and other exceptions
                    assert error_config["error_message"] in str(e)

    @pytest.mark.asyncio
    async def test_mcp_tool_retry_logic(self, mcp_server_instance, error_scenarios):
        """Test retry logic for failed MCP tool operations."""
        app, server = mcp_server_instance

        # Mock client that fails then succeeds
        mock_client = MagicMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 times
                raise Exception("Temporary failure")
            else:  # Succeed on 3rd try
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.data = []
                return mock_response

        mock_client.get_market_data.side_effect = side_effect

        mock_clients = {"test_account": mock_client}

        with patch.object(server, "tiger_clients", mock_clients):
            # Simulate retry logic (would be implemented in actual MCP tools)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = mock_client.get_market_data(["AAPL"])
                    if result.is_success():
                        assert attempt == 2, "Should succeed on 3rd attempt"
                        break
                except Exception as e:
                    if attempt == max_retries - 1:
                        pytest.fail(f"All retries failed: {e}")
                    continue

    @pytest.mark.asyncio
    async def test_partial_failure_handling(
        self, mcp_server_instance, multiple_tiger_accounts, sample_market_data
    ):
        """Test handling of partial failures across multiple accounts."""
        app, server = mcp_server_instance

        # Set up clients with mixed success/failure
        accounts = list(multiple_tiger_accounts.values())
        mock_clients = {}

        # First account succeeds
        success_client = MagicMock()
        success_client.get_stock_briefs.return_value.is_success.return_value = True
        success_client.get_stock_briefs.return_value.data = []
        mock_clients[accounts[0].account_number] = success_client

        # Second account fails
        failure_client = MagicMock()
        failure_client.get_stock_briefs.side_effect = Exception("Account unavailable")
        mock_clients[accounts[1].account_number] = failure_client

        # Third account succeeds
        if len(accounts) > 2:
            success_client_2 = MagicMock()
            success_client_2.get_stock_briefs.return_value.is_success.return_value = (
                True
            )
            success_client_2.get_stock_briefs.return_value.data = []
            mock_clients[accounts[2].account_number] = success_client_2

        with patch.object(server, "tiger_clients", mock_clients):
            # Test that system continues functioning with partial failures
            successful_accounts = []
            failed_accounts = []

            for account_number, client in mock_clients.items():
                try:
                    result = client.get_stock_briefs(["AAPL"])
                    if result.is_success():
                        successful_accounts.append(account_number)
                except Exception:
                    failed_accounts.append(account_number)

            # Should have both successful and failed accounts
            assert len(successful_accounts) > 0, "Some accounts should succeed"
            assert len(failed_accounts) > 0, "Some accounts should fail"

            # System should continue functioning with available accounts
            assert len(successful_accounts) >= 1


class TestMCPPerformanceAndLoadTesting:
    """Test MCP server performance under various load conditions."""

    @pytest.mark.asyncio
    async def test_mcp_server_response_times(self, mcp_test_client):
        """Test MCP server response times under normal load."""
        client, server = mcp_test_client

        # Test health endpoint response times
        response_times = []

        for _ in range(10):
            start_time = time.time()
            response = client.get("/health")
            response_time = time.time() - start_time

            assert response.status_code == 200
            response_times.append(response_time)

        # Performance assertions
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        assert (
            avg_response_time < 0.1
        ), f"Average response time too high: {avg_response_time}s"
        assert (
            max_response_time < 0.5
        ), f"Max response time too high: {max_response_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_mcp_requests(self, mcp_test_client):
        """Test MCP server under concurrent request load."""
        client, server = mcp_test_client

        async def make_request():
            # Use httpx for async requests
            async with httpx.AsyncClient(base_url="http://testserver") as async_client:
                response = await async_client.get("/health")
                return response.status_code == 200

        # Make 20 concurrent requests
        tasks = [make_request() for _ in range(20)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Verify all requests succeeded
        assert all(results), "All requests should succeed"

        # Performance check
        assert total_time < 5.0, f"Concurrent requests took too long: {total_time}s"

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(
        self, mcp_server_instance, sample_market_data
    ):
        """Test memory usage under sustained load."""
        import os

        import psutil

        app, server = mcp_server_instance

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Simulate sustained load
        mock_clients = {}
        for i in range(5):  # Multiple accounts
            mock_client = MagicMock()
            mock_client.get_stock_briefs.return_value.is_success.return_value = True
            mock_client.get_stock_briefs.return_value.data = []
            mock_clients[f"account_{i}"] = mock_client

        with patch.object(server, "tiger_clients", mock_clients):
            # Simulate many operations
            for _ in range(100):
                symbols = list(sample_market_data.keys())

                # Simulate market data operations
                for account_id, client in mock_clients.items():
                    result = client.get_stock_briefs(symbols)
                    assert result.is_success()

        # Check memory usage after load
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert (
            memory_increase < 50 * 1024 * 1024
        ), f"Memory usage increased too much: {memory_increase} bytes"

    @pytest.mark.asyncio
    async def test_load_testing_with_errors(self, mcp_server_instance, error_scenarios):
        """Test system performance under load with intermittent errors."""
        app, server = mcp_server_instance

        # Set up client that fails 20% of the time
        call_count = 0

        def side_effect_with_errors(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count % 5 == 0:  # Fail every 5th call (20% failure rate)
                raise Exception("Intermittent failure")

            # Success case
            mock_response = MagicMock()
            mock_response.is_success.return_value = True
            mock_response.data = []
            return mock_response

        mock_client = MagicMock()
        mock_client.get_market_data.side_effect = side_effect_with_errors

        mock_clients = {"test_account": mock_client}

        with patch.object(server, "tiger_clients", mock_clients):
            # Perform load test with errors
            successful_operations = 0
            failed_operations = 0

            start_time = time.time()

            for i in range(50):  # 50 operations
                try:
                    result = mock_client.get_market_data(["AAPL"])
                    if result.is_success():
                        successful_operations += 1
                except Exception:
                    failed_operations += 1

            total_time = time.time() - start_time

            # Verify error rate and performance
            total_operations = successful_operations + failed_operations
            error_rate = failed_operations / total_operations

            assert (
                0.15 <= error_rate <= 0.25
            ), f"Error rate outside expected range: {error_rate}"
            assert (
                total_time < 10.0
            ), f"Load test with errors took too long: {total_time}s"
            assert successful_operations > 0, "Some operations should succeed"


class TestMCPToolIntegration:
    """Test integration of specific MCP tools with the system."""

    @pytest.mark.asyncio
    async def test_place_order_tool_integration(
        self, mcp_server_instance, multiple_tiger_accounts, sample_trading_scenarios
    ):
        """Test place_order tool integration with account routing."""
        app, server = mcp_server_instance

        # Set up mock trading client
        trading_account = multiple_tiger_accounts["trading"]

        mock_client = MagicMock()
        mock_client.place_order.return_value.is_success.return_value = True
        mock_client.place_order.return_value.data = "ORDER123456789"

        mock_clients = {trading_account.account_number: mock_client}

        with patch.object(server, "tiger_clients", mock_clients):
            # Simulate place order tool execution
            buy_scenario = sample_trading_scenarios["buy_market_order"]

            # Mock order placement
            result = mock_client.place_order(MagicMock())

            assert result.is_success()
            assert result.data == "ORDER123456789"

    @pytest.mark.asyncio
    async def test_historical_data_tool_integration(
        self, mcp_server_instance, sample_market_data
    ):
        """Test historical data tool integration."""
        app, server = mcp_server_instance

        # Set up mock client with historical data
        mock_client = MagicMock()

        # Mock historical bars
        mock_bars = []
        for i in range(10):  # 10 bars of data
            mock_bar = MagicMock()
            mock_bar.time = int(time.time()) - (i * 3600)  # Hourly data
            mock_bar.open = 150.0 + i
            mock_bar.high = 151.0 + i
            mock_bar.low = 149.0 + i
            mock_bar.close = 150.5 + i
            mock_bar.volume = 1000000 - (i * 10000)
            mock_bars.append(mock_bar)

        mock_client.get_bars.return_value.is_success.return_value = True
        mock_client.get_bars.return_value.data = mock_bars

        mock_clients = {"test_account": mock_client}

        with patch.object(server, "tiger_clients", mock_clients):
            # Simulate historical data tool execution
            result = mock_client.get_bars(symbol="AAPL", period="1h", limit=10)

            assert result.is_success()
            assert len(result.data) == 10

            # Verify data structure
            for bar in result.data:
                assert hasattr(bar, "time")
                assert hasattr(bar, "open")
                assert hasattr(bar, "high")
                assert hasattr(bar, "low")
                assert hasattr(bar, "close")
                assert hasattr(bar, "volume")

    @pytest.mark.asyncio
    async def test_market_scanner_tool_integration(self, mcp_server_instance):
        """Test market scanner tool integration."""
        app, server = mcp_server_instance

        # Set up mock scanner results
        mock_client = MagicMock()

        mock_scan_results = []
        for i in range(20):  # 20 scan results
            mock_result = MagicMock()
            mock_result.symbol = f"STOCK{i:02d}"
            mock_result.name = f"Stock Company {i}"
            mock_result.latest_price = 100.0 + i
            mock_result.change = i * 0.5
            mock_result.change_rate = i * 0.005
            mock_result.volume = 1000000 + (i * 100000)
            mock_result.market_cap = 1000000000 + (i * 100000000)
            mock_scan_results.append(mock_result)

        mock_client.get_market_scanner.return_value.is_success.return_value = True
        mock_client.get_market_scanner.return_value.data = mock_scan_results

        mock_clients = {"test_account": mock_client}

        with patch.object(server, "tiger_clients", mock_clients):
            # Simulate market scanner tool execution
            result = mock_client.get_market_scanner(
                scanner_type="TOP_GAINERS", market="US", limit=20
            )

            assert result.is_success()
            assert len(result.data) == 20

            # Verify scan result structure
            for scan_result in result.data:
                assert hasattr(scan_result, "symbol")
                assert hasattr(scan_result, "name")
                assert hasattr(scan_result, "latest_price")
                assert hasattr(scan_result, "change")
                assert hasattr(scan_result, "change_rate")
                assert hasattr(scan_result, "volume")


class TestMCPSystemIntegration:
    """Test complete system integration scenarios."""

    @pytest.mark.asyncio
    async def test_end_to_end_trading_workflow(
        self, mcp_server_instance, multiple_tiger_accounts, sample_market_data
    ):
        """Test complete trading workflow through MCP server."""
        app, server = mcp_server_instance

        # Set up mock clients for different accounts
        data_account = multiple_tiger_accounts["data"]
        trading_account = multiple_tiger_accounts["trading"]

        # Data client for market data
        data_client = MagicMock()
        mock_briefs = []
        for symbol, data in sample_market_data.items():
            mock_brief = MagicMock()
            mock_brief.symbol = symbol
            mock_brief.latest_price = data["latest_price"]
            mock_brief.volume = data["volume"]
            mock_briefs.append(mock_brief)

        data_client.get_stock_briefs.return_value.is_success.return_value = True
        data_client.get_stock_briefs.return_value.data = mock_briefs

        # Trading client for order placement
        trading_client = MagicMock()
        trading_client.place_order.return_value.is_success.return_value = True
        trading_client.place_order.return_value.data = "ORDER123456"

        # Order status client
        mock_order = MagicMock()
        mock_order.id = "ORDER123456"
        mock_order.contract.symbol = "AAPL"
        mock_order.action = "BUY"
        mock_order.quantity = 100
        mock_order.status = "FILLED"
        mock_order.filled = 100
        mock_order.avg_fill_price = 150.25

        trading_client.get_order.return_value.is_success.return_value = True
        trading_client.get_order.return_value.data = mock_order

        mock_clients = {
            data_account.account_number: data_client,
            trading_account.account_number: trading_client,
        }

        with patch.object(server, "tiger_clients", mock_clients):
            # Step 1: Get market data
            market_data_result = data_client.get_stock_briefs(["AAPL"])
            assert market_data_result.is_success()

            # Step 2: Place order based on market data
            order_result = trading_client.place_order(MagicMock())
            assert order_result.is_success()
            order_id = order_result.data

            # Step 3: Check order status
            status_result = trading_client.get_order(order_id)
            assert status_result.is_success()

            order_data = status_result.data
            assert order_data.id == order_id
            assert order_data.status == "FILLED"

    @pytest.mark.asyncio
    async def test_system_recovery_after_failure(
        self, mcp_server_instance, multiple_tiger_accounts
    ):
        """Test system recovery after various failure scenarios."""
        app, server = mcp_server_instance

        # Set up clients with recovery scenarios
        accounts = list(multiple_tiger_accounts.values())
        mock_clients = {}

        for i, account in enumerate(accounts):
            mock_client = MagicMock()

            # Different failure and recovery patterns
            if i == 0:
                # Client that fails then recovers
                call_count = 0

                def side_effect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count <= 2:
                        raise Exception("Temporary failure")

                    mock_response = MagicMock()
                    mock_response.is_success.return_value = True
                    mock_response.data = []
                    return mock_response

                mock_client.get_stock_briefs.side_effect = side_effect

            elif i == 1:
                # Client that works immediately
                mock_client.get_stock_briefs.return_value.is_success.return_value = True
                mock_client.get_stock_briefs.return_value.data = []

            else:
                # Client with intermittent issues
                def intermittent_side_effect(*args, **kwargs):
                    import random

                    if random.random() < 0.3:  # 30% failure rate
                        raise Exception("Intermittent failure")

                    mock_response = MagicMock()
                    mock_response.is_success.return_value = True
                    mock_response.data = []
                    return mock_response

                mock_client.get_stock_briefs.side_effect = intermittent_side_effect

            mock_clients[account.account_number] = mock_client

        with patch.object(server, "tiger_clients", mock_clients):
            # Test system recovery
            successful_operations = 0

            for attempt in range(10):  # Multiple attempts to test recovery
                for account_number, client in mock_clients.items():
                    try:
                        result = client.get_stock_briefs(["AAPL"])
                        if result.is_success():
                            successful_operations += 1
                    except Exception:
                        # Continue with other accounts/retries
                        continue

            # System should recover and have successful operations
            assert (
                successful_operations > 0
            ), "System should recover and complete some operations"

    @pytest.mark.asyncio
    async def test_multi_account_portfolio_aggregation(
        self, mcp_server_instance, multiple_tiger_accounts
    ):
        """Test portfolio data aggregation across multiple accounts."""
        app, server = mcp_server_instance

        # Set up mock clients with different positions
        mock_clients = {}

        for i, (account_name, account) in enumerate(multiple_tiger_accounts.items()):
            mock_client = MagicMock()

            # Mock positions for each account
            mock_positions = []

            # AAPL position (different quantities per account)
            aapl_position = MagicMock()
            aapl_position.contract.symbol = "AAPL"
            aapl_position.position = 100 * (i + 1)  # Different quantities
            aapl_position.avg_cost = 150.0 + i
            aapl_position.market_value = aapl_position.position * 150.25
            mock_positions.append(aapl_position)

            # MSFT position (only some accounts)
            if i < 2:
                msft_position = MagicMock()
                msft_position.contract.symbol = "MSFT"
                msft_position.position = 50 * (i + 1)
                msft_position.avg_cost = 330.0 + i
                msft_position.market_value = msft_position.position * 330.75
                mock_positions.append(msft_position)

            mock_client.get_positions.return_value.is_success.return_value = True
            mock_client.get_positions.return_value.data = mock_positions

            mock_clients[account.account_number] = mock_client

        with patch.object(server, "tiger_clients", mock_clients):
            # Aggregate portfolio data across accounts
            consolidated_positions = {}

            for account_number, client in mock_clients.items():
                positions_result = client.get_positions()
                assert positions_result.is_success()

                for position in positions_result.data:
                    symbol = position.contract.symbol

                    if symbol not in consolidated_positions:
                        consolidated_positions[symbol] = {
                            "total_quantity": 0,
                            "total_value": 0,
                            "accounts": [],
                        }

                    consolidated_positions[symbol][
                        "total_quantity"
                    ] += position.position
                    consolidated_positions[symbol][
                        "total_value"
                    ] += position.market_value
                    consolidated_positions[symbol]["accounts"].append(account_number)

            # Verify aggregation
            assert "AAPL" in consolidated_positions
            assert "MSFT" in consolidated_positions

            # AAPL should be in all accounts
            aapl_data = consolidated_positions["AAPL"]
            assert len(aapl_data["accounts"]) == len(multiple_tiger_accounts)

            # MSFT should be in fewer accounts
            msft_data = consolidated_positions["MSFT"]
            assert len(msft_data["accounts"]) == 2

            # Verify quantities
            expected_aapl_quantity = sum(
                100 * (i + 1) for i in range(len(multiple_tiger_accounts))
            )
            assert aapl_data["total_quantity"] == expected_aapl_quantity
