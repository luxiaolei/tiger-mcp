"""
Unit tests for Tiger MCP Info Tools.

Tests all 4 informational tools:
1. tiger_get_contracts - Contract/instrument information
2. tiger_get_financials - Financial data and ratios
3. tiger_get_corporate_actions - Corporate actions (dividends, splits)
4. tiger_get_earnings - Earnings data and estimates
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

# Import the tools under test
from mcp_server.tools.info_tools import (
    tiger_get_contracts,
    tiger_get_corporate_actions,
    tiger_get_earnings,
    tiger_get_financials,
)


class TestInfoTools:
    """Test suite for Tiger MCP info tools."""

    @pytest.mark.asyncio
    async def test_tiger_get_contracts_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful contract information retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.contracts_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_contracts("AAPL")

        # Verify results
        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.data is not None
        assert "contracts" in result.data
        assert len(result.data["contracts"]) > 0

        # Verify contract structure
        contract = result.data["contracts"][0]
        expected_fields = ["symbol", "name", "currency", "exchange", "market", "type"]
        assert all(field in contract for field in expected_fields)

        # Verify calls
        mock_account_router.route_data_request.assert_called_once()
        mock_process_manager.execute_task.assert_called_once()

        # Verify task parameters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][0] == "test_account_123"  # account_id
        assert call_args[0][1] == "get_contracts"  # method
        assert call_args[0][2] == ["AAPL"]  # args

    @pytest.mark.asyncio
    async def test_tiger_get_contracts_with_filters(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test contract retrieval with market and type filters."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.contracts_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with filters
        result = await tiger_get_contracts("AAPL", "US", "STOCK")

        # Verify results
        assert result.success is True

        # Verify call parameters include filters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][2] == ["AAPL", "US", "STOCK"]

    @pytest.mark.asyncio
    async def test_tiger_get_contracts_invalid_symbol(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test contract retrieval with invalid symbol."""
        # Setup mocks for error response
        error_response = mock_tiger_api_data.get_error_response("invalid_symbol")
        mock_process_manager.execute_task.return_value = error_response
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_contracts("INVALID")

        # Verify error response
        assert result.success is False
        assert result.symbol == "INVALID"
        assert result.data is None
        assert "Symbol not found" in result.error

    @pytest.mark.asyncio
    async def test_tiger_get_financials_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful financial data retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.financials_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_financials("AAPL")

        # Verify results
        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.data is not None
        assert "financial_data" in result.data

        # Verify financial data structure
        financial_data = result.data["financial_data"]
        expected_fields = ["revenue", "net_income", "eps", "pe_ratio", "market_cap"]
        assert all(field in financial_data for field in expected_fields)

        # Verify data types and reasonable values
        assert isinstance(financial_data["revenue"], (int, float))
        assert isinstance(financial_data["eps"], (int, float))
        assert financial_data["revenue"] > 0
        assert financial_data["pe_ratio"] > 0

    @pytest.mark.asyncio
    async def test_tiger_get_financials_with_period(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test financial data retrieval with specific period."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.financials_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with period
        result = await tiger_get_financials("AAPL", "annual")

        # Verify results
        assert result.success is True

        # Verify call parameters include period
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][2] == ["AAPL", "annual"]

    @pytest.mark.asyncio
    async def test_tiger_get_corporate_actions_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful corporate actions retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.corporate_actions_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_corporate_actions("AAPL")

        # Verify results
        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.data is not None
        assert "corporate_actions" in result.data
        assert len(result.data["corporate_actions"]) > 0

        # Verify corporate action structure
        actions = result.data["corporate_actions"]

        # Find dividend action
        dividend_action = next((a for a in actions if a["type"] == "DIVIDEND"), None)
        assert dividend_action is not None
        expected_dividend_fields = ["type", "ex_date", "pay_date", "amount", "currency"]
        assert all(field in dividend_action for field in expected_dividend_fields)

        # Find split action
        split_action = next((a for a in actions if a["type"] == "SPLIT"), None)
        assert split_action is not None
        expected_split_fields = ["type", "ex_date", "ratio", "status"]
        assert all(field in split_action for field in expected_split_fields)

    @pytest.mark.asyncio
    async def test_tiger_get_corporate_actions_with_date_range(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test corporate actions retrieval with date range."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.corporate_actions_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with date range
        start_date = "2024-01-01"
        end_date = "2024-12-31"
        result = await tiger_get_corporate_actions("AAPL", start_date, end_date)

        # Verify results
        assert result.success is True

        # Verify call parameters include date range
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][2] == ["AAPL", start_date, end_date]

    @pytest.mark.asyncio
    async def test_tiger_get_corporate_actions_with_action_type(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test corporate actions retrieval filtered by action type."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.corporate_actions_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with action type filter
        result = await tiger_get_corporate_actions("AAPL", action_type="DIVIDEND")

        # Verify results
        assert result.success is True

        # Verify call parameters include action type
        call_args = mock_process_manager.execute_task.call_args
        assert "DIVIDEND" in call_args[0][2] or "DIVIDEND" in str(
            call_args[1]
        )  # Could be in kwargs

    @pytest.mark.asyncio
    async def test_tiger_get_earnings_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful earnings data retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.earnings_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_earnings("AAPL")

        # Verify results
        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.data is not None
        assert "earnings" in result.data
        assert len(result.data["earnings"]) > 0

        # Verify earnings data structure
        earnings = result.data["earnings"]
        latest_earnings = earnings[0]
        expected_fields = [
            "quarter",
            "year",
            "announce_date",
            "eps_estimate",
            "eps_actual",
            "revenue_estimate",
            "revenue_actual",
        ]
        assert all(field in latest_earnings for field in expected_fields)

        # Verify data types
        assert isinstance(latest_earnings["eps_actual"], (int, float))
        assert isinstance(latest_earnings["revenue_actual"], (int, float))
        assert latest_earnings["year"] >= 2020  # Reasonable year range

    @pytest.mark.asyncio
    async def test_tiger_get_earnings_with_limit(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test earnings data retrieval with result limit."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.earnings_response
        )
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool with limit
        result = await tiger_get_earnings("AAPL", limit=5)

        # Verify results
        assert result.success is True

        # Verify call parameters include limit
        call_args = mock_process_manager.execute_task.call_args
        assert 5 in call_args[0][2] or "limit" in str(call_args[1])

    @pytest.mark.asyncio
    async def test_info_tools_error_handling(
        self, mock_process_manager, mock_account_router
    ):
        """Test error handling across all info tools."""
        # Setup mocks for various error scenarios
        error_scenarios = [
            RuntimeError("Process execution failed"),
            TimeoutError("Request timed out"),
            ConnectionError("Network unreachable"),
        ]

        tools_to_test = [
            (tiger_get_contracts, "AAPL"),
            (tiger_get_financials, "AAPL"),
            (tiger_get_corporate_actions, "AAPL"),
            (tiger_get_earnings, "AAPL"),
        ]

        for error in error_scenarios:
            for tool_func, symbol in tools_to_test:
                # Setup mock for this error
                mock_process_manager.execute_task.side_effect = error
                mock_account_router.route_data_request.return_value = "test_account_123"

                # Execute tool
                result = await tool_func(symbol)

                # Verify error handling
                assert result.success is False
                assert result.data is None
                assert result.error is not None
                assert len(result.error) > 0

    @pytest.mark.asyncio
    async def test_info_tools_no_account_error(
        self, mock_process_manager, mock_account_router
    ):
        """Test info tools when no account is available."""
        # Setup mocks for no account scenario
        mock_account_router.route_data_request.side_effect = RuntimeError(
            "No account available for data requests"
        )

        tools_to_test = [
            tiger_get_contracts,
            tiger_get_financials,
            tiger_get_corporate_actions,
            tiger_get_earnings,
        ]

        for tool_func in tools_to_test:
            # Execute tool
            result = await tool_func("AAPL")

            # Verify error handling
            assert result.success is False
            assert "No account available" in result.error

    @pytest.mark.asyncio
    async def test_concurrent_info_requests(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test concurrent info tool requests."""

        # Setup mocks with different responses for each tool
        def mock_execute_task(account_id, method, args, **kwargs):
            method_responses = {
                "get_contracts": mock_tiger_api_data.contracts_response,
                "get_financials": mock_tiger_api_data.financials_response,
                "get_corporate_actions": mock_tiger_api_data.corporate_actions_response,
                "get_earnings": mock_tiger_api_data.earnings_response,
            }
            return method_responses.get(method, {"success": True})

        mock_process_manager.execute_task.side_effect = mock_execute_task
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute multiple concurrent requests
        tasks = [
            tiger_get_contracts("AAPL"),
            tiger_get_financials("AAPL"),
            tiger_get_corporate_actions("AAPL"),
            tiger_get_earnings("AAPL"),
        ]
        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert all(result.success for result in results)
        assert len(results) == 4

        # Verify different tool types were called
        assert mock_process_manager.execute_task.call_count == 4

    @pytest.mark.parametrize(
        "symbol,expected_valid",
        [
            ("AAPL", True),
            ("MSFT", True),
            ("GOOGL", True),
            ("", False),
            ("INVALID_SYMBOL", True),  # Should be handled by API, not validation
        ],
    )
    @pytest.mark.asyncio
    async def test_symbol_parameter_handling(
        self,
        symbol,
        expected_valid,
        mock_process_manager,
        mock_account_router,
        mock_tiger_api_data,
    ):
        """Test symbol parameter handling across info tools."""
        if expected_valid and symbol:
            # Setup for valid symbol
            mock_process_manager.execute_task.return_value = (
                mock_tiger_api_data.contracts_response
            )
            mock_account_router.route_data_request.return_value = "test_account_123"

            result = await tiger_get_contracts(symbol)
            if symbol != "INVALID_SYMBOL":
                assert result.success is True
        else:
            # Empty symbols should be handled gracefully
            result = await tiger_get_contracts(symbol)
            if not expected_valid:
                assert result.success is False

    @pytest.mark.asyncio
    async def test_info_tools_response_structure_validation(
        self, mock_process_manager, mock_account_router
    ):
        """Test that info tools properly validate response structures."""
        # Setup mock with malformed response
        malformed_response = {
            "success": True,
            "symbol": "AAPL",
            "data": "this should be a dict, not a string",
            "timestamp": datetime.utcnow().isoformat(),
        }

        mock_process_manager.execute_task.return_value = malformed_response
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_contracts("AAPL")

        # Tool should handle malformed response gracefully
        # Either succeed with data validation or fail with appropriate error
        assert isinstance(result.success, bool)
        if not result.success:
            assert result.error is not None


class TestInfoToolsIntegration:
    """Integration tests for info tools."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_info_tools_full_workflow(
        self, mock_account_manager, mock_tiger_api_data
    ):
        """Test complete workflow for info tools."""
        with patch(
            "mcp_server.tools.info_tools.get_process_manager"
        ) as mock_get_process_manager:
            mock_process_manager = AsyncMock()
            mock_get_process_manager.return_value = mock_process_manager

            with patch(
                "mcp_server.tools.info_tools.get_account_router"
            ) as mock_get_router:
                mock_router = AsyncMock()
                mock_router.route_data_request.return_value = "test_account_123"
                mock_get_router.return_value = mock_router

                # Setup different responses for each tool
                def mock_execute_task(account_id, method, args, **kwargs):
                    responses = {
                        "get_contracts": mock_tiger_api_data.contracts_response,
                        "get_financials": mock_tiger_api_data.financials_response,
                        "get_corporate_actions": mock_tiger_api_data.corporate_actions_response,
                        "get_earnings": mock_tiger_api_data.earnings_response,
                    }
                    return responses.get(
                        method, {"success": False, "error": "Unknown method"}
                    )

                mock_process_manager.execute_task.side_effect = mock_execute_task

                # Execute full workflow
                symbol = "AAPL"

                # Get basic contract info
                contracts_result = await tiger_get_contracts(symbol)
                assert contracts_result.success is True

                # Get financial data
                financials_result = await tiger_get_financials(symbol)
                assert financials_result.success is True

                # Get corporate actions
                actions_result = await tiger_get_corporate_actions(symbol)
                assert actions_result.success is True

                # Get earnings data
                earnings_result = await tiger_get_earnings(symbol)
                assert earnings_result.success is True

                # Verify all tools were called
                assert mock_process_manager.execute_task.call_count == 4

                # Verify account routing was used
                assert mock_router.route_data_request.call_count == 4

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_info_tools_performance(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test performance of info tools with multiple requests."""

        # Setup mocks
        def mock_execute_task(account_id, method, args, **kwargs):
            responses = {
                "get_contracts": mock_tiger_api_data.contracts_response,
                "get_financials": mock_tiger_api_data.financials_response,
                "get_corporate_actions": mock_tiger_api_data.corporate_actions_response,
                "get_earnings": mock_tiger_api_data.earnings_response,
            }
            return responses.get(method, {"success": False})

        mock_process_manager.execute_task.side_effect = mock_execute_task
        mock_account_router.route_data_request.return_value = "test_account_123"

        # Create multiple requests for different symbols
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
        tasks = []

        for symbol in symbols:
            tasks.extend(
                [
                    tiger_get_contracts(symbol),
                    tiger_get_financials(symbol),
                    tiger_get_corporate_actions(symbol),
                    tiger_get_earnings(symbol),
                ]
            )

        # Execute all requests and measure time
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()

        # Verify results
        successful_results = [
            r for r in results if not isinstance(r, Exception) and r.success
        ]
        assert len(successful_results) == len(tasks)

        # Verify performance
        execution_time = end_time - start_time
        assert execution_time < 15.0  # Should complete within 15 seconds

        print(
            f"Performance test: {len(tasks)} info tool requests completed in {execution_time:.2f} seconds"
        )
