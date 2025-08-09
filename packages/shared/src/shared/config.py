"""
Configuration management for Tiger MCP system.

Provides environment variable management, security configuration defaults,
and key management utilities with validation and type conversion.
"""

import os
import secrets
import time
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from loguru import logger
from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings


class ConfigError(Exception):
    """Base exception for configuration errors."""


class SecurityConfig(BaseSettings):
    """Security configuration with environment variable support."""

    # Encryption settings
    pbkdf2_iterations: int = Field(default=100000, env="PBKDF2_ITERATIONS")
    encryption_key_size: int = Field(default=32, env="ENCRYPTION_KEY_SIZE")  # 256 bits

    # JWT settings
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire: int = Field(
        default=3600, env="JWT_ACCESS_TOKEN_EXPIRE"
    )  # 1 hour
    jwt_refresh_token_expire: int = Field(
        default=604800, env="JWT_REFRESH_TOKEN_EXPIRE"
    )  # 7 days

    # Password hashing settings
    password_hash_algorithm: str = Field(
        default="argon2", env="PASSWORD_HASH_ALGORITHM"
    )
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")
    argon2_time_cost: int = Field(default=3, env="ARGON2_TIME_COST")
    argon2_memory_cost: int = Field(default=65536, env="ARGON2_MEMORY_COST")  # 64MB
    argon2_parallelism: int = Field(default=2, env="ARGON2_PARALLELISM")

    # Rate limiting defaults
    default_rate_limit_per_hour: int = Field(
        default=1000, env="DEFAULT_RATE_LIMIT_HOUR"
    )
    default_rate_limit_per_day: int = Field(default=10000, env="DEFAULT_RATE_LIMIT_DAY")
    rate_limit_window_size: int = Field(
        default=3600, env="RATE_LIMIT_WINDOW_SIZE"
    )  # 1 hour

    # API key settings
    api_key_prefix: str = Field(default="tk", env="API_KEY_PREFIX")
    api_key_length: int = Field(default=32, env="API_KEY_LENGTH")
    api_key_prefix_display_length: int = Field(
        default=8, env="API_KEY_PREFIX_DISPLAY_LENGTH"
    )

    # Security audit settings
    audit_retention_days: int = Field(default=90, env="AUDIT_RETENTION_DAYS")
    audit_critical_alert: bool = Field(default=True, env="AUDIT_CRITICAL_ALERT")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("pbkdf2_iterations")
    @classmethod
    def validate_pbkdf2_iterations(cls, v):
        """Validate PBKDF2 iterations."""
        if v < 10000:
            raise ValueError("PBKDF2 iterations must be at least 10,000")
        return v

    @field_validator("encryption_key_size")
    @classmethod
    def validate_encryption_key_size(cls, v):
        """Validate encryption key size."""
        if v not in [16, 24, 32]:  # 128, 192, 256 bits
            raise ValueError("Encryption key size must be 16, 24, or 32 bytes")
        return v

    @field_validator("password_hash_algorithm")
    @classmethod
    def validate_password_algorithm(cls, v):
        """Validate password hashing algorithm."""
        if v not in ["argon2", "bcrypt"]:
            raise ValueError("Password algorithm must be 'argon2' or 'bcrypt'")
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be development, staging, or production")
        return v


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    # Connection settings
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_host: str = Field(default="localhost", env="DATABASE_HOST")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(default="tiger_mcp", env="DATABASE_NAME")
    database_user: str = Field(default="postgres", env="DATABASE_USER")
    database_password: str = Field(default="", env="DATABASE_PASSWORD")

    # Connection pool settings
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")

    # SSL settings
    database_ssl_mode: str = Field(default="prefer", env="DATABASE_SSL_MODE")
    database_ssl_cert: Optional[str] = Field(default=None, env="DATABASE_SSL_CERT")
    database_ssl_key: Optional[str] = Field(default=None, env="DATABASE_SSL_KEY")
    database_ssl_ca: Optional[str] = Field(default=None, env="DATABASE_SSL_CA")

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    @property
    def connection_string(self) -> str:
        """Get database connection string."""
        if self.database_url:
            return self.database_url

        return (
            f"postgresql://{self.database_user}:{self.database_password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )


class TigerAPIConfig(BaseSettings):
    """Tiger API configuration."""

    # Default API settings
    tiger_api_timeout: int = Field(default=30, env="TIGER_API_TIMEOUT")
    tiger_api_retries: int = Field(default=3, env="TIGER_API_RETRIES")
    tiger_api_retry_delay: float = Field(default=1.0, env="TIGER_API_RETRY_DELAY")

    # Environment settings
    tiger_sandbox_url: str = Field(
        default="https://openapi-sandbox.tigerbrokers.com", env="TIGER_SANDBOX_URL"
    )
    tiger_production_url: str = Field(
        default="https://openapi.tigerbrokers.com", env="TIGER_PRODUCTION_URL"
    )

    # Rate limiting
    tiger_rate_limit_per_second: int = Field(default=10, env="TIGER_RATE_LIMIT_SECOND")
    tiger_rate_limit_per_minute: int = Field(default=600, env="TIGER_RATE_LIMIT_MINUTE")

    model_config = ConfigDict(env_file=".env", case_sensitive=False)


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    # Log level settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="detailed", env="LOG_FORMAT"
    )  # simple, detailed, json

    # File logging settings
    log_file_enabled: bool = Field(default=True, env="LOG_FILE_ENABLED")
    log_file_path: str = Field(default="logs/tiger-mcp.log", env="LOG_FILE_PATH")
    log_file_rotation: str = Field(default="100 MB", env="LOG_FILE_ROTATION")
    log_file_retention: str = Field(default="30 days", env="LOG_FILE_RETENTION")

    # Security logging
    log_security_events: bool = Field(default=True, env="LOG_SECURITY_EVENTS")
    log_audit_trail: bool = Field(default=True, env="LOG_AUDIT_TRAIL")

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        if v not in ["simple", "detailed", "json"]:
            raise ValueError("Log format must be simple, detailed, or json")
        return v


class AppConfig(BaseSettings):
    """Application configuration combining all sub-configs."""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # Service settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # Sub-configurations
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    tiger_api: TigerAPIConfig = Field(default_factory=TigerAPIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    def __init__(self, **kwargs):
        """Initialize app config and load environment variables."""
        # Load environment file if it exists
        self._load_environment_file()
        super().__init__(**kwargs)

    def _load_environment_file(self) -> None:
        """Load environment variables from .env file."""
        # Look for .env file in current directory and parent directories
        current_dir = Path.cwd()
        for path in [current_dir] + list(current_dir.parents):
            env_file = path / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                logger.info(f"Loaded environment from: {env_file}")
                return

        logger.debug("No .env file found")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


class KeyManager:
    """Utility class for managing encryption keys and secrets."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize key manager."""
        self.config = config or SecurityConfig()

    @staticmethod
    def generate_master_key() -> str:
        """Generate a new master encryption key."""
        key_bytes = secrets.token_bytes(32)  # 256 bits
        return key_bytes.hex()

    @staticmethod
    def generate_jwt_secret() -> str:
        """Generate a new JWT secret."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_api_key_secret() -> str:
        """Generate a secure API key."""
        return secrets.token_urlsafe(32)

    def validate_master_key(self, key: str) -> bool:
        """Validate master key format."""
        try:
            key_bytes = bytes.fromhex(key)
            return len(key_bytes) == 32  # 256 bits
        except ValueError:
            return False

    def get_environment_keys(self) -> Dict[str, Optional[str]]:
        """Get all security-related environment variables."""
        return {
            "ENCRYPTION_MASTER_KEY": os.getenv("ENCRYPTION_MASTER_KEY"),
            "JWT_SECRET": os.getenv("JWT_SECRET"),
            "DATABASE_PASSWORD": os.getenv("DATABASE_PASSWORD"),
            "DATABASE_URL": os.getenv("DATABASE_URL"),
        }

    def validate_environment_security(self) -> List[str]:
        """Validate security of environment configuration."""
        issues = []

        # Check for missing critical keys
        env_keys = self.get_environment_keys()

        if not env_keys["ENCRYPTION_MASTER_KEY"]:
            issues.append("Missing ENCRYPTION_MASTER_KEY environment variable")
        elif not self.validate_master_key(env_keys["ENCRYPTION_MASTER_KEY"]):
            issues.append(
                "Invalid ENCRYPTION_MASTER_KEY format (must be 64 hex characters)"
            )

        if not env_keys["JWT_SECRET"]:
            issues.append("Missing JWT_SECRET environment variable")
        elif len(env_keys["JWT_SECRET"]) < 32:
            issues.append("JWT_SECRET is too short (minimum 32 characters)")

        if self.config.environment == "production":
            if not env_keys["DATABASE_URL"] and not env_keys["DATABASE_PASSWORD"]:
                issues.append("Missing database credentials for production")

        return issues

    def generate_environment_template(self) -> str:
        """Generate a template .env file with secure defaults."""
        template = f"""# Tiger MCP Security Configuration
# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}

# Environment
ENVIRONMENT=development
DEBUG=false

# Encryption
ENCRYPTION_MASTER_KEY={self.generate_master_key()}

# JWT
JWT_SECRET={self.generate_jwt_secret()}
JWT_ACCESS_TOKEN_EXPIRE=3600
JWT_REFRESH_TOKEN_EXPIRE=604800

# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=tiger_mcp
DATABASE_USER=postgres
DATABASE_PASSWORD={self.generate_api_key_secret()}
# DATABASE_URL=postgresql://user:password@localhost:5432/tiger_mcp

# Security Settings
PBKDF2_ITERATIONS=100000
PASSWORD_HASH_ALGORITHM=argon2
DEFAULT_RATE_LIMIT_HOUR=1000
DEFAULT_RATE_LIMIT_DAY=10000

# Tiger API
TIGER_API_TIMEOUT=30
TIGER_API_RETRIES=3

# Logging
LOG_LEVEL=INFO
LOG_FILE_ENABLED=true
LOG_SECURITY_EVENTS=true
"""
        return template


# Global configuration instance
_app_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global application configuration instance."""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig()
    return _app_config


def get_security_config() -> SecurityConfig:
    """Get security configuration."""
    return get_config().security


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return get_config().database


def get_tiger_api_config() -> TigerAPIConfig:
    """Get Tiger API configuration."""
    return get_config().tiger_api


def get_logging_config() -> LoggingConfig:
    """Get logging configuration."""
    return get_config().logging


# Convenience functions


def load_environment_config(env_file: Optional[str] = None) -> AppConfig:
    """Load configuration with optional custom .env file."""
    if env_file:
        load_dotenv(env_file)
    return AppConfig()


def validate_security_config() -> List[str]:
    """Validate security configuration and return list of issues."""
    key_manager = KeyManager()
    return key_manager.validate_environment_security()


def generate_env_template(output_file: str = ".env.template") -> None:
    """Generate environment template file."""
    key_manager = KeyManager()
    template = key_manager.generate_environment_template()

    with open(output_file, "w") as f:
        f.write(template)

    logger.info(f"Environment template generated: {output_file}")


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """Setup logging based on configuration."""
    config = config or get_logging_config()

    # Remove default logger
    logger.remove()

    # Console logging
    if config.log_format == "json":
        log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    elif config.log_format == "simple":
        log_format = "{time:HH:mm:ss} | {level: <8} | {message}"
    else:  # detailed
        log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    logger.add(
        sink=lambda msg: print(msg, end=""),
        format=log_format,
        level=config.log_level,
        colorize=True,
    )

    # File logging
    if config.log_file_enabled:
        # Ensure log directory exists
        log_path = Path(config.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            sink=config.log_file_path,
            format=log_format,
            level=config.log_level,
            rotation=config.log_file_rotation,
            retention=config.log_file_retention,
            compression="zip",
        )

    logger.info(
        f"Logging configured: level={config.log_level}, format={config.log_format}"
    )
