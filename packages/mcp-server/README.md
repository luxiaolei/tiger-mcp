# Tiger MCP Server

A FastMCP server providing Tiger Brokers API integration with comprehensive MCP (Model Context Protocol) tools for trading, account management, market data, and more.

## Features

- **Complete Tiger Brokers API Integration**: Access to trading, market data, account management, and financial information
- **MCP Protocol Support**: Full compliance with Model Context Protocol specifications
- **Multiple Transport Methods**: Support for both stdio and Server-Sent Events (SSE) transports
- **Process Pool Management**: Isolated worker processes for API calls with load balancing
- **Account Management**: Multi-account support with token refresh and routing
- **Comprehensive Configuration**: Environment-based configuration with validation
- **Health Monitoring**: Built-in health checks and monitoring capabilities
- **Production Ready**: Logging, error handling, and graceful shutdown

## Quick Start

### 1. Installation

```bash
# Navigate to the package directory
cd packages/mcp-server

# Install in development mode
pip install -e .
```

### 2. Configuration

Create a `.env` file in the package root:

```env
# Tiger API Configuration
TIGER_SANDBOX_MODE=true
TIGER_DEFAULT_MARKET=US
TIGER_REQUEST_TIMEOUT=30

# Database Configuration  
TIGER_MCP_DATABASE_URL=sqlite:///tiger_mcp.db

# Server Configuration
TIGER_MCP_SERVER_HOST=localhost
TIGER_MCP_SERVER_PORT=8000
TIGER_MCP_SERVER_LOG_LEVEL=INFO

# Process Pool Configuration
TIGER_MCP_PROCESS_MIN_WORKERS=2
TIGER_MCP_PROCESS_MAX_WORKERS=8
TIGER_MCP_PROCESS_TARGET_WORKERS=4

# Security Configuration
TIGER_MCP_SECURITY_ENABLE_TOKEN_VALIDATION=true
TIGER_MCP_SECURITY_TOKEN_REFRESH_THRESHOLD=300
```

### 3. Run the Server

#### Using the simple startup script:

```bash
# Run with stdio transport (default)
python run_server.py

# Run with SSE transport
python run_server.py --transport sse --host 0.0.0.0 --port 8000

# Run in development mode
python run_server.py --environment development
```

#### Using the CLI:

```bash
# Run with stdio transport
tiger-mcp-server

# Run with SSE transport  
tiger-mcp-server --transport sse --host 0.0.0.0 --port 8000

# Check server health
tiger-mcp-server health

# Validate configuration
tiger-mcp-server validate-config --show-config

# Run with debug logging
tiger-mcp-server --log-level DEBUG --log-file server.log
```

## Available MCP Tools

### Data Tools
- `tiger_get_quote` - Get real-time stock quotes
- `tiger_get_kline` - Get historical K-line/candlestick data
- `tiger_get_market_data` - Get comprehensive market data
- `tiger_search_symbols` - Search for trading symbols
- `tiger_get_option_chain` - Get options chain data
- `tiger_get_market_status` - Get market status and trading hours

### Info Tools
- `tiger_get_contracts` - Get contract specifications
- `tiger_get_financials` - Get financial statements and ratios
- `tiger_get_corporate_actions` - Get corporate actions data
- `tiger_get_earnings` - Get earnings data and estimates

### Account Tools
- `tiger_list_accounts` - List all configured accounts
- `tiger_add_account` - Add new Tiger account
- `tiger_remove_account` - Remove account
- `tiger_get_account_status` - Get account status and info
- `tiger_refresh_token` - Refresh account access tokens
- `tiger_set_default_data_account` - Set default account for data requests
- `tiger_set_default_trading_account` - Set default account for trading

### Trading Tools
- `tiger_get_positions` - Get account positions
- `tiger_get_account_info` - Get detailed account information
- `tiger_get_orders` - Get order history and status
- `tiger_place_order` - Place new trading orders
- `tiger_cancel_order` - Cancel existing orders
- `tiger_modify_order` - Modify existing orders

## Architecture

### Components

1. **TigerMCPServer**: Main orchestration class that manages all server components
2. **TigerFastMCPServer**: FastMCP integration layer that registers MCP tools
3. **ConfigManager**: Configuration loading, validation, and management
4. **ProcessManager**: Multi-process worker pool for API calls
5. **AccountManager**: Multi-account management and token handling
6. **CLI**: Command-line interface for server management

### Process Flow

1. **Initialization**: Configuration loading, database setup, account initialization
2. **Process Pool Setup**: Worker processes for isolated API calls
3. **Tool Registration**: All MCP tools registered with FastMCP
4. **Request Handling**: MCP requests routed to appropriate tools
5. **API Execution**: Tools execute via process pool with account routing
6. **Response Processing**: Results formatted and returned via MCP

### Configuration

The server uses a hierarchical configuration system:

1. **Default Values**: Built-in sensible defaults
2. **Environment Variables**: Override defaults with `TIGER_MCP_*` prefixed variables
3. **Environment Files**: `.env` and `.env.{environment}` files
4. **Command Line**: CLI arguments override all other sources

### Health Monitoring

The server includes comprehensive health monitoring:

- **Background Tasks**: Token refresh, health checks, cleanup
- **Process Pool Monitoring**: Worker health, request metrics, auto-scaling  
- **Account Status**: Token validity, account connectivity
- **Resource Usage**: Memory, CPU, database connections

## Development

### Project Structure

```
mcp-server/
├── src/mcp_server/
│   ├── __init__.py           # Package exports
│   ├── main.py               # FastMCP integration
│   ├── server.py             # Main server orchestration
│   ├── config_manager.py     # Configuration management
│   ├── cli.py                # Command-line interface
│   ├── process_manager.py    # Process pool management
│   ├── tiger_process_pool.py # Process pool implementation
│   ├── tiger_worker.py       # Worker process implementation
│   ├── example_usage.py      # Usage examples and service class
│   └── tools/                # MCP tool implementations
│       ├── __init__.py
│       ├── data_tools.py     # Market data tools
│       ├── info_tools.py     # Information tools
│       ├── account_tools.py  # Account management tools
│       └── trading_tools.py  # Trading tools
├── pyproject.toml            # Package configuration
├── run_server.py             # Simple startup script
└── README.md                 # This file
```

### Environment Variables

All configuration can be controlled via environment variables with the prefix `TIGER_MCP_`:

#### Database Configuration
- `TIGER_MCP_DATABASE_URL` - Database connection URL
- `TIGER_MCP_DATABASE_ECHO` - Enable SQL query logging
- `TIGER_MCP_DATABASE_POOL_SIZE` - Connection pool size

#### Server Configuration  
- `TIGER_MCP_SERVER_HOST` - Server bind host
- `TIGER_MCP_SERVER_PORT` - Server bind port
- `TIGER_MCP_SERVER_DEBUG` - Enable debug mode
- `TIGER_MCP_SERVER_LOG_LEVEL` - Logging level

#### Process Configuration
- `TIGER_MCP_PROCESS_MIN_WORKERS` - Minimum worker processes
- `TIGER_MCP_PROCESS_MAX_WORKERS` - Maximum worker processes
- `TIGER_MCP_PROCESS_TARGET_WORKERS` - Target worker count

#### Security Configuration
- `TIGER_MCP_SECURITY_ENABLE_TOKEN_VALIDATION` - Enable token validation
- `TIGER_MCP_SECURITY_TOKEN_REFRESH_THRESHOLD` - Token refresh threshold (seconds)
- `TIGER_MCP_SECURITY_API_RATE_LIMIT` - API rate limit (requests/minute)

#### Tiger API Configuration
- `TIGER_SANDBOX_MODE` - Enable sandbox mode
- `TIGER_DEFAULT_MARKET` - Default market (US, HK, CN)
- `TIGER_REQUEST_TIMEOUT` - API request timeout

### Testing

```bash
# Test configuration validation
tiger-mcp-server validate-config

# Test server health
tiger-mcp-server health

# Run with debug logging
tiger-mcp-server --log-level DEBUG
```

### Troubleshooting

#### Common Issues

1. **Import Errors**: Ensure all dependencies are installed and paths are correct
2. **Database Connection**: Check database URL and permissions
3. **Tiger API Access**: Verify API keys and sandbox mode setting
4. **Process Pool Issues**: Check worker limits and system resources

#### Logs

The server provides detailed logging at multiple levels:
- **ERROR**: Critical errors requiring immediate attention
- **WARNING**: Important events that may need review
- **INFO**: General operational information
- **DEBUG**: Detailed debugging information

Use `--log-level DEBUG` for maximum verbosity during development.

## License

This project is part of the Tiger MCP system and follows the same licensing terms.