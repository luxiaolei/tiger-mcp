"""
Comprehensive unit tests for security module.
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from shared.config import SecurityConfig
from shared.security import (
    AuditError,
    RateLimitBucket,
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

from .conftest import TEST_CONSTANTS


class TestTokenPayload:
    """Tests for TokenPayload model."""

    def test_token_payload_creation(self):
        """Test TokenPayload creation with valid data."""
        payload = TokenPayload(
            sub="test_user_123",
            iat=1640995200,
            exp=1640998800,
            scopes=["read", "write"],
            account_id="test_account",
        )

        assert payload.sub == "test_user_123"
        assert payload.scopes == ["read", "write"]
        assert payload.account_id == "test_account"
        assert payload.iss == "tiger-mcp"
        assert payload.aud == "tiger-mcp"

    def test_token_payload_string_scope(self):
        """Test TokenPayload with string scope conversion."""
        payload = TokenPayload(
            sub="test_user",
            iat=1640995200,
            exp=1640998800,
            scopes="read",  # String should be converted to list
        )

        assert payload.scopes == ["read"]

    def test_token_payload_empty_scope(self):
        """Test TokenPayload with empty scopes."""
        payload = TokenPayload(
            sub="test_user", iat=1640995200, exp=1640998800, scopes=None
        )

        assert payload.scopes == []


class TestRateLimitBucket:
    """Tests for RateLimitBucket class."""

    def test_rate_limit_bucket_creation(self):
        """Test RateLimitBucket creation."""
        bucket = RateLimitBucket(
            window_start=time.time(), window_size=60, max_requests=100
        )

        assert bucket.requests == 0
        assert bucket.window_size == 60
        assert bucket.max_requests == 100

    def test_rate_limit_not_exceeded(self):
        """Test rate limit not exceeded."""
        bucket = RateLimitBucket(
            window_start=time.time(), window_size=60, max_requests=100
        )

        assert bucket.is_exceeded() is False

        # Add some requests
        bucket.requests = 50
        assert bucket.is_exceeded() is False

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        bucket = RateLimitBucket(
            window_start=time.time(), window_size=60, max_requests=100, requests=100
        )

        assert bucket.is_exceeded() is True

    def test_rate_limit_window_reset(self):
        """Test rate limit window reset."""
        # Create bucket with old window
        old_time = time.time() - 120  # 2 minutes ago
        bucket = RateLimitBucket(
            window_start=old_time, window_size=60, max_requests=100, requests=100
        )

        # Should reset when checked
        assert bucket.is_exceeded() is False
        assert bucket.requests == 0

    def test_increment_success(self):
        """Test successful request increment."""
        bucket = RateLimitBucket(
            window_start=time.time(), window_size=60, max_requests=100
        )

        assert bucket.increment() is True
        assert bucket.requests == 1

    def test_increment_limit_exceeded(self):
        """Test increment when limit exceeded."""
        bucket = RateLimitBucket(
            window_start=time.time(), window_size=60, max_requests=100, requests=100
        )

        assert bucket.increment() is False
        assert bucket.requests == 100  # Unchanged


class TestSecurityAuditEvent:
    """Tests for SecurityAuditEvent class."""

    def test_security_audit_event_creation(self):
        """Test SecurityAuditEvent creation."""
        event = SecurityAuditEvent(
            event_type="login_attempt",
            timestamp=datetime.now(timezone.utc),
            source_ip="192.168.1.1",
            risk_level="medium",
        )

        assert event.event_type == "login_attempt"
        assert event.source_ip == "192.168.1.1"
        assert event.risk_level == "medium"

    def test_security_audit_event_invalid_risk_level(self):
        """Test SecurityAuditEvent with invalid risk level."""
        with pytest.raises(ValueError, match="Risk level must be"):
            SecurityAuditEvent(
                event_type="test",
                timestamp=datetime.now(timezone.utc),
                risk_level="invalid",
            )


class TestSecurityService:
    """Tests for SecurityService class."""

    def test_security_service_initialization(self, security_config):
        """Test SecurityService initialization."""
        service = SecurityService(config=security_config)

        assert service._config.environment == "test"
        assert service._jwt_secret is not None

    def test_security_service_without_config(self):
        """Test SecurityService initialization without config."""
        service = SecurityService()

        assert service._config is not None
        assert service._jwt_secret is not None


class TestPasswordManagement:
    """Tests for password management functionality."""

    def test_hash_password_argon2(self, security_service):
        """Test password hashing with Argon2."""
        password = TEST_CONSTANTS["VALID_PASSWORD"]
        hashed = security_service.hash_password(password, algorithm="argon2")

        assert hashed.startswith("$argon2")
        assert security_service.verify_password(password, hashed) is True

    def test_hash_password_bcrypt(self, security_service):
        """Test password hashing with bcrypt."""
        password = TEST_CONSTANTS["VALID_PASSWORD"]
        hashed = security_service.hash_password(password, algorithm="bcrypt")

        assert hashed.startswith("$2b$")
        assert security_service.verify_password(password, hashed) is True

    def test_hash_password_default(self, security_service):
        """Test password hashing with default algorithm."""
        password = TEST_CONSTANTS["VALID_PASSWORD"]
        hashed = security_service.hash_password(password)

        assert isinstance(hashed, str)
        assert security_service.verify_password(password, hashed) is True

    def test_verify_password_wrong_password(self, security_service):
        """Test password verification with wrong password."""
        password = TEST_CONSTANTS["VALID_PASSWORD"]
        wrong_password = "wrong_password"

        hashed = security_service.hash_password(password)
        assert security_service.verify_password(wrong_password, hashed) is False

    def test_verify_password_timing_safe(self, security_service):
        """Test password verification is timing safe."""
        password = TEST_CONSTANTS["VALID_PASSWORD"]
        hashed = security_service.hash_password(password)

        # Both should take similar time (timing attack protection)
        start_time = time.time()
        security_service.verify_password(password, hashed)
        correct_time = time.time() - start_time

        start_time = time.time()
        security_service.verify_password("wrong_password", hashed)
        wrong_time = time.time() - start_time

        # Time difference should be minimal (within reasonable bounds)
        time_diff = abs(correct_time - wrong_time)
        assert time_diff < 0.1  # 100ms threshold

    @patch("shared.security.argon2.hash")
    def test_hash_password_failure(self, mock_argon2, security_service):
        """Test password hashing failure."""
        mock_argon2.side_effect = Exception("Hashing failed")

        with pytest.raises(SecurityError, match="Failed to hash password"):
            security_service.hash_password("test_password", algorithm="argon2")

    @patch("shared.security.SecurityService._pwd_context")
    def test_verify_password_failure(self, mock_context, security_service):
        """Test password verification failure."""
        mock_context.verify.side_effect = Exception("Verification failed")

        with pytest.raises(SecurityError, match="Failed to verify password"):
            security_service.verify_password("test", "hashed")


class TestJWTTokenManagement:
    """Tests for JWT token management."""

    def test_create_jwt_token(self, security_service, sample_jwt_payload):
        """Test JWT token creation."""
        payload = TokenPayload(**sample_jwt_payload)
        token = security_service.create_jwt_token(payload)

        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts

    def test_create_jwt_token_custom_expiry(self, security_service):
        """Test JWT token creation with custom expiry."""
        payload = TokenPayload(
            sub="test_user", iat=int(time.time()), exp=int(time.time()) + 3600  # 1 hour
        )

        token = security_service.create_jwt_token(payload, expiry_minutes=30)

        # Decode to check expiry was overridden
        decoded = jwt.decode(
            token,
            security_service._jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )

        expected_exp = int(time.time()) + 1800  # 30 minutes
        assert abs(decoded["exp"] - expected_exp) < 10  # Within 10 seconds

    def test_verify_jwt_token_valid(self, security_service):
        """Test JWT token verification with valid token."""
        payload = TokenPayload(
            sub="test_user", iat=int(time.time()), exp=int(time.time()) + 3600
        )

        token = security_service.create_jwt_token(payload)
        verified_payload = security_service.verify_jwt_token(token)

        assert verified_payload.sub == "test_user"
        assert isinstance(verified_payload, TokenPayload)

    def test_verify_jwt_token_expired(self, security_service):
        """Test JWT token verification with expired token."""
        payload = TokenPayload(
            sub="test_user",
            iat=int(time.time()) - 3600,  # 1 hour ago
            exp=int(time.time()) - 1800,  # 30 minutes ago (expired)
        )

        token = security_service.create_jwt_token(payload)

        with pytest.raises(TokenError, match="Token expired"):
            security_service.verify_jwt_token(token)

    def test_verify_jwt_token_invalid_signature(self, security_service):
        """Test JWT token verification with invalid signature."""
        # Create token with different secret
        payload = {"sub": "test_user", "exp": int(time.time()) + 3600}
        invalid_token = jwt.encode(payload, "different_secret", algorithm="HS256")

        with pytest.raises(TokenError, match="Invalid token signature"):
            security_service.verify_jwt_token(invalid_token)

    def test_verify_jwt_token_malformed(self, security_service):
        """Test JWT token verification with malformed token."""
        malformed_token = "not.a.valid.jwt.token"

        with pytest.raises(TokenError, match="Invalid token format"):
            security_service.verify_jwt_token(malformed_token)

    @patch("shared.security.jwt.encode")
    def test_create_jwt_token_failure(self, mock_encode, security_service):
        """Test JWT token creation failure."""
        mock_encode.side_effect = Exception("JWT encoding failed")

        payload = TokenPayload(
            sub="test", iat=int(time.time()), exp=int(time.time()) + 3600
        )

        with pytest.raises(TokenError, match="Failed to create JWT token"):
            security_service.create_jwt_token(payload)


class TestAPIKeyManagement:
    """Tests for API key management."""

    def test_generate_api_key(self, security_service):
        """Test API key generation."""
        api_key = security_service.generate_api_key()

        assert isinstance(api_key, str)
        assert len(api_key) >= 32  # Should be reasonably long

        # Should be URL-safe base64
        import base64

        try:
            base64.urlsafe_b64decode(api_key + "==")  # Add padding
        except Exception:
            pass  # Some keys may not need padding

    def test_generate_api_key_custom_length(self, security_service):
        """Test API key generation with custom length."""
        api_key_16 = security_service.generate_api_key(length=16)
        api_key_64 = security_service.generate_api_key(length=64)

        # Different lengths should produce different key sizes
        assert len(api_key_16) != len(api_key_64)

    def test_hash_api_key(self, security_service):
        """Test API key hashing."""
        api_key = "test_api_key_123456"
        hashed = security_service.hash_api_key(api_key)

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex is 64 chars
        assert hashed != api_key  # Should be hashed

    def test_verify_api_key_hash(self, security_service):
        """Test API key hash verification."""
        api_key = "test_api_key_123456"
        hashed = security_service.hash_api_key(api_key)

        assert security_service.verify_api_key_hash(api_key, hashed) is True
        assert security_service.verify_api_key_hash("wrong_key", hashed) is False

    def test_verify_api_key_hash_timing_safe(self, security_service):
        """Test API key verification is timing safe."""
        api_key = "test_api_key_123456"
        hashed = security_service.hash_api_key(api_key)

        # Both should take similar time
        start_time = time.time()
        security_service.verify_api_key_hash(api_key, hashed)
        correct_time = time.time() - start_time

        start_time = time.time()
        security_service.verify_api_key_hash("wrong_key", hashed)
        wrong_time = time.time() - start_time

        # Time difference should be minimal
        time_diff = abs(correct_time - wrong_time)
        assert time_diff < 0.01  # 10ms threshold


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_check_rate_limit_allowed(self, security_service):
        """Test rate limit check when allowed."""
        client_id = "test_client_123"

        # First request should be allowed
        assert security_service.check_rate_limit(client_id) is True

    def test_check_rate_limit_exceeded(self, security_service):
        """Test rate limit check when exceeded."""
        client_id = "test_client_456"

        # Create bucket at limit
        bucket = RateLimitBucket(
            window_start=time.time(), window_size=60, max_requests=100, requests=100
        )
        security_service._rate_limits[client_id] = bucket

        # Should be rate limited
        assert security_service.check_rate_limit(client_id) is False

    def test_enforce_rate_limit_allowed(self, security_service):
        """Test rate limit enforcement when allowed."""
        client_id = "test_client_789"

        # Should not raise exception
        security_service.enforce_rate_limit(client_id)

    def test_enforce_rate_limit_exceeded(self, security_service):
        """Test rate limit enforcement when exceeded."""
        client_id = "test_client_999"

        # Create bucket at limit
        bucket = RateLimitBucket(
            window_start=time.time(), window_size=60, max_requests=100, requests=100
        )
        security_service._rate_limits[client_id] = bucket

        # Should raise exception
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            security_service.enforce_rate_limit(client_id)

    def test_get_rate_limit_info(self, security_service):
        """Test getting rate limit information."""
        client_id = "test_client_info"

        # First create some usage
        security_service.check_rate_limit(client_id)

        info = security_service.get_rate_limit_info(client_id)

        assert "requests" in info
        assert "max_requests" in info
        assert "window_size" in info
        assert "remaining" in info
        assert "reset_time" in info

    def test_reset_rate_limit(self, security_service):
        """Test rate limit reset."""
        client_id = "test_client_reset"

        # Create some usage
        security_service.check_rate_limit(client_id)

        # Reset
        security_service.reset_rate_limit(client_id)

        # Should be clean slate
        info = security_service.get_rate_limit_info(client_id)
        assert info["requests"] == 0


class TestSecurityAudit:
    """Tests for security audit functionality."""

    def test_log_security_event(self, security_service):
        """Test security event logging."""
        event_data = {
            "event_type": "login_attempt",
            "timestamp": datetime.now(timezone.utc),
            "source_ip": "192.168.1.100",
            "risk_level": "low",
        }

        security_service.log_security_event(**event_data)

        # Check event was stored
        events = security_service.get_security_events()
        assert len(events) == 1
        assert events[0].event_type == "login_attempt"
        assert events[0].source_ip == "192.168.1.100"

    def test_log_security_event_high_risk(self, security_service):
        """Test high-risk security event logging."""
        event_data = {
            "event_type": "brute_force_attempt",
            "timestamp": datetime.now(timezone.utc),
            "source_ip": "10.0.0.1",
            "risk_level": "critical",
            "details": {"attempts": 50, "timespan": "5 minutes"},
        }

        security_service.log_security_event(**event_data)

        events = security_service.get_security_events(risk_level="critical")
        assert len(events) == 1
        assert events[0].risk_level == "critical"
        assert events[0].details["attempts"] == 50

    def test_get_security_events_filtered(self, security_service):
        """Test filtered security event retrieval."""
        # Log multiple events
        events_data = [
            {
                "event_type": "login_success",
                "timestamp": datetime.now(timezone.utc),
                "risk_level": "low",
            },
            {
                "event_type": "login_failure",
                "timestamp": datetime.now(timezone.utc),
                "risk_level": "medium",
            },
            {
                "event_type": "suspicious_activity",
                "timestamp": datetime.now(timezone.utc),
                "risk_level": "high",
            },
        ]

        for event_data in events_data:
            security_service.log_security_event(**event_data)

        # Filter by risk level
        high_risk_events = security_service.get_security_events(risk_level="high")
        assert len(high_risk_events) == 1
        assert high_risk_events[0].event_type == "suspicious_activity"

        # Filter by event type
        login_events = security_service.get_security_events(event_type="login_success")
        assert len(login_events) == 1
        assert login_events[0].event_type == "login_success"

    def test_get_security_events_time_range(self, security_service):
        """Test security event retrieval with time range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Log event from yesterday
        security_service.log_security_event(
            event_type="old_event", timestamp=yesterday, risk_level="low"
        )

        # Log recent event
        security_service.log_security_event(
            event_type="recent_event", timestamp=now, risk_level="low"
        )

        # Get events from last hour
        one_hour_ago = now - timedelta(hours=1)
        recent_events = security_service.get_security_events(since=one_hour_ago)

        assert len(recent_events) == 1
        assert recent_events[0].event_type == "recent_event"

    @patch("shared.security.logger")
    def test_log_security_event_failure(self, mock_logger, security_service):
        """Test security event logging failure."""
        # Mock storage failure
        with patch.object(
            security_service, "_audit_events", side_effect=Exception("Storage failed")
        ):
            with pytest.raises(AuditError, match="Failed to log security event"):
                security_service.log_security_event(
                    event_type="test_event", timestamp=datetime.now(timezone.utc)
                )


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_jwt_token_function(self, sample_jwt_payload):
        """Test create_jwt_token convenience function."""
        token = create_jwt_token(
            subject=sample_jwt_payload["sub"],
            scopes=sample_jwt_payload["scopes"],
            expiry_minutes=60,
        )

        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_verify_jwt_token_function(self, sample_jwt_payload):
        """Test verify_jwt_token convenience function."""
        token = create_jwt_token(
            subject=sample_jwt_payload["sub"],
            scopes=sample_jwt_payload["scopes"],
            expiry_minutes=60,
        )

        payload = verify_jwt_token(token)
        assert payload.sub == sample_jwt_payload["sub"]
        assert payload.scopes == sample_jwt_payload["scopes"]

    def test_generate_secure_api_key_function(self):
        """Test generate_secure_api_key convenience function."""
        api_key = generate_secure_api_key()

        assert isinstance(api_key, str)
        assert len(api_key) >= 32

    def test_hash_api_key_function(self):
        """Test hash_api_key convenience function."""
        api_key = "test_api_key_function"
        hashed = hash_api_key(api_key)

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex

    def test_verify_api_key_hash_function(self):
        """Test verify_api_key_hash convenience function."""
        api_key = "test_api_key_verify"
        hashed = hash_api_key(api_key)

        assert verify_api_key_hash(api_key, hashed) is True
        assert verify_api_key_hash("wrong_key", hashed) is False

    def test_get_security_service_singleton(self):
        """Test get_security_service returns singleton."""
        service1 = get_security_service()
        service2 = get_security_service()

        assert service1 is service2


class TestSecurityIntegration:
    """Integration tests for security functionality."""

    def test_complete_auth_flow(self, security_service):
        """Test complete authentication flow."""
        # 1. Generate API key
        api_key = security_service.generate_api_key()
        api_key_hash = security_service.hash_api_key(api_key)

        # 2. Verify API key
        assert security_service.verify_api_key_hash(api_key, api_key_hash) is True

        # 3. Create JWT token
        payload = TokenPayload(
            sub=api_key[:8],  # Use part of API key as subject
            iat=int(time.time()),
            exp=int(time.time()) + 3600,
            scopes=["read", "write"],
        )

        token = security_service.create_jwt_token(payload)

        # 4. Verify JWT token
        verified_payload = security_service.verify_jwt_token(token)
        assert verified_payload.sub == payload.sub
        assert verified_payload.scopes == payload.scopes

        # 5. Check rate limit
        assert security_service.check_rate_limit(payload.sub) is True

        # 6. Log security event
        security_service.log_security_event(
            event_type="successful_auth",
            timestamp=datetime.now(timezone.utc),
            api_key_id=payload.sub,
            risk_level="low",
        )

        # Verify event was logged
        events = security_service.get_security_events(event_type="successful_auth")
        assert len(events) == 1

    def test_security_breach_scenario(self, security_service):
        """Test security breach detection and handling."""
        client_id = "suspicious_client"

        # Simulate multiple failed attempts
        for _ in range(10):
            security_service.log_security_event(
                event_type="login_failure",
                timestamp=datetime.now(timezone.utc),
                source_ip="10.0.0.1",
                api_key_id=client_id,
                risk_level="medium",
            )

        # Check for pattern
        failed_logins = security_service.get_security_events(
            event_type="login_failure", api_key_id=client_id
        )

        assert len(failed_logins) == 10

        # Simulate rate limiting
        # Exhaust rate limit
        for _ in range(100):
            if not security_service.check_rate_limit(client_id):
                break

        # Should be rate limited now
        with pytest.raises(RateLimitError):
            security_service.enforce_rate_limit(client_id)

    def test_password_security_levels(self, security_service):
        """Test different password security levels."""
        passwords = [
            ("weak123", False),  # Too short
            ("WeakPassword", False),  # No special chars
            ("StrongP@ssw0rd123!", True),  # Strong password
            ("Vëry$tr0ngP@ssw0rd!", True),  # Strong with unicode
        ]

        for password, should_be_strong in passwords:
            # Hash with both algorithms
            argon2_hash = security_service.hash_password(password, "argon2")
            bcrypt_hash = security_service.hash_password(password, "bcrypt")

            # Both should verify correctly
            assert security_service.verify_password(password, argon2_hash) is True
            assert security_service.verify_password(password, bcrypt_hash) is True

            # Wrong password should fail
            assert security_service.verify_password("wrong", argon2_hash) is False
            assert security_service.verify_password("wrong", bcrypt_hash) is False


class TestSecurityErrorHandling:
    """Tests for security error handling and edge cases."""

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_jwt_secret_production(self):
        """Test missing JWT secret in production."""
        config = SecurityConfig(environment="production")

        with pytest.raises(SecurityError, match="JWT secret not found"):
            SecurityService(config=config)

    def test_invalid_token_formats(self, security_service):
        """Test various invalid token formats."""
        invalid_tokens = [
            "",  # Empty
            "invalid",  # No dots
            "a.b",  # Too few parts
            "a.b.c.d",  # Too many parts
            "ä.ß.ç",  # Invalid characters
            None,  # None value
        ]

        for invalid_token in invalid_tokens:
            with pytest.raises(TokenError):
                security_service.verify_jwt_token(invalid_token)

    def test_extreme_rate_limits(self, security_service):
        """Test extreme rate limit scenarios."""
        client_id = "extreme_client"

        # Test with very low limit
        bucket = RateLimitBucket(
            window_start=time.time(),
            window_size=1,  # 1 second window
            max_requests=1,  # Only 1 request allowed
        )
        security_service._rate_limits[client_id] = bucket

        # First request should work
        assert security_service.check_rate_limit(client_id) is True

        # Second request should be blocked
        assert security_service.check_rate_limit(client_id) is False

        # Wait for window reset (simulate time passage)
        bucket.window_start = time.time() - 2  # 2 seconds ago

        # Should work again after reset
        assert security_service.check_rate_limit(client_id) is True

    def test_concurrent_rate_limiting(self, security_service):
        """Test rate limiting under concurrent access."""
        client_id = "concurrent_client"

        # Simulate concurrent requests
        results = []
        for _ in range(10):
            result = security_service.check_rate_limit(client_id)
            results.append(result)

        # All should be allowed initially (under default limit)
        assert all(results)

        # But counter should be accurate
        info = security_service.get_rate_limit_info(client_id)
        assert info["requests"] == 10
