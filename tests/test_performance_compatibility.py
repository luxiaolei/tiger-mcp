#!/usr/bin/env python3
"""
Performance and compatibility test script for Tiger authentication system.
Tests multiple account handling, environment switching, and token management.
"""
import sys
import time
import tempfile
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any

# Add the packages to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'packages/shared/src'))

def test_multiple_account_configurations():
    """Test handling multiple Tiger account configurations."""
    print("\n🧪 Testing multiple Tiger account configurations...")
    
    try:
        from shared.tiger_config import TigerConfig, create_tiger_config_from_dict
        from shared.encryption import EncryptionService
        
        # Create multiple account configurations representing different regions and environments
        account_configs = [
            {
                "tiger_id": f"hk_trader_{i:03d}",
                "account": f"1111{i:04d}",
                "license": "TBHK",
                "environment": "PROD" if i % 2 == 0 else "SANDBOX",
                "private_key_pk8": f"-----BEGIN PRIVATE KEY-----\nhk_key_{i}\n-----END PRIVATE KEY-----"
            } for i in range(10)
        ] + [
            {
                "tiger_id": f"sg_trader_{i:03d}",
                "account": f"2222{i:04d}",
                "license": "TBSG", 
                "environment": "PROD" if i % 3 == 0 else "SANDBOX",
                "private_key_pk8": f"-----BEGIN PRIVATE KEY-----\nsg_key_{i}\n-----END PRIVATE KEY-----"
            } for i in range(10)
        ] + [
            {
                "tiger_id": f"nz_trader_{i:03d}",
                "account": f"3333{i:04d}",
                "license": "TBNZ",
                "environment": "PROD",
                "private_key_pk8": f"-----BEGIN PRIVATE KEY-----\nnz_key_{i}\n-----END PRIVATE KEY-----"
            } for i in range(5)
        ]
        
        # Test configuration creation performance
        start_time = time.time()
        configs = []
        for config_data in account_configs:
            config = create_tiger_config_from_dict(config_data)
            assert config.is_valid(), f"Config for {config_data['tiger_id']} should be valid"
            configs.append(config)
        
        creation_time = time.time() - start_time
        print(f"✅ Created {len(configs)} Tiger configurations in {creation_time:.3f}s")
        
        # Test license-based routing performance
        start_time = time.time()
        license_groups = {}
        for config in configs:
            if config.license not in license_groups:
                license_groups[config.license] = []
            license_groups[config.license].append(config)
        
        routing_time = time.time() - start_time
        print(f"✅ License-based routing completed in {routing_time:.3f}s")
        print(f"   License distribution: {[(k, len(v)) for k, v in license_groups.items()]}")
        
        # Test concurrent encryption of credentials
        encryption = EncryptionService()
        
        def encrypt_config(config):
            credentials = {
                "tiger_id": config.tiger_id,
                "account": config.account,
                "private_key": config.private_key
            }
            return encryption.encrypt_credentials(credentials)
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            encrypted_results = list(executor.map(encrypt_config, configs))
        
        concurrent_encryption_time = time.time() - start_time
        print(f"✅ Concurrent encryption of {len(configs)} configs in {concurrent_encryption_time:.3f}s")
        
        # Performance metrics
        avg_creation_time = creation_time / len(configs) * 1000  # ms per config
        avg_encryption_time = concurrent_encryption_time / len(configs) * 1000  # ms per config
        
        print(f"📊 Performance Metrics:")
        print(f"   Average config creation: {avg_creation_time:.2f}ms per account")
        print(f"   Average encryption: {avg_encryption_time:.2f}ms per account")
        
        # Performance assertions
        assert avg_creation_time < 10, "Config creation should be under 10ms per account"
        assert avg_encryption_time < 100, "Encryption should be under 100ms per account" 
        print("✅ Performance requirements met")
        
        return True
        
    except Exception as e:
        print(f"❌ Multiple account configuration test failed: {e}")
        return False

def test_environment_switching():
    """Test environment switching between PROD and SANDBOX."""
    print("\n🧪 Testing environment switching...")
    
    try:
        from shared.tiger_config import TigerConfig
        
        # Create base configuration
        base_config = {
            "tiger_id": "env_test_trader",
            "account": "88888888",
            "license": "TBHK",
            "private_key_pk8": "-----BEGIN PRIVATE KEY-----\ntest_key\n-----END PRIVATE KEY-----"
        }
        
        # Test switching between environments
        environments = ["PROD", "SANDBOX"]
        configs = {}
        
        start_time = time.time()
        for env in environments:
            config = TigerConfig(
                **base_config,
                environment=env
            )
            assert config.is_valid(), f"{env} config should be valid"
            configs[env] = config
        
        switch_time = time.time() - start_time
        print(f"✅ Environment switching completed in {switch_time:.3f}s")
        
        # Test environment-specific validation
        prod_config = configs["PROD"]
        sandbox_config = configs["SANDBOX"]
        
        assert prod_config.environment == "PROD", "Production config should have PROD environment"
        assert sandbox_config.environment == "SANDBOX", "Sandbox config should have SANDBOX environment"
        print("✅ Environment-specific validation works")
        
        # Test bulk environment switching
        start_time = time.time()
        bulk_configs = []
        for i in range(100):
            env = "PROD" if i % 2 == 0 else "SANDBOX"
            config = TigerConfig(
                tiger_id=f"bulk_trader_{i:03d}",
                account=f"9999{i:04d}",
                license="TBSG",
                environment=env,
                private_key_pk8=f"-----BEGIN PRIVATE KEY-----\nbulk_key_{i}\n-----END PRIVATE KEY-----"
            )
            bulk_configs.append(config)
        
        bulk_switch_time = time.time() - start_time
        print(f"✅ Bulk environment switching (100 configs) in {bulk_switch_time:.3f}s")
        
        # Environment distribution
        prod_count = sum(1 for c in bulk_configs if c.environment == "PROD")
        sandbox_count = sum(1 for c in bulk_configs if c.environment == "SANDBOX")
        print(f"   Environment distribution: {prod_count} PROD, {sandbox_count} SANDBOX")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment switching test failed: {e}")
        return False

def test_token_management_scenarios():
    """Test token management scenarios."""
    print("\n🧪 Testing token management scenarios...")
    
    try:
        from shared.tiger_config import TigerPropertiesManager
        
        # Test token operations with temporary directories
        token_managers = []
        temp_dirs = []
        
        # Create multiple temporary directories for different accounts
        for i in range(10):
            temp_dir = tempfile.mkdtemp()
            temp_dirs.append(temp_dir)
            manager = TigerPropertiesManager(temp_dir)
            token_managers.append(manager)
        
        # Test concurrent token saving
        start_time = time.time()
        test_tokens = [f"token_for_account_{i:03d}_data" for i in range(10)]
        
        def save_token(manager_token_pair):
            manager, token = manager_token_pair
            return manager.save_token(token)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            save_results = list(executor.map(save_token, zip(token_managers, test_tokens)))
        
        save_time = time.time() - start_time
        successful_saves = sum(1 for result in save_results if result)
        print(f"✅ Concurrent token saving: {successful_saves}/{len(test_tokens)} in {save_time:.3f}s")
        
        # Test concurrent token loading
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            load_results = list(executor.map(lambda m: m.load_token(), token_managers))
        
        load_time = time.time() - start_time
        successful_loads = sum(1 for token in load_results if token)
        print(f"✅ Concurrent token loading: {successful_loads}/{len(token_managers)} in {load_time:.3f}s")
        
        # Test token expiry checking performance
        start_time = time.time()
        expiry_results = []
        for manager in token_managers:
            is_expired = manager.is_token_expired()
            expiry_results.append(is_expired)
        
        expiry_check_time = time.time() - start_time
        print(f"✅ Token expiry checking completed in {expiry_check_time:.3f}s")
        print(f"   Expired tokens: {sum(1 for expired in expiry_results if expired)}/{len(expiry_results)}")
        
        # Cleanup
        import shutil
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Token management test failed: {e}")
        return False

def test_license_based_routing():
    """Test license-based routing performance and accuracy."""
    print("\n🧪 Testing license-based routing...")
    
    try:
        from shared.tiger_config import TigerConfig
        
        # Create accounts with different licenses
        licenses = ["TBHK", "TBSG", "TBNZ", "TBAU", "TBUK"]
        configs_per_license = 20
        
        all_configs = []
        for license_type in licenses:
            for i in range(configs_per_license):
                config = TigerConfig(
                    tiger_id=f"{license_type.lower()}_trader_{i:03d}",
                    account=f"{hash(license_type) % 9000 + 1000}{i:04d}",
                    license=license_type,
                    environment="PROD" if i % 2 == 0 else "SANDBOX",
                    private_key_pk8=f"-----BEGIN PRIVATE KEY-----\n{license_type.lower()}_key_{i}\n-----END PRIVATE KEY-----"
                )
                all_configs.append(config)
        
        print(f"✅ Created {len(all_configs)} configs across {len(licenses)} licenses")
        
        # Test routing performance
        start_time = time.time()
        license_routes = {}
        for config in all_configs:
            if config.license not in license_routes:
                license_routes[config.license] = []
            license_routes[config.license].append(config)
        
        routing_time = time.time() - start_time
        print(f"✅ License-based routing completed in {routing_time:.3f}s")
        
        # Verify routing accuracy
        for license_type in licenses:
            expected_count = configs_per_license
            actual_count = len(license_routes.get(license_type, []))
            assert actual_count == expected_count, f"{license_type} should have {expected_count} configs"
        
        print("✅ License-based routing accuracy verified")
        
        # Test license-specific operations performance
        start_time = time.time()
        license_operations = {}
        for license_type, configs in license_routes.items():
            # Simulate license-specific operations
            prod_configs = [c for c in configs if c.environment == "PROD"]
            sandbox_configs = [c for c in configs if c.environment == "SANDBOX"]
            
            license_operations[license_type] = {
                "total": len(configs),
                "prod": len(prod_configs),
                "sandbox": len(sandbox_configs)
            }
        
        operations_time = time.time() - start_time
        print(f"✅ License-specific operations completed in {operations_time:.3f}s")
        
        # Display routing statistics
        print("📊 License Routing Statistics:")
        for license_type, stats in license_operations.items():
            print(f"   {license_type}: {stats['total']} total ({stats['prod']} PROD, {stats['sandbox']} SANDBOX)")
        
        return True
        
    except Exception as e:
        print(f"❌ License-based routing test failed: {e}")
        return False

def test_concurrent_operations():
    """Test concurrent operations on Tiger configurations."""
    print("\n🧪 Testing concurrent operations...")
    
    try:
        from shared.tiger_config import TigerConfig, TigerPropertiesManager
        from shared.encryption import EncryptionService
        
        # Create test configurations
        test_configs = []
        for i in range(50):
            config = TigerConfig(
                tiger_id=f"concurrent_trader_{i:03d}",
                account=f"7777{i:04d}",
                license=["TBHK", "TBSG", "TBNZ"][i % 3],
                environment="PROD" if i % 2 == 0 else "SANDBOX",
                private_key_pk8=f"-----BEGIN PRIVATE KEY-----\nconcurrent_key_{i}\n-----END PRIVATE KEY-----"
            )
            test_configs.append(config)
        
        # Test concurrent validation
        start_time = time.time()
        def validate_config(config):
            return config.is_valid()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            validation_results = list(executor.map(validate_config, test_configs))
        
        validation_time = time.time() - start_time
        valid_configs = sum(1 for result in validation_results if result)
        print(f"✅ Concurrent validation: {valid_configs}/{len(test_configs)} in {validation_time:.3f}s")
        
        # Test concurrent encryption
        encryption = EncryptionService()
        
        def encrypt_config_credentials(config):
            credentials = {
                "tiger_id": config.tiger_id,
                "account": config.account,
                "private_key": config.private_key
            }
            return encryption.encrypt_credentials(credentials)
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            encryption_results = list(executor.map(encrypt_config_credentials, test_configs))
        
        encryption_time = time.time() - start_time
        print(f"✅ Concurrent encryption: {len(encryption_results)} configs in {encryption_time:.3f}s")
        
        # Test concurrent decryption
        start_time = time.time()
        def decrypt_credentials(encrypted_data):
            return encryption.decrypt_credentials(encrypted_data)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            decryption_results = list(executor.map(decrypt_credentials, encryption_results))
        
        decryption_time = time.time() - start_time
        print(f"✅ Concurrent decryption: {len(decryption_results)} configs in {decryption_time:.3f}s")
        
        # Verify data integrity
        for i, (original, decrypted) in enumerate(zip(test_configs, decryption_results)):
            assert decrypted["tiger_id"] == original.tiger_id, f"Config {i} tiger_id mismatch"
            assert decrypted["account"] == original.account, f"Config {i} account mismatch"
        
        print("✅ Concurrent operations data integrity verified")
        
        # Performance summary
        print("📊 Concurrent Operations Performance:")
        print(f"   Validation: {validation_time/len(test_configs)*1000:.2f}ms per config")
        print(f"   Encryption: {encryption_time/len(test_configs)*1000:.2f}ms per config")
        print(f"   Decryption: {decryption_time/len(test_configs)*1000:.2f}ms per config")
        
        return True
        
    except Exception as e:
        print(f"❌ Concurrent operations test failed: {e}")
        return False

def run_all_performance_tests():
    """Run all performance and compatibility tests."""
    print("🚀 Starting Tiger Authentication Performance & Compatibility Tests\n")
    print("=" * 80)
    
    test_results = []
    
    # Run each test
    tests = [
        ("Multiple Account Configurations", test_multiple_account_configurations),
        ("Environment Switching", test_environment_switching),
        ("Token Management Scenarios", test_token_management_scenarios),
        ("License-based Routing", test_license_based_routing),
        ("Concurrent Operations", test_concurrent_operations)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            result = test_func()
            test_results.append((test_name, "✅" if result else "⚠️ "))
        except Exception as e:
            test_results.append((test_name, f"❌ {e}"))
    
    print("\n" + "=" * 80)
    print("🏁 Tiger Authentication Performance & Compatibility Test Results:")
    print("=" * 80)
    
    success_count = 0
    for test_name, result in test_results:
        print(f"  {test_name}: {result}")
        if result.startswith("✅"):
            success_count += 1
    
    print(f"\n📊 Test Summary: {success_count}/{len(tests)} tests passed")
    print("=" * 80)

if __name__ == "__main__":
    run_all_performance_tests()