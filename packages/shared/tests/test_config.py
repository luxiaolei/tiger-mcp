"""
Comprehensive unit tests for configuration module.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from shared.config import (
    AppConfig,
    DatabaseConfig,
    KeyManager,
    LoggingConfig,
    SecurityConfig,
    TigerAPIConfig,
    generate_env_template,
    get_config,
    get_database_config,
    get_logging_config,
    get_security_config,
    get_tiger_api_config,
    load_environment_config,
    setup_logging,
    validate_security_config,
)


class TestSecurityConfig:
    """Tests for SecurityConfig class."""

    def test_security_config_defaults(self):
        """Test SecurityConfig with default values."""
        config = SecurityConfig()

        assert config.pbkdf2_iterations == 100000
        assert config.encryption_key_size == 32
        assert config.jwt_algorithm == "HS256"
        assert config.password_hash_algorithm == "argon2"
        assert config.environment == "development"
        assert config.debug is False

    def test_security_config_from_env(self):
        """Test SecurityConfig loading from environment variables."""
        env_vars = {
            "PBKDF2_ITERATIONS": "150000",
            "JWT_ACCESS_TOKEN_EXPIRE": "7200",
            "ENVIRONMENT": "production",
            "DEBUG": "true",
        }

        with patch.dict(os.environ, env_vars):
            config = SecurityConfig()

            assert config.pbkdf2_iterations == 150000
            assert config.jwt_access_token_expire == 7200
            assert config.environment == "production"
            assert config.debug is True

    def test_security_config_pbkdf2_validation(self):
        """Test PBKDF2 iterations validation."""
        with pytest.raises(
            ValidationError, match="PBKDF2 iterations must be at least 10,000"
        ):
            SecurityConfig(pbkdf2_iterations=5000)

        # Valid value should work
        config = SecurityConfig(pbkdf2_iterations=50000)
        assert config.pbkdf2_iterations == 50000

    def test_security_config_key_size_validation(self):
        """Test encryption key size validation."""
        with pytest.raises(
            ValidationError, match="Encryption key size must be 16, 24, or 32 bytes"
        ):
            SecurityConfig(encryption_key_size=15)

        # Valid sizes should work
        for size in [16, 24, 32]:
            config = SecurityConfig(encryption_key_size=size)
            assert config.encryption_key_size == size

    def test_security_config_algorithm_validation(self):
        """Test password algorithm validation."""
        with pytest.raises(
            ValidationError, match="Password algorithm must be 'argon2' or 'bcrypt'"
        ):
            SecurityConfig(password_hash_algorithm="md5")

        # Valid algorithms should work
        for algorithm in ["argon2", "bcrypt"]:
            config = SecurityConfig(password_hash_algorithm=algorithm)
            assert config.password_hash_algorithm == algorithm

    def test_security_config_environment_validation(self):
        """Test environment validation."""
        with pytest.raises(
            ValidationError,
            match="Environment must be development, staging, or production",
        ):
            SecurityConfig(environment="invalid")

        # Valid environments should work
        for env in ["development", "staging", "production"]:
            config = SecurityConfig(environment=env)
            assert config.environment == env

    def test_security_config_case_insensitive(self):
        """Test case-insensitive environment variable loading."""
        env_vars = {"pbkdf2_iterations": "120000", "JWT_ALGORITHM": "hs256"}

        with patch.dict(os.environ, env_vars):
            config = SecurityConfig()
            assert config.pbkdf2_iterations == 120000


class TestDatabaseConfig:
    """Tests for DatabaseConfig class."""

    def test_database_config_defaults(self):
        """Test DatabaseConfig with default values."""
        config = DatabaseConfig()

        assert config.database_host == "localhost"
        assert config.database_port == 5432
        assert config.database_name == "tiger_mcp"
        assert config.database_user == "postgres"
        assert config.database_password == ""
        assert config.database_pool_size == 5
        assert config.database_ssl_mode == "prefer"

    def test_database_config_from_env(self):
        """Test DatabaseConfig loading from environment."""
        env_vars = {
            "DATABASE_HOST": "db.example.com",
            "DATABASE_PORT": "5433",
            "DATABASE_NAME": "test_db",
            "DATABASE_POOL_SIZE": "10",
        }

        with patch.dict(os.environ, env_vars):
            config = DatabaseConfig()

            assert config.database_host == "db.example.com"
            assert config.database_port == 5433
            assert config.database_name == "test_db"
            assert config.database_pool_size == 10

    def test_database_connection_string_from_url(self):
        """Test connection string when DATABASE_URL is provided."""
        url = "postgresql://user:pass@host:5432/dbname"
        config = DatabaseConfig(database_url=url)

        assert config.connection_string == url

    def test_database_connection_string_from_components(self):
        """Test connection string built from components."""
        config = DatabaseConfig(
            database_host="testhost",
            database_port=5433,
            database_name="testdb",
            database_user="testuser",
            database_password="testpass",
        )

        expected = "postgresql://testuser:testpass@testhost:5433/testdb"
        assert config.connection_string == expected

    def test_database_connection_string_empty_password(self):
        """Test connection string with empty password."""
        config = DatabaseConfig(
            database_host="testhost",
            database_name="testdb",
            database_user="testuser",
            database_password="",
        )

        expected = "postgresql://testuser:@testhost:5432/testdb"
        assert config.connection_string == expected


class TestTigerAPIConfig:
    """Tests for TigerAPIConfig class."""

    def test_tiger_api_config_defaults(self):
        """Test TigerAPIConfig with default values."""
        config = TigerAPIConfig()

        assert config.tiger_api_timeout == 30
        assert config.tiger_api_retries == 3
        assert config.tiger_api_retry_delay == 1.0
        assert "sandbox" in config.tiger_sandbox_url
        assert "tigerbrokers.com" in config.tiger_production_url

    def test_tiger_api_config_from_env(self):
        """Test TigerAPIConfig loading from environment."""
        env_vars = {
            "TIGER_API_TIMEOUT": "60",
            "TIGER_API_RETRIES": "5",
            "TIGER_RATE_LIMIT_SECOND": "5",
        }

        with patch.dict(os.environ, env_vars):
            config = TigerAPIConfig()

            assert config.tiger_api_timeout == 60
            assert config.tiger_api_retries == 5
            assert config.tiger_rate_limit_per_second == 5


class TestLoggingConfig:
    """Tests for LoggingConfig class."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig with default values."""
        config = LoggingConfig()

        assert config.log_level == "INFO"
        assert config.log_format == "detailed"
        assert config.log_file_enabled is True
        assert config.log_file_path == "logs/tiger-mcp.log"
        assert config.log_security_events is True

    def test_logging_config_from_env(self):
        """Test LoggingConfig loading from environment."""
        env_vars = {
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "json",
            "LOG_FILE_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars):
            config = LoggingConfig()

            assert config.log_level == "DEBUG"
            assert config.log_format == "json"
            assert config.log_file_enabled is False

    def test_logging_config_log_level_validation(self):
        """Test log level validation."""
        with pytest.raises(ValidationError, match="Log level must be one of"):
            LoggingConfig(log_level="INVALID")

        # Valid levels should work and be uppercased
        for level in ["debug", "info", "warning", "error", "critical"]:
            config = LoggingConfig(log_level=level)
            assert config.log_level == level.upper()

    def test_logging_config_format_validation(self):
        """Test log format validation."""
        with pytest.raises(
            ValidationError, match="Log format must be simple, detailed, or json"
        ):
            LoggingConfig(log_format="invalid")

        # Valid formats should work
        for format_type in ["simple", "detailed", "json"]:
            config = LoggingConfig(log_format=format_type)
            assert config.log_format == format_type


class TestAppConfig:
    """Tests for AppConfig class."""

    def test_app_config_defaults(self):
        """Test AppConfig with default values."""
        config = AppConfig()

        assert config.environment == "development"
        assert config.debug is False
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.tiger_api, TigerAPIConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_app_config_properties(self):
        """Test AppConfig convenience properties."""
        dev_config = AppConfig(environment="development")
        prod_config = AppConfig(environment="production")

        assert dev_config.is_development is True
        assert dev_config.is_production is False

        assert prod_config.is_development is False
        assert prod_config.is_production is True

    @patch("shared.config.load_dotenv")
    @patch("pathlib.Path.exists")
    def test_app_config_load_env_file(self, mock_exists, mock_load_dotenv):
        """Test loading environment file."""
        mock_exists.return_value = True

        AppConfig()

        mock_load_dotenv.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_app_config_no_env_file(self, mock_exists):
        """Test when no environment file exists."""
        mock_exists.return_value = False

        # Should not raise exception
        config = AppConfig()
        assert config is not None


class TestKeyManager:
    """Tests for KeyManager class."""

    def test_key_manager_initialization(self):
        """Test KeyManager initialization."""
        manager = KeyManager()
        assert isinstance(manager.config, SecurityConfig)

        custom_config = SecurityConfig(environment="production")
        manager_with_config = KeyManager(config=custom_config)
        assert manager_with_config.config.environment == "production"

    def test_generate_master_key(self):
        """Test master key generation."""
        key = KeyManager.generate_master_key()

        assert isinstance(key, str)
        assert len(key) == 64  # 32 bytes in hex = 64 chars

        # Should be valid hex
        bytes.fromhex(key)

        # Multiple calls should generate different keys
        key2 = KeyManager.generate_master_key()
        assert key != key2

    def test_generate_jwt_secret(self):
        """Test JWT secret generation."""
        secret = KeyManager.generate_jwt_secret()

        assert isinstance(secret, str)
        assert len(secret) >= 32

        # Multiple calls should generate different secrets
        secret2 = KeyManager.generate_jwt_secret()
        assert secret != secret2

    def test_generate_api_key_secret(self):
        """Test API key secret generation."""
        secret = KeyManager.generate_api_key_secret()

        assert isinstance(secret, str)
        assert len(secret) >= 32

        # Multiple calls should generate different secrets
        secret2 = KeyManager.generate_api_key_secret()
        assert secret != secret2

    def test_validate_master_key(self):
        """Test master key validation."""
        manager = KeyManager()

        # Valid 64 character hex string (32 bytes)
        valid_key = "a" * 64
        assert manager.validate_master_key(valid_key) is True

        # Invalid length
        assert manager.validate_master_key("a" * 63) is False
        assert manager.validate_master_key("a" * 65) is False

        # Invalid hex characters
        assert manager.validate_master_key("g" * 64) is False

        # Empty string
        assert manager.validate_master_key("") is False

    def test_get_environment_keys(self):
        """Test getting environment keys."""
        manager = KeyManager()

        env_vars = {
            "ENCRYPTION_MASTER_KEY": "test_master_key",
            "JWT_SECRET": "test_jwt_secret",
            "DATABASE_PASSWORD": "test_db_pass",
        }

        with patch.dict(os.environ, env_vars):
            keys = manager.get_environment_keys()

            assert keys["ENCRYPTION_MASTER_KEY"] == "test_master_key"
            assert keys["JWT_SECRET"] == "test_jwt_secret"
            assert keys["DATABASE_PASSWORD"] == "test_db_pass"

    def test_validate_environment_security_missing_keys(self):
        """Test environment security validation with missing keys."""
        manager = KeyManager()

        # Clear environment
        with patch.dict(os.environ, {}, clear=True):
            issues = manager.validate_environment_security()

            assert len(issues) >= 2  # At least missing master key and JWT secret
            assert any("ENCRYPTION_MASTER_KEY" in issue for issue in issues)
            assert any("JWT_SECRET" in issue for issue in issues)

    def test_validate_environment_security_invalid_keys(self):
        """Test environment security validation with invalid keys."""
        manager = KeyManager()

        env_vars = {
            "ENCRYPTION_MASTER_KEY": "invalid_key",  # Not 64 hex chars
            "JWT_SECRET": "short",  # Too short
        }

        with patch.dict(os.environ, env_vars):
            issues = manager.validate_environment_security()

            assert len(issues) >= 2
            assert any("Invalid ENCRYPTION_MASTER_KEY" in issue for issue in issues)
            assert any("JWT_SECRET is too short" in issue for issue in issues)

    def test_validate_environment_security_production(self):
        """Test environment security validation in production."""
        config = SecurityConfig(environment="production")
        manager = KeyManager(config=config)

        env_vars = {
            "ENCRYPTION_MASTER_KEY": "a" * 64,
            "JWT_SECRET": "a" * 32,
            # Missing database credentials
        }

        with patch.dict(os.environ, env_vars):
            issues = manager.validate_environment_security()

            assert any("database credentials" in issue for issue in issues)

    def test_generate_environment_template(self):
        """Test environment template generation."""
        manager = KeyManager()

        template = manager.generate_environment_template()

        assert "ENCRYPTION_MASTER_KEY=" in template
        assert "JWT_SECRET=" in template
        assert "DATABASE_PASSWORD=" in template
        assert "ENVIRONMENT=" in template
        assert "# Tiger MCP Security Configuration" in template

        # Should contain generated values
        lines = template.split("\n")
        master_key_line = next(
            line for line in lines if line.startswith("ENCRYPTION_MASTER_KEY=")
        )
        assert len(master_key_line.split("=")[1]) == 64  # 32 bytes hex


class TestGlobalFunctions:
    """Tests for global configuration functions."""

    def test_get_config_singleton(self):
        """Test get_config returns singleton."""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_get_sub_configs(self):
        """Test getting sub-configuration objects."""
        security_config = get_security_config()
        database_config = get_database_config()
        tiger_config = get_tiger_api_config()
        logging_config = get_logging_config()

        assert isinstance(security_config, SecurityConfig)
        assert isinstance(database_config, DatabaseConfig)
        assert isinstance(tiger_config, TigerAPIConfig)
        assert isinstance(logging_config, LoggingConfig)

    def test_load_environment_config(self):
        """Test loading configuration with custom env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("ENVIRONMENT=staging\nDEBUG=true\n")
            f.flush()

            try:
                config = load_environment_config(f.name)
                assert config.environment == "staging"
                assert config.debug is True
            finally:
                os.unlink(f.name)

    def test_validate_security_config_function(self):
        """Test validate_security_config convenience function."""
        with patch.dict(os.environ, {}, clear=True):
            issues = validate_security_config()

            assert isinstance(issues, list)
            assert len(issues) >= 2  # Missing keys

    def test_generate_env_template_function(self):
        """Test generate_env_template convenience function."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            try:
                generate_env_template(f.name)

                # Check file was created and has content
                with open(f.name, "r") as read_f:
                    content = read_f.read()
                    assert "ENCRYPTION_MASTER_KEY=" in content
                    assert "JWT_SECRET=" in content
            finally:
                os.unlink(f.name)


class TestSetupLogging:
    """Tests for logging setup functionality."""

    @patch("shared.config.logger")
    def test_setup_logging_default(self, mock_logger):
        """Test setup logging with default configuration."""
        setup_logging()

        # Verify logger methods were called
        mock_logger.remove.assert_called_once()
        assert mock_logger.add.call_count >= 1  # Console + maybe file

    @patch("shared.config.logger")
    def test_setup_logging_custom_config(self, mock_logger):
        """Test setup logging with custom configuration."""
        config = LoggingConfig(
            log_level="DEBUG", log_format="simple", log_file_enabled=False
        )

        setup_logging(config)

        mock_logger.remove.assert_called_once()
        assert mock_logger.add.call_count >= 1

    @patch("shared.config.logger")
    @patch("pathlib.Path.mkdir")
    def test_setup_logging_file_enabled(self, mock_mkdir, mock_logger):
        """Test setup logging with file logging enabled."""
        config = LoggingConfig(log_file_enabled=True, log_file_path="test/logs/app.log")

        setup_logging(config)

        # Should create log directory
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Should add both console and file handlers
        assert mock_logger.add.call_count == 2

    @patch("shared.config.logger")
    def test_setup_logging_different_formats(self, mock_logger):
        """Test setup logging with different formats."""
        formats = ["simple", "detailed", "json"]

        for log_format in formats:
            mock_logger.reset_mock()
            config = LoggingConfig(log_format=log_format)

            setup_logging(config)

            # Should call add at least once for each format
            assert mock_logger.add.call_count >= 1


class TestConfigurationIntegration:
    """Integration tests for configuration system."""

    def test_full_config_from_env(self):
        """Test loading full configuration from environment variables."""
        env_vars = {
            "ENVIRONMENT": "staging",
            "DEBUG": "true",
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "PBKDF2_ITERATIONS": "150000",
            "DATABASE_HOST": "db.staging.com",
            "DATABASE_PORT": "5433",
            "TIGER_API_TIMEOUT": "45",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars):
            config = AppConfig()

            # App level
            assert config.environment == "staging"
            assert config.debug is True
            assert config.host == "127.0.0.1"
            assert config.port == 9000

            # Security
            assert config.security.pbkdf2_iterations == 150000
            assert config.security.environment == "staging"

            # Database
            assert config.database.database_host == "db.staging.com"
            assert config.database.database_port == 5433

            # Tiger API
            assert config.tiger_api.tiger_api_timeout == 45

            # Logging
            assert config.logging.log_level == "DEBUG"

    def test_config_validation_chain(self):
        """Test configuration validation across all config classes."""
        # Valid configuration
        valid_env = {
            "ENVIRONMENT": "production",
            "PBKDF2_ITERATIONS": "100000",
            "ENCRYPTION_KEY_SIZE": "32",
            "PASSWORD_HASH_ALGORITHM": "argon2",
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": "json",
        }

        with patch.dict(os.environ, valid_env):
            config = AppConfig()  # Should not raise

            assert config.security.environment == "production"
            assert config.logging.log_level == "INFO"

    def test_config_with_dotenv_file(self):
        """Test configuration loading with .env file."""
        env_content = """
ENVIRONMENT=staging
DEBUG=true
PBKDF2_ITERATIONS=150000
DATABASE_HOST=staging.db.com
LOG_LEVEL=DEBUG
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                # Change to directory containing the env file
                original_cwd = os.getcwd()
                os.chdir(os.path.dirname(f.name))
                os.rename(f.name, ".env")

                config = AppConfig()

                assert config.environment == "staging"
                assert config.debug is True
                assert config.security.pbkdf2_iterations == 150000
                assert config.database.database_host == "staging.db.com"
                assert config.logging.log_level == "DEBUG"

            finally:
                os.chdir(original_cwd)
                try:
                    os.unlink(".env")
                except FileNotFoundError:
                    pass

    def test_config_precedence(self):
        """Test environment variable precedence over defaults."""
        # Set conflicting values
        env_vars = {
            "ENVIRONMENT": "production",  # Override default
            "DEBUG": "true",  # Override default
            "PORT": "9000",  # Override default
        }

        with patch.dict(os.environ, env_vars):
            config = AppConfig()

            # Environment variables should take precedence
            assert config.environment == "production"
            assert config.debug is True
            assert config.port == 9000

            # Defaults should still work for unset variables
            assert config.host == "0.0.0.0"  # Default value

    def test_security_configuration_comprehensive(self):
        """Test comprehensive security configuration scenarios."""
        production_manager = KeyManager(SecurityConfig(environment="production"))
        dev_manager = KeyManager(SecurityConfig(environment="development"))

        # Production should have stricter validation
        with patch.dict(os.environ, {}, clear=True):
            prod_issues = production_manager.validate_environment_security()
            dev_issues = dev_manager.validate_environment_security()

            # Production should find more issues (database credentials)
            assert len(prod_issues) >= len(dev_issues)

        # Valid production setup
        valid_prod_env = {
            "ENCRYPTION_MASTER_KEY": "a" * 64,
            "JWT_SECRET": "a" * 32,
            "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        }

        with patch.dict(os.environ, valid_prod_env):
            prod_issues = production_manager.validate_environment_security()
            assert len(prod_issues) == 0  # Should be clean
