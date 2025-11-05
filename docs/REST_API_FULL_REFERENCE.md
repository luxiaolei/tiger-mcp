# Tiger MCP REST API - Full Reference

Complete REST API documentation for Tiger Brokers integration with automatic token refresh.

## Overview

**Version:** 2.0.0
**Base URL:** `http://localhost:9000`
**Authentication:** Bearer Token (API Key)

### Features

- ✅ **22 Complete API Endpoints** covering all Tiger Brokers functionality
- ✅ **Automatic Token Refresh** every 12 hours (Tiger tokens expire in 15 days)
- ✅ **Multi-Account Support** with role-based access control
- ✅ **API Key Authentication** with permission management
- ✅ **CORS Enabled** for web applications

---

## Quick Start

### 1. Start the Server

```bash
cd /home/trader/tiger-mcp
python tiger_rest_api_full.py
```

Server starts on `http://localhost:9000`

### 2. Test Health Endpoint

```bash
curl http://localhost:9000/health
```

### 3. Make Authenticated Request

```bash
curl -X POST http://localhost:9000/api/market/quote \
  -H "Authorization: Bearer client_key_001" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "67686635",
    "symbol": "AAPL"
  }'
```

---

## Authentication

All endpoints (except `/health` and `/api/endpoints`) require authentication via Bearer token.

### Available API Keys

| API Key | Name | Allowed Accounts | Permissions |
|---------|------|------------------|-------------|
| `client_key_001` | Full Access Client | 67686635, 66804149, 20240830213609658 | read, trade, admin |
| `client_key_demo` | Demo Only Client | 20240830213609658 | read, trade |

### Request Header

```
Authorization: Bearer <api_key>
```

### Example

```bash
curl -H "Authorization: Bearer client_key_001" \
     http://localhost:9000/api/accounts
```

---

## API Endpoints

### System Endpoints (2)

#### 1. Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Tiger MCP REST API - Full Edition",
  "version": "2.0.0",
  "timestamp": "2025-10-29T12:00:00",
  "features": [
    "22 Tiger API endpoints",
    "Automatic token refresh (12h interval)",
    "Multi-account support",
    "API key authentication"
  ]
}
```

#### 2. List All Endpoints
```
GET /api/endpoints
```

**Response:** Complete list of all available endpoints grouped by category.

---

### Account Management (2 endpoints)

#### 1. List Accounts
```
GET /api/accounts
```

**Headers:** `Authorization: Bearer <api_key>`

**Response:**
```json
{
  "success": true,
  "data": {
    "accounts": [
      {
        "account": "67686635",
        "tiger_id": "20154747",
        "account_type": "live",
        "license": "TBHK"
      }
    ],
    "permissions": ["read", "trade", "admin"],
    "api_key_name": "Full Access Client"
  },
  "account": "system",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 2. Manual Token Refresh
```
POST /api/token/refresh
```

**Requires:** `admin` permission

**Request Body:**
```json
{
  "account": "67686635"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "refreshed": true,
    "tiger_id": "20154747",
    "account": "67686635",
    "managed_accounts": ["67686635"]
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

---

### Market Data Endpoints (6)

> ⚠️ **Tiger market entitlements required**
> - 使用 `/api/market/quote`、`/api/market/kline`、`/api/market/batch` 查询美股时，帐户和设备必须具备 **US market** 实时行情权限，否则 Tiger 会返回 `code=4000 permission denied`。
> - `/api/market/option-chain` 在不带 `expiry` 时可以获取到期日列表；如果需要传入 `expiry` 拿到具体合约，必须开通 **US option quote** 权限，否则会同样收到 `code=4000`。
> - 接口目前只支持美股代码；例如传入 `00700` 会得到 `code=1010 ... is not US stock symbol`。
> - 若当前权限不足，建议先用拥有对应市场权限的帐户测试，再联系 Tiger Brokers 开通需要的行情/期权权限。

#### 1. Get Real-Time Quote
```
POST /api/market/quote
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbol": "AAPL"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "latest_price": 175.50,
    "pre_close": 174.20,
    "open": 174.80,
    "high": 176.00,
    "low": 174.50,
    "volume": 52000000,
    "timestamp": 1698595200000
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 2. Get K-Line (Historical Data)
```
POST /api/market/kline
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbol": "AAPL",
  "period": "day",
  "begin_time": "2025-01-01 00:00:00",
  "end_time": "2025-10-29 23:59:59",
  "limit": 100
}
```

**Period Options:** `day`, `week`, `month`, `year`, `1min`, `5min`, `15min`, `30min`, `60min`

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "period": "day",
    "count": 100,
    "bars": [
      {
        "time": 1698595200000,
        "open": 174.80,
        "high": 176.00,
        "low": 174.50,
        "close": 175.50,
        "volume": 52000000
      }
    ]
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 3. Get Batch Market Data
```
POST /api/market/batch
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbols": ["AAPL", "TSLA", "GOOGL"],
  "fields": ["latest_price", "volume", "open", "high", "low"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbols": ["AAPL", "TSLA", "GOOGL"],
    "count": 3,
    "quotes": {
      "AAPL": {
        "latest_price": 175.50,
        "volume": 52000000,
        "open": 174.80,
        "high": 176.00,
        "low": 174.50,
        "pre_close": 174.20
      },
      "TSLA": { /* ... */ },
      "GOOGL": { /* ... */ }
    }
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 4. Search Symbols
```
POST /api/market/search
```

**Request Body:**
```json
{
  "account": "67686635",
  "keyword": "apple",
  "market": "US"
}
```

**Market Options:** `US`, `HK`, `CN`

**Response:**
```json
{
  "success": true,
  "data": {
    "keyword": "apple",
    "market": "US",
    "results": [
      {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "market": "US"
      }
    ]
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 5. Get Option Chain
```
POST /api/market/option-chain
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbol": "AAPL",
  "expiry": "20251219"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "expirations": ["20251219", "20260116", "20260220"]
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 6. Get Market Status
```
POST /api/market/status
```

**Request Body:**
```json
{
  "account": "67686635",
  "market": "US"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "market": "US",
    "status": "Trading"
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

---

### Company Info Endpoints (4)

#### 1. Get Contracts
```
POST /api/info/contracts
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbols": ["AAPL", "TSLA"],
  "sec_type": "STK"
}
```

**Security Types:** `STK`, `OPT`, `FUT`, `CASH`, `FOP`, `WAR`, `IOPT`

**Response:**
```json
{
  "success": true,
  "data": {
    "contracts": [
      {
        "symbol": "AAPL",
        "sec_type": "STK",
        "currency": "USD",
        "exchange": "NASDAQ"
      }
    ]
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 2. Get Financials
```
POST /api/info/financials
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbols": ["AAPL"],
  "fields": ["revenue", "net_income", "eps"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "financials": [
      {
        "symbol": "AAPL",
        "revenue": 394328000000,
        "net_income": 99803000000,
        "eps": 6.13
      }
    ]
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 3. Get Corporate Actions
```
POST /api/info/corporate-actions
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbols": ["AAPL"],
  "action_type": "dividend"
}
```

**Action Types:** `dividend`, `split`, `merge`

**Response:**
```json
{
  "success": true,
  "data": {
    "corporate_actions": [
      {
        "symbol": "AAPL",
        "action_type": "dividend",
        "amount": 0.24,
        "ex_date": "2025-11-08",
        "pay_date": "2025-11-14"
      }
    ]
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 4. Get Earnings Calendar
```
POST /api/info/earnings
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbols": ["AAPL"],
  "begin_date": "2025-01-01",
  "end_date": "2025-12-31"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "earnings": [
      {
        "symbol": "AAPL",
        "report_date": "2025-11-02",
        "fiscal_quarter": "Q4 2025",
        "eps_estimate": 1.55,
        "revenue_estimate": 94000000000
      }
    ]
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

---

### Trading Endpoints (6)

#### 1. Get Positions
```
POST /api/trade/positions
```

**Request Body:**
```json
{
  "account": "67686635"
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
        "average_cost": 150.00,
        "market_price": 175.50,
        "market_value": 17550.00,
        "unrealized_pnl": 2550.00
      }
    ],
    "count": 1
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 2. Get Account Info
```
POST /api/trade/account-info
```

**Request Body:**
```json
{
  "account": "67686635"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "account_id": "67686635",
    "tiger_id": "20154747",
    "net_liquidation": 150000.00,
    "cash_balance": 50000.00,
    "buying_power": 200000.00,
    "gross_position_value": 100000.00,
    "unrealized_pnl": 5000.00,
    "realized_pnl": 2500.00,
    "update_timestamp": 1698595200000
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 3. Get Orders
```
POST /api/trade/orders
```

**Request Body:**
```json
{
  "account": "67686635",
  "status": "Submitted",
  "start_date": "2025-10-01",
  "end_date": "2025-10-29"
}
```

**Status Options:** `Initial`, `Submitted`, `Filled`, `Cancelled`, `PendingCancel`

**Response:**
```json
{
  "success": true,
  "data": {
    "orders": [
      {
        "order_id": "12345678",
        "symbol": "AAPL",
        "action": "BUY",
        "order_type": "LMT",
        "quantity": 100,
        "limit_price": 175.00,
        "status": "Submitted",
        "filled": 0,
        "avg_fill_price": null,
        "order_time": 1698595200000
      }
    ],
    "count": 1
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 4. Place Order
```
POST /api/trade/place-order
```

**Request Body:**
```json
{
  "account": "67686635",
  "symbol": "AAPL",
  "action": "BUY",
  "order_type": "LMT",
  "quantity": 100,
  "limit_price": 175.00,
  "time_in_force": "DAY",
  "outside_rth": true
}
```

**Order Types:**
- `MKT` - Market Order
- `LMT` - Limit Order (requires `limit_price`)
- `STP` - Stop Order (requires `stop_price`)
- `STP_LMT` - Stop Limit Order (requires both `limit_price` and `stop_price`)

**Time in Force:** `DAY`, `GTC`, `IOC`, `FOK`

**Note:** `outside_rth` is optional. When omitted, market orders default to `true` so they can execute during extended hours.

**Response:**
```json
{
  "success": true,
  "data": {
    "order_id": "40139406481165312",
    "account_order_id": "1024",
    "symbol": "AAPL",
    "action": "BUY",
    "order_type": "LMT",
    "quantity": 100,
    "status": "Submitted",
    "filled": 0,
    "remaining": 100,
    "avg_fill_price": null,
    "limit_price": 175.00,
    "stop_price": null,
    "time_in_force": "DAY",
    "outside_rth": true,
    "order_time": 1755073344000,
    "update_time": 1755073344000,
    "commission": 0.0,
    "realized_pnl": 0.0,
    "filled_cash_amount": 0.0,
    "status_details": null
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 5. Modify Order
```
POST /api/trade/modify-order
```

**Request Body:**
```json
{
  "account": "67686635",
  "order_id": "12345678",
  "quantity": 150,
  "limit_price": 174.00
}
```

**Note:** At least one of `quantity`, `limit_price`, or `stop_price` must be supplied.

**Response:**
```json
{
  "success": true,
  "data": {
    "order_id": "40139406481165312",
    "account_order_id": "1024",
    "requested_order_id": "12345678",
    "status": "Submitted",
    "symbol": "AAPL",
    "action": "BUY",
    "order_type": "LMT",
    "quantity": 150,
    "filled": 0,
    "remaining": 150,
    "avg_fill_price": null,
    "limit_price": 174.00,
    "stop_price": null,
    "time_in_force": "DAY",
    "outside_rth": true,
    "order_time": 1755073344000,
    "update_time": 1755073361000,
    "commission": 0.0,
    "realized_pnl": 0.0,
    "filled_cash_amount": 0.0,
    "status_details": null,
    "modified_fields": {
      "quantity": 150,
      "limit_price": 174.00
    },
    "modify_reference_id": "40139406481165312",
    "result": "40139406481165312"
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

#### 6. Cancel Order
```
POST /api/trade/cancel-order
```

**Request Body:**
```json
{
  "account": "67686635",
  "order_id": "12345678"
}
```

**Note:** You can supply either the global order ID (long numeric value returned by the Tiger API) or the account-specific incremental order ID shown in `get_orders`.

**Response:**
```json
{
  "success": true,
  "data": {
    "order_id": "40139406481165312",
    "account_order_id": "12345678",
    "requested_order_id": "12345678",
    "status": "Cancelled",
    "symbol": "AAPL",
    "action": "BUY",
    "order_type": "LMT",
    "quantity": 150,
    "filled": 0,
    "remaining": 150,
    "avg_fill_price": null,
    "limit_price": 174.00,
    "stop_price": null,
    "time_in_force": "DAY",
    "outside_rth": true,
    "order_time": 1755073344000,
    "update_time": 1755073600000,
    "commission": 0.0,
    "realized_pnl": 0.0,
    "filled_cash_amount": 0.0,
    "status_details": null,
    "cancel_reference_id": "40139406481165312"
  },
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

---

## Automatic Token Refresh

### How It Works

The server automatically refreshes Tiger Brokers API tokens in the background:

1. **Refresh Interval:** Every 12 hours
2. **Tiger Token Expiry:** 15 days
3. **Mechanism:** Tiger SDK auto-updates `tiger_openapi_token.properties` file
4. **Coverage:** All configured accounts

### Token Lifecycle

```
Server Start
    ↓
Wait 1 minute (server initialization)
    ↓
First Token Refresh (all accounts)
    ↓
Wait 12 hours
    ↓
Scheduled Token Refresh
    ↓
(Loop continues)
```

### Manual Token Refresh

You can also manually trigger token refresh via API:

```bash
curl -X POST http://localhost:9000/api/token/refresh \
  -H "Authorization: Bearer client_key_001" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "67686635"
  }'
```

**Note:** Requires `admin` permission.

### Monitoring Token Refresh

Check server logs for token refresh activity:

```
🔄 Starting scheduled token refresh for all accounts...
✅ Token refresh successful for account 67686635, tiger_id: 20154747
✅ Token refresh completed: 3/3 successful
⏰ Next token refresh in 12.0h
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error description here",
  "account": "67686635",
  "timestamp": "2025-10-29T12:00:00"
}
```

### Common HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (invalid API key)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (account not found)
- `500` - Internal Server Error

---

## Configuration

### Adding New API Keys

Edit `tiger_rest_api_full.py`:

```python
API_KEYS = {
    "your_new_key": {
        "name": "Your Client Name",
        "allowed_accounts": ["account1", "account2"],
        "permissions": ["read", "trade"]  # or ["read", "trade", "admin"]
    }
}
```

### Adding New Accounts

```python
ACCOUNT_MAPPING = {
    "your_account_id": {
        "tiger_id": "your_tiger_id",
        "type": "live",  # or "demo"
        "license": "TBHK"  # or your license
    }
}
```

### Adjusting Token Refresh Interval

```python
TOKEN_REFRESH_INTERVAL = 12 * 3600  # seconds (12 hours)
```

---

## Testing

### Test Basic Connectivity

```bash
# Health check
curl http://localhost:9000/health

# List endpoints
curl http://localhost:9000/api/endpoints
```

### Test Authentication

```bash
# List accounts (requires valid API key)
curl -H "Authorization: Bearer client_key_001" \
     http://localhost:9000/api/accounts
```

### Test Market Data

```bash
# Get quote
curl -X POST http://localhost:9000/api/market/quote \
  -H "Authorization: Bearer client_key_001" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "67686635",
    "symbol": "AAPL"
  }'
```

### Test Trading (Demo Account)

```bash
# Get positions
curl -X POST http://localhost:9000/api/trade/positions \
  -H "Authorization: Bearer client_key_demo" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "20240830213609658"
  }'
```

---

## Complete Endpoint Summary

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **System** | `/health` | GET | Health check |
| | `/api/endpoints` | GET | List all endpoints |
| **Account** | `/api/accounts` | GET | List accessible accounts |
| | `/api/token/refresh` | POST | Manual token refresh |
| **Market Data** | `/api/market/quote` | POST | Real-time quote |
| | `/api/market/kline` | POST | Historical K-line data |
| | `/api/market/batch` | POST | Batch market data |
| | `/api/market/search` | POST | Search symbols |
| | `/api/market/option-chain` | POST | Option chain |
| | `/api/market/status` | POST | Market status |
| **Company Info** | `/api/info/contracts` | POST | Contract details |
| | `/api/info/financials` | POST | Financial data |
| | `/api/info/corporate-actions` | POST | Corporate actions |
| | `/api/info/earnings` | POST | Earnings calendar |
| **Trading** | `/api/trade/positions` | POST | Get positions |
| | `/api/trade/account-info` | POST | Account information |
| | `/api/trade/orders` | POST | Get orders |
| | `/api/trade/place-order` | POST | Place order |
| | `/api/trade/modify-order` | POST | Modify order |
| | `/api/trade/cancel-order` | POST | Cancel order |

**Total: 20 API endpoints** (22 including health and endpoints listing)

---

## Support & Troubleshooting

### Common Issues

**1. "Invalid API Key" Error**
- Verify your API key is correctly configured in the `Authorization` header
- Check that the API key exists in the `API_KEYS` configuration

**2. "Access denied" Error**
- Verify the account is in your API key's `allowed_accounts` list
- Check that you have the required permission (`read`, `trade`, or `admin`)

**3. Token Expiration**
- The automatic refresh runs every 12 hours
- Check server logs for refresh status
- Manually trigger refresh via `/api/token/refresh`

**4. Tiger SDK Errors**
- Ensure `tiger_openapi_config.properties` file exists
- Verify Tiger API credentials are valid
- Check Tiger Brokers account status

### Server Logs

Monitor logs for detailed information:

```bash
# If running in foreground
# Logs appear in console

# If running in background
tail -f /path/to/log/file
```

---

## License & Credits

Part of the Tiger MCP project.

For more information, see the main project documentation.
