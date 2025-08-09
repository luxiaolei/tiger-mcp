"""
Unit tests for Tiger MCP Trading Tools.

Tests all 6 trading tools:
1. tiger_get_positions - Get current positions
2. tiger_get_account_info - Get account balance and info
3. tiger_get_orders - Get order history and status
4. tiger_place_order - Place new trading orders
5. tiger_cancel_order - Cancel existing orders
6. tiger_modify_order - Modify existing orders
"""

import asyncio
from datetime import datetime

import pytest

# Import the tools under test
from mcp_server.tools.trading_tools import (
    tiger_cancel_order,
    tiger_get_account_info,
    tiger_get_orders,
    tiger_get_positions,
    tiger_modify_order,
    tiger_place_order,
)


class TestTradingTools:
    """Test suite for Tiger MCP trading tools."""

    @pytest.mark.asyncio
    async def test_tiger_get_positions_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful positions retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.positions_response
        )
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_positions()

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "positions" in result.data
        assert len(result.data["positions"]) > 0
        assert "total_market_value" in result.data
        assert "total_unrealized_pnl" in result.data

        # Verify position structure
        position = result.data["positions"][0]
        expected_fields = [
            "symbol",
            "quantity",
            "average_cost",
            "market_value",
            "unrealized_pnl",
            "currency",
            "position_side",
        ]
        assert all(field in position for field in expected_fields)

        # Verify data types
        assert isinstance(position["quantity"], (int, float))
        assert isinstance(position["market_value"], (int, float))
        assert position["quantity"] > 0  # Long position

        # Verify calls
        mock_account_router.route_trading_request.assert_called_once()
        mock_process_manager.execute_task.assert_called_once()

        # Verify task parameters
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][0] == "test_account_123"  # account_id
        assert call_args[0][1] == "get_positions"  # method

    @pytest.mark.asyncio
    async def test_tiger_get_positions_with_symbol_filter(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test positions retrieval with symbol filter."""
        # Setup mocks
        filtered_response = mock_tiger_api_data.positions_response.copy()
        filtered_response["data"]["positions"] = [
            pos
            for pos in filtered_response["data"]["positions"]
            if pos["symbol"] == "AAPL"
        ]
        mock_process_manager.execute_task.return_value = filtered_response
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool with symbol filter
        result = await tiger_get_positions("AAPL")

        # Verify results
        assert result.success is True
        assert all(pos["symbol"] == "AAPL" for pos in result.data["positions"])

        # Verify call parameters include symbol
        call_args = mock_process_manager.execute_task.call_args
        assert "AAPL" in call_args[0][2] or "AAPL" in str(call_args[1])

    @pytest.mark.asyncio
    async def test_tiger_get_positions_empty(
        self, mock_process_manager, mock_account_router
    ):
        """Test positions retrieval with no positions."""
        # Setup mocks for empty positions
        empty_response = {
            "success": True,
            "account_id": "test_account_123",
            "data": {
                "positions": [],
                "total_market_value": 0.0,
                "total_unrealized_pnl": 0.0,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        mock_process_manager.execute_task.return_value = empty_response
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_positions()

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert len(result.data["positions"]) == 0
        assert result.data["total_market_value"] == 0.0

    @pytest.mark.asyncio
    async def test_tiger_get_account_info_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful account information retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.account_info_response
        )
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_account_info()

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "account" in result.data

        # Verify account info structure
        account = result.data["account"]
        expected_fields = [
            "account_number",
            "account_type",
            "currency",
            "buying_power",
            "cash_balance",
            "market_value",
            "total_equity",
        ]
        assert all(field in account for field in expected_fields)

        # Verify data types and values
        assert isinstance(account["buying_power"], (int, float))
        assert isinstance(account["cash_balance"], (int, float))
        assert account["buying_power"] >= 0
        assert account["total_equity"] >= 0
        assert account["currency"] in ["USD", "HKD", "SGD", "CNY"]

        # Verify calls
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "get_account_info"

    @pytest.mark.asyncio
    async def test_tiger_get_orders_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful orders retrieval."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.orders_response
        )
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_get_orders()

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "orders" in result.data
        assert len(result.data["orders"]) > 0

        # Verify order structure
        order = result.data["orders"][0]
        expected_fields = [
            "order_id",
            "symbol",
            "action",
            "quantity",
            "order_type",
            "status",
            "created_at",
        ]
        assert all(field in order for field in expected_fields)

        # Verify data types and values
        assert isinstance(order["quantity"], (int, float))
        assert order["action"] in ["BUY", "SELL"]
        assert order["order_type"] in ["MKT", "LMT", "STP", "STP_LMT"]
        assert order["status"] in [
            "PENDING_SUBMIT",
            "SUBMITTED",
            "FILLED",
            "CANCELLED",
            "REJECTED",
        ]

        # Verify calls
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "get_orders"

    @pytest.mark.asyncio
    async def test_tiger_get_orders_with_filters(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test orders retrieval with filters."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.orders_response
        )
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool with filters
        result = await tiger_get_orders(
            symbol="AAPL",
            status="FILLED",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        # Verify results
        assert result.success is True

        # Verify call parameters include filters
        call_args = mock_process_manager.execute_task.call_args
        args_str = str(call_args[0][2]) + str(
            call_args[1] if len(call_args) > 1 else ""
        )
        assert "AAPL" in args_str
        assert "FILLED" in args_str
        assert "2024-01-01" in args_str

    @pytest.mark.asyncio
    async def test_tiger_place_order_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful order placement."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.place_order_response
        )
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_place_order(
            symbol="AAPL",
            action="BUY",
            quantity=100,
            order_type="LMT",
            limit_price=150.00,
        )

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "order" in result.data

        # Verify order response structure
        order = result.data["order"]
        assert "order_id" in order
        assert order["symbol"] == "AAPL"
        assert order["action"] == "BUY"
        assert order["quantity"] == 100
        assert order["order_type"] == "LMT"
        assert order["limit_price"] == 150.00
        assert order["status"] == "PENDING_SUBMIT"

        # Verify calls
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "place_order"

        # Verify order parameters
        order_params = call_args[0][2]
        assert "AAPL" in order_params
        assert "BUY" in order_params
        assert 100 in order_params
        assert "LMT" in order_params

    @pytest.mark.asyncio
    async def test_tiger_place_order_market_order(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test market order placement."""
        # Setup mocks
        market_response = mock_tiger_api_data.place_order_response.copy()
        market_response["data"]["order"]["order_type"] = "MKT"
        market_response["data"]["order"].pop("limit_price", None)
        mock_process_manager.execute_task.return_value = market_response
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool for market order
        result = await tiger_place_order(
            symbol="AAPL", action="BUY", quantity=100, order_type="MKT"
        )

        # Verify results
        assert result.success is True
        assert result.data["order"]["order_type"] == "MKT"
        assert (
            "limit_price" not in result.data["order"]
            or result.data["order"]["limit_price"] is None
        )

    @pytest.mark.asyncio
    async def test_tiger_place_order_validation_error(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test order placement with validation errors."""
        # Setup mocks for validation error
        error_response = mock_tiger_api_data.get_error_response("insufficient_funds")
        mock_process_manager.execute_task.return_value = error_response
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool with order that would fail validation
        result = await tiger_place_order(
            symbol="AAPL",
            action="BUY",
            quantity=10000,  # Large quantity
            order_type="MKT",
        )

        # Verify error handling
        assert result.success is False
        assert result.data is None
        assert "Insufficient buying power" in result.error

    @pytest.mark.asyncio
    async def test_tiger_place_order_invalid_parameters(self):
        """Test order placement with invalid parameters."""
        # Test invalid order type
        result = await tiger_place_order(
            symbol="AAPL", action="BUY", quantity=100, order_type="INVALID_TYPE"
        )
        assert result.success is False
        assert result.error is not None

        # Test invalid action
        result = await tiger_place_order(
            symbol="AAPL", action="INVALID_ACTION", quantity=100, order_type="MKT"
        )
        assert result.success is False
        assert result.error is not None

        # Test invalid quantity
        result = await tiger_place_order(
            symbol="AAPL",
            action="BUY",
            quantity=0,  # Invalid quantity
            order_type="MKT",
        )
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_tiger_cancel_order_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful order cancellation."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.cancel_order_response
        )
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        order_id = "ORD_123456789"
        result = await tiger_cancel_order(order_id)

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert result.data["order_id"] == order_id
        assert result.data["status"] == "CANCELLED"
        assert "cancelled_at" in result.data

        # Verify calls
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "cancel_order"
        assert order_id in call_args[0][2]

    @pytest.mark.asyncio
    async def test_tiger_cancel_order_not_found(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test cancelling non-existent order."""
        # Setup mocks for order not found
        error_response = {
            "success": False,
            "error": "Order not found: ORD_INVALID",
            "error_code": "ORDER_NOT_FOUND",
            "timestamp": datetime.utcnow().isoformat(),
        }
        mock_process_manager.execute_task.return_value = error_response
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_cancel_order("ORD_INVALID")

        # Verify error handling
        assert result.success is False
        assert result.data is None
        assert "Order not found" in result.error

    @pytest.mark.asyncio
    async def test_tiger_cancel_order_already_filled(
        self, mock_process_manager, mock_account_router
    ):
        """Test cancelling already filled order."""
        # Setup mocks for already filled order
        error_response = {
            "success": False,
            "error": "Cannot cancel order: Order is already filled",
            "error_code": "ORDER_ALREADY_FILLED",
            "timestamp": datetime.utcnow().isoformat(),
        }
        mock_process_manager.execute_task.return_value = error_response
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_cancel_order("ORD_123456789")

        # Verify error handling
        assert result.success is False
        assert "already filled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tiger_modify_order_success(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test successful order modification."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.modify_order_response
        )
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        order_id = "ORD_123456789"
        result = await tiger_modify_order(
            order_id=order_id,
            quantity=150,  # Modified quantity
            limit_price=148.50,  # Modified price
        )

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "order" in result.data

        # Verify modified order
        order = result.data["order"]
        assert order["order_id"] == order_id
        assert order["quantity"] == 150
        assert order["limit_price"] == 148.50
        assert order["status"] == "PENDING_SUBMIT"
        assert "updated_at" in order

        # Verify calls
        call_args = mock_process_manager.execute_task.call_args
        assert call_args[0][1] == "modify_order"
        args_str = str(call_args[0][2]) + str(
            call_args[1] if len(call_args) > 1 else ""
        )
        assert order_id in args_str
        assert "150" in args_str or 150 in call_args[0][2]
        assert "148.5" in args_str or 148.5 in call_args[0][2]

    @pytest.mark.asyncio
    async def test_tiger_modify_order_quantity_only(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test order modification with quantity only."""
        # Setup mocks
        mock_process_manager.execute_task.return_value = (
            mock_tiger_api_data.modify_order_response
        )
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool with quantity modification only
        order_id = "ORD_123456789"
        result = await tiger_modify_order(order_id=order_id, quantity=200)

        # Verify results
        assert result.success is True
        assert result.data["order"]["quantity"] == 150  # From mock response

        # Verify only quantity was passed (no limit_price)
        call_args = mock_process_manager.execute_task.call_args
        args_str = str(call_args)
        assert "200" in args_str or 200 in call_args[0][2]

    @pytest.mark.asyncio
    async def test_tiger_modify_order_invalid_order(
        self, mock_process_manager, mock_account_router
    ):
        """Test modifying non-existent order."""
        # Setup mocks for order not found
        error_response = {
            "success": False,
            "error": "Order not found: ORD_INVALID",
            "error_code": "ORDER_NOT_FOUND",
            "timestamp": datetime.utcnow().isoformat(),
        }
        mock_process_manager.execute_task.return_value = error_response
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute tool
        result = await tiger_modify_order(order_id="ORD_INVALID", quantity=100)

        # Verify error handling
        assert result.success is False
        assert "Order not found" in result.error

    @pytest.mark.asyncio
    async def test_trading_tools_no_account_error(
        self, mock_process_manager, mock_account_router
    ):
        """Test trading tools when no trading account is available."""
        # Setup mocks for no trading account
        mock_account_router.route_trading_request.side_effect = RuntimeError(
            "No trading account available"
        )

        # Test all trading tools
        trading_tools = [
            (tiger_get_positions, []),
            (tiger_get_account_info, []),
            (tiger_get_orders, []),
            (tiger_place_order, ["AAPL", "BUY", 100, "MKT"]),
            (tiger_cancel_order, ["ORD_123456789"]),
            (tiger_modify_order, ["ORD_123456789"], {"quantity": 100}),
        ]

        for tool_data in trading_tools:
            tool_func = tool_data[0]
            args = tool_data[1] if len(tool_data) > 1 else []
            kwargs = tool_data[2] if len(tool_data) > 2 else {}

            # Execute tool
            result = await tool_func(*args, **kwargs)

            # Verify error handling
            assert result.success is False
            assert "No trading account available" in result.error

    @pytest.mark.asyncio
    async def test_trading_tools_market_closed_error(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test trading tools during market closed hours."""
        # Setup mocks for market closed error
        market_closed_error = mock_tiger_api_data.get_error_response("market_closed")
        mock_process_manager.execute_task.return_value = market_closed_error
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Test order placement during market closed
        result = await tiger_place_order(
            symbol="AAPL", action="BUY", quantity=100, order_type="MKT"
        )

        # Verify error handling
        assert result.success is False
        assert "Market is closed" in result.error

    @pytest.mark.asyncio
    async def test_concurrent_trading_operations(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test concurrent trading operations."""

        # Setup mocks with different responses
        def mock_execute_task(account_id, method, args, **kwargs):
            method_responses = {
                "get_positions": mock_tiger_api_data.positions_response,
                "get_account_info": mock_tiger_api_data.account_info_response,
                "get_orders": mock_tiger_api_data.orders_response,
                "place_order": mock_tiger_api_data.place_order_response,
            }
            return method_responses.get(method, {"success": True})

        mock_process_manager.execute_task.side_effect = mock_execute_task
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Execute multiple concurrent operations
        tasks = [
            tiger_get_positions(),
            tiger_get_account_info(),
            tiger_get_orders(),
            tiger_place_order("AAPL", "BUY", 100, "MKT"),
        ]
        results = await asyncio.gather(*tasks)

        # Verify all operations succeeded
        assert all(result.success for result in results)
        assert len(results) == 4

        # Verify different methods were called
        assert mock_process_manager.execute_task.call_count == 4

    @pytest.mark.parametrize(
        "order_type,limit_price,stop_price,expected_valid",
        [
            ("MKT", None, None, True),
            ("LMT", 150.00, None, True),
            ("STP", None, 145.00, True),
            ("STP_LMT", 150.00, 145.00, True),
            ("INVALID", None, None, False),
            ("LMT", None, None, False),  # Limit order without limit price
            ("STP", None, None, False),  # Stop order without stop price
        ],
    )
    @pytest.mark.asyncio
    async def test_order_type_validation(
        self,
        order_type,
        limit_price,
        stop_price,
        expected_valid,
        mock_process_manager,
        mock_account_router,
        mock_tiger_api_data,
    ):
        """Test order type validation in place_order tool."""
        if expected_valid:
            # Setup for valid order
            mock_process_manager.execute_task.return_value = (
                mock_tiger_api_data.place_order_response
            )
            mock_account_router.route_trading_request.return_value = "test_account_123"

        # Prepare order parameters
        order_kwargs = {"order_type": order_type}
        if limit_price is not None:
            order_kwargs["limit_price"] = limit_price
        if stop_price is not None:
            order_kwargs["stop_price"] = stop_price

        # Execute tool
        result = await tiger_place_order(
            symbol="AAPL", action="BUY", quantity=100, **order_kwargs
        )

        # Verify results based on expected validity
        if expected_valid:
            assert result.success is True or "required" in result.error.lower()
        else:
            assert result.success is False
            assert result.error is not None


class TestTradingToolsIntegration:
    """Integration tests for trading tools."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_trading_workflow(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test complete trading workflow from account info to order execution."""

        # Setup mocks for complete workflow
        def mock_execute_task(account_id, method, args, **kwargs):
            responses = {
                "get_account_info": mock_tiger_api_data.account_info_response,
                "get_positions": mock_tiger_api_data.positions_response,
                "place_order": mock_tiger_api_data.place_order_response,
                "get_orders": mock_tiger_api_data.orders_response,
                "modify_order": mock_tiger_api_data.modify_order_response,
                "cancel_order": mock_tiger_api_data.cancel_order_response,
            }
            return responses.get(method, {"success": False})

        mock_process_manager.execute_task.side_effect = mock_execute_task
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # 1. Get account info to check buying power
        account_result = await tiger_get_account_info()
        assert account_result.success is True
        buying_power = account_result.data["account"]["buying_power"]
        assert buying_power > 0

        # 2. Get current positions
        positions_result = await tiger_get_positions()
        assert positions_result.success is True

        # 3. Place a new order
        order_result = await tiger_place_order(
            symbol="AAPL",
            action="BUY",
            quantity=100,
            order_type="LMT",
            limit_price=150.00,
        )
        assert order_result.success is True
        order_id = order_result.data["order"]["order_id"]

        # 4. Get orders to verify placement
        orders_result = await tiger_get_orders()
        assert orders_result.success is True
        assert len(orders_result.data["orders"]) > 0

        # 5. Modify the order
        modify_result = await tiger_modify_order(
            order_id=order_id, quantity=150, limit_price=148.50
        )
        assert modify_result.success is True

        # 6. Cancel the order
        cancel_result = await tiger_cancel_order(order_id)
        assert cancel_result.success is True
        assert cancel_result.data["status"] == "CANCELLED"

        # Verify all operations were called
        assert mock_process_manager.execute_task.call_count == 6

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_trading_tools_stress_test(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Stress test with multiple concurrent trading operations."""

        # Setup mocks
        def mock_execute_task(account_id, method, args, **kwargs):
            responses = {
                "get_positions": mock_tiger_api_data.positions_response,
                "get_account_info": mock_tiger_api_data.account_info_response,
                "get_orders": mock_tiger_api_data.orders_response,
                "place_order": mock_tiger_api_data.place_order_response,
            }
            return responses.get(method, {"success": True})

        mock_process_manager.execute_task.side_effect = mock_execute_task
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Create many concurrent requests
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
        tasks = []

        # Multiple position checks
        tasks.extend([tiger_get_positions(symbol) for symbol in symbols])

        # Multiple account info requests
        tasks.extend([tiger_get_account_info() for _ in range(10)])

        # Multiple order queries
        tasks.extend([tiger_get_orders(symbol=symbol) for symbol in symbols])

        # Multiple order placements
        for symbol in symbols:
            tasks.append(
                tiger_place_order(
                    symbol=symbol, action="BUY", quantity=100, order_type="MKT"
                )
            )

        # Execute all requests and measure performance
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
        assert execution_time < 20.0  # Should complete within 20 seconds

        print(
            f"Trading tools stress test: {len(tasks)} operations completed in {execution_time:.2f} seconds"
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_trading_tools_error_scenarios(
        self, mock_process_manager, mock_account_router, mock_tiger_api_data
    ):
        """Test various error scenarios in trading tools."""
        mock_account_router.route_trading_request.return_value = "test_account_123"

        # Test different error scenarios
        error_scenarios = [
            ("insufficient_funds", tiger_place_order, ["AAPL", "BUY", 10000, "MKT"]),
            ("rate_limit", tiger_get_positions, []),
            ("network", tiger_get_account_info, []),
            ("authentication", tiger_get_orders, []),
        ]

        for error_type, tool_func, args in error_scenarios:
            # Setup mock for this error
            error_response = mock_tiger_api_data.get_error_response(error_type)
            mock_process_manager.execute_task.return_value = error_response

            # Execute tool
            result = await tool_func(*args)

            # Verify error handling
            assert result.success is False
            assert result.error is not None
            assert len(result.error) > 0
