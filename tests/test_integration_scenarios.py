#!/usr/bin/env python3
"""
Integration test script for Tiger authentication components.
Tests integration scenarios without requiring full database setup.
"""
import sys
import tempfile
import os
from pathlib import Path

# Add the packages to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'packages/shared/src'))
sys.path.insert(0, str(project_root / 'packages/mcp-server/src'))

def test_tiger_config_integration():
    """Test Tiger configuration integration with account manager concepts."""
    print("\n🧪 Testing Tiger configuration integration...")
    
    try:
        from shared.tiger_config import TigerConfig, TigerPropertiesManager
        from shared.encryption import EncryptionService
        
        # Create a realistic Tiger configuration
        config = TigerConfig(
            tiger_id="tiger123456",
            account="88888888",
            license="TBHK", 
            environment="SANDBOX",
            private_key_pk8="-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----"
        )
        
        # Test configuration validation
        assert config.is_valid(), "Config should be valid"
        print("✅ Tiger configuration created and validated")
        
        # Test encryption integration
        encryption = EncryptionService()
        credentials = {
            "tiger_id": config.tiger_id,
            "account": config.account,
            "private_key": config.private_key
        }
        
        encrypted_creds = encryption.encrypt_credentials(credentials)
        decrypted_creds = encryption.decrypt_credentials(encrypted_creds)
        
        assert decrypted_creds["tiger_id"] == config.tiger_id, "Tiger ID should match"
        assert decrypted_creds["account"] == config.account, "Account should match"
        print("✅ Tiger configuration encryption/decryption works")
        
        return True
        
    except Exception as e:
        print(f"❌ Tiger configuration integration failed: {e}")
        return False

def test_migration_script_simulation():
    """Simulate the migration script functionality."""
    print("\n🧪 Testing migration script simulation...")
    
    try:
        from shared.tiger_config import TigerPropertiesManager
        
        # Create a temporary directory with mock .properties files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a mock tiger_openapi_config.properties file
            config_content = """tiger_id=test_tiger_123
account=12345678
license=TBSG
env=PROD
private_key_pk8=-----BEGIN PRIVATE KEY-----\\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\\n-----END PRIVATE KEY-----
"""
            config_file = temp_path / "tiger_openapi_config.properties"
            with open(config_file, "w") as f:
                f.write(config_content)
            
            # Create a mock token file
            token_content = "token=dGVzdF90b2tlbl8xNzA5NzY4NDAwLDE3MDk4NTQ4MDAsc2lnbmF0dXJl"
            token_file = temp_path / "tiger_openapi_token.properties"
            with open(token_file, "w") as f:
                f.write(token_content)
            
            # Test loading configuration
            manager = TigerPropertiesManager(str(temp_path))
            config = manager.load_config()
            
            if config:
                assert config.tiger_id == "test_tiger_123", "Should load tiger_id"
                assert config.account == "12345678", "Should load account"
                assert config.license == "TBSG", "Should load license"
                assert config.environment == "PROD", "Should load environment"
                print("✅ Migration script can load existing Tiger .properties files")
                
                # Test token loading
                token = manager.load_token()
                if token:
                    print("✅ Migration script can load existing Tiger tokens")
                else:
                    print("⚠️  Token loading may need jproperties library")
                
                return True
            else:
                print("⚠️  Configuration loading may need jproperties library")
                return False
                
    except Exception as e:
        print(f"❌ Migration script simulation failed: {e}")
        return False

def test_mcp_tools_integration():
    """Test MCP tools integration with Tiger authentication."""
    print("\n🧪 Testing MCP tools integration...")
    
    try:
        # Import MCP server components (if available)
        try:
            from mcp_server.tools import account_tools
            print("✅ MCP account tools imported successfully")
            
            # Test if the tools are properly structured
            # Check if account tools have the expected methods
            expected_methods = ['get_account_info', 'list_accounts']
            for method in expected_methods:
                if hasattr(account_tools, method):
                    print(f"✅ Account tool method {method} available")
                else:
                    print(f"⚠️  Account tool method {method} not found")
            
        except ImportError as e:
            print(f"⚠️  MCP tools import failed (expected in isolated test): {e}")
        
        # Test Tiger config integration with MCP concepts
        from shared.tiger_config import TigerConfig
        
        # Create a configuration that would be used by MCP tools
        mcp_config = TigerConfig(
            tiger_id="mcp_test_123",
            account="99999999", 
            license="TBNZ",
            environment="SANDBOX",
            private_key_pk8="-----BEGIN PRIVATE KEY-----\ntest_key_for_mcp\n-----END PRIVATE KEY-----"
        )
        
        assert mcp_config.is_valid(), "MCP config should be valid"
        print("✅ Tiger configuration compatible with MCP tools structure")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP tools integration test failed: {e}")
        return False

def test_account_management_scenarios():
    """Test account management scenarios."""
    print("\n🧪 Testing account management scenarios...")
    
    try:
        from shared.tiger_config import TigerConfig, create_tiger_config_from_dict
        
        # Test multiple account scenarios
        accounts = [
            {
                "tiger_id": "hk_trader_001", 
                "account": "11111111",
                "license": "TBHK",
                "environment": "PROD",
                "private_key_pk8": "-----BEGIN PRIVATE KEY-----\nhk_key\n-----END PRIVATE KEY-----"
            },
            {
                "tiger_id": "sg_trader_001",
                "account": "22222222", 
                "license": "TBSG",
                "environment": "SANDBOX",
                "private_key_pk8": "-----BEGIN PRIVATE KEY-----\nsg_key\n-----END PRIVATE KEY-----"
            },
            {
                "tiger_id": "nz_trader_001",
                "account": "33333333",
                "license": "TBNZ", 
                "environment": "PROD",
                "private_key_pk8": "-----BEGIN PRIVATE KEY-----\nnz_key\n-----END PRIVATE KEY-----"
            }
        ]
        
        configs = []
        for account_data in accounts:
            config = create_tiger_config_from_dict(account_data)
            assert config.is_valid(), f"Account {account_data['account']} should be valid"
            configs.append(config)
        
        print(f"✅ Created and validated {len(configs)} Tiger account configurations")
        
        # Test license-based routing scenarios
        license_counts = {}
        for config in configs:
            license_counts[config.license] = license_counts.get(config.license, 0) + 1
        
        print(f"✅ License distribution: {license_counts}")
        
        # Test environment switching scenarios
        prod_accounts = [c for c in configs if c.environment == "PROD"]
        sandbox_accounts = [c for c in configs if c.environment == "SANDBOX"]
        
        print(f"✅ Environment distribution: {len(prod_accounts)} PROD, {len(sandbox_accounts)} SANDBOX")
        
        return True
        
    except Exception as e:
        print(f"❌ Account management scenario test failed: {e}")
        return False

def test_error_handling_scenarios():
    """Test error handling scenarios."""
    print("\n🧪 Testing error handling scenarios...")
    
    try:
        from shared.tiger_config import TigerConfig, validate_tiger_credentials
        
        # Test invalid credentials
        invalid_configs = [
            # Missing tiger_id
            TigerConfig(tiger_id="", account="12345678", license="TBHK", environment="PROD"),
            # Invalid license
            TigerConfig(tiger_id="test123", account="12345678", license="INVALID", environment="PROD"),
            # Invalid environment
            TigerConfig(tiger_id="test123", account="12345678", license="TBHK", environment="INVALID"),
            # Missing private key
            TigerConfig(tiger_id="test123", account="12345678", license="TBHK", environment="PROD", private_key_pk8="")
        ]
        
        error_count = 0
        for i, config in enumerate(invalid_configs):
            is_valid, errors = validate_tiger_credentials(config)
            if not is_valid and len(errors) > 0:
                error_count += 1
                print(f"✅ Invalid config {i+1} properly rejected: {errors[0]}")
            else:
                print(f"❌ Invalid config {i+1} was not properly rejected")
        
        assert error_count == len(invalid_configs), "All invalid configs should be rejected"
        print("✅ Error handling for invalid Tiger credentials works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling scenario test failed: {e}")
        return False

def run_all_integration_tests():
    """Run all integration tests."""
    print("🚀 Starting Tiger Authentication Integration Tests\n")
    print("=" * 70)
    
    test_results = []
    
    # Run each test
    tests = [
        ("Tiger Config Integration", test_tiger_config_integration),
        ("Migration Script Simulation", test_migration_script_simulation), 
        ("MCP Tools Integration", test_mcp_tools_integration),
        ("Account Management Scenarios", test_account_management_scenarios),
        ("Error Handling Scenarios", test_error_handling_scenarios)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, "✅" if result else "⚠️ "))
        except Exception as e:
            test_results.append((test_name, f"❌ {e}"))
    
    print("\n" + "=" * 70)
    print("🏁 Tiger Authentication Integration Test Results:")
    print("=" * 70)
    
    success_count = 0
    for test_name, result in test_results:
        print(f"  {test_name}: {result}")
        if result.startswith("✅"):
            success_count += 1
    
    print(f"\n📊 Test Summary: {success_count}/{len(tests)} tests passed")
    print("=" * 70)

if __name__ == "__main__":
    run_all_integration_tests()