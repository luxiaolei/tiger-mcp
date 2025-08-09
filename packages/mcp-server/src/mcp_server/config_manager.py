"""
Configuration manager for Tiger MCP server.

Handles environment configuration loading, validation, and service coordination.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from loguru import logger

# Add paths for shared imports
_SHARED_PATH = Path(__file__).parent.parent.parent.parent / "shared" / "src"
_DATABASE_PATH = Path(__file__).parent.parent.parent.parent / "database" / "src"

if str(_SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(_SHARED_PATH))
if str(_DATABASE_PATH) not in sys.path:
    sys.path.insert(0, str(_DATABASE_PATH))


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    url: str = "sqlite:///tiger_mcp.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class ProcessConfig:
    """Process pool configuration settings."""

    min_workers: int = 2
    max_workers: int = 8
    target_workers: int = 4
    startup_timeout: int = 30
    shutdown_timeout: int = 15
    health_check_interval: int = 60
    worker_restart_threshold: int = 10
    load_balance_strategy: str = "round_robin"


@dataclass
class SecurityConfig:
    """Security configuration settings."""

    enable_token_validation: bool = True
    token_refresh_threshold: int = 300  # 5 minutes
    max_failed_attempts: int = 3
    account_lockout_duration: int = 300  # 5 minutes
    api_rate_limit: int = 100  # requests per minute
    enable_request_logging: bool = True


@dataclass
class ServerConfig:
    """Server configuration settings."""

    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    request_timeout: int = 30
    max_request_size: int = 16 * 1024 * 1024  # 16MB


@dataclass
class TigerConfig:
    """Tiger API configuration settings."""

    sandbox_mode: bool = True
    default_market: str = "US"
    request_timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    enable_websocket: bool = False
    websocket_timeout: int = 10


@dataclass
class TigerMCPConfig:
    """Complete Tiger MCP server configuration."""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    process: ProcessConfig = field(default_factory=ProcessConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    tiger: TigerConfig = field(default_factory=TigerConfig)

    # Runtime settings
    environment: str = "development"
    config_file: Optional[str] = None

    def validate(self) -> List[str]:
        """
        Validate configuration settings.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Process configuration validation
        if self.process.min_workers < 1:
            errors.append("process.min_workers must be at least 1")
        if self.process.max_workers < self.process.min_workers:
            errors.append("process.max_workers must be >= min_workers")
        if (
            self.process.target_workers < self.process.min_workers
            or self.process.target_workers > self.process.max_workers
        ):
            errors.append(
                "process.target_workers must be between min_workers and max_workers"
            )

        # Server configuration validation
        if not (1 <= self.server.port <= 65535):
            errors.append("server.port must be between 1 and 65535")
        if self.server.request_timeout < 1:
            errors.append("server.request_timeout must be at least 1 second")
        if self.server.max_request_size < 1024:
            errors.append("server.max_request_size must be at least 1KB")

        # Security configuration validation
        if self.security.token_refresh_threshold < 60:
            errors.append(
                "security.token_refresh_threshold should be at least 60 seconds"
            )
        if self.security.max_failed_attempts < 1:
            errors.append("security.max_failed_attempts must be at least 1")
        if self.security.api_rate_limit < 1:
            errors.append("security.api_rate_limit must be at least 1")

        # Tiger configuration validation
        if self.tiger.retry_count < 0:
            errors.append("tiger.retry_count cannot be negative")
        if self.tiger.retry_delay < 0:
            errors.append("tiger.retry_delay cannot be negative")
        if self.tiger.request_timeout < 1:
            errors.append("tiger.request_timeout must be at least 1 second")

        return errors


class ConfigManager:
    """
    Configuration manager for Tiger MCP server.

    Handles loading, validation, and management of all configuration settings.
    """

    def __init__(
        self, config_file: Optional[str] = None, environment: Optional[str] = None
    ):
        """
        Initialize configuration manager.

        Args:
            config_file: Optional path to configuration file
            environment: Environment name (development, testing, production)
        """
        self.config_file = config_file
        self.environment = environment or os.getenv(
            "TIGER_MCP_ENVIRONMENT", "development"
        )
        self._config: Optional[TigerMCPConfig] = None
        self._loaded = False

    def load_config(self) -> TigerMCPConfig:
        """
        Load and validate configuration from environment and files.

        Returns:
            Complete configuration object

        Raises:
            ValueError: If configuration is invalid
            FileNotFoundError: If specified config file doesn't exist
        """
        if self._loaded and self._config:
            return self._config

        # Load environment variables from .env file if present
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment variables from {env_file}")

        # Load environment-specific .env file
        env_specific_file = Path(f".env.{self.environment}")
        if env_specific_file.exists():
            load_dotenv(env_specific_file, override=True)
            logger.info(
                f"Loaded environment-specific variables from {env_specific_file}"
            )

        # Create configuration from environment variables
        config = TigerMCPConfig(
            environment=self.environment,
            config_file=self.config_file,
            database=self._load_database_config(),
            process=self._load_process_config(),
            security=self._load_security_config(),
            server=self._load_server_config(),
            tiger=self._load_tiger_config(),
        )

        # Validate configuration
        errors = config.validate()
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        self._config = config
        self._loaded = True

        logger.info(
            f"Configuration loaded successfully for environment: {self.environment}"
        )
        return config

    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment."""
        return DatabaseConfig(
            url=os.getenv("TIGER_MCP_DATABASE_URL", "sqlite:///tiger_mcp.db"),
            echo=os.getenv("TIGER_MCP_DATABASE_ECHO", "false").lower() == "true",
            pool_size=int(os.getenv("TIGER_MCP_DATABASE_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("TIGER_MCP_DATABASE_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("TIGER_MCP_DATABASE_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("TIGER_MCP_DATABASE_POOL_RECYCLE", "3600")),
        )

    def _load_process_config(self) -> ProcessConfig:
        """Load process pool configuration from environment."""
        return ProcessConfig(
            min_workers=int(os.getenv("TIGER_MCP_PROCESS_MIN_WORKERS", "2")),
            max_workers=int(os.getenv("TIGER_MCP_PROCESS_MAX_WORKERS", "8")),
            target_workers=int(os.getenv("TIGER_MCP_PROCESS_TARGET_WORKERS", "4")),
            startup_timeout=int(os.getenv("TIGER_MCP_PROCESS_STARTUP_TIMEOUT", "30")),
            shutdown_timeout=int(os.getenv("TIGER_MCP_PROCESS_SHUTDOWN_TIMEOUT", "15")),
            health_check_interval=int(
                os.getenv("TIGER_MCP_PROCESS_HEALTH_CHECK_INTERVAL", "60")
            ),
            worker_restart_threshold=int(
                os.getenv("TIGER_MCP_PROCESS_WORKER_RESTART_THRESHOLD", "10")
            ),
            load_balance_strategy=os.getenv(
                "TIGER_MCP_PROCESS_LOAD_BALANCE_STRATEGY", "round_robin"
            ),
        )

    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration from environment."""
        return SecurityConfig(
            enable_token_validation=os.getenv(
                "TIGER_MCP_SECURITY_ENABLE_TOKEN_VALIDATION", "true"
            ).lower()
            == "true",
            token_refresh_threshold=int(
                os.getenv("TIGER_MCP_SECURITY_TOKEN_REFRESH_THRESHOLD", "300")
            ),
            max_failed_attempts=int(
                os.getenv("TIGER_MCP_SECURITY_MAX_FAILED_ATTEMPTS", "3")
            ),
            account_lockout_duration=int(
                os.getenv("TIGER_MCP_SECURITY_ACCOUNT_LOCKOUT_DURATION", "300")
            ),
            api_rate_limit=int(os.getenv("TIGER_MCP_SECURITY_API_RATE_LIMIT", "100")),
            enable_request_logging=os.getenv(
                "TIGER_MCP_SECURITY_ENABLE_REQUEST_LOGGING", "true"
            ).lower()
            == "true",
        )

    def _load_server_config(self) -> ServerConfig:
        """Load server configuration from environment."""
        cors_origins = os.getenv("TIGER_MCP_SERVER_CORS_ORIGINS", "*").split(",")
        cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

        return ServerConfig(
            host=os.getenv("TIGER_MCP_SERVER_HOST", "localhost"),
            port=int(os.getenv("TIGER_MCP_SERVER_PORT", "8000")),
            debug=os.getenv("TIGER_MCP_SERVER_DEBUG", "false").lower() == "true",
            log_level=os.getenv("TIGER_MCP_SERVER_LOG_LEVEL", "INFO"),
            enable_cors=os.getenv("TIGER_MCP_SERVER_ENABLE_CORS", "true").lower()
            == "true",
            cors_origins=cors_origins,
            request_timeout=int(os.getenv("TIGER_MCP_SERVER_REQUEST_TIMEOUT", "30")),
            max_request_size=int(
                os.getenv("TIGER_MCP_SERVER_MAX_REQUEST_SIZE", str(16 * 1024 * 1024))
            ),
        )

    def _load_tiger_config(self) -> TigerConfig:
        """Load Tiger API configuration from environment."""
        return TigerConfig(
            sandbox_mode=os.getenv("TIGER_SANDBOX_MODE", "true").lower() == "true",
            default_market=os.getenv("TIGER_DEFAULT_MARKET", "US"),
            request_timeout=int(os.getenv("TIGER_REQUEST_TIMEOUT", "30")),
            retry_count=int(os.getenv("TIGER_RETRY_COUNT", "3")),
            retry_delay=float(os.getenv("TIGER_RETRY_DELAY", "1.0")),
            enable_websocket=os.getenv("TIGER_ENABLE_WEBSOCKET", "false").lower()
            == "true",
            websocket_timeout=int(os.getenv("TIGER_WEBSOCKET_TIMEOUT", "10")),
        )

    def get_config(self) -> TigerMCPConfig:
        """
        Get current configuration.

        Returns:
            Configuration object (loads if not already loaded)
        """
        if not self._loaded:
            return self.load_config()
        return self._config

    def reload_config(self) -> TigerMCPConfig:
        """
        Reload configuration from environment.

        Returns:
            Reloaded configuration object
        """
        self._loaded = False
        self._config = None
        return self.load_config()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(
    config_file: Optional[str] = None, environment: Optional[str] = None
) -> ConfigManager:
    """
    Get global configuration manager instance.

    Args:
        config_file: Optional configuration file path
        environment: Environment name

    Returns:
        Configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(
            config_file=config_file, environment=environment
        )
    return _config_manager


def get_config() -> TigerMCPConfig:
    """
    Get current configuration.

    Returns:
        Configuration object
    """
    return get_config_manager().get_config()
