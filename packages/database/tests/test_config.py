"""
Tests for database configuration.

This module tests:
- Database configuration loading
- Connection string generation
- SSL configuration and validation
- Environment-specific settings
"""

import os
from unittest.mock import patch

import pytest
from database.config import DatabaseConfig, db_config


class TestDatabaseConfig:
    """Test cases for DatabaseConfig class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = DatabaseConfig()

        # Test default values
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.name == "tiger_mcp"
        assert config.user == "postgres"
        assert config.password == ""
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600
        assert config.connect_timeout == 10
        assert config.query_timeout == 30
        assert config.environment == "development"
        assert config.debug is False

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "DB_HOST": "test.example.com",
                "DB_PORT": "5433",
                "DB_NAME": "test_db",
                "DB_USER": "test_user",
                "DB_PASSWORD": "test_password",
                "DB_POOL_SIZE": "5",
                "DB_MAX_OVERFLOW": "10",
                "DB_POOL_TIMEOUT": "60",
                "DB_POOL_RECYCLE": "7200",
                "DB_CONNECT_TIMEOUT": "20",
                "DB_QUERY_TIMEOUT": "60",
                "ENVIRONMENT": "testing",
                "DB_DEBUG": "true",
            },
        ):
            config = DatabaseConfig()

            assert config.host == "test.example.com"
            assert config.port == 5433
            assert config.name == "test_db"
            assert config.user == "test_user"
            assert config.password == "test_password"
            assert config.pool_size == 5
            assert config.max_overflow == 10
            assert config.pool_timeout == 60
            assert config.pool_recycle == 7200
            assert config.connect_timeout == 20
            assert config.query_timeout == 60
            assert config.environment == "testing"
            assert config.debug is True

    def test_ssl_configuration(self):
        """Test SSL configuration options."""
        with patch.dict(
            os.environ,
            {
                "DB_SSL_MODE": "require",
                "DB_SSL_CERT": "/path/to/cert.pem",
                "DB_SSL_KEY": "/path/to/key.pem",
                "DB_SSL_CA": "/path/to/ca.pem",
            },
        ):
            config = DatabaseConfig()

            assert config.ssl_mode == "require"
            assert config.ssl_cert == "/path/to/cert.pem"
            assert config.ssl_key == "/path/to/key.pem"
            assert config.ssl_ca == "/path/to/ca.pem"

    def test_database_url_generation_basic(self):
        """Test basic database URL generation."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
        )

        expected_url = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
        assert config.database_url == expected_url

    def test_database_url_generation_no_password(self):
        """Test database URL generation without password."""
        config = DatabaseConfig(
            host="localhost", port=5432, name="test_db", user="test_user", password=""
        )

        expected_url = "postgresql+asyncpg://test_user@localhost:5432/test_db"
        assert config.database_url == expected_url

    def test_database_url_with_ssl_parameters(self):
        """Test database URL generation with SSL parameters."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
            ssl_mode="require",
            ssl_cert="/path/to/cert.pem",
            ssl_key="/path/to/key.pem",
            ssl_ca="/path/to/ca.pem",
        )

        url = config.database_url

        # Check base URL
        assert url.startswith(
            "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
        )

        # Check SSL parameters
        assert "sslmode=require" in url
        assert "sslcert=/path/to/cert.pem" in url
        assert "sslkey=/path/to/key.pem" in url
        assert "sslrootcert=/path/to/ca.pem" in url

    def test_sync_database_url_generation(self):
        """Test synchronous database URL generation for Alembic."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
        )

        expected_url = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert config.sync_database_url == expected_url

    def test_sync_database_url_with_ssl(self):
        """Test synchronous database URL with SSL parameters."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
            ssl_mode="require",
        )

        url = config.sync_database_url

        assert url.startswith("postgresql://test_user:test_pass@localhost:5432/test_db")
        assert "sslmode=require" in url

    def test_is_production_property(self):
        """Test is_production property."""
        # Test production environment
        config = DatabaseConfig(environment="production")
        assert config.is_production is True

        config = DatabaseConfig(environment="PRODUCTION")
        assert config.is_production is True

        # Test non-production environments
        for env in ["development", "testing", "staging", "dev"]:
            config = DatabaseConfig(environment=env)
            assert config.is_production is False

    def test_validation_success(self):
        """Test successful configuration validation."""
        config = DatabaseConfig(
            host="localhost", port=5432, name="test_db", user="test_user", pool_size=5
        )

        # Should not raise any exception
        config.validate()

    def test_validation_missing_host(self):
        """Test validation with missing host."""
        config = DatabaseConfig(host="")

        with pytest.raises(ValueError, match="Database host is required"):
            config.validate()

    def test_validation_missing_name(self):
        """Test validation with missing database name."""
        config = DatabaseConfig(name="")

        with pytest.raises(ValueError, match="Database name is required"):
            config.validate()

    def test_validation_missing_user(self):
        """Test validation with missing user."""
        config = DatabaseConfig(user="")

        with pytest.raises(ValueError, match="Database user is required"):
            config.validate()

    def test_validation_invalid_port(self):
        """Test validation with invalid port."""
        config = DatabaseConfig(port=0)

        with pytest.raises(ValueError, match="Database port must be positive"):
            config.validate()

        config = DatabaseConfig(port=-1)

        with pytest.raises(ValueError, match="Database port must be positive"):
            config.validate()

    def test_validation_invalid_pool_size(self):
        """Test validation with invalid pool size."""
        config = DatabaseConfig(pool_size=0)

        with pytest.raises(ValueError, match="Pool size must be positive"):
            config.validate()

        config = DatabaseConfig(pool_size=-1)

        with pytest.raises(ValueError, match="Pool size must be positive"):
            config.validate()


class TestDatabaseConfigCreation:
    """Test different ways of creating database configuration."""

    def test_explicit_parameters(self):
        """Test creating config with explicit parameters."""
        config = DatabaseConfig(
            host="db.example.com",
            port=5433,
            name="my_db",
            user="my_user",
            password="my_pass",
            pool_size=15,
            debug=True,
        )

        assert config.host == "db.example.com"
        assert config.port == 5433
        assert config.name == "my_db"
        assert config.user == "my_user"
        assert config.password == "my_pass"
        assert config.pool_size == 15
        assert config.debug is True

    def test_mixed_explicit_and_environment(self):
        """Test mixed explicit parameters and environment variables."""
        with patch.dict(os.environ, {"DB_HOST": "env.example.com", "DB_PORT": "5433"}):
            # Explicit parameters should take precedence
            config = DatabaseConfig(host="explicit.example.com", name="explicit_db")

            assert config.host == "explicit.example.com"  # Explicit wins
            assert config.port == 5432  # Default (env var doesn't override explicit)
            assert config.name == "explicit_db"  # Explicit


class TestDatabaseConfigEdgeCases:
    """Test edge cases and special scenarios."""

    def test_special_characters_in_password(self):
        """Test handling of special characters in password."""
        config = DatabaseConfig(host="localhost", user="user", password="p@ssw0rd!#$%")

        # URL should be properly encoded
        url = config.database_url
        assert "p@ssw0rd!#$%" in url  # asyncpg handles URL encoding

    def test_unicode_in_database_name(self):
        """Test handling of unicode characters."""
        config = DatabaseConfig(host="localhost", user="user", name="test_db_üñíçödé")

        url = config.database_url
        assert "test_db_üñíçödé" in url

    def test_very_long_values(self):
        """Test handling of very long configuration values."""
        long_host = "x" * 255
        long_user = "u" * 100
        long_password = "p" * 500

        config = DatabaseConfig(host=long_host, user=long_user, password=long_password)

        # Should handle long values without errors
        url = config.database_url
        assert long_host in url
        assert long_user in url
        assert long_password in url

    def test_boolean_environment_variables(self):
        """Test various boolean representations in environment variables."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("", False),
            ("invalid", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"DB_DEBUG": env_value}):
                config = DatabaseConfig()
                assert config.debug == expected, f"Failed for env_value='{env_value}'"

    def test_numeric_environment_variables(self):
        """Test various numeric representations in environment variables."""
        # Valid numeric values
        with patch.dict(os.environ, {"DB_PORT": "5433"}):
            config = DatabaseConfig()
            assert config.port == 5433

        # Invalid numeric values should use defaults
        with patch.dict(os.environ, {"DB_PORT": "invalid"}):
            # Should raise ValueError when creating DatabaseConfig
            with pytest.raises(ValueError):
                DatabaseConfig()


class TestGlobalDatabaseConfig:
    """Test the global db_config instance."""

    def test_global_config_instance(self):
        """Test that global config instance is created."""
        assert db_config is not None
        assert isinstance(db_config, DatabaseConfig)

    def test_global_config_environment_integration(self):
        """Test that global config integrates with environment variables."""
        # The global config should use environment variables
        with patch.dict(os.environ, {"DB_HOST": "global.test.com"}):
            # Need to recreate the global config to pick up env changes
            from database.config import DatabaseConfig

            test_config = DatabaseConfig()

            assert test_config.host == "global.test.com"


class TestDatabaseConfigSecurity:
    """Test security aspects of database configuration."""

    def test_password_not_in_repr(self):
        """Test that password is not exposed in string representation."""
        config = DatabaseConfig(password="secret_password")

        # Convert to string representations
        str_repr = str(config)
        repr_str = repr(config)

        # Password should not appear in either representation
        assert "secret_password" not in str_repr
        assert "secret_password" not in repr_str

    def test_sensitive_fields_handling(self):
        """Test handling of sensitive configuration fields."""
        config = DatabaseConfig(
            password="secret_password", ssl_key="/secret/key/path.pem"
        )

        # Direct access should work
        assert config.password == "secret_password"
        assert config.ssl_key == "/secret/key/path.pem"

        # But they should not leak in string representations
        config_str = str(config)
        assert "secret_password" not in config_str
        assert "/secret/key/path.pem" not in config_str


class TestDatabaseConfigPerformance:
    """Test performance-related configuration aspects."""

    def test_connection_pool_settings(self):
        """Test connection pool configuration."""
        config = DatabaseConfig(
            pool_size=20, max_overflow=50, pool_timeout=60, pool_recycle=7200
        )

        assert config.pool_size == 20
        assert config.max_overflow == 50
        assert config.pool_timeout == 60
        assert config.pool_recycle == 7200

    def test_timeout_settings(self):
        """Test timeout configuration."""
        config = DatabaseConfig(connect_timeout=30, query_timeout=120)

        assert config.connect_timeout == 30
        assert config.query_timeout == 120

    def test_production_vs_development_defaults(self):
        """Test different defaults for production vs development."""
        # Production config
        prod_config = DatabaseConfig(environment="production")
        assert prod_config.is_production is True

        # Development config
        dev_config = DatabaseConfig(environment="development")
        assert dev_config.is_production is False

        # Debug should typically be False in production
        prod_config_debug = DatabaseConfig(environment="production", debug=True)
        assert prod_config_debug.debug is True  # Explicit override works


class TestDatabaseConfigCompatibility:
    """Test compatibility with different database configurations."""

    def test_postgresql_url_format(self):
        """Test PostgreSQL URL format compatibility."""
        config = DatabaseConfig(
            host="postgres.example.com",
            port=5432,
            name="myapp_prod",
            user="myapp_user",
            password="complex_password_123",
        )

        async_url = config.database_url
        sync_url = config.sync_database_url

        # Check async URL format
        assert async_url.startswith("postgresql+asyncpg://")
        assert "myapp_user:complex_password_123" in async_url
        assert "@postgres.example.com:5432/myapp_prod" in async_url

        # Check sync URL format
        assert sync_url.startswith("postgresql://")
        assert "myapp_user:complex_password_123" in sync_url
        assert "@postgres.example.com:5432/myapp_prod" in sync_url

    def test_ssl_mode_values(self):
        """Test different SSL mode values."""
        ssl_modes = [
            "disable",
            "allow",
            "prefer",
            "require",
            "verify-ca",
            "verify-full",
        ]

        for ssl_mode in ssl_modes:
            config = DatabaseConfig(ssl_mode=ssl_mode)
            url = config.database_url

            assert f"sslmode={ssl_mode}" in url

    def test_ipv6_host_support(self):
        """Test IPv6 host support."""
        config = DatabaseConfig(
            host="::1", port=5432, name="test_db", user="test_user"  # IPv6 localhost
        )

        url = config.database_url
        assert "::1" in url


class TestDatabaseConfigValidationEdgeCases:
    """Test edge cases in configuration validation."""

    def test_validation_with_none_values(self):
        """Test validation with None values."""
        # Host as None should fail
        config = DatabaseConfig(host=None)
        with pytest.raises((ValueError, TypeError)):
            config.validate()

    def test_validation_with_whitespace_values(self):
        """Test validation with whitespace-only values."""
        config = DatabaseConfig(host="   ")
        with pytest.raises(ValueError):
            config.validate()

        config = DatabaseConfig(name="\t\n")
        with pytest.raises(ValueError):
            config.validate()

    def test_validation_port_range(self):
        """Test port validation with edge values."""
        # Port 1 should be valid
        config = DatabaseConfig(port=1)
        config.validate()  # Should not raise

        # Port 65535 should be valid
        config = DatabaseConfig(port=65535)
        config.validate()  # Should not raise

        # Port 65536 should be invalid (out of range)
        config = DatabaseConfig(port=65536)
        with pytest.raises(ValueError):
            config.validate()
