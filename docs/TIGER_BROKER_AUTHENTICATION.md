# Tiger Broker Authentication Guide

This guide explains how Tiger Broker's authentication system works and how to integrate it with the Tiger MCP system.

## 🔐 Understanding Tiger's Authentication System

Tiger Brokers uses a **multi-layered authentication system** with the following components:

### 1. Core Identity Components

| Component | Description | Example | Required |
|-----------|-------------|---------|----------|
| **Tiger ID** | Your unique developer ID from Tiger | `20154747` | ✅ Yes |
| **Account** | Your trading account number | `67686635` | ✅ Yes |
| **License** | Your broker license/region | `TBHK`, `TBSG`, `TBNZ` | ✅ Yes |
| **Private Key** | RSA private key for API signing | PEM format key | ✅ Yes |
| **Environment** | Production or Sandbox | `PROD`, `SANDBOX` | ✅ Yes |
| **Token** | Session token (auto-refreshed) | Base64 encoded | ❌ Auto-generated |

### 2. Authentication Files

Tiger provides two configuration files when you register for API access:

#### `tiger_openapi_config.properties` - Main Configuration
```properties
private_key_pk1=MIICXQIBAAKBgQDjFtUnVaz+c5uk6on8E8sij6sub4aP...
private_key_pk8=MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAA...
tiger_id=20154747
account=67686635
license=TBHK
env=PROD
```

#### `tiger_openapi_token.properties` - Session Token
```properties
token=MTczNjMyNzcxMDQ1NCwxNzM3NjIzNzEwNDU03YvvaR9OG6H2iIw1Re6Srg==
```

## 🏗️ How Tiger MCP Handles Authentication

### 1. Multi-Source Configuration Loading

The Tiger MCP system loads configuration from multiple sources in priority order:

1. **Database** (encrypted storage) - Highest priority
2. **Properties files** (Tiger's standard format)
3. **Environment variables** - Lowest priority

```python
# Priority: Database → Properties → Environment
tiger_config = await load_tiger_configuration(account_id)
```

### 2. Account Model Structure

```python
class TigerAccount:
    # Core Tiger Identity
    tiger_id: str           # From Tiger website
    account: str            # Your account number
    license: TigerLicense   # TBHK, TBSG, TBNZ, etc.
    environment: str        # PROD or SANDBOX
    
    # Authentication
    encrypted_credentials: str  # Private key (encrypted)
    private_key_format: str     # "PK1" or "PK8"
    
    # Token Management
    token: Optional[str]         # Current session token
    token_expires_at: datetime   # Token expiration
    
    # Account Settings
    account_type: str           # "trading", "data", "both"
    is_default_trading: bool
    is_default_data: bool
```

## 📋 Step-by-Step Setup Guide

### Step 1: Get Your Tiger API Credentials

1. **Login to Tiger Brokers Website**
   - Go to your Tiger account dashboard
   - Navigate to "API" or "Developer" section

2. **Request API Access**
   - Apply for API access if you haven't already
   - Wait for approval (usually 1-3 business days)

3. **Download Credential Files**
   - Download `tiger_openapi_config.properties`
   - Download `tiger_openapi_token.properties`
   - Keep these files secure - they contain sensitive credentials

### Step 2: Understanding Your Credentials

Open your `tiger_openapi_config.properties` file and identify:

```properties
# Your unique Tiger developer ID
tiger_id=20154747

# Your trading account number  
account=67686635

# Your broker license (determines region/features)
license=TBHK

# Environment (PROD for live trading, SANDBOX for testing)
env=PROD

# Private keys (both formats provided for compatibility)
private_key_pk1=MII...
private_key_pk8=MII...
```

### Step 3: Choose Your Integration Method

#### Option A: Import from Properties Files (Recommended)
```bash
# Migrate from existing dashboard
python scripts/migrate_from_dashboard.py --dashboard-path ./references/tiger_dashboard

# Or import from properties files directly
python scripts/migrate_from_dashboard.py --config-path /path/to/properties/files
```

#### Option B: Add Account via MCP Tools
```python
# Use MCP tool to add account
await tiger_add_account(
    name="My Tiger Account",
    tiger_id="20154747",
    account="67686635", 
    license="TBHK",
    private_key="-----BEGIN RSA PRIVATE KEY-----\nMII...",
    environment="PROD",
    account_type="both"
)
```

#### Option C: Manual Database Entry
```python
from shared.account_manager import TigerAccountManager
from shared.tiger_config import TigerConfig

tiger_config = TigerConfig(
    tiger_id="20154747",
    account="67686635",
    license="TBHK",
    private_key="-----BEGIN RSA PRIVATE KEY-----\nMII...",
    environment="PROD"
)

account = await account_manager.create_account_from_properties(
    name="My Tiger Account",
    tiger_config=tiger_config
)
```

## 🔐 Security Best Practices

### 1. Credential Storage
- ✅ **DO**: Use encrypted database storage (our default)
- ✅ **DO**: Keep `.properties` files secure with proper file permissions
- ❌ **DON'T**: Store credentials in plain text configuration files
- ❌ **DON'T**: Commit credentials to version control

### 2. Token Management  
- ✅ **DO**: Let the system auto-refresh tokens
- ✅ **DO**: Monitor token expiration and refresh failures
- ❌ **DON'T**: Manually manage tokens unless necessary

### 3. Environment Separation
- ✅ **DO**: Use SANDBOX for development and testing
- ✅ **DO**: Use PROD only for live trading
- ❌ **DON'T**: Mix sandbox and production credentials

## 🧪 Testing Your Setup

### 1. Validate Configuration
```bash
# Test configuration loading
tiger-mcp-server validate-config

# Test Tiger connection
python scripts/test_tiger_connection.py
```

### 2. Use MCP Tools
```python
# List accounts
accounts = await tiger_list_accounts()

# Test connection
status = await tiger_get_account_status("your-account-id")

# Get account info (requires valid credentials)
info = await tiger_get_account_info("your-account-id")
```

### 3. Monitor Logs
```bash
# Run with debug logging
tiger-mcp-server --log-level DEBUG

# Monitor token refresh
tail -f logs/tiger-mcp.log | grep "token"
```

## 🔧 Troubleshooting

### Common Issues

#### 1. "Invalid Tiger ID or Account"
- **Cause**: Incorrect `tiger_id` or `account` in configuration
- **Solution**: Verify values match exactly with Tiger's provided files

#### 2. "Private Key Format Error"
- **Cause**: Private key format or encoding issues
- **Solution**: Use the exact private key from Tiger's `.properties` file

#### 3. "License Not Supported"  
- **Cause**: Invalid or unsupported license type
- **Solution**: Use exact license from Tiger (TBHK, TBSG, TBNZ, etc.)

#### 4. "Token Expired or Invalid"
- **Cause**: Token expiration or corruption
- **Solution**: Delete token and let system re-authenticate

#### 5. "Environment Mismatch"
- **Cause**: Using PROD credentials in SANDBOX or vice versa
- **Solution**: Ensure environment setting matches your account type

### Debug Steps

1. **Check Credential Loading**
   ```bash
   python -c "from shared.tiger_config import TigerPropertiesManager; print(TigerPropertiesManager('.').load_config())"
   ```

2. **Verify Database Storage**
   ```bash
   tiger-mcp-server --validate
   ```

3. **Test API Connection**
   ```python
   # Test basic connection
   config = TigerOpenClientConfig()
   client = TradeClient(config)
   assets = client.get_prime_assets()
   ```

## 📚 Additional Resources

- **Tiger Open API Documentation**: [https://www.tigerfintech.com/openapi](https://www.tigerfintech.com/openapi)
- **Tiger Python SDK**: [GitHub Repository](https://github.com/tigerfintech/openapi-python-sdk)
- **Account Types**: Different licenses support different markets and features
- **Rate Limits**: Be aware of API rate limits (vary by license type)

## 🤝 Getting Help

If you encounter issues:

1. **Check Logs**: Enable debug logging to see detailed error information
2. **Verify Credentials**: Ensure all Tiger-provided values are correct
3. **Test Isolation**: Test each component (config loading, authentication, API calls) separately
4. **Contact Support**: Tiger support for credential issues, project issues for system bugs

---

*This guide covers the authentication system for Tiger Brokers API integration. Keep your credentials secure and never share them publicly.*