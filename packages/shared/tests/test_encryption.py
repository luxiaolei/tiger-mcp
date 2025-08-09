"""
Comprehensive unit tests for encryption module.
"""

import base64
import os
from unittest.mock import patch

import pytest
from shared.config import SecurityConfig
from shared.encryption import (
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


class TestEncryptedData:
    """Tests for EncryptedData model."""

    def test_encrypted_data_creation(self):
        """Test creation of EncryptedData with valid base64 data."""
        encrypted_data = EncryptedData(
            ciphertext=base64.b64encode(b"test_ciphertext").decode(),
            nonce=base64.b64encode(b"test_nonce").decode(),
            tag=base64.b64encode(b"test_tag").decode(),
            salt=base64.b64encode(b"test_salt").decode(),
            key_version=1,
            algorithm="AES-256-GCM",
        )

        assert encrypted_data.key_version == 1
        assert encrypted_data.algorithm == "AES-256-GCM"

    def test_encrypted_data_invalid_base64(self):
        """Test EncryptedData validation with invalid base64."""
        with pytest.raises(ValueError, match="Invalid base64 encoding"):
            EncryptedData(
                ciphertext="invalid_base64!@#$",
                nonce=base64.b64encode(b"test_nonce").decode(),
                tag=base64.b64encode(b"test_tag").decode(),
                salt=base64.b64encode(b"test_salt").decode(),
            )


class TestKeyRotationInfo:
    """Tests for KeyRotationInfo model."""

    def test_key_rotation_info_creation(self):
        """Test creation of KeyRotationInfo."""
        rotation_info = KeyRotationInfo(
            current_version=2,
            previous_version=1,
            rotation_timestamp=1640995200.0,
            reason="security_breach",
        )

        assert rotation_info.current_version == 2
        assert rotation_info.previous_version == 1
        assert rotation_info.reason == "security_breach"


class TestEncryptionService:
    """Tests for EncryptionService class."""

    def test_encryption_service_initialization(self, security_config):
        """Test EncryptionService initialization."""
        service = EncryptionService(config=security_config)

        assert service.current_key_version == 1
        assert service._config.environment == "test"

    def test_encryption_service_without_config(self):
        """Test EncryptionService initialization without config."""
        service = EncryptionService()

        assert service.current_key_version == 1
        assert service._config is not None

    def test_load_master_key_from_environment(self, security_config):
        """Test loading master key from environment variable."""
        service = EncryptionService(config=security_config)

        # Should load key from ENCRYPTION_MASTER_KEY env var
        assert len(service._master_key) == 32  # 256 bits

    @patch.dict(os.environ, {"ENCRYPTION_MASTER_KEY": "invalid_key"})
    def test_load_master_key_invalid_format(self, security_config):
        """Test loading invalid master key format."""
        with pytest.raises(EncryptionError, match="Invalid master key"):
            EncryptionService(config=security_config)

    @patch.dict(os.environ, {}, clear=True)
    def test_load_master_key_missing_production(self):
        """Test missing master key in production environment."""
        config = SecurityConfig(environment="production")

        with pytest.raises(EncryptionError, match="Master key not found"):
            EncryptionService(config=config)

    @patch.dict(os.environ, {}, clear=True)
    def test_load_master_key_development_generation(self):
        """Test master key generation in development environment."""
        config = SecurityConfig(environment="development")
        service = EncryptionService(config=config)

        assert len(service._master_key) == 32

    def test_derive_key(self, encryption_service):
        """Test key derivation functionality."""
        salt = b"test_salt_16byte"
        derived_key = encryption_service._derive_key(salt, version=1)

        assert len(derived_key) == 32  # 256 bits

        # Test caching - should return same key for same salt and version
        derived_key2 = encryption_service._derive_key(salt, version=1)
        assert derived_key == derived_key2

    def test_derive_key_different_versions(self, encryption_service):
        """Test key derivation with different versions."""
        salt = b"test_salt_16byte"

        key_v1 = encryption_service._derive_key(salt, version=1)
        key_v2 = encryption_service._derive_key(salt, version=2)

        assert key_v1 != key_v2

    @patch("shared.encryption.PBKDF2HMAC")
    def test_derive_key_failure(self, mock_pbkdf2, encryption_service):
        """Test key derivation failure."""
        mock_pbkdf2.return_value.derive.side_effect = Exception("KDF failed")

        with pytest.raises(KeyDerivationError, match="Failed to derive key"):
            encryption_service._derive_key(b"test_salt", version=1)


class TestEncryption:
    """Tests for encryption functionality."""

    def test_encrypt_string(self, encryption_service):
        """Test encrypting string data."""
        plaintext = "test_plaintext_string"
        encrypted_data = encryption_service.encrypt(plaintext)

        assert isinstance(encrypted_data, EncryptedData)
        assert encrypted_data.algorithm == "AES-256-GCM"
        assert encrypted_data.key_version == 1

        # Verify base64 encoding
        assert base64.b64decode(encrypted_data.ciphertext)
        assert base64.b64decode(encrypted_data.nonce)
        assert base64.b64decode(encrypted_data.tag)
        assert base64.b64decode(encrypted_data.salt)

    def test_encrypt_bytes(self, encryption_service):
        """Test encrypting byte data."""
        plaintext = b"test_plaintext_bytes"
        encrypted_data = encryption_service.encrypt(plaintext)

        assert isinstance(encrypted_data, EncryptedData)
        assert encrypted_data.algorithm == "AES-256-GCM"

    def test_encrypt_with_key_version(self, encryption_service):
        """Test encryption with specific key version."""
        plaintext = "test_plaintext"
        encrypted_data = encryption_service.encrypt(plaintext, key_version=2)

        assert encrypted_data.key_version == 2

    @patch("shared.encryption.secrets.token_bytes")
    def test_encrypt_failure(self, mock_token_bytes, encryption_service):
        """Test encryption failure."""
        mock_token_bytes.side_effect = Exception("Random generation failed")

        with pytest.raises(EncryptionError, match="Failed to encrypt data"):
            encryption_service.encrypt("test_plaintext")


class TestDecryption:
    """Tests for decryption functionality."""

    def test_decrypt_roundtrip(self, encryption_service):
        """Test encryption/decryption roundtrip."""
        plaintext = "test_roundtrip_plaintext"

        # Encrypt
        encrypted_data = encryption_service.encrypt(plaintext)

        # Decrypt
        decrypted_bytes = encryption_service.decrypt(encrypted_data)
        decrypted_string = encryption_service.decrypt_to_string(encrypted_data)

        assert decrypted_bytes == plaintext.encode()
        assert decrypted_string == plaintext

    def test_decrypt_bytes_roundtrip(self, encryption_service):
        """Test encryption/decryption roundtrip with bytes."""
        plaintext = b"test_bytes_roundtrip"

        encrypted_data = encryption_service.encrypt(plaintext)
        decrypted_bytes = encryption_service.decrypt(encrypted_data)

        assert decrypted_bytes == plaintext

    def test_decrypt_different_key_versions(self, encryption_service):
        """Test decryption with different key versions."""
        plaintext = "test_version_compatibility"

        # Encrypt with version 1
        encrypted_v1 = encryption_service.encrypt(plaintext, key_version=1)

        # Encrypt with version 2
        encrypted_v2 = encryption_service.encrypt(plaintext, key_version=2)

        # Should be able to decrypt both versions
        decrypted_v1 = encryption_service.decrypt_to_string(encrypted_v1)
        decrypted_v2 = encryption_service.decrypt_to_string(encrypted_v2)

        assert decrypted_v1 == plaintext
        assert decrypted_v2 == plaintext

    def test_decrypt_invalid_base64(self, encryption_service):
        """Test decryption with invalid base64 data."""
        invalid_encrypted = EncryptedData(
            ciphertext="valid_base64_data",
            nonce="invalid_base64!@#$",
            tag=base64.b64encode(b"test_tag").decode(),
            salt=base64.b64encode(b"test_salt").decode(),
        )

        with pytest.raises(DecryptionError):
            encryption_service.decrypt(invalid_encrypted)

    def test_decrypt_corrupted_data(self, encryption_service):
        """Test decryption with corrupted ciphertext."""
        plaintext = "test_corruption"
        encrypted_data = encryption_service.encrypt(plaintext)

        # Corrupt the ciphertext
        corrupted_ciphertext = base64.b64encode(b"corrupted_data").decode()
        corrupted_encrypted = EncryptedData(
            ciphertext=corrupted_ciphertext,
            nonce=encrypted_data.nonce,
            tag=encrypted_data.tag,
            salt=encrypted_data.salt,
            key_version=encrypted_data.key_version,
        )

        with pytest.raises(DecryptionError):
            encryption_service.decrypt(corrupted_encrypted)

    def test_decrypt_to_string_invalid_utf8(self, encryption_service):
        """Test decrypt_to_string with invalid UTF-8 data."""
        # Create encrypted data that will decrypt to invalid UTF-8
        invalid_bytes = b"\xff\xfe\xfd"
        encrypted_data = encryption_service.encrypt(invalid_bytes)

        with pytest.raises(
            DecryptionError, match="Failed to decode decrypted data as UTF-8"
        ):
            encryption_service.decrypt_to_string(encrypted_data)


class TestCredentialEncryption:
    """Tests for credential encryption functionality."""

    def test_encrypt_credentials(self, encryption_service, sample_tiger_credentials):
        """Test encrypting multiple credentials."""
        encrypted_creds = encryption_service.encrypt_credentials(
            sample_tiger_credentials
        )

        assert len(encrypted_creds) == len(sample_tiger_credentials)

        for name in sample_tiger_credentials.keys():
            assert name in encrypted_creds
            assert isinstance(encrypted_creds[name], EncryptedData)

    def test_decrypt_credentials(self, encryption_service, sample_tiger_credentials):
        """Test decrypting multiple credentials."""
        # Encrypt first
        encrypted_creds = encryption_service.encrypt_credentials(
            sample_tiger_credentials
        )

        # Then decrypt
        decrypted_creds = encryption_service.decrypt_credentials(encrypted_creds)

        assert decrypted_creds == sample_tiger_credentials

    def test_encrypt_credentials_failure(self, encryption_service):
        """Test credential encryption failure."""
        with patch.object(
            encryption_service, "encrypt", side_effect=Exception("Encryption failed")
        ):
            credentials = {"test_key": "test_value"}

            with pytest.raises(EncryptionError, match="Failed to encrypt credential"):
                encryption_service.encrypt_credentials(credentials)

    def test_decrypt_credentials_failure(
        self, encryption_service, sample_encrypted_data
    ):
        """Test credential decryption failure."""
        with patch.object(
            encryption_service,
            "decrypt_to_string",
            side_effect=Exception("Decryption failed"),
        ):
            encrypted_creds = {"test_key": sample_encrypted_data}

            with pytest.raises(DecryptionError, match="Failed to decrypt credential"):
                encryption_service.decrypt_credentials(encrypted_creds)


class TestKeyRotation:
    """Tests for key rotation functionality."""

    def test_rotate_key(self, encryption_service):
        """Test key rotation functionality."""
        initial_version = encryption_service.current_key_version

        rotation_info = encryption_service.rotate_key("security_update")

        assert rotation_info.current_version == initial_version + 1
        assert rotation_info.previous_version == initial_version
        assert rotation_info.reason == "security_update"
        assert encryption_service.current_key_version == initial_version + 1

    def test_rotate_key_clears_cache(self, encryption_service):
        """Test that key rotation clears derived key cache."""
        # Derive a key to populate cache
        salt = b"test_salt_16byte"
        encryption_service._derive_key(salt, version=1)

        assert len(encryption_service._derived_keys) > 0

        # Rotate key
        encryption_service.rotate_key()

        # Cache should be cleared
        assert len(encryption_service._derived_keys) == 0

    def test_decrypt_after_rotation(self, encryption_service):
        """Test decryption of old data after key rotation."""
        plaintext = "test_rotation_compatibility"

        # Encrypt with version 1
        encrypted_data = encryption_service.encrypt(plaintext)
        assert encrypted_data.key_version == 1

        # Rotate key
        encryption_service.rotate_key()
        assert encryption_service.current_key_version == 2

        # Should still be able to decrypt old data
        decrypted = encryption_service.decrypt_to_string(encrypted_data)
        assert decrypted == plaintext

    def test_can_decrypt_version(self, encryption_service):
        """Test can_decrypt_version method."""
        assert encryption_service.can_decrypt_version(1) is True
        assert encryption_service.can_decrypt_version(5) is True
        assert encryption_service.can_decrypt_version(0) is False
        assert encryption_service.can_decrypt_version(-1) is False


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_generate_secure_key(self, encryption_service):
        """Test secure key generation."""
        key_32 = encryption_service.generate_secure_key(32)
        key_16 = encryption_service.generate_secure_key(16)

        # Should be base64 encoded
        assert base64.b64decode(key_32)
        assert base64.b64decode(key_16)

        # Different lengths should produce different key sizes
        assert len(base64.b64decode(key_32)) == 32
        assert len(base64.b64decode(key_16)) == 16

        # Default length should be 32
        default_key = encryption_service.generate_secure_key()
        assert len(base64.b64decode(default_key)) == 32

    def test_hash_key(self, encryption_service):
        """Test key hashing."""
        key = "test_key_to_hash"
        hash1 = encryption_service.hash_key(key)
        hash2 = encryption_service.hash_key(key)

        # Same key should produce same hash
        assert hash1 == hash2

        # Should be SHA-256 hex (64 characters)
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)

        # Different keys should produce different hashes
        different_hash = encryption_service.hash_key("different_key")
        assert hash1 != different_hash

    def test_verify_data_integrity_valid(self, encryption_service):
        """Test data integrity verification with valid data."""
        plaintext = "test_integrity_check"
        encrypted_data = encryption_service.encrypt(plaintext)

        assert encryption_service.verify_data_integrity(encrypted_data) is True

    def test_verify_data_integrity_invalid(self, encryption_service):
        """Test data integrity verification with invalid data."""
        # Create corrupted encrypted data
        corrupted_data = EncryptedData(
            ciphertext=base64.b64encode(b"corrupted").decode(),
            nonce=base64.b64encode(b"test_nonce12").decode(),
            tag=base64.b64encode(b"invalid_tag_data").decode(),
            salt=base64.b64encode(b"test_salt_16byte").decode(),
            key_version=1,
        )

        assert encryption_service.verify_data_integrity(corrupted_data) is False


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_encrypt_tiger_credentials(self, sample_tiger_credentials):
        """Test encrypt_tiger_credentials convenience function."""
        encrypted_creds = encrypt_tiger_credentials(
            tiger_id=sample_tiger_credentials["tiger_id"],
            private_key=sample_tiger_credentials["private_key"],
            access_token=sample_tiger_credentials["access_token"],
            refresh_token=sample_tiger_credentials["refresh_token"],
        )

        assert "tiger_id" in encrypted_creds
        assert "private_key" in encrypted_creds
        assert "access_token" in encrypted_creds
        assert "refresh_token" in encrypted_creds

        for name, encrypted_data in encrypted_creds.items():
            assert isinstance(encrypted_data, EncryptedData)

    def test_encrypt_tiger_credentials_minimal(self):
        """Test encrypt_tiger_credentials with minimal required fields."""
        encrypted_creds = encrypt_tiger_credentials(
            tiger_id="test_id", private_key="test_private_key"
        )

        assert "tiger_id" in encrypted_creds
        assert "private_key" in encrypted_creds
        assert "access_token" not in encrypted_creds
        assert "refresh_token" not in encrypted_creds

    def test_decrypt_tiger_credentials(self, sample_tiger_credentials):
        """Test decrypt_tiger_credentials convenience function."""
        # First encrypt
        encrypted_creds = encrypt_tiger_credentials(**sample_tiger_credentials)

        # Then decrypt
        decrypted_creds = decrypt_tiger_credentials(encrypted_creds)

        assert decrypted_creds == sample_tiger_credentials

    def test_get_encryption_service_singleton(self):
        """Test get_encryption_service returns singleton."""
        service1 = get_encryption_service()
        service2 = get_encryption_service()

        assert service1 is service2


class TestEncryptionVersioning:
    """Tests for encryption versioning and compatibility."""

    def test_encryption_version_metadata(self, encryption_service):
        """Test encryption includes version metadata."""
        plaintext = "test_version_metadata"
        encrypted_data = encryption_service.encrypt(plaintext)

        assert encrypted_data.key_version == encryption_service.current_key_version
        assert encrypted_data.algorithm == "AES-256-GCM"

    def test_multiple_version_compatibility(self, encryption_service):
        """Test compatibility across multiple key versions."""
        plaintext = "test_multi_version"
        encrypted_versions = []

        # Create encrypted data with different versions
        for version in [1, 2, 3]:
            encrypted_data = encryption_service.encrypt(plaintext, key_version=version)
            encrypted_versions.append(encrypted_data)

        # All versions should decrypt successfully
        for encrypted_data in encrypted_versions:
            decrypted = encryption_service.decrypt_to_string(encrypted_data)
            assert decrypted == plaintext


class TestEncryptionErrorHandling:
    """Tests for encryption error handling and edge cases."""

    def test_encrypt_empty_string(self, encryption_service):
        """Test encryption of empty string."""
        encrypted_data = encryption_service.encrypt("")
        decrypted = encryption_service.decrypt_to_string(encrypted_data)

        assert decrypted == ""

    def test_encrypt_empty_bytes(self, encryption_service):
        """Test encryption of empty bytes."""
        encrypted_data = encryption_service.encrypt(b"")
        decrypted = encryption_service.decrypt(encrypted_data)

        assert decrypted == b""

    def test_encrypt_unicode_string(self, encryption_service):
        """Test encryption of unicode string."""
        unicode_text = "测试中文 🚀 émojis and spéciäl chars"
        encrypted_data = encryption_service.encrypt(unicode_text)
        decrypted = encryption_service.decrypt_to_string(encrypted_data)

        assert decrypted == unicode_text

    def test_large_data_encryption(self, encryption_service):
        """Test encryption of large data."""
        large_data = "x" * 10000  # 10KB
        encrypted_data = encryption_service.encrypt(large_data)
        decrypted = encryption_service.decrypt_to_string(encrypted_data)

        assert decrypted == large_data

    @patch("shared.encryption.logger")
    def test_encryption_logging(self, mock_logger, encryption_service):
        """Test encryption logging."""
        plaintext = "test_logging"
        encryption_service.encrypt(plaintext)

        # Verify debug log was called
        mock_logger.debug.assert_called()

        encrypted_data = encryption_service.encrypt(plaintext)
        encryption_service.decrypt(encrypted_data)

        # Verify decrypt debug log was called
        assert mock_logger.debug.call_count >= 2
