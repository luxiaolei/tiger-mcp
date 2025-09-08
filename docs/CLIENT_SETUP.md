# 🚀 Tiger MCP Client Setup Guide

## 📦 **Quick Installation**

### From GitHub (Recommended)
```bash
pip install git+https://github.com/your-username/tiger-mcp.git
```

### Alternative: Clone and Install
```bash
git clone https://github.com/your-username/tiger-mcp.git
cd tiger-mcp
pip install -e .
```

## ⚙️ **Configuration Setup**

### 1. Tiger API Credentials
```bash
# Copy example files
cp tiger_openapi_config.properties.example tiger_openapi_config.properties
cp tiger_openapi_token.properties.example tiger_openapi_token.properties

# Edit with your credentials
nano tiger_openapi_config.properties
```

**Required Information:**
- Tiger ID (from [Tiger Developer Portal](https://quant.itiger.com/openapi/info))
- Private Key (RSA Key from Tiger)
- Account Number
- License (TBHK/TBSG/TBNZ)

### 2. Client Configuration
```bash
# Copy and configure MCP client
cp .mcp.json.example .mcp.json
nano .mcp.json
```

**Configure:**
- `TIGER_API_KEY`: Your client API key
- `TIGER_SERVER_URL`: Tiger MCP server address
- `DEFAULT_ACCOUNT`: Your default account number

## 🔧 **Usage Methods**

### Method 1: REST API Client
```python
import requests

# Connect to Tiger MCP server
response = requests.post("http://server:9000/tiger/get_positions", 
    headers={"Authorization": "Bearer your_api_key"},
    json={"account": "your_account_number"}
)

data = response.json()
if data["success"]:
    positions = data["data"]["positions"]
    for pos in positions:
        print(f"{pos['symbol']}: {pos['quantity']} shares")
```

### Method 2: Claude Code Integration  
```json
{
  "mcpServers": {
    "tiger-mcp": {
      "command": "python",
      "args": ["-m", "tiger_mcp.mcp_client"],
      "env": {
        "TIGER_API_KEY": "your_api_key",
        "TIGER_SERVER_URL": "http://your-server:9000",
        "DEFAULT_ACCOUNT": "your_account_number"
      }
    }
  }
}
```

### Method 3: Direct Python Usage
```python
# After pip install
from tiger_mcp.client import TigerClient

client = TigerClient(
    api_key="your_api_key",
    server_url="http://server:9000"
)

# Get account info
account_info = client.get_account_info("your_account")
print(f"Total Assets: ${account_info['total_assets']:,.2f}")

# Place order
order_result = client.place_order(
    account="your_account",
    symbol="AAPL", 
    side="BUY",
    quantity=1,
    order_type="MKT"
)
```

## 🎯 **Available Functions**

### Market Data
- `get_quote(symbol)` - Real-time quotes
- `get_kline(symbol, period)` - Historical K-line data  
- `get_market_status(market)` - Market trading status
- `search_symbols(keyword)` - Symbol search

### Trading Operations
- `get_positions(account)` - Current positions
- `get_account_info(account)` - Account balance & info
- `get_orders(account)` - Order history
- `place_order(account, symbol, side, quantity, order_type)` - Place orders
- `cancel_order(account, order_id)` - Cancel orders
- `modify_order(account, order_id, ...)` - Modify orders

### Account Management
- `list_accounts()` - Available accounts
- `get_account_status(account)` - Account health status

## 🔐 **Security Notes**

### API Key Permissions
- Request demo account access for testing
- Use separate API keys for different applications
- Regularly rotate API keys

### Safe Trading Practices
- Always test with demo accounts first
- Set position limits and stop losses
- Monitor API usage and rate limits

## 🆘 **Troubleshooting**

### Common Issues
1. **Connection Failed**: Check server URL and API key
2. **Permission Denied**: Verify account access rights
3. **Token Expired**: Server will auto-refresh tokens

### Getting Help
- Check server logs for detailed error messages
- Verify Tiger API credentials are valid
- Ensure account permissions are properly configured

---

**Start trading with Tiger MCP in minutes! 📈**