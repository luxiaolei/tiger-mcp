"""
Test configuration and fixtures for Tiger MCP Server tests.

Provides shared fixtures, mock services, and test configuration for all test modules.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from loguru import logger

# Add project paths
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SHARED_PATH = _PROJECT_ROOT / "shared" / "src"
_DATABASE_PATH = _PROJECT_ROOT / "database" / "src"
_MCP_SERVER_PATH = Path(__file__).parent.parent / "src"

for path in [_SHARED_PATH, _DATABASE_PATH, _MCP_SERVER_PATH]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Import fixtures data
from tests.fixtures.mock_data import (
    MockAccountData,
    MockProcessData,
    MockTigerAPIData,
)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "network: Tests requiring network access")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers."""
    for item in items:
        if "integration" not in item.keywords and "slow" not in item.keywords:
            item.add_marker(pytest.mark.unit)


# Event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Environment fixtures
@pytest.fixture(scope="session")
def test_env():
    """Setup test environment variables."""
    original_env = os.environ.copy()

    # Set test environment variables
    test_vars = {
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": "sqlite:///:memory:",
        "TIGER_SDK_PATH": "/tmp/test_tiger_sdk",
        "ENCRYPTION_KEY": "test_key_12345678901234567890123456789012",
    }

    os.environ.update(test_vars)

    yield test_vars

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Configuration fixtures
@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    from mcp_server.config_manager import TigerMCPConfig

    config = TigerMCPConfig()
    config.environment = "testing"
    config.server.log_level = "DEBUG"
    config.database.url = "sqlite:///:memory:"
    config.database.echo = False
    config.process.min_workers = 1
    config.process.max_workers = 2
    config.process.target_workers = 1
    config.security.encryption_key = "test_key_12345678901234567890123456789012"

    return config


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    mock_manager = MagicMock()
    mock_manager.load_config.return_value = mock_config()
    return mock_manager


# Database fixtures
@pytest.fixture
async def mock_db_manager():
    """Mock database manager."""
    mock_manager = AsyncMock()
    mock_manager.initialize = AsyncMock()
    mock_manager.cleanup = AsyncMock()
    mock_manager.get_session = AsyncMock()

    with patch("database.get_db_manager", return_value=mock_manager):
        yield mock_manager


# Account management fixtures
@pytest.fixture
async def mock_account_manager():
    """Mock account manager with test accounts."""
    mock_manager = AsyncMock()
    mock_data = MockAccountData()

    # Setup mock methods
    mock_manager.initialize = AsyncMock()
    mock_manager.cleanup = AsyncMock()
    mock_manager.get_account_by_id = AsyncMock()
    mock_manager.list_accounts = AsyncMock(return_value=mock_data.accounts)
    mock_manager.add_account = AsyncMock()
    mock_manager.remove_account = AsyncMock()
    mock_manager.refresh_expiring_tokens = AsyncMock()
    mock_manager.cleanup_expired_sessions = AsyncMock()

    # Setup account data
    mock_manager.accounts = {acc.id: acc for acc in mock_data.accounts}

    with patch("shared.account_manager.get_account_manager", return_value=mock_manager):
        yield mock_manager


@pytest.fixture
async def mock_account_router():
    """Mock account router."""
    mock_router = AsyncMock()
    mock_router.route_data_request = AsyncMock()
    mock_router.route_trading_request = AsyncMock()
    mock_router.get_default_data_account = AsyncMock()
    mock_router.get_default_trading_account = AsyncMock()

    with patch("shared.account_router.get_account_router", return_value=mock_router):
        yield mock_router


# Process pool fixtures
@pytest.fixture
async def mock_process_pool():
    """Mock Tiger process pool."""
    mock_pool = AsyncMock()
    mock_data = MockProcessData()

    # Setup mock methods
    mock_pool.start = AsyncMock()
    mock_pool.stop = AsyncMock()
    mock_pool.get_or_create_process = AsyncMock(return_value="test_process_id")
    mock_pool.execute_task = AsyncMock()
    mock_pool.get_process_status = AsyncMock()
    mock_pool.get_all_processes = AsyncMock(return_value=mock_data.processes)
    mock_pool.restart_process = AsyncMock(return_value=True)
    mock_pool.remove_process = AsyncMock(return_value=True)

    # Setup process data
    mock_pool.processes = {proc.process_id: proc for proc in mock_data.processes}
    mock_pool.max_processes = 4

    with patch(
        "mcp_server.tiger_process_pool.get_process_pool", return_value=mock_pool
    ):
        yield mock_pool


@pytest.fixture
async def mock_process_manager():
    """Mock process manager."""
    mock_manager = AsyncMock()

    # Setup mock methods
    mock_manager.configure = AsyncMock()
    mock_manager.start = AsyncMock()
    mock_manager.stop = AsyncMock()
    mock_manager.check_worker_health = AsyncMock(return_value=[])
    mock_manager.auto_scale = AsyncMock()
    mock_manager.cleanup_old_metrics = AsyncMock()

    # Setup manager data
    mock_manager.workers = {}

    with patch(
        "mcp_server.process_manager.get_process_manager", return_value=mock_manager
    ):
        yield mock_manager


# Tiger API fixtures
@pytest.fixture
def mock_tiger_api_data():
    """Mock Tiger API response data."""
    return MockTigerAPIData()


@pytest.fixture
async def mock_tiger_service():
    """Mock Tiger API service."""
    mock_service = AsyncMock()
    mock_service.start = AsyncMock()
    mock_service.stop = AsyncMock()

    with patch("mcp_server.example_usage.TigerAPIService", return_value=mock_service):
        yield mock_service


# MCP Server fixtures
@pytest.fixture
async def mock_mcp_server(
    mock_config,
    mock_db_manager,
    mock_account_manager,
    mock_account_router,
    mock_process_manager,
    mock_tiger_service,
):
    """Mock Tiger MCP Server with all dependencies."""
    from mcp_server.server import TigerMCPServer

    server = TigerMCPServer()
    server.config = mock_config
    server.account_manager = mock_account_manager
    server.account_router = mock_account_router
    server.process_manager = mock_process_manager
    server.tiger_service = mock_tiger_service
    server._started = False
    server.background_tasks = []

    yield server


@pytest.fixture
async def mock_fastmcp_server():
    """Mock FastMCP server."""
    mock_server = MagicMock()
    mock_server.run = AsyncMock()
    mock_server.run_sse = AsyncMock()

    with patch("fastmcp.FastMCP", return_value=mock_server):
        yield mock_server


# Tool execution fixtures
@pytest.fixture
async def mock_tool_executor():
    """Mock tool executor for testing tool calls."""
    mock_executor = AsyncMock()

    # Setup tool execution results
    mock_tiger_data = MockTigerAPIData()

    mock_executor.execute_data_tool = AsyncMock(
        return_value=mock_tiger_data.quote_response
    )
    mock_executor.execute_info_tool = AsyncMock(
        return_value=mock_tiger_data.contracts_response
    )
    mock_executor.execute_account_tool = AsyncMock(return_value={"success": True})
    mock_executor.execute_trading_tool = AsyncMock(
        return_value=mock_tiger_data.positions_response
    )

    yield mock_executor


# Process isolation fixtures
@pytest.fixture
def mock_multiprocessing():
    """Mock multiprocessing components for isolated testing."""
    mock_process = MagicMock()
    mock_process.is_alive.return_value = True
    mock_process.pid = 12345
    mock_process.start = MagicMock()
    mock_process.join = MagicMock()
    mock_process.terminate = MagicMock()
    mock_process.kill = MagicMock()

    mock_queue = MagicMock()
    mock_queue.put = MagicMock()
    mock_queue.get = MagicMock()
    mock_queue.put_nowait = MagicMock()
    mock_queue.get_nowait = MagicMock()
    mock_queue.empty.return_value = False

    with (
        patch("multiprocessing.Process", return_value=mock_process),
        patch("multiprocessing.Queue", return_value=mock_queue),
    ):
        yield {"process": mock_process, "queue": mock_queue}


# Utility fixtures
@pytest.fixture
def capture_logs():
    """Capture log messages for testing."""
    logs = []

    def capture_handler(record):
        logs.append(record)

    # Add custom handler to capture logs
    handler_id = logger.add(capture_handler, level="DEBUG")

    yield logs

    # Remove handler after test
    logger.remove(handler_id)


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing."""
    test_time = datetime(2024, 1, 15, 10, 30, 0)

    with patch("datetime.datetime") as mock_dt:
        mock_dt.utcnow.return_value = test_time
        mock_dt.return_value = test_time
        yield test_time


# Test data fixtures
@pytest.fixture
def sample_account_id():
    """Sample account ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_task_request():
    """Sample task request for testing."""
    return {
        "task_id": str(uuid.uuid4()),
        "method": "get_quote",
        "args": ["AAPL"],
        "kwargs": {},
        "timeout": 30.0,
    }


@pytest.fixture
def sample_tiger_symbols():
    """Sample Tiger symbols for testing."""
    return ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]


# Error simulation fixtures
@pytest.fixture
def simulate_network_error():
    """Simulate network errors for testing error handling."""

    def _simulate_error(method):
        if method == "network_error":
            raise ConnectionError("Network unreachable")
        elif method == "timeout_error":
            raise TimeoutError("Request timed out")
        elif method == "api_error":
            raise RuntimeError("API returned error")
        return {"success": True}

    return _simulate_error


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Auto cleanup after each test."""
    yield

    # Clear any remaining asyncio tasks
    pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
    if pending_tasks:
        for task in pending_tasks:
            task.cancel()
        await asyncio.gather(*pending_tasks, return_exceptions=True)
