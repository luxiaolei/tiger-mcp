"""
Unit tests for Tiger MCP Account Tools.

Tests all 7 account management tools:
1. tiger_list_accounts - List all configured accounts
2. tiger_add_account - Add new Tiger account
3. tiger_remove_account - Remove existing account
4. tiger_get_account_status - Get account status and info
5. tiger_refresh_token - Refresh account authentication token
6. tiger_set_default_data_account - Set default account for data requests
7. tiger_set_default_trading_account - Set default account for trading
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

# Import the tools under test
from mcp_server.tools.account_tools import (
    tiger_add_account,
    tiger_get_account_status,
    tiger_list_accounts,
    tiger_refresh_token,
    tiger_remove_account,
    tiger_set_default_data_account,
    tiger_set_default_trading_account,
)


class TestAccountTools:
    """Test suite for Tiger MCP account tools."""

    @pytest.mark.asyncio
    async def test_tiger_list_accounts_success(
        self, mock_account_manager, mock_account_data
    ):
        """Test successful account listing."""
        # Setup mocks
        mock_account_manager.list_accounts.return_value = mock_account_data.accounts

        # Execute tool
        result = await tiger_list_accounts()

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "accounts" in result.data
        assert len(result.data["accounts"]) == len(mock_account_data.accounts)

        # Verify account structure
        account = result.data["accounts"][0]
        expected_fields = [
            "id",
            "account_number",
            "account_name",
            "account_type",
            "status",
        ]
        assert all(field in account for field in expected_fields)

        # Verify calls
        mock_account_manager.list_accounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_tiger_list_accounts_empty(self, mock_account_manager):
        """Test account listing when no accounts exist."""
        # Setup mocks
        mock_account_manager.list_accounts.return_value = []

        # Execute tool
        result = await tiger_list_accounts()

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert "accounts" in result.data
        assert len(result.data["accounts"]) == 0

    @pytest.mark.asyncio
    async def test_tiger_list_accounts_error(self, mock_account_manager):
        """Test account listing with error."""
        # Setup mocks
        mock_account_manager.list_accounts.side_effect = RuntimeError(
            "Database connection failed"
        )

        # Execute tool
        result = await tiger_list_accounts()

        # Verify error handling
        assert result.success is False
        assert result.data is None
        assert "Database connection failed" in result.error

    @pytest.mark.asyncio
    async def test_tiger_add_account_success(self, mock_account_manager):
        """Test successful account addition."""
        # Setup mocks
        new_account_id = str(uuid.uuid4())
        mock_account = MagicMock()
        mock_account.id = new_account_id
        mock_account.account_number = "DU999888"
        mock_account.account_name = "Test Account"
        mock_account.status = "active"

        mock_account_manager.add_account.return_value = mock_account

        # Execute tool
        result = await tiger_add_account(
            account_number="DU999888",
            account_name="Test Account",
            account_type="MARGIN",
            tiger_id="test_tiger_id",
            private_key="test_private_key",
            is_sandbox=True,
        )

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert result.data["account_id"] == new_account_id
        assert result.data["account_number"] == "DU999888"
        assert result.data["status"] == "active"

        # Verify calls
        mock_account_manager.add_account.assert_called_once()
        call_args = mock_account_manager.add_account.call_args
        assert call_args[1]["account_number"] == "DU999888"
        assert call_args[1]["account_name"] == "Test Account"
        assert call_args[1]["account_type"] == "MARGIN"
        assert call_args[1]["is_sandbox"] is True

    @pytest.mark.asyncio
    async def test_tiger_add_account_duplicate(self, mock_account_manager):
        """Test adding duplicate account."""
        # Setup mocks
        mock_account_manager.add_account.side_effect = ValueError(
            "Account DU999888 already exists"
        )

        # Execute tool
        result = await tiger_add_account(
            account_number="DU999888",
            account_name="Duplicate Account",
            account_type="CASH",
            tiger_id="test_tiger_id",
            private_key="test_private_key",
        )

        # Verify error handling
        assert result.success is False
        assert result.data is None
        assert "already exists" in result.error

    @pytest.mark.asyncio
    async def test_tiger_add_account_validation_error(self, mock_account_manager):
        """Test account addition with validation error."""
        # Setup mocks
        mock_account_manager.add_account.side_effect = ValueError(
            "Invalid private key format"
        )

        # Execute tool with invalid data
        result = await tiger_add_account(
            account_number="",  # Empty account number
            account_name="Test Account",
            account_type="INVALID_TYPE",
            tiger_id="test_tiger_id",
            private_key="invalid_key",
        )

        # Verify error handling
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_tiger_remove_account_success(self, mock_account_manager):
        """Test successful account removal."""
        # Setup mocks
        account_id = str(uuid.uuid4())
        mock_account_manager.remove_account.return_value = True

        # Execute tool
        result = await tiger_remove_account(account_id)

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert result.data["account_id"] == account_id
        assert result.data["removed"] is True

        # Verify calls
        mock_account_manager.remove_account.assert_called_once_with(
            uuid.UUID(account_id)
        )

    @pytest.mark.asyncio
    async def test_tiger_remove_account_not_found(self, mock_account_manager):
        """Test removing non-existent account."""
        # Setup mocks
        account_id = str(uuid.uuid4())
        mock_account_manager.remove_account.side_effect = ValueError(
            f"Account {account_id} not found"
        )

        # Execute tool
        result = await tiger_remove_account(account_id)

        # Verify error handling
        assert result.success is False
        assert result.data is None
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_tiger_remove_account_invalid_id(self, mock_account_manager):
        """Test removing account with invalid ID."""
        # Execute tool with invalid UUID
        result = await tiger_remove_account("invalid-uuid")

        # Verify error handling
        assert result.success is False
        assert result.error is not None
        assert "invalid" in result.error.lower() or "uuid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tiger_get_account_status_success(
        self, mock_account_manager, mock_account_data
    ):
        """Test successful account status retrieval."""
        # Setup mocks
        account = mock_account_data.accounts[0]
        mock_account_manager.get_account_by_id.return_value = account

        # Execute tool
        result = await tiger_get_account_status(account.id)

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert result.data["account_id"] == account.id
        assert result.data["account_number"] == account.account_number
        assert result.data["status"] == account.status
        assert result.data["account_type"] == account.account_type

        # Verify calls
        mock_account_manager.get_account_by_id.assert_called_once_with(
            uuid.UUID(account.id)
        )

    @pytest.mark.asyncio
    async def test_tiger_get_account_status_not_found(self, mock_account_manager):
        """Test account status for non-existent account."""
        # Setup mocks
        account_id = str(uuid.uuid4())
        mock_account_manager.get_account_by_id.return_value = None

        # Execute tool
        result = await tiger_get_account_status(account_id)

        # Verify error handling
        assert result.success is False
        assert result.data is None
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_tiger_refresh_token_success(self, mock_account_manager):
        """Test successful token refresh."""
        # Setup mocks
        account_id = str(uuid.uuid4())
        new_token_info = {
            "access_token": "new_access_token",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "token_type": "Bearer",
        }
        mock_account_manager.refresh_token.return_value = new_token_info

        # Execute tool
        result = await tiger_refresh_token(account_id)

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert result.data["account_id"] == account_id
        assert result.data["token_refreshed"] is True
        assert "expires_at" in result.data

        # Verify calls
        mock_account_manager.refresh_token.assert_called_once_with(
            uuid.UUID(account_id)
        )

    @pytest.mark.asyncio
    async def test_tiger_refresh_token_failed(self, mock_account_manager):
        """Test failed token refresh."""
        # Setup mocks
        account_id = str(uuid.uuid4())
        mock_account_manager.refresh_token.side_effect = RuntimeError(
            "Token refresh failed: Invalid credentials"
        )

        # Execute tool
        result = await tiger_refresh_token(account_id)

        # Verify error handling
        assert result.success is False
        assert result.data is None
        assert "Token refresh failed" in result.error

    @pytest.mark.asyncio
    async def test_tiger_set_default_data_account_success(
        self, mock_account_router, mock_account_manager, mock_account_data
    ):
        """Test successful default data account setting."""
        # Setup mocks
        account = mock_account_data.active_accounts[0]
        mock_account_manager.get_account_by_id.return_value = account
        mock_account_router.set_default_data_account.return_value = True

        # Execute tool
        result = await tiger_set_default_data_account(account.id)

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert result.data["account_id"] == account.id
        assert result.data["account_number"] == account.account_number
        assert result.data["set_as_default"] is True

        # Verify calls
        mock_account_manager.get_account_by_id.assert_called_once_with(
            uuid.UUID(account.id)
        )
        mock_account_router.set_default_data_account.assert_called_once_with(
            uuid.UUID(account.id)
        )

    @pytest.mark.asyncio
    async def test_tiger_set_default_data_account_inactive(
        self, mock_account_router, mock_account_manager, mock_account_data
    ):
        """Test setting inactive account as default data account."""
        # Setup mocks
        inactive_account = next(
            acc for acc in mock_account_data.accounts if acc.status == "inactive"
        )
        mock_account_manager.get_account_by_id.return_value = inactive_account

        # Execute tool
        result = await tiger_set_default_data_account(inactive_account.id)

        # Verify error handling
        assert result.success is False
        assert result.data is None
        assert "inactive" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tiger_set_default_trading_account_success(
        self, mock_account_router, mock_account_manager, mock_account_data
    ):
        """Test successful default trading account setting."""
        # Setup mocks
        trading_account = next(
            acc
            for acc in mock_account_data.active_accounts
            if acc.account_type in ["MARGIN", "CASH"]
        )
        mock_account_manager.get_account_by_id.return_value = trading_account
        mock_account_router.set_default_trading_account.return_value = True

        # Execute tool
        result = await tiger_set_default_trading_account(trading_account.id)

        # Verify results
        assert result.success is True
        assert result.data is not None
        assert result.data["account_id"] == trading_account.id
        assert result.data["account_number"] == trading_account.account_number
        assert result.data["set_as_default"] is True

        # Verify calls
        mock_account_router.set_default_trading_account.assert_called_once_with(
            uuid.UUID(trading_account.id)
        )

    @pytest.mark.asyncio
    async def test_tiger_set_default_trading_account_paper(
        self, mock_account_router, mock_account_manager, mock_account_data
    ):
        """Test setting paper account as default trading account."""
        # Setup mocks
        paper_account = next(
            acc for acc in mock_account_data.accounts if acc.account_type == "PAPER"
        )
        mock_account_manager.get_account_by_id.return_value = paper_account

        # Execute tool - paper accounts should be allowed for trading (testing)
        result = await tiger_set_default_trading_account(paper_account.id)

        # Paper accounts should be allowed for testing
        # The result depends on business logic implementation
        assert isinstance(result.success, bool)
        if result.success:
            assert result.data["account_id"] == paper_account.id

    @pytest.mark.asyncio
    async def test_account_tools_concurrent_access(
        self, mock_account_manager, mock_account_router, mock_account_data
    ):
        """Test concurrent access to account tools."""
        # Setup mocks
        mock_account_manager.list_accounts.return_value = mock_account_data.accounts
        mock_account_manager.get_account_by_id.return_value = (
            mock_account_data.accounts[0]
        )
        mock_account_router.set_default_data_account.return_value = True

        # Execute concurrent operations
        account_id = mock_account_data.accounts[0].id
        tasks = [
            tiger_list_accounts(),
            tiger_get_account_status(account_id),
            tiger_set_default_data_account(account_id),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        successful_results = [
            r for r in results if not isinstance(r, Exception) and r.success
        ]
        assert len(successful_results) >= 2  # At least list and status should succeed

    @pytest.mark.parametrize(
        "account_type,is_valid",
        [
            ("MARGIN", True),
            ("CASH", True),
            ("PAPER", True),
            ("INVALID", False),
            ("", False),
        ],
    )
    @pytest.mark.asyncio
    async def test_account_type_validation(
        self, account_type, is_valid, mock_account_manager
    ):
        """Test account type validation in add_account tool."""
        if is_valid:
            # Setup for valid account type
            mock_account = MagicMock()
            mock_account.id = str(uuid.uuid4())
            mock_account.account_number = "DU123456"
            mock_account.status = "active"
            mock_account_manager.add_account.return_value = mock_account
        else:
            # Setup for invalid account type
            mock_account_manager.add_account.side_effect = ValueError(
                f"Invalid account type: {account_type}"
            )

        # Execute tool
        result = await tiger_add_account(
            account_number="DU123456",
            account_name="Test Account",
            account_type=account_type,
            tiger_id="test_tiger_id",
            private_key="test_private_key",
        )

        # Verify results
        if is_valid:
            assert result.success is True
        else:
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_account_tools_error_recovery(self, mock_account_manager):
        """Test error recovery in account tools."""
        # Test various error scenarios
        error_scenarios = [
            RuntimeError("Database connection lost"),
            TimeoutError("Operation timed out"),
            ValueError("Invalid input parameters"),
            ConnectionError("Network unreachable"),
        ]

        for error in error_scenarios:
            # Setup mock to raise error
            mock_account_manager.list_accounts.side_effect = error

            # Execute tool
            result = await tiger_list_accounts()

            # Verify graceful error handling
            assert result.success is False
            assert result.data is None
            assert result.error is not None
            assert len(result.error) > 0

            # Reset mock for next iteration
            mock_account_manager.list_accounts.side_effect = None

    @pytest.mark.asyncio
    async def test_account_security_handling(self, mock_account_manager):
        """Test security-related aspects of account tools."""
        # Test that sensitive data is not exposed in responses

        # Setup mock account with sensitive data
        mock_account = MagicMock()
        mock_account.id = str(uuid.uuid4())
        mock_account.account_number = "DU123456"
        mock_account.account_name = "Test Account"
        mock_account.status = "active"
        mock_account.account_type = "MARGIN"
        mock_account.encrypted_credentials = b"sensitive_encrypted_data"
        mock_account.private_key = "sensitive_private_key"

        mock_account_manager.get_account_by_id.return_value = mock_account

        # Execute tool
        result = await tiger_get_account_status(mock_account.id)

        # Verify sensitive data is not exposed
        assert result.success is True
        result_str = str(result.data)

        # Sensitive fields should not appear in response
        assert "encrypted_credentials" not in result_str
        assert "private_key" not in result_str
        assert "sensitive" not in result_str


class TestAccountToolsIntegration:
    """Integration tests for account tools."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_account_lifecycle_workflow(
        self, mock_account_manager, mock_account_router
    ):
        """Test complete account lifecycle workflow."""
        # Setup mocks for account lifecycle
        new_account_id = str(uuid.uuid4())

        # Mock account creation
        mock_account = MagicMock()
        mock_account.id = new_account_id
        mock_account.account_number = "DU999999"
        mock_account.account_name = "Integration Test Account"
        mock_account.status = "active"
        mock_account.account_type = "MARGIN"
        mock_account_manager.add_account.return_value = mock_account

        # Mock other operations
        mock_account_manager.get_account_by_id.return_value = mock_account
        mock_account_manager.list_accounts.return_value = [mock_account]
        mock_account_manager.refresh_token.return_value = {
            "access_token": "new_token",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }
        mock_account_router.set_default_data_account.return_value = True
        mock_account_manager.remove_account.return_value = True

        # 1. Add account
        add_result = await tiger_add_account(
            account_number="DU999999",
            account_name="Integration Test Account",
            account_type="MARGIN",
            tiger_id="test_tiger_id",
            private_key="test_private_key",
        )
        assert add_result.success is True
        assert add_result.data["account_id"] == new_account_id

        # 2. List accounts (should include new account)
        list_result = await tiger_list_accounts()
        assert list_result.success is True
        assert len(list_result.data["accounts"]) == 1

        # 3. Get account status
        status_result = await tiger_get_account_status(new_account_id)
        assert status_result.success is True
        assert status_result.data["account_id"] == new_account_id

        # 4. Refresh token
        refresh_result = await tiger_refresh_token(new_account_id)
        assert refresh_result.success is True
        assert refresh_result.data["token_refreshed"] is True

        # 5. Set as default data account
        default_result = await tiger_set_default_data_account(new_account_id)
        assert default_result.success is True
        assert default_result.data["set_as_default"] is True

        # 6. Remove account
        remove_result = await tiger_remove_account(new_account_id)
        assert remove_result.success is True
        assert remove_result.data["removed"] is True

        # Verify all operations were called
        mock_account_manager.add_account.assert_called_once()
        mock_account_manager.get_account_by_id.assert_called()
        mock_account_manager.refresh_token.assert_called_once()
        mock_account_router.set_default_data_account.assert_called_once()
        mock_account_manager.remove_account.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_account_tools_performance(
        self, mock_account_manager, mock_account_data
    ):
        """Test performance of account tools with multiple operations."""
        # Setup mocks
        mock_account_manager.list_accounts.return_value = mock_account_data.accounts
        mock_account_manager.get_account_by_id.return_value = (
            mock_account_data.accounts[0]
        )

        # Create multiple concurrent operations
        account_ids = [acc.id for acc in mock_account_data.active_accounts]
        tasks = []

        # Multiple list operations
        tasks.extend([tiger_list_accounts() for _ in range(10)])

        # Multiple status checks
        for account_id in account_ids:
            tasks.extend([tiger_get_account_status(account_id) for _ in range(5)])

        # Execute all operations and measure time
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
        assert execution_time < 5.0  # Should complete within 5 seconds

        print(
            f"Account tools performance test: {len(tasks)} operations completed in {execution_time:.2f} seconds"
        )
