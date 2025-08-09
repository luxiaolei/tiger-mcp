# Tiger MCP System

A comprehensive Model Context Protocol (MCP) server system for Tiger Brokers API integration, featuring real-time market data, trading capabilities, and a web dashboard for monitoring and management.

## UV Workspace Structure

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

## Features

### MCP Server
- **Market Data**: Real-time quotes, historical data, market scanning
- **Trading Operations**: Order placement, portfolio management, position tracking
- **Account Management**: Account info, funding, transactions
- **Data Analysis**: Technical indicators, financial metrics, research data

### Dashboard
- **Portfolio Monitoring**: Real-time portfolio tracking and P&L analysis
- **Trading Interface**: Order management and execution monitoring
- **Market Overview**: Market scanners, watchlists, and alerts
- **Analytics**: Performance metrics, risk analysis, and reporting

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 13+
- Docker & Docker Compose

### Development Setup

#### Prerequisites
- Python 3.11+
- [UV](https://docs.astral.sh/uv/) package manager
- Node.js 18+
- PostgreSQL 13+ (or use Docker)
- Docker & Docker Compose (optional)

#### Setup Instructions

1. **Clone and initialize workspace**:
```bash
git clone <repository>
cd tiger-mcp
cp .env.example .env  # Configure your Tiger API credentials
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

# Dashboard Frontend (not implemented yet)
# cd dashboard-frontend
# npm install  
# npm start
```

#### Workspace Commands

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

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Tiger API Configuration
TIGER_CLIENT_ID=your_client_id
TIGER_PRIVATE_KEY=your_private_key
TIGER_ACCOUNT=your_account_id
TIGER_SANDBOX=true

# Database Configuration
DATABASE_URL=postgresql://tiger:tiger@localhost:5432/tiger_mcp

# Application Configuration
DEBUG=true
LOG_LEVEL=info
```

## MCP Integration

### Using with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "tiger-mcp": {
      "command": "uv",
      "args": ["run", "--package", "mcp-server", "python", "-m", "mcp_server.main"],
      "cwd": "/path/to/tiger-mcp",
      "env": {
        "TIGER_CLIENT_ID": "your_client_id",
        "TIGER_PRIVATE_KEY": "your_private_key",
        "TIGER_ACCOUNT": "your_account_id"
      }
    }
  }
}
```

### Available Tools

- `get_account_info` - Account details and balances
- `get_portfolio` - Portfolio positions and P&L
- `get_market_data` - Real-time quotes and market data
- `place_order` - Execute trading orders
- `get_order_status` - Check order status
- `scan_market` - Market scanning and screening
- `get_historical_data` - Historical price data
- `calculate_indicators` - Technical analysis indicators

## Development

### Project Structure

- **packages/mcp-server/**: Core MCP server implementation using FastMCP
- **packages/dashboard-api/**: FastAPI REST API for web dashboard  
- **packages/database/**: Database models and migration scripts
- **packages/shared/**: Shared utilities and configurations
- **docker/**: Docker configurations for all services
- **config/**: Configuration files and templates
- **tests/**: Test files and integration tests
- **reports/**: Validation reports and security scans

### Testing

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
# cd dashboard-frontend && npm test  # Not implemented yet
```

### Deployment

Production deployment using Docker:

```bash
docker-compose -f docker/docker-compose.prod.yml up -d
```

## Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICK_START_GUIDE.md) - Get up and running in 30 minutes
- [Tiger Authentication Setup](docs/TIGER_AUTHENTICATION_SETUP.md) - Complete auth configuration
- [Migration Guide](docs/MIGRATION_GUIDE.md) - Upgrade from previous versions

### 🤖 Claude Code Integration
- **[Claude Code Integration Guide](docs/CLAUDE_CODE_INTEGRATION.md)** - Complete setup and configuration guide for Claude Code
- **[Claude Code Quick Start](docs/CLAUDE_CODE_QUICK_START.md)** - Get Tiger MCP working with Claude Code in 15 minutes
- **[Usage Examples & Workflows](docs/CLAUDE_CODE_EXAMPLES.md)** - Practical trading and analysis examples
- **[Security & Best Practices](docs/CLAUDE_CODE_SECURITY.md)** - Security guidelines and production deployment
- **[Troubleshooting Guide](docs/CLAUDE_CODE_TROUBLESHOOTING.md)** - Common issues and solutions for Claude Code integration

### 📚 Reference Guides
- [API Reference](docs/API_REFERENCE.md) - Complete MCP tools and REST API documentation
- [Docker Guide](docs/DOCKER.md) - Comprehensive containerization guide
- [Tiger Broker Authentication](docs/TIGER_BROKER_AUTHENTICATION.md) - Authentication system details

### 🏭 Operations
- [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md) - Production setup and best practices
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [System Validation Report](reports/validation/FINAL_VALIDATION_REPORT.md) - Current system status

### 🔧 Package Documentation
- [MCP Server](packages/mcp-server/README.md) - MCP server implementation
- [Database Package](packages/database/README.md) - Database models and migrations
- [Shared Security](packages/shared/README.md) - Encryption and security services
- [Account Management](packages/shared/README_ACCOUNT_SERVICE.md) - Account service details
- [Dashboard API](packages/dashboard-api/README.md) - REST API backend

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

For issues and questions:
- Create an issue on GitHub
- Check the [documentation](docs/)
- Review the [Tiger API documentation](https://www.itiger.com/openapi)