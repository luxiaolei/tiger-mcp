# Tiger MCP Tools

This module provides FastMCP tools for the Tiger Brokers API integration, allowing MCP clients to retrieve market data, financial information, and other trading-related data through the Tiger API process pool system.

## Architecture

The tools are organized into two main categories:

- **Data Tools** (`data_tools.py`): Market data, quotes, historical data, and market status
- **Info Tools** (`info_tools.py`): Contract details, financial data, corporate actions, and earnings

All tools integrate with:
- **Process Pool Manager**: For account routing and API execution
- **Account Manager**: For default account handling
- **Account Router**: For intelligent account selection

## Data Tools

### tiger_get_quote(symbol, data_account_id=None)
Get real-time quote for a symbol.

**Parameters:**
- `symbol` (str): Stock symbol (e.g., 'AAPL', 'TSLA', 'SPY')
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Real-time quote data including bid/ask, volume, change, etc.

**Example:**
```python
response = await tiger_get_quote("AAPL")
if response.success:
    price = response.data["latest_price"]
    print(f"AAPL: ${price}")
```

### tiger_get_kline(symbol, period="1d", count=100, data_account_id=None)
Get historical K-line (candlestick) data.

**Parameters:**
- `symbol` (str): Stock symbol
- `period` (str): Time period ('1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M')
- `count` (int): Number of bars (max 300)
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Historical OHLCV data for technical analysis.

**Example:**
```python
response = await tiger_get_kline("TSLA", "1d", 30)
for bar in response.data:
    print(f"OHLC: {bar['open']}, {bar['high']}, {bar['low']}, {bar['close']}")
```

### tiger_get_market_data(symbols, fields=None, data_account_id=None)
Get batch market data for multiple symbols.

**Parameters:**
- `symbols` (List[str]): List of symbols (max 50)
- `fields` (Optional[List[str]]): Specific fields to retrieve
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Market data organized by symbol.

**Example:**
```python
response = await tiger_get_market_data(['AAPL', 'MSFT', 'GOOGL'])
for symbol, data in response.data.items():
    print(f"{symbol}: ${data['latest_price']}")
```

### tiger_search_symbols(keyword, market="US", data_account_id=None)
Search for symbols by keyword.

**Parameters:**
- `keyword` (str): Search term (company name, symbol, etc.)
- `market` (str): Market ('US', 'HK', 'SG', 'CN')
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Matching symbols with company names and details.

**Example:**
```python
response = await tiger_search_symbols("tesla", "US")
for result in response.data:
    print(f"{result['symbol']}: {result['name']}")
```

### tiger_get_option_chain(symbol, data_account_id=None)
Get option chain data for a symbol.

**Parameters:**
- `symbol` (str): Underlying stock symbol
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Option contracts (calls/puts) with strikes, expiry, bid/ask, etc.

**Example:**
```python
response = await tiger_get_option_chain("SPY")
calls = response.data["calls"]
puts = response.data["puts"]
print(f"Found {len(calls)} calls, {len(puts)} puts")
```

### tiger_get_market_status(market="US", data_account_id=None)
Get current market status and trading hours.

**Parameters:**
- `market` (str): Market to check ('US', 'HK', 'SG', 'CN')
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Market status, trading hours, and session information.

**Example:**
```python
response = await tiger_get_market_status("US")
print(f"US Market: {response.data['status']}")
```

## Info Tools

### tiger_get_contracts(symbols, data_account_id=None)
Get detailed contract information for symbols.

**Parameters:**
- `symbols` (List[str]): List of symbols (max 20)
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Contract details including sec_type, exchange, currency, lot_size, etc.

**Example:**
```python
response = await tiger_get_contracts(['AAPL', 'TSLA'])
for symbol, contract in response.data.items():
    print(f"{symbol}: {contract['sec_type']} on {contract['exchange']}")
```

### tiger_get_financials(symbol, data_account_id=None)
Get financial data and key metrics.

**Parameters:**
- `symbol` (str): Stock symbol
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Financial metrics including P/E, market cap, revenue, EPS, etc.

**Example:**
```python
response = await tiger_get_financials("AAPL")
data = response.data
print(f"Market Cap: ${data['market_cap']:,}")
print(f"P/E Ratio: {data['pe_ratio']}")
```

### tiger_get_corporate_actions(symbol, data_account_id=None)
Get corporate actions data.

**Parameters:**
- `symbol` (str): Stock symbol
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Corporate actions like dividends, splits, mergers, etc.

**Example:**
```python
response = await tiger_get_corporate_actions("MSFT")
for action in response.data:
    if action['action_type'] == 'DIVIDEND':
        print(f"Dividend: ${action['amount']} ex: {action['ex_date']}")
```

### tiger_get_earnings(symbol, data_account_id=None)
Get earnings data and estimates.

**Parameters:**
- `symbol` (str): Stock symbol
- `data_account_id` (Optional[str]): Specific data account ID

**Returns:** Earnings reports, estimates, and growth metrics.

**Example:**
```python
response = await tiger_get_earnings("GOOGL")
data = response.data
print(f"Last EPS: ${data['last_reported_eps']}")
print(f"Next Report: {data['next_report_date']}")
```

## Account Routing

All tools support flexible account routing:

1. **Explicit Account**: Use `data_account_id` parameter
2. **Default Account**: Uses configured default data account
3. **Smart Routing**: Account router selects optimal account

The tools automatically handle:
- Account validation and status checking
- Process pool routing and execution
- Error handling and retry logic
- Response formatting and validation

## Error Handling

All tools return structured responses with:
- `success` (bool): Operation success status
- `data` (dict): Response data when successful
- `error` (str): Error message when failed
- `timestamp` (str): ISO timestamp
- `account_id` (str): Account used for the request

Example error handling:
```python
response = await tiger_get_quote("INVALID_SYMBOL")
if not response.success:
    print(f"Error: {response.error}")
    # Handle error appropriately
```

## Integration with MCP Server

These tools are designed to be used as FastMCP tools in an MCP server. They can be:

1. Imported directly into an MCP server application
2. Used with the existing Tiger MCP server framework
3. Extended with additional functionality as needed

The tools leverage the existing Tiger process pool infrastructure for scalability and reliability.

## Usage Examples

See `usage_example.py` for comprehensive examples of all tools in action.

Run the example:
```bash
python -m mcp_server.tools.usage_example
```

This will demonstrate each tool with realistic data and show proper error handling patterns.