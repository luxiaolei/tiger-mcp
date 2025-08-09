"""
Advanced encryption service for Tiger MCP system.

Provides AES-256-GCM encryption for sensitive data with key derivation,
rotation support, and secure credential management.
"""

import base64
import hashlib
import os
import secrets
import time
from typing import Dict, Optional, Union

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger
from pydantic import BaseModel, field_validator

from .config import SecurityConfig


class EncryptionError(Exception):
    """Base exception for encryption operations."""


class KeyDerivationError(EncryptionError):
    """Exception raised during key derivation."""


class DecryptionError(EncryptionError):
    """Exception raised during decryption."""


class EncryptedData(BaseModel):
    """Container for encrypted data with metadata."""

    ciphertext: str  # Base64 encoded
    nonce: str  # Base64 encoded
    tag: str  # Base64 encoded
    salt: str  # Base64 encoded
    key_version: int = 1
    algorithm: str = "AES-256-GCM"

    @field_validator("ciphertext", "nonce", "tag", "salt")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        """Validate base64 encoding."""
        try:
            base64.b64decode(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {e}")


class KeyRotationInfo(BaseModel):
    """Information about key rotation."""

    current_version: int
    previous_version: Optional[int] = None
    rotation_timestamp: float
    reason: str = "scheduled_rotation"


class EncryptionService:
    """
    Advanced encryption service using AES-256-GCM.

    Features:
    - AES-256-GCM encryption with authenticated encryption
    - PBKDF2 key derivation with configurable iterations
    - Key rotation support with version tracking
    - Environment-based master key management
    - Secure random salt and nonce generation
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize encryption service."""
        self._config = config or SecurityConfig()
        self._master_key = self._load_master_key()
        self._current_key_version = 1
        self._derived_keys: Dict[int, bytes] = {}

        logger.info("Encryption service initialized with AES-256-GCM")

    def _load_master_key(self) -> bytes:
        """Load master key from environment or generate new one."""
        key_b64 = os.getenv("ENCRYPTION_MASTER_KEY")

        if key_b64:
            try:
                key = base64.b64decode(key_b64)
                if len(key) != 32:  # 256 bits
                    raise ValueError("Master key must be 256 bits (32 bytes)")
                logger.info("Loaded master key from environment")
                return key
            except Exception as e:
                logger.error(f"Failed to load master key from environment: {e}")
                raise EncryptionError(f"Invalid master key: {e}")

        # Generate new master key for development
        if self._config.environment == "development":
            key = secrets.token_bytes(32)
            logger.warning(
                "Generated new master key for development. "
                f"Set ENCRYPTION_MASTER_KEY={base64.b64encode(key).decode()}"
            )
            return key

        raise EncryptionError(
            "Master key not found. Set ENCRYPTION_MASTER_KEY environment variable"
        )

    def _derive_key(self, salt: bytes, version: int = 1) -> bytes:
        """
        Derive encryption key using PBKDF2.

        Args:
            salt: Random salt for key derivation
            version: Key version for rotation support

        Returns:
            Derived 256-bit key
        """
        cache_key = (salt.hex(), version)
        if cache_key in self._derived_keys:
            return self._derived_keys[cache_key]

        try:
            # Combine master key with version for key rotation
            versioned_key = self._master_key + version.to_bytes(4, "big")

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits
                salt=salt,
                iterations=self._config.pbkdf2_iterations,
            )

            derived_key = kdf.derive(versioned_key)

            # Cache derived key
            self._derived_keys[cache_key] = derived_key

            return derived_key

        except Exception as e:
            logger.error(f"Key derivation failed: {e}")
            raise KeyDerivationError(f"Failed to derive key: {e}")

    def encrypt(
        self, plaintext: Union[str, bytes], key_version: Optional[int] = None
    ) -> EncryptedData:
        """
        Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: Data to encrypt
            key_version: Key version for rotation support

        Returns:
            EncryptedData container with ciphertext and metadata
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        version = key_version or self._current_key_version

        try:
            # Generate random salt and nonce
            salt = secrets.token_bytes(16)  # 128 bits
            nonce = secrets.token_bytes(12)  # 96 bits for GCM

            # Derive encryption key
            key = self._derive_key(salt, version)

            # Create cipher
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
            encryptor = cipher.encryptor()

            # Encrypt data
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()
            tag = encryptor.tag

            # Create encrypted data container
            encrypted_data = EncryptedData(
                ciphertext=base64.b64encode(ciphertext).decode(),
                nonce=base64.b64encode(nonce).decode(),
                tag=base64.b64encode(tag).decode(),
                salt=base64.b64encode(salt).decode(),
                key_version=version,
            )

            logger.debug(f"Successfully encrypted data (key_version={version})")
            return encrypted_data

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")

    def decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """
        Decrypt ciphertext using AES-256-GCM.

        Args:
            encrypted_data: Container with encrypted data and metadata

        Returns:
            Decrypted plaintext as bytes
        """
        try:
            # Decode base64 components
            ciphertext = base64.b64decode(encrypted_data.ciphertext)
            nonce = base64.b64decode(encrypted_data.nonce)
            tag = base64.b64decode(encrypted_data.tag)
            salt = base64.b64decode(encrypted_data.salt)

            # Derive decryption key
            key = self._derive_key(salt, encrypted_data.key_version)

            # Create cipher
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
            decryptor = cipher.decryptor()

            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            logger.debug(
                f"Successfully decrypted data (key_version={encrypted_data.key_version})"
            )
            return plaintext

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt data: {e}")

    def decrypt_to_string(self, encrypted_data: EncryptedData) -> str:
        """
        Decrypt ciphertext and return as string.

        Args:
            encrypted_data: Container with encrypted data and metadata

        Returns:
            Decrypted plaintext as string
        """
        plaintext_bytes = self.decrypt(encrypted_data)
        try:
            return plaintext_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise DecryptionError(f"Failed to decode decrypted data as UTF-8: {e}")

    def encrypt_credentials(
        self, credentials: Dict[str, Union[str, bytes]]
    ) -> Dict[str, EncryptedData]:
        """
        Encrypt multiple credentials.

        Args:
            credentials: Dictionary of credential name -> value

        Returns:
            Dictionary of credential name -> EncryptedData
        """
        encrypted_credentials = {}

        for name, value in credentials.items():
            try:
                encrypted_credentials[name] = self.encrypt(value)
                logger.debug(f"Encrypted credential: {name}")
            except Exception as e:
                logger.error(f"Failed to encrypt credential {name}: {e}")
                raise EncryptionError(f"Failed to encrypt credential {name}: {e}")

        return encrypted_credentials

    def decrypt_credentials(
        self, encrypted_credentials: Dict[str, EncryptedData]
    ) -> Dict[str, str]:
        """
        Decrypt multiple credentials.

        Args:
            encrypted_credentials: Dictionary of credential name -> EncryptedData

        Returns:
            Dictionary of credential name -> decrypted value
        """
        credentials = {}

        for name, encrypted_data in encrypted_credentials.items():
            try:
                credentials[name] = self.decrypt_to_string(encrypted_data)
                logger.debug(f"Decrypted credential: {name}")
            except Exception as e:
                logger.error(f"Failed to decrypt credential {name}: {e}")
                raise DecryptionError(f"Failed to decrypt credential {name}: {e}")

        return credentials

    def rotate_key(self, reason: str = "scheduled_rotation") -> KeyRotationInfo:
        """
        Rotate encryption key to new version.

        Args:
            reason: Reason for key rotation

        Returns:
            Information about the key rotation
        """
        previous_version = self._current_key_version
        self._current_key_version += 1

        # Clear derived key cache to force re-derivation
        self._derived_keys.clear()

        rotation_info = KeyRotationInfo(
            current_version=self._current_key_version,
            previous_version=previous_version,
            rotation_timestamp=time.time(),
            reason=reason,
        )

        logger.info(
            f"Key rotated from version {previous_version} to {self._current_key_version} "
            f"(reason: {reason})"
        )

        return rotation_info

    def can_decrypt_version(self, key_version: int) -> bool:
        """Check if a specific key version can be decrypted."""
        # We can decrypt any version as long as we have the master key
        return key_version > 0

    @property
    def current_key_version(self) -> int:
        """Get current key version."""
        return self._current_key_version

    def generate_secure_key(self, length: int = 32) -> str:
        """
        Generate cryptographically secure random key.

        Args:
            length: Key length in bytes (default: 32 for 256-bit)

        Returns:
            Base64-encoded secure random key
        """
        return base64.b64encode(secrets.token_bytes(length)).decode()

    def hash_key(self, key: str) -> str:
        """
        Create SHA-256 hash of a key for verification.

        Args:
            key: Key to hash

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def verify_data_integrity(self, encrypted_data: EncryptedData) -> bool:
        """
        Verify data integrity by attempting decryption.

        Args:
            encrypted_data: Encrypted data to verify

        Returns:
            True if data integrity is intact
        """
        try:
            self.decrypt(encrypted_data)
            return True
        except DecryptionError:
            return False


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions for common operations


def encrypt_tiger_credentials(
    tiger_id: str,
    private_key: str,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
) -> Dict[str, EncryptedData]:
    """
    Encrypt Tiger API credentials.

    Args:
        tiger_id: Tiger ID
        private_key: Private key for Tiger API
        access_token: Optional access token
        refresh_token: Optional refresh token

    Returns:
        Dictionary of encrypted credentials
    """
    service = get_encryption_service()

    credentials = {
        "tiger_id": tiger_id,
        "private_key": private_key,
    }

    if access_token:
        credentials["access_token"] = access_token

    if refresh_token:
        credentials["refresh_token"] = refresh_token

    return service.encrypt_credentials(credentials)


def decrypt_tiger_credentials(
    encrypted_credentials: Dict[str, EncryptedData],
) -> Dict[str, str]:
    """
    Decrypt Tiger API credentials.

    Args:
        encrypted_credentials: Dictionary of encrypted credentials

    Returns:
        Dictionary of decrypted credentials
    """
    service = get_encryption_service()
    return service.decrypt_credentials(encrypted_credentials)
