# Tiger Authentication Setup Guide

This guide explains how to properly set up Tiger Broker authentication for the Tiger MCP system, based on Tiger's official SDK requirements.

## Overview

Tiger Broker uses a specific authentication system that requires:
- **Tiger ID**: Developer application ID from Tiger's developer portal
- **Account Number**: Your trading account number (can be paper or live)
- **License**: Broker license identifying your region (TBHK, TBSG, TBNZ, etc.)
- **Private Key**: RSA private key for API signing (PK1 or PK8 format)
- **Environment**: PROD for production, SANDBOX for testing

## Getting Your Credentials

### 1. Register as Tiger Developer

1. Go to [Tiger Open API Portal](https://www.itiger.com/openapi/info)
2. Register as a developer and create an application
3. Note down your **Tiger ID** (application ID)

### 2. Generate RSA Key Pair

Tiger requires RSA private keys for API authentication. You can generate them using OpenSSL:

```bash
# Generate private key (PK1 format)
openssl genrsa -out rsa_private_key.pem 1024

# Generate public key
openssl rsa -in rsa_private_key.pem -pubout -out rsa_public_key.pem

# Optional: Convert to PK8 format
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in rsa_private_key.pem -out rsa_private_key_pk8.pem
```

### 3. Upload Public Key to Tiger

1. Log into Tiger Open API portal
2. Go to your application settings
3. Upload the `rsa_public_key.pem` file
4. Wait for approval (usually 1-2 business days)

### 4. Get Your Account Details

- **Account Number**: Find in Tiger trading app or web platform
- **License**: Depends on your region:
  - `TBHK`: Tiger Brokers Hong Kong
  - `TBSG`: Tiger Brokers Singapore  
  - `TBNZ`: Tiger Brokers New Zealand
  - `TBAU`: Tiger Brokers Australia
  - `TBUK`: Tiger Brokers UK

## Configuration Methods

The Tiger MCP system supports multiple ways to configure authentication:

### Method 1: Tiger Properties Files (Recommended)

This is Tiger's standard configuration method using `.properties` files.

#### Create `tiger_openapi_config.properties`

```properties
private_key_pk1=-----BEGIN RSA PRIVATE KEY-----\nMIICXQIBAAKBgQDj...your_private_key_here...\n-----END RSA PRIVATE KEY-----
tiger_id=20154747
account=67686635
license=TBHK
env=PROD
```

#### Create `tiger_openapi_token.properties`

```properties
token=
```

(This file will be auto-populated by Tiger SDK with access tokens)

**File Locations:**
- Place these files in your project root or specify path with `TIGER_PROPERTIES_PATH`
- The MCP server will automatically load from these files

### Method 2: Database Account Management

You can store encrypted credentials in the database using the account manager:

```python
from shared.account_manager import get_account_manager
from database.models.accounts import TigerLicense, TigerEnvironment, AccountType

manager = get_account_manager()

# Create account from properties files
account = await manager.create_account_from_properties(
    account_name="My Tiger Account",
    properties_path="./path/to/properties",  # Optional, defaults to current dir
    account_type=AccountType.STANDARD,
    is_default_trading=True
)

# Or create manually
account = await manager.create_account(
    account_name="My Tiger Account",
    account_number="67686635",
    tiger_id="20154747",
    private_key="-----BEGIN RSA PRIVATE KEY-----...",
    license=TigerLicense.TBHK,
    environment=TigerEnvironment.PROD,
    private_key_format="PK1"
)
```

### Method 3: Environment Variables (Fallback)

Set these environment variables as a fallback:

```bash
export TIGER_CLIENT_ID="20154747"
export TIGER_ACCOUNT="67686635"
export TIGER_LICENSE="TBHK"
export TIGER_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
export TIGER_SANDBOX="false"  # true for sandbox
```

## MCP Server Configuration

### Environment Variables

```bash
# Configuration method priority
export TIGER_USE_PROPERTIES="true"        # Use .properties files (default)
export TIGER_PROPERTIES_PATH="."          # Path to .properties files
export TIGER_DEFAULT_ACCOUNT_ID="uuid"    # Default account from database

# Logging
export LOG_LEVEL="INFO"
```

### Configuration Priority

The MCP server loads configuration in this order:
1. **Database account** (if `TIGER_DEFAULT_ACCOUNT_ID` is set)
2. **Properties files** (if `TIGER_USE_PROPERTIES=true`)
3. **Environment variables** (fallback)

## Testing Your Setup

### 1. Test Configuration Loading

```python
from shared.tiger_config import load_tiger_config_from_properties, validate_tiger_credentials

# Load config
config = load_tiger_config_from_properties("./path/to/properties")
print(f"Loaded config for account {config.account} ({config.license})")

# Validate
is_valid, errors = validate_tiger_credentials(config)
if not is_valid:
    print(f"Validation errors: {errors}")
```

### 2. Test MCP Tools

Once the MCP server is running, you can test using these tools:

```bash
# Get current Tiger configuration
mcp-tool get_tiger_config

# Validate API connection
mcp-tool validate_tiger_connection

# Get account information
mcp-tool get_account_info
```

### 3. Test Tiger SDK Directly

```python
from tigeropen.tiger_open_config import get_client_config
from tigeropen.trade.trade_client import TradeClient

# Using your properties files
config = get_client_config(
    private_key_path="./rsa_private_key.pem",
    tiger_id="20154747",
    account="67686635",
    sandbox_debug=False,  # False for production
    license="TBHK"
)

trade_client = TradeClient(config)
assets = trade_client.get_assets()
print(assets.data if assets.is_success() else assets.message)
```

## Common Issues and Solutions

### 1. "Invalid Private Key Format"
- Ensure your private key is in proper PEM format
- Check for correct `-----BEGIN RSA PRIVATE KEY-----` headers
- Try converting between PK1 and PK8 formats

### 2. "Tiger ID Not Found"
- Verify your Tiger ID is correct
- Ensure your developer application is approved
- Check that your public key was uploaded correctly

### 3. "Account Access Denied"
- Verify account number is correct
- Check that your Tiger ID has access to this account
- Ensure you're using the correct license for your region

### 4. "Token Refresh Failed"
- Check your internet connection
- Verify Tiger servers are accessible
- Ensure your private key matches the uploaded public key

### 5. "Properties File Not Found"
- Check file path and permissions
- Ensure files are named exactly `tiger_openapi_config.properties`
- Verify the MCP server has read access to the directory

## Security Best Practices

1. **Never commit private keys to version control**
2. **Use environment-specific configurations**
3. **Regularly rotate keys** (Tiger allows multiple keys)
4. **Monitor API usage** for unusual activity
5. **Use sandbox environment** for testing
6. **Encrypt credentials** when storing in database
7. **Limit account permissions** to minimum required

## Environment-Specific Setup

### Development
```properties
env=SANDBOX
```

### Production
```properties
env=PROD
```

### Testing
- Use paper trading accounts when available
- Set `env=SANDBOX` for all testing
- Never test with real money in development

## Support and Resources

- [Tiger Open API Documentation](https://www.itiger.com/openapi/docs)
- [Tiger Python SDK](https://github.com/tigerfintech/openapi-python-sdk)
- [Tiger Developer Portal](https://www.itiger.com/openapi/info)
- [OpenSSL Documentation](https://www.openssl.org/docs/)

## Example Complete Setup

Here's a complete example for Hong Kong users:

1. **Generate keys:**
```bash
openssl genrsa -out rsa_private_key.pem 1024
openssl rsa -in rsa_private_key.pem -pubout -out rsa_public_key.pem
```

2. **Create `tiger_openapi_config.properties`:**
```properties
private_key_pk1=-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDj...your_full_private_key_here...
-----END RSA PRIVATE KEY-----
tiger_id=20154747
account=67686635
license=TBHK
env=PROD
```

3. **Create empty `tiger_openapi_token.properties`:**
```properties
token=
```

4. **Set environment variables:**
```bash
export TIGER_USE_PROPERTIES="true"
export TIGER_PROPERTIES_PATH="."
export LOG_LEVEL="INFO"
```

5. **Test connection:**
```bash
# Start MCP server
python mcp-server/server.py

# In another terminal, test
echo '{"method": "get_tiger_config"}' | mcp-cli
```

This setup should work for most Tiger Broker regions. Adjust the `license` field according to your Tiger Broker region.