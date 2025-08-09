"""
Security utilities for Tiger MCP system.

Provides password hashing, JWT token management, rate limiting,
and security audit helpers.
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import bcrypt
import jwt
from loguru import logger
from passlib.context import CryptContext
from passlib.hash import argon2
from pydantic import BaseModel, field_validator

from .config import SecurityConfig


class SecurityError(Exception):
    """Base exception for security operations."""


class TokenError(SecurityError):
    """Exception raised during token operations."""


class RateLimitError(SecurityError):
    """Exception raised when rate limit is exceeded."""


class AuditError(SecurityError):
    """Exception raised during security audit operations."""


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # Subject (user/api key ID)
    iat: int  # Issued at
    exp: int  # Expires at
    iss: str = "tiger-mcp"  # Issuer
    aud: str = "tiger-mcp"  # Audience
    jti: Optional[str] = None  # JWT ID
    scopes: List[str] = []
    account_id: Optional[str] = None
    api_key_id: Optional[str] = None

    @field_validator("scopes", mode="before")
    @classmethod
    def validate_scopes(cls, v):
        """Ensure scopes is a list."""
        if isinstance(v, str):
            return [v]
        return v or []


class RateLimitBucket(BaseModel):
    """Rate limiting bucket for tracking usage."""

    requests: int = 0
    window_start: float
    window_size: int  # seconds
    max_requests: int

    def is_exceeded(self) -> bool:
        """Check if rate limit is exceeded."""
        current_time = time.time()

        # Reset bucket if window has passed
        if current_time - self.window_start >= self.window_size:
            self.requests = 0
            self.window_start = current_time

        return self.requests >= self.max_requests

    def increment(self) -> bool:
        """Increment request count. Returns False if limit exceeded."""
        if self.is_exceeded():
            return False

        self.requests += 1
        return True


class SecurityAuditEvent(BaseModel):
    """Security audit event structure."""

    event_type: str
    timestamp: datetime
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    api_key_id: Optional[str] = None
    account_id: Optional[str] = None
    details: Dict[str, Any] = {}
    risk_level: str = "low"  # low, medium, high, critical

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v):
        """Validate risk level values."""
        if v not in ["low", "medium", "high", "critical"]:
            raise ValueError("Risk level must be low, medium, high, or critical")
        return v


class SecurityService:
    """
    Comprehensive security service for Tiger MCP system.

    Features:
    - Argon2 and bcrypt password hashing
    - JWT token generation and validation
    - Rate limiting with sliding windows
    - Security audit logging
    - API key generation and verification
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize security service."""
        self._config = config or SecurityConfig()

        # Initialize password context with both Argon2 and bcrypt
        self._pwd_context = CryptContext(
            schemes=["argon2", "bcrypt"],
            deprecated="auto",
            argon2__memory_cost=65536,  # 64MB
            argon2__time_cost=3,
            argon2__parallelism=2,
            bcrypt__rounds=12,
        )

        # Rate limiting storage
        self._rate_limits: Dict[str, RateLimitBucket] = {}

        # JWT secret
        self._jwt_secret = self._load_jwt_secret()

        # Audit events storage (in production, this would be a database)
        self._audit_events: List[SecurityAuditEvent] = []

        logger.info("Security service initialized")

    def _load_jwt_secret(self) -> str:
        """Load JWT secret from environment or generate new one."""
        import os

        secret = os.getenv("JWT_SECRET")

        if secret:
            return secret

        # Generate new secret for development
        if self._config.environment == "development":
            secret = secrets.token_urlsafe(32)
            logger.warning(
                f"Generated new JWT secret for development. " f"Set JWT_SECRET={secret}"
            )
            return secret

        raise SecurityError("JWT secret not found. Set JWT_SECRET environment variable")

    # Password Management

    def hash_password(self, password: str, algorithm: str = "argon2") -> str:
        """
        Hash password using specified algorithm.

        Args:
            password: Password to hash
            algorithm: Hashing algorithm ("argon2" or "bcrypt")

        Returns:
            Hashed password string
        """
        try:
            if algorithm == "argon2":
                return argon2.hash(password)
            elif algorithm == "bcrypt":
                return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            else:
                # Use passlib context for backward compatibility
                return self._pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise SecurityError(f"Failed to hash password: {e}")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        Args:
            password: Plain text password
            hashed_password: Hashed password to verify against

        Returns:
            True if password matches
        """
        try:
            # Try with passlib context first (supports both algorithms)
            if self._pwd_context.verify(password, hashed_password):
                return True

            # Fallback for direct bcrypt verification
            if hashed_password.startswith("$2"):
                return bcrypt.checkpw(password.encode(), hashed_password.encode())

            return False

        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if password hash needs to be updated."""
        return self._pwd_context.needs_update(hashed_password)

    # API Key Management

    def generate_api_key(self, prefix: str = "tk", length: int = 32) -> Tuple[str, str]:
        """
        Generate secure API key and its hash.

        Args:
            prefix: Key prefix for identification
            length: Key length in bytes

        Returns:
            Tuple of (api_key, hash) where hash is SHA-256
        """
        # Generate random key
        secrets.token_bytes(length)
        key_b64 = secrets.token_urlsafe(length)

        # Create full API key with prefix
        api_key = f"{prefix}_{key_b64}"

        # Generate SHA-256 hash for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        logger.debug(f"Generated API key with prefix {prefix}")
        return api_key, key_hash

    def verify_api_key(self, api_key: str, stored_hash: str) -> bool:
        """
        Verify API key against stored hash.

        Args:
            api_key: API key to verify
            stored_hash: SHA-256 hash to verify against

        Returns:
            True if API key matches hash
        """
        try:
            computed_hash = hashlib.sha256(api_key.encode()).hexdigest()
            return secrets.compare_digest(computed_hash, stored_hash)
        except Exception as e:
            logger.error(f"API key verification failed: {e}")
            return False

    def extract_key_prefix(self, api_key: str, length: int = 8) -> str:
        """Extract prefix from API key for identification."""
        return api_key[:length] if len(api_key) >= length else api_key

    # JWT Token Management

    def create_token(
        self,
        subject: str,
        scopes: List[str],
        expires_in: int = 3600,
        account_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create JWT token.

        Args:
            subject: Token subject (user/api key ID)
            scopes: List of access scopes
            expires_in: Token expiration in seconds
            account_id: Optional account ID
            api_key_id: Optional API key ID
            extra_claims: Additional claims to include

        Returns:
            JWT token string
        """
        try:
            now = datetime.now(timezone.utc)
            payload = TokenPayload(
                sub=subject,
                iat=int(now.timestamp()),
                exp=int((now + timedelta(seconds=expires_in)).timestamp()),
                jti=secrets.token_urlsafe(16),
                scopes=scopes,
                account_id=account_id,
                api_key_id=api_key_id,
            )

            # Add extra claims
            token_data = payload.model_dump()
            if extra_claims:
                token_data.update(extra_claims)

            token = jwt.encode(token_data, self._jwt_secret, algorithm="HS256")

            logger.debug(f"Created JWT token for subject {subject}")
            return token

        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            raise TokenError(f"Failed to create token: {e}")

    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token payload
        """
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=["HS256"],
                audience="tiger-mcp",
                issuer="tiger-mcp",
            )

            return TokenPayload(**payload)

        except jwt.ExpiredSignatureError:
            raise TokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise TokenError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise TokenError(f"Token verification failed: {e}")

    def refresh_token(self, token: str, new_expires_in: int = 3600) -> str:
        """
        Refresh JWT token with new expiration.

        Args:
            token: Current JWT token
            new_expires_in: New expiration in seconds

        Returns:
            New JWT token
        """
        try:
            # Decode current token (allowing expired)
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )

            # Create new token with same claims
            return self.create_token(
                subject=payload["sub"],
                scopes=payload.get("scopes", []),
                expires_in=new_expires_in,
                account_id=payload.get("account_id"),
                api_key_id=payload.get("api_key_id"),
            )

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise TokenError(f"Failed to refresh token: {e}")

    # Rate Limiting

    def check_rate_limit(
        self, key: str, max_requests: int, window_size: int = 3600
    ) -> bool:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (e.g., IP address, API key)
            max_requests: Maximum requests allowed
            window_size: Time window in seconds

        Returns:
            True if request is allowed
        """
        current_time = time.time()

        if key not in self._rate_limits:
            self._rate_limits[key] = RateLimitBucket(
                window_start=current_time,
                window_size=window_size,
                max_requests=max_requests,
            )

        bucket = self._rate_limits[key]
        return bucket.increment()

    def get_rate_limit_status(self, key: str) -> Optional[Dict[str, Union[int, float]]]:
        """
        Get current rate limit status for key.

        Args:
            key: Rate limit key

        Returns:
            Dictionary with rate limit information or None
        """
        if key not in self._rate_limits:
            return None

        bucket = self._rate_limits[key]
        current_time = time.time()

        return {
            "requests": bucket.requests,
            "max_requests": bucket.max_requests,
            "window_size": bucket.window_size,
            "window_start": bucket.window_start,
            "time_remaining": max(
                0, bucket.window_size - (current_time - bucket.window_start)
            ),
            "requests_remaining": max(0, bucket.max_requests - bucket.requests),
        }

    def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for specific key."""
        if key in self._rate_limits:
            del self._rate_limits[key]
            logger.debug(f"Reset rate limit for key: {key}")

    # Security Audit

    def audit_event(
        self,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        risk_level: str = "low",
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        api_key_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> None:
        """
        Log security audit event.

        Args:
            event_type: Type of security event
            details: Additional event details
            risk_level: Risk level (low, medium, high, critical)
            source_ip: Source IP address
            user_agent: User agent string
            api_key_id: API key ID if applicable
            account_id: Account ID if applicable
        """
        event = SecurityAuditEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            details=details or {},
            risk_level=risk_level,
            source_ip=source_ip,
            user_agent=user_agent,
            api_key_id=api_key_id,
            account_id=account_id,
        )

        self._audit_events.append(event)

        # Log based on risk level
        log_message = f"Security event: {event_type} (risk: {risk_level})"
        if risk_level == "critical":
            logger.critical(log_message, extra=event.model_dump())
        elif risk_level == "high":
            logger.error(log_message, extra=event.model_dump())
        elif risk_level == "medium":
            logger.warning(log_message, extra=event.model_dump())
        else:
            logger.info(log_message, extra=event.model_dump())

    def get_audit_events(
        self,
        event_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        limit: int = 100,
    ) -> List[SecurityAuditEvent]:
        """
        Get security audit events with optional filtering.

        Args:
            event_type: Filter by event type
            risk_level: Filter by risk level
            limit: Maximum number of events to return

        Returns:
            List of matching audit events
        """
        events = self._audit_events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if risk_level:
            events = [e for e in events if e.risk_level == risk_level]

        # Sort by timestamp descending and limit
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security metrics summary."""
        total_events = len(self._audit_events)
        risk_counts = {}

        for event in self._audit_events:
            risk_counts[event.risk_level] = risk_counts.get(event.risk_level, 0) + 1

        recent_events = [
            e
            for e in self._audit_events
            if e.timestamp > datetime.now(timezone.utc) - timedelta(hours=24)
        ]

        return {
            "total_events": total_events,
            "risk_level_counts": risk_counts,
            "recent_events_24h": len(recent_events),
            "active_rate_limits": len(self._rate_limits),
            "critical_events_count": risk_counts.get("critical", 0),
            "high_risk_events_count": risk_counts.get("high", 0),
        }


# Global security service instance
_security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """Get global security service instance."""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service


# Convenience functions


def hash_api_key(api_key: str) -> str:
    """Hash API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_secure_api_key(prefix: str = "tk") -> Tuple[str, str]:
    """Generate API key and return (key, hash) tuple."""
    service = get_security_service()
    return service.generate_api_key(prefix)


def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
    """Verify API key against stored hash."""
    service = get_security_service()
    return service.verify_api_key(api_key, stored_hash)


def create_jwt_token(
    subject: str, scopes: List[str], expires_in: int = 3600, **kwargs
) -> str:
    """Create JWT token with specified parameters."""
    service = get_security_service()
    return service.create_token(subject, scopes, expires_in, **kwargs)


def verify_jwt_token(token: str) -> TokenPayload:
    """Verify JWT token and return payload."""
    service = get_security_service()
    return service.verify_token(token)
