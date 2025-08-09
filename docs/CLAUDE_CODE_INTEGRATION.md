# Claude Code Integration Guide for Tiger MCP Server

A comprehensive guide for integrating the Tiger MCP server with Claude Code, enabling AI-powered trading operations and market analysis through natural language commands.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation Methods](#installation-methods)
4. [Configuration](#configuration)
5. [Authentication Setup](#authentication-setup)
6. [Testing and Validation](#testing-and-validation)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)
9. [Security Considerations](#security-considerations)
10. [Advanced Configuration](#advanced-configuration)
11. [Best Practices](#best-practices)

## Overview

The Tiger MCP server provides comprehensive trading capabilities through the Model Context Protocol (MCP), allowing Claude Code to interact with Tiger Brokers' API for:

- **Market Data**: Real-time quotes, historical data, market scanning
- **Trading Operations**: Order placement, portfolio management, position tracking  
- **Account Management**: Account info, balances, transaction history
- **Analysis Tools**: Technical indicators, market research, risk analysis

### Architecture

```
Claude Code ←→ Tiger MCP Server ←→ Tiger Brokers API
     ↑                ↑                    ↑
  Natural         MCP Protocol        Trading Data
 Language         Communication       & Operations
Commands
```

## Prerequisites

### System Requirements

- **Python**: 3.11+ (required for Tiger MCP server)
- **Claude Code**: Latest version (`npm install -g @anthropic-ai/claude-code`)
- **Tiger Brokers Account**: Active trading account with API access
- **Operating System**: Windows, macOS, or Linux

### Dependencies

```bash
# Check Python version
python --version  # Should be 3.11+

# Check Claude Code installation
claude --version

# Verify Node.js (required for Claude Code)
node --version    # Should be 18+
npm --version
```

## Installation Methods

### Method 1: Direct Server Path (Recommended)

This method runs the Tiger MCP server directly from your local installation.

#### Step 1: Clone and Setup Tiger MCP

```bash
# Clone the repository
git clone <your-repository>
cd tiger-mcp

# Install dependencies using UV
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install UV if needed
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your Tiger API credentials
```

#### Step 2: Add MCP Server to Claude Code

```bash
# Add the Tiger MCP server using stdio transport
claude mcp add tiger-mcp \
  --env TIGER_CLIENT_ID=your_client_id \
  --env TIGER_PRIVATE_KEY=your_private_key \
  --env TIGER_ACCOUNT=your_account \
  --env TIGER_SANDBOX=true \
  -- uv run --package mcp-server python mcp-server/server.py
```

### Method 2: Using Docker Container

For containerized deployment with additional services (database, dashboard):

#### Step 1: Build and Start Services

```bash
cd tiger-mcp

# Start all services including MCP server
docker-compose up -d

# Get the container name for MCP server
docker ps | grep mcp-server
```

#### Step 2: Add Docker-based MCP Server

```bash
# Add MCP server using docker exec
claude mcp add tiger-mcp-docker \
  --env TIGER_CLIENT_ID=your_client_id \
  --env TIGER_PRIVATE_KEY=your_private_key \
  --env TIGER_ACCOUNT=your_account \
  -- docker exec -i tiger-mcp-mcp-server-1 python server.py
```

### Method 3: SSE/HTTP Transport (Production)

For production deployments with network-accessible MCP server:

#### Step 1: Deploy MCP Server with HTTP Transport

```bash
# Start MCP server with SSE transport (requires additional setup)
uv run --package mcp-server python mcp-server/server.py --transport sse --port 8080
```

#### Step 2: Add Remote MCP Server

```bash
# Add SSE-based MCP server
claude mcp add --transport sse tiger-mcp-sse \
  --env Authorization="Bearer your-api-token" \
  https://your-domain.com:8080/sse
```

## Configuration

### Environment Variables

The Tiger MCP server supports multiple configuration methods:

#### Primary Configuration (.env file)
```bash
# Tiger API Credentials
TIGER_CLIENT_ID=your_tiger_client_id
TIGER_PRIVATE_KEY=your_private_key_content
TIGER_ACCOUNT=your_account_number
TIGER_SANDBOX=true  # Use false for production
TIGER_LICENSE=TBHK  # or TBNZ, TBSG depending on your account

# Optional: Database configuration for multi-account support
DATABASE_URL=postgresql://user:pass@localhost:5432/tiger_mcp
TIGER_DEFAULT_ACCOUNT_ID=uuid-of-default-account

# Logging
LOG_LEVEL=INFO
```

#### Properties Files (Legacy Support)
```bash
# tiger.properties (alternative to env vars)
tiger_id=your_client_id
account=your_account
private_key=your_private_key_content
sandbox=true
license=TBHK
```

### Server Scopes

Choose the appropriate scope for your installation:

#### Project Scope (Team Collaboration)
```bash
# Adds server to .mcp.json for team sharing
claude mcp add tiger-mcp -s project /path/to/server
```

#### User Scope (Personal Use)
```bash
# Available across all your projects
claude mcp add tiger-mcp -s user /path/to/server
```

#### Local Scope (Current Project Only)
```bash
# Default - local to current project
claude mcp add tiger-mcp -s local /path/to/server
```

### Configuration Verification

```bash
# List all configured MCP servers
claude mcp list

# Get details for Tiger MCP server
claude mcp get tiger-mcp

# Test connection
claude -p "Test Tiger MCP connection" --mcp-config tiger-mcp.json
```

## Authentication Setup

### Tiger API Credentials

#### Step 1: Obtain API Credentials

1. **Log into Tiger Brokers**: Visit your trading platform
2. **API Management**: Navigate to Account → API Management
3. **Create API Key**: Generate new API credentials
4. **Download Private Key**: Save the private key file securely
5. **Note Client ID**: Copy your client ID and account number

#### Step 2: Private Key Formats

Tiger MCP supports both PK1 and PK8 private key formats:

```python
# PK1 Format (PKCS#1)
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA...
-----END RSA PRIVATE KEY-----

# PK8 Format (PKCS#8) 
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQE...
-----END PRIVATE KEY-----
```

#### Step 3: Environment Configuration

**Option A: Environment Variables**
```bash
export TIGER_CLIENT_ID="your_client_id"
export TIGER_PRIVATE_KEY="$(cat your_private_key.pem)"
export TIGER_ACCOUNT="your_account_number"
export TIGER_SANDBOX="true"  # false for production
export TIGER_LICENSE="TBHK"   # TBHK, TBNZ, TBSG
```

**Option B: Properties File**
```bash
# Create tiger.properties file
cat > tiger.properties << EOF
tiger_id=your_client_id
account=your_account_number
private_key=$(cat your_private_key.pem)
sandbox=true
license=TBHK
EOF
```

### Multi-Account Setup (Advanced)

For users with multiple Tiger accounts:

#### Step 1: Database Setup

```bash
# Start PostgreSQL (if using Docker)
docker-compose up -d postgres

# Run database migrations
uv run --package database python -m database.migrations.run
```

#### Step 2: Add Accounts via Dashboard

```bash
# Start dashboard API
uv run --package dashboard-api uvicorn dashboard_api.main:app --reload --port 8000

# Access dashboard at http://localhost:8000
# Add multiple accounts through the web interface
```

#### Step 3: Configure Default Account

```bash
# Set default account ID in environment
export TIGER_DEFAULT_ACCOUNT_ID="uuid-from-dashboard"
```

## Testing and Validation

### Basic Connection Test

```bash
# Test basic MCP server functionality
claude -p "Get Tiger MCP configuration and test connection"
```

### Available Tools Verification

```bash
# List all available Tiger MCP tools
claude -p "What Tiger MCP tools are available?"
```

Expected tools should include:
- `mcp__tiger-mcp__get_account_info`
- `mcp__tiger-mcp__get_portfolio` 
- `mcp__tiger-mcp__get_market_data`
- `mcp__tiger-mcp__place_order`
- `mcp__tiger-mcp__get_order_status`
- `mcp__tiger-mcp__scan_market`
- `mcp__tiger-mcp__get_historical_data`
- `mcp__tiger-mcp__validate_tiger_connection`

### Comprehensive Validation

```bash
# Run validation sequence
claude -p "Please run a comprehensive validation of Tiger MCP server:
1. Check configuration
2. Validate API connection  
3. Test market data retrieval for AAPL
4. Get account information
5. Verify portfolio access"
```

### Manual Tool Testing

```bash
# Test specific tools directly
claude -p "Use mcp__tiger-mcp__validate_tiger_connection to test the connection"
claude -p "Use mcp__tiger-mcp__get_account_info to show my account details"
claude -p "Use mcp__tiger-mcp__get_market_data with symbols ['AAPL', 'MSFT'] to get quotes"
```

## Usage Examples

### Market Analysis

```bash
# Get market overview
claude -p "Get current market data for AAPL, MSFT, GOOGL and analyze the trends"

# Market scanning
claude -p "Scan the market for top gainers in the US market and show the top 10"

# Historical analysis
claude -p "Get 30 days of historical data for TSLA and identify key support/resistance levels"
```

### Portfolio Management

```bash
# Portfolio overview
claude -p "Show my current portfolio with positions, P&L, and performance metrics"

# Risk analysis
claude -p "Analyze my portfolio risk exposure and suggest any needed rebalancing"

# Account summary
claude -p "Provide a comprehensive account summary including cash, buying power, and overall performance"
```

### Trading Operations

⚠️ **WARNING**: Only use trading commands in sandbox/paper trading mode initially.

```bash
# Order placement (SANDBOX ONLY)
claude -p "Place a limit buy order for 100 shares of AAPL at $150"

# Order monitoring
claude -p "Check the status of my recent orders and show any fills or cancellations"

# Position management
claude -p "Show all my open positions with current market values and unrealized P&L"
```

### Advanced Workflows

```bash
# Multi-step analysis
claude -p "Perform a complete investment analysis:
1. Get top 5 performers from market scan
2. Analyze historical data for each
3. Check my portfolio for any existing positions
4. Suggest potential trades based on analysis"

# Risk monitoring
claude -p "Monitor my portfolio and alert me to any positions with >5% daily losses"

# Research integration
claude -p "Research NVDA: get current price, 1-year chart, recent news sentiment, and technical indicators"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Server Connection Failed

**Symptoms**:
```
Error: Tiger client not initialized
Error: Failed to initialize Tiger clients
```

**Solutions**:
```bash
# Verify credentials
claude -p "Use mcp__tiger-mcp__get_tiger_config to check configuration"

# Test connection
claude -p "Use mcp__tiger-mcp__validate_tiger_connection"

# Check environment variables
env | grep TIGER

# Verify server is running
ps aux | grep mcp-server
```

#### 2. Authentication Errors

**Symptoms**:
```
Error: Invalid credentials
Error: Failed to authenticate with Tiger API
```

**Solutions**:
```bash
# Verify API credentials are correct
# Check Tiger Brokers account status
# Ensure API access is enabled
# Verify private key format (PK1 vs PK8)

# Test with minimal config
export TIGER_CLIENT_ID="your_id"
export TIGER_PRIVATE_KEY="$(cat key.pem)"
export TIGER_ACCOUNT="your_account"
export TIGER_SANDBOX="true"
```

#### 3. Market Data Issues

**Symptoms**:
```
Error: Failed to get market data
Error: Quote client not initialized
```

**Solutions**:
```bash
# Check market hours (US: 9:30 AM - 4:00 PM ET)
# Verify symbol format (use correct ticker symbols)
# Test with well-known symbols like AAPL, MSFT

# Enable detailed logging
export LOG_LEVEL=DEBUG
```

#### 4. Tool Permissions

**Symptoms**:
```
Error: MCP tool not allowed
Permission denied for tool execution
```

**Solutions**:
```bash
# Explicitly allow MCP tools
claude -p "Test connection" \
  --allowedTools "mcp__tiger-mcp__get_account_info,mcp__tiger-mcp__get_market_data"

# Check Claude Code settings
claude config get permissions
```

#### 5. Database Connection Issues (Multi-Account)

**Symptoms**:
```
Error: Could not connect to database
Error: Account not found
```

**Solutions**:
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Verify database URL
echo $DATABASE_URL

# Run migrations
uv run --package database python -m database.migrations.run

# Check account exists
psql $DATABASE_URL -c "SELECT id, account_name FROM accounts;"
```

### Debugging Tools

#### Enable Detailed Logging

```bash
# Set debug logging
export LOG_LEVEL=DEBUG

# Restart MCP server with debug
claude mcp remove tiger-mcp
claude mcp add tiger-mcp --env LOG_LEVEL=DEBUG /path/to/server
```

#### MCP Server Diagnostics

```bash
# Check server health
claude -p "Use mcp__tiger-mcp__validate_tiger_connection to run diagnostics"

# Get configuration details
claude -p "Use mcp__tiger-mcp__get_tiger_config to show current settings"

# Test API endpoints individually
curl -X POST https://api.tiger.com/v1/authenticate \
  -H "Content-Type: application/json" \
  -d '{"client_id":"your_id"}'
```

#### Network and Connectivity

```bash
# Test network connectivity
ping api.tiger.com
nslookup api.tiger.com

# Check proxy settings (if applicable)
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Test Python SSL/TLS
python -c "import ssl; print(ssl.OPENSSL_VERSION)"
```

### Log Analysis

#### Common Log Patterns

```bash
# Successful initialization
"Tiger API clients initialized successfully for account"

# Authentication success  
"Loaded Tiger config from"

# API call success
"Request successful: GET /v1/account/assets"

# Common errors
"Failed to authenticate"
"Connection timeout" 
"Invalid symbol"
"Market closed"
```

#### Log File Locations

```bash
# Docker logs
docker logs tiger-mcp-mcp-server-1

# Local development
tail -f logs/mcp-server.log

# Claude Code logs
~/.claude/logs/
```

## Security Considerations

### Credential Security

#### 1. Private Key Protection

```bash
# Set proper file permissions
chmod 600 your_private_key.pem

# Use environment variables instead of config files
export TIGER_PRIVATE_KEY="$(cat your_private_key.pem)"

# Avoid logging private keys
grep -v "private_key" logs/mcp-server.log
```

#### 2. Environment Variable Security

```bash
# Use .env files (not committed to git)
echo ".env" >> .gitignore

# In production, use secure secret management
# Examples: AWS Secrets Manager, HashiCorp Vault, etc.

# Rotate API keys regularly
# Monitor API key usage through Tiger Brokers console
```

#### 3. Network Security

```bash
# Use HTTPS for all API communications
# Enable SSL/TLS verification
export CURL_CA_BUNDLE=/path/to/ca-certificates.crt

# Whitelist IP addresses in Tiger Brokers console
# Use VPN or secure networks for trading operations
```

### Production Security Checklist

- [ ] **API Keys**: Stored securely, not in code or logs
- [ ] **Private Keys**: Proper file permissions (600)
- [ ] **Network**: HTTPS only, IP whitelisting enabled
- [ ] **Logging**: No sensitive data in logs
- [ ] **Access Control**: MCP server access restricted
- [ ] **Monitoring**: API usage monitoring enabled
- [ ] **Backup**: Secure backup of credentials
- [ ] **Rotation**: Regular key rotation schedule

### Sandbox vs Production

#### Always Start with Sandbox

```bash
# Sandbox configuration
export TIGER_SANDBOX=true
export TIGER_LICENSE=TBHK

# Verify sandbox mode
claude -p "Use mcp__tiger-mcp__get_tiger_config to confirm sandbox environment"
```

#### Production Migration

```bash
# Only after thorough testing
export TIGER_SANDBOX=false

# Production-specific settings
export TIGER_LICENSE=TBHK  # or TBNZ, TBSG
export LOG_LEVEL=WARN      # Reduce logging in production

# Additional production safeguards
export TIGER_MAX_ORDER_SIZE=1000
export TIGER_DAILY_LOSS_LIMIT=5000
```

## Advanced Configuration

### Custom Tool Allowlist

```bash
# Restrict to specific tools only
claude -p "Test market data" \
  --allowedTools "mcp__tiger-mcp__get_market_data,mcp__tiger-mcp__get_account_info" \
  --mcp-config tiger-config.json
```

### Performance Optimization

#### Connection Pooling

```python
# In server configuration
TIGER_CONNECTION_POOL_SIZE=5
TIGER_CONNECTION_TIMEOUT=30
TIGER_RETRY_ATTEMPTS=3
```

#### Caching Configuration

```bash
# Enable data caching
export TIGER_CACHE_ENABLED=true
export TIGER_CACHE_TTL=60  # seconds
export REDIS_URL=redis://localhost:6379
```

### Multi-Region Setup

```bash
# US Markets
export TIGER_LICENSE=TBHK
export TIGER_MARKET_TIMEZONE=America/New_York

# Hong Kong Markets
export TIGER_LICENSE=TBHK
export TIGER_MARKET_TIMEZONE=Asia/Hong_Kong

# Singapore Markets  
export TIGER_LICENSE=TBSG
export TIGER_MARKET_TIMEZONE=Asia/Singapore
```

### Integration with Other MCP Servers

```bash
# Add multiple MCP servers for comprehensive analysis
claude mcp add github-mcp /path/to/github-server
claude mcp add news-mcp /path/to/news-server
claude mcp add economic-data-mcp /path/to/economic-server

# Use multiple servers in single query
claude -p "Get AAPL market data, recent GitHub commits related to Apple, latest news about Apple, and economic indicators affecting tech stocks"
```

## Best Practices

### Development Workflow

1. **Start with Sandbox**: Always test with sandbox environment
2. **Incremental Testing**: Test each tool individually before complex workflows
3. **Error Handling**: Implement proper error handling and logging
4. **Documentation**: Keep configuration documented and version controlled
5. **Security Review**: Regular security audits and key rotation

### Trading Safety

1. **Position Limits**: Set maximum position sizes
2. **Loss Limits**: Implement daily/monthly loss limits  
3. **Order Validation**: Always validate orders before execution
4. **Market Hours**: Respect market hours and holidays
5. **Risk Management**: Implement proper risk management rules

### Performance Monitoring

```bash
# Monitor API usage
claude -p "Show me my API usage statistics and rate limits"

# Track performance metrics
export OTEL_METRICS_EXPORTER=prometheus
export CLAUDE_CODE_ENABLE_TELEMETRY=1

# Regular health checks
claude -p "Run Tiger MCP health check and show system status"
```

### Maintenance Schedule

- **Daily**: Check connection health, review logs
- **Weekly**: Verify account balances, review trading activity
- **Monthly**: Rotate API keys, update dependencies, backup configurations
- **Quarterly**: Security audit, performance review, update documentation

## Support and Resources

### Documentation Links

- [Tiger Brokers API Documentation](https://www.itiger.com/openapi)
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Model Context Protocol Specification](https://modelcontextprotocol.io)

### Project Resources

- [Tiger MCP GitHub Repository](../README.md)
- [API Reference](API_REFERENCE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Migration Guide](MIGRATION_GUIDE.md)

### Community and Support

- **GitHub Issues**: Report bugs and request features
- **Discord Community**: Real-time community support
- **Documentation Wiki**: Community-maintained guides and examples

---

## Quick Reference Commands

```bash
# Essential Commands
claude mcp list                                    # List all MCP servers
claude mcp get tiger-mcp                          # Get Tiger MCP details
claude -p "Test Tiger connection"                 # Quick connection test
claude -p "Get account info"                      # Account information
claude -p "Get market data for AAPL"             # Market data
claude -p "Show portfolio"                        # Portfolio overview

# Troubleshooting
claude -p "Use mcp__tiger-mcp__validate_tiger_connection"  # Connection test
claude -p "Use mcp__tiger-mcp__get_tiger_config"          # Configuration check
export LOG_LEVEL=DEBUG                                      # Debug logging
docker logs tiger-mcp-mcp-server-1                        # Container logs

# Configuration
claude config list                                # Claude Code settings
claude config set permissions.allow "mcp__*"     # Allow all MCP tools
claude mcp add tiger-mcp -s project /path        # Add project-scoped server
```

This comprehensive integration guide should get you up and running with Tiger MCP server in Claude Code. Remember to always start with sandbox mode and test thoroughly before any production trading activities.