"""
TokenManager for Tiger API token management and refresh automation.

Provides comprehensive token management including refresh automation,
expiration monitoring, retry logic with exponential backoff, and
integration with Tiger API for token operations.
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import httpx
from loguru import logger
from sqlalchemy import select

# Note: These imports assume the database package is available in the Python path
try:
    from database.engine import get_session
    from database.models.accounts import TigerAccount
    from database.models.token_status import (
        RefreshTrigger,
        TokenRefreshStatus,
        TokenStatus,
    )
except ImportError:
    print(
        "Warning: Database imports not available. Please ensure database package is in Python path."
    )
    raise ImportError("Database package required but not found in Python path")

from .account_manager import get_account_manager
from .config import get_tiger_api_config
from .encryption import get_encryption_service


class TokenManagerError(Exception):
    """Base exception for token manager operations."""


class TokenRefreshError(TokenManagerError):
    """Exception raised when token refresh fails."""


class TokenValidationError(TokenManagerError):
    """Exception raised when token validation fails."""


class TokenRateLimitError(TokenManagerError):
    """Exception raised when rate limit is exceeded."""


class TokenManager:
    """
    Comprehensive Tiger API token management service.

    Handles token refresh automation, expiration monitoring, retry logic
    with exponential backoff, and integration with Tiger API.
    """

    def __init__(self):
        """Initialize token manager."""
        self._config = get_tiger_api_config()
        self._account_manager = get_account_manager()
        self._encryption_service = get_encryption_service()
        self._refresh_locks: Dict[str, asyncio.Lock] = {}
        self._refresh_tasks: Dict[str, asyncio.Task] = {}

        logger.info("TokenManager initialized")

    async def refresh_token(
        self,
        account: TigerAccount,
        trigger: RefreshTrigger = RefreshTrigger.MANUAL,
        force: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Refresh access token for an account.

        Args:
            account: TigerAccount instance
            trigger: What triggered the refresh
            force: Force refresh even if not needed

        Returns:
            Tuple of (success, error_message)
        """
        account_key = str(account.id)

        # Use per-account lock to prevent concurrent refreshes
        if account_key not in self._refresh_locks:
            self._refresh_locks[account_key] = asyncio.Lock()

        async with self._refresh_locks[account_key]:
            return await self._do_refresh_token(account, trigger, force)

    async def _do_refresh_token(
        self, account: TigerAccount, trigger: RefreshTrigger, force: bool
    ) -> Tuple[bool, Optional[str]]:
        """Internal token refresh implementation."""
        try:
            # Check if refresh is needed (unless forced)
            if (
                not force
                and account.has_valid_token
                and not account.needs_token_refresh
            ):
                logger.debug(
                    f"Token refresh not needed for account {account.account_name}"
                )
                return True, None

            # Get current token hash for tracking
            current_token_hash = None
            if account.access_token:
                credentials = await self._account_manager.decrypt_credentials(account)
                current_access_token = credentials.get("access_token")
                if current_access_token:
                    current_token_hash = hashlib.sha256(
                        current_access_token.encode()
                    ).hexdigest()

            # Create token status record
            token_status = TokenStatus(
                tiger_account_id=account.id,
                status=TokenRefreshStatus.PENDING,
                trigger=trigger,
                old_token_expires_at=account.token_expires_at,
                old_token_hash=current_token_hash,
                environment=account.environment,
            )

            async with get_session() as session:
                session.add(token_status)
                await session.flush()  # Get the ID

                # Start the refresh
                token_status.start_refresh()

                try:
                    # Perform the actual API call
                    new_token_data = await self._call_tiger_refresh_api(account)

                    # Calculate new expiry time
                    expires_in = new_token_data.get(
                        "expires_in", 3600
                    )  # Default 1 hour
                    new_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                    # Hash new token
                    new_token_hash = hashlib.sha256(
                        new_token_data["access_token"].encode()
                    ).hexdigest()

                    # Update account with new tokens
                    await self._account_manager.update_tokens(
                        account.id,
                        access_token=new_token_data["access_token"],
                        refresh_token=new_token_data.get("refresh_token"),
                        token_expires_at=new_expires_at,
                    )

                    # Complete the token status
                    token_status.complete_refresh(
                        success=True,
                        new_token_expires_at=new_expires_at,
                        new_token_hash=new_token_hash,
                        api_response_code=200,
                    )

                    # Reset error count on successful refresh
                    await self._account_manager.reset_error_count(account.id)

                    await session.commit()

                    logger.info(
                        f"Successfully refreshed token for account {account.account_name} "
                        f"(expires at {new_expires_at})"
                    )

                    return True, None

                except Exception as refresh_error:
                    # Handle refresh failure
                    error_message = str(refresh_error)
                    error_code = getattr(refresh_error, "status_code", "UNKNOWN")

                    # Complete the token status with failure
                    token_status.complete_refresh(
                        success=False,
                        error_code=str(error_code),
                        error_message=error_message,
                        api_response_code=getattr(refresh_error, "status_code", None),
                    )

                    # Increment account error count
                    await self._account_manager.increment_error_count(
                        account.id, error_message
                    )

                    await session.commit()

                    logger.error(
                        f"Failed to refresh token for account {account.account_name}: {error_message}"
                    )

                    return False, error_message

        except Exception as e:
            logger.error(f"Token refresh error for account {account.account_name}: {e}")
            return False, str(e)

    async def _call_tiger_refresh_api(self, account: TigerAccount) -> Dict:
        """
        Call Tiger API to refresh token.

        Args:
            account: TigerAccount instance

        Returns:
            Dictionary with token response data

        Raises:
            TokenRefreshError: If API call fails
        """
        try:
            # Get decrypted credentials
            credentials = await self._account_manager.decrypt_credentials(account)

            # Determine API endpoint
            if account.environment == "production":
                base_url = self._config.tiger_production_url
            else:
                base_url = self._config.tiger_sandbox_url

            # Prepare request
            url = f"{base_url}/tiger/oauth2/token"

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Tiger-MCP-Server/1.0",
            }

            # For Tiger API, we need to use the refresh token or re-authenticate
            # This is a simplified example - actual implementation depends on Tiger API spec
            data = {
                "grant_type": "refresh_token",
                "refresh_token": credentials.get("refresh_token"),
                "client_id": credentials["tiger_id"],
            }

            # If no refresh token, try client credentials flow
            if not credentials.get("refresh_token"):
                data = {
                    "grant_type": "client_credentials",
                    "client_id": credentials["tiger_id"],
                    "client_secret": credentials["private_key"],  # Simplified
                }

            # Make API call with retries
            async with httpx.AsyncClient(
                timeout=self._config.tiger_api_timeout
            ) as client:
                for attempt in range(self._config.tiger_api_retries):
                    try:
                        response = await client.post(url, json=data, headers=headers)

                        if response.status_code == 200:
                            response_data = response.json()

                            # Validate response
                            if "access_token" not in response_data:
                                raise TokenRefreshError("No access token in response")

                            return response_data

                        elif response.status_code == 429:
                            # Rate limited
                            retry_after = int(response.headers.get("Retry-After", 60))
                            if attempt < self._config.tiger_api_retries - 1:
                                logger.warning(
                                    f"Rate limited, waiting {retry_after}s before retry {attempt + 1}"
                                )
                                await asyncio.sleep(retry_after)
                                continue
                            else:
                                raise TokenRateLimitError(
                                    "Rate limit exceeded, max retries reached"
                                )

                        else:
                            # Other HTTP error
                            error_msg = f"HTTP {response.status_code}: {response.text}"
                            if attempt < self._config.tiger_api_retries - 1:
                                wait_time = self._config.tiger_api_retry_delay * (
                                    2**attempt
                                )
                                logger.warning(
                                    f"API error, retrying in {wait_time}s: {error_msg}"
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise TokenRefreshError(error_msg)

                    except httpx.TimeoutException:
                        if attempt < self._config.tiger_api_retries - 1:
                            wait_time = self._config.tiger_api_retry_delay * (
                                2**attempt
                            )
                            logger.warning(f"Request timeout, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise TokenRefreshError(
                                "Request timeout, max retries reached"
                            )

                    except httpx.RequestError as e:
                        if attempt < self._config.tiger_api_retries - 1:
                            wait_time = self._config.tiger_api_retry_delay * (
                                2**attempt
                            )
                            logger.warning(
                                f"Request error, retrying in {wait_time}s: {e}"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise TokenRefreshError(f"Request error: {e}")

            raise TokenRefreshError("All retry attempts failed")

        except TokenRefreshError:
            raise
        except Exception as e:
            raise TokenRefreshError(f"Unexpected error during token refresh: {e}")

    async def validate_token(self, account: TigerAccount) -> Tuple[bool, Optional[str]]:
        """
        Validate that an account's token is working.

        Args:
            account: TigerAccount instance

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not account.access_token:
                return False, "No access token available"

            if not account.has_valid_token:
                return False, "Token has expired"

            # Make a simple API call to validate token
            credentials = await self._account_manager.decrypt_credentials(account)

            # Determine API endpoint
            if account.environment == "production":
                base_url = self._config.tiger_production_url
            else:
                base_url = self._config.tiger_sandbox_url

            # Use a lightweight endpoint for validation
            url = f"{base_url}/tiger/account/profile"

            headers = {
                "Authorization": f"Bearer {credentials['access_token']}",
                "User-Agent": "Tiger-MCP-Server/1.0",
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return True, None
                elif response.status_code == 401:
                    return False, "Token is invalid or expired"
                else:
                    return False, f"Validation failed: HTTP {response.status_code}"

        except Exception as e:
            logger.error(f"Token validation error for {account.account_name}: {e}")
            return False, str(e)

    async def refresh_expired_tokens(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        Refresh tokens for all accounts that need it.

        Returns:
            Dictionary mapping account_name to (success, error_message)
        """
        try:
            # Get accounts needing refresh
            accounts = await self._account_manager.get_accounts_needing_token_refresh()

            if not accounts:
                logger.info("No accounts need token refresh")
                return {}

            logger.info(f"Found {len(accounts)} accounts needing token refresh")

            # Refresh tokens concurrently but with some limits
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent refreshes
            results = {}

            async def refresh_with_semaphore(account):
                async with semaphore:
                    return await self.refresh_token(account, RefreshTrigger.SCHEDULED)

            tasks = [(account, refresh_with_semaphore(account)) for account in accounts]

            for account, task in tasks:
                try:
                    success, error = await task
                    results[account.account_name] = (success, error)
                except Exception as e:
                    results[account.account_name] = (False, str(e))

            # Log summary
            successful = sum(1 for success, _ in results.values() if success)
            failed = len(results) - successful

            logger.info(
                f"Token refresh completed: {successful} successful, {failed} failed"
            )

            return results

        except Exception as e:
            logger.error(f"Error during bulk token refresh: {e}")
            raise TokenManagerError(f"Bulk token refresh failed: {e}")

    async def schedule_token_refresh(
        self, account: TigerAccount, refresh_time: Optional[datetime] = None
    ) -> TokenStatus:
        """
        Schedule a token refresh for an account.

        Args:
            account: TigerAccount instance
            refresh_time: When to refresh (default: 1 hour before expiry)

        Returns:
            Created TokenStatus instance
        """
        try:
            if refresh_time is None:
                if account.token_expires_at:
                    # Schedule 1 hour before expiry
                    refresh_time = account.token_expires_at - timedelta(hours=1)
                else:
                    # No expiry info, schedule in 1 hour
                    refresh_time = datetime.utcnow() + timedelta(hours=1)

            # Get current token hash
            current_token_hash = None
            if account.access_token:
                credentials = await self._account_manager.decrypt_credentials(account)
                current_access_token = credentials.get("access_token")
                if current_access_token:
                    current_token_hash = hashlib.sha256(
                        current_access_token.encode()
                    ).hexdigest()

            # Create scheduled refresh
            token_status = TokenStatus.create_scheduled_refresh(
                tiger_account_id=account.id,
                next_refresh_at=refresh_time,
                current_token_expires_at=account.token_expires_at,
                current_token_hash=current_token_hash,
            )

            async with get_session() as session:
                session.add(token_status)
                await session.commit()

            logger.info(
                f"Scheduled token refresh for {account.account_name} at {refresh_time}"
            )

            return token_status

        except Exception as e:
            logger.error(f"Failed to schedule token refresh: {e}")
            raise TokenManagerError(f"Failed to schedule token refresh: {e}")

    async def get_token_status_history(
        self, account_id: Optional[str] = None, limit: int = 100
    ) -> List[TokenStatus]:
        """
        Get token refresh status history.

        Args:
            account_id: Filter by account ID (optional)
            limit: Maximum number of records

        Returns:
            List of TokenStatus instances
        """
        try:
            async with get_session() as session:
                stmt = (
                    select(TokenStatus)
                    .order_by(TokenStatus.created_at.desc())
                    .limit(limit)
                )

                if account_id:
                    stmt = stmt.where(TokenStatus.tiger_account_id == account_id)

                result = await session.execute(stmt)
                return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get token status history: {e}")
            raise TokenManagerError(f"Failed to get token status history: {e}")

    async def get_refresh_statistics(
        self, account_id: Optional[str] = None, days: int = 30
    ) -> Dict[str, any]:
        """
        Get token refresh statistics.

        Args:
            account_id: Filter by account ID (optional)
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)

            async with get_session() as session:
                stmt = select(TokenStatus).where(TokenStatus.created_at >= since_date)

                if account_id:
                    stmt = stmt.where(TokenStatus.tiger_account_id == account_id)

                result = await session.execute(stmt)
                token_statuses = list(result.scalars().all())

            if not token_statuses:
                return {
                    "total_refreshes": 0,
                    "successful_refreshes": 0,
                    "failed_refreshes": 0,
                    "success_rate": 0.0,
                    "average_duration_ms": 0,
                    "triggers": {},
                }

            # Calculate statistics
            total = len(token_statuses)
            successful = sum(1 for ts in token_statuses if ts.is_successful)
            failed = total - successful
            success_rate = (successful / total) * 100 if total > 0 else 0

            # Average duration for completed operations
            durations = [
                ts.duration_ms for ts in token_statuses if ts.duration_ms is not None
            ]
            avg_duration = sum(durations) / len(durations) if durations else 0

            # Trigger counts
            triggers = {}
            for ts in token_statuses:
                trigger = ts.trigger.value
                triggers[trigger] = triggers.get(trigger, 0) + 1

            return {
                "total_refreshes": total,
                "successful_refreshes": successful,
                "failed_refreshes": failed,
                "success_rate": round(success_rate, 2),
                "average_duration_ms": round(avg_duration, 2),
                "triggers": triggers,
                "period_days": days,
            }

        except Exception as e:
            logger.error(f"Failed to get refresh statistics: {e}")
            raise TokenManagerError(f"Failed to get refresh statistics: {e}")

    async def start_background_refresh_scheduler(self) -> None:
        """Start background task for automatic token refresh scheduling."""
        try:

            async def refresh_scheduler():
                """Background task to refresh tokens."""
                while True:
                    try:
                        await self.refresh_expired_tokens()
                        # Wait 15 minutes before next check
                        await asyncio.sleep(900)
                    except Exception as e:
                        logger.error(f"Error in background refresh scheduler: {e}")
                        # Wait 5 minutes before retrying on error
                        await asyncio.sleep(300)

            # Start the background task
            task = asyncio.create_task(refresh_scheduler())
            self._refresh_tasks["scheduler"] = task

            logger.info("Started background token refresh scheduler")

        except Exception as e:
            logger.error(f"Failed to start background refresh scheduler: {e}")
            raise TokenManagerError(f"Failed to start background scheduler: {e}")

    async def stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        for name, task in self._refresh_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.info(f"Stopped background task: {name}")

        self._refresh_tasks.clear()


# Global token manager instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Get global token manager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager
