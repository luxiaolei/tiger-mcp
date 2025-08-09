# Tiger MCP Shared Security Package

Advanced encryption and security services for the Tiger MCP system, providing AES-256-GCM encryption, JWT token management, password hashing, rate limiting, and security audit capabilities.

## Features

### 🔐 Encryption Service
- **AES-256-GCM Encryption**: Authenticated encryption with associated data (AEAD)
- **PBKDF2 Key Derivation**: Secure key derivation with configurable iterations
- **Key Rotation Support**: Version-controlled encryption keys with rotation capability
- **Environment-based Key Management**: Secure master key storage via environment variables
- **Tiger API Credential Encryption**: Specialized functions for Tiger broker credentials

### 🛡️ Security Service
- **Password Hashing**: Argon2 and bcrypt support with automatic algorithm selection
- **JWT Token Management**: Create, verify, and refresh JWT tokens with configurable expiration
- **API Key Generation**: Cryptographically secure API key generation with SHA-256 hashing
- **Rate Limiting**: Sliding window rate limiting with per-key tracking
- **Security Audit**: Comprehensive security event logging with risk level classification

### ⚙️ Configuration Management
- **Environment Variable Support**: Automatic loading of .env files with validation
- **Security Defaults**: Production-ready security configuration defaults
- **Database Configuration**: Connection string management with SSL support
- **Logging Configuration**: Structured logging with security event support

### 🔧 Utility Functions
- **Secure Password Generation**: Cryptographically secure password generation
- **Tiger Account Encryption**: Convenient functions for Tiger broker account data
- **Token Validation**: JWT token scope and account access validation
- **Security Metrics**: Comprehensive security monitoring and reporting

## Installation

Install the package in development mode:

```bash
cd packages/shared
pip install -e .
```

Or install from the project root:

```bash
pip install -e packages/shared/
```

## Quick Start

### 1. Environment Setup

Create a `.env` file or set environment variables:

```bash
# Required for production
ENCRYPTION_MASTER_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
JWT_SECRET=your-jwt-secret-key-here-minimum-32-characters

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/tiger_mcp

# Optional configuration
ENVIRONMENT=production
PBKDF2_ITERATIONS=100000
PASSWORD_HASH_ALGORITHM=argon2
```

Generate secure keys using the utility:

```python
from shared import KeyManager

km = KeyManager()
print("Master Key:", km.generate_master_key())
print("JWT Secret:", km.generate_jwt_secret())
```

### 2. Basic Encryption Usage

```python
from shared import get_encryption_service, encrypt_tiger_credentials

# Get encryption service
encryption = get_encryption_service()

# Encrypt sensitive data
encrypted = encryption.encrypt("sensitive data")
print(f"Encrypted with key version: {encrypted.key_version}")

# Decrypt data
decrypted = encryption.decrypt_to_string(encrypted)
print(f"Decrypted: {decrypted}")

# Encrypt Tiger credentials
credentials = encrypt_tiger_credentials(
    tiger_id="your_tiger_id",
    private_key="your_private_key",
    access_token="your_access_token"
)
```

### 3. Security Service Usage

```python
from shared import get_security_service, create_jwt_token

# Get security service
security = get_security_service()

# Hash password
password_hash = security.hash_password("user_password")

# Verify password
is_valid = security.verify_password("user_password", password_hash)

# Generate API key
api_key, key_hash = security.generate_api_key("tk")  # tk_xxxxx format

# Create JWT token
token = create_jwt_token(
    subject="user_id",
    scopes=["read", "write"],
    expires_in=3600
)

# Verify token
payload = security.verify_token(token)
print(f"Token subject: {payload.sub}")
print(f"Token scopes: {payload.scopes}")
```

### 4. Tiger Account Integration

```python
from shared import encrypt_tiger_account_data, decrypt_tiger_account_data

# Encrypt Tiger account data for database storage
encrypted_data = encrypt_tiger_account_data(
    tiger_id="12345",
    private_key="-----BEGIN PRIVATE KEY-----\n...",
    access_token="access_token_here",
    refresh_token="refresh_token_here"
)

# Store encrypted_data in database...

# Later, decrypt for API usage
credentials = decrypt_tiger_account_data(encrypted_data)
tiger_id = credentials["tiger_id"]
private_key = credentials["private_key"]
```

### 5. Rate Limiting

```python
from shared import verify_rate_limit, get_security_service

# Check rate limit
api_key_id = "api_key_12345"
if verify_rate_limit(api_key_id, max_requests=100, window_size=3600):
    # Process request
    print("Request allowed")
else:
    # Rate limit exceeded
    print("Rate limit exceeded")

# Get rate limit status
security = get_security_service()
status = security.get_rate_limit_status(api_key_id)
print(f"Requests remaining: {status['requests_remaining']}")
```

### 6. Security Auditing

```python
from shared import audit_security_event, get_security_metrics

# Log security event
audit_security_event(
    event_type="api_key_created",
    api_key_id="key_123",
    details={"scopes": ["read", "write"]},
    risk_level="low",
    source_ip="192.168.1.1"
)

# Get security metrics
metrics = get_security_metrics()
print(f"Total events: {metrics['security_summary']['total_events']}")
print(f"Critical events: {metrics['security_summary']['critical_events_count']}")
```

## Configuration

### Security Configuration

All security settings can be configured via environment variables:

```python
from shared import get_security_config

config = get_security_config()
print(f"PBKDF2 iterations: {config.pbkdf2_iterations}")
print(f"Password algorithm: {config.password_hash_algorithm}")
print(f"JWT expiration: {config.jwt_access_token_expire}")
```

### Database Configuration

```python
from shared import get_database_config

db_config = get_database_config()
connection_string = db_config.connection_string
print(f"Database: {connection_string}")
```

### Generate Configuration Template

```python
from shared import generate_env_template

# Generate .env template with secure defaults
generate_env_template(".env.template")
```

## Security Best Practices

### 1. Key Management
- Use strong, randomly generated master keys (256-bit)
- Rotate encryption keys regularly
- Store keys securely (environment variables, secrets management)
- Never commit keys to version control

### 2. Password Security
- Use Argon2 for new password hashes
- Set appropriate PBKDF2 iterations (100,000+)
- Implement password strength requirements
- Consider password breach detection

### 3. Token Security
- Use short expiration times for access tokens
- Implement token refresh mechanisms
- Validate token scopes and account access
- Log all token operations

### 4. Rate Limiting
- Implement per-API-key rate limiting
- Use sliding window algorithms
- Monitor for unusual usage patterns
- Implement progressive penalties

### 5. Audit and Monitoring
- Log all security-relevant events
- Monitor for critical and high-risk events
- Implement alerting for security incidents
- Retain audit logs per compliance requirements

## Testing

Run the test suite to verify functionality:

```bash
python packages/shared/test_encryption.py
```

The test suite covers:
- Basic encryption/decryption
- Tiger credential encryption
- Key rotation
- Password hashing and verification
- JWT token lifecycle
- API key generation and verification
- Rate limiting
- Security auditing

## Integration with Database Models

The encryption service integrates seamlessly with the database models:

```python
from shared import encrypt_tiger_account_data, EncryptedData
from database.models import TigerAccount

# When creating a new account
encrypted_creds = encrypt_tiger_account_data(
    tiger_id=form_data.tiger_id,
    private_key=form_data.private_key
)

account = TigerAccount(
    account_name=form_data.name,
    account_number=form_data.number,
    tiger_id=encrypted_creds["tiger_id"].json(),  # Store as JSON
    private_key=encrypted_creds["private_key"].json()
)
```

## Error Handling

The package provides specific exceptions for different error types:

```python
from shared import EncryptionError, DecryptionError, TokenError

try:
    encrypted = encryption_service.encrypt(data)
except EncryptionError as e:
    print(f"Encryption failed: {e}")

try:
    payload = security_service.verify_token(token)
except TokenError as e:
    print(f"Token validation failed: {e}")
```

## Development

### Code Structure

```
src/shared/
├── __init__.py          # Public API exports
├── config.py           # Configuration management
├── encryption.py       # AES-256-GCM encryption service
├── security.py         # JWT, hashing, rate limiting, audit
└── utils.py            # Convenience functions
```

### Adding New Features

1. Add new functionality to appropriate module
2. Update `__init__.py` exports
3. Add tests to `test_encryption.py`
4. Update documentation

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENCRYPTION_MASTER_KEY` | 64-char hex master key | Generated | Yes (prod) |
| `JWT_SECRET` | JWT signing secret | Generated | Yes (prod) |
| `ENVIRONMENT` | Environment name | development | No |
| `PBKDF2_ITERATIONS` | Key derivation iterations | 100000 | No |
| `PASSWORD_HASH_ALGORITHM` | argon2 or bcrypt | argon2 | No |
| `JWT_ACCESS_TOKEN_EXPIRE` | Token expiration (seconds) | 3600 | No |
| `DEFAULT_RATE_LIMIT_HOUR` | Hourly rate limit | 1000 | No |

## License

This package is part of the Tiger MCP system and follows the same licensing terms.