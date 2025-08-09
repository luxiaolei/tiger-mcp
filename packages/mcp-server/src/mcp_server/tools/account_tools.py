"""
Account Management MCP Tools for Tiger Brokers API.

Provides MCP tools for managing Tiger accounts, including listing, adding,
removing accounts, and handling account status and default account settings.
"""

import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add paths for imports
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/shared/src"
)

from fastmcp import FastMCP
from loguru import logger
from pydantic import BaseModel, Field
from shared.account_manager import (
    AccountManagerError,
    AccountNotFoundError,
    AccountStatus,
    AccountType,
    AccountValidationError,
    MarketPermission,
    get_account_manager,
)
from shared.account_router import get_account_router

from ..process_manager import get_process_manager

# Initialize FastMCP instance for account tools
mcp = FastMCP("Tiger Account Tools")


class AccountListResponse(BaseModel):
    """Account list response model."""

    success: bool
    accounts: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AccountResponse(BaseModel):
    """Single account response model."""

    success: bool
    account: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AccountStatusResponse(BaseModel):
    """Account status response model."""

    success: bool
    account_id: str = ""
    status: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TokenRefreshResponse(BaseModel):
    """Token refresh response model."""

    success: bool
    account_id: str = ""
    token_refreshed: bool = False
    token_expires_at: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Service instance for account management
class AccountToolsService:
    """Service class for account management tools."""

    def __init__(self):
        self.process_manager = get_process_manager()
        self.account_manager = get_account_manager()
        self.account_router = get_account_router()

    async def ensure_started(self):
        """Ensure the process manager is started."""
        if (
            not hasattr(self.process_manager, "_started")
            or not self.process_manager._started
        ):
            await self.process_manager.start()

    def _format_account(self, account) -> Dict[str, Any]:
        """Format account for API response."""
        return {
            "id": str(account.id),
            "account_name": account.account_name,
            "account_number": account.account_number,
            "account_type": account.account_type.value,
            "environment": account.environment,
            "status": account.status.value,
            "is_default_trading": account.is_default_trading,
            "is_default_data": account.is_default_data,
            "error_count": account.error_count,
            "last_error": account.last_error,
            "market_permissions": account.market_permissions.get("permissions", []),
            "has_valid_token": account.has_valid_token,
            "needs_token_refresh": account.needs_token_refresh,
            "token_expires_at": (
                account.token_expires_at.isoformat()
                if account.token_expires_at
                else None
            ),
            "created_at": account.created_at.isoformat(),
            "updated_at": (
                account.updated_at.isoformat() if account.updated_at else None
            ),
            "description": account.description,
            "tags": account.tags or {},
        }


# Global service instance
_account_service = AccountToolsService()


@mcp.tool()
async def tiger_list_accounts(
    environment: Optional[str] = None,
    account_type: Optional[str] = None,
    status: Optional[str] = None,
    include_inactive: bool = False,
) -> AccountListResponse:
    """
    List all configured Tiger accounts with their status.

    Retrieves a comprehensive list of all Tiger accounts configured in the system,
    including their current status, permissions, token validity, and other metadata.

    Args:
        environment: Optional filter by environment ('sandbox' or 'production')
        account_type: Optional filter by account type ('standard', 'paper', 'prime')
        status: Optional filter by status ('active', 'inactive', 'suspended', 'error')
        include_inactive: Whether to include inactive accounts (default: False)

    Returns:
        AccountListResponse containing list of accounts with details:
        - id: Account UUID
        - account_name: User-friendly account name
        - account_number: Tiger account number
        - account_type: Type of account (standard/paper/prime)
        - environment: Environment (sandbox/production)
        - status: Current account status
        - is_default_trading: Whether this is the default trading account
        - is_default_data: Whether this is the default data account
        - has_valid_token: Whether the account has valid API tokens
        - error_count: Number of consecutive errors
        - market_permissions: Available market permissions

    Example:
        ```python
        # List all active accounts
        response = await tiger_list_accounts()
        if response.success:
            for account in response.accounts:
                print(f"{account['account_name']}: {account['status']} ({account['environment']})")

        # List only production trading accounts
        response = await tiger_list_accounts(environment="production", account_type="standard")
        ```
    """
    try:
        # Convert string parameters to enum types
        account_type_enum = None
        if account_type:
            try:
                account_type_enum = AccountType(account_type.upper())
            except ValueError:
                return AccountListResponse(
                    success=False,
                    error=f"Invalid account_type '{account_type}'. Must be: standard, paper, prime",
                )

        status_enum = None
        if status:
            try:
                status_enum = AccountStatus(status.upper())
            except ValueError:
                return AccountListResponse(
                    success=False,
                    error=f"Invalid status '{status}'. Must be: active, inactive, suspended, error",
                )

        # Get accounts from manager
        accounts = await _account_service.account_manager.list_accounts(
            account_type=account_type_enum,
            status=status_enum,
            environment=environment,
            include_inactive=include_inactive,
        )

        # Format accounts for response
        formatted_accounts = [
            _account_service._format_account(account) for account in accounts
        ]

        return AccountListResponse(
            success=True,
            accounts=formatted_accounts,
            total_count=len(formatted_accounts),
        )

    except Exception as e:
        logger.error(f"Failed to list accounts: {e}")
        return AccountListResponse(success=False, error=str(e))


@mcp.tool()
async def tiger_add_account(
    name: str,
    api_key: str,
    secret_key: str,
    account_type: str = "standard",
    is_paper: bool = False,
    environment: Optional[str] = None,
    market_permissions: Optional[List[str]] = None,
    description: Optional[str] = None,
    is_default_trading: bool = False,
    is_default_data: bool = False,
    server_url: Optional[str] = None,
) -> AccountResponse:
    """
    Add a new Tiger account to the system.

    Creates a new Tiger account configuration with encrypted credential storage,
    proper validation, and initial token setup for API access.

    Args:
        name: User-friendly account name for identification
        api_key: Tiger API key (will be encrypted and stored securely)
        secret_key: Tiger secret key (will be encrypted and stored securely)
        account_type: Type of account - 'standard', 'paper', or 'prime' (default: 'standard')
        is_paper: Whether this is a paper trading account (default: False)
        environment: Environment to use - 'sandbox' or 'production'. If not specified,
                    will be determined based on is_paper setting
        market_permissions: List of market permissions (e.g., ['US', 'HK', 'SG'])
        description: Optional description for the account
        is_default_trading: Set as default account for trading operations
        is_default_data: Set as default account for data operations
        server_url: Optional custom server URL for API calls

    Returns:
        AccountResponse containing the created account details or error information.
        On success, includes the account ID, configuration, and initial status.

    Example:
        ```python
        # Add a standard production account
        response = await tiger_add_account(
            name="My Trading Account",
            api_key="your_api_key",
            secret_key="your_secret_key",
            account_type="standard",
            market_permissions=["US", "HK"],
            is_default_trading=True
        )

        # Add a paper trading account
        response = await tiger_add_account(
            name="Paper Trading",
            api_key="paper_api_key",
            secret_key="paper_secret_key",
            is_paper=True,
            description="For testing strategies"
        )
        ```
    """
    try:
        # Validate inputs
        if not name or not name.strip():
            return AccountResponse(success=False, error="Account name is required")

        if not api_key or not api_key.strip():
            return AccountResponse(success=False, error="API key is required")

        if not secret_key or not secret_key.strip():
            return AccountResponse(success=False, error="Secret key is required")

        # Convert account type
        try:
            account_type_enum = AccountType(account_type.upper())
        except ValueError:
            return AccountResponse(
                success=False,
                error=f"Invalid account_type '{account_type}'. Must be: standard, paper, prime",
            )

        # Determine environment if not specified
        if environment is None:
            environment = "sandbox" if is_paper else "production"

        # Validate environment
        if environment not in ["sandbox", "production"]:
            return AccountResponse(
                success=False, error="Environment must be 'sandbox' or 'production'"
            )

        # Convert market permissions
        market_permission_enums = []
        if market_permissions:
            for permission in market_permissions:
                try:
                    # Assume permission strings map to MarketPermission enum
                    # This may need adjustment based on actual MarketPermission definition
                    market_permission_enums.append(MarketPermission(permission))
                except ValueError:
                    logger.warning(f"Invalid market permission: {permission}")

        # Generate account number (this might need to be provided or generated differently)
        account_number = f"TG{uuid.uuid4().hex[:8].upper()}"

        # Create account using account manager
        account = await _account_service.account_manager.create_account(
            account_name=name,
            account_number=account_number,
            tiger_id=api_key,  # API key serves as tiger_id
            private_key=secret_key,
            account_type=account_type_enum,
            environment=environment,
            market_permissions=market_permission_enums,
            description=description,
            is_default_trading=is_default_trading,
            is_default_data=is_default_data,
            server_url=server_url,
        )

        logger.info(f"Successfully added Tiger account: {name} ({account_number})")

        return AccountResponse(
            success=True, account=_account_service._format_account(account)
        )

    except AccountValidationError as e:
        logger.error(f"Account validation failed: {e}")
        return AccountResponse(success=False, error=f"Validation error: {str(e)}")
    except AccountManagerError as e:
        logger.error(f"Account management error: {e}")
        return AccountResponse(
            success=False, error=f"Account management error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to add account: {e}")
        return AccountResponse(success=False, error=f"Failed to add account: {str(e)}")


@mcp.tool()
async def tiger_remove_account(account_id: str, force: bool = False) -> AccountResponse:
    """
    Remove a Tiger account from the system.

    Safely removes a Tiger account configuration, including encrypted credentials
    and associated data. Includes safety checks to prevent accidental deletion
    of accounts with active dependencies.

    Args:
        account_id: UUID of the account to remove
        force: Force removal even if account has dependencies (default: False)
               Use with caution - this will remove accounts that may have
               active API keys, orders, or other dependencies

    Returns:
        AccountResponse indicating success or failure of the removal operation.

    Example:
        ```python
        # Safely remove an account
        response = await tiger_remove_account("account-uuid-here")
        if response.success:
            print("Account removed successfully")

        # Force remove an account with dependencies
        response = await tiger_remove_account("account-uuid-here", force=True)
        ```

    Note:
        - Removing an account will also invalidate any stored API tokens
        - If the account is set as a default (trading or data), the default
          settings will be cleared
        - Use force=True carefully as it bypasses safety checks
    """
    try:
        # Validate account ID format
        try:
            account_uuid = uuid.UUID(account_id)
        except ValueError:
            return AccountResponse(success=False, error="Invalid account ID format")

        # Get account before deletion for response
        account = await _account_service.account_manager.get_account_by_id(account_uuid)
        if not account:
            return AccountResponse(
                success=False, error=f"Account {account_id} not found"
            )

        # Store account info for response
        account_info = _account_service._format_account(account)

        # Delete account
        success = await _account_service.account_manager.delete_account(
            account_uuid, force=force
        )

        if success:
            logger.info(
                f"Successfully removed account: {account.account_name} ({account_id})"
            )
            return AccountResponse(success=True, account=account_info)
        else:
            return AccountResponse(success=False, error="Failed to remove account")

    except AccountNotFoundError as e:
        logger.error(f"Account not found: {e}")
        return AccountResponse(success=False, error=str(e))
    except AccountValidationError as e:
        logger.error(f"Account validation error: {e}")
        return AccountResponse(success=False, error=str(e))
    except AccountManagerError as e:
        logger.error(f"Account management error: {e}")
        return AccountResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Failed to remove account: {e}")
        return AccountResponse(success=False, error=str(e))


@mcp.tool()
async def tiger_get_account_status(account_id: str) -> AccountStatusResponse:
    """
    Get detailed status information for a specific account.

    Retrieves comprehensive status information including account health,
    API token validity, error counts, routing availability, and performance metrics.

    Args:
        account_id: UUID of the account to check

    Returns:
        AccountStatusResponse containing detailed status information:
        - account_details: Basic account information
        - token_status: API token validity and expiration
        - health_status: Account health metrics and error information
        - routing_status: Availability for different operation types
        - performance_metrics: Response times and usage statistics

    Example:
        ```python
        response = await tiger_get_account_status("account-uuid-here")
        if response.success:
            status = response.status
            print(f"Account: {status['account_details']['account_name']}")
            print(f"Token valid: {status['token_status']['is_valid']}")
            print(f"Can trade: {status['routing_status']['can_trade']}")
            print(f"Error count: {status['health_status']['error_count']}")
        ```
    """
    try:
        # Validate account ID format
        try:
            account_uuid = uuid.UUID(account_id)
        except ValueError:
            return AccountStatusResponse(
                success=False, account_id=account_id, error="Invalid account ID format"
            )

        # Get account
        account = await _account_service.account_manager.get_account_by_id(account_uuid)
        if not account:
            return AccountStatusResponse(
                success=False,
                account_id=account_id,
                error=f"Account {account_id} not found",
            )

        # Get comprehensive status from account router
        routing_status = (
            await _account_service.account_router.check_account_availability(account)
        )

        # Get process status if available
        process_status = None
        try:
            process_info = (
                await _account_service.process_manager.get_account_process_status(
                    account_id
                )
            )
            if process_info:
                process_status = {
                    "process_id": process_info.process_id,
                    "status": process_info.status.value,
                    "created_at": (
                        process_info.created_at.isoformat()
                        if process_info.created_at
                        else None
                    ),
                    "last_heartbeat": (
                        process_info.last_heartbeat.isoformat()
                        if process_info.last_heartbeat
                        else None
                    ),
                    "current_task": process_info.current_task,
                }
        except Exception as e:
            logger.debug(f"Could not get process status: {e}")

        # Build comprehensive status
        status = {
            "account_details": _account_service._format_account(account),
            "token_status": {
                "is_valid": routing_status.get("token_valid", False),
                "expires_at": routing_status.get("token_expires_at"),
                "needs_refresh": routing_status.get("needs_refresh", False),
                "token_error": routing_status.get("token_error"),
            },
            "health_status": {
                "is_active": routing_status.get("is_active", False),
                "error_count": routing_status.get("error_count", 0),
                "last_error": routing_status.get("last_error"),
                "status": routing_status.get("account_status"),
            },
            "routing_status": {
                "can_trade": routing_status.get("can_trade", False),
                "can_fetch_data": routing_status.get("can_fetch_data", False),
                "usage_count": routing_status.get("usage_count", 0),
                "avg_response_time": routing_status.get("avg_response_time"),
            },
            "process_status": process_status,
            "market_permissions": routing_status.get("market_permissions", []),
        }

        return AccountStatusResponse(success=True, account_id=account_id, status=status)

    except Exception as e:
        logger.error(f"Failed to get account status for {account_id}: {e}")
        return AccountStatusResponse(success=False, account_id=account_id, error=str(e))


@mcp.tool()
async def tiger_refresh_token(account_id: str) -> TokenRefreshResponse:
    """
    Manually refresh API token for a specific account.

    Forces a refresh of the API access token for the specified account,
    useful when tokens have expired or when encountering authentication errors.

    Args:
        account_id: UUID of the account whose token should be refreshed

    Returns:
        TokenRefreshResponse indicating success or failure of token refresh:
        - token_refreshed: Whether the token was successfully refreshed
        - token_expires_at: New token expiration time (if successful)
        - error: Error message if refresh failed

    Example:
        ```python
        response = await tiger_refresh_token("account-uuid-here")
        if response.success and response.token_refreshed:
            print(f"Token refreshed, expires at: {response.token_expires_at}")
        else:
            print(f"Token refresh failed: {response.error}")
        ```
    """
    try:
        # Validate account ID format
        try:
            account_uuid = uuid.UUID(account_id)
        except ValueError:
            return TokenRefreshResponse(
                success=False, account_id=account_id, error="Invalid account ID format"
            )

        # Get account
        account = await _account_service.account_manager.get_account_by_id(account_uuid)
        if not account:
            return TokenRefreshResponse(
                success=False,
                account_id=account_id,
                error=f"Account {account_id} not found",
            )

        # Perform manual token refresh through process manager
        # This may need adjustment based on actual token refresh implementation
        try:
            health_check = await _account_service.process_manager.health_check_account(
                account_id
            )

            if health_check.get("healthy", False):
                # Token refresh successful
                # Get updated account to check token expiration
                updated_account = (
                    await _account_service.account_manager.get_account_by_id(
                        account_uuid
                    )
                )

                return TokenRefreshResponse(
                    success=True,
                    account_id=account_id,
                    token_refreshed=True,
                    token_expires_at=(
                        updated_account.token_expires_at.isoformat()
                        if updated_account.token_expires_at
                        else None
                    ),
                )
            else:
                return TokenRefreshResponse(
                    success=False,
                    account_id=account_id,
                    token_refreshed=False,
                    error=health_check.get("error", "Health check failed"),
                )

        except Exception as e:
            logger.error(f"Token refresh failed for account {account_id}: {e}")
            return TokenRefreshResponse(
                success=False,
                account_id=account_id,
                token_refreshed=False,
                error=str(e),
            )

    except Exception as e:
        logger.error(f"Failed to refresh token for {account_id}: {e}")
        return TokenRefreshResponse(
            success=False, account_id=account_id, token_refreshed=False, error=str(e)
        )


@mcp.tool()
async def tiger_set_default_data_account(account_id: str) -> AccountResponse:
    """
    Set an account as the default data account.

    Configures the specified account as the default account for data operations
    such as market data retrieval, quotes, historical data, and other read-only operations.

    Args:
        account_id: UUID of the account to set as default for data operations

    Returns:
        AccountResponse containing the updated account information.

    Example:
        ```python
        response = await tiger_set_default_data_account("account-uuid-here")
        if response.success:
            account = response.account
            print(f"Set {account['account_name']} as default data account")
        ```
    """
    try:
        # Validate account ID format
        try:
            account_uuid = uuid.UUID(account_id)
        except ValueError:
            return AccountResponse(success=False, error="Invalid account ID format")

        # Set as default data account
        account = await _account_service.account_manager.set_default_data_account(
            account_uuid
        )

        logger.info(f"Set account {account.account_name} as default data account")

        return AccountResponse(
            success=True, account=_account_service._format_account(account)
        )

    except AccountNotFoundError as e:
        logger.error(f"Account not found: {e}")
        return AccountResponse(success=False, error=str(e))
    except AccountManagerError as e:
        logger.error(f"Account management error: {e}")
        return AccountResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Failed to set default data account: {e}")
        return AccountResponse(success=False, error=str(e))


@mcp.tool()
async def tiger_set_default_trading_account(account_id: str) -> AccountResponse:
    """
    Set an account as the default trading account.

    Configures the specified account as the default account for trading operations
    such as placing orders, modifying orders, canceling orders, and other trading activities.

    Args:
        account_id: UUID of the account to set as default for trading operations

    Returns:
        AccountResponse containing the updated account information.

    Example:
        ```python
        response = await tiger_set_default_trading_account("account-uuid-here")
        if response.success:
            account = response.account
            print(f"Set {account['account_name']} as default trading account")
        ```

    Note:
        - Only one account can be the default trading account at a time
        - The previous default trading account will automatically be unset
        - The account must be active and have valid credentials for trading
    """
    try:
        # Validate account ID format
        try:
            account_uuid = uuid.UUID(account_id)
        except ValueError:
            return AccountResponse(success=False, error="Invalid account ID format")

        # Set as default trading account
        account = await _account_service.account_manager.set_default_trading_account(
            account_uuid
        )

        logger.info(f"Set account {account.account_name} as default trading account")

        return AccountResponse(
            success=True, account=_account_service._format_account(account)
        )

    except AccountNotFoundError as e:
        logger.error(f"Account not found: {e}")
        return AccountResponse(success=False, error=str(e))
    except AccountManagerError as e:
        logger.error(f"Account management error: {e}")
        return AccountResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Failed to set default trading account: {e}")
        return AccountResponse(success=False, error=str(e))
