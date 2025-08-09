#!/usr/bin/env python3
"""
Test script for Tiger MCP encryption service.

This script demonstrates and tests the key functionality of the encryption service.
"""

import os
import sys
from pathlib import Path

# Add the shared package to Python path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shared import (
    EncryptionService,
    SecurityService,
    create_api_key_with_hash,
    decrypt_tiger_account_data,
    encrypt_tiger_account_data,
    generate_secure_password,
    get_security_metrics,
)


def test_encryption_service():
    """Test encryption service functionality."""
    print("🔐 Testing Encryption Service")
    print("-" * 40)

    # Set up test environment variables
    os.environ["ENCRYPTION_MASTER_KEY"] = (
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    os.environ["ENVIRONMENT"] = "development"

    try:
        # Test basic encryption/decryption
        service = EncryptionService()

        test_data = "This is sensitive test data!"
        print(f"Original data: {test_data}")

        # Encrypt
        encrypted_data = service.encrypt(test_data)
        print(f"Encrypted successfully with key version: {encrypted_data.key_version}")
        print(f"Algorithm: {encrypted_data.algorithm}")

        # Decrypt
        decrypted_data = service.decrypt_to_string(encrypted_data)
        print(f"Decrypted data: {decrypted_data}")

        assert test_data == decrypted_data, "Decryption failed!"
        print("✅ Basic encryption/decryption test passed")

        # Test Tiger credentials encryption
        tiger_id = "test_tiger_id_12345"
        private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC..."
        access_token = "test_access_token_abcdef"

        encrypted_creds = encrypt_tiger_account_data(
            tiger_id=tiger_id, private_key=private_key, access_token=access_token
        )

        print(f"✅ Tiger credentials encrypted: {list(encrypted_creds.keys())}")

        # Decrypt Tiger credentials
        decrypted_creds = decrypt_tiger_account_data(encrypted_creds)

        assert decrypted_creds["tiger_id"] == tiger_id
        assert decrypted_creds["private_key"] == private_key
        assert decrypted_creds["access_token"] == access_token

        print("✅ Tiger credentials encryption/decryption test passed")

        # Test key rotation
        rotation_info = service.rotate_key("test_rotation")
        print(
            f"✅ Key rotated: version {rotation_info.previous_version} → {rotation_info.current_version}"
        )

        # Test data integrity verification
        is_valid = service.verify_data_integrity(encrypted_data)
        print(f"✅ Data integrity check: {is_valid}")

    except Exception as e:
        print(f"❌ Encryption test failed: {e}")
        return False

    return True


def test_security_service():
    """Test security service functionality."""
    print("\n🛡️  Testing Security Service")
    print("-" * 40)

    # Set up test environment variables
    os.environ["JWT_SECRET"] = "test_jwt_secret_for_development_only_not_production"

    try:
        service = SecurityService()

        # Test password hashing
        password = "test_password_123!"
        hashed = service.hash_password(password)
        print(f"✅ Password hashed using {service._config.password_hash_algorithm}")

        # Test password verification
        is_valid = service.verify_password(password, hashed)
        assert is_valid, "Password verification failed!"
        print("✅ Password verification passed")

        # Test API key generation
        api_key, key_hash = service.generate_api_key("test")
        print(f"✅ API key generated: {api_key[:12]}...")

        # Test API key verification
        is_valid = service.verify_api_key(api_key, key_hash)
        assert is_valid, "API key verification failed!"
        print("✅ API key verification passed")

        # Test JWT token creation
        token = service.create_token(
            subject="test_user", scopes=["read", "write"], expires_in=3600
        )
        print(f"✅ JWT token created: {token[:20]}...")

        # Test JWT token verification
        payload = service.verify_token(token)
        assert payload.sub == "test_user"
        assert "read" in payload.scopes
        print("✅ JWT token verification passed")

        # Test rate limiting
        key = "test_ip_192.168.1.1"
        allowed = service.check_rate_limit(key, max_requests=5, window_size=60)
        assert allowed, "Rate limit check failed!"
        print("✅ Rate limiting test passed")

        # Test security audit
        service.audit_event(
            event_type="test_event", details={"test": "data"}, risk_level="low"
        )
        print("✅ Security audit logging passed")

    except Exception as e:
        print(f"❌ Security test failed: {e}")
        return False

    return True


def test_utility_functions():
    """Test utility functions."""
    print("\n🔧 Testing Utility Functions")
    print("-" * 40)

    try:
        # Test secure password generation
        password = generate_secure_password(16, include_symbols=True)
        print(f"✅ Generated secure password: {password}")
        assert len(password) == 16

        # Test API key creation with hash
        api_key, key_hash, key_prefix = create_api_key_with_hash(
            name="test_key", scopes=["read", "write"], description="Test API key"
        )
        print(f"✅ API key created: {key_prefix}... (hash length: {len(key_hash)})")

        # Test security metrics
        metrics = get_security_metrics()
        print(f"✅ Security metrics retrieved: {list(metrics.keys())}")

    except Exception as e:
        print(f"❌ Utility test failed: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("🚀 Tiger MCP Encryption Service Test Suite")
    print("=" * 50)

    all_passed = True

    # Run tests
    all_passed &= test_encryption_service()
    all_passed &= test_security_service()
    all_passed &= test_utility_functions()

    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Encryption service is working correctly.")
        print("\n📋 Next steps:")
        print("1. Set up environment variables in production:")
        print("   - ENCRYPTION_MASTER_KEY (64 hex characters)")
        print("   - JWT_SECRET (32+ characters)")
        print("   - DATABASE_URL or individual DB settings")
        print("2. Install the package: pip install -e packages/shared/")
        print("3. Import and use in your application")
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
