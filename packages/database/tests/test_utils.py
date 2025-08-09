"""
Tests for database utility functions.

This module tests all utility classes including:
- CRUD operations with different filtering
- Pagination and sorting functionality
- Bulk operations and transactions
- Error handling and data validation
- Mock database sessions for isolation
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from database.models import TigerAccount
from database.models.accounts import AccountStatus, AccountType
from database.models.api_keys import APIKeyScope, APIKeyStatus
from database.models.audit_logs import AuditAction, AuditResult, AuditSeverity
from database.models.token_status import RefreshTrigger, TokenRefreshStatus
from database.utils import (
    APIKeyUtils,
    AuditLogUtils,
    DatabaseUtils,
    TigerAccountUtils,
    TokenStatusUtils,
    create_utils,
)
from sqlalchemy.exc import IntegrityError, NoResultFound


class TestDatabaseUtils:
    """Test cases for base DatabaseUtils class."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_utils, sample_tiger_account):
        """Test retrieving object by ID."""
        result = await db_utils.get_by_id(TigerAccount, sample_tiger_account.id)

        assert result is not None
        assert result.id == sample_tiger_account.id
        assert result.account_name == sample_tiger_account.account_name

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_utils):
        """Test retrieving non-existent object by ID."""
        non_existent_id = uuid.uuid4()
        result = await db_utils.get_by_id(TigerAccount, non_existent_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_relationships(
        self, db_utils, sample_tiger_account, sample_api_key
    ):
        """Test retrieving object with relationship loading."""
        result = await db_utils.get_by_id(
            TigerAccount, sample_tiger_account.id, load_relations=["api_keys"]
        )

        assert result is not None
        assert len(result.api_keys) >= 1
        assert any(key.id == sample_api_key.id for key in result.api_keys)

    @pytest.mark.asyncio
    async def test_get_by_field(self, db_utils, sample_tiger_account):
        """Test retrieving object by field value."""
        result = await db_utils.get_by_field(
            TigerAccount, "account_number", sample_tiger_account.account_number
        )

        assert result is not None
        assert result.id == sample_tiger_account.id
        assert result.account_number == sample_tiger_account.account_number

    @pytest.mark.asyncio
    async def test_get_by_field_not_found(self, db_utils):
        """Test retrieving non-existent object by field."""
        result = await db_utils.get_by_field(
            TigerAccount, "account_number", "NON_EXISTENT_ACCOUNT"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_list_with_pagination_basic(
        self, db_utils, db_session, tiger_account_factory
    ):
        """Test basic pagination functionality."""
        # Create test accounts
        accounts = tiger_account_factory.create_batch(5)
        for account in accounts:
            db_session.add(account)
        await db_session.flush()

        # Test pagination
        result = await db_utils.list_with_pagination(TigerAccount, page=1, page_size=3)

        assert result["total_count"] == 5
        assert len(result["items"]) == 3
        assert result["page"] == 1
        assert result["page_size"] == 3
        assert result["total_pages"] == 2
        assert result["has_next"] is True
        assert result["has_prev"] is False

    @pytest.mark.asyncio
    async def test_list_with_pagination_filters(
        self, db_utils, db_session, tiger_account_factory
    ):
        """Test pagination with filters."""
        # Create accounts with different types
        account1 = tiger_account_factory.create(account_type=AccountType.STANDARD)
        account2 = tiger_account_factory.create(account_type=AccountType.PAPER)
        account3 = tiger_account_factory.create(account_type=AccountType.STANDARD)

        for account in [account1, account2, account3]:
            db_session.add(account)
        await db_session.flush()

        # Filter by account type
        result = await db_utils.list_with_pagination(
            TigerAccount, filters={"account_type": AccountType.STANDARD}
        )

        assert result["total_count"] == 2
        assert len(result["items"]) == 2
        assert all(
            item.account_type == AccountType.STANDARD for item in result["items"]
        )

    @pytest.mark.asyncio
    async def test_list_with_pagination_ordering(
        self, db_utils, db_session, tiger_account_factory
    ):
        """Test pagination with ordering."""
        # Create accounts with different names
        accounts = [
            tiger_account_factory.create(account_name="Alpha Account"),
            tiger_account_factory.create(account_name="Beta Account"),
            tiger_account_factory.create(account_name="Charlie Account"),
        ]

        for account in accounts:
            db_session.add(account)
        await db_session.flush()

        # Order by name ascending
        result = await db_utils.list_with_pagination(
            TigerAccount, order_by="account_name", order_desc=False
        )

        names = [item.account_name for item in result["items"]]
        assert names == sorted(names)

        # Order by name descending
        result = await db_utils.list_with_pagination(
            TigerAccount, order_by="account_name", order_desc=True
        )

        names = [item.account_name for item in result["items"]]
        assert names == sorted(names, reverse=True)

    @pytest.mark.asyncio
    async def test_create(self, db_utils):
        """Test creating new object."""
        account_data = {
            "account_name": "New Test Account",
            "account_number": "NEW123456789",
            "account_type": AccountType.STANDARD,
            "status": AccountStatus.ACTIVE,
            "tiger_id": "new_tiger_id",
            "private_key": "new_private_key",
        }

        result = await db_utils.create(TigerAccount, **account_data)

        assert result.id is not None
        assert result.account_name == account_data["account_name"]
        assert result.account_number == account_data["account_number"]
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_update(self, db_utils, sample_tiger_account):
        """Test updating existing object."""
        new_name = "Updated Account Name"
        original_updated_at = sample_tiger_account.updated_at

        # Small delay to ensure timestamp difference
        import asyncio

        await asyncio.sleep(0.01)

        result = await db_utils.update(sample_tiger_account, account_name=new_name)

        assert result.account_name == new_name
        assert result.updated_at > original_updated_at
        assert result.id == sample_tiger_account.id  # ID should remain the same

    @pytest.mark.asyncio
    async def test_delete(self, db_utils, db_session, tiger_account_factory):
        """Test deleting object."""
        # Create account to delete
        account = tiger_account_factory.create()
        db_session.add(account)
        await db_session.flush()

        account_id = account.id

        # Delete the account
        await db_utils.delete(account)

        # Verify deletion
        result = await db_utils.get_by_id(TigerAccount, account_id)
        assert result is None


class TestTigerAccountUtils:
    """Test cases for TigerAccountUtils class."""

    @pytest.mark.asyncio
    async def test_get_default_trading_account(
        self, account_utils, db_session, tiger_account_factory
    ):
        """Test getting default trading account."""
        # Create default trading account
        default_account = tiger_account_factory.create(is_default_trading=True)
        regular_account = tiger_account_factory.create(is_default_trading=False)

        db_session.add(default_account)
        db_session.add(regular_account)
        await db_session.flush()

        result = await account_utils.get_default_trading_account()

        assert result is not None
        assert result.id == default_account.id
        assert result.is_default_trading is True

    @pytest.mark.asyncio
    async def test_get_default_data_account(
        self, account_utils, db_session, tiger_account_factory
    ):
        """Test getting default data account."""
        # Create default data account
        default_account = tiger_account_factory.create(is_default_data=True)
        regular_account = tiger_account_factory.create(is_default_data=False)

        db_session.add(default_account)
        db_session.add(regular_account)
        await db_session.flush()

        result = await account_utils.get_default_data_account()

        assert result is not None
        assert result.id == default_account.id
        assert result.is_default_data is True

    @pytest.mark.asyncio
    async def test_get_by_account_number(self, account_utils, sample_tiger_account):
        """Test getting account by account number."""
        result = await account_utils.get_by_account_number(
            sample_tiger_account.account_number
        )

        assert result is not None
        assert result.id == sample_tiger_account.id
        assert result.account_number == sample_tiger_account.account_number

    @pytest.mark.asyncio
    async def test_get_active_accounts(
        self, account_utils, db_session, tiger_account_factory
    ):
        """Test getting all active accounts."""
        # Create mix of active and inactive accounts
        active_accounts = [
            tiger_account_factory.create(status=AccountStatus.ACTIVE),
            tiger_account_factory.create(status=AccountStatus.ACTIVE),
        ]
        inactive_account = tiger_account_factory.create(status=AccountStatus.INACTIVE)

        for account in active_accounts + [inactive_account]:
            db_session.add(account)
        await db_session.flush()

        result = await account_utils.get_active_accounts()

        assert len(result) >= 2  # At least our test accounts
        assert all(account.status == AccountStatus.ACTIVE for account in result)

    @pytest.mark.asyncio
    async def test_get_accounts_needing_token_refresh(
        self, account_utils, db_session, tiger_account_factory
    ):
        """Test getting accounts needing token refresh."""
        now = datetime.now(timezone.utc)

        # Create accounts with different token states
        expired_account = tiger_account_factory.create(
            token_expires_at=now - timedelta(hours=1)
        )
        no_token_account = tiger_account_factory.create(token_expires_at=None)
        valid_account = tiger_account_factory.create(
            token_expires_at=now + timedelta(hours=2)
        )

        for account in [expired_account, no_token_account, valid_account]:
            db_session.add(account)
        await db_session.flush()

        result = await account_utils.get_accounts_needing_token_refresh()

        # Should include expired and no-token accounts
        account_ids = [account.id for account in result]
        assert expired_account.id in account_ids
        assert no_token_account.id in account_ids
        assert valid_account.id not in account_ids

    @pytest.mark.asyncio
    async def test_set_default_trading_account(
        self, account_utils, db_session, tiger_account_factory
    ):
        """Test setting default trading account."""
        # Create accounts
        account1 = tiger_account_factory.create(is_default_trading=True)
        account2 = tiger_account_factory.create(is_default_trading=False)

        db_session.add(account1)
        db_session.add(account2)
        await db_session.flush()

        # Set account2 as default
        result = await account_utils.set_default_trading_account(account2.id)

        assert result.id == account2.id
        assert result.is_default_trading is True

        # Verify account1 is no longer default
        await db_session.refresh(account1)
        assert account1.is_default_trading is False

    @pytest.mark.asyncio
    async def test_set_default_trading_account_not_found(self, account_utils):
        """Test setting default for non-existent account."""
        non_existent_id = uuid.uuid4()

        with pytest.raises(NoResultFound):
            await account_utils.set_default_trading_account(non_existent_id)


class TestAPIKeyUtils:
    """Test cases for APIKeyUtils class."""

    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = APIKeyUtils.generate_api_key()

        assert api_key.startswith("tmcp_")
        assert len(api_key) > 10  # Should be reasonably long

        # Generate another key to ensure uniqueness
        api_key2 = APIKeyUtils.generate_api_key()
        assert api_key != api_key2

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "test_api_key_12345"
        hash1 = APIKeyUtils.hash_api_key(api_key)
        hash2 = APIKeyUtils.hash_api_key(api_key)

        # Same input should produce same hash
        assert hash1 == hash2

        # Hash should be SHA-256 (64 hex characters)
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)

        # Different inputs should produce different hashes
        different_hash = APIKeyUtils.hash_api_key("different_key")
        assert hash1 != different_hash

    def test_get_key_prefix(self):
        """Test API key prefix extraction."""
        api_key = "tmcp_abcdef123456789"
        prefix = APIKeyUtils.get_key_prefix(api_key)

        assert prefix == "tmcp_abc"
        assert len(prefix) == 8

    @pytest.mark.asyncio
    async def test_get_by_hash(self, api_key_utils, sample_api_key):
        """Test getting API key by hash."""
        result = await api_key_utils.get_by_hash(sample_api_key.key_hash)

        assert result is not None
        assert result.id == sample_api_key.id
        assert result.key_hash == sample_api_key.key_hash

    @pytest.mark.asyncio
    async def test_get_active_keys(self, api_key_utils, db_session, api_key_factory):
        """Test getting active API keys."""
        now = datetime.now(timezone.utc)

        # Create mix of active, inactive, and expired keys
        active_key = api_key_factory.create(
            status=APIKeyStatus.ACTIVE, expires_at=now + timedelta(days=30)
        )
        inactive_key = api_key_factory.create(
            status=APIKeyStatus.INACTIVE, expires_at=now + timedelta(days=30)
        )
        expired_key = api_key_factory.create(
            status=APIKeyStatus.ACTIVE, expires_at=now - timedelta(days=1)
        )

        for key in [active_key, inactive_key, expired_key]:
            db_session.add(key)
        await db_session.flush()

        result = await api_key_utils.get_active_keys()

        # Should only include active, non-expired keys
        key_ids = [key.id for key in result]
        assert active_key.id in key_ids
        assert inactive_key.id not in key_ids
        assert expired_key.id not in key_ids

    @pytest.mark.asyncio
    async def test_get_keys_for_account(
        self, api_key_utils, sample_tiger_account, db_session, api_key_factory
    ):
        """Test getting keys for specific account."""
        # Create keys for different accounts
        account_key = api_key_factory.create(tiger_account_id=sample_tiger_account.id)
        other_key = api_key_factory.create(
            tiger_account_id=uuid.uuid4()
        )  # Different account

        db_session.add(account_key)
        db_session.add(other_key)
        await db_session.flush()

        result = await api_key_utils.get_keys_for_account(sample_tiger_account.id)

        # Should include keys for the specified account
        key_ids = [key.id for key in result]
        assert account_key.id in key_ids
        assert other_key.id not in key_ids

    @pytest.mark.asyncio
    async def test_create_api_key(self, api_key_utils, sample_tiger_account):
        """Test creating new API key."""
        scopes = [APIKeyScope.MCP_READ, APIKeyScope.MCP_WRITE]
        expires_at = datetime.now(timezone.utc) + timedelta(days=90)

        api_key, raw_key = await api_key_utils.create_api_key(
            name="Test Key",
            scopes=scopes,
            tiger_account_id=sample_tiger_account.id,
            expires_at=expires_at,
        )

        assert api_key.id is not None
        assert api_key.name == "Test Key"
        assert api_key.scopes == [scope.value for scope in scopes]
        assert api_key.tiger_account_id == sample_tiger_account.id
        assert api_key.expires_at == expires_at

        # Raw key should start with prefix
        assert raw_key.startswith("tmcp_")

        # Hash should match
        expected_hash = APIKeyUtils.hash_api_key(raw_key)
        assert api_key.key_hash == expected_hash

    @pytest.mark.asyncio
    async def test_verify_api_key(self, api_key_utils, db_session):
        """Test API key verification."""
        # Create API key
        scopes = [APIKeyScope.MCP_READ]
        api_key, raw_key = await api_key_utils.create_api_key(
            name="Verify Test Key", scopes=scopes
        )
        await db_session.flush()

        # Test valid key
        verified_key = await api_key_utils.verify_api_key(raw_key)

        assert verified_key is not None
        assert verified_key.id == api_key.id
        assert verified_key.usage_count > 0  # Should increment usage

        # Test invalid key
        invalid_result = await api_key_utils.verify_api_key("invalid_key")
        assert invalid_result is None

    @pytest.mark.asyncio
    async def test_verify_inactive_api_key(self, api_key_utils, db_session):
        """Test verification of inactive API key."""
        # Create inactive API key
        scopes = [APIKeyScope.MCP_READ]
        api_key, raw_key = await api_key_utils.create_api_key(
            name="Inactive Key", scopes=scopes
        )
        api_key.status = APIKeyStatus.INACTIVE
        await db_session.flush()

        # Should fail verification
        result = await api_key_utils.verify_api_key(raw_key)
        assert result is None


class TestAuditLogUtils:
    """Test cases for AuditLogUtils class."""

    @pytest.mark.asyncio
    async def test_log_event(
        self, audit_log_utils, sample_tiger_account, sample_api_key
    ):
        """Test logging audit event."""
        details = {"request_id": "req_123", "action": "create_account"}

        audit_log = await audit_log_utils.log_event(
            action=AuditAction.ACCOUNT_CREATE,
            result=AuditResult.SUCCESS,
            severity=AuditSeverity.MEDIUM,
            tiger_account_id=sample_tiger_account.id,
            api_key_id=sample_api_key.id,
            user_id="test_user",
            ip_address="192.168.1.100",
            details=details,
        )

        assert audit_log.id is not None
        assert audit_log.action == AuditAction.ACCOUNT_CREATE
        assert audit_log.result == AuditResult.SUCCESS
        assert audit_log.severity == AuditSeverity.MEDIUM
        assert audit_log.tiger_account_id == sample_tiger_account.id
        assert audit_log.api_key_id == sample_api_key.id
        assert audit_log.user_id == "test_user"
        assert audit_log.ip_address == "192.168.1.100"
        assert audit_log.details == details

    @pytest.mark.asyncio
    async def test_get_recent_events(
        self, audit_log_utils, db_session, audit_log_factory
    ):
        """Test getting recent audit events."""
        # Create multiple audit logs
        logs = audit_log_factory.create_batch(5)
        for log in logs:
            db_session.add(log)
        await db_session.flush()

        # Get recent events
        result = await audit_log_utils.get_recent_events(limit=3)

        assert len(result) == 3
        # Should be ordered by created_at desc (most recent first)
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at

    @pytest.mark.asyncio
    async def test_get_recent_events_with_filters(
        self, audit_log_utils, db_session, audit_log_factory
    ):
        """Test getting recent events with filters."""
        # Create logs with different severities
        critical_log = audit_log_factory.create(severity=AuditSeverity.CRITICAL)
        medium_log = audit_log_factory.create(severity=AuditSeverity.MEDIUM)
        low_log = audit_log_factory.create(severity=AuditSeverity.LOW)

        for log in [critical_log, medium_log, low_log]:
            db_session.add(log)
        await db_session.flush()

        # Filter by severity
        result = await audit_log_utils.get_recent_events(
            severity=AuditSeverity.CRITICAL
        )

        assert (
            len([log for log in result if log.severity == AuditSeverity.CRITICAL]) >= 1
        )
        assert all(log.severity == AuditSeverity.CRITICAL for log in result)

    @pytest.mark.asyncio
    async def test_get_security_events(
        self, audit_log_utils, db_session, audit_log_factory
    ):
        """Test getting security-related events."""
        # Create security and non-security events
        security_log = audit_log_factory.create(
            action=AuditAction.SECURITY_BREACH_DETECTED
        )
        regular_log = audit_log_factory.create(action=AuditAction.ACCOUNT_UPDATE)

        db_session.add(security_log)
        db_session.add(regular_log)
        await db_session.flush()

        result = await audit_log_utils.get_security_events(hours=24)

        # Should include security events
        security_actions = [
            AuditAction.SECURITY_AUTH_FAIL,
            AuditAction.SECURITY_ACCESS_DENIED,
            AuditAction.SECURITY_BREACH_DETECTED,
            AuditAction.API_KEY_CREATE,
            AuditAction.API_KEY_REVOKE,
            AuditAction.ACCOUNT_LOGIN,
        ]

        security_log_ids = [log.id for log in result if log.action in security_actions]
        assert security_log.id in security_log_ids


class TestTokenStatusUtils:
    """Test cases for TokenStatusUtils class."""

    @pytest.mark.asyncio
    async def test_get_latest_status(
        self, token_status_utils, sample_tiger_account, db_session, token_status_factory
    ):
        """Test getting latest token status for account."""
        # Create multiple token statuses for the account
        older_status = token_status_factory.create(
            tiger_account_id=sample_tiger_account.id, status=TokenRefreshStatus.SUCCESS
        )
        newer_status = token_status_factory.create(
            tiger_account_id=sample_tiger_account.id, status=TokenRefreshStatus.PENDING
        )

        db_session.add(older_status)
        await db_session.flush()

        # Add newer status with slight delay
        import asyncio

        await asyncio.sleep(0.01)
        db_session.add(newer_status)
        await db_session.flush()

        result = await token_status_utils.get_latest_status(sample_tiger_account.id)

        assert result is not None
        assert result.id == newer_status.id
        assert result.status == TokenRefreshStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_pending_refreshes(
        self, token_status_utils, db_session, token_status_factory
    ):
        """Test getting pending token refresh operations."""
        # Create mix of pending and completed refreshes
        pending_status = token_status_factory.create(status=TokenRefreshStatus.PENDING)
        success_status = token_status_factory.create(status=TokenRefreshStatus.SUCCESS)
        failed_status = token_status_factory.create(status=TokenRefreshStatus.FAILED)

        for status in [pending_status, success_status, failed_status]:
            db_session.add(status)
        await db_session.flush()

        result = await token_status_utils.get_pending_refreshes()

        # Should only include pending refreshes
        pending_ids = [status.id for status in result]
        assert pending_status.id in pending_ids
        assert success_status.id not in pending_ids
        assert failed_status.id not in pending_ids

    @pytest.mark.asyncio
    async def test_get_failed_refreshes(
        self, token_status_utils, db_session, token_status_factory
    ):
        """Test getting failed refresh operations."""
        # Create failed refresh within time window
        failed_status = token_status_factory.create(status=TokenRefreshStatus.FAILED)
        success_status = token_status_factory.create(status=TokenRefreshStatus.SUCCESS)

        for status in [failed_status, success_status]:
            db_session.add(status)
        await db_session.flush()

        result = await token_status_utils.get_failed_refreshes(hours=24)

        # Should only include failed refreshes
        failed_ids = [status.id for status in result]
        assert failed_status.id in failed_ids
        assert success_status.id not in failed_ids

    @pytest.mark.asyncio
    async def test_create_refresh_operation(
        self, token_status_utils, sample_tiger_account
    ):
        """Test creating token refresh operation."""
        current_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        current_hash = "current_token_hash"

        token_status = await token_status_utils.create_refresh_operation(
            tiger_account_id=sample_tiger_account.id,
            trigger=RefreshTrigger.AUTOMATIC,
            current_token_expires_at=current_expires,
            current_token_hash=current_hash,
        )

        assert token_status.id is not None
        assert token_status.tiger_account_id == sample_tiger_account.id
        assert token_status.trigger == RefreshTrigger.AUTOMATIC
        assert token_status.old_token_expires_at == current_expires
        assert token_status.old_token_hash == current_hash
        assert token_status.status == TokenRefreshStatus.PENDING


class TestCreateUtils:
    """Test cases for create_utils convenience function."""

    @pytest.mark.asyncio
    async def test_create_utils_function(self, db_session):
        """Test creating utils instances."""
        utils = create_utils(db_session)

        assert "base" in utils
        assert "accounts" in utils
        assert "api_keys" in utils
        assert "audit_logs" in utils
        assert "token_status" in utils

        assert isinstance(utils["base"], DatabaseUtils)
        assert isinstance(utils["accounts"], TigerAccountUtils)
        assert isinstance(utils["api_keys"], APIKeyUtils)
        assert isinstance(utils["audit_logs"], AuditLogUtils)
        assert isinstance(utils["token_status"], TokenStatusUtils)

        # All utils should use the same session
        for util in utils.values():
            assert util.session == db_session


class TestUtilsErrorHandling:
    """Test error handling in utility functions."""

    @pytest.mark.asyncio
    async def test_create_with_integrity_error(self, db_utils, tiger_account_factory):
        """Test create operation with integrity constraint violation."""
        # Create first account
        account1_data = {
            "account_name": "Test Account",
            "account_number": "DUPLICATE123",
            "account_type": AccountType.STANDARD,
            "status": AccountStatus.ACTIVE,
            "tiger_id": "tiger_id_1",
            "private_key": "private_key_1",
        }
        await db_utils.create(TigerAccount, **account1_data)

        # Try to create account with same account number
        account2_data = account1_data.copy()
        account2_data["tiger_id"] = "tiger_id_2"

        with pytest.raises(IntegrityError):
            await db_utils.create(TigerAccount, **account2_data)

    @pytest.mark.asyncio
    async def test_update_nonexistent_object(self, db_utils, tiger_account_factory):
        """Test updating an object that doesn't exist in session."""
        account = tiger_account_factory.create()
        # Don't add to session

        # This should work as update just sets attributes
        result = await db_utils.update(account, account_name="New Name")
        assert result.account_name == "New Name"

    @pytest.mark.asyncio
    async def test_api_key_verification_with_mock_session(self, mock_async_session):
        """Test API key verification with mocked session."""
        api_key_utils = APIKeyUtils(mock_async_session)

        # Mock the database query to return None (key not found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await api_key_utils.verify_api_key("invalid_key")

        assert result is None
        mock_async_session.execute.assert_called_once()


class TestUtilsPerformance:
    """Test performance aspects of utility functions."""

    @pytest.mark.asyncio
    async def test_bulk_operations_performance(
        self, db_utils, db_session, tiger_account_factory
    ):
        """Test performance of bulk operations."""
        # Create multiple accounts for testing
        accounts = tiger_account_factory.create_batch(10)

        # Add all at once for better performance
        for account in accounts:
            db_session.add(account)
        await db_session.flush()

        # Test that pagination works efficiently with larger datasets
        result = await db_utils.list_with_pagination(TigerAccount, page=1, page_size=5)

        assert len(result["items"]) == 5
        assert result["total_count"] >= 10

    @pytest.mark.asyncio
    async def test_relationship_loading_efficiency(
        self, account_utils, db_session, tiger_account_factory, api_key_factory
    ):
        """Test efficient relationship loading."""
        # Create account with multiple API keys
        account = tiger_account_factory.create()
        db_session.add(account)
        await db_session.flush()

        # Create multiple API keys for the account
        api_keys = api_key_factory.create_batch(3)
        for key in api_keys:
            key.tiger_account_id = account.id
            db_session.add(key)
        await db_session.flush()

        # Get account with relationships loaded
        result = await account_utils.get_by_account_number(account.account_number)

        assert result is not None
        assert len(result.api_keys) == 3
        # This should not cause N+1 queries due to selectin loading
