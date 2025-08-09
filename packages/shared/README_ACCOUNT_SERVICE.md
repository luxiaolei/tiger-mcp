# Tiger Account Management Service

This service provides comprehensive account management functionality for the Tiger MCP system, including account CRUD operations, token management with automatic refresh, and intelligent account routing.

## Overview

The account management service consists of three main components:

1. **TigerAccountManager** - CRUD operations for Tiger accounts with encrypted credential storage
2. **TokenManager** - Automatic token refresh, expiration monitoring, and retry logic
3. **AccountRouter** - Intelligent routing of operations to appropriate accounts with load balancing

## Components

### TigerAccountManager (`account_manager.py`)

Handles all Tiger account operations with integrated encryption and database management.

#### Key Features:
- Account CRUD operations with validation
- Encrypted credential storage using AES-256-GCM
- Default account management (trading vs data accounts)
- Account status management and error tracking
- Market permission management
- Automatic token status initialization

#### Usage Example:

```python
from shared import get_account_manager, AccountType, MarketPermission

async def create_account_example():
    account_manager = get_account_manager()
    
    # Create new account
    account = await account_manager.create_account(
        account_name="My Trading Account",
        account_number="12345678",
        tiger_id="your_tiger_id",
        private_key="your_private_key",
        account_type=AccountType.STANDARD,
        environment="sandbox",  # or "production"
        market_permissions=[MarketPermission.US_STOCK, MarketPermission.US_OPTION],
        is_default_trading=True
    )
    
    # Get account
    account = await account_manager.get_account_by_id(account.id)
    
    # Update account
    updated = await account_manager.update_account(
        account.id,
        {"description": "Updated description"}
    )
    
    # Decrypt credentials when needed
    credentials = await account_manager.decrypt_credentials(account)
    tiger_id = credentials["tiger_id"]
    private_key = credentials["private_key"]
```

### TokenManager (`token_manager.py`)

Manages Tiger API tokens with automatic refresh and comprehensive error handling.

#### Key Features:
- Automatic token refresh with configurable scheduling
- Token expiration monitoring
- Retry logic with exponential backoff
- Rate limit handling
- Token validation
- Comprehensive statistics and history tracking
- Background refresh scheduler

#### Usage Example:

```python
from shared import get_token_manager, TokenManager

async def token_management_example():
    token_manager = get_token_manager()
    
    # Refresh token manually
    success, error = await token_manager.refresh_token(account)
    
    # Validate token
    is_valid, error = await token_manager.validate_token(account)
    
    # Schedule automatic refresh
    token_status = await token_manager.schedule_token_refresh(account)
    
    # Refresh all expired tokens
    results = await token_manager.refresh_expired_tokens()
    
    # Get refresh statistics
    stats = await token_manager.get_refresh_statistics(days=30)
    
    # Start background scheduler
    await token_manager.start_background_refresh_scheduler()
```

### AccountRouter (`account_router.py`)

Intelligently routes operations to the most appropriate accounts based on operation type, capabilities, and load balancing.

#### Key Features:
- Operation type-based routing (trading vs data operations)
- Multiple load balancing strategies
- Account availability checking
- Market permission validation
- Automatic failover and retry
- Response time tracking
- Comprehensive routing statistics

#### Usage Example:

```python
from shared import (
    get_account_router, 
    OperationType, 
    LoadBalanceStrategy,
    MarketPermission
)

async def routing_example():
    router = get_account_router()
    
    # Route a trading operation
    trading_account = await router.route_trading_operation(
        OperationType.PLACE_ORDER,
        market_permissions=[MarketPermission.US_STOCK],
        strategy=LoadBalanceStrategy.LEAST_USED
    )
    
    # Route a data operation
    data_account = await router.route_data_operation(
        OperationType.MARKET_DATA,
        strategy=LoadBalanceStrategy.FASTEST_RESPONSE
    )
    
    # General routing
    account = await router.route_operation(
        operation_type=OperationType.QUOTE,
        environment="production",
        strategy=LoadBalanceStrategy.ROUND_ROBIN
    )
    
    # Check account availability
    availability = await router.check_account_availability(account)
    
    # Record operation metrics
    router.record_operation_response_time(account, 150.5)  # 150.5ms
```

## Operation Types

The system supports various operation types for intelligent routing:

### Data Operations (Read-only)
- `MARKET_DATA` - Market data fetching
- `QUOTE` - Real-time quotes
- `HISTORICAL_DATA` - Historical price data
- `FUNDAMENTALS` - Company fundamentals
- `OPTIONS_CHAIN` - Options chain data

### Trading Operations (Write)
- `PLACE_ORDER` - Place new orders
- `MODIFY_ORDER` - Modify existing orders
- `CANCEL_ORDER` - Cancel orders

### Account Operations (Read/Write)
- `ACCOUNT_INFO` - Account information
- `POSITIONS` - Portfolio positions
- `ORDERS` - Order history/status
- `TRANSACTIONS` - Transaction history

## Load Balancing Strategies

- `ROUND_ROBIN` - Rotate through accounts sequentially
- `RANDOM` - Random selection
- `LEAST_USED` - Select account with lowest usage count
- `FASTEST_RESPONSE` - Select account with best response time

## Integration with Database

The service integrates with the database package for:

- **TigerAccount model** - Account information with encrypted credentials
- **TokenStatus model** - Token refresh history and scheduling
- **APIKey model** - API key management and scoping
- **AuditLog model** - Security and operation auditing

## Integration with Encryption

All sensitive data is encrypted using the shared encryption service:

- Tiger ID and private keys are encrypted at rest
- Access and refresh tokens are encrypted
- Encryption uses AES-256-GCM with key derivation
- Supports key rotation and version management

## Error Handling

The service provides comprehensive error handling:

### AccountManagerError Hierarchy
- `AccountManagerError` - Base exception
- `AccountNotFoundError` - Account not found
- `AccountValidationError` - Validation failures
- `DefaultAccountError` - Default account operations

### TokenManagerError Hierarchy
- `TokenManagerError` - Base exception
- `TokenRefreshError` - Refresh failures
- `TokenValidationError` - Validation failures
- `TokenRateLimitError` - Rate limiting

### AccountRouterError Hierarchy
- `AccountRouterError` - Base exception
- `NoAccountsAvailableError` - No suitable accounts
- `OperationNotSupportedError` - Unsupported operations

## Configuration

The service uses configuration from the shared config package:

```python
from shared import get_config, get_tiger_api_config

config = get_config()
tiger_config = get_tiger_api_config()

# Access configuration values
timeout = tiger_config.tiger_api_timeout
retries = tiger_config.tiger_api_retries
```

## Background Tasks

The TokenManager supports background tasks for automatic maintenance:

```python
# Start background token refresh scheduler
await token_manager.start_background_refresh_scheduler()

# Stop all background tasks when shutting down
await token_manager.stop_background_tasks()
```

## Best Practices

1. **Account Management**:
   - Always validate account data before creation
   - Use appropriate account types (STANDARD, PAPER, PRIME)
   - Set proper market permissions
   - Monitor error counts and handle suspended accounts

2. **Token Management**:
   - Schedule automatic refreshes before expiration
   - Handle refresh failures gracefully
   - Monitor token validation regularly
   - Use background scheduler for production

3. **Account Routing**:
   - Use appropriate operation types for routing
   - Monitor account availability and response times
   - Implement proper error handling and retries
   - Choose suitable load balancing strategies

4. **Security**:
   - Never log decrypted credentials
   - Use proper error handling to avoid credential leakage
   - Rotate encryption keys regularly
   - Monitor audit logs for security events

## Dependencies

- `sqlalchemy` - Database operations
- `cryptography` - Encryption services
- `httpx` - HTTP client for Tiger API
- `loguru` - Logging
- `pydantic` - Configuration and validation

## Testing

See `example_usage.py` for comprehensive usage examples and testing scenarios.

## Production Deployment

1. Set up proper environment variables:
   ```bash
   ENCRYPTION_MASTER_KEY=<your_master_key>
   DATABASE_URL=<your_database_url>
   TIGER_API_TIMEOUT=30
   TIGER_API_RETRIES=3
   ```

2. Initialize database schema:
   ```bash
   python -m database.manage_db migrate
   ```

3. Configure proper logging and monitoring

4. Start background token refresh scheduler

5. Monitor account health and token refresh success rates