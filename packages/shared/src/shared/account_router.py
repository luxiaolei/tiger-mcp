"""
AccountRouter for routing operations to the correct Tiger accounts.

Provides intelligent routing of trading vs data operations, account selection
based on operation type, load balancing across accounts, and account
availability checks with automatic failover.
"""

import random
from enum import Enum
from typing import Dict, List, Optional, Set

from loguru import logger

# Note: These imports assume the database package is available in the Python path
try:
    from database.models.accounts import (
        AccountStatus,
        AccountType,
        MarketPermission,
        TigerAccount,
    )
except ImportError:
    print(
        "Warning: Database imports not available. Please ensure database package is in Python path."
    )
    raise ImportError("Database package required but not found in Python path")

from .account_manager import get_account_manager
from .token_manager import get_token_manager


class OperationType(str, Enum):
    """Types of operations that can be routed."""

    # Data operations (read-only)
    MARKET_DATA = "market_data"
    QUOTE = "quote"
    HISTORICAL_DATA = "historical_data"
    FUNDAMENTALS = "fundamentals"
    OPTIONS_CHAIN = "options_chain"

    # Trading operations (write)
    PLACE_ORDER = "place_order"
    MODIFY_ORDER = "modify_order"
    CANCEL_ORDER = "cancel_order"

    # Account operations (read/write)
    ACCOUNT_INFO = "account_info"
    POSITIONS = "positions"
    ORDERS = "orders"
    TRANSACTIONS = "transactions"

    # Analysis operations
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    RISK_ANALYSIS = "risk_analysis"


class LoadBalanceStrategy(str, Enum):
    """Load balancing strategies for account selection."""

    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_USED = "least_used"
    FASTEST_RESPONSE = "fastest_response"


class AccountRouterError(Exception):
    """Base exception for account router operations."""


class NoAccountsAvailableError(AccountRouterError):
    """Exception raised when no accounts are available for operation."""


class OperationNotSupportedError(AccountRouterError):
    """Exception raised when operation is not supported by available accounts."""


class AccountRouter:
    """
    Intelligent account routing service for Tiger operations.

    Routes operations to the most appropriate accounts based on operation type,
    account capabilities, availability, and load balancing strategies.
    """

    def __init__(self):
        """Initialize account router."""
        self._account_manager = get_account_manager()
        self._token_manager = get_token_manager()

        # Load balancing state
        self._round_robin_counters: Dict[str, int] = {}
        self._usage_counters: Dict[str, int] = {}
        self._response_times: Dict[str, List[float]] = {}

        # Routing preferences
        self._operation_preferences = self._build_operation_preferences()

        logger.info("AccountRouter initialized")

    async def route_operation(
        self,
        operation_type: OperationType,
        market_permissions: Optional[List[MarketPermission]] = None,
        environment: Optional[str] = None,
        account_type: Optional[AccountType] = None,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_USED,
        exclude_accounts: Optional[Set[str]] = None,
    ) -> TigerAccount:
        """
        Route an operation to the best available account.

        Args:
            operation_type: Type of operation to perform
            market_permissions: Required market permissions
            environment: Required environment (sandbox/production)
            account_type: Required account type
            strategy: Load balancing strategy
            exclude_accounts: Account IDs to exclude

        Returns:
            Selected TigerAccount instance

        Raises:
            NoAccountsAvailableError: If no suitable accounts available
            OperationNotSupportedError: If operation not supported
        """
        try:
            # Get candidate accounts
            candidates = await self._get_candidate_accounts(
                operation_type=operation_type,
                market_permissions=market_permissions,
                environment=environment,
                account_type=account_type,
                exclude_accounts=exclude_accounts,
            )

            if not candidates:
                raise NoAccountsAvailableError(
                    f"No accounts available for {operation_type.value} operation"
                )

            # Apply load balancing strategy
            selected_account = await self._apply_load_balancing(
                candidates, strategy, operation_type
            )

            # Validate token before returning
            if not await self._ensure_valid_token(selected_account):
                # Remove this account and try again
                exclude_accounts = exclude_accounts or set()
                exclude_accounts.add(str(selected_account.id))

                return await self.route_operation(
                    operation_type=operation_type,
                    market_permissions=market_permissions,
                    environment=environment,
                    account_type=account_type,
                    strategy=strategy,
                    exclude_accounts=exclude_accounts,
                )

            # Record usage
            self._record_account_usage(selected_account)

            logger.info(
                f"Routed {operation_type.value} to account {selected_account.account_name} "
                f"using {strategy.value} strategy"
            )

            return selected_account

        except AccountRouterError:
            raise
        except Exception as e:
            logger.error(f"Error routing operation {operation_type.value}: {e}")
            raise AccountRouterError(f"Failed to route operation: {e}")

    async def get_default_trading_account(self) -> Optional[TigerAccount]:
        """
        Get the default trading account with validation.

        Returns:
            Default trading account or None if not available
        """
        try:
            account = await self._account_manager.get_default_trading_account()

            if account and account.is_active:
                # Ensure token is valid
                if await self._ensure_valid_token(account):
                    return account
                else:
                    logger.warning(
                        f"Default trading account {account.account_name} has invalid token"
                    )

            return None

        except Exception as e:
            logger.error(f"Error getting default trading account: {e}")
            return None

    async def get_default_data_account(self) -> Optional[TigerAccount]:
        """
        Get the default data account with validation.

        Returns:
            Default data account or None if not available
        """
        try:
            account = await self._account_manager.get_default_data_account()

            if account and account.is_active:
                # Ensure token is valid
                if await self._ensure_valid_token(account):
                    return account
                else:
                    logger.warning(
                        f"Default data account {account.account_name} has invalid token"
                    )

            return None

        except Exception as e:
            logger.error(f"Error getting default data account: {e}")
            return None

    async def route_trading_operation(
        self,
        operation_type: OperationType,
        market_permissions: Optional[List[MarketPermission]] = None,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_USED,
    ) -> TigerAccount:
        """
        Route a trading operation to the best trading account.

        Args:
            operation_type: Trading operation type
            market_permissions: Required market permissions
            strategy: Load balancing strategy

        Returns:
            Selected trading account
        """
        if not self._is_trading_operation(operation_type):
            raise OperationNotSupportedError(
                f"{operation_type.value} is not a trading operation"
            )

        # Try default trading account first
        default_account = await self.get_default_trading_account()
        if default_account and self._account_supports_operation(
            default_account, operation_type, market_permissions
        ):
            self._record_account_usage(default_account)
            return default_account

        # Route to any suitable trading account
        return await self.route_operation(
            operation_type=operation_type,
            market_permissions=market_permissions,
            strategy=strategy,
        )

    async def route_data_operation(
        self,
        operation_type: OperationType,
        market_permissions: Optional[List[MarketPermission]] = None,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
    ) -> TigerAccount:
        """
        Route a data operation to the best data account.

        Args:
            operation_type: Data operation type
            market_permissions: Required market permissions
            strategy: Load balancing strategy

        Returns:
            Selected data account
        """
        if not self._is_data_operation(operation_type):
            raise OperationNotSupportedError(
                f"{operation_type.value} is not a data operation"
            )

        # Try default data account first
        default_account = await self.get_default_data_account()
        if default_account and self._account_supports_operation(
            default_account, operation_type, market_permissions
        ):
            self._record_account_usage(default_account)
            return default_account

        # Route to any suitable data account
        return await self.route_operation(
            operation_type=operation_type,
            market_permissions=market_permissions,
            strategy=strategy,
        )

    async def get_available_accounts_for_operation(
        self,
        operation_type: OperationType,
        market_permissions: Optional[List[MarketPermission]] = None,
        environment: Optional[str] = None,
    ) -> List[TigerAccount]:
        """
        Get all accounts that can handle a specific operation.

        Args:
            operation_type: Type of operation
            market_permissions: Required market permissions
            environment: Required environment

        Returns:
            List of suitable accounts
        """
        try:
            return await self._get_candidate_accounts(
                operation_type=operation_type,
                market_permissions=market_permissions,
                environment=environment,
            )

        except Exception as e:
            logger.error(f"Error getting available accounts: {e}")
            return []

    async def check_account_availability(self, account: TigerAccount) -> Dict[str, any]:
        """
        Check comprehensive availability of an account.

        Args:
            account: TigerAccount to check

        Returns:
            Dictionary with availability details
        """
        try:
            availability = {
                "account_id": str(account.id),
                "account_name": account.account_name,
                "is_active": account.is_active,
                "environment": account.environment,
                "account_type": account.account_type.value,
                "error_count": account.error_count,
                "last_error": account.last_error,
                "token_valid": False,
                "token_expires_at": account.token_expires_at,
                "needs_refresh": account.needs_token_refresh,
                "market_permissions": account.market_permissions.get("permissions", []),
                "can_trade": False,
                "can_fetch_data": True,
                "usage_count": self._usage_counters.get(str(account.id), 0),
                "avg_response_time": None,
            }

            # Check token validity
            if account.access_token:
                token_valid, token_error = await self._token_manager.validate_token(
                    account
                )
                availability["token_valid"] = token_valid
                availability["token_error"] = token_error

            # Determine capabilities
            availability["can_trade"] = (
                account.is_active
                and availability["token_valid"]
                and account.error_count < 5
            )

            availability["can_fetch_data"] = (
                account.is_active
                and availability["token_valid"]
                and account.error_count < 10
            )

            # Average response time
            account_id = str(account.id)
            if account_id in self._response_times:
                response_times = self._response_times[account_id]
                if response_times:
                    availability["avg_response_time"] = sum(response_times) / len(
                        response_times
                    )

            return availability

        except Exception as e:
            logger.error(f"Error checking account availability: {e}")
            return {
                "account_id": str(account.id),
                "account_name": account.account_name,
                "error": str(e),
            }

    def record_operation_response_time(
        self, account: TigerAccount, response_time_ms: float
    ) -> None:
        """
        Record response time for an account operation.

        Args:
            account: TigerAccount that handled the operation
            response_time_ms: Response time in milliseconds
        """
        account_id = str(account.id)

        if account_id not in self._response_times:
            self._response_times[account_id] = []

        # Keep only last 100 response times
        response_times = self._response_times[account_id]
        response_times.append(response_time_ms)

        if len(response_times) > 100:
            response_times.pop(0)

        logger.debug(
            f"Recorded {response_time_ms:.2f}ms response time for account {account.account_name}"
        )

    async def get_routing_statistics(self) -> Dict[str, any]:
        """
        Get routing statistics and performance metrics.

        Returns:
            Dictionary with routing statistics
        """
        try:
            # Get all accounts
            accounts = await self._account_manager.list_accounts(include_inactive=True)

            stats = {
                "total_accounts": len(accounts),
                "active_accounts": len([a for a in accounts if a.is_active]),
                "accounts_with_errors": len([a for a in accounts if a.error_count > 0]),
                "usage_distribution": dict(self._usage_counters),
                "average_response_times": {},
                "account_details": [],
            }

            # Calculate average response times
            for account_id, response_times in self._response_times.items():
                if response_times:
                    stats["average_response_times"][account_id] = sum(
                        response_times
                    ) / len(response_times)

            # Get detailed account info
            for account in accounts:
                availability = await self.check_account_availability(account)
                stats["account_details"].append(availability)

            return stats

        except Exception as e:
            logger.error(f"Error getting routing statistics: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _get_candidate_accounts(
        self,
        operation_type: OperationType,
        market_permissions: Optional[List[MarketPermission]] = None,
        environment: Optional[str] = None,
        account_type: Optional[AccountType] = None,
        exclude_accounts: Optional[Set[str]] = None,
    ) -> List[TigerAccount]:
        """Get accounts that could handle the operation."""
        try:
            # Get all active accounts
            accounts = await self._account_manager.list_accounts(
                account_type=account_type,
                status=AccountStatus.ACTIVE,
                environment=environment,
            )

            candidates = []
            exclude_accounts = exclude_accounts or set()

            for account in accounts:
                # Skip excluded accounts
                if str(account.id) in exclude_accounts:
                    continue

                # Check if account supports this operation
                if not self._account_supports_operation(
                    account, operation_type, market_permissions
                ):
                    continue

                # Check error threshold
                if (
                    self._is_trading_operation(operation_type)
                    and account.error_count >= 5
                ):
                    continue

                if (
                    self._is_data_operation(operation_type)
                    and account.error_count >= 10
                ):
                    continue

                candidates.append(account)

            return candidates

        except Exception as e:
            logger.error(f"Error getting candidate accounts: {e}")
            return []

    def _account_supports_operation(
        self,
        account: TigerAccount,
        operation_type: OperationType,
        market_permissions: Optional[List[MarketPermission]] = None,
    ) -> bool:
        """Check if account supports the operation."""
        try:
            # Check market permissions
            if market_permissions:
                for permission in market_permissions:
                    if not account.has_market_permission(permission):
                        return False

            # Check operation-specific requirements
            if operation_type in [
                OperationType.PLACE_ORDER,
                OperationType.MODIFY_ORDER,
                OperationType.CANCEL_ORDER,
            ]:
                # Trading operations need production environment for real trading
                # or paper account for testing
                if (
                    account.environment == "production"
                    or account.account_type == AccountType.PAPER
                ):
                    return True
                return False

            # Data operations are generally supported by all accounts
            return True

        except Exception as e:
            logger.error(f"Error checking account support: {e}")
            return False

    async def _apply_load_balancing(
        self,
        candidates: List[TigerAccount],
        strategy: LoadBalanceStrategy,
        operation_type: OperationType,
    ) -> TigerAccount:
        """Apply load balancing strategy to select account."""
        if len(candidates) == 1:
            return candidates[0]

        operation_key = f"{operation_type.value}_{strategy.value}"

        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            counter = self._round_robin_counters.get(operation_key, 0)
            selected = candidates[counter % len(candidates)]
            self._round_robin_counters[operation_key] = counter + 1
            return selected

        elif strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(candidates)

        elif strategy == LoadBalanceStrategy.LEAST_USED:
            # Select account with lowest usage count
            def get_usage(account):
                return self._usage_counters.get(str(account.id), 0)

            return min(candidates, key=get_usage)

        elif strategy == LoadBalanceStrategy.FASTEST_RESPONSE:
            # Select account with fastest average response time
            def get_avg_response_time(account):
                account_id = str(account.id)
                if account_id in self._response_times:
                    response_times = self._response_times[account_id]
                    if response_times:
                        return sum(response_times) / len(response_times)
                return float("inf")  # No data = lowest priority

            return min(candidates, key=get_avg_response_time)

        else:
            # Default to random
            return random.choice(candidates)

    async def _ensure_valid_token(self, account: TigerAccount) -> bool:
        """Ensure account has a valid token, refreshing if needed."""
        try:
            if account.has_valid_token and not account.needs_token_refresh:
                return True

            # Token needs refresh
            logger.info(f"Refreshing token for account {account.account_name}")
            success, error = await self._token_manager.refresh_token(account)

            if not success:
                logger.error(
                    f"Failed to refresh token for account {account.account_name}: {error}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error ensuring valid token: {e}")
            return False

    def _record_account_usage(self, account: TigerAccount) -> None:
        """Record usage of an account."""
        account_id = str(account.id)
        self._usage_counters[account_id] = self._usage_counters.get(account_id, 0) + 1

    def _is_trading_operation(self, operation_type: OperationType) -> bool:
        """Check if operation is a trading operation."""
        return operation_type in [
            OperationType.PLACE_ORDER,
            OperationType.MODIFY_ORDER,
            OperationType.CANCEL_ORDER,
        ]

    def _is_data_operation(self, operation_type: OperationType) -> bool:
        """Check if operation is a data operation."""
        return operation_type in [
            OperationType.MARKET_DATA,
            OperationType.QUOTE,
            OperationType.HISTORICAL_DATA,
            OperationType.FUNDAMENTALS,
            OperationType.OPTIONS_CHAIN,
        ]

    def _build_operation_preferences(self) -> Dict[OperationType, Dict]:
        """Build operation preferences and requirements."""
        return {
            OperationType.MARKET_DATA: {
                "preferred_account_type": None,
                "required_permissions": [],
                "priority": "data",
            },
            OperationType.QUOTE: {
                "preferred_account_type": None,
                "required_permissions": [],
                "priority": "data",
            },
            OperationType.HISTORICAL_DATA: {
                "preferred_account_type": None,
                "required_permissions": [],
                "priority": "data",
            },
            OperationType.PLACE_ORDER: {
                "preferred_account_type": AccountType.STANDARD,
                "required_permissions": [],
                "priority": "trading",
            },
            OperationType.MODIFY_ORDER: {
                "preferred_account_type": AccountType.STANDARD,
                "required_permissions": [],
                "priority": "trading",
            },
            OperationType.CANCEL_ORDER: {
                "preferred_account_type": AccountType.STANDARD,
                "required_permissions": [],
                "priority": "trading",
            },
        }


# Global account router instance
_account_router: Optional[AccountRouter] = None


def get_account_router() -> AccountRouter:
    """Get global account router instance."""
    global _account_router
    if _account_router is None:
        _account_router = AccountRouter()
    return _account_router
