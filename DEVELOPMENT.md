# 🔧 Development Guide

This guide covers technical details, workspace management, and development workflows for the Tiger MCP system.

## 🏗️ UV Workspace Structure

This project uses [UV](https://docs.astral.sh/uv/) workspace management for efficient Python package management and dependency resolution.

```
tiger-mcp/                    # Root workspace
├── pyproject.toml           # Workspace configuration
├── uv.lock                  # Lockfile for reproducible builds
├── packages/                # Workspace packages
│   ├── mcp-server/         # FastMCP server package  
│   ├── dashboard-api/      # FastAPI backend package
│   ├── database/           # Database models/migrations package
│   └── shared/             # Shared utilities package
├── docker/                 # Docker configurations
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── tests/                  # Integration and unit tests
├── reports/                # Generated reports and validation
├── config/                 # Configuration files and templates
└── references/            # Reference implementations and docs
```

### Workspace Benefits

- **Unified Dependencies**: Single lockfile for all Python packages
- **Cross-Package Development**: Easy local development across packages
- **Consistent Versions**: Shared dependencies automatically resolved
- **Fast Installs**: Efficient dependency resolution and caching
- **Type Safety**: Shared type definitions across packages

## 🚀 Development Setup

### Prerequisites
- Python 3.11+
- [UV](https://docs.astral.sh/uv/) package manager
- Node.js 18+
- PostgreSQL 13+ (or use Docker)
- Docker & Docker Compose (optional)

### Setup Instructions

1. **Clone and initialize workspace**:
```bash
git clone <repository>
cd tiger-mcp
cp .env.template .env  # Configure your Tiger API credentials
```

2. **Initialize UV workspace**:
```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync workspace dependencies
uv sync
```

3. **Start with Docker Compose (recommended)**:
```bash
docker-compose up -d
```

4. **Or run components separately**:

```bash
# Database
docker-compose up -d postgres

# MCP Server (in workspace)
uv run --package mcp-server python -m mcp_server

# Dashboard API (in workspace)  
uv run --package dashboard-api uvicorn dashboard_api.main:app --reload
```

## 🔧 Multi-Account Configuration

The Tiger MCP system supports **multiple Tiger Brokers accounts** through a single MCP server instance with flexible account routing.

### Account Configuration

Configure multiple accounts in your environment:

```bash
# Primary account (default)
TIGER_CLIENT_ID=your_primary_client_id
TIGER_PRIVATE_KEY=your_primary_private_key
TIGER_ACCOUNT=your_primary_account_id

# Additional accounts (comma-separated)
TIGER_ADDITIONAL_ACCOUNTS=account2_id,account3_id
TIGER_CLIENT_ID_ACCOUNT2=your_client_id_2
TIGER_PRIVATE_KEY_ACCOUNT2=your_private_key_2
TIGER_CLIENT_ID_ACCOUNT3=your_client_id_3
TIGER_PRIVATE_KEY_ACCOUNT3=your_private_key_3

# Account permissions (optional - controls which accounts can trade)
TIGER_TRADING_ACCOUNTS=your_primary_account_id,account2_id  # account3 is read-only
```

### Claude Code Integration with Multi-Accounts

When using with Claude Code, specify accounts in your requests:

```
💬 "Show me portfolio for account account2_id"
💬 "Switch to trading account account3_id and buy 100 AAPL"
💬 "Compare performance across all my accounts"
💬 "What's the total portfolio value across accounts?"
```

The MCP server automatically routes requests to the appropriate Tiger Brokers account based on:
1. Explicit account specification in the request
2. Default account configuration
3. Account permissions and trading restrictions

### Account Management Features

- **Account Discovery**: Automatically detects and validates configured accounts
- **Permission Control**: Granular control over trading vs read-only access
- **Portfolio Aggregation**: Cross-account portfolio views and analytics
- **Account Switching**: Seamless switching between accounts in conversations
- **Risk Management**: Account-specific position limits and risk controls

## 🧪 Workspace Commands

```bash
# Install workspace dependencies
uv sync

# Run commands in specific packages
uv run --package mcp-server <command>
uv run --package dashboard-api <command>

# Add dependencies to specific packages
uv add --package mcp-server fastapi
uv add --package shared pydantic

# Run tests across workspace
uv run pytest

# Format code across workspace
uv run black .
uv run isort .
```

## 🏗️ Project Structure

### Package Details

- **packages/mcp-server/**: Core MCP server implementation using FastMCP
- **packages/dashboard-api/**: FastAPI REST API for web dashboard  
- **packages/database/**: Database models and migration scripts
- **packages/shared/**: Shared utilities and configurations
- **docker/**: Docker configurations for all services
- **config/**: Configuration files and templates
- **tests/**: Test files and integration tests
- **reports/**: Validation reports and security scans

### Environment Configuration

Complete environment template (`.env`):

```bash
# Tiger API Configuration
TIGER_CLIENT_ID=your_client_id
TIGER_PRIVATE_KEY=your_private_key
TIGER_ACCOUNT=your_account_id
TIGER_SANDBOX=true

# Multi-Account Setup (optional)
TIGER_ADDITIONAL_ACCOUNTS=account2,account3
TIGER_CLIENT_ID_ACCOUNT2=client_id_2
TIGER_PRIVATE_KEY_ACCOUNT2=private_key_2
TIGER_CLIENT_ID_ACCOUNT3=client_id_3
TIGER_PRIVATE_KEY_ACCOUNT3=private_key_3
TIGER_TRADING_ACCOUNTS=your_account_id,account2

# Database Configuration
DATABASE_URL=postgresql://tiger:tiger@localhost:5432/tiger_mcp

# Application Configuration
DEBUG=true
LOG_LEVEL=info
MCP_SERVER_PORT=8000
DASHBOARD_API_PORT=8001

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=your_jwt_secret_key
ENCRYPTION_KEY=your_encryption_key
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run specific test files
uv run pytest tests/test_tiger_auth.py
uv run pytest tests/test_integration_scenarios.py
uv run pytest tests/test_performance_compatibility.py

# Test individual components
cd packages/mcp-server && python -m pytest
cd packages/dashboard-api && python -m pytest

# Run tests with coverage
uv run pytest --cov=packages --cov-report=html
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component and API testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Authentication and authorization testing
- **Multi-Account Tests**: Account routing and permission testing

## 🐳 Docker Development

### Development Environment

```bash
# Start development stack
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f mcp-server
docker-compose logs -f dashboard-api

# Rebuild services
docker-compose -f docker-compose.dev.yml build --no-cache
```

### Production Deployment

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Health checks
curl http://localhost:8000/health
curl http://localhost:8001/health
```

## 🔍 Code Quality

### Linting and Formatting

```bash
# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy packages/

# Security scanning
uv run bandit -r packages/

# All quality checks
make lint
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

## 🏷️ Package Management

### Adding Dependencies

```bash
# Add to specific package
uv add --package mcp-server "fastapi>=0.100.0"
uv add --package shared "pydantic>=2.0.0"

# Add development dependencies
uv add --dev "pytest>=7.4.0"

# Sync after changes
uv sync
```

### Version Management

```bash
# Show package info
uv show

# Update dependencies
uv sync --upgrade

# Lock dependencies
uv lock
```

## 🔧 Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and test
uv sync
uv run pytest

# Format and lint
make lint

# Commit and push
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature
```

### 2. Package Development

```bash
# Work on specific package
cd packages/mcp-server

# Install in development mode
uv sync

# Run package tests
python -m pytest

# Test integration
cd ../.. && uv run pytest tests/
```

### 3. Debug Mode

```bash
# Start in debug mode
DEBUG=true uv run --package mcp-server python -m mcp_server

# With verbose logging
LOG_LEVEL=debug uv run --package mcp-server python -m mcp_server

# Debug with pdb
uv run --package mcp-server python -m pdb -m mcp_server
```

## 📊 Monitoring and Observability

### Health Checks

```bash
# MCP Server health
curl http://localhost:8000/health

# Dashboard API health  
curl http://localhost:8001/health

# Database connectivity
uv run python -c "from packages.database.connection import test_connection; test_connection()"
```

### Logging

```bash
# View real-time logs
tail -f logs/mcp-server.log
tail -f logs/dashboard-api.log

# Log analysis
grep ERROR logs/mcp-server.log
grep "account" logs/mcp-server.log | head -10
```

## 🚀 Performance Optimization

### Profiling

```bash
# Profile MCP server
uv run python -m cProfile -o profile.stats -m mcp_server

# Analyze profile
uv run python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('tottime'); p.print_stats(20)"

# Memory profiling
uv run python -m memory_profiler packages/mcp-server/mcp_server/main.py
```

### Load Testing

```bash
# Install load testing tools
uv add --dev locust

# Run load tests
uv run locust -f tests/load_test.py --host=http://localhost:8000
```

## 🔐 Security Best Practices

### Credential Management

- Never commit real credentials to version control
- Use `.env` files for local development
- Use secure environment variables for production
- Rotate API keys regularly
- Use separate accounts for testing and production

### Network Security

```bash
# Generate SSL certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/ssl/server.key \
  -out docker/ssl/server.crt

# Start with SSL
docker-compose -f docker-compose.prod.yml up -d
```

### Account Security

- Enable account-specific permissions
- Use read-only accounts for analysis
- Implement position limits per account
- Monitor for suspicious activity
- Enable audit logging

## 🏁 Troubleshooting

### Common Issues

1. **UV sync fails**
   ```bash
   # Clear cache
   uv clean
   rm -rf .venv uv.lock
   uv sync
   ```

2. **Database connection issues**
   ```bash
   # Reset database
   docker-compose down -v
   docker-compose up -d postgres
   uv run alembic upgrade head
   ```

3. **Tiger API authentication**
   ```bash
   # Test credentials
   uv run python -c "from packages.shared.tiger_auth import test_auth; test_auth()"
   ```

4. **Multi-account configuration**
   ```bash
   # Validate account setup
   uv run python -c "from packages.mcp-server.account_manager import validate_accounts; validate_accounts()"
   ```

### Debug Commands

```bash
# Test MCP server
uv run --package mcp-server python -m mcp_server --debug

# Test account routing
uv run python tests/test_account_routing.py

# Validate environment
uv run python scripts/validate_env.py
```