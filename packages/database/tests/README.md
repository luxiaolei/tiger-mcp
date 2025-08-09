# Database Package Tests

This directory contains comprehensive unit tests for the database package.

## Test Structure

- **`conftest.py`**: Pytest configuration and shared fixtures
- **`test_models.py`**: Tests for all SQLAlchemy models
- **`test_utils.py`**: Tests for database utility functions
- **`test_migrations.py`**: Tests for Alembic migration operations
- **`test_config.py`**: Tests for database configuration
- **`test_engine.py`**: Tests for async database engine and session management

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov
```

### Run All Tests

```bash
# From the database package root
pytest

# With coverage report
pytest --cov=src/database --cov-report=html
```

### Run Specific Test Categories

```bash
# Run only model tests
pytest -m models

# Run only async tests
pytest -m async

# Run only unit tests (fast)
pytest -m unit

# Run integration tests
pytest -m integration
```

### Run Specific Test Files

```bash
# Run model tests
pytest tests/test_models.py

# Run utility tests
pytest tests/test_utils.py

# Run migration tests
pytest tests/test_migrations.py
```

### Run Specific Test Classes or Methods

```bash
# Run specific test class
pytest tests/test_models.py::TestTigerAccountModel

# Run specific test method
pytest tests/test_models.py::TestTigerAccountModel::test_create_tiger_account
```

## Test Configuration

The test suite uses the following configuration:

- **Async Support**: Full async/await support with `pytest-asyncio`
- **Database Isolation**: Each test uses isolated database sessions
- **Fixtures**: Comprehensive fixtures for database setup and test data
- **Coverage**: 90% minimum coverage requirement
- **Markers**: Test categorization with pytest markers

## Database Testing Strategy

### Test Database Setup

Tests use temporary SQLite databases for isolation:

- Each test gets a fresh database instance
- Transactions are rolled back after each test
- No persistent state between tests

### Test Data Factories

The test suite includes factories for creating test data:

- `TigerAccountFactory`: Creates test Tiger accounts
- `APIKeyFactory`: Creates test API keys
- `AuditLogFactory`: Creates test audit logs
- `TokenStatusFactory`: Creates test token status records

### Async Testing

All async operations are properly tested:

- Database sessions and transactions
- Connection pooling and cleanup
- Error handling and retries

## Environment Variables

Tests use environment variables for configuration:

- `ENVIRONMENT=test`: Sets test environment
- `DB_DEBUG=true`: Enables debug logging
- `TESTING=true`: Indicates test execution

## Coverage Requirements

The test suite maintains 90% minimum coverage:

```bash
# Generate coverage report
pytest --cov=src/database --cov-report=html

# View coverage in browser
open htmlcov/index.html
```

## Migration Testing

Migration tests include:

- Schema creation and validation
- Upgrade and downgrade operations
- Data preservation during migrations
- PostgreSQL-specific features (when available)

## Performance Testing

Performance aspects tested include:

- Connection pooling efficiency
- Concurrent session usage
- Bulk operation performance
- Memory usage patterns

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the database package is in your Python path
2. **Async Errors**: Check that `pytest-asyncio` is installed
3. **Coverage Issues**: Verify test paths in `pytest.ini`
4. **Database Errors**: Ensure temporary directories are writable

### Debug Mode

Run tests with debug output:

```bash
pytest -v -s --log-cli-level=DEBUG
```

### Test Selection

Use pytest's powerful test selection:

```bash
# Run tests matching a pattern
pytest -k "test_create"

# Run tests in specific file with pattern
pytest tests/test_models.py -k "tiger_account"

# Skip slow tests
pytest -m "not slow"
```

## Contributing

When adding new tests:

1. Follow existing naming conventions
2. Use appropriate test markers
3. Include both positive and negative test cases
4. Test error conditions and edge cases
5. Maintain async/await patterns for async code
6. Update coverage requirements if needed

## Test Data Management

The test suite uses factories and fixtures for consistent test data:

- Always use factories for creating test objects
- Use fixtures for shared setup/teardown
- Ensure tests are independent and can run in any order
- Clean up resources in fixture teardown