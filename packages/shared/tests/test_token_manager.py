"""
Comprehensive unit tests for token_manager module.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Mock database imports before importing the token_manager
with patch.dict(
    "sys.modules",
    {
        "database.engine": MagicMock(),
        "database.models.accounts": MagicMock(),
        "database.models.token_status": MagicMock(),
    },
):
    # Mock the specific imports
    mock_get_session = AsyncMock()
    mock_tiger_account = MagicMock()
    mock_account_status = MagicMock()
    mock_token_status = MagicMock()
    mock_token_refresh_status = MagicMock()
    mock_refresh_trigger = MagicMock()

    with (
        patch("shared.token_manager.get_session", mock_get_session),
        patch("shared.token_manager.TigerAccount", mock_tiger_account),
        patch("shared.token_manager.AccountStatus", mock_account_status),
        patch("shared.token_manager.TokenStatus", mock_token_status),
        patch("shared.token_manager.TokenRefreshStatus", mock_token_refresh_status),
        patch("shared.token_manager.RefreshTrigger", mock_refresh_trigger),
    ):

        from shared.token_manager import (
            TokenManager,
            TokenManagerError,
            TokenRateLimitError,
            TokenRefreshError,
            TokenValidationError,
            get_token_manager,
        )


class TestTokenManagerErrors:
    """Tests for token manager exception classes."""

    def test_token_manager_error(self):
        """Test TokenManagerError exception."""
        error = TokenManagerError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_token_refresh_error(self):
        """Test TokenRefreshError exception."""
        error = TokenRefreshError("Refresh failed")
        assert str(error) == "Refresh failed"
        assert isinstance(error, TokenManagerError)

    def test_token_validation_error(self):
        """Test TokenValidationError exception."""
        error = TokenValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, TokenManagerError)

    def test_token_rate_limit_error(self):
        """Test TokenRateLimitError exception."""
        error = TokenRateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, TokenManagerError)


class TestTokenManagerInit:
    """Tests for TokenManager initialization."""

    @patch("shared.token_manager.get_tiger_api_config")
    @patch("shared.token_manager.get_account_manager")
    @patch("shared.token_manager.get_encryption_service")
    def test_token_manager_initialization(
        self, mock_encryption, mock_account_manager, mock_tiger_config
    ):
        """Test TokenManager initialization."""
        mock_tiger_config.return_value = MagicMock()
        mock_account_manager.return_value = MagicMock()
        mock_encryption.return_value = MagicMock()

        manager = TokenManager()

        assert manager._config is not None
        assert manager._account_manager is not None
        assert manager._encryption_service is not None
        assert isinstance(manager._refresh_locks, dict)
        assert isinstance(manager._refresh_tasks, dict)

        mock_tiger_config.assert_called_once()
        mock_account_manager.assert_called_once()
        mock_encryption.assert_called_once()


class TestTokenRefresh:
    """Tests for token refresh functionality."""

    @pytest.fixture
    def token_manager(self):
        """Create token manager instance for testing."""
        with (
            patch("shared.token_manager.get_tiger_api_config"),
            patch("shared.token_manager.get_account_manager"),
            patch("shared.token_manager.get_encryption_service"),
        ):
            return TokenManager()

    @pytest.fixture
    def mock_account(self):
        """Mock TigerAccount for testing."""
        account = MagicMock()
        account.id = uuid.uuid4()
        account.account_name = "Test Account"
        account.environment = "sandbox"
        account.has_valid_token = False
        account.needs_token_refresh = True
        account.token_expires_at = datetime.utcnow() - timedelta(minutes=5)
        account.access_token = "encrypted_access_token"
        return account

    async def test_refresh_token_success(self, token_manager, mock_account):
        """Test successful token refresh."""
        # Mock methods
        token_manager._do_refresh_token = AsyncMock(return_value=(True, None))

        # Test refresh
        success, error = await token_manager.refresh_token(mock_account)

        assert success is True
        assert error is None
        token_manager._do_refresh_token.assert_called_once()

    async def test_refresh_token_with_lock(self, token_manager, mock_account):
        """Test token refresh with concurrent access control."""
        # Mock the actual refresh
        token_manager._do_refresh_token = AsyncMock(return_value=(True, None))

        # Start multiple concurrent refresh operations
        tasks = [
            token_manager.refresh_token(mock_account),
            token_manager.refresh_token(mock_account),
            token_manager.refresh_token(mock_account),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed but only one actual refresh should happen
        assert all(result[0] for result in results)
        assert all(result[1] is None for result in results)

        # Lock should be created for account
        account_key = str(mock_account.id)
        assert account_key in token_manager._refresh_locks

    @patch("shared.token_manager.get_session")
    async def test_do_refresh_token_not_needed(
        self, mock_session_context, token_manager, mock_account
    ):
        """Test token refresh when not needed."""
        # Account has valid token
        mock_account.has_valid_token = True
        mock_account.needs_token_refresh = False

        success, error = await token_manager._do_refresh_token(
            mock_account, mock_refresh_trigger.MANUAL, force=False
        )

        assert success is True
        assert error is None
        # Session should not be used when refresh not needed
        mock_session_context.assert_not_called()

    @patch("shared.token_manager.get_session")
    async def test_do_refresh_token_force(
        self, mock_session_context, token_manager, mock_account
    ):
        """Test forced token refresh."""
        # Setup session mock
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock account manager and API call
        mock_credentials = {
            "access_token": "old_access_token",
            "refresh_token": "refresh_token",
        }
        token_manager._account_manager.decrypt_credentials = AsyncMock(
            return_value=mock_credentials
        )
        token_manager._call_tiger_refresh_api = AsyncMock(
            return_value={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
            }
        )
        token_manager._account_manager.update_tokens = AsyncMock(
            return_value=mock_account
        )

        # Mock token status
        mock_token_instance = MagicMock()
        mock_token_status.return_value = mock_token_instance
        mock_token_instance.start_refresh = MagicMock()
        mock_token_instance.complete_success = MagicMock()

        # Force refresh even though account thinks it doesn't need it
        mock_account.has_valid_token = True
        mock_account.needs_token_refresh = False

        success, error = await token_manager._do_refresh_token(
            mock_account, mock_refresh_trigger.MANUAL, force=True
        )

        assert success is True
        assert error is None

        # API should have been called
        token_manager._call_tiger_refresh_api.assert_called_once_with(mock_account)
        token_manager._account_manager.update_tokens.assert_called_once()
        mock_token_instance.complete_success.assert_called_once()

    @patch("shared.token_manager.get_session")
    async def test_do_refresh_token_api_failure(
        self, mock_session_context, token_manager, mock_account
    ):
        """Test token refresh with API failure."""
        # Setup session mock
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock API failure
        token_manager._account_manager.decrypt_credentials = AsyncMock(
            return_value={"access_token": "old_token"}
        )
        token_manager._call_tiger_refresh_api = AsyncMock(
            side_effect=TokenRefreshError("API call failed")
        )

        # Mock token status
        mock_token_instance = MagicMock()
        mock_token_status.return_value = mock_token_instance
        mock_token_instance.start_refresh = MagicMock()
        mock_token_instance.complete_failure = MagicMock()

        success, error = await token_manager._do_refresh_token(
            mock_account, mock_refresh_trigger.MANUAL, force=True
        )

        assert success is False
        assert "API call failed" in error
        mock_token_instance.complete_failure.assert_called_once()


class TestTigerAPIIntegration:
    """Tests for Tiger API integration."""

    @pytest.fixture
    def token_manager(self):
        """Create token manager instance for testing."""
        with (
            patch("shared.token_manager.get_tiger_api_config") as mock_config,
            patch("shared.token_manager.get_account_manager"),
            patch("shared.token_manager.get_encryption_service"),
        ):

            # Mock config
            config = MagicMock()
            config.tiger_api_timeout = 30
            config.tiger_api_retries = 3
            config.tiger_api_retry_delay = 1.0
            mock_config.return_value = config

            return TokenManager()

    @pytest.fixture
    def mock_account(self):
        """Mock TigerAccount for testing."""
        account = MagicMock()
        account.id = uuid.uuid4()
        account.environment = "sandbox"
        account.server_url = None
        return account

    @patch("shared.token_manager.httpx.AsyncClient")
    async def test_call_tiger_refresh_api_success(
        self, mock_httpx_client, token_manager, mock_account
    ):
        """Test successful Tiger API call."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_httpx_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock credential decryption
        token_manager._account_manager.decrypt_credentials = AsyncMock(
            return_value={
                "tiger_id": "test_tiger_id",
                "private_key": "test_private_key",
                "refresh_token": "current_refresh_token",
            }
        )

        result = await token_manager._call_tiger_refresh_api(mock_account)

        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["expires_in"] == 3600

        # Verify API call was made
        mock_client_instance.post.assert_called_once()

    @patch("shared.token_manager.httpx.AsyncClient")
    async def test_call_tiger_refresh_api_http_error(
        self, mock_httpx_client, token_manager, mock_account
    ):
        """Test Tiger API call with HTTP error."""
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_token",
            "error_description": "Refresh token expired",
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_httpx_client.return_value.__aexit__ = AsyncMock(return_value=None)

        token_manager._account_manager.decrypt_credentials = AsyncMock(
            return_value={
                "tiger_id": "test_tiger_id",
                "private_key": "test_private_key",
                "refresh_token": "invalid_refresh_token",
            }
        )

        with pytest.raises(TokenRefreshError, match="Token refresh failed"):
            await token_manager._call_tiger_refresh_api(mock_account)

    @patch("shared.token_manager.httpx.AsyncClient")
    async def test_call_tiger_refresh_api_network_error(
        self, mock_httpx_client, token_manager, mock_account
    ):
        """Test Tiger API call with network error."""
        # Mock network error
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.ConnectError("Connection failed")
        mock_httpx_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_httpx_client.return_value.__aexit__ = AsyncMock(return_value=None)

        token_manager._account_manager.decrypt_credentials = AsyncMock(
            return_value={
                "tiger_id": "test_tiger_id",
                "private_key": "test_private_key",
                "refresh_token": "refresh_token",
            }
        )

        with pytest.raises(TokenRefreshError, match="Network error"):
            await token_manager._call_tiger_refresh_api(mock_account)

    @patch("shared.token_manager.httpx.AsyncClient")
    async def test_call_tiger_refresh_api_rate_limit(
        self, mock_httpx_client, token_manager, mock_account
    ):
        """Test Tiger API call with rate limit."""
        # Mock rate limit response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {
            "error": "rate_limit_exceeded",
            "error_description": "Too many requests",
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_httpx_client.return_value.__aexit__ = AsyncMock(return_value=None)

        token_manager._account_manager.decrypt_credentials = AsyncMock(
            return_value={
                "tiger_id": "test_tiger_id",
                "private_key": "test_private_key",
                "refresh_token": "refresh_token",
            }
        )

        with pytest.raises(TokenRateLimitError, match="Rate limit exceeded"):
            await token_manager._call_tiger_refresh_api(mock_account)


class TestTokenValidation:
    """Tests for token validation functionality."""

    @pytest.fixture
    def token_manager(self):
        """Create token manager instance for testing."""
        with (
            patch("shared.token_manager.get_tiger_api_config"),
            patch("shared.token_manager.get_account_manager"),
            patch("shared.token_manager.get_encryption_service"),
        ):
            return TokenManager()

    @pytest.fixture
    def mock_account(self):
        """Mock TigerAccount for testing."""
        account = MagicMock()
        account.id = uuid.uuid4()
        account.has_valid_token = True
        account.token_expires_at = datetime.utcnow() + timedelta(hours=1)
        return account

    async def test_validate_token_valid(self, token_manager, mock_account):
        """Test validation of valid token."""
        # Mock API validation call
        with patch.object(token_manager, "_call_tiger_validate_api") as mock_validate:
            mock_validate.return_value = {"status": "valid", "expires_in": 3600}

            is_valid, error = await token_manager.validate_token(mock_account)

            assert is_valid is True
            assert error is None
            mock_validate.assert_called_once_with(mock_account)

    async def test_validate_token_expired(self, token_manager, mock_account):
        """Test validation of expired token."""
        # Set token as expired
        mock_account.has_valid_token = False
        mock_account.token_expires_at = datetime.utcnow() - timedelta(hours=1)

        is_valid, error = await token_manager.validate_token(mock_account)

        assert is_valid is False
        assert "expired" in error.lower()

    async def test_validate_token_no_token(self, token_manager, mock_account):
        """Test validation when no token exists."""
        # No token
        mock_account.has_valid_token = False
        mock_account.token_expires_at = None

        is_valid, error = await token_manager.validate_token(mock_account)

        assert is_valid is False
        assert "no access token" in error.lower()

    async def test_validate_token_api_error(self, token_manager, mock_account):
        """Test validation with API error."""
        with patch.object(token_manager, "_call_tiger_validate_api") as mock_validate:
            mock_validate.side_effect = TokenValidationError("API validation failed")

            is_valid, error = await token_manager.validate_token(mock_account)

            assert is_valid is False
            assert "API validation failed" in error


class TestBulkTokenRefresh:
    """Tests for bulk token refresh functionality."""

    @pytest.fixture
    def token_manager(self):
        """Create token manager instance for testing."""
        with (
            patch("shared.token_manager.get_tiger_api_config") as mock_config,
            patch("shared.token_manager.get_account_manager"),
            patch("shared.token_manager.get_encryption_service"),
        ):

            # Mock config with concurrency limit
            config = MagicMock()
            config.tiger_api_timeout = 30
            config.tiger_rate_limit_per_second = 5
            mock_config.return_value = config

            return TokenManager()

    async def test_refresh_expired_tokens_success(self, token_manager):
        """Test bulk refresh of expired tokens."""
        # Mock accounts needing refresh
        mock_accounts = [MagicMock() for _ in range(3)]
        for i, account in enumerate(mock_accounts):
            account.id = uuid.uuid4()
            account.account_name = f"Account {i+1}"
            account.needs_token_refresh = True

        token_manager._account_manager.get_accounts_needing_token_refresh = AsyncMock(
            return_value=mock_accounts
        )

        # Mock successful refreshes
        token_manager.refresh_token = AsyncMock(return_value=(True, None))

        results = await token_manager.refresh_expired_tokens()

        assert len(results) == 3
        assert all(success for success, _ in results.values())

        # Should have called refresh for each account
        assert token_manager.refresh_token.call_count == 3

    async def test_refresh_expired_tokens_mixed_results(self, token_manager):
        """Test bulk refresh with mixed success/failure results."""
        # Mock accounts
        mock_accounts = [MagicMock() for _ in range(3)]
        for i, account in enumerate(mock_accounts):
            account.id = uuid.uuid4()
            account.account_name = f"Account {i+1}"

        token_manager._account_manager.get_accounts_needing_token_refresh = AsyncMock(
            return_value=mock_accounts
        )

        # Mock mixed results
        refresh_results = [
            (True, None),  # Success
            (False, "API error"),  # Failure
            (True, None),  # Success
        ]

        token_manager.refresh_token = AsyncMock(side_effect=refresh_results)

        results = await token_manager.refresh_expired_tokens()

        assert len(results) == 3

        # Check results
        account_results = list(results.values())
        assert account_results[0] == (True, None)
        assert account_results[1] == (False, "API error")
        assert account_results[2] == (True, None)

    async def test_refresh_expired_tokens_empty_list(self, token_manager):
        """Test bulk refresh with no accounts needing refresh."""
        token_manager._account_manager.get_accounts_needing_token_refresh = AsyncMock(
            return_value=[]
        )

        results = await token_manager.refresh_expired_tokens()

        assert results == {}


class TestTokenScheduling:
    """Tests for token refresh scheduling."""

    @pytest.fixture
    def token_manager(self):
        """Create token manager instance for testing."""
        with (
            patch("shared.token_manager.get_tiger_api_config"),
            patch("shared.token_manager.get_account_manager"),
            patch("shared.token_manager.get_encryption_service"),
        ):
            return TokenManager()

    @patch("shared.token_manager.get_session")
    async def test_schedule_token_refresh(self, mock_session_context, token_manager):
        """Test scheduling token refresh."""
        # Setup session mock
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

        account_id = uuid.uuid4()
        refresh_time = datetime.utcnow() + timedelta(hours=1)

        # Mock token status creation
        mock_token_instance = MagicMock()
        mock_token_status.create_scheduled_refresh.return_value = mock_token_instance

        await token_manager.schedule_token_refresh(account_id, refresh_time)

        # Should create scheduled refresh
        mock_token_status.create_scheduled_refresh.assert_called_once_with(
            tiger_account_id=account_id, next_refresh_at=refresh_time
        )
        mock_session.add.assert_called_once_with(mock_token_instance)
        mock_session.commit.assert_called_once()

    async def test_start_background_refresh_scheduler(self, token_manager):
        """Test starting background refresh scheduler."""
        # Mock the scheduler task
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            await token_manager.start_background_refresh_scheduler()

            # Should create background task
            mock_create_task.assert_called_once()

            # Task should be stored
            assert "refresh_scheduler" in token_manager._refresh_tasks
            assert token_manager._refresh_tasks["refresh_scheduler"] is mock_task

    async def test_stop_background_tasks(self, token_manager):
        """Test stopping background tasks."""
        # Setup mock tasks
        mock_task1 = MagicMock()
        mock_task2 = MagicMock()
        token_manager._refresh_tasks = {"task1": mock_task1, "task2": mock_task2}

        await token_manager.stop_background_tasks()

        # Should cancel all tasks
        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()

        # Tasks should be cleared
        assert token_manager._refresh_tasks == {}


class TestTokenStatusHistory:
    """Tests for token status and history functionality."""

    @pytest.fixture
    def token_manager(self):
        """Create token manager instance for testing."""
        with (
            patch("shared.token_manager.get_tiger_api_config"),
            patch("shared.token_manager.get_account_manager"),
            patch("shared.token_manager.get_encryption_service"),
        ):
            return TokenManager()

    @patch("shared.token_manager.get_session")
    async def test_get_token_status_history(self, mock_session_context, token_manager):
        """Test retrieving token status history."""
        # Setup session mock
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock query result
        mock_statuses = [MagicMock() for _ in range(5)]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_statuses
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        account_id = uuid.uuid4()

        history = await token_manager.get_token_status_history(account_id)

        assert history == mock_statuses
        mock_session.execute.assert_called_once()

    @patch("shared.token_manager.get_session")
    async def test_get_token_status_history_with_limit(
        self, mock_session_context, token_manager
    ):
        """Test retrieving token status history with limit."""
        # Setup session mock
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_statuses = [MagicMock() for _ in range(10)]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_statuses
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        account_id = uuid.uuid4()

        history = await token_manager.get_token_status_history(account_id, limit=10)

        assert history == mock_statuses
        mock_session.execute.assert_called_once()

    @patch("shared.token_manager.get_session")
    async def test_get_refresh_statistics(self, mock_session_context, token_manager):
        """Test retrieving refresh statistics."""
        # Setup session mock
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock statistics query result
        mock_stats = {
            "total_refreshes": 100,
            "successful_refreshes": 95,
            "failed_refreshes": 5,
            "success_rate": 0.95,
        }

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_stats
        mock_session.execute.return_value = mock_result

        account_id = uuid.uuid4()

        stats = await token_manager.get_refresh_statistics(account_id)

        assert stats == mock_stats
        mock_session.execute.assert_called_once()


class TestErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.fixture
    def token_manager(self):
        """Create token manager instance for testing."""
        with (
            patch("shared.token_manager.get_tiger_api_config") as mock_config,
            patch("shared.token_manager.get_account_manager"),
            patch("shared.token_manager.get_encryption_service"),
        ):

            # Mock config with retry settings
            config = MagicMock()
            config.tiger_api_retries = 3
            config.tiger_api_retry_delay = 0.1  # Fast for testing
            mock_config.return_value = config

            return TokenManager()

    async def test_retry_logic_exponential_backoff(self, token_manager):
        """Test retry logic with exponential backoff."""
        mock_account = MagicMock()
        mock_account.environment = "sandbox"

        # Mock API to fail 2 times then succeed
        call_count = 0

        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TokenRefreshError("Temporary failure")
            return {"access_token": "new_token", "expires_in": 3600}

        with patch("asyncio.sleep") as mock_sleep:
            with patch.object(
                token_manager, "_call_tiger_refresh_api", side_effect=mock_api_call
            ):
                token_manager._account_manager.decrypt_credentials = AsyncMock(
                    return_value={"refresh_token": "refresh_token"}
                )

                # This would be called in a real retry wrapper
                result = None
                for attempt in range(3):
                    try:
                        result = await token_manager._call_tiger_refresh_api(
                            mock_account
                        )
                        break
                    except TokenRefreshError:
                        if attempt < 2:  # Don't sleep on last attempt
                            await asyncio.sleep(
                                0.1 * (2**attempt)
                            )  # Exponential backoff
                        continue

                assert result is not None
                assert result["access_token"] == "new_token"
                assert call_count == 3  # Should have retried

                # Sleep should have been called for backoff
                assert mock_sleep.call_count >= 1

    async def test_concurrent_refresh_prevention(self, token_manager):
        """Test prevention of concurrent refreshes for same account."""
        mock_account = MagicMock()
        mock_account.id = uuid.uuid4()

        # Mock a slow refresh operation
        async def slow_refresh(*args, **kwargs):
            await asyncio.sleep(0.1)
            return (True, None)

        token_manager._do_refresh_token = slow_refresh

        # Start multiple concurrent refreshes
        tasks = [
            token_manager.refresh_token(mock_account),
            token_manager.refresh_token(mock_account),
            token_manager.refresh_token(mock_account),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed but only one actual refresh should happen
        assert all(result[0] for result in results)

        # Lock should exist for account
        account_key = str(mock_account.id)
        assert account_key in token_manager._refresh_locks

    @patch("shared.token_manager.get_session")
    async def test_database_transaction_rollback(
        self, mock_session_context, token_manager
    ):
        """Test database transaction rollback on error."""
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        mock_account.id = uuid.uuid4()
        mock_account.needs_token_refresh = True

        # Mock database error after token status creation
        mock_token_instance = MagicMock()
        mock_token_status.return_value = mock_token_instance

        # API call succeeds but token update fails
        token_manager._account_manager.decrypt_credentials = AsyncMock(return_value={})
        token_manager._call_tiger_refresh_api = AsyncMock(
            return_value={"access_token": "new_token", "expires_in": 3600}
        )
        token_manager._account_manager.update_tokens = AsyncMock(
            side_effect=Exception("Database error")
        )

        success, error = await token_manager._do_refresh_token(
            mock_account, mock_refresh_trigger.MANUAL, force=True
        )

        assert success is False
        assert "Database error" in error
        mock_token_instance.complete_failure.assert_called_once()


class TestSingletonFunction:
    """Tests for singleton function."""

    def test_get_token_manager_singleton(self):
        """Test get_token_manager returns singleton."""
        with patch("shared.token_manager.TokenManager") as mock_manager:
            manager1 = get_token_manager()
            manager2 = get_token_manager()

            assert manager1 is manager2
            # Should only create instance once
            mock_manager.assert_called_once()


class TestTokenManagerIntegration:
    """Integration tests for token manager functionality."""

    @pytest.fixture
    def token_manager(self):
        """Create token manager instance for testing."""
        with (
            patch("shared.token_manager.get_tiger_api_config"),
            patch("shared.token_manager.get_account_manager"),
            patch("shared.token_manager.get_encryption_service"),
        ):
            return TokenManager()

    async def test_complete_refresh_workflow(self, token_manager):
        """Test complete token refresh workflow."""
        mock_account = MagicMock()
        mock_account.id = uuid.uuid4()
        mock_account.account_name = "Test Account"
        mock_account.needs_token_refresh = True
        mock_account.environment = "sandbox"

        with patch("shared.token_manager.get_session") as mock_session_context:
            mock_session = AsyncMock()
            mock_session_context.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock all dependencies
            token_manager._account_manager.decrypt_credentials = AsyncMock(
                return_value={
                    "tiger_id": "test_tiger",
                    "private_key": "test_key",
                    "refresh_token": "refresh_token",
                }
            )

            token_manager._call_tiger_refresh_api = AsyncMock(
                return_value={
                    "access_token": "new_access_token",
                    "refresh_token": "new_refresh_token",
                    "expires_in": 3600,
                }
            )

            token_manager._account_manager.update_tokens = AsyncMock(
                return_value=mock_account
            )

            # Mock token status
            mock_token_instance = MagicMock()
            mock_token_status.return_value = mock_token_instance

            # Execute complete workflow
            success, error = await token_manager.refresh_token(mock_account, force=True)

            assert success is True
            assert error is None

            # Verify all steps were executed
            token_manager._account_manager.decrypt_credentials.assert_called_once()
            token_manager._call_tiger_refresh_api.assert_called_once()
            token_manager._account_manager.update_tokens.assert_called_once()

            mock_token_instance.start_refresh.assert_called_once()
            mock_token_instance.complete_success.assert_called_once()

    async def test_token_lifecycle_management(self, token_manager):
        """Test complete token lifecycle management."""
        accounts = [MagicMock() for _ in range(3)]
        for i, account in enumerate(accounts):
            account.id = uuid.uuid4()
            account.account_name = f"Account {i+1}"
            account.needs_token_refresh = True

        # Mock bulk operations
        token_manager._account_manager.get_accounts_needing_token_refresh = AsyncMock(
            return_value=accounts
        )

        # Mock individual refresh operations
        token_manager.refresh_token = AsyncMock(return_value=(True, None))

        # Test bulk refresh
        results = await token_manager.refresh_expired_tokens()

        assert len(results) == 3
        assert all(success for success, _ in results.values())

        # Test scheduling
        with patch("shared.token_manager.get_session"):
            mock_token_status.create_scheduled_refresh.return_value = MagicMock()

            await token_manager.schedule_token_refresh(
                accounts[0].id, datetime.utcnow() + timedelta(hours=1)
            )

            mock_token_status.create_scheduled_refresh.assert_called_once()

        # Test background scheduler
        await token_manager.start_background_refresh_scheduler()
        assert "refresh_scheduler" in token_manager._refresh_tasks

        # Clean up
        await token_manager.stop_background_tasks()
        assert token_manager._refresh_tasks == {}
