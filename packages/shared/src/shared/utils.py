"""
Utility functions for the Tiger MCP encryption service.

Provides convenience functions for common operations like credential
encryption, key management, and security validations.
"""

import secrets
import string
from typing import Dict, List, Optional, Tuple

from .config import get_security_config
from .encryption import EncryptedData, get_encryption_service
from .security import TokenPayload, get_security_service


def generate_secure_password(
    length: int = 16, include_symbols: bool = True, exclude_ambiguous: bool = True
) -> str:
    """
    Generate a cryptographically secure password.

    Args:
        length: Password length
        include_symbols: Include symbols in password
        exclude_ambiguous: Exclude ambiguous characters (0, O, I, l, etc.)

    Returns:
        Secure random password
    """
    # Character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    if exclude_ambiguous:
        # Remove ambiguous characters
        lowercase = lowercase.replace("l", "")
        uppercase = uppercase.replace("O", "").replace("I", "")
        digits = digits.replace("0", "").replace("1", "")
        symbols = symbols.replace("|", "").replace(":", "").replace(";", "")

    # Build character set
    charset = lowercase + uppercase + digits
    if include_symbols:
        charset += symbols

    # Ensure password has at least one character from each required set
    password_chars = []

    # Add required characters
    password_chars.append(secrets.choice(lowercase))
    password_chars.append(secrets.choice(uppercase))
    password_chars.append(secrets.choice(digits))

    if include_symbols:
        password_chars.append(secrets.choice(symbols))

    # Fill remaining length with random characters
    remaining_length = length - len(password_chars)
    for _ in range(remaining_length):
        password_chars.append(secrets.choice(charset))

    # Shuffle the password characters
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)


def encrypt_tiger_account_data(
    tiger_id: str,
    private_key: str,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
) -> Dict[str, EncryptedData]:
    """
    Encrypt Tiger account credentials for database storage.

    Args:
        tiger_id: Tiger account ID
        private_key: Private key for Tiger API
        access_token: Optional access token
        refresh_token: Optional refresh token

    Returns:
        Dictionary mapping field names to encrypted data
    """
    service = get_encryption_service()

    encrypted_data = {
        "tiger_id": service.encrypt(tiger_id),
        "private_key": service.encrypt(private_key),
    }

    if access_token:
        encrypted_data["access_token"] = service.encrypt(access_token)

    if refresh_token:
        encrypted_data["refresh_token"] = service.encrypt(refresh_token)

    return encrypted_data


def decrypt_tiger_account_data(
    encrypted_data: Dict[str, EncryptedData],
) -> Dict[str, str]:
    """
    Decrypt Tiger account credentials from database storage.

    Args:
        encrypted_data: Dictionary mapping field names to encrypted data

    Returns:
        Dictionary mapping field names to decrypted values
    """
    service = get_encryption_service()

    decrypted_data = {}
    for field_name, encrypted_value in encrypted_data.items():
        decrypted_data[field_name] = service.decrypt_to_string(encrypted_value)

    return decrypted_data


def create_api_key_with_hash(
    name: str,
    scopes: List[str],
    description: Optional[str] = None,
    prefix: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Create API key with hash for database storage.

    Args:
        name: Human-readable key name
        scopes: List of API key scopes
        description: Optional description
        prefix: Optional key prefix (defaults to config)

    Returns:
        Tuple of (api_key, key_hash, key_prefix)
    """
    config = get_security_config()
    security_service = get_security_service()

    key_prefix = prefix or config.api_key_prefix
    api_key, key_hash = security_service.generate_api_key(key_prefix)

    # Extract display prefix
    display_prefix = api_key[: config.api_key_prefix_display_length]

    return api_key, key_hash, display_prefix


def create_access_token(
    api_key_id: str,
    scopes: List[str],
    account_id: Optional[str] = None,
    expires_in: Optional[int] = None,
) -> str:
    """
    Create JWT access token for API key.

    Args:
        api_key_id: API key ID as subject
        scopes: List of access scopes
        account_id: Optional Tiger account ID
        expires_in: Optional custom expiration in seconds

    Returns:
        JWT access token
    """
    config = get_security_config()
    security_service = get_security_service()

    expires = expires_in or config.jwt_access_token_expire

    return security_service.create_token(
        subject=api_key_id,
        scopes=scopes,
        expires_in=expires,
        account_id=account_id,
        api_key_id=api_key_id,
    )


def validate_token_scopes(
    token_payload: TokenPayload, required_scopes: List[str], require_all: bool = True
) -> bool:
    """
    Validate that token has required scopes.

    Args:
        token_payload: Decoded JWT token payload
        required_scopes: List of required scopes
        require_all: Whether all scopes are required (vs. any)

    Returns:
        True if token has required scopes
    """
    token_scopes = set(token_payload.scopes)
    required_scopes_set = set(required_scopes)

    if require_all:
        return required_scopes_set.issubset(token_scopes)
    else:
        return bool(required_scopes_set.intersection(token_scopes))


def check_account_access(token_payload: TokenPayload, target_account_id: str) -> bool:
    """
    Check if token has access to specific Tiger account.

    Args:
        token_payload: Decoded JWT token payload
        target_account_id: Target account ID to check access for

    Returns:
        True if token can access the account
    """
    # If token is not bound to any account, it can access any account
    # (assuming it has the right scopes)
    if not token_payload.account_id:
        return True

    # If token is bound to an account, it can only access that account
    return token_payload.account_id == target_account_id


def audit_security_event(
    event_type: str,
    api_key_id: Optional[str] = None,
    account_id: Optional[str] = None,
    details: Optional[Dict] = None,
    risk_level: str = "low",
    source_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    Log security audit event.

    Args:
        event_type: Type of security event
        api_key_id: API key ID involved
        account_id: Account ID involved
        details: Additional event details
        risk_level: Risk level (low, medium, high, critical)
        source_ip: Source IP address
        user_agent: User agent string
    """
    security_service = get_security_service()

    security_service.audit_event(
        event_type=event_type,
        details=details or {},
        risk_level=risk_level,
        source_ip=source_ip,
        user_agent=user_agent,
        api_key_id=api_key_id,
        account_id=account_id,
    )


def verify_rate_limit(
    key: str, max_requests: Optional[int] = None, window_size: Optional[int] = None
) -> bool:
    """
    Check rate limit for a key.

    Args:
        key: Rate limit key (e.g., IP address, API key ID)
        max_requests: Max requests (defaults to config)
        window_size: Window size in seconds (defaults to config)

    Returns:
        True if request is allowed
    """
    config = get_security_config()
    security_service = get_security_service()

    max_req = max_requests or config.default_rate_limit_per_hour
    window = window_size or config.rate_limit_window_size

    return security_service.check_rate_limit(key, max_req, window)


def rotate_encryption_key(reason: str = "scheduled_rotation") -> Dict[str, any]:
    """
    Rotate encryption key and return rotation info.

    Args:
        reason: Reason for rotation

    Returns:
        Dictionary with rotation information
    """
    encryption_service = get_encryption_service()
    rotation_info = encryption_service.rotate_key(reason)

    # Log security event
    audit_security_event(
        event_type="key_rotation",
        details={
            "reason": reason,
            "previous_version": rotation_info.previous_version,
            "current_version": rotation_info.current_version,
        },
        risk_level="medium",
    )

    return rotation_info.model_dump()


def validate_encrypted_data(encrypted_data: EncryptedData) -> bool:
    """
    Validate encrypted data integrity.

    Args:
        encrypted_data: Encrypted data to validate

    Returns:
        True if data is valid and can be decrypted
    """
    encryption_service = get_encryption_service()
    return encryption_service.verify_data_integrity(encrypted_data)


def get_security_metrics() -> Dict[str, any]:
    """
    Get comprehensive security metrics.

    Returns:
        Dictionary with security metrics and audit information
    """
    security_service = get_security_service()
    encryption_service = get_encryption_service()

    return {
        "security_summary": security_service.get_security_summary(),
        "current_key_version": encryption_service.current_key_version,
        "encryption_algorithm": "AES-256-GCM",
        "password_algorithm": get_security_config().password_hash_algorithm,
    }


def create_database_connection_string(include_password: bool = True) -> str:
    """
    Create database connection string from config.

    Args:
        include_password: Whether to include password in connection string

    Returns:
        Database connection string
    """
    from .config import get_database_config

    db_config = get_database_config()

    if include_password:
        return db_config.connection_string
    else:
        # Return connection string without password for logging
        return db_config.connection_string.replace(
            f":{db_config.database_password}@", ":***@"
        )
