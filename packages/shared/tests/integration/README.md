# Tiger MCP Integration Tests

Comprehensive integration tests for Tiger MCP multi-account workflows with real database operations, process pools, and MCP server testing.

## Overview

This test suite provides complete integration testing for the Tiger MCP system including:

- **Multi-account workflows**: End-to-end scenarios with multiple Tiger accounts
- **Database integration**: Real PostgreSQL operations with connection pooling  
- **Process pool testing**: Multiprocessing with real worker processes
- **MCP server integration**: Full server functionality testing
- **Performance testing**: Load testing and performance validation
- **Fault tolerance**: Error scenarios and recovery testing

## Test Structure

### Core Test Files

- `test_multi_account_workflows.py` - End-to-end multi-account scenarios
- `test_database_integration.py` - Database operations with real PostgreSQL
- `test_process_pool_integration.py` - Process pool with real multiprocessing
- `test_mcp_server_integration.py` - Full MCP server integration tests

### Supporting Files

- `fixtures/integration_fixtures.py` - Comprehensive test fixtures
- `test_data/` - Sample API responses, market data, and test scenarios
- `docker-compose.test.yml` - Test environment configuration
- `run_integration_tests.py` - Custom test runner with infrastructure management

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- At least 4GB RAM available
- Ports 15432 (PostgreSQL) and 16379 (Redis) available

### Run All Tests

```bash
# Using Docker Compose (Recommended)
docker-compose -f docker-compose.test.yml up integration-tests

# Using local Python (requires manual setup)
python tests/integration/run_integration_tests.py
```

### Run Specific Test Categories

```bash
# Multi-account workflow tests
python -m pytest tests/integration/test_multi_account_workflows.py -v

# Database integration tests
python -m pytest tests/integration/test_database_integration.py -v

# Process pool tests
python -m pytest tests/integration/test_process_pool_integration.py -v

# MCP server tests
python -m pytest tests/integration/test_mcp_server_integration.py -v
```

## Advanced Usage

### Performance and Load Testing

```bash
# Performance tests
docker-compose -f docker-compose.test.yml --profile performance up

# Load tests (high resource usage)  
docker-compose -f docker-compose.test.yml --profile load-test up

# Custom performance testing
python tests/integration/run_integration_tests.py --performance --parallel 8
```

### Development and Debugging

```bash
# Run with coverage
python tests/integration/run_integration_tests.py --coverage

# Run specific test pattern
python tests/integration/run_integration_tests.py -k "test_multi_account"

# Verbose output for debugging
python tests/integration/run_integration_tests.py --verbose

# Run single test file
python tests/integration/run_integration_tests.py -f test_database_integration.py
```

### Custom Configuration

```bash
# Set custom environment variables
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test_db"
export REDIS_URL="redis://localhost:6379/0"
export ENCRYPTION_MASTER_KEY="your_test_key_here"

# Run with custom settings
python -m pytest tests/integration/ --tb=short --maxfail=5
```

## Test Categories

### Multi-Account Workflows

Tests complete workflows across multiple Tiger accounts:

- **Account Creation**: Multiple accounts with different configurations
- **Default Account Management**: Setting and switching default accounts  
- **Cross-Account Operations**: Data operations with intelligent routing
- **Failover Scenarios**: Account failures and automatic failover
- **Load Balancing**: Distribution of operations across accounts
- **Token Management**: Automated token refresh across accounts

### Database Integration

Tests database operations with real PostgreSQL:

- **Connection Pooling**: Multiple concurrent database connections
- **Transaction Management**: ACID compliance and isolation
- **Concurrent Operations**: Multi-threaded database access
- **Performance Testing**: Query performance and optimization
- **Data Consistency**: Referential integrity and constraints
- **Migration Testing**: Schema changes and data migrations

### Process Pool Integration

Tests multiprocessing with real worker processes:

- **Process Management**: Worker process lifecycle
- **Task Distribution**: Load balancing across processes
- **Error Handling**: Process failure and recovery
- **Resource Management**: Memory and CPU usage monitoring
- **Performance Scaling**: Multi-core utilization testing

### MCP Server Integration

Tests complete MCP server functionality:

- **Tool Execution**: All MCP tools with real data
- **Account Routing**: Request routing to appropriate accounts
- **Error Handling**: API failures and recovery
- **Concurrent Operations**: Multiple simultaneous requests
- **Performance Testing**: Response times and throughput

## Test Data and Fixtures

### Sample Data

- `api_responses/tiger_api_samples.json` - Tiger API response samples
- `market_data/sample_market_data.json` - Market data for testing
- `scenarios/trading_scenarios.json` - Trading scenarios and edge cases

### Test Fixtures

The integration fixtures provide:

- **Real Database**: PostgreSQL container with test schema
- **Redis Instance**: Redis container for caching tests
- **Multiple Accounts**: Pre-configured Tiger accounts
- **Mock APIs**: Tiger API response mocking
- **Process Pools**: Real multiprocessing executors
- **MCP Server**: Complete server instance

### Infrastructure Management

The test suite automatically manages:

- Docker containers for PostgreSQL and Redis
- Database schema creation and migration
- Test data loading and cleanup
- Network configuration
- Container lifecycle management

## Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL="postgresql+asyncpg://tiger_test:tiger_test@localhost:15432/tiger_mcp_test"
REDIS_URL="redis://localhost:16379/15"

# Test Configuration  
ENVIRONMENT="test"
LOG_LEVEL="DEBUG"
PYTEST_VERBOSITY="2"

# Security Configuration
ENCRYPTION_MASTER_KEY="dGVzdF9lbmNyeXB0aW9uX2tleV8zMl9ieXRlc190ZXN0"
JWT_SECRET="test_jwt_secret_integration_tests_very_secure"

# Tiger API Configuration
TIGER_MOCK_MODE="true"
TIGER_SANDBOX="true"

# Performance Configuration
PYTEST_WORKERS="4"
MAX_CONCURRENT_TESTS="10"
```

### Docker Compose Profiles

- `default` - Basic integration tests
- `performance` - Performance and benchmark tests
- `load-test` - High-load stress testing
- `reporting` - Test report generation

## Performance Benchmarks

### Expected Performance Targets

- **Database Operations**: < 100ms per query
- **Account Creation**: < 2 seconds per account
- **Token Refresh**: < 500ms per account
- **MCP Tool Execution**: < 1 second per tool
- **Process Pool Tasks**: < 100ms per task

### Load Testing Targets

- **Concurrent Users**: 50-100 simultaneous operations
- **Throughput**: 500+ operations per second
- **Error Rate**: < 2% under normal load
- **Response Time**: 95th percentile < 1 second

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check if ports are in use
   lsof -i :15432  # PostgreSQL
   lsof -i :16379  # Redis
   
   # Kill processes using ports
   sudo kill -9 $(lsof -t -i:15432)
   ```

2. **Docker Issues**
   ```bash
   # Clean up Docker containers
   docker-compose -f docker-compose.test.yml down -v
   
   # Rebuild images
   docker-compose -f docker-compose.test.yml build --no-cache
   ```

3. **Database Connection Issues**
   ```bash
   # Check PostgreSQL container logs
   docker logs tiger-mcp-postgres-test
   
   # Manually test connection
   pg_isready -h localhost -p 15432 -U tiger_test
   ```

4. **Memory Issues**
   ```bash
   # Check available memory
   free -h
   
   # Reduce parallel workers
   python tests/integration/run_integration_tests.py --parallel 2
   ```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL="DEBUG"
export PYTEST_VERBOSITY="3"

# Run with pdb on failures
python -m pytest tests/integration/ --pdb

# Profile test execution
python -m pytest tests/integration/ --profile-svg
```

## Contributing

### Adding New Tests

1. **Follow naming convention**: `test_*.py` files with `test_*` functions
2. **Use appropriate fixtures**: Import from `fixtures.integration_fixtures`
3. **Add proper markers**: Use `@pytest.mark.asyncio` for async tests
4. **Document test purpose**: Clear docstrings explaining what is tested
5. **Include error scenarios**: Test both success and failure paths

### Test Categories

Mark tests with appropriate categories:

```python
@pytest.mark.integration  # All integration tests
@pytest.mark.database     # Database-specific tests  
@pytest.mark.performance  # Performance tests
@pytest.mark.load_test    # Load testing
@pytest.mark.slow         # Long-running tests
```

### Performance Considerations

- Keep individual tests under 30 seconds
- Use appropriate timeouts for external resources
- Clean up resources in teardown methods
- Avoid unnecessary database recreations
- Use connection pooling efficiently

## Monitoring and Reporting

### Test Results

Test results are generated in multiple formats:

- **JUnit XML**: `test_results/integration-results.xml`
- **Coverage HTML**: `test_results/coverage_html/`
- **Coverage XML**: `test_results/coverage.xml`
- **Test Logs**: `test_results/integration_tests.log`

### Metrics Tracked

- Test execution time
- Database query performance  
- Memory usage patterns
- Process pool utilization
- API response times
- Error rates and patterns

### Continuous Integration

The integration tests are designed to run in CI environments:

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  run: |
    docker-compose -f docker-compose.test.yml up --abort-on-container-exit integration-tests
    
- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: test_results/
```

## Support

For issues with the integration tests:

1. Check the troubleshooting section above
2. Review the test logs in `test_results/integration_tests.log`  
3. Ensure all prerequisites are met
4. Verify Docker and database connectivity
5. Check system resources (memory, disk space, network)

The integration test suite is designed to provide comprehensive validation of the Tiger MCP system's multi-account functionality with real-world scenarios and performance testing.