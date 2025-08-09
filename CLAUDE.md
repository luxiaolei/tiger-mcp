# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tiger MCP is a comprehensive Model Context Protocol (MCP) server system that bridges Claude AI with Tiger Brokers trading platform. The project uses a **UV workspace architecture** with **process isolation** to solve Tiger SDK's single-account limitation through dedicated worker processes.

## Core Architecture

### UV Workspace Structure
```
packages/
├── mcp-server/          # FastMCP server with 22 trading tools
├── dashboard-api/       # FastAPI REST backend (optional)  
├── database/           # SQLAlchemy models and Alembic migrations
└── shared/             # Common utilities, encryption, security
```

### Key Architectural Concepts

1. **Process Pool Architecture**: Each Tiger account runs in an isolated worker process to circumvent SDK limitations. The `TigerProcessPool` manages worker lifecycle and load balancing.

2. **Multi-Account Routing**: The `AccountRouter` in `shared/` intelligently routes operations to appropriate accounts based on permissions and load balancing strategies.

3. **FastMCP Integration**: Tools are registered with FastMCP framework via `TigerFastMCPServer.register_tools()`. All 22 tools are categorized as data, info, account, and trading tools.

4. **Security Layer**: AES-256-GCM encryption for credentials, JWT tokens for authentication, and comprehensive audit logging through the `shared/security.py` module.

## Development Commands

### UV Workspace Commands
```bash
# Install dependencies across workspace
uv sync

# Run MCP server in development
uv run --package mcp-server python -m mcp_server

# Run specific package commands  
uv run --package mcp-server python -m mcp_server.cli --help
uv run --package dashboard-api uvicorn dashboard_api.main:app --reload

# Add dependencies to specific packages
uv add --package mcp-server "new-dependency>=1.0.0"
```

### Docker Operations (via Makefile)
```bash
# Development environment
make dev-up              # Start all development services
make dev-down           # Stop development services 
make dev-logs           # View logs (add SERVICE=name for specific service)
make health             # Check service health endpoints

# Production environment
make prod-up            # Start production services
make prod-build-up      # Build and start production
```

### Testing
```bash
# Run all tests across workspace
uv run pytest

# Test specific components
uv run pytest packages/mcp-server/tests/
uv run pytest tests/test_integration_scenarios.py

# Run with coverage
uv run pytest --cov=packages --cov-report=html
```

### Code Quality
```bash
# Format and lint (configured in pyproject.toml)
uv run black .
uv run isort .
uv run mypy packages/

# Security scanning
uv run bandit -r packages/
```

### Database Operations
```bash
# Run migrations
make db-migrate

# Access PostgreSQL shell
make db-shell

# Backup/restore database
make db-backup
make db-restore BACKUP=backup-file.sql
```

## Key Integration Points

### MCP Tools Registration
Tools are dynamically imported and registered in `packages/mcp-server/src/mcp_server/main.py:_register_tools()`. Each tool follows FastMCP patterns with proper type hints and error handling.

### Process Pool Management
The `TigerProcessPool` in `packages/mcp-server/src/mcp_server/tiger_process_pool.py` manages worker processes. Each process loads the Tiger SDK at a fixed path and handles one account exclusively.

### Account Management
Multi-account support is handled through:
- `shared/account_manager.py`: CRUD operations for Tiger accounts
- `shared/account_router.py`: Intelligent routing and load balancing  
- `shared/token_manager.py`: Automated token refresh for all accounts

### Configuration Management
Configuration is centralized in `shared/config.py` with environment-specific overrides. The `ConfigManager` handles loading from files, environment variables, and defaults.

## Important Implementation Details

### Tiger SDK Integration
The Tiger SDK is loaded from `references/openapi-python-sdk/` and requires specific initialization patterns. Worker processes must load the SDK before handling any operations.

### Database Session Management
Use `get_session()` from `database/engine.py` for async session management. All database operations should use proper transaction contexts via `get_transaction()`.

### Security Considerations
- Never commit real credentials - use `.env.template` as reference
- All sensitive data goes through `EncryptionService` in `shared/encryption.py`
- API operations require proper authentication via `SecurityService`

### Error Handling
All MCP tools follow consistent error handling patterns with proper logging via loguru. Exceptions are wrapped in appropriate domain-specific error types.

### Testing Strategy
- Unit tests for individual components
- Integration tests in `tests/` directory
- Performance tests for multi-account scenarios
- Mock Tiger API responses for consistent testing

## Configuration

### Environment Setup
1. Copy `.env.template` to `.env`
2. Configure Tiger API credentials (use sandbox for development)
3. Set up database connection (or use Docker services)

### Claude Desktop Integration
Add to `~/.config/claude/config.json`:
```json
{
  "mcpServers": {
    "tiger-mcp": {
      "command": "uv",
      "args": ["run", "--package", "mcp-server", "python", "-m", "mcp_server.main"],
      "cwd": "/path/to/tiger-mcp"
    }
  }
}
```

## Security Architecture

The system implements multi-layer security:
- Transport: TLS 1.3 for all communications
- Authentication: JWT tokens with configurable expiration
- Authorization: Role-based access with account-specific permissions  
- Data: AES-256-GCM encryption for sensitive credentials
- Audit: Comprehensive logging of all security events

## Performance Considerations

- Process pool workers are created on-demand with configurable limits
- Database connections use async SQLAlchemy with connection pooling
- Redis caching layer for frequently accessed market data
- Rate limiting prevents Tiger API quota exhaustion
- Load balancing across multiple accounts for high-throughput operations