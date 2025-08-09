"""
Integration tests for Tiger MCP multi-account workflows.

This package contains comprehensive integration tests that verify the complete
functionality of the Tiger MCP system including:

- Multi-account creation and management
- Cross-account data operations with routing logic
- Account failover and recovery scenarios
- Token refresh automation across accounts
- Trading operations with proper account isolation
- Load balancing and performance under load
- Database operations with real PostgreSQL
- Process pool integration with real multiprocessing
- MCP server integration with full system testing

Test Structure:
- test_multi_account_workflows.py: End-to-end multi-account scenarios
- test_database_integration.py: Database operations with real PostgreSQL
- test_process_pool_integration.py: Process pool with real multiprocessing
- test_mcp_server_integration.py: Full server integration tests

Fixtures:
- fixtures/integration_fixtures.py: Real database, Redis, Tiger API fixtures
- fixtures/: Comprehensive test data and scenarios

Test Data:
- test_data/api_responses/: Sample Tiger API responses
- test_data/market_data/: Market data samples for testing
- test_data/scenarios/: Trading and error scenarios

Docker Support:
- docker-compose.test.yml: Test environment with PostgreSQL and Redis
- Dockerfile.integration-tests: Test runner container
- Dockerfile.test-db-setup: Database setup container

Usage:
    # Run all integration tests
    python -m pytest tests/integration/

    # Run specific test suite
    python -m pytest tests/integration/test_multi_account_workflows.py

    # Run with coverage
    python -m pytest tests/integration/ --cov=shared

    # Run using Docker Compose
    docker-compose -f docker-compose.test.yml up integration-tests

    # Run performance tests
    docker-compose -f docker-compose.test.yml --profile performance up

    # Run load tests
    docker-compose -f docker-compose.test.yml --profile load-test up

    # Use custom test runner
    python tests/integration/run_integration_tests.py --coverage --parallel 4

Environment Variables:
    DATABASE_URL: PostgreSQL connection string for tests
    REDIS_URL: Redis connection string for tests
    ENVIRONMENT: Should be set to 'test'
    ENCRYPTION_MASTER_KEY: Test encryption key
    JWT_SECRET: Test JWT secret
    TIGER_MOCK_MODE: Enable mock mode for Tiger API
"""

import pytest

# Test markers for categorizing tests
pytest_plugins = ["fixtures.integration_fixtures"]

# Custom markers
pytestmark = [
    pytest.mark.integration,  # All tests in this package are integration tests
]

# Test configuration
INTEGRATION_TEST_CONFIG = {
    "database_url": "postgresql+asyncpg://tiger_test:tiger_test@localhost:15432/tiger_mcp_test",
    "redis_url": "redis://localhost:16379/15",
    "test_timeout": 300,  # 5 minutes max per test
    "max_concurrent_tests": 10,
    "setup_timeout": 60,  # 1 minute for setup
    "teardown_timeout": 30,  # 30 seconds for teardown
}

__all__ = [
    "INTEGRATION_TEST_CONFIG",
]
