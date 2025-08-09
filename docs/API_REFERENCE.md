# Tiger MCP API Reference

Complete API reference for the Tiger MCP system, covering MCP tools, REST API endpoints, and WebSocket connections.

## MCP Tools API Reference

The Tiger MCP system provides comprehensive Model Context Protocol tools for trading and market data operations.

### Account Management Tools

#### `tiger_list_accounts`

List all configured Tiger accounts with their status and permissions.

**Parameters:**
```json
{
  "environment": "production|sandbox",  // Optional: Filter by environment
  "account_type": "standard|paper|prime",  // Optional: Filter by account type
  "status": "active|inactive|suspended",  // Optional: Filter by status
  "include_inactive": false  // Optional: Include inactive accounts
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "account_name": "My Trading Account",
      "account_number": "12345678",
      "account_type": "standard",
      "environment": "production",
      "status": "active",
      "market_permissions": ["US_STOCK", "US_OPTION"],
      "is_default_trading": true,
      "is_default_data": false,
      "token_status": {
        "is_valid": true,
        "expires_at": "2024-12-31T23:59:59Z",
        "last_refreshed": "2024-01-01T12:00:00Z"
      }
    }
  ],
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### `tiger_add_account`

Add a new Tiger account to the system.

**Parameters:**
```json
{
  "name": "My New Account",  // Required: Account display name
  "tiger_id": "20154747",  // Required: Tiger API ID
  "account": "12345678",  // Required: Account number
  "license": "TBHK",  // Required: Tiger broker license
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",  // Required: Private key
  "environment": "production",  // Required: "production" or "sandbox"
  "account_type": "standard",  // Optional: Default "standard"
  "market_permissions": ["US_STOCK", "US_OPTION"],  // Optional: Default all markets
  "is_default_trading": false,  // Optional: Set as default trading account
  "is_default_data": false  // Optional: Set as default data account
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "account_name": "My New Account",
    "account_number": "12345678",
    "status": "active",
    "created_at": "2024-01-01T12:00:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### `tiger_remove_account`

Remove an account from the system.

**Parameters:**
```json
{
  "account_id": "uuid",  // Required: Account UUID
  "force": false  // Optional: Force removal even with dependencies
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "removed_account_id": "uuid",
    "removed_at": "2024-01-01T12:00:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Market Data Tools

#### `tiger_get_quote`

Get real-time quote for a single symbol.

**Parameters:**
```json
{
  "symbol": "AAPL",  // Required: Trading symbol
  "data_account_id": "uuid"  // Optional: Specific data account
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "latest_price": 150.25,
    "bid": 150.20,
    "ask": 150.30,
    "bid_size": 100,
    "ask_size": 200,
    "volume": 45234567,
    "change": 2.15,
    "change_percent": 1.45,
    "high": 151.00,
    "low": 148.50,
    "open": 149.00,
    "prev_close": 148.10,
    "timestamp": "2024-01-01T15:30:00Z"
  },
  "account_id": "uuid",
  "timestamp": "2024-01-01T15:30:00Z"
}
```

#### `tiger_get_kline`

Get historical K-line (candlestick) data.

**Parameters:**
```json
{
  "symbol": "TSLA",  // Required: Trading symbol
  "period": "1d",  // Optional: Time period (1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M)
  "count": 100,  // Optional: Number of bars (max 300)
  "data_account_id": "uuid"  // Optional: Specific data account
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "time": "2024-01-01T09:30:00Z",
      "open": 245.50,
      "high": 248.75,
      "low": 244.20,
      "close": 247.85,
      "volume": 2345678
    }
  ],
  "symbol": "TSLA",
  "period": "1d",
  "count": 100,
  "account_id": "uuid",
  "timestamp": "2024-01-01T16:00:00Z"
}
```

#### `tiger_get_market_data`

Get batch market data for multiple symbols.

**Parameters:**
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],  // Required: List of symbols (max 50)
  "fields": ["latest_price", "volume", "change"],  // Optional: Specific fields
  "data_account_id": "uuid"  // Optional: Specific data account
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "AAPL": {
      "symbol": "AAPL",
      "latest_price": 150.25,
      "volume": 45234567,
      "change": 2.15
    },
    "MSFT": {
      "symbol": "MSFT",
      "latest_price": 378.90,
      "volume": 23456789,
      "change": -1.25
    }
  },
  "account_id": "uuid",
  "timestamp": "2024-01-01T15:30:00Z"
}
```

### Trading Tools

#### `tiger_get_positions`

Get current portfolio positions.

**Parameters:**
```json
{
  "trading_account_id": "uuid"  // Optional: Specific trading account
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "positions": [
      {
        "symbol": "AAPL",
        "quantity": 100,
        "average_cost": 145.50,
        "market_value": 15025.00,
        "unrealized_pnl": 475.00,
        "unrealized_pnl_percent": 3.26,
        "side": "long"
      }
    ],
    "summary": {
      "total_market_value": 15025.00,
      "total_cost": 14550.00,
      "total_unrealized_pnl": 475.00,
      "total_unrealized_pnl_percent": 3.26
    }
  },
  "account_id": "uuid",
  "timestamp": "2024-01-01T16:00:00Z"
}
```

#### `tiger_place_order`

Place a new trading order. **⚠️ Warning: This executes real trades in production.**

**Parameters:**
```json
{
  "symbol": "AAPL",  // Required: Trading symbol
  "side": "BUY",  // Required: BUY or SELL
  "quantity": 100,  // Required: Number of shares
  "order_type": "LIMIT",  // Required: MARKET, LIMIT, STOP, STOP_LIMIT
  "price": 150.00,  // Required for LIMIT and STOP_LIMIT orders
  "stop_price": 148.00,  // Required for STOP and STOP_LIMIT orders
  "time_in_force": "DAY",  // Optional: DAY, GTC, IOC, FOK
  "trading_account_id": "uuid"  // Optional: Specific trading account
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "order_id": "12345678901",
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": 100,
    "order_type": "LIMIT",
    "price": 150.00,
    "status": "PENDING_NEW",
    "created_at": "2024-01-01T15:30:00Z"
  },
  "account_id": "uuid",
  "timestamp": "2024-01-01T15:30:00Z"
}
```

## Error Codes and Responses

### Standard Error Response Format

```json
{
  "success": false,
  "error": "Error message description",
  "error_code": "TIGER_API_ERROR",
  "details": {
    "parameter": "Additional error context"
  },
  "timestamp": "2024-01-01T15:30:00Z"
}
```

### Common Error Codes

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| `INVALID_SYMBOL` | Symbol not found or invalid | 400 | Check symbol format and market |
| `ACCOUNT_NOT_FOUND` | Account ID not found | 404 | Verify account ID exists |
| `INSUFFICIENT_FUNDS` | Not enough buying power | 400 | Check account balance |
| `MARKET_CLOSED` | Market is closed for trading | 400 | Wait for market hours |
| `TOKEN_EXPIRED` | API token has expired | 401 | Refresh token or re-authenticate |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 | Wait and retry with backoff |
| `TIGER_API_ERROR` | General Tiger API error | 500 | Check Tiger API status |
| `ACCOUNT_SUSPENDED` | Account is suspended | 403 | Contact account administrator |
| `INVALID_ORDER_TYPE` | Order type not supported | 400 | Use supported order types |
| `POSITION_NOT_FOUND` | Position does not exist | 404 | Verify position exists |

## Rate Limits

The Tiger MCP system implements rate limiting to protect against abuse:

- **Account Operations**: 10 requests per minute
- **Market Data**: 60 requests per minute  
- **Trading Operations**: 30 requests per minute
- **Bulk Operations**: 5 requests per minute

Rate limits are per API key and reset every minute. Exceeded limits return HTTP 429 with retry-after header.

## Authentication

All MCP tools use the configured Tiger accounts for authentication. Ensure accounts are properly configured with valid tokens before making requests.

### Token Management

Tokens are automatically refreshed by the system when they approach expiration. Manual refresh is available via the `tiger_refresh_token` tool.

## Data Types

### Common Data Types

- **UUID**: Standard UUID format (e.g., "550e8400-e29b-41d4-a716-446655440000")
- **Decimal**: Monetary values with up to 4 decimal places
- **Timestamp**: ISO 8601 format with timezone (e.g., "2024-01-01T15:30:00Z")
- **Symbol**: Stock symbols in uppercase (e.g., "AAPL", "TSLA")

### Enumerations

#### Account Types
- `standard`: Regular trading account
- `paper`: Paper trading account
- `prime`: Prime brokerage account

#### Order Sides
- `BUY`: Buy order
- `SELL`: Sell order

#### Order Types
- `MARKET`: Market order
- `LIMIT`: Limit order
- `STOP`: Stop order
- `STOP_LIMIT`: Stop limit order

#### Time in Force
- `DAY`: Day order (expires at market close)
- `GTC`: Good till cancelled
- `IOC`: Immediate or cancel
- `FOK`: Fill or kill

## Best Practices

1. **Error Handling**: Always check the `success` field in responses
2. **Rate Limiting**: Implement exponential backoff for rate limit errors
3. **Account Selection**: Use appropriate accounts for trading vs data operations
4. **Order Validation**: Validate order parameters before submission
5. **Position Management**: Check positions before placing orders
6. **Market Hours**: Verify market status before trading operations
7. **Token Management**: Monitor token expiration and refresh proactively

## Examples

### Complete Trading Workflow

```python
# 1. List accounts
accounts = await tiger_list_accounts()

# 2. Get account info
account_info = await tiger_get_account_info()

# 3. Get current positions
positions = await tiger_get_positions()

# 4. Get market quote
quote = await tiger_get_quote("AAPL")

# 5. Place order
order = await tiger_place_order(
    symbol="AAPL",
    side="BUY", 
    quantity=100,
    order_type="LIMIT",
    price=150.00
)

# 6. Check order status
orders = await tiger_get_orders(order_id=order.data.order_id)
```

### Market Data Analysis

```python
# Get historical data
kline_data = await tiger_get_kline("TSLA", "1d", 30)

# Get multiple symbols
market_data = await tiger_get_market_data(["AAPL", "MSFT", "GOOGL"])

# Search for symbols
search_results = await tiger_search_symbols("tesla", "US")

# Get option chain
options = await tiger_get_option_chain("SPY")
```

This API reference covers all available MCP tools and their usage patterns. For specific implementation details, see the individual package documentation.