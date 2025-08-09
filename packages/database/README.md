# Database Package

Database models and migrations for Tiger MCP system.

## Overview

This package provides comprehensive database support for the Tiger MCP system including:

- **SQLAlchemy Models**: Fully-featured async models for all entities
- **Alembic Migrations**: Schema versioning and migration management
- **Database Configuration**: Environment-based configuration with SSL support
- **Utility Functions**: Common database operations and helpers
- **Management CLI**: Command-line tools for database operations

## Models

### TigerAccount
Stores Tiger Broker account information with encrypted credentials:
- Account configuration and status
- Encrypted API credentials (Tiger ID, private key, tokens)
- Market permissions and rate limiting
- Default account designation for trading/data operations

### APIKey
Authentication keys for MCP server and dashboard access:
- Scoped permissions (MCP, dashboard, trading, system)
- Optional account binding for trading operations
- Rate limiting and IP restrictions
- Usage tracking and expiration

### AuditLog
Comprehensive audit trail for compliance and debugging:
- All user actions and system events
- Security events and access attempts
- Trading operations and API calls
- Rich metadata and error tracking

### TokenStatus
Tiger API token refresh tracking:
- Automatic token refresh scheduling
- Retry logic and error handling
- Performance metrics and monitoring
- Historical refresh operations

## Configuration

Configure database connection via environment variables:

```bash
# Database connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tiger_mcp
DB_USER=postgres
DB_PASSWORD=secret

# Connection pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# SSL (optional)
DB_SSL_MODE=prefer
DB_SSL_CERT=/path/to/client-cert.pem
DB_SSL_KEY=/path/to/client-key.pem
DB_SSL_CA=/path/to/ca-cert.pem

# Environment
ENVIRONMENT=development
DB_DEBUG=false
```

## Usage

### Basic Setup

```python
from database import (
    get_session, create_utils,
    TigerAccount, APIKey, AccountType, APIKeyScope
)

# Get database session
async with get_session() as session:
    utils = create_utils(session)
    
    # Create Tiger account
    account = await utils["accounts"].create(
        TigerAccount,
        account_name="My Trading Account",
        account_number="12345678",
        tiger_id="encrypted_tiger_id",
        private_key="encrypted_private_key",
        account_type=AccountType.STANDARD
    )
    
    # Create API key
    api_key, raw_key = await utils["api_keys"].create_api_key(
        name="MCP Server Key",
        scopes=[APIKeyScope.MCP_READ, APIKeyScope.MCP_WRITE],
        tiger_account_id=account.id
    )
```

### Account Management

```python
# Get default accounts
trading_account = await utils["accounts"].get_default_trading_account()
data_account = await utils["accounts"].get_default_data_account()

# Get account by number
account = await utils["accounts"].get_by_account_number("12345678")

# Get accounts needing token refresh
expired_accounts = await utils["accounts"].get_accounts_needing_token_refresh()
```

### API Key Operations

```python
# Verify API key
api_key = await utils["api_keys"].verify_api_key(raw_key_string)
if api_key and api_key.is_active:
    # Key is valid and active
    if api_key.has_scope(APIKeyScope.TRADE_WRITE):
        # Can perform trading operations
        pass

# Get keys for account
keys = await utils["api_keys"].get_keys_for_account(account.id)
```

### Audit Logging

```python
from database.models.audit_logs import AuditAction, AuditResult

# Log trading event
await utils["audit_logs"].log_event(
    action=AuditAction.TRADE_PLACE_ORDER,
    result=AuditResult.SUCCESS,
    tiger_account_id=account.id,
    api_key_id=api_key.id,
    user_id="trader1",
    ip_address="192.168.1.100",
    details={
        "symbol": "AAPL",
        "quantity": 100,
        "price": 150.00,
        "order_type": "limit"
    }
)

# Get recent security events
security_events = await utils["audit_logs"].get_security_events(hours=24)
```

### Token Management

```python
from database.models.token_status import RefreshTrigger

# Create token refresh operation
token_status = await utils["token_status"].create_refresh_operation(
    tiger_account_id=account.id,
    trigger=RefreshTrigger.SCHEDULED
)

# Update refresh status
token_status.start_refresh()
# ... perform refresh ...
token_status.complete_refresh(
    success=True,
    new_token_expires_at=new_expiry,
    new_token_hash="hash_of_new_token"
)
```

## Database Management CLI

The package includes a comprehensive management CLI:

```bash
# Navigate to database package
cd packages/database

# Initialize database
python manage_db.py init

# Run migrations
python manage_db.py migrate

# Create new migration
python manage_db.py revision -m "Add new feature"

# Health check
python manage_db.py health-check

# Create test account
python manage_db.py create-account \
  --account-name "Test Account" \
  --account-number "12345678" \
  --tiger-id "test_id" \
  --private-key "test_key"

# Create API key
python manage_db.py create-api-key \
  --name "Test Key" \
  --scopes "mcp:read,mcp:write"

# List accounts and keys
python manage_db.py list-accounts
python manage_db.py list-api-keys
```

## Migrations

### Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade 001

# Downgrade one step
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

### Creating Migrations

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Add new table"

# Empty migration template
alembic revision -m "Custom changes"
```

## Security Considerations

### Credential Encryption
- All sensitive data (Tiger ID, private keys, tokens) should be encrypted at rest
- Use proper encryption keys and key management
- Consider using database-level encryption features

### Access Control
- API keys should have minimal required scopes
- Use IP restrictions and rate limiting
- Monitor audit logs for suspicious activity
- Rotate API keys regularly

### Database Security
- Use SSL connections in production
- Implement proper database access controls
- Regular security audits and updates
- Backup encryption and secure storage

## Performance

### Indexes
All models include comprehensive indexing for:
- Primary keys and foreign keys
- Query-heavy fields (status, timestamps)
- Composite indexes for common query patterns
- Partial indexes for filtered queries

### Connection Pooling
- Configurable pool sizes
- Connection recycling
- Health checks and recovery

### Query Optimization
- Relationship loading strategies
- Pagination support
- Efficient bulk operations
- Query result caching

## Development

### Adding New Models

1. Create model file in `src/database/models/`
2. Add imports to `src/database/models/__init__.py`
3. Create migration: `alembic revision --autogenerate -m "Add model"`
4. Update utility classes if needed
5. Add to main `__init__.py` exports

### Testing

```python
# Use test database configuration
import pytest
from database import get_session, create_utils

@pytest.fixture
async def db_session():
    async with get_session() as session:
        yield session
        await session.rollback()  # Rollback after test

async def test_account_creation(db_session):
    utils = create_utils(db_session)
    account = await utils["accounts"].create(
        TigerAccount,
        account_name="Test",
        account_number="test123"
        # ... other fields
    )
    assert account.account_name == "Test"
```

### Database Schema Design

The schema follows these principles:
- UUID primary keys for all entities
- Automatic timestamps (created_at, updated_at)
- Rich metadata with JSONB fields
- Comprehensive audit trails
- Proper foreign key relationships
- Check constraints for data integrity