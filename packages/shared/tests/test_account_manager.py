"""
Comprehensive unit tests for account_manager module.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock database imports before importing the account_manager
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
    mock_account_type = MagicMock()
    mock_account_status = MagicMock()
    mock_market_permission = MagicMock()
    mock_token_status = MagicMock()

    with (
        patch("shared.account_manager.get_session", mock_get_session),
        patch("shared.account_manager.TigerAccount", mock_tiger_account),
        patch("shared.account_manager.AccountType", mock_account_type),
        patch("shared.account_manager.AccountStatus", mock_account_status),
        patch("shared.account_manager.MarketPermission", mock_market_permission),
        patch("shared.account_manager.TokenStatus", mock_token_status),
    ):

        from shared.account_manager import (
            AccountManagerError,
            AccountNotFoundError,
            AccountValidationError,
            DefaultAccountError,
            TigerAccountManager,
            get_account_manager,
        )


class TestAccountManagerErrors:
    """Tests for account manager exception classes."""

    def test_account_manager_error(self):
        """Test AccountManagerError exception."""
        error = AccountManagerError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_account_not_found_error(self):
        """Test AccountNotFoundError exception."""
        error = AccountNotFoundError("Account not found")
        assert str(error) == "Account not found"
        assert isinstance(error, AccountManagerError)

    def test_account_validation_error(self):
        """Test AccountValidationError exception."""
        error = AccountValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, AccountManagerError)

    def test_default_account_error(self):
        """Test DefaultAccountError exception."""
        error = DefaultAccountError("Default account error")
        assert str(error) == "Default account error"
        assert isinstance(error, AccountManagerError)


class TestTigerAccountManagerInit:
    """Tests for TigerAccountManager initialization."""

    @patch("shared.account_manager.get_config")
    @patch("shared.account_manager.get_encryption_service")
    def test_account_manager_initialization(self, mock_encryption, mock_config):
        """Test TigerAccountManager initialization."""
        mock_config.return_value = MagicMock()
        mock_encryption.return_value = MagicMock()

        manager = TigerAccountManager()

        assert manager._config is not None
        assert manager._encryption_service is not None
        mock_config.assert_called_once()
        mock_encryption.assert_called_once()


class TestAccountCreation:
    """Tests for account creation functionality."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def sample_account_data(self):
        """Sample account creation data."""
        return {
            "account_name": "Test Account",
            "account_number": "12345678",
            "tiger_id": "test_tiger_id",
            "private_key": "test_private_key",
            "environment": "sandbox",
            "description": "Test account description",
        }

    @patch("shared.account_manager.encrypt_tiger_credentials")
    @patch("shared.account_manager.get_session")
    async def test_create_account_success(
        self,
        mock_get_session,
        mock_encrypt_creds,
        account_manager,
        mock_session,
        sample_account_data,
    ):
        """Test successful account creation."""
        # Setup mocks
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock encryption
        mock_encrypt_creds.return_value = {
            "tiger_id": MagicMock(json=MagicMock(return_value="encrypted_tiger_id")),
            "private_key": MagicMock(
                json=MagicMock(return_value="encrypted_private_key")
            ),
        }

        # Mock account instance
        mock_account_instance = MagicMock()
        mock_account_instance.id = uuid.uuid4()
        mock_tiger_account.return_value = mock_account_instance

        # Mock no existing account
        account_manager._get_account_by_number = AsyncMock(return_value=None)
        account_manager._validate_account_data = AsyncMock()
        account_manager._clear_default_trading_account = AsyncMock()
        account_manager._clear_default_data_account = AsyncMock()

        # Mock token status creation
        mock_token_status.create_scheduled_refresh.return_value = MagicMock()

        # Test account creation
        result = await account_manager.create_account(**sample_account_data)

        # Verify calls
        account_manager._validate_account_data.assert_called_once()
        mock_encrypt_creds.assert_called_once()
        mock_session.add.assert_called()
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once()

        assert result is mock_account_instance

    @patch("shared.account_manager.get_session")
    async def test_create_account_duplicate_number(
        self, mock_get_session, account_manager, mock_session, sample_account_data
    ):
        """Test account creation with duplicate account number."""
        # Setup mocks
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock existing account found
        existing_account = MagicMock()
        account_manager._get_account_by_number = AsyncMock(
            return_value=existing_account
        )
        account_manager._validate_account_data = AsyncMock()

        # Should raise validation error
        with pytest.raises(AccountValidationError, match="already exists"):
            await account_manager.create_account(**sample_account_data)

    @patch("shared.account_manager.get_session")
    async def test_create_account_validation_failure(
        self, mock_get_session, account_manager, mock_session, sample_account_data
    ):
        """Test account creation with validation failure."""
        # Setup mocks
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock validation failure
        account_manager._validate_account_data = AsyncMock(
            side_effect=AccountValidationError("Invalid data")
        )

        # Should raise validation error
        with pytest.raises(AccountValidationError, match="Invalid data"):
            await account_manager.create_account(**sample_account_data)

    async def test_create_account_default_trading_account(
        self, account_manager, sample_account_data
    ):
        """Test creating default trading account."""
        with (
            patch("shared.account_manager.get_session") as mock_get_session,
            patch("shared.account_manager.encrypt_tiger_credentials") as mock_encrypt,
        ):

            # Setup session mock
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # Setup mocks
            account_manager._validate_account_data = AsyncMock()
            account_manager._get_account_by_number = AsyncMock(return_value=None)
            account_manager._clear_default_trading_account = AsyncMock()
            account_manager._clear_default_data_account = AsyncMock()

            mock_encrypt.return_value = {
                "tiger_id": MagicMock(json=MagicMock(return_value="encrypted")),
                "private_key": MagicMock(json=MagicMock(return_value="encrypted")),
            }

            mock_account = MagicMock()
            mock_account.id = uuid.uuid4()
            mock_tiger_account.return_value = mock_account
            mock_token_status.create_scheduled_refresh.return_value = MagicMock()

            # Test with default trading flag
            sample_account_data["is_default_trading"] = True

            await account_manager.create_account(**sample_account_data)

            # Should clear existing default trading account
            account_manager._clear_default_trading_account.assert_called_once()


class TestAccountRetrieval:
    """Tests for account retrieval functionality."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    @patch("shared.account_manager.get_session")
    async def test_get_account_by_id_success(self, mock_get_session, account_manager):
        """Test successful account retrieval by ID."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_result = MagicMock()
        mock_account = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_session.execute.return_value = mock_result

        account_id = uuid.uuid4()

        # Test retrieval
        result = await account_manager.get_account_by_id(account_id)

        assert result is mock_account
        mock_session.execute.assert_called_once()

    @patch("shared.account_manager.get_session")
    async def test_get_account_by_id_not_found(self, mock_get_session, account_manager):
        """Test account retrieval when account not found."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        account_id = uuid.uuid4()

        # Test retrieval
        result = await account_manager.get_account_by_id(account_id)

        assert result is None

    @patch("shared.account_manager.get_session")
    async def test_get_account_by_id_database_error(
        self, mock_get_session, account_manager
    ):
        """Test account retrieval with database error."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_session.execute.side_effect = Exception("Database error")

        account_id = uuid.uuid4()

        # Should raise AccountManagerError
        with pytest.raises(AccountManagerError, match="Failed to get account"):
            await account_manager.get_account_by_id(account_id)

    async def test_get_account_by_number(self, account_manager):
        """Test get account by number."""
        with patch("shared.account_manager.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_account = MagicMock()
            account_manager._get_account_by_number = AsyncMock(
                return_value=mock_account
            )

            result = await account_manager.get_account_by_number("12345678")

            assert result is mock_account
            account_manager._get_account_by_number.assert_called_once_with(
                mock_session, "12345678"
            )


class TestAccountListing:
    """Tests for account listing functionality."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    @patch("shared.account_manager.get_session")
    async def test_list_accounts_no_filters(self, mock_get_session, account_manager):
        """Test listing accounts without filters."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_accounts = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_accounts
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Test listing
        result = await account_manager.list_accounts()

        assert result == mock_accounts
        mock_session.execute.assert_called_once()

    @patch("shared.account_manager.get_session")
    async def test_list_accounts_with_filters(self, mock_get_session, account_manager):
        """Test listing accounts with filters."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_accounts = [MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_accounts
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Test with filters
        result = await account_manager.list_accounts(
            environment="sandbox", include_inactive=True
        )

        assert result == mock_accounts
        mock_session.execute.assert_called_once()


class TestAccountUpdate:
    """Tests for account update functionality."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    @patch("shared.account_manager.get_session")
    async def test_update_account_success(self, mock_get_session, account_manager):
        """Test successful account update."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        mock_account.account_name = "Old Name"
        account_manager._get_account_by_id_for_update = AsyncMock(
            return_value=mock_account
        )

        account_id = uuid.uuid4()
        updates = {"account_name": "New Name", "description": "Updated description"}

        # Test update
        result = await account_manager.update_account(account_id, updates)

        assert result is mock_account
        assert mock_account.account_name == "New Name"
        assert mock_account.description == "Updated description"
        mock_session.commit.assert_called_once()

    @patch("shared.account_manager.get_session")
    async def test_update_account_not_found(self, mock_get_session, account_manager):
        """Test account update when account not found."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        account_manager._get_account_by_id_for_update = AsyncMock(
            side_effect=AccountNotFoundError("Account not found")
        )

        account_id = uuid.uuid4()
        updates = {"account_name": "New Name"}

        # Should raise AccountNotFoundError
        with pytest.raises(AccountNotFoundError, match="Account not found"):
            await account_manager.update_account(account_id, updates)


class TestAccountDeletion:
    """Tests for account deletion functionality."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    @patch("shared.account_manager.get_session")
    async def test_delete_account_soft_delete(self, mock_get_session, account_manager):
        """Test soft account deletion."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        account_manager._get_account_by_id_for_update = AsyncMock(
            return_value=mock_account
        )

        account_id = uuid.uuid4()

        # Test soft delete
        result = await account_manager.delete_account(account_id, force=False)

        assert result is True
        # Should set status to INACTIVE and deleted_at timestamp
        mock_session.commit.assert_called_once()

    @patch("shared.account_manager.get_session")
    async def test_delete_account_hard_delete(self, mock_get_session, account_manager):
        """Test hard account deletion."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        account_manager._get_account_by_id_for_update = AsyncMock(
            return_value=mock_account
        )

        account_id = uuid.uuid4()

        # Test hard delete
        result = await account_manager.delete_account(account_id, force=True)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_account)
        mock_session.commit.assert_called_once()


class TestDefaultAccountManagement:
    """Tests for default account management."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    @patch("shared.account_manager.get_session")
    async def test_get_default_trading_account(self, mock_get_session, account_manager):
        """Test getting default trading account."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_session.execute.return_value = mock_result

        # Test retrieval
        result = await account_manager.get_default_trading_account()

        assert result is mock_account

    @patch("shared.account_manager.get_session")
    async def test_set_default_trading_account(self, mock_get_session, account_manager):
        """Test setting default trading account."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        account_manager._get_account_by_id_for_update = AsyncMock(
            return_value=mock_account
        )
        account_manager._clear_default_trading_account = AsyncMock()

        account_id = uuid.uuid4()

        # Test setting default
        result = await account_manager.set_default_trading_account(account_id)

        assert result is mock_account
        assert mock_account.is_default_trading is True
        account_manager._clear_default_trading_account.assert_called_once()
        mock_session.commit.assert_called_once()


class TestCredentialManagement:
    """Tests for credential encryption/decryption."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service") as mock_encryption,
        ):
            manager = TigerAccountManager()
            manager._encryption_service = mock_encryption.return_value
            return manager

    @patch("shared.account_manager.decrypt_tiger_credentials")
    async def test_decrypt_credentials(self, mock_decrypt_creds, account_manager):
        """Test credential decryption."""
        mock_account = MagicMock()
        mock_account.tiger_id = '{"encrypted": "tiger_id_data"}'
        mock_account.private_key = '{"encrypted": "private_key_data"}'

        decrypted_creds = {
            "tiger_id": "decrypted_tiger_id",
            "private_key": "decrypted_private_key",
        }
        mock_decrypt_creds.return_value = decrypted_creds

        result = await account_manager.decrypt_credentials(mock_account)

        assert result == decrypted_creds
        mock_decrypt_creds.assert_called_once()


class TestTokenManagement:
    """Tests for token management functionality."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    @patch("shared.account_manager.encrypt_tiger_credentials")
    @patch("shared.account_manager.get_session")
    async def test_update_tokens(
        self, mock_get_session, mock_encrypt_creds, account_manager
    ):
        """Test token update functionality."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        account_manager._get_account_by_id_for_update = AsyncMock(
            return_value=mock_account
        )

        mock_encrypt_creds.return_value = {
            "access_token": MagicMock(json=MagicMock(return_value="encrypted_access")),
            "refresh_token": MagicMock(
                json=MagicMock(return_value="encrypted_refresh")
            ),
        }

        account_id = uuid.uuid4()
        tokens = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        # Test token update
        result = await account_manager.update_tokens(account_id, tokens)

        assert result is mock_account
        mock_encrypt_creds.assert_called_once()
        mock_session.commit.assert_called_once()


class TestAccountStatus:
    """Tests for account status management."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    @patch("shared.account_manager.get_session")
    async def test_update_account_status(self, mock_get_session, account_manager):
        """Test account status update."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        account_manager._get_account_by_id_for_update = AsyncMock(
            return_value=mock_account
        )

        account_id = uuid.uuid4()
        new_status = MagicMock()
        reason = "Test reason"

        # Test status update
        result = await account_manager.update_account_status(
            account_id, new_status, reason
        )

        assert result is mock_account
        assert mock_account.status == new_status
        assert mock_account.status_reason == reason
        mock_session.commit.assert_called_once()

    @patch("shared.account_manager.get_session")
    async def test_increment_error_count(self, mock_get_session, account_manager):
        """Test error count increment."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_account = MagicMock()
        mock_account.error_count = 2
        account_manager._get_account_by_id_for_update = AsyncMock(
            return_value=mock_account
        )

        account_id = uuid.uuid4()
        error_message = "Test error"

        # Test error count increment
        result = await account_manager.increment_error_count(account_id, error_message)

        assert result is mock_account
        assert mock_account.error_count == 3
        assert mock_account.last_error == error_message
        mock_session.commit.assert_called_once()


class TestPrivateMethods:
    """Tests for private/helper methods."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    async def test_validate_account_data_success(self, account_manager):
        """Test account data validation success."""
        # Should not raise exception for valid data
        await account_manager._validate_account_data(
            account_name="Test Account",
            account_number="12345678",
            tiger_id="test_tiger_id",
            private_key="test_private_key",
            environment="sandbox",
        )

    async def test_validate_account_data_invalid_name(self, account_manager):
        """Test account data validation with invalid name."""
        with pytest.raises(AccountValidationError, match="Account name"):
            await account_manager._validate_account_data(
                account_name="",  # Empty name
                account_number="12345678",
                tiger_id="test_tiger_id",
                private_key="test_private_key",
                environment="sandbox",
            )

    async def test_validate_account_data_invalid_environment(self, account_manager):
        """Test account data validation with invalid environment."""
        with pytest.raises(AccountValidationError, match="Environment"):
            await account_manager._validate_account_data(
                account_name="Test Account",
                account_number="12345678",
                tiger_id="test_tiger_id",
                private_key="test_private_key",
                environment="invalid",  # Invalid environment
            )


class TestSingletonFunction:
    """Tests for singleton function."""

    def test_get_account_manager_singleton(self):
        """Test get_account_manager returns singleton."""
        with patch("shared.account_manager.TigerAccountManager") as mock_manager:
            manager1 = get_account_manager()
            manager2 = get_account_manager()

            assert manager1 is manager2
            # Should only create instance once
            mock_manager.assert_called_once()


class TestAccountManagerIntegration:
    """Integration tests for account manager functionality."""

    @pytest.fixture
    def account_manager(self):
        """Create account manager instance for testing."""
        with (
            patch("shared.account_manager.get_config"),
            patch("shared.account_manager.get_encryption_service"),
        ):
            return TigerAccountManager()

    async def test_complete_account_lifecycle(self, account_manager):
        """Test complete account lifecycle."""
        with (
            patch("shared.account_manager.get_session") as mock_get_session,
            patch("shared.account_manager.encrypt_tiger_credentials") as mock_encrypt,
        ):

            # Setup mocks for account creation
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            account_manager._validate_account_data = AsyncMock()
            account_manager._get_account_by_number = AsyncMock(return_value=None)
            account_manager._clear_default_trading_account = AsyncMock()
            account_manager._clear_default_data_account = AsyncMock()

            mock_encrypt.return_value = {
                "tiger_id": MagicMock(json=MagicMock(return_value="encrypted")),
                "private_key": MagicMock(json=MagicMock(return_value="encrypted")),
            }

            account_id = uuid.uuid4()
            mock_account = MagicMock()
            mock_account.id = account_id
            mock_tiger_account.return_value = mock_account
            mock_token_status.create_scheduled_refresh.return_value = MagicMock()

            # 1. Create account
            created_account = await account_manager.create_account(
                account_name="Test Account",
                account_number="12345678",
                tiger_id="test_tiger_id",
                private_key="test_private_key",
            )

            assert created_account is mock_account

            # 2. Update account
            account_manager._get_account_by_id_for_update = AsyncMock(
                return_value=mock_account
            )

            updated_account = await account_manager.update_account(
                account_id, {"account_name": "Updated Account"}
            )

            assert updated_account is mock_account

            # 3. Delete account (soft delete)
            deleted = await account_manager.delete_account(account_id, force=False)

            assert deleted is True

    async def test_error_handling_chain(self, account_manager):
        """Test error handling across different operations."""
        account_id = uuid.uuid4()

        # Test cascading error handling
        with patch("shared.account_manager.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # Database error should be caught and re-raised as AccountManagerError
            mock_session.execute.side_effect = Exception("Database connection failed")

            with pytest.raises(AccountManagerError, match="Failed to get account"):
                await account_manager.get_account_by_id(account_id)

    async def test_concurrent_default_account_operations(self, account_manager):
        """Test concurrent default account operations."""
        with patch("shared.account_manager.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            account_manager._get_account_by_id_for_update = AsyncMock()
            account_manager._clear_default_trading_account = AsyncMock()

            # Mock accounts
            account1_id = uuid.uuid4()
            account2_id = uuid.uuid4()

            mock_account1 = MagicMock()
            mock_account2 = MagicMock()

            account_manager._get_account_by_id_for_update.side_effect = [
                mock_account1,
                mock_account2,
            ]

            # Set multiple accounts as default (should clear previous)
            await account_manager.set_default_trading_account(account1_id)
            await account_manager.set_default_trading_account(account2_id)

            # Should have cleared default twice (once for each set operation)
            assert account_manager._clear_default_trading_account.call_count == 2
