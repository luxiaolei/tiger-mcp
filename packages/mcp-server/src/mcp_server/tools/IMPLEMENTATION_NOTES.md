# Tiger MCP Tools Implementation

This document describes the implementation of account management and trading MCP tools for the Tiger MCP system.

## Implemented Tools

### Account Management Tools (`account_tools.py`)

1. **`tiger_list_accounts()`** - List all configured accounts with status
   - Supports filtering by environment, account type, and status
   - Returns comprehensive account information including permissions and token status
   - Includes validation for filter parameters

2. **`tiger_add_account()`** - Add new Tiger account
   - Creates account with encrypted credential storage
   - Supports paper trading and production accounts
   - Validates all input parameters including market permissions
   - Handles default account settings

3. **`tiger_remove_account()`** - Remove account safely
   - Includes safety checks for accounts with dependencies
   - Supports force removal option
   - Validates UUID format

4. **`tiger_get_account_status()`** - Get detailed account status
   - Returns comprehensive status including token validity, health metrics
   - Integrates with account router for routing availability
   - Includes process status information

5. **`tiger_refresh_token()`** - Manual token refresh
   - Forces token refresh for specific account
   - Returns new token expiration information
   - Handles refresh failures gracefully

6. **`tiger_set_default_data_account()`** - Set default data account
   - Configures account for data operations
   - Validates account existence and status

7. **`tiger_set_default_trading_account()`** - Set default trading account  
   - Configures account for trading operations
   - Ensures only one default trading account

### Trading Tools (`trading_tools.py`)

1. **`tiger_get_positions()`** - Get current positions
   - Returns all positions with market values and P&L
   - Calculates total portfolio metrics
   - Supports account routing

2. **`tiger_get_account_info()`** - Get account balance and info
   - Returns cash balances, buying power, margin info
   - Includes net liquidation value and P&L summary
   - Routes to appropriate trading account

3. **`tiger_get_orders()`** - Get orders with filtering
   - Supports filtering by status, symbol, date range
   - Returns comprehensive order details
   - Limits results to prevent performance issues

4. **`tiger_place_order()`** - Place new trading orders
   - Supports market, limit, stop, and stop-limit orders
   - Comprehensive input validation
   - Handles time-in-force options
   - **Warning: Executes real trades in production**

5. **`tiger_cancel_order()`** - Cancel existing orders
   - Cancels pending or partially filled orders
   - Returns final order status
   - Handles cancellation failures

6. **`tiger_modify_order()`** - Modify existing orders
   - Supports quantity, price, and stop price modifications
   - Validates modification parameters
   - Works with pending and partially filled orders

## Architecture Features

### Error Handling
- Comprehensive validation for all input parameters
- Structured error responses with meaningful messages
- Graceful handling of API failures and timeouts
- Proper exception logging

### Security
- Integration with encrypted credential storage
- Account permission validation
- Safe account removal with dependency checks
- Secure token management

### Account Routing
- Automatic routing to appropriate accounts
- Support for default account preferences
- Load balancing through account router integration
- Fallback mechanisms for account selection

### Response Structure
- Consistent response models using Pydantic
- Success/error status indicators
- Timestamps for all operations
- Structured data with proper typing

### Integration Points
- Process manager for API call execution
- Account manager for credential management
- Account router for intelligent account selection
- Shared services across the MCP system

## Key Design Decisions

1. **Account Routing Strategy**: Tools support both explicit account specification and automatic routing through the account router system.

2. **Validation First**: All tools perform comprehensive input validation before attempting API calls to provide clear error messages.

3. **Structured Responses**: All tools return structured response objects with consistent fields for success status, data, errors, and timestamps.

4. **Safety Mechanisms**: Trading tools include safety checks and warnings about real money operations.

5. **Service Layer**: Tools use a service layer pattern for shared functionality and consistent account routing logic.

## Usage Examples

### Account Management
```python
# List all accounts
accounts = await tiger_list_accounts()

# Add new account
response = await tiger_add_account(
    name="My Trading Account",
    api_key="your_key", 
    secret_key="your_secret",
    account_type="standard"
)

# Set default accounts
await tiger_set_default_trading_account(account_id)
await tiger_set_default_data_account(account_id)
```

### Trading Operations
```python
# Get positions
positions = await tiger_get_positions()

# Place market order
order = await tiger_place_order(
    symbol="AAPL",
    side="BUY",
    quantity=100,
    order_type="MARKET"
)

# Get account info
info = await tiger_get_account_info()
```

## Dependencies

- FastMCP: MCP tool decoration and schema validation
- Pydantic: Response model validation and serialization  
- Loguru: Structured logging
- Shared services: Account manager, account router, process manager
- Database models: Account types, status enums, permissions

## Testing

A test integration script (`test_tools_integration.py`) is provided to validate:
- Input parameter validation
- Response structure consistency
- Error handling behavior
- Tool integration points

## Security Considerations

1. **Real Money Warning**: Trading tools can execute real trades in production environments
2. **Credential Protection**: All credentials are encrypted before storage
3. **Permission Validation**: Market permissions are validated before operations
4. **Account Isolation**: Each tool respects account boundaries and permissions
5. **Audit Trail**: All operations are logged for security audit purposes

## Future Enhancements

1. **Extended Order Types**: Support for advanced order types (OCO, bracket orders)
2. **Portfolio Analytics**: Advanced portfolio analysis and risk metrics
3. **Real-time Updates**: WebSocket integration for real-time position/order updates
4. **Batch Operations**: Support for batch order placement and modifications
5. **Paper Trading Integration**: Enhanced paper trading simulation features