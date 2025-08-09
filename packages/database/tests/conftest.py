"""
Pytest configuration and shared fixtures for database package tests.
"""

import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from database.base import Base
from database.config import DatabaseConfig
from database.models import APIKey, AuditLog, TigerAccount, TokenStatus
from database.models.accounts import AccountStatus, AccountType, MarketPermission
from database.models.api_keys import APIKeyScope, APIKeyStatus
from database.models.audit_logs import AuditAction, AuditResult, AuditSeverity
from database.models.token_status import RefreshTrigger, TokenRefreshStatus
from database.utils import (
    APIKeyUtils,
    AuditLogUtils,
    DatabaseUtils,
    TigerAccountUtils,
    TokenStatusUtils,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

# Test configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///test.db"
TEST_SYNC_DATABASE_URL = "sqlite:///test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Set test environment variables
    original_values = {}
    test_env_vars = {
        "ENVIRONMENT": "test",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test_tiger_mcp",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "DB_DEBUG": "true",
    }

    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment variables
    for key, value in original_values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest_asyncio.fixture
async def temp_db_file():
    """Create temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def test_db_config():
    """Create test database configuration."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        name="test_tiger_mcp",
        user="test_user",
        password="test_password",
        environment="test",
        debug=True,
        pool_size=1,
        max_overflow=0,
        pool_timeout=5,
        pool_recycle=300,
    )


@pytest_asyncio.fixture
async def test_engine(temp_db_file) -> AsyncEngine:
    """Create test async engine."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{temp_db_file}", echo=False, future=True
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with transaction rollback."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )

    async with session_factory() as session:
        # Start a transaction
        trans = await session.begin()

        yield session

        # Always rollback to keep tests isolated
        await trans.rollback()


@pytest_asyncio.fixture
async def db_utils(db_session: AsyncSession) -> DatabaseUtils:
    """Create database utils instance."""
    return DatabaseUtils(db_session)


@pytest_asyncio.fixture
async def account_utils(db_session: AsyncSession) -> TigerAccountUtils:
    """Create Tiger account utils instance."""
    return TigerAccountUtils(db_session)


@pytest_asyncio.fixture
async def api_key_utils(db_session: AsyncSession) -> APIKeyUtils:
    """Create API key utils instance."""
    return APIKeyUtils(db_session)


@pytest_asyncio.fixture
async def audit_log_utils(db_session: AsyncSession) -> AuditLogUtils:
    """Create audit log utils instance."""
    return AuditLogUtils(db_session)


@pytest_asyncio.fixture
async def token_status_utils(db_session: AsyncSession) -> TokenStatusUtils:
    """Create token status utils instance."""
    return TokenStatusUtils(db_session)


# Test data factories
class TigerAccountFactory:
    """Factory for creating test TigerAccount instances."""

    @staticmethod
    def create(
        account_name: str = "Test Account",
        account_number: str = None,
        account_type: AccountType = AccountType.STANDARD,
        status: AccountStatus = AccountStatus.ACTIVE,
        tiger_id: str = "test_tiger_id_123",
        private_key: str = "test_private_key_data",
        access_token: str = "test_access_token_data",
        refresh_token: str = "test_refresh_token_data",
        is_default_trading: bool = False,
        is_default_data: bool = False,
        environment: str = "sandbox",
        market_permissions: Dict = None,
        **kwargs,
    ) -> TigerAccount:
        """Create a TigerAccount instance with test data."""
        if account_number is None:
            account_number = f"ACC{uuid.uuid4().hex[:8].upper()}"

        if market_permissions is None:
            market_permissions = {
                "permissions": [
                    MarketPermission.US_STOCK.value,
                    MarketPermission.HK_STOCK.value,
                ]
            }

        return TigerAccount(
            account_name=account_name,
            account_number=account_number,
            account_type=account_type,
            status=status,
            tiger_id=tiger_id,
            private_key=private_key,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_default_trading=is_default_trading,
            is_default_data=is_default_data,
            market_permissions=market_permissions,
            environment=environment,
            **kwargs,
        )

    @staticmethod
    def create_batch(
        count: int = 3, base_name: str = "Test Account"
    ) -> List[TigerAccount]:
        """Create multiple TigerAccount instances."""
        accounts = []
        for i in range(count):
            accounts.append(
                TigerAccountFactory.create(
                    account_name=f"{base_name} {i + 1}",
                    account_number=f"ACC{uuid.uuid4().hex[:8].upper()}",
                    tiger_id=f"test_tiger_id_{i + 1}",
                )
            )
        return accounts


class APIKeyFactory:
    """Factory for creating test APIKey instances."""

    @staticmethod
    def create(
        name: str = "Test API Key",
        key_hash: str = "test_key_hash_123",
        key_prefix: str = "tmcp_123",
        status: APIKeyStatus = APIKeyStatus.ACTIVE,
        scopes: List[str] = None,
        tiger_account_id: uuid.UUID = None,
        expires_at: datetime = None,
        **kwargs,
    ) -> APIKey:
        """Create an APIKey instance with test data."""
        if scopes is None:
            scopes = [APIKeyScope.MCP_READ.value, APIKeyScope.MCP_WRITE.value]

        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        return APIKey(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            status=status,
            scopes=scopes,
            tiger_account_id=tiger_account_id,
            expires_at=expires_at,
            **kwargs,
        )

    @staticmethod
    def create_batch(count: int = 3, base_name: str = "Test API Key") -> List[APIKey]:
        """Create multiple APIKey instances."""
        keys = []
        for i in range(count):
            keys.append(
                APIKeyFactory.create(
                    name=f"{base_name} {i + 1}",
                    key_hash=f"test_key_hash_{i + 1}",
                    key_prefix=f"tmcp_{i + 1:03d}",
                )
            )
        return keys


class AuditLogFactory:
    """Factory for creating test AuditLog instances."""

    @staticmethod
    def create(
        action: AuditAction = AuditAction.ACCOUNT_CREATE,
        result: AuditResult = AuditResult.SUCCESS,
        severity: AuditSeverity = AuditSeverity.LOW,
        tiger_account_id: uuid.UUID = None,
        api_key_id: uuid.UUID = None,
        user_id: str = "test_user",
        ip_address: str = "127.0.0.1",
        details: Dict = None,
        **kwargs,
    ) -> AuditLog:
        """Create an AuditLog instance with test data."""
        if details is None:
            details = {"test_data": "test_value"}

        return AuditLog(
            action=action,
            result=result,
            severity=severity,
            tiger_account_id=tiger_account_id,
            api_key_id=api_key_id,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            **kwargs,
        )

    @staticmethod
    def create_batch(
        count: int = 3, actions: List[AuditAction] = None
    ) -> List[AuditLog]:
        """Create multiple AuditLog instances."""
        if actions is None:
            actions = [
                AuditAction.ACCOUNT_CREATE,
                AuditAction.API_KEY_CREATE,
                AuditAction.TOKEN_REFRESH,
            ]

        logs = []
        for i in range(count):
            action = actions[i % len(actions)]
            logs.append(
                AuditLogFactory.create(
                    action=action,
                    user_id=f"test_user_{i + 1}",
                    ip_address=f"127.0.0.{i + 1}",
                    details={"action_index": i},
                )
            )
        return logs


class TokenStatusFactory:
    """Factory for creating test TokenStatus instances."""

    @staticmethod
    def create(
        tiger_account_id: uuid.UUID = None,
        status: TokenRefreshStatus = TokenRefreshStatus.PENDING,
        trigger: RefreshTrigger = RefreshTrigger.MANUAL,
        old_token_expires_at: datetime = None,
        old_token_hash: str = "old_token_hash",
        new_token_expires_at: datetime = None,
        new_token_hash: str = "new_token_hash",
        **kwargs,
    ) -> TokenStatus:
        """Create a TokenStatus instance with test data."""
        if old_token_expires_at is None:
            old_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        if new_token_expires_at is None and status == TokenRefreshStatus.SUCCESS:
            new_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        return TokenStatus(
            tiger_account_id=tiger_account_id or uuid.uuid4(),
            status=status,
            trigger=trigger,
            old_token_expires_at=old_token_expires_at,
            old_token_hash=old_token_hash,
            new_token_expires_at=new_token_expires_at,
            new_token_hash=(
                new_token_hash if status == TokenRefreshStatus.SUCCESS else None
            ),
            **kwargs,
        )

    @staticmethod
    def create_batch(
        count: int = 3, tiger_account_id: uuid.UUID = None
    ) -> List[TokenStatus]:
        """Create multiple TokenStatus instances."""
        if tiger_account_id is None:
            tiger_account_id = uuid.uuid4()

        statuses = []
        status_values = [
            TokenRefreshStatus.PENDING,
            TokenRefreshStatus.SUCCESS,
            TokenRefreshStatus.FAILED,
        ]

        for i in range(count):
            status = status_values[i % len(status_values)]
            statuses.append(
                TokenStatusFactory.create(
                    tiger_account_id=tiger_account_id,
                    status=status,
                    old_token_hash=f"old_token_hash_{i + 1}",
                    new_token_hash=(
                        f"new_token_hash_{i + 1}"
                        if status == TokenRefreshStatus.SUCCESS
                        else None
                    ),
                )
            )
        return statuses


# Fixtures using factories
@pytest.fixture
def tiger_account_factory():
    """Provide TigerAccountFactory."""
    return TigerAccountFactory


@pytest.fixture
def api_key_factory():
    """Provide APIKeyFactory."""
    return APIKeyFactory


@pytest.fixture
def audit_log_factory():
    """Provide AuditLogFactory."""
    return AuditLogFactory


@pytest.fixture
def token_status_factory():
    """Provide TokenStatusFactory."""
    return TokenStatusFactory


@pytest_asyncio.fixture
async def sample_tiger_account(db_session: AsyncSession) -> TigerAccount:
    """Create and persist a sample TigerAccount."""
    account = TigerAccountFactory.create()
    db_session.add(account)
    await db_session.flush()
    return account


@pytest_asyncio.fixture
async def sample_api_key(
    db_session: AsyncSession, sample_tiger_account: TigerAccount
) -> APIKey:
    """Create and persist a sample APIKey."""
    api_key = APIKeyFactory.create(tiger_account_id=sample_tiger_account.id)
    db_session.add(api_key)
    await db_session.flush()
    return api_key


@pytest_asyncio.fixture
async def sample_audit_log(
    db_session: AsyncSession, sample_tiger_account: TigerAccount, sample_api_key: APIKey
) -> AuditLog:
    """Create and persist a sample AuditLog."""
    audit_log = AuditLogFactory.create(
        tiger_account_id=sample_tiger_account.id, api_key_id=sample_api_key.id
    )
    db_session.add(audit_log)
    await db_session.flush()
    return audit_log


@pytest_asyncio.fixture
async def sample_token_status(
    db_session: AsyncSession, sample_tiger_account: TigerAccount
) -> TokenStatus:
    """Create and persist a sample TokenStatus."""
    token_status = TokenStatusFactory.create(tiger_account_id=sample_tiger_account.id)
    db_session.add(token_status)
    await db_session.flush()
    return token_status


# Mock fixtures
@pytest.fixture
def mock_encryption_service():
    """Mock encryption service."""
    mock_service = MagicMock()
    mock_service.encrypt.return_value = "encrypted_data"
    mock_service.decrypt.return_value = "decrypted_data"
    return mock_service


@pytest.fixture
def mock_async_session():
    """Mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.scalar_one_or_none = AsyncMock()
    session.scalars = AsyncMock()
    return session


@pytest.fixture
def mock_tiger_api_client():
    """Mock Tiger API client."""
    client = AsyncMock()
    client.authenticate.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    client.refresh_token.return_value = {
        "access_token": "refreshed_access_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    return client


# Test constants
TEST_CONSTANTS = {
    "VALID_ACCOUNT_NUMBER": "20230101000001",
    "VALID_TIGER_ID": "test_tiger_12345",
    "VALID_PRIVATE_KEY": "test_private_key_data",
    "VALID_ACCESS_TOKEN": "test_access_token_xyz789",
    "VALID_REFRESH_TOKEN": "test_refresh_token_abc123",
    "VALID_API_KEY": "tmcp_test_api_key_secure_random_string",
    "VALID_API_KEY_HASH": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
    "VALID_IP_ADDRESS": "192.168.1.100",
    "VALID_USER_AGENT": "TigerMCP/1.0.0",
    "TEST_USER_ID": "test_user_123",
}


# Pytest markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.database = pytest.mark.database
