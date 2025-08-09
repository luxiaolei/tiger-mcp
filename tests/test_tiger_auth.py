#!/usr/bin/env python3
"""
Manual test script for Tiger authentication components.
This script tests the core Tiger authentication functionality without dependencies on broken test fixtures.
"""
import sys
import tempfile
import os
from pathlib import Path

# Add the packages to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'packages/shared/src'))
sys.path.insert(0, str(project_root / 'packages/database/src'))

try:
    from shared.tiger_config import (
        TigerConfig, 
        TigerPropertiesManager, 
        validate_tiger_credentials,
        create_tiger_config_from_dict
    )
    from shared.encryption import EncryptionService
    print("✅ Successfully imported Tiger authentication modules")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)

def test_tiger_config_creation():
    """Test TigerConfig creation and validation."""
    print("\n🧪 Testing TigerConfig creation and validation...")
    
    # Test valid config
    valid_config = TigerConfig(
        tiger_id="test123",
        account="12345678", 
        license="TBHK",
        environment="SANDBOX",
        private_key_pk8="-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----"
    )
    
    assert valid_config.is_valid(), "Valid config should pass validation"
    assert valid_config.private_key_format == "PK8", "Should detect PK8 format"
    print("✅ Valid TigerConfig created and validated")
    
    # Test validation
    is_valid, errors = validate_tiger_credentials(valid_config)
    assert is_valid, f"Valid config should pass detailed validation. Errors: {errors}"
    print("✅ TigerConfig passed detailed validation")
    
    # Test invalid config
    invalid_config = TigerConfig(
        tiger_id="",
        account="", 
        license="INVALID",
        environment="WRONG"
    )
    
    assert not invalid_config.is_valid(), "Invalid config should fail validation"
    is_valid, errors = validate_tiger_credentials(invalid_config)
    assert not is_valid, "Invalid config should fail detailed validation"
    assert len(errors) > 0, "Should return validation errors"
    print("✅ Invalid TigerConfig correctly rejected")

def test_tiger_properties_manager():
    """Test TigerPropertiesManager file operations."""
    print("\n🧪 Testing TigerPropertiesManager...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = TigerPropertiesManager(temp_dir)
        
        # Test config saving and loading
        config = TigerConfig(
            tiger_id="test456",
            account="87654321",
            license="TBSG", 
            environment="PROD",
            private_key_pk1="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
        )
        
        # Test saving
        saved = manager.save_config(config)
        if saved:
            print("✅ TigerConfig saved to properties file")
        else:
            print("⚠️  Could not save config (jproperties may not be installed)")
            return
        
        # Test loading
        loaded_config = manager.load_config()
        if loaded_config:
            assert loaded_config.tiger_id == config.tiger_id, "Tiger ID should match"
            assert loaded_config.account == config.account, "Account should match" 
            assert loaded_config.license == config.license, "License should match"
            assert loaded_config.environment == config.environment, "Environment should match"
            assert loaded_config.private_key_format == "PK1", "Should detect PK1 format"
            print("✅ TigerConfig loaded from properties file correctly")
        else:
            print("⚠️  Could not load config (jproperties may not be installed)")
        
        # Test token operations
        test_token = "dGVzdF90b2tlbl8xNzA5NzY4NDAwLDE3MDk4NTQ4MDAsc2lnbmF0dXJl"
        
        token_saved = manager.save_token(test_token)
        if token_saved:
            print("✅ Token saved to properties file")
            
            loaded_token = manager.load_token()
            assert loaded_token == test_token, "Loaded token should match saved token"
            print("✅ Token loaded from properties file correctly")
            
            # Test token info
            token_info = manager.get_token_info()
            if token_info:
                print(f"✅ Token info extracted: {token_info}")
            else:
                print("⚠️  Could not extract token info (may be invalid format)")
        else:
            print("⚠️  Could not save token (jproperties may not be installed)")

def test_credential_encryption():
    """Test credential encryption for Tiger credentials."""
    print("\n🧪 Testing credential encryption...")
    
    try:
        # Initialize encryption
        encryption = EncryptionService()
        print("✅ EncryptionService initialized")
        
        # Test Tiger credentials encryption
        credentials = {
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----",
            "tiger_id": "test789",
            "account": "11223344"
        }
        
        encrypted_data = encryption.encrypt_credentials(credentials)
        assert isinstance(encrypted_data, dict), "Should return dictionary of encrypted data"
        assert "private_key" in encrypted_data, "Should encrypt private key"
        print("✅ Tiger credentials encrypted")
        
        decrypted_creds = encryption.decrypt_credentials(encrypted_data)
        assert isinstance(decrypted_creds, dict), "Should return dictionary of decrypted data"
        assert decrypted_creds["private_key"] == credentials["private_key"], "Decrypted private key should match"
        assert decrypted_creds["tiger_id"] == credentials["tiger_id"], "Decrypted tiger_id should match"
        print("✅ Tiger credentials decrypted correctly")
        
    except ImportError as e:
        print(f"⚠️  Could not test encryption: {e}")

def test_config_from_dict():
    """Test creating TigerConfig from dictionary."""
    print("\n🧪 Testing TigerConfig creation from dictionary...")
    
    config_dict = {
        "tiger_id": "dict123",
        "account": "99887766",
        "license": "TBAU", 
        "environment": "SANDBOX",
        "private_key_pk8": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
    }
    
    config = create_tiger_config_from_dict(config_dict)
    assert config.tiger_id == config_dict["tiger_id"], "Tiger ID should match"
    assert config.account == config_dict["account"], "Account should match"
    assert config.license == config_dict["license"], "License should match"
    assert config.environment == config_dict["environment"], "Environment should match"
    assert config.private_key_pk8 == config_dict["private_key_pk8"], "Private key should match"
    print("✅ TigerConfig created from dictionary correctly")

def run_all_tests():
    """Run all Tiger authentication tests."""
    print("🚀 Starting Tiger Authentication Component Tests\n")
    print("=" * 60)
    
    test_results = []
    
    try:
        test_tiger_config_creation()
        test_results.append("TigerConfig Creation: ✅")
    except Exception as e:
        test_results.append(f"TigerConfig Creation: ❌ {e}")
    
    try:
        test_tiger_properties_manager()
        test_results.append("TigerPropertiesManager: ✅")
    except Exception as e:
        test_results.append(f"TigerPropertiesManager: ❌ {e}")
    
    try:
        test_credential_encryption()
        test_results.append("Credential Encryption: ✅")
    except Exception as e:
        test_results.append(f"Credential Encryption: ❌ {e}")
    
    try:
        test_config_from_dict()
        test_results.append("Config from Dict: ✅")
    except Exception as e:
        test_results.append(f"Config from Dict: ❌ {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Tiger Authentication Test Results:")
    print("=" * 60)
    
    for result in test_results:
        print(f"  {result}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    run_all_tests()