# Migration Guide: Updated Tiger Authentication

This guide helps you migrate from the previous Tiger authentication system to the new enhanced system that properly supports Tiger's official authentication requirements.

## What Changed

### Database Model Updates

The `TigerAccount` model has been enhanced with new required fields:

#### New Fields Added:
- `license`: Tiger broker license (TBHK, TBSG, TBNZ, etc.) - **REQUIRED**
- `private_key_format`: Specifies if private key is in PK1 or PK8 format - **REQUIRED**
- `environment`: Now uses proper enum (TigerEnvironment.PROD/SANDBOX) instead of strings

#### Changed Fields:
- `environment`: Changed from `string` to `TigerEnvironment` enum

### Configuration System Updates

#### New Configuration Methods:
1. **Tiger .properties files** (recommended - standard Tiger SDK format)
2. **Enhanced database storage** with proper encryption
3. **Environment variables** (fallback only)

#### MCP Server Updates:
- New configuration loading priority system
- Support for multiple authentication sources
- Enhanced error handling and validation
- New MCP tools for configuration management

## Migration Steps

### Step 1: Database Schema Migration

If you have existing accounts in the database, you'll need to run a migration to add the new required fields.

**Note**: This migration requires manual intervention as we need to determine the correct `license` for existing accounts.

```python
# Example migration script
from shared.account_manager import get_account_manager
from database.models.accounts import TigerLicense, TigerEnvironment

async def migrate_accounts():
    manager = get_account_manager()
    
    # Get all existing accounts
    accounts = await manager.list_accounts(include_inactive=True)
    
    for account in accounts:
        print(f"Migrating account: {account.account_name} ({account.account_number})")
        
        # You need to determine the correct license for each account
        # This depends on which Tiger Broker region the account belongs to
        license = input(f"Enter license for account {account.account_number} (TBHK/TBSG/TBNZ/TBAU/TBUK): ")
        
        # Update account with new fields
        updates = {
            'license': TigerLicense(license),
            'private_key_format': 'PK1',  # Assume PK1 format for existing keys
            'environment': TigerEnvironment.PROD if account.environment == 'production' else TigerEnvironment.SANDBOX
        }
        
        await manager.update_account(account.id, updates)
        print(f"✓ Migrated {account.account_name}")

# Run the migration
import asyncio
asyncio.run(migrate_accounts())
```

### Step 2: Update Existing Configurations

#### If Using Environment Variables Only:

**Old format:**
```bash
export TIGER_CLIENT_ID="20154747"
export TIGER_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
export TIGER_ACCOUNT="67686635"
export TIGER_SANDBOX="false"
```

**New format (add license):**
```bash
export TIGER_CLIENT_ID="20154747"
export TIGER_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
export TIGER_ACCOUNT="67686635"
export TIGER_LICENSE="TBHK"  # ← NEW: Add your Tiger broker license
export TIGER_SANDBOX="false"
```

#### Migrate to Properties Files (Recommended):

Create `tiger_openapi_config.properties`:
```properties
tiger_id=20154747
account=67686635
license=TBHK
env=PROD
private_key_pk1=-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDj...your_private_key_here...
-----END RSA PRIVATE KEY-----
```

Create empty `tiger_openapi_token.properties`:
```properties
token=
```

### Step 3: Update MCP Server Configuration

#### New Environment Variables:

```bash
# Enable properties file usage (default: true)
export TIGER_USE_PROPERTIES="true"

# Path to properties files (default: current directory)
export TIGER_PROPERTIES_PATH="."

# Optional: Use specific database account
export TIGER_DEFAULT_ACCOUNT_ID="your-account-uuid"
```

#### Update Your Startup Scripts:

**Old:**
```bash
python mcp-server/server.py
```

**New (no changes needed, but now supports more options):**
```bash
# Option 1: Use properties files (default)
TIGER_USE_PROPERTIES=true python mcp-server/server.py

# Option 2: Use specific database account
TIGER_DEFAULT_ACCOUNT_ID="uuid-here" python mcp-server/server.py

# Option 3: Custom properties path
TIGER_PROPERTIES_PATH="/path/to/config" python mcp-server/server.py
```

### Step 4: Test Your Migration

#### 1. Verify Configuration Loading:

```bash
# Test configuration
python -c "
from shared.tiger_config import load_tiger_config_from_properties
config = load_tiger_config_from_properties()
print(f'Config loaded: {config.account} @ {config.license}')
"
```

#### 2. Test MCP Tools:

```bash
# Start MCP server
python mcp-server/server.py

# In another terminal, test new tools
echo '{"method": "get_tiger_config"}' | your-mcp-client
echo '{"method": "validate_tiger_connection"}' | your-mcp-client
```

#### 3. Verify Account Access:

```bash
# Test account info (should now show license and environment)
echo '{"method": "get_account_info"}' | your-mcp-client
```

## Breaking Changes

### 1. Database Schema Changes

- **`license` field**: Now required, must be set for all accounts
- **`private_key_format` field**: Now required, defaults to "PK1"
- **`environment` field**: Changed from string to enum

### 2. API Changes

#### TigerAccountManager.create_account():

**Old signature:**
```python
async def create_account(
    self,
    account_name: str,
    account_number: str,
    tiger_id: str,
    private_key: str,
    account_type: AccountType = AccountType.STANDARD,
    environment: str = "sandbox",  # ← String
    # ... other params
) -> TigerAccount:
```

**New signature:**
```python
async def create_account(
    self,
    account_name: str,
    account_number: str,
    tiger_id: str,
    private_key: str,
    license: TigerLicense,  # ← NEW: Required
    account_type: AccountType = AccountType.STANDARD,
    environment: TigerEnvironment = TigerEnvironment.SANDBOX,  # ← Enum
    private_key_format: str = "PK1",  # ← NEW: Optional
    # ... other params
) -> TigerAccount:
```

#### TigerAccountManager.list_accounts():

**New parameter:**
```python
async def list_accounts(
    self,
    account_type: Optional[AccountType] = None,
    status: Optional[AccountStatus] = None,
    environment: Optional[TigerEnvironment] = None,  # ← Now enum
    license: Optional[TigerLicense] = None,  # ← NEW: Filter by license
    include_inactive: bool = False,
) -> List[TigerAccount]:
```

### 3. Configuration Validation

The new system includes enhanced validation:
- Private key format validation
- License validation against known Tiger licenses
- Environment validation
- Complete credential validation before account creation

## New Features

### 1. Properties File Support

Full support for Tiger's standard `.properties` file format, allowing seamless integration with other Tiger SDK applications.

### 2. Enhanced Account Management

```python
# Import account from existing properties
account = await manager.create_account_from_properties(
    account_name="Migrated Account",
    properties_path="./tiger-config/"
)

# Export account to properties
await manager.export_account_to_properties(
    account.id,
    properties_path="./exported-config/",
    include_token=True
)
```

### 3. New MCP Tools

- `get_tiger_config`: Get current configuration details
- `validate_tiger_connection`: Test API connectivity
- Enhanced `get_account_info`: Now includes license and environment

### 4. Multiple Authentication Sources

Configuration priority:
1. Database account (if `TIGER_DEFAULT_ACCOUNT_ID` set)
2. Properties files (if `TIGER_USE_PROPERTIES=true`)
3. Environment variables (fallback)

## Troubleshooting

### "Missing license field" Error

**Problem**: Existing accounts missing required `license` field.

**Solution**: Run the migration script above to add license information to existing accounts.

### "Invalid environment value" Error  

**Problem**: Database contains old string values ("sandbox"/"production") instead of enum values.

**Solution**: Update accounts with proper enum values:
```python
updates = {
    'environment': TigerEnvironment.PROD if old_env == 'production' else TigerEnvironment.SANDBOX
}
await manager.update_account(account.id, updates)
```

### "Properties file not found" Error

**Problem**: MCP server can't find `.properties` files.

**Solution**: 
1. Check file path: `TIGER_PROPERTIES_PATH`
2. Ensure files exist and have correct names
3. Check file permissions

### "Invalid Tiger configuration" Error

**Problem**: Configuration validation fails.

**Solution**:
1. Verify all required fields are present
2. Check private key format (must include headers)
3. Validate license value against supported licenses
4. Use the validation tools:

```python
from shared.tiger_config import validate_tiger_credentials
is_valid, errors = validate_tiger_credentials(config)
if not is_valid:
    print(f"Validation errors: {errors}")
```

## Support

If you encounter issues during migration:

1. **Check the logs**: Set `LOG_LEVEL=DEBUG` for detailed information
2. **Validate step by step**: Use the testing commands in each migration step
3. **Review the setup guide**: See `TIGER_AUTHENTICATION_SETUP.md` for complete setup instructions
4. **Test with minimal config**: Start with a simple `.properties` file setup

## Example: Complete Migration

Here's a complete example migrating an existing setup:

### Before (Environment Variables):
```bash
export TIGER_CLIENT_ID="20154747"
export TIGER_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIC..."
export TIGER_ACCOUNT="67686635"  
export TIGER_SANDBOX="false"
```

### After (Properties Files):

**tiger_openapi_config.properties:**
```properties
tiger_id=20154747
account=67686635
license=TBHK
env=PROD
private_key_pk1=-----BEGIN RSA PRIVATE KEY-----
MIIC...
-----END RSA PRIVATE KEY-----
```

**tiger_openapi_token.properties:**
```properties
token=
```

**.env updates:**
```bash
TIGER_USE_PROPERTIES=true
TIGER_PROPERTIES_PATH=.
LOG_LEVEL=INFO
```

This migration provides better security, compatibility with Tiger's standard tools, and enhanced features while maintaining backward compatibility where possible.