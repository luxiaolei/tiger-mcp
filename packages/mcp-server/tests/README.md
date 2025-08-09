# Tiger MCP Server Test Suite

Comprehensive unit tests for the Tiger MCP Server package covering all components and tools.

## Test Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── fixtures/
│   ├── __init__.py
│   └── mock_data.py           # Mock data and response fixtures
├── test_tools/                # Tool-specific tests (22 tools)
│   ├── __init__.py
│   ├── test_data_tools.py     # 6 data fetching tools
│   ├── test_info_tools.py     # 4 informational tools
│   ├── test_account_tools.py  # 7 account management tools
│   └── test_trading_tools.py  # 5 trading tools
├── test_process_pool.py       # Process pool management tests
├── test_server.py             # Server orchestration tests
├── test_main.py               # FastMCP integration tests
└── README.md                  # This file
```

## Test Categories

### Unit Tests (Default)
Fast, isolated tests that mock external dependencies:
- Individual component testing
- Function-level testing
- Mock-based isolation

### Integration Tests
Component interaction tests:
- Service integration testing
- End-to-end workflows
- Cross-component communication

### Slow Tests
Time-intensive tests:
- Performance testing
- Stress testing
- Concurrent operation testing

### Network Tests
Tests requiring network access:
- External API testing (when needed)
- Network failure simulation

## Running Tests

### Run All Tests
```bash
# From mcp-server directory
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=src/mcp_server --cov-report=html
```

### Run Specific Test Categories
```bash
# Unit tests only (default)
pytest -m unit

# Integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Run specific test file
pytest tests/test_tools/test_data_tools.py

# Run specific test
pytest tests/test_server.py::TestTigerMCPServer::test_server_initialization
```

### Run with Different Verbosity
```bash
# Quiet output
pytest -q

# Verbose output
pytest -v

# Extra verbose (show test names)
pytest -vv

# Show local variables on failure
pytest -l
```

## Test Coverage

Current test coverage targets:
- **Minimum Coverage**: 80%
- **Target Coverage**: 90%+
- **Critical Components**: 95%+

### Coverage Reports
```bash
# Terminal report
pytest --cov=src/mcp_server --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=src/mcp_server --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=src/mcp_server --cov-report=xml
```

## Test Components

### Tool Tests (`test_tools/`)

#### Data Tools Tests (`test_data_tools.py`)
Tests for 6 market data tools:
- `tiger_get_quote` - Real-time quotes
- `tiger_get_kline` - Historical K-line data
- `tiger_get_market_data` - Market overview
- `tiger_search_symbols` - Symbol search
- `tiger_get_option_chain` - Options data
- `tiger_get_market_status` - Market hours

#### Info Tools Tests (`test_info_tools.py`)
Tests for 4 informational tools:
- `tiger_get_contracts` - Contract details
- `tiger_get_financials` - Financial data
- `tiger_get_corporate_actions` - Corporate actions
- `tiger_get_earnings` - Earnings data

#### Account Tools Tests (`test_account_tools.py`)
Tests for 7 account management tools:
- `tiger_list_accounts` - Account listing
- `tiger_add_account` - Account creation
- `tiger_remove_account` - Account deletion
- `tiger_get_account_status` - Account status
- `tiger_refresh_token` - Token refresh
- `tiger_set_default_data_account` - Default data account
- `tiger_set_default_trading_account` - Default trading account

#### Trading Tools Tests (`test_trading_tools.py`)
Tests for 6 trading tools:
- `tiger_get_positions` - Position data
- `tiger_get_account_info` - Account info
- `tiger_get_orders` - Order history
- `tiger_place_order` - Order placement
- `tiger_cancel_order` - Order cancellation
- `tiger_modify_order` - Order modification

### Process Pool Tests (`test_process_pool.py`)
Tests for `TigerProcessPool` class:
- Process lifecycle management
- Worker isolation and communication
- Health monitoring and recovery
- Task execution and routing
- Error handling and timeouts

### Server Tests (`test_server.py`)
Tests for `TigerMCPServer` class:
- Server initialization and lifecycle
- Service orchestration
- Background task management
- Configuration loading
- Health status reporting
- Graceful shutdown

### Main Integration Tests (`test_main.py`)
Tests for `TigerFastMCPServer` and entry points:
- FastMCP integration
- Tool registration
- Transport handling (stdio/SSE)
- CLI integration
- End-to-end workflows

## Mock Data and Fixtures

### Mock Data (`fixtures/mock_data.py`)
Comprehensive mock data including:
- **MockTigerAPIData**: Realistic Tiger API responses
- **MockAccountData**: Account fixtures
- **MockProcessData**: Process pool fixtures
- **MockServerData**: Server status fixtures

### Test Fixtures (`conftest.py`)
Shared test fixtures:
- **Configuration mocks**: Test configurations
- **Service mocks**: Database, account, process managers
- **Environment setup**: Test environment variables
- **Async utilities**: Event loops, async helpers

## Writing New Tests

### Test File Template
```python
"""
Unit tests for [Component Name].

Description of what this component does and what the tests cover.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import component under test
from mcp_server.[module] import [Component]


class Test[Component]:
    """Test suite for [Component]."""
    
    @pytest.mark.asyncio
    async def test_[functionality]_success(self, mock_dependencies):
        """Test successful [functionality]."""
        # Setup
        # Execute
        # Verify
        pass
    
    @pytest.mark.asyncio
    async def test_[functionality]_error(self, mock_dependencies):
        """Test [functionality] error handling."""
        # Setup error conditions
        # Execute
        # Verify error handling
        pass


class Test[Component]Integration:
    """Integration tests for [Component]."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_[integration_scenario](self, integration_fixtures):
        """Test [integration scenario]."""
        pass
```

### Test Best Practices
1. **Use descriptive test names**: `test_[what]_[when]_[expected]`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Mock external dependencies**: Use fixtures and mocks
4. **Test both success and failure cases**
5. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
6. **Mock at the right level**: Mock external services, not internal logic
7. **Test edge cases**: Empty inputs, boundary conditions
8. **Verify state changes**: Check that operations have expected effects
9. **Use async/await properly**: For async components

### Common Fixtures
- `mock_config`: Mock configuration
- `mock_account_manager`: Mock account management
- `mock_process_manager`: Mock process pool
- `mock_tiger_api_data`: Mock API responses
- `mock_multiprocessing`: Mock process operations

## Continuous Integration

The test suite is designed for CI/CD integration:
- **Fast feedback**: Unit tests run in <30 seconds
- **Parallel execution**: Tests can run in parallel
- **Coverage reporting**: XML/HTML reports for CI systems
- **Exit codes**: Proper exit codes for CI success/failure
- **Minimal dependencies**: Mock external services

### CI Configuration Example
```yaml
# Example GitHub Actions or similar
- name: Run Tests
  run: |
    pytest --cov=src/mcp_server --cov-report=xml --cov-fail-under=80
    
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure PYTHONPATH includes src
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   pytest
   ```

2. **Async Test Issues**
   ```python
   # Use pytest-asyncio
   @pytest.mark.asyncio
   async def test_async_function():
       await async_function()
   ```

3. **Mock Issues**
   ```python
   # Mock at the right level
   with patch('mcp_server.module.function') as mock_func:
       # Not with patch('module.function')
   ```

4. **Fixture Issues**
   ```python
   # Use fixtures from conftest.py
   def test_something(mock_account_manager):
       # Fixtures available automatically
   ```

### Debug Tests
```bash
# Run with debugging
pytest --pdb  # Drop to debugger on failure
pytest -s     # Show print statements
pytest --tb=long  # Full traceback
```

## Performance

### Test Performance Targets
- **Unit tests**: <30 seconds total
- **Integration tests**: <2 minutes total
- **Full suite**: <5 minutes total
- **Individual test**: <1 second each

### Performance Optimization
- Use mocks instead of real services
- Minimize setup/teardown time
- Run tests in parallel when possible
- Cache expensive fixtures
- Use fast assertion methods

## Contributing

When adding new tests:
1. Follow the existing structure and patterns
2. Add appropriate markers (`unit`, `integration`, `slow`)
3. Update this README if adding new test categories
4. Ensure tests pass in CI environment
5. Maintain test coverage above 80%
6. Add docstrings explaining what each test covers