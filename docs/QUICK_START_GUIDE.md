# Tiger MCP Quick Start Guide

Get up and running with the Tiger MCP system in under 30 minutes. This guide covers everything from initial setup to your first API call.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **Docker and Docker Compose** installed
- **UV package manager** ([installation guide](https://docs.astral.sh/uv/))
- **Tiger Brokers account** with API access approved
- **Basic knowledge of trading** and financial markets

## Step 1: Get Your Tiger API Credentials

### 1.1 Apply for Tiger API Access

1. Log into your Tiger Brokers account
2. Navigate to **API** or **Developer** section
3. Apply for API access (approval takes 1-3 business days)
4. Once approved, download your credential files:
   - `tiger_openapi_config.properties`
   - `tiger_openapi_token.properties`

### 1.2 Understand Your Credentials

Your `tiger_openapi_config.properties` should look like this:
```properties
tiger_id=20154747
account=67686635
license=TBHK  # Your broker license (TBHK, TBSG, TBNZ, etc.)
env=PROD      # PROD for live trading, SANDBOX for testing
private_key_pk1=-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDj...
-----END RSA PRIVATE KEY-----
```

**Important**: Keep these files secure and never commit them to version control.

## Step 2: Clone and Setup the Project

```bash
# Clone the repository
git clone <repository-url>
cd tiger-mcp

# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup environment
cp .env.example .env
```

## Step 3: Configure Your Environment

Edit the `.env` file with your settings:

```bash
# Tiger API Configuration (if not using properties files)
TIGER_CLIENT_ID=20154747
TIGER_ACCOUNT=67686635
TIGER_LICENSE=TBHK
TIGER_SANDBOX=false

# Database Configuration
DATABASE_URL=postgresql://tiger:tiger@localhost:5432/tiger_mcp

# MCP Server Configuration
MCP_SERVER_PORT=8000
LOG_LEVEL=INFO
```

## Step 4: Choose Your Setup Method

### Option A: Docker Setup (Recommended for Beginners)

**Fastest way to get started:**

```bash
# Copy your Tiger properties files
cp /path/to/tiger_openapi_config.properties .
cp /path/to/tiger_openapi_token.properties .

# Start everything with Docker
docker-compose up -d

# Check service status
docker-compose ps
```

**Services will be available at:**
- MCP Server: http://localhost:8000
- Dashboard API: http://localhost:8001
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Option B: Development Setup

**For developers who want to run components individually:**

```bash
# Install workspace dependencies
uv sync

# Start database services
docker-compose up -d postgres redis

# Run database migrations
uv run --package database python manage_db.py migrate

# Start MCP server (in one terminal)
uv run --package mcp-server python run_server.py

# Start dashboard API (in another terminal)  
uv run --package dashboard-api uvicorn dashboard_api.main:app --reload
```

## Step 5: Test Your Setup

### 5.1 Health Check

```bash
# Check if services are running
curl http://localhost:8000/health
curl http://localhost:8001/health

# Or use the provided script
make health
```

### 5.2 Add Your Tiger Account

Using the MCP CLI (if available):
```bash
# Add your account
tiger-mcp add-account \
  --name "My Trading Account" \
  --from-properties ./tiger_openapi_config.properties
```

Or using the Python API:
```python
from shared import get_account_manager
from database.models.accounts import TigerLicense, TigerEnvironment

async def add_account():
    manager = get_account_manager()
    
    account = await manager.create_account_from_properties(
        account_name="My Trading Account",
        properties_path="./",  # Directory with .properties files
        is_default_trading=True,
        is_default_data=True
    )
    
    print(f"Account added: {account.account_name} ({account.id})")

# Run it
import asyncio
asyncio.run(add_account())
```

## Step 6: Make Your First API Call

### 6.1 Using MCP Tools (Python)

```python
from mcp_server.tools import tiger_get_quote, tiger_get_account_info

async def first_calls():
    # Get a stock quote
    quote_response = await tiger_get_quote("AAPL")
    if quote_response.success:
        price = quote_response.data["latest_price"]
        print(f"AAPL current price: ${price}")
    else:
        print(f"Error getting quote: {quote_response.error}")
    
    # Get account information
    account_response = await tiger_get_account_info()
    if account_response.success:
        balance = account_response.data["net_liquidation"]
        print(f"Account balance: ${balance}")
    else:
        print(f"Error getting account info: {account_response.error}")

import asyncio
asyncio.run(first_calls())
```

### 6.2 Using Claude Desktop Integration

Add to your Claude Desktop configuration (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "tiger-mcp": {
      "command": "python",
      "args": ["/path/to/tiger-mcp/packages/mcp-server/run_server.py"],
      "env": {
        "TIGER_USE_PROPERTIES": "true",
        "TIGER_PROPERTIES_PATH": "/path/to/tiger-mcp"
      }
    }
  }
}
```

Then ask Claude:
- "Get me a quote for Apple stock"
- "What's my current account balance?"
- "Show me my portfolio positions"

## Step 7: Explore Available Features

### Market Data Tools
```bash
# Get real-time quotes
curl -X POST http://localhost:8000/mcp/tools/tiger_get_quote \
  -H "Content-Type: application/json" \
  -d '{"symbol": "TSLA"}'

# Get historical data
curl -X POST http://localhost:8000/mcp/tools/tiger_get_kline \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "period": "1d", "count": 30}'
```

### Account Management
```bash
# List all accounts
curl -X POST http://localhost:8000/mcp/tools/tiger_list_accounts

# Get account status
curl -X POST http://localhost:8000/mcp/tools/tiger_get_account_status
```

### Trading Tools (⚠️ Use with caution in production)
```bash
# Get current positions
curl -X POST http://localhost:8000/mcp/tools/tiger_get_positions

# Get orders
curl -X POST http://localhost:8000/mcp/tools/tiger_get_orders
```

## Common Issues and Solutions

### Issue 1: "Tiger API connection failed"
**Cause**: Invalid credentials or expired token
**Solution**: 
1. Verify your `.properties` files are correct
2. Check if your Tiger API access is approved
3. Ensure you're using the right environment (PROD vs SANDBOX)

### Issue 2: "Database connection error"
**Cause**: PostgreSQL not running or wrong connection string
**Solution**:
```bash
# Check if database is running
docker-compose ps postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
uv run --package database python manage_db.py migrate
```

### Issue 3: "Import errors when running Python scripts"
**Cause**: Python path or dependency issues
**Solution**:
```bash
# Reinstall dependencies
uv sync --reinstall

# Run from project root
cd /path/to/tiger-mcp
uv run --package mcp-server python -m mcp_server.main
```

### Issue 4: "Rate limit exceeded"
**Cause**: Too many API calls
**Solution**: Wait 1 minute and retry. Consider implementing backoff in your code.

## Next Steps

Now that you have Tiger MCP running:

1. **Explore the Documentation**:
   - [API Reference](./API_REFERENCE.md) - Complete API documentation
   - [Tiger Authentication Guide](./TIGER_AUTHENTICATION_SETUP.md) - Advanced auth setup
   - [Docker Guide](./DOCKER.md) - Production deployment

2. **Build Your First Application**:
   - Create a portfolio tracker
   - Build trading alerts
   - Develop market analysis tools

3. **Production Deployment**:
   - Follow the [Production Deployment Guide](./PRODUCTION_DEPLOYMENT.md)
   - Set up monitoring and logging
   - Configure security and backups

## Support and Resources

- **Documentation**: `/docs` directory
- **Examples**: `/packages/*/example_usage.py` files
- **Tiger API Docs**: https://www.itiger.com/openapi
- **Issues**: Create GitHub issues for bugs or feature requests

## Security Reminders

- ✅ **DO**: Use SANDBOX environment for testing
- ✅ **DO**: Keep your private keys secure
- ✅ **DO**: Use proper error handling in production
- ❌ **DON'T**: Commit credentials to version control
- ❌ **DON'T**: Use production accounts for development
- ❌ **DON'T**: Place real orders without proper safeguards

## Quick Reference Card

```bash
# Essential Commands
docker-compose up -d              # Start all services
docker-compose down              # Stop all services
make health                      # Check service health
uv run --package mcp-server python run_server.py  # Start MCP server
uv run --package database python manage_db.py migrate  # Run migrations

# Testing Commands
curl http://localhost:8000/health  # MCP server health
curl http://localhost:8001/health  # Dashboard API health
```

Congratulations! You now have a fully functional Tiger MCP system. Start building your trading applications! 🚀