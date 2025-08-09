"""
Tests for database models.

This module tests all SQLAlchemy models including:
- Model relationships and foreign keys
- Validation constraints and unique indexes
- ENUM types and JSONB fields
- Model creation, updates, and deletions
- UUID generation and timestamp handling
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from database.models import APIKey, AuditLog, TigerAccount
from database.models.accounts import AccountStatus, AccountType, MarketPermission
from database.models.api_keys import APIKeyScope, APIKeyStatus
from database.models.audit_logs import AuditAction, AuditResult, AuditSeverity
from database.models.token_status import RefreshTrigger, TokenRefreshStatus
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


class TestTigerAccountModel:
    """Test cases for TigerAccount model."""

    @pytest.mark.asyncio
    async def test_create_tiger_account(self, db_session, tiger_account_factory):
        """Test creating a TigerAccount instance."""
        account = tiger_account_factory.create()
        db_session.add(account)
        await db_session.flush()

        assert account.id is not None
        assert isinstance(account.id, uuid.UUID)
        assert account.created_at is not None
        assert account.updated_at is not None
        assert account.account_name == "Test Account"
        assert account.account_type == AccountType.STANDARD
        assert account.status == AccountStatus.ACTIVE
        assert account.environment == "sandbox"

    @pytest.mark.asyncio
    async def test_tiger_account_unique_account_number(
        self, db_session, tiger_account_factory
    ):
        """Test that account_number must be unique."""
        account_number = "ACC12345678"

        # Create first account
        account1 = tiger_account_factory.create(account_number=account_number)
        db_session.add(account1)
        await db_session.flush()

        # Try to create second account with same number
        account2 = tiger_account_factory.create(account_number=account_number)
        db_session.add(account2)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_tiger_account_default_constraints(
        self, db_session, tiger_account_factory
    ):
        """Test that only one default trading/data account can exist."""
        # Create first default trading account
        account1 = tiger_account_factory.create(
            account_number="ACC1", is_default_trading=True
        )
        db_session.add(account1)
        await db_session.flush()

        # Try to create second default trading account
        account2 = tiger_account_factory.create(
            account_number="ACC2", is_default_trading=True
        )
        db_session.add(account2)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_tiger_account_enum_values(self, db_session, tiger_account_factory):
        """Test ENUM field validations."""
        account = tiger_account_factory.create(
            account_type=AccountType.PAPER, status=AccountStatus.INACTIVE
        )
        db_session.add(account)
        await db_session.flush()

        assert account.account_type == AccountType.PAPER
        assert account.status == AccountStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_tiger_account_jsonb_fields(self, db_session, tiger_account_factory):
        """Test JSONB field functionality."""
        permissions = {
            "permissions": [
                MarketPermission.US_STOCK.value,
                MarketPermission.HK_STOCK.value,
                MarketPermission.US_OPTION.value,
            ]
        }
        tags = {"environment": "production", "region": "US", "risk_level": "medium"}

        account = tiger_account_factory.create(
            market_permissions=permissions, tags=tags
        )
        db_session.add(account)
        await db_session.flush()

        # Refetch from database
        result = await db_session.execute(
            select(TigerAccount).where(TigerAccount.id == account.id)
        )
        saved_account = result.scalar_one()

        assert saved_account.market_permissions == permissions
        assert saved_account.tags == tags

    @pytest.mark.asyncio
    async def test_tiger_account_check_constraints(
        self, db_session, tiger_account_factory
    ):
        """Test check constraints."""
        # Test negative API calls constraint
        account = tiger_account_factory.create(daily_api_calls=-1)
        db_session.add(account)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    def test_tiger_account_properties(self, tiger_account_factory):
        """Test model properties."""
        # Test active account
        account = tiger_account_factory.create(status=AccountStatus.ACTIVE)
        assert account.is_active is True

        # Test inactive account
        account.status = AccountStatus.INACTIVE
        assert account.is_active is False

        # Test production environment
        account.environment = "production"
        assert account.is_production is True

        # Test sandbox environment
        account.environment = "sandbox"
        assert account.is_production is False

    def test_token_validity_methods(self, tiger_account_factory):
        """Test token validity checking methods."""
        now = datetime.now(timezone.utc)

        # Test valid token
        account = tiger_account_factory.create(
            access_token="valid_token", token_expires_at=now + timedelta(hours=2)
        )
        assert account.has_valid_token is True
        assert account.needs_token_refresh is False

        # Test expired token
        account.token_expires_at = now - timedelta(hours=1)
        assert account.has_valid_token is False
        assert account.needs_token_refresh is True

        # Test token expiring soon
        account.token_expires_at = now + timedelta(minutes=30)
        assert account.has_valid_token is True
        assert account.needs_token_refresh is True

    def test_market_permission_methods(self, tiger_account_factory):
        """Test market permission management methods."""
        permissions = {"permissions": [MarketPermission.US_STOCK.value]}
        account = tiger_account_factory.create(market_permissions=permissions)

        # Test has permission
        assert account.has_market_permission(MarketPermission.US_STOCK) is True
        assert account.has_market_permission(MarketPermission.HK_STOCK) is False

        # Test add permission
        account.add_market_permission(MarketPermission.HK_STOCK)
        assert (
            MarketPermission.HK_STOCK.value in account.market_permissions["permissions"]
        )

        # Test remove permission
        account.remove_market_permission(MarketPermission.US_STOCK)
        assert (
            MarketPermission.US_STOCK.value
            not in account.market_permissions["permissions"]
        )

    def test_error_tracking_methods(self, tiger_account_factory):
        """Test error tracking methods."""
        account = tiger_account_factory.create()

        # Test increment error count
        account.increment_error_count("Test error message")
        assert account.error_count == 1
        assert account.last_error == "Test error message"
        assert account.last_error_at is not None

        # Test reset error count
        account.reset_error_count()
        assert account.error_count == 0
        assert account.last_error is None
        assert account.last_error_at is None

    def test_to_dict_safe(self, tiger_account_factory):
        """Test safe dictionary conversion."""
        account = tiger_account_factory.create()
        safe_dict = account.to_dict_safe()

        # Sensitive fields should be removed
        assert "tiger_id" not in safe_dict
        assert "private_key" not in safe_dict
        assert "access_token" not in safe_dict
        assert "refresh_token" not in safe_dict

        # Non-sensitive fields should be present
        assert "account_name" in safe_dict
        assert "account_number" in safe_dict
        assert "account_type" in safe_dict

    @pytest.mark.asyncio
    async def test_tiger_account_relationships(
        self, db_session, tiger_account_factory, api_key_factory
    ):
        """Test model relationships."""
        account = tiger_account_factory.create()
        db_session.add(account)
        await db_session.flush()

        # Create related API key
        api_key = api_key_factory.create(tiger_account_id=account.id)
        db_session.add(api_key)
        await db_session.flush()

        # Test relationship loading
        result = await db_session.execute(
            select(TigerAccount).where(TigerAccount.id == account.id)
        )
        loaded_account = result.scalar_one()

        # API keys should be loaded due to selectin loading
        assert len(loaded_account.api_keys) == 1
        assert loaded_account.api_keys[0].id == api_key.id


class TestAPIKeyModel:
    """Test cases for APIKey model."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, db_session, api_key_factory):
        """Test creating an APIKey instance."""
        api_key = api_key_factory.create()
        db_session.add(api_key)
        await db_session.flush()

        assert api_key.id is not None
        assert isinstance(api_key.id, uuid.UUID)
        assert api_key.created_at is not None
        assert api_key.updated_at is not None
        assert api_key.name == "Test API Key"
        assert api_key.status == APIKeyStatus.ACTIVE
        assert len(api_key.scopes) > 0

    @pytest.mark.asyncio
    async def test_api_key_unique_hash(self, db_session, api_key_factory):
        """Test that key_hash must be unique."""
        key_hash = "duplicate_hash_123"

        # Create first API key
        api_key1 = api_key_factory.create(key_hash=key_hash)
        db_session.add(api_key1)
        await db_session.flush()

        # Try to create second API key with same hash
        api_key2 = api_key_factory.create(key_hash=key_hash)
        db_session.add(api_key2)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_api_key_foreign_key_constraint(self, db_session, api_key_factory):
        """Test foreign key constraint for tiger_account_id."""
        # Try to create API key with non-existent account ID
        api_key = api_key_factory.create(tiger_account_id=uuid.uuid4())
        db_session.add(api_key)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_api_key_array_fields(self, db_session, api_key_factory):
        """Test array field functionality."""
        scopes = [
            APIKeyScope.MCP_READ.value,
            APIKeyScope.MCP_WRITE.value,
            APIKeyScope.TRADE_READ.value,
        ]
        allowed_ips = ["192.168.1.100", "10.0.0.50"]
        allowed_user_agents = ["TigerMCP/1.0", "TestClient/2.0"]

        api_key = api_key_factory.create(
            scopes=scopes,
            allowed_ips=allowed_ips,
            allowed_user_agents=allowed_user_agents,
        )
        db_session.add(api_key)
        await db_session.flush()

        # Refetch from database
        result = await db_session.execute(select(APIKey).where(APIKey.id == api_key.id))
        saved_key = result.scalar_one()

        assert saved_key.scopes == scopes
        assert saved_key.allowed_ips == allowed_ips
        assert saved_key.allowed_user_agents == allowed_user_agents

    def test_api_key_properties(self, api_key_factory):
        """Test API key properties."""
        now = datetime.now(timezone.utc)

        # Test active key
        api_key = api_key_factory.create(
            status=APIKeyStatus.ACTIVE, expires_at=now + timedelta(days=30)
        )
        assert api_key.is_active is True
        assert api_key.is_expired is False
        assert api_key.expires_in_days == 29  # Should be 29 days

        # Test expired key
        api_key.expires_at = now - timedelta(days=1)
        assert api_key.is_active is False
        assert api_key.is_expired is True

        # Test revoked key
        api_key.status = APIKeyStatus.REVOKED
        api_key.expires_at = now + timedelta(days=30)
        assert api_key.is_active is False

    def test_scope_management_methods(self, api_key_factory):
        """Test scope management methods."""
        api_key = api_key_factory.create(scopes=[APIKeyScope.MCP_READ.value])

        # Test has_scope
        assert api_key.has_scope(APIKeyScope.MCP_READ) is True
        assert api_key.has_scope(APIKeyScope.MCP_WRITE) is False

        # Test add_scope
        api_key.add_scope(APIKeyScope.MCP_WRITE)
        assert APIKeyScope.MCP_WRITE.value in api_key.scopes

        # Test remove_scope
        api_key.remove_scope(APIKeyScope.MCP_READ)
        assert APIKeyScope.MCP_READ.value not in api_key.scopes

        # Test has_any_scope
        api_key.scopes = [APIKeyScope.MCP_READ.value, APIKeyScope.TRADE_READ.value]
        assert (
            api_key.has_any_scope([APIKeyScope.MCP_WRITE, APIKeyScope.TRADE_READ])
            is True
        )
        assert (
            api_key.has_any_scope(
                [APIKeyScope.DASHBOARD_READ, APIKeyScope.SYSTEM_ADMIN]
            )
            is False
        )

        # Test has_all_scopes
        assert (
            api_key.has_all_scopes([APIKeyScope.MCP_READ, APIKeyScope.TRADE_READ])
            is True
        )
        assert (
            api_key.has_all_scopes([APIKeyScope.MCP_READ, APIKeyScope.MCP_WRITE])
            is False
        )

    def test_access_control_methods(self, api_key_factory):
        """Test access control methods."""
        api_key = api_key_factory.create(
            allowed_ips=["192.168.1.100", "10.0.0.50"],
            allowed_user_agents=["TigerMCP/1.0"],
        )

        # Test IP restrictions
        assert api_key.is_ip_allowed("192.168.1.100") is True
        assert api_key.is_ip_allowed("192.168.1.200") is False

        # Test user agent restrictions
        assert api_key.is_user_agent_allowed("TigerMCP/1.0 (Linux)") is True
        assert api_key.is_user_agent_allowed("BadClient/1.0") is False

        # Test no restrictions (empty arrays)
        api_key.allowed_ips = []
        api_key.allowed_user_agents = []
        assert api_key.is_ip_allowed("any.ip.address") is True
        assert api_key.is_user_agent_allowed("any user agent") is True

    def test_account_access_method(self, api_key_factory):
        """Test account access control."""
        account_id = uuid.uuid4()

        # Key bound to specific account
        bound_key = api_key_factory.create(tiger_account_id=account_id)
        assert bound_key.can_access_account(account_id) is True
        assert bound_key.can_access_account(uuid.uuid4()) is False

        # Unbound key (can access any account)
        unbound_key = api_key_factory.create(tiger_account_id=None)
        assert unbound_key.can_access_account(account_id) is True
        assert unbound_key.can_access_account(uuid.uuid4()) is True

    def test_usage_tracking(self, api_key_factory):
        """Test usage tracking functionality."""
        api_key = api_key_factory.create()
        initial_count = api_key.usage_count
        initial_time = api_key.last_used_at

        api_key.record_usage("192.168.1.100")

        assert api_key.usage_count == initial_count + 1
        assert api_key.last_used_at != initial_time

    def test_key_revocation(self, api_key_factory):
        """Test API key revocation."""
        api_key = api_key_factory.create()

        api_key.revoke("Security breach")

        assert api_key.status == APIKeyStatus.REVOKED
        assert api_key.tags["revocation_reason"] == "Security breach"
        assert "revoked_at" in api_key.tags

    def test_expiration_extension(self, api_key_factory):
        """Test expiration extension."""
        now = datetime.now(timezone.utc)
        api_key = api_key_factory.create(expires_at=now + timedelta(days=10))

        original_expiry = api_key.expires_at
        api_key.extend_expiration(30)

        expected_expiry = original_expiry + timedelta(days=30)
        assert abs((api_key.expires_at - expected_expiry).total_seconds()) < 1

    def test_class_methods(self, api_key_factory):
        """Test class methods for scope groups."""
        trading_scopes = APIKey.get_trading_scopes()
        dashboard_scopes = APIKey.get_dashboard_scopes()
        mcp_scopes = APIKey.get_mcp_scopes()

        assert APIKeyScope.TRADE_READ in trading_scopes
        assert APIKeyScope.DASHBOARD_READ in dashboard_scopes
        assert APIKeyScope.MCP_READ in mcp_scopes


class TestAuditLogModel:
    """Test cases for AuditLog model."""

    @pytest.mark.asyncio
    async def test_create_audit_log(self, db_session, audit_log_factory):
        """Test creating an AuditLog instance."""
        audit_log = audit_log_factory.create()
        db_session.add(audit_log)
        await db_session.flush()

        assert audit_log.id is not None
        assert isinstance(audit_log.id, uuid.UUID)
        assert audit_log.created_at is not None
        assert audit_log.updated_at is not None
        assert audit_log.action == AuditAction.ACCOUNT_CREATE
        assert audit_log.result == AuditResult.SUCCESS
        assert audit_log.severity == AuditSeverity.LOW

    @pytest.mark.asyncio
    async def test_audit_log_enum_values(self, db_session, audit_log_factory):
        """Test ENUM field validations."""
        audit_log = audit_log_factory.create(
            action=AuditAction.SECURITY_BREACH_DETECTED,
            result=AuditResult.FAILURE,
            severity=AuditSeverity.CRITICAL,
        )
        db_session.add(audit_log)
        await db_session.flush()

        assert audit_log.action == AuditAction.SECURITY_BREACH_DETECTED
        assert audit_log.result == AuditResult.FAILURE
        assert audit_log.severity == AuditSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_audit_log_jsonb_details(self, db_session, audit_log_factory):
        """Test JSONB details field."""
        details = {
            "request_id": "req_12345",
            "method": "POST",
            "endpoint": "/api/accounts",
            "response_time": 0.123,
            "error_code": None,
        }

        audit_log = audit_log_factory.create(details=details)
        db_session.add(audit_log)
        await db_session.flush()

        # Refetch from database
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.id == audit_log.id)
        )
        saved_log = result.scalar_one()

        assert saved_log.details == details

    @pytest.mark.asyncio
    async def test_audit_log_foreign_keys(
        self, db_session, sample_tiger_account, sample_api_key, audit_log_factory
    ):
        """Test foreign key relationships."""
        audit_log = audit_log_factory.create(
            tiger_account_id=sample_tiger_account.id, api_key_id=sample_api_key.id
        )
        db_session.add(audit_log)
        await db_session.flush()

        # Test relationship loading
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.id == audit_log.id)
        )
        loaded_log = result.scalar_one()

        # Relationships should be accessible
        assert loaded_log.tiger_account_id == sample_tiger_account.id
        assert loaded_log.api_key_id == sample_api_key.id


class TestTokenStatusModel:
    """Test cases for TokenStatus model."""

    @pytest.mark.asyncio
    async def test_create_token_status(self, db_session, token_status_factory):
        """Test creating a TokenStatus instance."""
        token_status = token_status_factory.create()
        db_session.add(token_status)
        await db_session.flush()

        assert token_status.id is not None
        assert isinstance(token_status.id, uuid.UUID)
        assert token_status.created_at is not None
        assert token_status.updated_at is not None
        assert token_status.status == TokenRefreshStatus.PENDING
        assert token_status.trigger == RefreshTrigger.MANUAL

    @pytest.mark.asyncio
    async def test_token_status_enum_values(self, db_session, token_status_factory):
        """Test ENUM field validations."""
        token_status = token_status_factory.create(
            status=TokenRefreshStatus.SUCCESS, trigger=RefreshTrigger.AUTOMATIC
        )
        db_session.add(token_status)
        await db_session.flush()

        assert token_status.status == TokenRefreshStatus.SUCCESS
        assert token_status.trigger == RefreshTrigger.AUTOMATIC

    @pytest.mark.asyncio
    async def test_token_status_foreign_key(
        self, db_session, sample_tiger_account, token_status_factory
    ):
        """Test foreign key relationship."""
        token_status = token_status_factory.create(
            tiger_account_id=sample_tiger_account.id
        )
        db_session.add(token_status)
        await db_session.flush()

        assert token_status.tiger_account_id == sample_tiger_account.id

    @pytest.mark.asyncio
    async def test_token_status_check_constraints(
        self, db_session, token_status_factory
    ):
        """Test check constraints."""
        # Test positive attempt count constraint
        token_status = token_status_factory.create(attempt_count=-1)
        db_session.add(token_status)

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestModelTimestamps:
    """Test timestamp functionality across all models."""

    @pytest.mark.asyncio
    async def test_automatic_timestamp_creation(
        self, db_session, tiger_account_factory
    ):
        """Test that timestamps are set automatically on creation."""
        account = tiger_account_factory.create()
        creation_time = datetime.now(timezone.utc)

        db_session.add(account)
        await db_session.flush()

        assert account.created_at is not None
        assert account.updated_at is not None
        assert abs((account.created_at - creation_time).total_seconds()) < 1
        assert abs((account.updated_at - creation_time).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_automatic_timestamp_update(self, db_session, sample_tiger_account):
        """Test that updated_at is updated automatically on modification."""
        original_updated_at = sample_tiger_account.updated_at

        # Wait a moment to ensure timestamp difference
        import asyncio

        await asyncio.sleep(0.01)

        # Update the account
        sample_tiger_account.account_name = "Updated Name"
        await db_session.flush()

        assert sample_tiger_account.updated_at > original_updated_at


class TestModelValidation:
    """Test model validation and constraints."""

    @pytest.mark.asyncio
    async def test_required_fields_validation(self, db_session):
        """Test that required fields cannot be null."""
        # Test TigerAccount required fields
        with pytest.raises((IntegrityError, ValueError)):
            account = TigerAccount(
                # Missing required fields
                account_type=AccountType.STANDARD,
                status=AccountStatus.ACTIVE,
            )
            db_session.add(account)
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_field_length_constraints(self, db_session, tiger_account_factory):
        """Test field length constraints."""
        # Test account_name length constraint (should be <= 100)
        long_name = "x" * 101
        account = tiger_account_factory.create(account_name=long_name)
        db_session.add(account)

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestModelSerialization:
    """Test model serialization methods."""

    def test_to_dict_method(self, tiger_account_factory):
        """Test to_dict method."""
        account = tiger_account_factory.create()
        account_dict = account.to_dict()

        assert isinstance(account_dict, dict)
        assert "account_name" in account_dict
        assert "account_number" in account_dict
        assert "account_type" in account_dict
        assert account_dict["account_name"] == account.account_name

    def test_repr_method(self, tiger_account_factory):
        """Test __repr__ method."""
        account = tiger_account_factory.create()
        repr_str = repr(account)

        assert "TigerAccount" in repr_str
        assert account.account_name in repr_str or "..." in repr_str

    def test_str_method(self, tiger_account_factory):
        """Test __str__ method."""
        account = tiger_account_factory.create()
        str_repr = str(account)

        assert "TigerAccount" in str_repr
        assert account.account_name in str_repr
        assert account.account_number in str_repr


class TestModelCascading:
    """Test cascading delete and update behavior."""

    @pytest.mark.asyncio
    async def test_cascade_delete_api_keys(
        self, db_session, sample_tiger_account, api_key_factory
    ):
        """Test that deleting an account cascades to API keys."""
        # Create API key linked to account
        api_key = api_key_factory.create(tiger_account_id=sample_tiger_account.id)
        db_session.add(api_key)
        await db_session.flush()

        api_key_id = api_key.id

        # Delete the account
        await db_session.delete(sample_tiger_account)
        await db_session.flush()

        # API key should be deleted too
        result = await db_session.execute(select(APIKey).where(APIKey.id == api_key_id))
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_cascade_delete_audit_logs(
        self, db_session, sample_tiger_account, audit_log_factory
    ):
        """Test that deleting an account cascades to audit logs."""
        # Create audit log linked to account
        audit_log = audit_log_factory.create(tiger_account_id=sample_tiger_account.id)
        db_session.add(audit_log)
        await db_session.flush()

        audit_log_id = audit_log.id

        # Delete the account
        await db_session.delete(sample_tiger_account)
        await db_session.flush()

        # Audit log should be deleted too
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.id == audit_log_id)
        )
        assert result.scalar_one_or_none() is None
