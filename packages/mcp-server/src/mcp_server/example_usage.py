"""
Example usage of Tiger Process Pool Manager.

Demonstrates how to integrate the process pool with MCP server endpoints
and handle Tiger API calls with account isolation.
"""

import asyncio
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

# Add paths for imports
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/shared/src"
)
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/database/src"
)

from loguru import logger
from .process_manager import get_process_manager
from shared.account_manager import AccountStatus, get_account_manager
from shared.account_router import get_account_router


class TigerAPIService:
    """
    High-level Tiger API service using process pool manager.

    Provides a clean interface for MCP server endpoints to execute
    Tiger API calls with automatic account routing and process management.
    """

    def __init__(self):
        """Initialize the Tiger API service."""
        self.process_manager = get_process_manager()
        self.account_manager = get_account_manager()
        self.account_router = get_account_router()
        self._started = False

    async def start(self) -> None:
        """Start the Tiger API service."""
        if not self._started:
            await self.process_manager.start()
            self._started = True
            logger.info("TigerAPIService started")

    async def stop(self) -> None:
        """Stop the Tiger API service."""
        if self._started:
            await self.process_manager.stop()
            self._started = False
            logger.info("TigerAPIService stopped")

    async def get_account_info(
        self, account_id: Optional[str] = None, use_default: bool = True
    ) -> Dict[str, Any]:
        """
        Get account information.

        Args:
            account_id: Specific account ID, or None to use default/routing
            use_default: Use default trading account if no account_id specified

        Returns:
            Account information
        """
        try:
            # Route to appropriate account
            target_account_id = await self._route_account(
                account_id, use_default, "trading"
            )

            # Execute API call
            result = await self.process_manager.execute_api_call(
                account_id=target_account_id, method="trade.get_account", timeout=10.0
            )

            return {
                "success": True,
                "account_id": target_account_id,
                "data": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_positions(
        self, account_id: Optional[str] = None, use_default: bool = True
    ) -> Dict[str, Any]:
        """
        Get account positions.

        Args:
            account_id: Specific account ID, or None to use default/routing
            use_default: Use default trading account if no account_id specified

        Returns:
            Position information
        """
        try:
            # Route to appropriate account
            target_account_id = await self._route_account(
                account_id, use_default, "trading"
            )

            # Execute API call
            result = await self.process_manager.execute_api_call(
                account_id=target_account_id, method="trade.get_positions", timeout=10.0
            )

            return {
                "success": True,
                "account_id": target_account_id,
                "data": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_quote(
        self, symbol: str, account_id: Optional[str] = None, use_default: bool = True
    ) -> Dict[str, Any]:
        """
        Get stock quote.

        Args:
            symbol: Stock symbol
            account_id: Specific account ID, or None to use default/routing
            use_default: Use default data account if no account_id specified

        Returns:
            Quote information
        """
        try:
            # Route to appropriate account (prefer data account for quotes)
            target_account_id = await self._route_account(
                account_id, use_default, "data"
            )

            # Execute API call
            result = await self.process_manager.execute_api_call(
                account_id=target_account_id,
                method="quote.get_quote_brief",
                args=[symbol],
                timeout=10.0,
            )

            return {
                "success": True,
                "account_id": target_account_id,
                "symbol": symbol,
                "data": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: str = "MKT",
        price: Optional[float] = None,
        account_id: Optional[str] = None,
        use_default: bool = True,
    ) -> Dict[str, Any]:
        """
        Place a trading order.

        Args:
            symbol: Stock symbol
            action: Order action (BUY/SELL)
            quantity: Order quantity
            order_type: Order type (MKT, LMT, etc.)
            price: Limit price (required for limit orders)
            account_id: Specific account ID, or None to use default/routing
            use_default: Use default trading account if no account_id specified

        Returns:
            Order placement result
        """
        try:
            # Route to appropriate account (always use trading account for orders)
            target_account_id = await self._route_account(
                account_id, use_default, "trading"
            )

            # Prepare order parameters
            order_params = {
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "order_type": order_type,
            }

            if price is not None:
                order_params["price"] = price

            # Execute API call
            result = await self.process_manager.execute_api_call(
                account_id=target_account_id,
                method="trade.place_order",
                kwargs=order_params,
                timeout=15.0,
            )

            return {
                "success": True,
                "account_id": target_account_id,
                "order_params": order_params,
                "data": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_params": {
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "order_type": order_type,
                    "price": price,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_orders(
        self,
        account_id: Optional[str] = None,
        use_default: bool = True,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get order history.

        Args:
            account_id: Specific account ID, or None to use default/routing
            use_default: Use default trading account if no account_id specified
            status: Filter by order status

        Returns:
            Order history
        """
        try:
            # Route to appropriate account
            target_account_id = await self._route_account(
                account_id, use_default, "trading"
            )

            # Prepare parameters
            params = {}
            if status:
                params["status"] = status

            # Execute API call
            result = await self.process_manager.execute_api_call(
                account_id=target_account_id,
                method="trade.get_orders",
                kwargs=params,
                timeout=10.0,
            )

            return {
                "success": True,
                "account_id": target_account_id,
                "data": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_market_status(
        self,
        market: str = "US",
        account_id: Optional[str] = None,
        use_default: bool = True,
    ) -> Dict[str, Any]:
        """
        Get market status.

        Args:
            market: Market code (US, HK, etc.)
            account_id: Specific account ID, or None to use default/routing
            use_default: Use default data account if no account_id specified

        Returns:
            Market status information
        """
        try:
            # Route to appropriate account (prefer data account for market info)
            target_account_id = await self._route_account(
                account_id, use_default, "data"
            )

            # Execute API call
            result = await self.process_manager.execute_api_call(
                account_id=target_account_id,
                method="quote.get_market_status",
                args=[market],
                timeout=10.0,
            )

            return {
                "success": True,
                "account_id": target_account_id,
                "market": market,
                "data": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get market status: {e}")
            return {
                "success": False,
                "error": str(e),
                "market": market,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def health_check_all(self) -> Dict[str, Any]:
        """
        Perform health check on all accounts and processes.

        Returns:
            Health check results
        """
        try:
            # Get system metrics
            system_metrics = await self.process_manager.get_system_metrics()

            # Run health checks on all accounts
            health_results = await self.process_manager.health_check_all_accounts()

            # Get process metrics
            process_metrics = await self.process_manager.get_process_metrics()

            # Summarize health status
            healthy_accounts = sum(1 for r in health_results if r["healthy"])
            total_accounts = len(health_results)

            return {
                "success": True,
                "system_health": {
                    "total_processes": system_metrics.get("total_processes", 0),
                    "healthy_accounts": healthy_accounts,
                    "total_accounts": total_accounts,
                    "system_success_rate": system_metrics.get("success_rate", 0),
                    "average_response_time": system_metrics.get(
                        "average_response_time", 0
                    ),
                },
                "account_health": health_results,
                "process_metrics": {
                    pid: {
                        "total_tasks": metrics.total_tasks,
                        "success_rate": metrics.success_rate,
                        "error_rate": metrics.error_rate,
                        "average_response_time": metrics.average_response_time,
                        "uptime_seconds": metrics.uptime_seconds,
                    }
                    for pid, metrics in process_metrics.items()
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    # Private methods

    async def _route_account(
        self, account_id: Optional[str], use_default: bool, operation_type: str
    ) -> str:
        """
        Route request to appropriate account.

        Args:
            account_id: Specific account ID
            use_default: Use default account if no account_id
            operation_type: Type of operation (trading, data)

        Returns:
            Target account ID

        Raises:
            ValueError: If no suitable account found
        """
        if account_id:
            # Validate specific account
            account = await self.account_manager.get_account_by_id(
                uuid.UUID(account_id)
            )
            if not account:
                raise ValueError(f"Account {account_id} not found")
            if account.status != AccountStatus.ACTIVE:
                raise ValueError(f"Account {account.account_number} is not active")
            return account_id

        elif use_default:
            # Use default account
            if operation_type == "trading":
                account = await self.account_manager.get_default_trading_account()
                if not account:
                    raise ValueError("No default trading account configured")
            else:  # data operations
                account = await self.account_manager.get_default_data_account()
                if not account:
                    # Fall back to trading account for data operations
                    account = await self.account_manager.get_default_trading_account()
                    if not account:
                        raise ValueError(
                            "No default data or trading account configured"
                        )

            return str(account.id)

        else:
            # Use routing logic
            target_account = await self.account_router.route_request(operation_type)
            if not target_account:
                raise ValueError(
                    f"No suitable account found for {operation_type} operations"
                )
            return str(target_account.id)


async def demo_usage():
    """Demonstrate usage of the Tiger API service."""
    logger.info("=== Tiger API Service Demo ===")

    # Initialize service
    api_service = TigerAPIService()

    try:
        # Start the service
        await api_service.start()
        logger.info("Tiger API service started")

        # Example 1: Health check
        logger.info("\n1. Performing system health check...")
        health = await api_service.health_check_all()
        logger.info(f"System health: {health['success']}")

        if health["success"]:
            logger.info(
                f"Healthy accounts: {health['system_health']['healthy_accounts']}"
            )
            logger.info(
                f"Total processes: {health['system_health']['total_processes']}"
            )

        # Example 2: Get market status
        logger.info("\n2. Getting market status...")
        market_status = await api_service.get_market_status("US")
        logger.info(f"Market status request: {market_status['success']}")

        # Example 3: Get quote
        logger.info("\n3. Getting stock quote...")
        quote = await api_service.get_quote("AAPL")
        logger.info(f"Quote request: {quote['success']}")

        # Example 4: Get account info
        logger.info("\n4. Getting account information...")
        account_info = await api_service.get_account_info()
        logger.info(f"Account info request: {account_info['success']}")

        # Example 5: Get positions
        logger.info("\n5. Getting positions...")
        positions = await api_service.get_positions()
        logger.info(f"Positions request: {positions['success']}")

        # Note: Order placement would require valid credentials and permissions
        logger.info("\n6. Order operations (would require valid credentials)...")
        logger.info("   - place_order() for actual trading")
        logger.info("   - get_orders() for order history")

        logger.info("\n=== Demo completed successfully ===")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback

        logger.error(traceback.format_exc())

    finally:
        # Clean up
        await api_service.stop()
        logger.info("Tiger API service stopped")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>demo</cyan> | <level>{message}</level>",
        level="INFO",
    )

    # Run demo
    asyncio.run(demo_usage())
