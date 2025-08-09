"""
Pytest configuration and shared fixtures for shared package tests.
"""

import os
import tempfile
from typing import Dict, Generator
from unittest.mock import MagicMock

import pytest
from shared.config import AppConfig, DatabaseConfig, SecurityConfig, TigerAPIConfig
from shared.encryption import EncryptedData, EncryptionService
from shared.security import SecurityService


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["ENCRYPTION_MASTER_KEY"] = (
        "dGVzdF9tYXN0ZXJfa2V5XzEyMzQ1Njc4OTAxMjM0NTY="  # 32 bytes base64
    )
    os.environ["JWT_SECRET"] = "test_jwt_secret_for_unit_tests"
    os.environ["DATABASE_URL"] = "sqlite:///test.db"

    yield

    # Cleanup test environment variables
    test_vars = [
        "ENVIRONMENT",
        "LOG_LEVEL",
        "ENCRYPTION_MASTER_KEY",
        "JWT_SECRET",
        "DATABASE_URL",
    ]
    for var in test_vars:
        os.environ.pop(var, None)


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create and cleanup temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def security_config() -> SecurityConfig:
    """Create test security configuration."""
    return SecurityConfig(
        environment="test",
        jwt_expiry_minutes=15,
        refresh_token_expiry_days=7,
        pbkdf2_iterations=10000,  # Reduced for faster tests
        rate_limit_requests=100,
        rate_limit_window_seconds=60,
        password_min_length=8,
        api_key_length=32,
    )


@pytest.fixture
def database_config() -> DatabaseConfig:
    """Create test database configuration."""
    return DatabaseConfig(
        url="sqlite:///test.db",
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False,
    )


@pytest.fixture
def app_config() -> AppConfig:
    """Create test app configuration."""
    return AppConfig(
        name="tiger-mcp-test",
        version="0.1.0-test",
        environment="test",
        debug=True,
        host="127.0.0.1",
        port=8000,
    )


@pytest.fixture
def tiger_api_config() -> TigerAPIConfig:
    """Create test Tiger API configuration."""
    return TigerAPIConfig(
        base_url="https://openapi-sandbox.itiger.com",
        timeout=30,
        max_retries=3,
        rate_limit_requests=100,
        rate_limit_window=60,
    )


@pytest.fixture
def encryption_service(security_config: SecurityConfig) -> EncryptionService:
    """Create test encryption service."""
    return EncryptionService(config=security_config)


@pytest.fixture
def security_service(security_config: SecurityConfig) -> SecurityService:
    """Create test security service."""
    return SecurityService(config=security_config)


@pytest.fixture
def sample_encrypted_data() -> EncryptedData:
    """Create sample encrypted data for testing."""
    return EncryptedData(
        ciphertext="dGVzdF9jaXBoZXJ0ZXh0",  # base64: test_ciphertext
        nonce="dGVzdF9ub25jZQ==",  # base64: test_nonce
        tag="dGVzdF90YWc=",  # base64: test_tag
        salt="dGVzdF9zYWx0",  # base64: test_salt
        key_version=1,
        algorithm="AES-256-GCM",
    )


@pytest.fixture
def sample_tiger_credentials() -> Dict[str, str]:
    """Sample Tiger API credentials for testing."""
    return {
        "tiger_id": "test_tiger_id_123456",
        "private_key": "test_private_key_abcdef123456",
        "access_token": "test_access_token_xyz789",
        "refresh_token": "test_refresh_token_abc123",
    }


@pytest.fixture
def mock_database():
    """Mock database connection and operations."""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.session.return_value = mock_session

    # Mock common database operations
    mock_session.query.return_value = mock_session
    mock_session.filter.return_value = mock_session
    mock_session.filter_by.return_value = mock_session
    mock_session.first.return_value = None
    mock_session.all.return_value = []
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.delete.return_value = None

    return mock_db


@pytest.fixture
def mock_tiger_api():
    """Mock Tiger API client for testing."""
    mock_api = MagicMock()

    # Mock successful authentication response
    mock_api.authenticate.return_value = {
        "access_token": "new_access_token_123",
        "refresh_token": "new_refresh_token_456",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    # Mock successful refresh response
    mock_api.refresh_token.return_value = {
        "access_token": "refreshed_access_token_789",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    # Mock account info response
    mock_api.get_account_info.return_value = {
        "account_id": "test_account_123",
        "account_name": "Test Account",
        "status": "active",
        "permissions": ["read", "trade"],
    }

    return mock_api


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for testing."""
    mock_limiter = MagicMock()
    mock_limiter.is_allowed.return_value = True
    mock_limiter.get_current_usage.return_value = 0
    mock_limiter.get_reset_time.return_value = 60
    return mock_limiter


@pytest.fixture
def sample_jwt_payload() -> Dict:
    """Sample JWT payload for testing."""
    return {
        "sub": "test_user_123",
        "iat": 1640995200,  # 2022-01-01 00:00:00 UTC
        "exp": 1640998800,  # 2022-01-01 01:00:00 UTC
        "iss": "tiger-mcp",
        "aud": "tiger-mcp",
        "jti": "test_jti_123",
        "scopes": ["read", "write"],
        "account_id": "test_account_456",
        "api_key_id": "test_api_key_789",
    }


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_time(monkeypatch):
    """Mock time.time() to return consistent values."""
    mock_time_value = 1640995200.0  # 2022-01-01 00:00:00 UTC

    def mock_time_func():
        return mock_time_value

    monkeypatch.setattr("time.time", mock_time_func)
    return mock_time_value


@pytest.fixture
def mock_secrets(monkeypatch):
    """Mock secrets module for predictable testing."""

    def mock_token_bytes(length):
        return b"test_random_bytes"[:length].ljust(length, b"\x00")

    def mock_token_urlsafe(length):
        return "test_random_string"[:length].ljust(length, "x")

    monkeypatch.setattr("secrets.token_bytes", mock_token_bytes)
    monkeypatch.setattr("secrets.token_urlsafe", mock_token_urlsafe)


# Test data constants
TEST_CONSTANTS = {
    "VALID_TIGER_ID": "test_tiger_123456",
    "VALID_PRIVATE_KEY": "test_private_key_abcdef",
    "VALID_ACCESS_TOKEN": "test_access_token_xyz789",
    "VALID_REFRESH_TOKEN": "test_refresh_token_abc123",
    "VALID_API_KEY": "test_api_key_secure_random_string",
    "VALID_PASSWORD": "SecureTestPassword123!",
    "WEAK_PASSWORD": "123",
    "INVALID_EMAIL": "invalid.email.format",
    "VALID_EMAIL": "test@example.com",
    "TEST_SALT": b"test_salt_16bytes",
    "TEST_NONCE": b"test_nonce12",  # 12 bytes for GCM
    "TEST_TAG": b"test_tag_16byte",
    "TEST_CIPHERTEXT": b"encrypted_test_data",
}


class MockAccount:
    """Mock account object for testing."""

    def __init__(self, account_id: str = "test_account_123"):
        self.id = account_id
        self.tiger_id = f"tiger_{account_id}"
        self.name = f"Test Account {account_id}"
        self.is_active = True
        self.is_default = False
        self.encrypted_private_key = "encrypted_private_key_data"
        self.encrypted_access_token = "encrypted_access_token_data"
        self.encrypted_refresh_token = "encrypted_refresh_token_data"
        self.token_expires_at = None
        self.last_used_at = None
        self.created_at = "2022-01-01T00:00:00Z"
        self.updated_at = "2022-01-01T00:00:00Z"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tiger_id": self.tiger_id,
            "name": self.name,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@pytest.fixture
def mock_account():
    """Create mock account for testing."""
    return MockAccount()


@pytest.fixture
def multiple_mock_accounts():
    """Create multiple mock accounts for testing."""
    return [
        MockAccount("account_1"),
        MockAccount("account_2"),
        MockAccount("account_3"),
    ]
