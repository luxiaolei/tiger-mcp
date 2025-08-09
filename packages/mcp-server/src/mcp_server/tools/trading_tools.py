"""
Trading MCP Tools for Tiger Brokers API.

Provides MCP tools for trading operations including account information,
positions, orders, and trade execution through the Tiger API process pool.
"""

import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add paths for imports
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/shared/src"
)

from fastmcp import FastMCP
from loguru import logger
from pydantic import BaseModel, Field
from shared.account_manager import get_account_manager
from shared.account_router import OperationType, get_account_router

from ..process_manager import get_process_manager

# Initialize FastMCP instance for trading tools
mcp = FastMCP("Tiger Trading Tools")


class PositionsResponse(BaseModel):
    """Positions response model."""

    success: bool
    account_id: str = ""
    positions: List[Dict[str, Any]] = Field(default_factory=list)
    total_market_value: Optional[float] = None
    total_pnl: Optional[float] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AccountInfoResponse(BaseModel):
    """Account info response model."""

    success: bool
    account_id: str = ""
    account_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class OrdersResponse(BaseModel):
    """Orders response model."""

    success: bool
    account_id: str = ""
    orders: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class OrderResponse(BaseModel):
    """Single order response model."""

    success: bool
    account_id: str = ""
    order: Optional[Dict[str, Any]] = None
    order_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Service instance for trading operations
class TradingToolsService:
    """Service class for trading tools with account routing."""

    def __init__(self):
        self.process_manager = get_process_manager()
        self.account_manager = get_account_manager()
        self.account_router = get_account_router()

    async def _route_trading_account(
        self,
        account_id: Optional[str],
        operation_type: OperationType = OperationType.ACCOUNT_INFO,
    ) -> str:
        """Route request to appropriate trading account."""
        if account_id:
            # Use specified account
            return account_id
        else:
            # Use default trading account or router
            default_account = await self.account_manager.get_default_trading_account()
            if default_account:
                return str(default_account.id)
            else:
                # Use account router for trading operations
                routed_account = await self.account_router.route_trading_operation(
                    operation_type
                )
                return str(routed_account.id)

    async def ensure_started(self):
        """Ensure the process manager is started."""
        if (
            not hasattr(self.process_manager, "_started")
            or not self.process_manager._started
        ):
            await self.process_manager.start()


# Global service instance
_trading_service = TradingToolsService()


@mcp.tool()
async def tiger_get_positions(account_id: Optional[str] = None) -> PositionsResponse:
    """
    Get current positions for a Tiger account.

    Retrieves all current positions including stocks, options, and other securities
    held in the specified account with real-time market values and P&L information.

    Args:
        account_id: Optional specific account ID to use.
                   If not provided, uses default trading account or router.

    Returns:
        PositionsResponse containing positions data:
        - symbol: Security symbol
        - quantity: Number of shares/contracts held
        - market_value: Current market value of position
        - average_cost: Average cost basis
        - unrealized_pnl: Unrealized profit/loss
        - realized_pnl: Realized profit/loss
        - position_side: LONG or SHORT
        - security_type: STK, OPT, etc.

    Example:
        ```python
        # Get positions for default trading account
        response = await tiger_get_positions()
        if response.success:
            for position in response.positions:
                print(f"{position['symbol']}: {position['quantity']} shares, "
                      f"P&L: ${position['unrealized_pnl']:.2f}")

        # Get positions for specific account
        response = await tiger_get_positions("account-uuid-here")
        ```
    """
    try:
        await _trading_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _trading_service._route_trading_account(
            account_id, OperationType.POSITIONS
        )

        # Execute API call
        result = await _trading_service.process_manager.execute_api_call(
            account_id=target_account_id, method="trade.get_positions", timeout=15.0
        )

        # Process positions data
        positions = []
        total_market_value = 0.0
        total_pnl = 0.0

        if result:
            for position in result:
                position_data = {
                    "symbol": getattr(position, "symbol", ""),
                    "quantity": getattr(position, "quantity", 0),
                    "market_value": getattr(position, "market_value", 0.0),
                    "average_cost": getattr(position, "average_cost", 0.0),
                    "unrealized_pnl": getattr(position, "unrealized_pnl", 0.0),
                    "realized_pnl": getattr(position, "realized_pnl", 0.0),
                    "position_side": getattr(position, "position_side", "LONG"),
                    "security_type": getattr(position, "security_type", "STK"),
                    "currency": getattr(position, "currency", "USD"),
                    "local_symbol": getattr(position, "local_symbol", ""),
                    "multiplier": getattr(position, "multiplier", 1),
                    "strike": getattr(position, "strike", None),
                    "expiry": getattr(position, "expiry", None),
                    "right": getattr(position, "right", None),
                }
                positions.append(position_data)

                # Add to totals
                total_market_value += position_data["market_value"]
                total_pnl += position_data["unrealized_pnl"]

        return PositionsResponse(
            success=True,
            account_id=target_account_id,
            positions=positions,
            total_market_value=total_market_value,
            total_pnl=total_pnl,
        )

    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        return PositionsResponse(
            success=False, account_id=account_id or "", error=str(e)
        )


@mcp.tool()
async def tiger_get_account_info(
    account_id: Optional[str] = None,
) -> AccountInfoResponse:
    """
    Get account balance and information for a Tiger account.

    Retrieves comprehensive account information including cash balances,
    buying power, margin information, and account summary data.

    Args:
        account_id: Optional specific account ID to use.
                   If not provided, uses default trading account or router.

    Returns:
        AccountInfoResponse containing account information:
        - total_cash: Total cash available
        - buying_power: Available buying power
        - net_liquidation: Net liquidation value
        - total_market_value: Total market value of positions
        - unrealized_pnl: Total unrealized P&L
        - realized_pnl: Total realized P&L
        - margin_used: Margin currently used
        - maintenance_margin: Maintenance margin requirement
        - currency: Account base currency

    Example:
        ```python
        # Get account info for default account
        response = await tiger_get_account_info()
        if response.success:
            info = response.account_info
            print(f"Cash: ${info['total_cash']:.2f}")
            print(f"Buying Power: ${info['buying_power']:.2f}")
            print(f"P&L: ${info['unrealized_pnl']:.2f}")
        ```
    """
    try:
        await _trading_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _trading_service._route_trading_account(
            account_id, OperationType.ACCOUNT_INFO
        )

        # Execute API call
        result = await _trading_service.process_manager.execute_api_call(
            account_id=target_account_id, method="trade.get_account", timeout=15.0
        )

        # Process account info
        account_info = None
        if result:
            account_info = {
                "account_number": getattr(result, "account_number", ""),
                "total_cash": getattr(result, "total_cash", 0.0),
                "buying_power": getattr(result, "buying_power", 0.0),
                "net_liquidation": getattr(result, "net_liquidation", 0.0),
                "total_market_value": getattr(result, "total_market_value", 0.0),
                "unrealized_pnl": getattr(result, "unrealized_pnl", 0.0),
                "realized_pnl": getattr(result, "realized_pnl", 0.0),
                "margin_used": getattr(result, "margin_used", 0.0),
                "maintenance_margin": getattr(result, "maintenance_margin", 0.0),
                "available_funds": getattr(result, "available_funds", 0.0),
                "excess_liquidity": getattr(result, "excess_liquidity", 0.0),
                "currency": getattr(result, "currency", "USD"),
                "account_type": getattr(result, "account_type", ""),
                "trading_status": getattr(result, "trading_status", ""),
                "last_updated": getattr(
                    result, "last_updated", datetime.utcnow().isoformat()
                ),
            }

        return AccountInfoResponse(
            success=True, account_id=target_account_id, account_info=account_info
        )

    except Exception as e:
        logger.error(f"Failed to get account info: {e}")
        return AccountInfoResponse(
            success=False, account_id=account_id or "", error=str(e)
        )


@mcp.tool()
async def tiger_get_orders(
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> OrdersResponse:
    """
    Get orders for a Tiger account with optional filtering.

    Retrieves orders from the account with optional filtering by status,
    symbol, and date range. Useful for monitoring order execution and history.

    Args:
        account_id: Optional specific account ID to use.
                   If not provided, uses default trading account or router.
        status: Optional filter by order status:
               - 'PENDING': Orders awaiting execution
               - 'FILLED': Completely executed orders
               - 'PARTIAL_FILLED': Partially executed orders
               - 'CANCELLED': Cancelled orders
               - 'REJECTED': Rejected orders
        symbol: Optional filter by symbol (e.g., 'AAPL', 'TSLA')
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)
        limit: Maximum number of orders to return (default: 100, max: 500)

    Returns:
        OrdersResponse containing list of orders with details:
        - order_id: Unique order identifier
        - symbol: Trading symbol
        - side: BUY or SELL
        - quantity: Number of shares/contracts
        - order_type: MARKET, LIMIT, STOP, etc.
        - price: Order price (for limit orders)
        - status: Current order status
        - filled_quantity: Quantity already executed
        - average_fill_price: Average execution price
        - created_time: Order creation timestamp

    Example:
        ```python
        # Get all recent orders
        response = await tiger_get_orders()
        if response.success:
            for order in response.orders:
                print(f"{order['symbol']} {order['side']} {order['quantity']} @ "
                      f"{order['price']} - Status: {order['status']}")

        # Get pending orders for AAPL
        response = await tiger_get_orders(status="PENDING", symbol="AAPL")
        ```
    """
    try:
        await _trading_service.ensure_started()

        # Validate limit
        limit = min(max(limit, 1), 500)

        # Route to appropriate account
        target_account_id = await _trading_service._route_trading_account(
            account_id, OperationType.ORDERS
        )

        # Prepare filter parameters
        filters = {}
        if status:
            filters["status"] = status.upper()
        if symbol:
            filters["symbol"] = symbol.upper()
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        filters["limit"] = limit

        # Execute API call
        result = await _trading_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="trade.get_orders",
            kwargs=filters,
            timeout=15.0,
        )

        # Process orders
        orders = []
        if result:
            for order in result:
                order_data = {
                    "order_id": getattr(order, "order_id", ""),
                    "symbol": getattr(order, "symbol", ""),
                    "side": getattr(order, "side", ""),
                    "quantity": getattr(order, "quantity", 0),
                    "order_type": getattr(order, "order_type", ""),
                    "price": getattr(order, "price", None),
                    "stop_price": getattr(order, "stop_price", None),
                    "status": getattr(order, "status", ""),
                    "filled_quantity": getattr(order, "filled_quantity", 0),
                    "remaining_quantity": getattr(order, "remaining_quantity", 0),
                    "average_fill_price": getattr(order, "average_fill_price", None),
                    "created_time": getattr(order, "created_time", None),
                    "updated_time": getattr(order, "updated_time", None),
                    "time_in_force": getattr(order, "time_in_force", "DAY"),
                    "security_type": getattr(order, "security_type", "STK"),
                    "currency": getattr(order, "currency", "USD"),
                    "commission": getattr(order, "commission", 0.0),
                    "realized_pnl": getattr(order, "realized_pnl", 0.0),
                }
                orders.append(order_data)

        return OrdersResponse(
            success=True,
            account_id=target_account_id,
            orders=orders,
            total_count=len(orders),
        )

    except Exception as e:
        logger.error(f"Failed to get orders: {e}")
        return OrdersResponse(success=False, account_id=account_id or "", error=str(e))


@mcp.tool()
async def tiger_place_order(
    symbol: str,
    side: str,
    quantity: int,
    order_type: str,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "DAY",
    account_id: Optional[str] = None,
) -> OrderResponse:
    """
    Place a new order on Tiger Brokers.

    Submit a new trading order with specified parameters. Supports various
    order types including market, limit, stop, and stop-limit orders.

    Args:
        symbol: Trading symbol (e.g., 'AAPL', 'TSLA', 'SPY')
        side: Order side - 'BUY' or 'SELL'
        quantity: Number of shares to trade (must be positive integer)
        order_type: Type of order:
                   - 'MARKET': Execute at current market price
                   - 'LIMIT': Execute at specified price or better
                   - 'STOP': Stop-loss order (becomes market order when triggered)
                   - 'STOP_LIMIT': Stop order that becomes limit order when triggered
        price: Limit price (required for LIMIT and STOP_LIMIT orders)
        stop_price: Stop trigger price (required for STOP and STOP_LIMIT orders)
        time_in_force: Order duration:
                      - 'DAY': Valid for current trading day
                      - 'GTC': Good till cancelled
                      - 'IOC': Immediate or cancel
                      - 'FOK': Fill or kill
        account_id: Optional specific account ID to use.
                   If not provided, uses default trading account.

    Returns:
        OrderResponse containing the placed order details or error information.

    Example:
        ```python
        # Place a market buy order
        response = await tiger_place_order(
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type="MARKET"
        )

        # Place a limit sell order
        response = await tiger_place_order(
            symbol="TSLA",
            side="SELL",
            quantity=50,
            order_type="LIMIT",
            price=250.00,
            time_in_force="GTC"
        )

        # Place a stop-loss order
        response = await tiger_place_order(
            symbol="SPY",
            side="SELL",
            quantity=100,
            order_type="STOP",
            stop_price=400.00
        )
        ```

    Note:
        - This will execute real trades in production accounts
        - Always verify symbol, quantity, and prices before placing orders
        - Paper trading accounts can be used for testing
    """
    try:
        await _trading_service.ensure_started()

        # Validate inputs
        if not symbol or not symbol.strip():
            return OrderResponse(success=False, error="Symbol is required")

        side = side.upper().strip()
        if side not in ["BUY", "SELL"]:
            return OrderResponse(success=False, error="Side must be 'BUY' or 'SELL'")

        if quantity <= 0:
            return OrderResponse(success=False, error="Quantity must be positive")

        order_type = order_type.upper().strip()
        valid_order_types = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
        if order_type not in valid_order_types:
            return OrderResponse(
                success=False,
                error=f"Order type must be one of: {', '.join(valid_order_types)}",
            )

        # Validate price requirements
        if order_type in ["LIMIT", "STOP_LIMIT"] and price is None:
            return OrderResponse(
                success=False, error=f"{order_type} order requires a price"
            )

        if order_type in ["STOP", "STOP_LIMIT"] and stop_price is None:
            return OrderResponse(
                success=False, error=f"{order_type} order requires a stop_price"
            )

        # Route to appropriate account
        target_account_id = await _trading_service._route_trading_account(
            account_id, OperationType.PLACE_ORDER
        )

        # Prepare order parameters
        order_params = {
            "symbol": symbol.upper(),
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "time_in_force": time_in_force.upper(),
        }

        if price is not None:
            order_params["price"] = price
        if stop_price is not None:
            order_params["stop_price"] = stop_price

        # Execute order placement
        result = await _trading_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="trade.place_order",
            kwargs=order_params,
            timeout=30.0,
        )

        # Process order response
        order_info = None
        order_id = None
        if result:
            order_id = getattr(result, "order_id", None) or getattr(result, "id", None)
            order_info = {
                "order_id": order_id,
                "symbol": getattr(result, "symbol", symbol),
                "side": getattr(result, "side", side),
                "quantity": getattr(result, "quantity", quantity),
                "order_type": getattr(result, "order_type", order_type),
                "price": getattr(result, "price", price),
                "stop_price": getattr(result, "stop_price", stop_price),
                "time_in_force": getattr(result, "time_in_force", time_in_force),
                "status": getattr(result, "status", "PENDING"),
                "created_time": getattr(
                    result, "created_time", datetime.utcnow().isoformat()
                ),
                "account_id": target_account_id,
            }

        logger.info(
            f"Successfully placed order: {symbol} {side} {quantity} shares (ID: {order_id})"
        )

        return OrderResponse(
            success=True,
            account_id=target_account_id,
            order=order_info,
            order_id=order_id,
        )

    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        return OrderResponse(success=False, account_id=account_id or "", error=str(e))


@mcp.tool()
async def tiger_cancel_order(
    order_id: str, account_id: Optional[str] = None
) -> OrderResponse:
    """
    Cancel an existing order.

    Attempts to cancel a pending or partially filled order. Only orders
    that are not yet fully executed can be cancelled.

    Args:
        order_id: Unique identifier of the order to cancel
        account_id: Optional specific account ID to use.
                   If not provided, uses default trading account.

    Returns:
        OrderResponse indicating success or failure of the cancellation.

    Example:
        ```python
        response = await tiger_cancel_order("order-id-12345")
        if response.success:
            print("Order cancelled successfully")
            print(f"Final status: {response.order['status']}")
        ```

    Note:
        - Only pending or partially filled orders can be cancelled
        - Market orders may execute before cancellation can be processed
        - The order status will be updated to 'CANCELLED' if successful
    """
    try:
        await _trading_service.ensure_started()

        if not order_id or not order_id.strip():
            return OrderResponse(success=False, error="Order ID is required")

        # Route to appropriate account
        target_account_id = await _trading_service._route_trading_account(
            account_id, OperationType.CANCEL_ORDER
        )

        # Execute order cancellation
        result = await _trading_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="trade.cancel_order",
            kwargs={"order_id": order_id},
            timeout=15.0,
        )

        # Process cancellation response
        order_info = None
        if result:
            order_info = {
                "order_id": getattr(result, "order_id", order_id),
                "symbol": getattr(result, "symbol", ""),
                "side": getattr(result, "side", ""),
                "quantity": getattr(result, "quantity", 0),
                "status": getattr(result, "status", "CANCELLED"),
                "cancelled_time": getattr(
                    result, "cancelled_time", datetime.utcnow().isoformat()
                ),
                "filled_quantity": getattr(result, "filled_quantity", 0),
                "remaining_quantity": getattr(result, "remaining_quantity", 0),
            }

        logger.info(f"Successfully cancelled order: {order_id}")

        return OrderResponse(
            success=True,
            account_id=target_account_id,
            order=order_info,
            order_id=order_id,
        )

    except Exception as e:
        logger.error(f"Failed to cancel order {order_id}: {e}")
        return OrderResponse(
            success=False, account_id=account_id or "", order_id=order_id, error=str(e)
        )


@mcp.tool()
async def tiger_modify_order(
    order_id: str,
    new_quantity: Optional[int] = None,
    new_price: Optional[float] = None,
    new_stop_price: Optional[float] = None,
    account_id: Optional[str] = None,
) -> OrderResponse:
    """
    Modify an existing order.

    Updates the parameters of a pending or partially filled order.
    At least one parameter (quantity, price, or stop_price) must be provided.

    Args:
        order_id: Unique identifier of the order to modify
        new_quantity: New quantity for the order (must be positive)
        new_price: New limit price (for limit and stop-limit orders)
        new_stop_price: New stop trigger price (for stop and stop-limit orders)
        account_id: Optional specific account ID to use.
                   If not provided, uses default trading account.

    Returns:
        OrderResponse containing the modified order details or error information.

    Example:
        ```python
        # Modify order quantity
        response = await tiger_modify_order("order-id-12345", new_quantity=150)

        # Modify limit price
        response = await tiger_modify_order("order-id-12345", new_price=101.50)

        # Modify both quantity and price
        response = await tiger_modify_order(
            order_id="order-id-12345",
            new_quantity=200,
            new_price=102.00
        )
        ```

    Note:
        - Only pending or partially filled orders can be modified
        - Market orders typically cannot be modified
        - For partially filled orders, the new quantity must be >= filled quantity
        - Some brokers may cancel and replace the order instead of modifying in place
    """
    try:
        await _trading_service.ensure_started()

        if not order_id or not order_id.strip():
            return OrderResponse(success=False, error="Order ID is required")

        # Validate at least one modification parameter is provided
        if new_quantity is None and new_price is None and new_stop_price is None:
            return OrderResponse(
                success=False,
                error="At least one modification parameter (new_quantity, new_price, new_stop_price) must be provided",
            )

        # Validate new_quantity if provided
        if new_quantity is not None and new_quantity <= 0:
            return OrderResponse(success=False, error="New quantity must be positive")

        # Route to appropriate account
        target_account_id = await _trading_service._route_trading_account(
            account_id, OperationType.MODIFY_ORDER
        )

        # Prepare modification parameters
        modify_params = {"order_id": order_id}
        if new_quantity is not None:
            modify_params["quantity"] = new_quantity
        if new_price is not None:
            modify_params["price"] = new_price
        if new_stop_price is not None:
            modify_params["stop_price"] = new_stop_price

        # Execute order modification
        result = await _trading_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="trade.modify_order",
            kwargs=modify_params,
            timeout=15.0,
        )

        # Process modification response
        order_info = None
        if result:
            order_info = {
                "order_id": getattr(result, "order_id", order_id),
                "symbol": getattr(result, "symbol", ""),
                "side": getattr(result, "side", ""),
                "quantity": getattr(result, "quantity", new_quantity),
                "price": getattr(result, "price", new_price),
                "stop_price": getattr(result, "stop_price", new_stop_price),
                "status": getattr(result, "status", "PENDING"),
                "modified_time": getattr(
                    result, "modified_time", datetime.utcnow().isoformat()
                ),
                "filled_quantity": getattr(result, "filled_quantity", 0),
                "remaining_quantity": getattr(result, "remaining_quantity", 0),
            }

        logger.info(f"Successfully modified order: {order_id}")

        return OrderResponse(
            success=True,
            account_id=target_account_id,
            order=order_info,
            order_id=order_id,
        )

    except Exception as e:
        logger.error(f"Failed to modify order {order_id}: {e}")
        return OrderResponse(
            success=False, account_id=account_id or "", order_id=order_id, error=str(e)
        )
