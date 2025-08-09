"""
Database configuration management.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    # Database connection settings
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "tiger_mcp")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")

    # Connection pool settings
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))

    # Connection retry settings
    connect_timeout: int = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
    query_timeout: int = int(os.getenv("DB_QUERY_TIMEOUT", "30"))

    # SSL settings
    ssl_mode: Optional[str] = os.getenv("DB_SSL_MODE")  # prefer, require, disable
    ssl_cert: Optional[str] = os.getenv("DB_SSL_CERT")
    ssl_key: Optional[str] = os.getenv("DB_SSL_KEY")
    ssl_ca: Optional[str] = os.getenv("DB_SSL_CA")

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DB_DEBUG", "false").lower() == "true"

    @property
    def database_url(self) -> str:
        """Generate PostgreSQL database URL."""
        url = f"postgresql+asyncpg://{self.user}"
        if self.password:
            url += f":{self.password}"
        url += f"@{self.host}:{self.port}/{self.name}"

        # Add SSL parameters if configured
        params = []
        if self.ssl_mode:
            params.append(f"sslmode={self.ssl_mode}")
        if self.ssl_cert:
            params.append(f"sslcert={self.ssl_cert}")
        if self.ssl_key:
            params.append(f"sslkey={self.ssl_key}")
        if self.ssl_ca:
            params.append(f"sslrootcert={self.ssl_ca}")

        if params:
            url += "?" + "&".join(params)

        return url

    @property
    def sync_database_url(self) -> str:
        """Generate synchronous PostgreSQL database URL for Alembic."""
        url = f"postgresql://{self.user}"
        if self.password:
            url += f":{self.password}"
        url += f"@{self.host}:{self.port}/{self.name}"

        # Add SSL parameters if configured
        params = []
        if self.ssl_mode:
            params.append(f"sslmode={self.ssl_mode}")
        if self.ssl_cert:
            params.append(f"sslcert={self.ssl_cert}")
        if self.ssl_key:
            params.append(f"sslkey={self.ssl_key}")
        if self.ssl_ca:
            params.append(f"sslrootcert={self.ssl_ca}")

        if params:
            url += "?" + "&".join(params)

        return url

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.host:
            raise ValueError("Database host is required")
        if not self.name:
            raise ValueError("Database name is required")
        if not self.user:
            raise ValueError("Database user is required")
        if self.port <= 0:
            raise ValueError("Database port must be positive")
        if self.pool_size <= 0:
            raise ValueError("Pool size must be positive")


# Global configuration instance
db_config = DatabaseConfig()
