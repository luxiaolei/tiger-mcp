"""
Integration test fixtures for Tiger MCP multi-account workflows.

Provides real database, Redis, Tiger API, and MCP server fixtures for
comprehensive integration testing with multiple accounts.
"""

import asyncio
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from typing import Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
import redis
from fastapi.testclient import TestClient
from shared.account_manager import TigerAccountManager
from shared.account_router import AccountRouter, OperationType
from shared.token_manager import get_token_manager
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import docker

# Test configuration constants
TEST_DB_NAME = "tiger_mcp_test"
TEST_REDIS_DB = 15  # Use high-numbered DB for tests
POSTGRES_TEST_PORT = 15432
REDIS_TEST_PORT = 16379


class IntegrationTestConfig:
    """Configuration for integration tests."""

    def __init__(self):
        self.postgres_url = f"postgresql://tiger_test:tiger_test@localhost:{POSTGRES_TEST_PORT}/{TEST_DB_NAME}"
        self.postgres_async_url = f"postgresql+asyncpg://tiger_test:tiger_test@localhost:{POSTGRES_TEST_PORT}/{TEST_DB_NAME}"
        self.redis_url = f"redis://localhost:{REDIS_TEST_PORT}/{TEST_REDIS_DB}"
        self.encryption_key = (
            "dGVzdF9lbmNyeXB0aW9uX2tleV8zMl9ieXRlc190ZXN0"  # 32 bytes base64
        )
        self.jwt_secret = "test_jwt_secret_integration_tests_very_secure"


@pytest.fixture(scope="session")
def integration_config():
    """Integration test configuration."""
    return IntegrationTestConfig()


@pytest.fixture(scope="session")
def docker_client():
    """Docker client for managing test containers."""
    try:
        client = docker.from_env()
        yield client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")


@pytest.fixture(scope="session")
def postgres_container(docker_client, integration_config):
    """Start PostgreSQL container for integration tests."""
    try:
        # Check if container already exists
        containers = docker_client.containers.list(
            all=True, filters={"name": "tiger-mcp-test-postgres"}
        )

        if containers:
            container = containers[0]
            if container.status != "running":
                container.start()
        else:
            # Start new PostgreSQL container
            container = docker_client.containers.run(
                "postgres:15-alpine",
                name="tiger-mcp-test-postgres",
                environment={
                    "POSTGRES_DB": TEST_DB_NAME,
                    "POSTGRES_USER": "tiger_test",
                    "POSTGRES_PASSWORD": "tiger_test",
                    "POSTGRES_INITDB_ARGS": "--auth-host=scram-sha-256",
                },
                ports={5432: POSTGRES_TEST_PORT},
                detach=True,
                remove=False,  # Keep for session reuse
            )

        # Wait for PostgreSQL to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                engine = create_engine(integration_config.postgres_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                break
            except Exception:
                if i == max_retries - 1:
                    raise
                time.sleep(1)

        yield container

        # Cleanup: Stop container but don't remove (for session reuse)
        # container.stop()

    except Exception as e:
        pytest.skip(f"Failed to start PostgreSQL container: {e}")


@pytest.fixture(scope="session")
def redis_container(docker_client, integration_config):
    """Start Redis container for integration tests."""
    try:
        # Check if container already exists
        containers = docker_client.containers.list(
            all=True, filters={"name": "tiger-mcp-test-redis"}
        )

        if containers:
            container = containers[0]
            if container.status != "running":
                container.start()
        else:
            # Start new Redis container
            container = docker_client.containers.run(
                "redis:7-alpine",
                name="tiger-mcp-test-redis",
                command="redis-server --appendonly yes",
                ports={6379: REDIS_TEST_PORT},
                detach=True,
                remove=False,  # Keep for session reuse
            )

        # Wait for Redis to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                r = redis.Redis(
                    host="localhost", port=REDIS_TEST_PORT, db=TEST_REDIS_DB
                )
                r.ping()
                break
            except Exception:
                if i == max_retries - 1:
                    raise
                time.sleep(0.5)

        yield container

        # Cleanup: Stop container but don't remove (for session reuse)
        # container.stop()

    except Exception as e:
        pytest.skip(f"Failed to start Redis container: {e}")


@pytest.fixture(scope="session")
async def test_database(postgres_container, integration_config):
    """Set up test database with schema."""
    engine = create_async_engine(
        integration_config.postgres_async_url, echo=False, poolclass=StaticPool
    )

    try:
        # Import and create all database tables
        from database.models.base import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(test_database):
    """Database session for individual tests."""
    async with AsyncSession(test_database) as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
def redis_client(redis_container, integration_config):
    """Redis client for individual tests."""
    client = redis.Redis(
        host="localhost", port=REDIS_TEST_PORT, db=TEST_REDIS_DB, decode_responses=True
    )

    # Clear test database before each test
    client.flushdb()

    yield client

    # Clean up after test
    client.flushdb()


@pytest.fixture
def process_pool():
    """Process pool executor for multiprocessing tests."""
    with ProcessPoolExecutor(max_workers=4) as executor:
        yield executor


@pytest.fixture
async def account_manager(test_database, integration_config):
    """Account manager with real database connection."""
    # Set up test environment
    os.environ["DATABASE_URL"] = integration_config.postgres_async_url
    os.environ["ENCRYPTION_MASTER_KEY"] = integration_config.encryption_key
    os.environ["ENVIRONMENT"] = "test"

    manager = TigerAccountManager()
    yield manager


@pytest.fixture
async def account_router(account_manager):
    """Account router with real dependencies."""
    router = AccountRouter()
    yield router


@pytest.fixture
async def token_manager(test_database, integration_config):
    """Token manager with real database connection."""
    manager = get_token_manager()
    yield manager


@pytest.fixture
def tiger_api_configs() -> Dict[str, Dict]:
    """Multiple Tiger API configurations for testing."""
    return {
        "account_1": {
            "tiger_id": "test_tiger_id_001",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA1234567890...\n-----END RSA PRIVATE KEY-----",
            "account_number": "DU1234567",
            "environment": "sandbox",
            "server_url": "https://openapi-sandbox.itiger.com",
        },
        "account_2": {
            "tiger_id": "test_tiger_id_002",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0987654321...\n-----END RSA PRIVATE KEY-----",
            "account_number": "DU2345678",
            "environment": "sandbox",
            "server_url": "https://openapi-sandbox.itiger.com",
        },
        "account_3": {
            "tiger_id": "test_tiger_id_003",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA1122334455...\n-----END RSA PRIVATE KEY-----",
            "account_number": "DU3456789",
            "environment": "production",
            "server_url": "https://openapi.itiger.com",
        },
    }


@pytest.fixture
async def multiple_tiger_accounts(account_manager, tiger_api_configs):
    """Create multiple Tiger accounts for testing."""
    from database.models.accounts import AccountType, MarketPermission

    accounts = {}

    # Create account 1 - Default trading account
    account_1 = await account_manager.create_account(
        account_name="Test Trading Account",
        account_number=tiger_api_configs["account_1"]["account_number"],
        tiger_id=tiger_api_configs["account_1"]["tiger_id"],
        private_key=tiger_api_configs["account_1"]["private_key"],
        account_type=AccountType.STANDARD,
        environment=tiger_api_configs["account_1"]["environment"],
        market_permissions=[MarketPermission.US_STOCK, MarketPermission.US_OPTION],
        is_default_trading=True,
        is_default_data=False,
        server_url=tiger_api_configs["account_1"]["server_url"],
    )
    accounts["trading"] = account_1

    # Create account 2 - Default data account
    account_2 = await account_manager.create_account(
        account_name="Test Data Account",
        account_number=tiger_api_configs["account_2"]["account_number"],
        tiger_id=tiger_api_configs["account_2"]["tiger_id"],
        private_key=tiger_api_configs["account_2"]["private_key"],
        account_type=AccountType.PAPER,
        environment=tiger_api_configs["account_2"]["environment"],
        market_permissions=[MarketPermission.US_STOCK, MarketPermission.HK_STOCK],
        is_default_trading=False,
        is_default_data=True,
        server_url=tiger_api_configs["account_2"]["server_url"],
    )
    accounts["data"] = account_2

    # Create account 3 - Production backup account
    account_3 = await account_manager.create_account(
        account_name="Test Production Account",
        account_number=tiger_api_configs["account_3"]["account_number"],
        tiger_id=tiger_api_configs["account_3"]["tiger_id"],
        private_key=tiger_api_configs["account_3"]["private_key"],
        account_type=AccountType.STANDARD,
        environment=tiger_api_configs["account_3"]["environment"],
        market_permissions=[MarketPermission.US_STOCK],
        is_default_trading=False,
        is_default_data=False,
        server_url=tiger_api_configs["account_3"]["server_url"],
    )
    accounts["production"] = account_3

    yield accounts


@pytest.fixture
def mock_tiger_api_responses():
    """Mock Tiger API responses for testing."""
    return {
        "auth_success": {
            "code": 0,
            "msg": "success",
            "data": {
                "access_token": "mock_access_token_12345",
                "refresh_token": "mock_refresh_token_67890",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        },
        "auth_failure": {"code": 40001, "msg": "Authentication failed", "data": None},
        "account_info": {
            "code": 0,
            "msg": "success",
            "data": {
                "account": "DU1234567",
                "currency": "USD",
                "cash": 50000.00,
                "buying_power": 100000.00,
                "net_liquidation": 75000.00,
                "equity_value": 25000.00,
                "day_pnl": 1250.50,
                "unrealized_pnl": -250.75,
            },
        },
        "market_data": {
            "code": 0,
            "msg": "success",
            "data": [
                {
                    "symbol": "AAPL",
                    "latest_price": 150.25,
                    "prev_close": 149.80,
                    "open": 150.00,
                    "high": 151.50,
                    "low": 149.75,
                    "volume": 45678900,
                    "change": 0.45,
                    "change_rate": 0.003,
                    "latest_time": 1640995200000,
                }
            ],
        },
        "order_placed": {"code": 0, "msg": "success", "data": "ORDER123456789"},
        "rate_limit_error": {"code": 42901, "msg": "Rate limit exceeded", "data": None},
    }


@pytest.fixture
def mock_tiger_client_factory(mock_tiger_api_responses):
    """Factory for creating mock Tiger API clients."""

    def create_mock_client(
        account_id: str = "test_account",
        should_fail: bool = False,
        rate_limited: bool = False,
    ):
        mock_client = MagicMock()

        if rate_limited:
            mock_client.get_account_info.return_value = AsyncMock(
                return_value=mock_tiger_api_responses["rate_limit_error"]
            )
        elif should_fail:
            mock_client.authenticate.return_value = AsyncMock(
                return_value=mock_tiger_api_responses["auth_failure"]
            )
        else:
            mock_client.authenticate.return_value = AsyncMock(
                return_value=mock_tiger_api_responses["auth_success"]
            )
            mock_client.get_account_info.return_value = AsyncMock(
                return_value=mock_tiger_api_responses["account_info"]
            )
            mock_client.get_market_data.return_value = AsyncMock(
                return_value=mock_tiger_api_responses["market_data"]
            )
            mock_client.place_order.return_value = AsyncMock(
                return_value=mock_tiger_api_responses["order_placed"]
            )

        return mock_client

    return create_mock_client


@pytest.fixture
async def mcp_server_instance(test_database, redis_client, multiple_tiger_accounts):
    """Full MCP server instance for integration testing."""
    from fastapi import FastAPI
    from mcp_server.server import TigerMCPServer

    # Create MCP server with test configuration
    app = FastAPI(title="Tiger MCP Integration Test Server")
    server = TigerMCPServer()

    # Mock Tiger client initialization for testing
    server.tiger_clients = {}
    for account_name, account in multiple_tiger_accounts.items():
        mock_client = MagicMock()
        mock_client.account_id = account.account_number
        server.tiger_clients[account.account_number] = mock_client

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": time.time()}

    yield app, server


@pytest.fixture
def mcp_test_client(mcp_server_instance):
    """Test client for MCP server."""
    app, server = mcp_server_instance
    with TestClient(app) as client:
        yield client, server


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {
        "AAPL": {
            "symbol": "AAPL",
            "latest_price": 150.25,
            "prev_close": 149.80,
            "open": 150.00,
            "high": 151.50,
            "low": 149.75,
            "volume": 45678900,
            "change": 0.45,
            "change_rate": 0.003,
            "timestamp": datetime.utcnow(),
        },
        "MSFT": {
            "symbol": "MSFT",
            "latest_price": 330.75,
            "prev_close": 329.50,
            "open": 330.00,
            "high": 332.25,
            "low": 329.00,
            "volume": 23456789,
            "change": 1.25,
            "change_rate": 0.0038,
            "timestamp": datetime.utcnow(),
        },
        "GOOGL": {
            "symbol": "GOOGL",
            "latest_price": 2750.50,
            "prev_close": 2745.25,
            "open": 2748.00,
            "high": 2755.75,
            "low": 2742.50,
            "volume": 1234567,
            "change": 5.25,
            "change_rate": 0.0019,
            "timestamp": datetime.utcnow(),
        },
    }


@pytest.fixture
def sample_trading_scenarios():
    """Sample trading scenarios for testing."""
    return {
        "buy_market_order": {
            "operation_type": OperationType.PLACE_ORDER,
            "symbol": "AAPL",
            "action": "BUY",
            "order_type": "MKT",
            "quantity": 100,
            "expected_result": "success",
        },
        "sell_limit_order": {
            "operation_type": OperationType.PLACE_ORDER,
            "symbol": "MSFT",
            "action": "SELL",
            "order_type": "LMT",
            "quantity": 50,
            "price": 335.00,
            "expected_result": "success",
        },
        "invalid_symbol_order": {
            "operation_type": OperationType.PLACE_ORDER,
            "symbol": "INVALID",
            "action": "BUY",
            "order_type": "MKT",
            "quantity": 10,
            "expected_result": "error",
        },
    }


@pytest.fixture
def error_scenarios():
    """Error scenarios for testing fault tolerance."""
    return {
        "network_timeout": {
            "error_type": "timeout",
            "error_message": "Request timeout",
            "retry_count": 3,
        },
        "authentication_failure": {
            "error_type": "auth_error",
            "error_message": "Invalid credentials",
            "retry_count": 1,
        },
        "rate_limit_exceeded": {
            "error_type": "rate_limit",
            "error_message": "Rate limit exceeded",
            "retry_count": 5,
        },
        "insufficient_funds": {
            "error_type": "trading_error",
            "error_message": "Insufficient buying power",
            "retry_count": 0,
        },
        "market_closed": {
            "error_type": "market_error",
            "error_message": "Market is closed",
            "retry_count": 0,
        },
    }


@pytest.fixture
async def performance_test_data():
    """Large dataset for performance testing."""
    symbols = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "META",
        "NVDA",
        "NFLX",
        "CRM",
        "ORCL",
        "INTC",
        "AMD",
        "QCOM",
        "BABA",
        "JD",
        "PDD",
        "NIO",
        "XPEV",
        "LI",
        "DIDI",
        "UBER",
        "LYFT",
        "ABNB",
        "COIN",
    ]

    test_data = []
    for i, symbol in enumerate(symbols):
        for j in range(10):  # 10 operations per symbol
            test_data.append(
                {
                    "operation_id": f"{symbol}_{j}",
                    "symbol": symbol,
                    "operation_type": OperationType.MARKET_DATA,
                    "priority": i % 3,  # 0=high, 1=medium, 2=low
                    "expected_duration": 0.1 + (j * 0.05),  # Simulated duration
                }
            )

    return test_data


@pytest.fixture
def load_test_config():
    """Configuration for load testing."""
    return {
        "concurrent_operations": 50,
        "total_operations": 1000,
        "operation_timeout": 5.0,
        "acceptable_error_rate": 0.02,  # 2%
        "target_avg_response_time": 0.5,  # 500ms
        "target_95th_percentile": 1.0,  # 1 second
        "ramp_up_time": 10,  # seconds
        "steady_state_time": 60,  # seconds
        "ramp_down_time": 10,  # seconds
    }


# Cleanup fixtures
@pytest.fixture(scope="session", autouse=True)
def cleanup_environment():
    """Clean up test environment after session."""
    yield

    # Clean up Docker containers if needed
    try:
        client = docker.from_env()

        # List of test containers to clean up
        test_containers = ["tiger-mcp-test-postgres", "tiger-mcp-test-redis"]

        for container_name in test_containers:
            try:
                containers = client.containers.list(
                    all=True, filters={"name": container_name}
                )
                for container in containers:
                    container.stop()
                    container.remove()
            except Exception:
                pass  # Ignore cleanup errors

    except Exception:
        pass  # Docker might not be available


# Helper functions
def wait_for_condition(
    condition_func, timeout: int = 30, interval: float = 0.5
) -> bool:
    """Wait for a condition to become true."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False


async def simulate_load(
    operation_func, concurrent_requests: int, total_requests: int, **kwargs
):
    """Simulate load on a system."""
    semaphore = asyncio.Semaphore(concurrent_requests)
    results = []

    async def limited_operation():
        async with semaphore:
            start_time = time.time()
            try:
                result = await operation_func(**kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)

            duration = time.time() - start_time
            return {
                "success": success,
                "duration": duration,
                "result": result,
                "error": error,
            }

    # Create and run all operations
    tasks = [limited_operation() for _ in range(total_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
