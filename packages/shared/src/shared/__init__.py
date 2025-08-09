"""
Shared utilities and security services for Tiger MCP system.

This package provides:
- AES-256-GCM encryption for sensitive data
- JWT token management
- Password hashing and verification
- Rate limiting utilities
- Security audit logging
- Configuration management
- Tiger account management with CRUD operations
- Token refresh automation and management
- Intelligent account routing for operations
"""

from .config import (
    AppConfig,
    DatabaseConfig,
    KeyManager,
    LoggingConfig,
    SecurityConfig,
    TigerAPIConfig,
    generate_env_template,
    get_config,
    get_database_config,
    get_logging_config,
    get_security_config,
    get_tiger_api_config,
    load_environment_config,
    setup_logging,
    validate_security_config,
)
from .encryption import (
    DecryptionError,
    EncryptedData,
    EncryptionError,
    EncryptionService,
    KeyDerivationError,
    KeyRotationInfo,
    decrypt_tiger_credentials,
    encrypt_tiger_credentials,
    get_encryption_service,
)
from .security import (
    AuditError,
    RateLimitError,
    SecurityAuditEvent,
    SecurityError,
    SecurityService,
    TokenError,
    TokenPayload,
    create_jwt_token,
    generate_secure_api_key,
    get_security_service,
    hash_api_key,
    verify_api_key_hash,
    verify_jwt_token,
)
from .utils import (
    audit_security_event,
    check_account_access,
    create_access_token,
    create_api_key_with_hash,
    create_database_connection_string,
    decrypt_tiger_account_data,
    encrypt_tiger_account_data,
    generate_secure_password,
    get_security_metrics,
    rotate_encryption_key,
    validate_encrypted_data,
    validate_token_scopes,
    verify_rate_limit,
)

# Optional imports - require database package
try:
    from .account_manager import (
        AccountManagerError,
        AccountNotFoundError,
        AccountValidationError,
        DefaultAccountError,
        TigerAccountManager,
        get_account_manager,
    )
    from .account_router import (
        AccountRouter,
        AccountRouterError,
        LoadBalanceStrategy,
        NoAccountsAvailableError,
        OperationNotSupportedError,
        OperationType,
        get_account_router,
    )
    from .token_manager import (
        TokenManager,
        TokenManagerError,
        TokenRateLimitError,
        TokenRefreshError,
        TokenValidationError,
        get_token_manager,
    )

    _database_imports_available = True
except ImportError:
    # Database-dependent imports not available
    _database_imports_available = False

    # Define placeholder classes for testing
    class AccountManagerError(Exception):
        pass

    class AccountNotFoundError(Exception):
        pass

    class AccountValidationError(Exception):
        pass

    class DefaultAccountError(Exception):
        pass

    class TigerAccountManager:
        pass

    class TokenManager:
        pass

    class TokenManagerError(Exception):
        pass

    class TokenRateLimitError(Exception):
        pass

    class TokenRefreshError(Exception):
        pass

    class TokenValidationError(Exception):
        pass

    class AccountRouter:
        pass

    class AccountRouterError(Exception):
        pass

    class LoadBalanceStrategy:
        pass

    class NoAccountsAvailableError(Exception):
        pass

    class OperationType:
        pass

    class OperationNotSupportedError(Exception):
        pass

    def get_account_manager(*args, **kwargs):
        raise ImportError("Account manager requires database package")

    def get_token_manager(*args, **kwargs):
        raise ImportError("Token manager requires database package")

    def get_account_router(*args, **kwargs):
        raise ImportError("Account router requires database package")


__version__ = "0.1.0"
__all__ = [
    # Configuration
    "AppConfig",
    "DatabaseConfig",
    "KeyManager",
    "LoggingConfig",
    "SecurityConfig",
    "TigerAPIConfig",
    "generate_env_template",
    "get_config",
    "get_database_config",
    "get_logging_config",
    "get_security_config",
    "get_tiger_api_config",
    "load_environment_config",
    "setup_logging",
    "validate_security_config",
    # Encryption
    "DecryptionError",
    "EncryptedData",
    "EncryptionError",
    "EncryptionService",
    "KeyDerivationError",
    "KeyRotationInfo",
    "decrypt_tiger_credentials",
    "encrypt_tiger_credentials",
    "get_encryption_service",
    # Security
    "AuditError",
    "RateLimitError",
    "SecurityAuditEvent",
    "SecurityError",
    "SecurityService",
    "TokenError",
    "TokenPayload",
    "create_jwt_token",
    "generate_secure_api_key",
    "get_security_service",
    "hash_api_key",
    "verify_api_key_hash",
    "verify_jwt_token",
    # Utilities
    "audit_security_event",
    "check_account_access",
    "create_access_token",
    "create_api_key_with_hash",
    "create_database_connection_string",
    "decrypt_tiger_account_data",
    "encrypt_tiger_account_data",
    "generate_secure_password",
    "get_security_metrics",
    "rotate_encryption_key",
    "validate_encrypted_data",
    "validate_token_scopes",
    "verify_rate_limit",
    # Account Management
    "AccountManagerError",
    "AccountNotFoundError",
    "AccountValidationError",
    "DefaultAccountError",
    "TigerAccountManager",
    "get_account_manager",
    # Token Management
    "TokenManager",
    "TokenManagerError",
    "TokenRateLimitError",
    "TokenRefreshError",
    "TokenValidationError",
    "get_token_manager",
    # Account Routing
    "AccountRouter",
    "AccountRouterError",
    "LoadBalanceStrategy",
    "NoAccountsAvailableError",
    "OperationType",
    "OperationNotSupportedError",
    "get_account_router",
]
